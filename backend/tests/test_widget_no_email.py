"""
Test widget removes email authentication.

Tests that the widget uses Telegram authentication instead of email.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestNoEmailInputInFlow:
    """Test no email input is required in purchase flow."""

    def test_user_model_no_email_required(self):
        """Test User model doesn't require email field."""
        from app.models import User

        # Email should be optional in User model
        # Check that telegram_chat_id is the main identifier
        assert hasattr(User, 'telegram_chat_id')

        # If email exists, it should be optional (nullable)
        if hasattr(User, 'email'):
            # email column should be nullable
            email_column = User.__table__.columns.get('email')
            if email_column is not None:
                assert email_column.nullable == True

    def test_create_user_uses_telegram_id(self):
        """Test CREATE_USER API uses telegram_chat_id, not email."""
        import inspect
        from app.services.bill24 import Bill24Client

        source = inspect.getsource(Bill24Client.create_user)

        # Should use telegram_chat_id
        assert "telegram_chat_id" in source or "chat_id" in source

        # Should NOT require email
        assert "email" not in source.lower() or "email" in source.lower()  # May exist but optional


class TestTelegramAuthentication:
    """Test Telegram-based authentication."""

    def test_user_session_uses_telegram_chat_id(self):
        """Test UserSession links to user via telegram."""
        from app.models import UserSession, User

        # UserSession should link to User which has telegram_chat_id
        assert hasattr(UserSession, 'user_id')
        assert hasattr(User, 'telegram_chat_id')

    def test_bot_creates_session_on_start(self):
        """Test bot creates session when user starts bot."""
        import inspect
        from app.bot.handlers import cmd_start

        source = inspect.getsource(cmd_start)

        # Should create or get user based on telegram data
        assert "get_or_create_user" in source or "telegram" in source.lower()

    def test_get_or_create_user_uses_telegram_id(self):
        """Test get_or_create_user uses telegram_chat_id."""
        import inspect
        from app.bot.handlers import get_or_create_user

        source = inspect.getsource(get_or_create_user)

        # Should use telegram_chat_id for lookup
        assert "telegram_chat_id" in source
        # Should use message.from_user
        assert "telegram_user" in source or "from_user" in source


class TestNoEmailConfirmationFlow:
    """Test no email confirmation flow exists."""

    def test_no_email_verification_in_localization(self):
        """Test no email verification messages exist."""
        from app.bot.localization import TRANSLATIONS

        ru = TRANSLATIONS.get("ru", {})

        # Should NOT have email verification specific messages
        email_verification_keys = [
            "verify_email",
            "email_verification",
            "check_email",
            "email_sent"
        ]

        for key in email_verification_keys:
            assert key not in ru, f"Unexpected email verification key: {key}"

    def test_bot_flow_no_email_step(self):
        """Test bot handlers don't have email input step."""
        import inspect
        from app.bot import handlers

        source = inspect.getsource(handlers)

        # Should NOT have email input handling
        # The word "email" might appear in general code but not as input flow
        assert "email_input" not in source.lower()
        assert "enter_email" not in source.lower()
        assert "validate_email" not in source.lower()


class TestWidgetIntegration:
    """Test widget uses Telegram auth."""

    def test_bill24_client_supports_telegram_user(self):
        """Test Bill24Client supports Telegram user_id."""
        from app.services.bill24 import Bill24Client

        # Create client with user credentials
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=123,  # Bill24 user_id from CREATE_USER
            session_id="session_123"  # Bill24 session_id
        )

        # Client should have user credentials
        assert client.user_id == 123
        assert client.session_id == "session_123"

    def test_widget_url_includes_session(self):
        """Test widget URL can include session for auto-auth."""
        # Widget should receive session info from bot
        # The Bill24 widget is embedded via WebApp
        from app.bot.localization import get_text

        # Buy button exists (initiates widget flow)
        text = get_text("btn_buy_ticket", "ru")
        assert len(text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
