"""
Purchase Flow Handlers

Implements the full ticket purchase flow in Telegram chat:
Buy → Session selection → Seat category → Quantity → Reservation → Cart → Payment → Tickets
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.bot.localization import get_text, get_user_language
    from app.bot.states import PurchaseStates
    from app.core.database import get_async_session, async_session_maker
    from app.models import Agent, User, UserSession, Order
    from app.services.bill24 import Bill24Client, Bill24Error, Bill24SessionError
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.bot.localization import get_text, get_user_language
    from backend.app.bot.states import PurchaseStates
    from backend.app.core.database import get_async_session, async_session_maker
    from backend.app.models import Agent, User, UserSession, Order
    from backend.app.services.bill24 import Bill24Client, Bill24Error, Bill24SessionError
    from backend.app.core.config import settings

logger = logging.getLogger(__name__)

purchase_router = Router(name="purchase")


# =============================================================================
# Helper: get authenticated Bill24 client for user + agent
# =============================================================================

async def get_bill24_client_for_user(
    db_session: AsyncSession, user: User, agent: Agent
) -> Bill24Client:
    """
    Get or create a Bill24 client authenticated with the user's session.

    If no active UserSession exists for this user+agent, calls CREATE_USER
    to get one and stores it in the DB.
    """
    # Look for existing active session
    result = await db_session.execute(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.agent_id == agent.id,
            UserSession.is_active == True,
        )
    )
    user_session = result.scalar_one_or_none()

    if user_session:
        return Bill24Client(
            fid=agent.fid,
            token=agent.token,
            zone=agent.zone or "test",
            user_id=user_session.bil24_user_id,
            session_id=user_session.bil24_session_id,
        )

    # No session — create user in Bill24
    anon_client = Bill24Client(
        fid=agent.fid, token=agent.token, zone=agent.zone or "test"
    )
    try:
        resp = await anon_client.create_user(
            telegram_chat_id=user.telegram_chat_id,
            first_name=user.telegram_first_name,
            last_name=user.telegram_last_name,
        )
        new_session = UserSession(
            user_id=user.id,
            agent_id=agent.id,
            bil24_user_id=resp["userId"],
            bil24_session_id=resp["sessionId"],
            is_active=True,
        )
        db_session.add(new_session)
        await db_session.commit()

        return Bill24Client(
            fid=agent.fid,
            token=agent.token,
            zone=agent.zone or "test",
            user_id=resp["userId"],
            session_id=resp["sessionId"],
        )
    finally:
        await anon_client.close()


async def _get_user_and_agent(
    db_session: AsyncSession, telegram_user_id: int
) -> tuple:
    """Get User and their current Agent from DB. Returns (user, agent, lang)."""
    result = await db_session.execute(
        select(User).where(User.telegram_chat_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.current_agent_id:
        return None, None, "ru"

    lang = user.preferred_language or "ru"

    result = await db_session.execute(
        select(Agent).where(Agent.id == user.current_agent_id)
    )
    agent = result.scalar_one_or_none()
    return user, agent, lang


# =============================================================================
# Step 2: User clicks "Buy Ticket" → show sessions
# =============================================================================

@purchase_router.callback_query(F.data.startswith("buy_"))
async def handle_buy_ticket(callback: CallbackQuery, state: FSMContext):
    """Entry point: get sessions from cached events, show selection."""
    action_id = int(callback.data.split("_")[1])
    await callback.answer()

    async for db_session in get_async_session():
        user, agent, lang = await _get_user_and_agent(
            db_session, callback.from_user.id
        )
        if not user or not agent:
            await callback.message.answer(get_text("error_no_agent", lang))
            return

        try:
            # Get event data from cache (GET_ALL_ACTIONS already has actionEventList)
            try:
                from app.bot.handlers import fetch_events_from_bill24
            except ModuleNotFoundError:
                from backend.app.bot.handlers import fetch_events_from_bill24

            events = await fetch_events_from_bill24(agent)
            event = next(
                (e for e in events if e.get("actionId") == action_id), None
            )
            if not event:
                await callback.message.answer(get_text("error_event_not_found", lang))
                return

            sessions = event.get("actionEventList", [])
            event_name = event.get(
                "fullActionName", event.get("actionName", "")
            )

            if not sessions:
                await callback.message.answer(get_text("error_no_sessions", lang))
                return

            # If only one session, skip selection and go directly to categories
            if len(sessions) == 1:
                s = sessions[0]
                ae_id = s.get("actionEventId")
                # Extract categories from categoryLimitList
                categories = _extract_categories(s)
                if not categories:
                    await callback.message.answer(
                        get_text("error_no_seats_available", lang)
                    )
                    return

                session_currency = s.get("currency", "")
                await state.update_data(
                    action_id=action_id,
                    action_name=event_name,
                    action_event_id=ae_id,
                    categories=categories,
                    currency=session_currency,
                )
                await state.set_state(PurchaseStates.selecting_seats)
                await _show_categories(callback, lang, ae_id, categories, currency=session_currency)
                return

            # Multiple sessions — show selection
            await state.update_data(
                action_id=action_id,
                action_name=event_name,
                sessions_data={
                    str(s.get("actionEventId")): s for s in sessions
                },
            )
            await state.set_state(PurchaseStates.selecting_session)

            builder = InlineKeyboardBuilder()
            for s in sessions:
                ae_id = s.get("actionEventId")
                day = s.get("day", "")
                time_str = s.get("time", "")
                avail = s.get("availability", 0)
                label = f"📅 {day} {time_str} ({avail} шт.)"
                builder.row(
                    InlineKeyboardButton(
                        text=label, callback_data=f"session_{ae_id}"
                    )
                )
            builder.row(
                InlineKeyboardButton(
                    text=get_text("btn_cancel_purchase", lang),
                    callback_data="cancel_purchase",
                )
            )

            await callback.message.answer(
                get_text("select_session", lang, event_name=event_name),
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.exception(f"Buy ticket failed: {e}")
            await callback.message.answer(get_text("error_fetching_events", lang))


# =============================================================================
# Helpers for category extraction
# =============================================================================

def _extract_categories(session_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract ticket categories from an actionEvent's categoryLimitList.

    For non-placement events (GA), categories come from categoryLimitList.
    For placement events, we'd use GET_SEAT_LIST (handled separately).
    """
    categories: Dict[str, Dict[str, Any]] = {}
    for cl in session_data.get("categoryLimitList", []):
        for cat in cl.get("categoryList", []):
            cat_id = str(cat.get("categoryPriceId", 0))
            categories[cat_id] = {
                "name": cat.get("categoryPriceName", "Standard"),
                "price": cat.get("price", 0),
                "count": cat.get("availability", 0),
                "placement": cat.get("placement", False),
                "seat_ids": [],  # For non-placement; filled by GET_SEAT_LIST if needed
            }
    return categories


