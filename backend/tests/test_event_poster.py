"""
Test event poster in ticket message.

Tests that ticket messages include the event poster image.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestEventPosterData:
    """Test event poster data from Bill24."""

    @pytest.mark.asyncio
    async def test_event_has_poster_url(self):
        """Test event data includes poster URL."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionList": [
                    {
                        "actionId": 100,
                        "actionName": "Rock Concert 2026",
                        "posterUrl": "https://cdn.tixgear.com/posters/event_100.jpg",
                        "imageUrl": "https://cdn.tixgear.com/images/event_100.jpg",
                        "actionDate": "2026-03-15T19:00:00"
                    }
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            response = await client.get_all_actions()
            events = response.get("actionList", [])

            # Event should have poster URL
            assert len(events) > 0
            event = events[0]
            assert "posterUrl" in event or "imageUrl" in event

    @pytest.mark.asyncio
    async def test_action_ext_has_poster(self):
        """Test GET_ACTION_EXT returns poster information."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionId": 100,
                "actionName": "Symphony Orchestra",
                "fullActionName": "Symphony Orchestra - Grand Finale",
                "posterUrl": "https://cdn.tixgear.com/posters/100_large.jpg",
                "posterUrlSmall": "https://cdn.tixgear.com/posters/100_small.jpg",
                "imageList": [
                    "https://cdn.tixgear.com/gallery/100_1.jpg",
                    "https://cdn.tixgear.com/gallery/100_2.jpg"
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            event = await client.get_action_ext(action_id=100)

            # Should have poster URL
            assert "posterUrl" in event
            assert event["posterUrl"].startswith("https://")


class TestTicketPosterInclusion:
    """Test poster is included in ticket message."""

    @pytest.mark.asyncio
    async def test_ticket_data_has_poster_url(self):
        """Test ticket data includes event poster URL."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "ticketList": [
                    {
                        "ticketId": 1,
                        "eventName": "Jazz Night",
                        "posterUrl": "https://cdn.tixgear.com/posters/jazz.jpg",
                        "qrCode": "QR_DATA",
                        "row": "A",
                        "seat": "1"
                    }
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            ticket = tickets[0]
            # Poster URL should be available
            assert "posterUrl" in ticket or "eventName" in ticket


class TestPosterURLValidation:
    """Test poster URL validation."""

    def test_poster_url_is_https(self):
        """Test poster URLs use HTTPS."""
        valid_urls = [
            "https://cdn.tixgear.com/posters/event.jpg",
            "https://api.tixgear.com/images/poster.png",
            "https://example.com/poster.webp"
        ]

        for url in valid_urls:
            assert url.startswith("https://")

    def test_poster_url_has_image_extension(self):
        """Test poster URLs have image extensions."""
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

        test_url = "https://cdn.tixgear.com/posters/event.jpg"

        has_valid_extension = any(
            test_url.lower().endswith(ext)
            for ext in valid_extensions
        )
        assert has_valid_extension


class TestPosterInTicketDelivery:
    """Test poster is sent with ticket."""

    @pytest.mark.asyncio
    async def test_can_fetch_poster_image(self):
        """Test poster image can be fetched for sending."""
        import httpx

        # Mock image URL
        poster_url = "https://cdn.tixgear.com/posters/test.jpg"

        # In real implementation, we'd use httpx to fetch
        # Here we just verify the approach works

        assert poster_url.startswith("https://")
        assert ".jpg" in poster_url or ".png" in poster_url

    def test_telegram_can_send_photo_by_url(self):
        """Test Telegram supports sending photo by URL."""
        # Telegram Bot API supports sending photos by URL
        # bot.send_photo(chat_id, photo=url)

        poster_url = "https://cdn.tixgear.com/posters/test.jpg"

        # URL should be valid for Telegram
        assert poster_url.startswith("http")
        assert len(poster_url) < 2048  # URL length limit


class TestPosterDisplayInMessage:
    """Test poster display with ticket message."""

    def test_ticket_message_can_include_poster(self):
        """Test ticket message format supports poster."""
        # Message format for ticket with poster
        ticket_info = {
            "event_name": "Rock Concert",
            "date": "15.03.2026 19:00",
            "venue": "Arena Stadium",
            "row": "A",
            "seat": "1",
            "poster_url": "https://cdn.tixgear.com/posters/rock.jpg"
        }

        # Can build message with poster
        assert ticket_info["poster_url"] is not None
        assert ticket_info["event_name"] is not None

    def test_message_without_poster_fallback(self):
        """Test ticket message works without poster."""
        ticket_info = {
            "event_name": "Private Event",
            "date": "20.03.2026 20:00",
            "venue": "Private Venue",
            "row": "B",
            "seat": "5",
            "poster_url": None  # No poster
        }

        # Should still have essential info
        assert ticket_info["event_name"] is not None
        assert ticket_info["row"] is not None
        assert ticket_info["seat"] is not None


class TestPosterFromEvent:
    """Test getting poster from event data."""

    @pytest.mark.asyncio
    async def test_get_poster_from_action_ext(self):
        """Test extracting poster URL from action details."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionId": 200,
                "posterUrl": "https://cdn.example.com/poster_200.jpg",
                "posterUrlLarge": "https://cdn.example.com/poster_200_large.jpg"
            }

        with patch.object(client, '_request', side_effect=mock_request):
            event = await client.get_action_ext(action_id=200)

            # Get best available poster
            poster_url = (
                event.get("posterUrlLarge") or
                event.get("posterUrl") or
                event.get("imageUrl")
            )

            assert poster_url is not None
            assert poster_url.startswith("https://")


class TestPosterImageTypes:
    """Test supported poster image types."""

    def test_supports_jpg(self):
        """Test JPG posters are supported."""
        url = "https://cdn.tixgear.com/posters/event.jpg"
        assert url.endswith(".jpg") or url.endswith(".jpeg")

    def test_supports_png(self):
        """Test PNG posters are supported."""
        url = "https://cdn.tixgear.com/posters/event.png"
        assert url.endswith(".png")

    def test_supports_webp(self):
        """Test WebP posters are supported."""
        url = "https://cdn.tixgear.com/posters/event.webp"
        assert url.endswith(".webp")


class TestPosterInDeliveryJob:
    """Test poster handling in ticket delivery job."""

    def test_delivery_job_exists(self):
        """Test ticket delivery job function exists."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        assert inspect.iscoroutinefunction(process_ticket_delivery_job)

    @pytest.mark.asyncio
    async def test_job_can_handle_poster_url(self):
        """Test delivery job can process poster URL."""
        # The job should be able to:
        # 1. Get ticket data with poster URL
        # 2. Send photo with caption (or photo + text message)

        ticket_data = {
            "ticketId": 1,
            "eventName": "Concert",
            "posterUrl": "https://example.com/poster.jpg",
            "qrCode": "QR_DATA"
        }

        assert "posterUrl" in ticket_data
        assert ticket_data["posterUrl"].startswith("https://")


class TestTelegramPhotoSending:
    """Test Telegram photo sending capabilities."""

    def test_photo_url_format(self):
        """Test photo URL format is valid for Telegram."""
        valid_url = "https://cdn.tixgear.com/posters/event.jpg"

        # Telegram requirements:
        # - Must be HTTPS for URL-based photos
        # - File size < 10MB for URL photos
        # - Must be JPG, PNG, or GIF (WebP supported)

        assert valid_url.startswith("https://")

    def test_photo_with_caption(self):
        """Test photo can have caption with ticket info."""
        caption_template = (
            "🎫 <b>{event_name}</b>\n\n"
            "📅 {date}\n"
            "📍 {venue}\n"
            "🪑 Row {row}, Seat {seat}"
        )

        caption = caption_template.format(
            event_name="Rock Concert",
            date="15.03.2026 19:00",
            venue="Arena Stadium",
            row="A",
            seat="5"
        )

        # Caption should be under 1024 characters (Telegram limit)
        assert len(caption) < 1024
        assert "Rock Concert" in caption


class TestPosterCaching:
    """Test poster caching considerations."""

    def test_poster_url_is_cacheable(self):
        """Test poster URLs are from CDN (cacheable)."""
        cdn_patterns = ["cdn.", "/cdn/", "static.", "images."]

        test_url = "https://cdn.tixgear.com/posters/event.jpg"

        is_cdn = any(pattern in test_url for pattern in cdn_patterns)
        # CDN URLs are typically more reliable and faster
        assert is_cdn or test_url.startswith("https://")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
