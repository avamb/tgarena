"""
Test Bill24 API CREATE_USER integration.

Tests for user creation on Bill24 when new Telegram user registers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestCreateUserMethodExists:
    """Test CREATE_USER method exists in Bill24 client."""

    def test_create_user_method_exists(self):
        """Test create_user method exists."""
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test"
        )

        assert hasattr(client, 'create_user')
        assert callable(client.create_user)

    @pytest.mark.asyncio
    async def test_create_user_is_async(self):
        """Test create_user is an async method."""
        import inspect
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test"
        )

        assert inspect.iscoroutinefunction(client.create_user)


class TestCreateUserAPICall:
    """Test CREATE_USER API call."""

    @pytest.mark.asyncio
    async def test_create_user_calls_api(self):
        """Test create_user makes API call."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "userId": 12345,
            "sessionId": "session_abc123"
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.create_user(telegram_chat_id=123456789)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "CREATE_USER"

    @pytest.mark.asyncio
    async def test_create_user_returns_user_id(self):
        """Test create_user returns userId."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "userId": 12345,
            "sessionId": "session_abc123"
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.create_user(telegram_chat_id=123456789)

            assert "userId" in result or "user_id" in str(result).lower()

    @pytest.mark.asyncio
    async def test_create_user_returns_session_id(self):
        """Test create_user returns sessionId."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "userId": 12345,
            "sessionId": "session_abc123"
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.create_user(telegram_chat_id=123456789)

            assert "sessionId" in result or "session" in str(result).lower()


class TestUserSessionModel:
    """Test UserSession model for storing Bill24 credentials."""

    def test_user_session_model_exists(self):
        """Test UserSession model exists."""
        from app.models import UserSession

        assert UserSession is not None

    def test_user_session_has_bil24_user_id(self):
        """Test UserSession has bil24_user_id field."""
        from app.models import UserSession

        assert hasattr(UserSession, 'bil24_user_id')

    def test_user_session_has_bil24_session_id(self):
        """Test UserSession has bil24_session_id field."""
        from app.models import UserSession

        assert hasattr(UserSession, 'bil24_session_id')

    def test_user_session_has_user_id(self):
        """Test UserSession has user_id field."""
        from app.models import UserSession

        assert hasattr(UserSession, 'user_id')

    def test_user_session_has_agent_id(self):
        """Test UserSession has agent_id field."""
        from app.models import UserSession

        assert hasattr(UserSession, 'agent_id')

    def test_user_session_has_is_active(self):
        """Test UserSession has is_active field."""
        from app.models import UserSession

        assert hasattr(UserSession, 'is_active')


class TestUserModel:
    """Test User model for Telegram users."""

    def test_user_model_exists(self):
        """Test User model exists."""
        from app.models import User

        assert User is not None

    def test_user_has_telegram_chat_id(self):
        """Test User has telegram_chat_id field."""
        from app.models import User

        assert hasattr(User, 'telegram_chat_id')

    def test_user_has_current_agent_id(self):
        """Test User has current_agent_id field."""
        from app.models import User

        assert hasattr(User, 'current_agent_id')


class TestCreateUserIntegration:
    """Test CREATE_USER integration with database."""

    def test_create_user_source_includes_chat_id(self):
        """Test create_user method uses telegram_chat_id."""
        import inspect
        from app.services.bill24 import Bill24Client

        source = inspect.getsource(Bill24Client.create_user)

        # Verify telegram_chat_id is used in the method
        assert "telegram_chat_id" in source or "chat_id" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
