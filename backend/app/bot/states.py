"""
FSM States for the ticket purchase flow.

Tracks multi-step conversation: session selection -> seat selection -> cart -> payment.
"""

from aiogram.fsm.state import State, StatesGroup


class PurchaseStates(StatesGroup):
    """States for the ticket purchase flow."""

    # User is choosing a session (date/time) for the event
    selecting_session = State()

    # User is choosing seat category + quantity
    selecting_seats = State()

    # Reservation made, showing cart summary, waiting for "Pay" or "Cancel"
    cart_confirmation = State()

    # Payment in progress (user clicked pay, waiting for result)
    payment_pending = State()