async def _show_categories(
    callback: CallbackQuery,
    lang: str,
    action_event_id: int,
    categories: Dict[str, Dict[str, Any]],
    currency: str = "",
):
    """Show category selection keyboard."""
    builder = InlineKeyboardBuilder()
    for cat_id, cat in categories.items():
        avail = cat["count"]
        builder.row(
            InlineKeyboardButton(
                text=f"🎫 {cat['name']} — {cat['price']} {currency} ({avail} шт.)",
                callback_data=f"cat_{action_event_id}_{cat_id}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_cancel_purchase", lang),
            callback_data="cancel_purchase",
        )
    )

    await callback.message.answer(
        get_text("select_category", lang),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# =============================================================================
# Step 4: User selects session → show seat categories
# =============================================================================

@purchase_router.callback_query(
    PurchaseStates.selecting_session, F.data.startswith("session_")
)
async def handle_select_session(callback: CallbackQuery, state: FSMContext):
    """User picked a session — extract categories and show them."""
    action_event_id = int(callback.data.split("_")[1])
    await callback.answer()

    data = await state.get_data()
    lang = get_user_language(
        callback.from_user.language_code if callback.from_user else None
    )

    # Get session data from FSM
    sessions_data = data.get("sessions_data", {})
    session_info = sessions_data.get(str(action_event_id))

    if not session_info:
        await callback.message.answer(get_text("error_no_sessions", lang))
        await state.clear()
        return

    # Extract categories from categoryLimitList (non-placement events)
    categories = _extract_categories(session_info)

    if not categories:
        # Try GET_SEAT_LIST for placement events
        async for db_session in get_async_session():
            user, agent, _ = await _get_user_and_agent(
                db_session, callback.from_user.id
            )
            if user and agent:
                client = await get_bill24_client_for_user(db_session, user, agent)
                try:
                    seat_list = await client.get_seat_list(action_event_id)
                    for seat in seat_list:
                        if seat.get("statusInt") != 0:
                            continue
                        cat_id = str(seat.get("seatCategoryId", 0))
                        cat_name = seat.get("seatCategoryName", "Standard")
                        price = seat.get("price", 0)
                        if cat_id not in categories:
                            categories[cat_id] = {
                                "name": cat_name,
                                "price": price,
                                "count": 0,
                                "placement": True,
                                "seat_ids": [],
                            }
                        categories[cat_id]["seat_ids"].append(seat.get("seatId"))
                        categories[cat_id]["count"] = len(categories[cat_id]["seat_ids"])
                finally:
                    await client.close()

    if not categories:
        await callback.message.answer(get_text("error_no_seats_available", lang))
        await state.clear()
        return

    session_currency = session_info.get("currency", "") if session_info else ""
    await state.update_data(
        action_event_id=action_event_id,
        categories=categories,
        currency=session_currency,
    )
    await state.set_state(PurchaseStates.selecting_seats)
    await _show_categories(callback, lang, action_event_id, categories, currency=session_currency)


# =============================================================================
# Step 5b: User selects category → show quantity buttons
# =============================================================================

@purchase_router.callback_query(
    PurchaseStates.selecting_seats, F.data.startswith("cat_")
)
async def handle_select_category(callback: CallbackQuery, state: FSMContext):
    """Show quantity selection for chosen category."""
    parts = callback.data.split("_")
    action_event_id = int(parts[1])
    cat_id = parts[2]
    await callback.answer()

    data = await state.get_data()
    lang = get_user_language(
        callback.from_user.language_code if callback.from_user else None
    )
    categories = data.get("categories", {})
    cat = categories.get(cat_id)

    if not cat:
        await callback.message.answer(get_text("error_general", lang))
        await state.clear()
        return

    await state.update_data(selected_cat_id=cat_id)

    max_qty = min(cat["count"], 6)

    builder = InlineKeyboardBuilder()
    row_buttons = []
    for qty in range(1, max_qty + 1):
        row_buttons.append(
            InlineKeyboardButton(
                text=str(qty),
                callback_data=f"qty_{action_event_id}_{cat_id}_{qty}",
            )
        )
        if len(row_buttons) == 3:
            builder.row(*row_buttons)
            row_buttons = []
    if row_buttons:
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_cancel_purchase", lang),
            callback_data="cancel_purchase",
        )
    )

    await callback.message.answer(
        get_text(
            "select_quantity",
            lang,
            category=cat["name"],
            price=cat["price"],
            max_qty=max_qty,
            currency=data.get("currency", ""),
        ),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# =============================================================================
# Step 6-7: Quantity selected → RESERVE → show cart
# =============================================================================

@purchase_router.callback_query(
    PurchaseStates.selecting_seats, F.data.startswith("qty_")
)
async def handle_select_quantity(callback: CallbackQuery, state: FSMContext):
    """Reserve seats and show cart summary."""
    parts = callback.data.split("_")
    action_event_id = int(parts[1])
    cat_id = parts[2]
    quantity = int(parts[3])
    await callback.answer()

    data = await state.get_data()
    categories = data.get("categories", {})
    cat = categories.get(cat_id)
    if not cat:
        await callback.message.answer(get_text("error_general", "ru"))
        await state.clear()
        return

    is_placement = cat.get("placement", False)
    seat_ids = cat.get("seat_ids", [])[:quantity] if is_placement else []

    async for db_session in get_async_session():
        user, agent, lang = await _get_user_and_agent(
            db_session, callback.from_user.id
        )
        if not user or not agent:
            await state.clear()
            return

        client = await get_bill24_client_for_user(db_session, user, agent)
        try:
            loading_msg = await callback.message.answer(
                get_text("reserving_seats", lang)
            )

            # For GA (non-placement): use categoryList
            # For placement: use seatList
            if is_placement and seat_ids:
                reserve_result = await client.reserve_seats(
                    action_event_id, seat_ids=seat_ids
                )
            else:
                reserve_result = await client.reserve_seats(
                    action_event_id,
                    category_list=[
                        {
                            "categoryPriceId": int(cat_id),
                            "quantity": quantity,
                        }
                    ],
                )
            cart_timeout = reserve_result.get("cartTimeout", 600)
            total_sum = reserve_result.get("totalSum", 0)

            expires_at = datetime.utcnow() + timedelta(seconds=cart_timeout)
            minutes_left = cart_timeout // 60

            currency = reserve_result.get("currency", "ILS")

            await state.update_data(
                reserved_seat_ids=seat_ids,
                action_event_id=action_event_id,
                cart_timeout=cart_timeout,
                currency=currency,
                total_sum=total_sum,
                category_name=cat["name"],
                quantity=quantity,
            )
            await state.set_state(PurchaseStates.cart_confirmation)

            cart_text = get_text(
                "cart_summary",
                lang,
                event_name=data.get("action_name", ""),
                category=cat["name"],
                quantity=quantity,
                total=total_sum,
                timeout_minutes=minutes_left,
                currency=currency,
            )

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=get_text("btn_pay", lang),
                    callback_data="confirm_pay",
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text=get_text("btn_cancel_purchase", lang),
                    callback_data="cancel_reservation",
                )
            )

            await loading_msg.edit_text(
                cart_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )

        except Bill24Error as e:
            logger.error(f"RESERVATION failed: {e}")
            await callback.message.answer(
                get_text("error_reservation_failed", lang)
            )
            await state.clear()
        finally:
            await client.close()


