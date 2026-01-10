"""
Test Bill24 API unavailability handling.

Tests that API errors are handled gracefully with user-friendly messages and retry logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client, Bill24Error, Bill24SessionError
from app.bot.localization import get_text


class TestBill24ErrorClasses:
    """Test Bill24 error classes."""

    def test_bill24_error_basic(self):
        """Test Bill24Error creation."""
        error = Bill24Error(code=500, message="Server Error")
        assert error.code == 500
        assert error.message == "Server Error"
        assert "500" in str(error)
        assert "Server Error" in str(error)

    def test_bill24_error_with_cause(self):
        """Test Bill24Error with cause."""
        error = Bill24Error(code=100, message="API Error", cause="Connection refused")
        assert error.code == 100
        assert error.cause == "Connection refused"

    def test_bill24_session_error(self):
        """Test Bill24SessionError is subclass of Bill24Error."""
        error = Bill24SessionError(code=1, message="Invalid session")
        assert isinstance(error, Bill24Error)
        assert error.code == 1


class TestBill24ClientRetry:
    """Test Bill24 client retry mechanism."""

    def test_client_has_retry_decorator(self):
        """Verify _request method has retry decorator."""
        import inspect
        from app.services.bill24 import Bill24Client

        # Check that _request method exists
        assert hasattr(Bill24Client, '_request')

        # The retry decorator adds certain attributes
        client = Bill24Client(fid=1, token="test")
        assert hasattr(client._request, 'retry')

    @pytest.mark.asyncio
    async def test_client_initializes_correctly(self):
        """Test client initialization with parameters."""
        client = Bill24Client(
            fid=12345,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session123"
        )

        assert client.fid == 12345
        assert client.token == "test_token"
        assert client.zone == "test"
        assert client.user_id == 100
        assert client.session_id == "session123"

        await client.close()

    @pytest.mark.asyncio
    async def test_client_build_request(self):
        """Test request payload building."""
        client = Bill24Client(
            fid=123,
            token="mytoken",
            zone="test"
        )

        request = client._build_request("GET_ALL_ACTIONS", {"extra": "param"})

        assert request["command"] == "GET_ALL_ACTIONS"
        assert request["fid"] == 123
        assert request["token"] == "mytoken"
        assert request["extra"] == "param"
        assert "locale" in request

        await client.close()

    @pytest.mark.asyncio
    async def test_client_handle_response_success(self):
        """Test successful response handling."""
        client = Bill24Client(fid=1, token="test")

        response = {"resultCode": 0, "data": "success"}
        result = client._handle_response(response)

        assert result == response

        await client.close()

    @pytest.mark.asyncio
    async def test_client_handle_response_error(self):
        """Test error response handling."""
        client = Bill24Client(fid=1, token="test")

        response = {"resultCode": 100, "description": "API Error"}

        with pytest.raises(Bill24Error) as exc_info:
            client._handle_response(response)

        assert exc_info.value.code == 100
        assert "API Error" in exc_info.value.message

        await client.close()

    @pytest.mark.asyncio
    async def test_client_handle_session_error(self):
        """Test session error handling."""
        client = Bill24Client(fid=1, token="test")

        response = {"resultCode": 1, "description": "Session expired"}

        with pytest.raises(Bill24SessionError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.code == 1

        await client.close()


class TestUserFriendlyErrors:
    """Test user-friendly error messages."""

    def test_error_fetching_events_ru(self):
        """Test Russian error message for API errors."""
        text = get_text("error_fetching_events", "ru")
        assert text != "error_fetching_events"
        assert len(text) > 10  # Should be a meaningful message

    def test_error_fetching_events_en(self):
        """Test English error message for API errors."""
        text = get_text("error_fetching_events", "en")
        assert text != "error_fetching_events"
        assert "fail" in text.lower() or "error" in text.lower() or "load" in text.lower()

    def test_error_general_ru(self):
        """Test Russian general error message."""
        text = get_text("error_general", "ru")
        assert text != "error_general"
        assert len(text) > 10

    def test_error_general_en(self):
        """Test English general error message."""
        text = get_text("error_general", "en")
        assert text != "error_general"
        assert "error" in text.lower() or "try" in text.lower()


class TestHandlerErrorHandling:
    """Test that handlers properly handle API errors."""

    @pytest.mark.asyncio
    async def test_view_events_handles_bill24_error(self):
        """Test that view_events callback handles Bill24Error."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "en"
        callback.from_user.id = 123456
        callback.message = AsyncMock()

        # Mock to simulate API error
        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.fetch_events_from_bill24') as mock_fetch:
                mock_fetch.side_effect = Bill24Error(code=500, message="API Down")

                async def mock_gen():
                    session = AsyncMock()
                    user_mock = MagicMock()
                    user_mock.preferred_language = "en"
                    user_mock.current_agent_id = 1

                    agent_mock = MagicMock()
                    agent_mock.fid = 123
                    agent_mock.token = "token"
                    agent_mock.zone = "test"

                    results = [user_mock, agent_mock]
                    call_count = [0]

                    def get_result():
                        result = MagicMock()
                        result.scalar_one_or_none.return_value = results[min(call_count[0], len(results)-1)]
                        call_count[0] += 1
                        return result

                    session.execute.side_effect = lambda *args, **kwargs: get_result()
                    yield session

                mock_session.return_value = mock_gen()

                await callback_view_events(callback)

                # Should have answered callback
                callback.answer.assert_called()

                # Should have sent loading message then edited with error
                # The handler sends a loading message and then edits it
                callback.message.answer.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
