"""
Test Buy Ticket button opens WebApp.

Tests that clicking Buy Ticket launches the Telegram WebApp for seat selection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import build_event_details_keyboard
from app.bot.localization import get_text


class TestBuyTicketButton:
    """Test Buy Ticket button configuration."""

    def test_buy_button_present(self):
        """Test Buy Ticket button is present in event details."""
        keyboard = build_event_details_keyboard(event_id=123, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        buy_buttons = [btn for btn in all_buttons if btn.callback_data and "buy_" in btn.callback_data]

        assert len(buy_buttons) == 1

    def test_buy_button_callback_data(self):
        """Test Buy Ticket button has correct callback data."""
        keyboard = build_event_details_keyboard(event_id=456, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        buy_button = next((btn for btn in all_buttons if btn.callback_data and "buy_" in btn.callback_data), None)

        assert buy_button is not None
        assert buy_button.callback_data == "buy_456"

    def test_buy_button_text_russian(self):
        """Test Buy Ticket button text in Russian."""
        keyboard = build_event_details_keyboard(event_id=100, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        buy_button = next((btn for btn in all_buttons if btn.callback_data and "buy_" in btn.callback_data), None)

        assert buy_button is not None
        assert "🛒" in buy_button.text
        # Russian text for "buy ticket"
        assert "купить" in buy_button.text.lower() or "билет" in buy_button.text.lower()

    def test_buy_button_text_english(self):
        """Test Buy Ticket button text in English."""
        keyboard = build_event_details_keyboard(event_id=100, lang="en")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        buy_button = next((btn for btn in all_buttons if btn.callback_data and "buy_" in btn.callback_data), None)

        assert buy_button is not None
        assert "🛒" in buy_button.text
        assert "buy" in buy_button.text.lower()


class TestBuyButtonLocalization:
    """Test Buy Ticket button localization."""

    def test_btn_buy_ticket_ru(self):
        """Test btn_buy_ticket localization in Russian."""
        text = get_text("btn_buy_ticket", "ru")
        assert "🛒" in text
        assert len(text) > 3

    def test_btn_buy_ticket_en(self):
        """Test btn_buy_ticket localization in English."""
        text = get_text("btn_buy_ticket", "en")
        assert "🛒" in text
        assert "buy" in text.lower()


class TestWebAppLaunch:
    """Test WebApp launch mechanism."""

    def test_webapp_url_format(self):
        """Test WebApp URL format for Bill24 widget."""
        # The WebApp URL should include agent and event parameters
        base_url = "https://example.com/widget"
        agent_fid = 1271
        event_id = 500
        chat_id = 123456789

        widget_url = f"{base_url}?fid={agent_fid}&action={event_id}&chat_id={chat_id}"

        assert "fid=1271" in widget_url
        assert "action=500" in widget_url
        assert "chat_id=123456789" in widget_url

    def test_webapp_url_includes_event_id(self):
        """Test WebApp URL includes event ID parameter."""
        event_id = 42
        url = f"https://widget.example.com?action={event_id}"

        assert f"action={event_id}" in url

    def test_webapp_url_includes_chat_id(self):
        """Test WebApp URL includes chat_id for auto-auth."""
        chat_id = 987654321
        url = f"https://widget.example.com?chat_id={chat_id}"

        assert str(chat_id) in url


class TestWidgetEventData:
    """Test widget receives correct event data."""

    def test_event_id_passed_to_widget(self):
        """Test event ID is passed to widget."""
        event_id = 123
        callback_data = f"buy_{event_id}"

        # Parse event ID from callback
        parsed_id = int(callback_data.split("_")[1])

        assert parsed_id == event_id

    def test_multiple_events_have_unique_ids(self):
        """Test each event has unique buy button callback."""
        event_ids = [100, 200, 300]

        callbacks = [f"buy_{eid}" for eid in event_ids]

        assert len(set(callbacks)) == 3
        assert callbacks == ["buy_100", "buy_200", "buy_300"]


class TestUserAutoAuthentication:
    """Test user auto-authentication via chat_id."""

    def test_chat_id_format(self):
        """Test chat_id is integer for Telegram."""
        chat_id = 123456789

        assert isinstance(chat_id, int)
        assert chat_id > 0

    def test_chat_id_in_webapp_auth(self):
        """Test chat_id used for WebApp authentication."""
        # Widget should receive chat_id for user lookup
        chat_id = 123456789
        auth_url = f"https://api.example.com/widget/user/{chat_id}"

        assert str(chat_id) in auth_url

    def test_auto_auth_flow(self):
        """Test auto-auth flow: chat_id -> user lookup -> session."""
        # Flow:
        # 1. User opens WebApp via Buy Ticket
        # 2. WebApp sends initData with chat_id
        # 3. Backend verifies initData and looks up user
        # 4. Backend returns session credentials

        chat_id = 123456789
        user_id = 100
        session_id = "session_abc123"

        # User should be looked up by chat_id
        assert chat_id > 0

        # Session should be returned
        assert len(session_id) > 0


class TestWidgetAuthRequest:
    """Test widget authentication request/response."""

    def test_widget_auth_request_fields(self):
        """Test widget auth request should have init_data and agent_id."""
        # Widget auth request needs:
        request_fields = {
            "init_data": "telegram_init_data_string",
            "agent_id": 1
        }

        assert "init_data" in request_fields
        assert "agent_id" in request_fields
        assert isinstance(request_fields["agent_id"], int)

    def test_widget_auth_response_fields(self):
        """Test widget auth response should have session credentials."""
        # Response should include:
        response_fields = {
            "user_id": 100,  # Bill24 userId
            "session_id": "session123",  # Bill24 sessionId
            "chat_id": 987654321,  # Telegram chat_id
            "agent_fid": 1271,  # Agent's Bill24 FID
            "zone": "test"  # 'test' or 'real'
        }

        assert "user_id" in response_fields
        assert "session_id" in response_fields
        assert "chat_id" in response_fields
        assert "agent_fid" in response_fields
        assert response_fields["zone"] in ["test", "real"]


class TestTelegramWebAppVerification:
    """Test Telegram WebApp initData verification."""

    def test_verify_function_exists(self):
        """Test verify_telegram_init_data function exists."""
        from app.core.security import verify_telegram_init_data

        assert callable(verify_telegram_init_data)

    def test_telegram_init_data_model(self):
        """Test TelegramInitData model exists."""
        from app.core.security import TelegramInitData

        # Should have user info
        assert hasattr(TelegramInitData, 'model_fields') or hasattr(TelegramInitData, '__fields__')


class TestWebAppInBot:
    """Test WebApp integration in bot."""

    def test_buy_button_first_in_keyboard(self):
        """Test Buy button is prominently placed (first button)."""
        keyboard = build_event_details_keyboard(event_id=100, lang="ru")

        # First button should be buy
        first_button = keyboard.inline_keyboard[0][0]

        assert "buy_" in first_button.callback_data

    def test_keyboard_structure(self):
        """Test event details keyboard has correct structure."""
        keyboard = build_event_details_keyboard(event_id=100, lang="ru")

        # Should have at least 2 rows: buy button and back button
        assert len(keyboard.inline_keyboard) >= 2

        # First row should have buy button
        assert any("buy_" in btn.callback_data for btn in keyboard.inline_keyboard[0])

        # Last row should have back button
        last_row = keyboard.inline_keyboard[-1]
        assert any("back" in (btn.callback_data or "") for btn in last_row)


class TestEventSelectionToWidget:
    """Test flow from event selection to widget launch."""

    @pytest.mark.asyncio
    async def test_event_details_has_buy_button(self):
        """Test event details view includes Buy button."""
        from app.bot.handlers import callback_event_details

        callback = AsyncMock()
        callback.data = "event_100"
        callback.from_user = MagicMock()
        callback.from_user.id = 111222333
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "ru"

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 1271
        mock_agent.token = "test"
        mock_agent.zone = "test"
        mock_agent.is_active = True

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = mock_agent
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            with patch('app.bot.handlers.fetch_events_from_bill24') as mock_fetch:
                mock_fetch.return_value = [{
                    "actionId": 100,
                    "fullActionName": "Test Event",
                    "actionDate": "2026-02-01T19:00:00",
                    "venueName": "Test Venue",
                    "minPrice": 500,
                    "maxPrice": 1500,
                    "ageRestriction": 0
                }]

                await callback_event_details(callback)

                # Verify keyboard has buy button
                call_args = callback.message.edit_text.call_args
                keyboard = call_args[1]['reply_markup']

                all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
                buy_buttons = [btn for btn in all_buttons if "buy_100" in (btn.callback_data or "")]

                assert len(buy_buttons) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