# =============================================================================
# Step 8-9: User clicks "Pay" → create order → show payment link
# =============================================================================

@purchase_router.callback_query(
    PurchaseStates.cart_confirmation, F.data == "confirm_pay"
)
async def handle_confirm_pay(callback: CallbackQuery, state: FSMContext):
    """Create order and show payment link."""
    await callback.answer()

    async for db_session in get_async_session():
        user, agent, lang = await _get_user_and_agent(
            db_session, callback.from_user.id
        )
        if not user or not agent:
            await state.clear()
            return

        data = await state.get_data()
        client = await get_bill24_client_for_user(db_session, user, agent)

        try:
            # Variant A: Bill24 acquiring (Ticket Agent)
            bot_username = settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot"

            full_name = (
                f"{user.telegram_first_name} {user.telegram_last_name or ''}"
            ).strip()

            full_name = (
                f"{user.telegram_first_name} {user.telegram_last_name or ''}"
            ).strip()

            # Note: We can't include our DB order_id in successUrl because
            # it doesn't exist yet. Instead, we save the order first without
            # formUrl, then create the Bill24 order.
            # For the deep link, we use a simple return to bot —
            # the paid_ handler will find the latest unpaid order for this user.
            success_deep = f"https://t.me/{bot_username}?start=paid"
            fail_deep = f"https://t.me/{bot_username}"

            order_result = await client.create_order(
                success_url=success_deep,
                fail_url=fail_deep,
                full_name=full_name,
            )

            bil24_order_id = order_result.get("orderId")
            form_url = order_result.get("formUrl", "")

            # Save order to DB
            db_order = Order(
                user_id=user.id,
                agent_id=agent.id,
                bil24_order_id=bil24_order_id,
                status="NEW",
                total_sum=Decimal(str(data.get("total_sum", 0))),
                currency=data.get("currency", "ILS"),
                ticket_count=data.get("quantity", 0),
                payment_type=agent.payment_type or "bill24_acquiring",
                bil24_form_url=form_url,
            )
            db_session.add(db_order)
            await db_session.commit()
            await db_session.refresh(db_order)

            await state.update_data(
                order_id=db_order.id,
                bil24_order_id=bil24_order_id,
            )
            await state.set_state(PurchaseStates.payment_pending)

            # Send payment button
            builder = InlineKeyboardBuilder()

            # Check if Stripe is configured — use Mini App for payment
            if settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY:
                import urllib.parse
                pay_params = urllib.parse.urlencode({
                    "order_id": db_order.id,
                    "event": data.get("action_name", "")[:50],
                    "amount": data.get("total_sum", 0),
                    "currency": db_order.currency or "ILS",
                    "tickets": data.get("quantity", 1),
                })
                # Base URL from PAYMENT_SUCCESS_URL or construct from settings
                base_url = settings.PAYMENT_SUCCESS_URL or f"https://t.me/{bot_username}"
                if base_url.startswith("https://t.me"):
                    # No web domain set — fall back to form_url
                    pay_url = form_url
                    builder.row(
                        InlineKeyboardButton(
                            text=get_text("btn_open_payment", lang),
                            url=pay_url,
                        )
                    )
                else:
                    # Web domain available — use Mini App with Stripe
                    pay_url = f"{base_url.rstrip('/')}/static/pay.html?{pay_params}"
                    builder.row(
                        InlineKeyboardButton(
                            text=get_text("btn_open_payment", lang),
                            web_app=WebAppInfo(url=pay_url),
                        )
                    )
            else:
                # Bill24 acquiring — open formUrl in browser
                builder.row(
                    InlineKeyboardButton(
                        text=get_text("btn_open_payment", lang),
                        url=form_url,
                    )
                )

            builder.row(
                InlineKeyboardButton(
                    text=get_text("btn_check_payment", lang),
                    callback_data=f"check_payment_{db_order.id}",
                )
            )

            await callback.message.answer(
                get_text(
                    "payment_redirect",
                    lang,
                    amount=data.get("total_sum", 0),
                    currency=data.get("currency", ""),
                ),
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )

            logger.info(
                f"Order created: db_id={db_order.id}, "
                f"bil24_id={bil24_order_id}, user={user.telegram_chat_id}"
            )

        except Bill24Error as e:
            logger.error(f"CREATE_ORDER failed: {e}")
            await callback.message.answer(
                get_text("error_create_order_failed", lang)
            )
            await state.clear()
        finally:
            await client.close()


