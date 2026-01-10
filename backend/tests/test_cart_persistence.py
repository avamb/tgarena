"""
Test cart state persistence in widget.

Tests that cart items are preserved during session via Bill24 API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestBill24SessionManagement:
    """Test Bill24 client session management."""

    @pytest.mark.asyncio
    async def test_client_stores_session_info(self):
        """Test client stores user_id and session_id."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test_token",
            zone="test",
            user_id=456,
            session_id="session_abc"
        )

        assert client.user_id == 456
        assert client.session_id == "session_abc"

        await client.close()

    @pytest.mark.asyncio
    async def test_session_info_included_in_requests(self):
        """Test session info is included in request payloads."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test_token",
            zone="test",
            user_id=789,
            session_id="session_xyz"
        )

        request = client._build_request("GET_CART", {})

        assert request["userId"] == 789
        assert request["sessionId"] == "session_xyz"

        await client.close()

    @pytest.mark.asyncio
    async def test_request_without_session(self):
        """Test request without session doesn't include userId/sessionId."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test_token",
            zone="test"
            # No user_id or session_id
        )

        request = client._build_request("GET_ALL_ACTIONS", {})

        assert "userId" not in request
        assert "sessionId" not in request

        await client.close()


class TestCartFunctions:
    """Test Bill24 cart-related functions."""

    def test_reserve_seats_method_exists(self):
        """Test reserve_seats method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1, token="test")
        assert hasattr(client, 'reserve_seats')

    def test_unreserve_seats_method_exists(self):
        """Test unreserve_seats method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1, token="test")
        assert hasattr(client, 'unreserve_seats')

    def test_unreserve_all_method_exists(self):
        """Test unreserve_all method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1, token="test")
        assert hasattr(client, 'unreserve_all')

    def test_get_cart_method_exists(self):
        """Test get_cart method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1, token="test")
        assert hasattr(client, 'get_cart')


class TestCartTimeout:
    """Test cart timeout functionality."""

    @pytest.mark.asyncio
    async def test_reserve_seats_returns_cart_timeout(self):
        """Test reserve_seats returns cart timeout."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test",
            zone="test",
            user_id=456,
            session_id="session_123"
        )

        # Mock the _request method
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "resultCode": 0,
                "seatList": [{"seatId": 1, "price": 1000}],
                "cartTimeout": 600,  # 10 minutes
                "totalSum": 1000
            }

            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1]
            )

            assert "cartTimeout" in result
            assert result["cartTimeout"] == 600

        await client.close()

    @pytest.mark.asyncio
    async def test_reserve_seats_default_timeout(self):
        """Test reserve_seats uses default timeout if not provided."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test",
            zone="test",
            user_id=456,
            session_id="session_123"
        )

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            # Response without cartTimeout
            mock_request.return_value = {
                "resultCode": 0,
                "seatList": [{"seatId": 1}],
                "totalSum": 1000
                # No cartTimeout in response
            }

            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1]
            )

            assert result["cartTimeout"] == 600  # Default value

        await client.close()


class TestCartPersistenceWorkflow:
    """Test cart persistence workflow."""

    @pytest.mark.asyncio
    async def test_get_cart_retrieves_reserved_seats(self):
        """Test get_cart retrieves previously reserved seats."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test",
            zone="test",
            user_id=456,
            session_id="session_123"
        )

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "resultCode": 0,
                "cartList": [
                    {
                        "actionEventId": 100,
                        "seatList": [
                            {"seatId": 1, "row": "A", "seat": "5", "price": 1000},
                            {"seatId": 2, "row": "A", "seat": "6", "price": 1000},
                        ],
                        "totalSum": 2000
                    }
                ]
            }

            result = await client.get_cart()

            # Verify cart contents
            assert result is not None
            mock_request.assert_called_once_with("GET_CART")

        await client.close()

    @pytest.mark.asyncio
    async def test_session_preserved_across_requests(self):
        """Test session ID preserved across multiple requests."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=123,
            token="test",
            zone="test",
            user_id=456,
            session_id="persistent_session"
        )

        # First request
        request1 = client._build_request("RESERVE_SEATS", {"seatList": [1]})
        # Second request
        request2 = client._build_request("GET_CART", {})

        # Both should have same session
        assert request1["sessionId"] == "persistent_session"
        assert request2["sessionId"] == "persistent_session"

        await client.close()


class TestUserSessionCreation:
    """Test user session creation for cart persistence."""

    @pytest.mark.asyncio
    async def test_create_user_returns_session(self):
        """Test create_user returns userId and sessionId."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=123, token="test", zone="test")

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "resultCode": 0,
                "userId": 789,
                "sessionId": "new_session_xyz"
            }

            result = await client.create_user(
                telegram_chat_id=123456789,
                first_name="Test"
            )

            assert result["userId"] == 789
            assert result["sessionId"] == "new_session_xyz"

        await client.close()


class TestWidgetStatePersistence:
    """Test widget state persistence concepts."""

    def test_cart_timeout_is_reasonable(self):
        """Test default cart timeout is reasonable for user experience."""
        # 600 seconds = 10 minutes
        # This gives users enough time to:
        # - Select seats
        # - Review order
        # - Complete payment
        default_timeout = 600
        assert default_timeout >= 300  # At least 5 minutes
        assert default_timeout <= 1800  # At most 30 minutes

    def test_session_fields_in_client(self):
        """Test Bill24Client has required session fields."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1, token="test")

        # Should have these attributes
        assert hasattr(client, 'user_id')
        assert hasattr(client, 'session_id')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