# =============================================================================
# Check payment status manually
# =============================================================================

@purchase_router.callback_query(F.data.startswith("check_payment_"))
async def handle_check_payment(callback: CallbackQuery, state: FSMContext):
    """User manually checks if payment went through."""
    order_db_id = int(callback.data.split("_")[2])

    async for db_session in get_async_session():
        user, agent, lang = await _get_user_and_agent(
            db_session, callback.from_user.id
        )
        if not user or not agent:
            await callback.answer(get_text("error_general", lang))
            return

        # Get order from DB
        result = await db_session.execute(
            select(Order).where(Order.id == order_db_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await callback.answer(get_text("error_general", lang))
            return

        # Already paid?
        if order.status == "PAID":
            await callback.answer()
            await callback.message.answer(
                get_text("payment_confirmed", lang), parse_mode="HTML"
            )
            await state.clear()
            return

        # Check Bill24
        client = await get_bill24_client_for_user(db_session, user, agent)
        try:
            info = await client.get_order_info(order.bil24_order_id)
            status = info.get("statusExtStr", "")

            if status == "PAID":
                order.status = "PAID"
                order.paid_at = datetime.utcnow()
                await db_session.commit()

                await callback.answer()
                await callback.message.answer(
                    get_text("payment_confirmed", lang), parse_mode="HTML"
                )
                await state.clear()

                # Trigger ticket delivery (inline, without arq)
                try:
                    await _deliver_tickets(
                        order.id, order.bil24_order_id,
                        user.telegram_chat_id, agent, lang,
                    )
                except Exception as te:
                    logger.error(f"Ticket delivery failed: {te}")

                logger.info(
                    f"Payment confirmed: order={order.id}, "
                    f"bil24={order.bil24_order_id}"
                )

            elif status in ("CANCELLED", "EXPIRED"):
                order.status = "CANCELLED"
                await db_session.commit()

                await callback.answer()
                await callback.message.answer(
                    get_text("error_payment_failed", lang)
                )
                await state.clear()
            else:
                await callback.answer(
                    get_text("payment_not_yet", lang), show_alert=True
                )
        except Bill24Error as e:
            logger.error(f"GET_ORDER_INFO failed: {e}")
            await callback.answer(
                get_text("error_general", lang), show_alert=True
            )
        finally:
            await client.close()


# =============================================================================
# Cancel handlers
# =============================================================================

@purchase_router.callback_query(F.data == "cancel_purchase")
async def handle_cancel_purchase(callback: CallbackQuery, state: FSMContext):
    """Cancel purchase at any point before reservation."""
    lang = get_user_language(
        callback.from_user.language_code if callback.from_user else None
    )
    await callback.answer()
    await state.clear()
    await callback.message.answer(get_text("purchase_cancelled", lang))


@purchase_router.callback_query(F.data == "cancel_reservation")
async def handle_cancel_reservation(callback: CallbackQuery, state: FSMContext):
    """Cancel after reservation — release seats via UN_RESERVE_ALL."""
    lang = get_user_language(
        callback.from_user.language_code if callback.from_user else None
    )
    await callback.answer()

    data = await state.get_data()
    action_event_id = data.get("action_event_id")

    if action_event_id:
        async for db_session in get_async_session():
            user, agent, _ = await _get_user_and_agent(
                db_session, callback.from_user.id
            )
            if user and agent:
                client = await get_bill24_client_for_user(db_session, user, agent)
                try:
                    await client.unreserve_all(action_event_id)
                except Exception as e:
                    logger.warning(f"UN_RESERVE_ALL failed: {e}")
                finally:
                    await client.close()

    await state.clear()
    await callback.message.answer(get_text("purchase_cancelled", lang))


# =============================================================================
# Ticket delivery (inline, without arq)
# =============================================================================

def _generate_qr_code(data: str) -> bytes:
    """Generate QR code PNG image from data string."""
    import io
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_barcode(number: str) -> bytes:
    """Generate wide barcode PNG image from number string."""
    import io
    import barcode
    from barcode.writer import ImageWriter

    ean = barcode.get("ean13", number[:12], writer=ImageWriter())
    buf = io.BytesIO()
    ean.write(buf, options={
        "write_text": True,
        "module_height": 15,
        "module_width": 0.6,  # Wide bars — full width
        "quiet_zone": 2,  # Minimal side padding
        "font_size": 14,
        "text_distance": 8,  # Gap between bars and number
    })
    buf.seek(0)
    return buf.getvalue()


async def _deliver_tickets(
    order_id: int,
    bil24_order_id: int,
    chat_id: int,
    agent: Agent,
    lang: str,
):
    """Fetch tickets from Bill24 and send them to the user with QR + barcode."""
    import base64
    from aiogram.types import BufferedInputFile, URLInputFile, InputMediaPhoto

    try:
        from app.bot.bot import get_bot
    except ModuleNotFoundError:
        from backend.app.bot.bot import get_bot

    bot = get_bot()

    async with async_session_maker() as db_session:
        result = await db_session.execute(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        client = await get_bill24_client_for_user(db_session, user, agent)

    try:
        tickets = await client.get_tickets_by_order(bil24_order_id)
        if not tickets:
            logger.warning(f"No tickets for order {bil24_order_id}")
            return

        for ticket in tickets:
            # Parse date/time from "dd.MM.yyyy HH:mm"
            date_raw = ticket.get("date", "")
            date_str, time_str = "", ""
            if date_raw:
                parts = date_raw.split(" ", 1)
                date_str = parts[0] if parts else ""
                time_str = parts[1] if len(parts) > 1 else ""

            barcode_number = ticket.get("barCodeNumber", "")
            promoter = ticket.get("legalOwnerName", ticket.get("legalOwner", ""))
            age_limit = ticket.get("age", "")
            category = ticket.get("categoryName", "")
            venue_name = ticket.get("venueName", "")
            venue_address = ticket.get("venueAddress", "")
            venue_full = f"{venue_name}, {venue_address}" if venue_address else venue_name

            # Build ticket text (Bill24 ticket format)
            text_parts = [
                f"<b>Ticket number: {ticket.get('ticketId', '')}</b>",
                "",
                f"<b>{ticket.get('actionName', '')}</b>",
                f"📍 {venue_full}",
                f"📅 Date: {date_str}  Time: {time_str}",
            ]

            if category:
                text_parts.append(f"🎫 Category: {category}")

            # Seat info (for placement events)
            sector = ticket.get("sector")
            row_val = ticket.get("row")
            number = ticket.get("number")
            if sector or row_val or number:
                seat_parts = []
                if sector:
                    seat_parts.append(sector)
                if row_val:
                    seat_parts.append(f"Row {row_val}")
                if number:
                    seat_parts.append(f"Seat {number}")
                text_parts.append(f"🪑 {', '.join(seat_parts)}")

            text_parts.append(f"💰 Price: {ticket.get('price', 0)}")
            text_parts.append("")

            if promoter or age_limit:
                promo_line = []
                if promoter:
                    promo_line.append(f"Promoter: {promoter}")
                if age_limit:
                    promo_line.append(f"Age limit: {age_limit}")
                text_parts.append(", ".join(promo_line))

            # Legal disclaimer
            text_parts.append("")
            text_parts.append(
                "<i>The process of purchasing, using, and refunding "
                "electronic tickets is described in the User Agreement, "
                f"which is published on the website belonging to {promoter}</i>"
            )

            ticket_text = "\n".join(text_parts)

            # Poster URL
            poster_url = ticket.get("smallPosterUrl", "")

            # Barcode only (no QR) — use Bill24 image or generate
            bc_data = ticket.get("barCodeImg", "")
            bc_bytes = None
            if bc_data:
                bc_bytes = base64.b64decode(bc_data)
            elif barcode_number and len(barcode_number) >= 12:
                try:
                    bc_bytes = _generate_barcode(barcode_number)
                except Exception as e:
                    logger.warning(f"Barcode generation failed: {e}")

            # Send: poster (with caption) + barcode
            media = []

            if poster_url:
                media.append(
                    InputMediaPhoto(
                        media=URLInputFile(poster_url),
                        caption=ticket_text,
                        parse_mode="HTML",
                    )
                )

            if bc_bytes:
                bc_file = BufferedInputFile(bc_bytes, filename="barcode.png")
                if not media:
                    media.append(
                        InputMediaPhoto(
                            media=bc_file,
                            caption=ticket_text,
                            parse_mode="HTML",
                        )
                    )
                else:
                    media.append(InputMediaPhoto(media=bc_file))

            if media:
                try:
                    await bot.send_media_group(chat_id=chat_id, media=media)
                except Exception as e:
                    logger.error(f"send_media_group failed: {e}")
                    await bot.send_message(
                        chat_id=chat_id, text=ticket_text, parse_mode="HTML"
                    )
            else:
                await bot.send_message(
                    chat_id=chat_id, text=ticket_text, parse_mode="HTML"
                )

        logger.info(
            f"Delivered {len(tickets)} tickets for order {bil24_order_id} "
            f"to {chat_id}"
        )

    except Bill24Error as e:
        logger.error(f"GET_TICKETS_BY_ORDER failed for {bil24_order_id}: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=get_text("payment_confirmed", lang),
            parse_mode="HTML",
        )
    finally:
        await client.close()


# =============================================================================
# Auto-return after payment: /start paid
# =============================================================================

async def handle_paid_return(message, deep_link_param: str):
    """
    Handle return from payment via deep link /start paid.

    Finds the user's latest NEW order, checks Bill24 for payment status,
    and delivers tickets if paid. Prevents duplicate delivery by checking
    order status in DB.
    """
    from aiogram.types import Message

    telegram_user = message.from_user
    lang = get_user_language(
        telegram_user.language_code if telegram_user else None
    )

    async for db_session in get_async_session():
        # Find user
        result = await db_session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(get_text("error_no_agent", lang))
            return

        lang = user.preferred_language or lang

        # Find the latest order for this user that might need checking
        # Look for NEW orders first (not yet confirmed)
        result = await db_session.execute(
            select(Order)
            .where(
                Order.user_id == user.id,
                Order.status == "NEW",
            )
            .order_by(Order.id.desc())
            .limit(1)
        )
        order = result.scalar_one_or_none()

        if not order:
            # No pending orders — check if there's a recently paid one
            # (user might have clicked the link twice)
            result = await db_session.execute(
                select(Order)
                .where(
                    Order.user_id == user.id,
                    Order.status == "PAID",
                )
                .order_by(Order.id.desc())
                .limit(1)
            )
            paid_order = result.scalar_one_or_none()
            if paid_order:
                await message.answer(
                    get_text("payment_confirmed", lang),
                    parse_mode="HTML",
                )
            else:
                await message.answer(get_text("error_no_agent", lang))
            return

        # Get agent for this order
        result = await db_session.execute(
            select(Agent).where(Agent.id == order.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            await message.answer(get_text("error_general", lang))
            return

        # Check payment status with Bill24
        client = await get_bill24_client_for_user(db_session, user, agent)
        try:
            info = await client.get_order_info(order.bil24_order_id)
            status = info.get("statusExtStr", "")

            if status == "PAID":
                # Mark as paid (prevents duplicate delivery)
                order.status = "PAID"
                order.paid_at = datetime.utcnow()
                await db_session.commit()

                await message.answer(
                    get_text("payment_confirmed", lang),
                    parse_mode="HTML",
                )

                # Deliver tickets
                try:
                    await _deliver_tickets(
                        order.id, order.bil24_order_id,
                        user.telegram_chat_id, agent, lang,
                    )
                except Exception as e:
                    logger.error(f"Ticket delivery failed: {e}")

            elif status in ("CANCELLED", "EXPIRED"):
                order.status = "CANCELLED"
                await db_session.commit()
                await message.answer(get_text("error_payment_failed", lang))

            else:
                # Not yet paid — show check button
                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(
                        text=get_text("btn_check_payment", lang),
                        callback_data=f"check_payment_{order.id}",
                    )
                )
                # If formUrl is available, show pay button too
                if order.bil24_form_url:
                    builder.row(
                        InlineKeyboardButton(
                            text=get_text("btn_open_payment", lang),
                            url=order.bil24_form_url,
                        )
                    )
                await message.answer(
                    get_text("payment_not_yet", lang),
                    reply_markup=builder.as_markup(),
                )
        except Bill24Error as e:
            logger.error(f"GET_ORDER_INFO failed on paid return: {e}")
            await message.answer(get_text("error_general", lang))
        finally:
            await client.close()
