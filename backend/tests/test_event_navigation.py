"""
Test event navigation with Next button.

Tests that users can navigate through events using pagination buttons.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import (
    callback_events_page,
    build_events_pagination_keyboard,
    get_page_events,
    EVENTS_PER_PAGE,
)
from app.bot.localization import get_text


class TestNextButtonNavigation:
    """Test Next button navigates to next events page."""

    def test_next_button_callback_data_format(self):
        """Test Next button has correct callback data."""
        events = [{"actionId": i, "fullActionName": f"Event {i}"} for i in range(10)]

        keyboard = build_events_pagination_keyboard(events[:5], page=1, total_pages=2, lang="ru")

        # Find next button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        next_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_2"]

        assert len(next_buttons) == 1

    def test_next_button_text_russian(self):
        """Test Next button has Russian text."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=3, lang="ru")

        # Find next button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        next_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_2"]

        assert len(next_buttons) == 1
        # Should have arrow or localized text
        assert "➡" in next_buttons[0].text or "вперед" in next_buttons[0].text.lower()

    def test_next_button_text_english(self):
        """Test Next button has English text."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=3, lang="en")

        # Find next button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        next_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_2"]

        assert len(next_buttons) == 1
        # Should have arrow or localized text
        assert "➡" in next_buttons[0].text or "next" in next_buttons[0].text.lower()

    @pytest.mark.asyncio
    async def test_next_button_shows_different_events(self):
        """Test clicking Next shows different event set."""
        from app.bot.handlers import callback_events_page

        # First page callback
        callback = AsyncMock()
        callback.data = "events_page_2"  # Going to page 2
        callback.from_user = MagicMock()
        callback.from_user.id = 123456789
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
        mock_agent.token = "test_token"
        mock_agent.zone = "test"
        mock_agent.is_active = True

        # Create 10 events (2 pages)
        all_events = [
            {"actionId": i, "fullActionName": f"Event {i}", "actionDate": "2026-02-01", "minPrice": 100*i}
            for i in range(10)
        ]

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
                mock_fetch.return_value = all_events

                await callback_events_page(callback)

                # Verify edit_text was called
                callback.message.edit_text.assert_called()
                call_args = callback.message.edit_text.call_args
                message_text = call_args[0][0]

                # Page 2 should have events 5-9 (Event 5, Event 6, etc.)
                assert "Event 5" in message_text or "Event 6" in message_text

                # Page 2 should NOT have events from page 1
                assert "Event 0" not in message_text
                assert "Event 1" not in message_text


class TestCyclingThroughEvents:
    """Test navigating through all events."""

    def test_navigation_through_three_pages(self):
        """Test can navigate from page 1 to 2 to 3."""
        # 15 events = 3 pages of 5
        events = [{"actionId": i, "fullActionName": f"Event {i}"} for i in range(15)]

        # Page 1 events
        page1_events, total = get_page_events(events, page=1)
        assert [e["actionId"] for e in page1_events] == [0, 1, 2, 3, 4]

        # Page 2 events
        page2_events, total = get_page_events(events, page=2)
        assert [e["actionId"] for e in page2_events] == [5, 6, 7, 8, 9]

        # Page 3 events
        page3_events, total = get_page_events(events, page=3)
        assert [e["actionId"] for e in page3_events] == [10, 11, 12, 13, 14]

    def test_next_button_sequence_page_1_to_2_to_3(self):
        """Test Next buttons lead to sequential pages."""
        events = [{"actionId": i, "fullActionName": f"Event {i}"} for i in range(15)]

        # Page 1 keyboard
        kb1 = build_events_pagination_keyboard(events[:5], page=1, total_pages=3, lang="ru")
        all_buttons_1 = [btn for row in kb1.inline_keyboard for btn in row]
        next_1 = [btn for btn in all_buttons_1 if btn.callback_data == "events_page_2"]
        assert len(next_1) == 1

        # Page 2 keyboard
        kb2 = build_events_pagination_keyboard(events[5:10], page=2, total_pages=3, lang="ru")
        all_buttons_2 = [btn for row in kb2.inline_keyboard for btn in row]
        next_2 = [btn for btn in all_buttons_2 if btn.callback_data == "events_page_3"]
        assert len(next_2) == 1

        # Page 3 keyboard (last page - no next)
        kb3 = build_events_pagination_keyboard(events[10:15], page=3, total_pages=3, lang="ru")
        all_buttons_3 = [btn for row in kb3.inline_keyboard for btn in row]
        next_3 = [btn for btn in all_buttons_3 if btn.callback_data == "events_page_4"]
        assert len(next_3) == 0  # No next on last page


class TestPreviousButtonNavigation:
    """Test Previous button navigates back."""

    def test_prev_button_callback_data_format(self):
        """Test Previous button has correct callback data."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=2, total_pages=3, lang="ru")

        # Find prev button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        prev_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_1"]

        assert len(prev_buttons) == 1

    def test_prev_button_text_russian(self):
        """Test Previous button has Russian text."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=2, total_pages=3, lang="ru")

        # Find prev button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        prev_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_1"]

        assert len(prev_buttons) == 1
        # Should have arrow or localized text
        assert "⬅" in prev_buttons[0].text or "назад" in prev_buttons[0].text.lower()

    def test_prev_button_not_on_first_page(self):
        """Test no Previous button on first page."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=3, lang="ru")

        # Find prev button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        prev_buttons = [btn for btn in all_buttons if btn.callback_data == "events_page_0"]

        assert len(prev_buttons) == 0  # No prev on page 1

    @pytest.mark.asyncio
    async def test_prev_button_shows_previous_events(self):
        """Test clicking Previous shows previous event set."""
        from app.bot.handlers import callback_events_page

        # Going back to page 1 from page 2
        callback = AsyncMock()
        callback.data = "events_page_1"
        callback.from_user = MagicMock()
        callback.from_user.id = 123456789
        callback.from_user.language_code = "en"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "en"

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 1271
        mock_agent.token = "test_token"
        mock_agent.zone = "test"
        mock_agent.is_active = True

        all_events = [
            {"actionId": i, "fullActionName": f"Event {i}", "actionDate": "2026-02-01", "minPrice": 100*i}
            for i in range(10)
        ]

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
                mock_fetch.return_value = all_events

                await callback_events_page(callback)

                # Verify edit_text was called
                callback.message.edit_text.assert_called()
                call_args = callback.message.edit_text.call_args
                message_text = call_args[0][0]

                # Page 1 should have events 0-4
                assert "Event 0" in message_text or "Event 1" in message_text

                # Should NOT have page 2 events
                assert "Event 5" not in message_text


class TestPageIndicator:
    """Test page indicator shows current position."""

    def test_page_indicator_shows_current_page(self):
        """Test page indicator shows X/Y format."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=2, total_pages=5, lang="ru")

        # Find page indicator button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        indicator_buttons = [btn for btn in all_buttons if "2" in btn.text and "5" in btn.text]

        assert len(indicator_buttons) >= 1


class TestEventPageHandler:
    """Test callback_events_page handler."""

    @pytest.mark.asyncio
    async def test_handler_parses_page_number(self):
        """Test handler correctly parses page number from callback."""
        from app.bot.handlers import callback_events_page

        callback = AsyncMock()
        callback.data = "events_page_3"  # Page 3
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

        all_events = [
            {"actionId": i, "fullActionName": f"Event {i}", "actionDate": "2026-02-01", "minPrice": 100}
            for i in range(15)  # 3 pages
        ]

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
                mock_fetch.return_value = all_events

                await callback_events_page(callback)

                # Should answer the callback
                callback.answer.assert_called_once()

                # Should edit text with page 3 events
                callback.message.edit_text.assert_called()
                call_args = callback.message.edit_text.call_args
                message_text = call_args[0][0]

                # Page 3 has events 10-14
                assert "Event 10" in message_text or "Event 11" in message_text

    @pytest.mark.asyncio
    async def test_handler_handles_no_user(self):
        """Test handler handles missing user."""
        from app.bot.handlers import callback_events_page

        callback = AsyncMock()
        callback.data = "events_page_1"
        callback.from_user = MagicMock()
        callback.from_user.id = 999999999
        callback.from_user.language_code = "en"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            result = MagicMock()
            result.scalar_one_or_none.return_value = None  # No user
            mock_session.execute.return_value = result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await callback_events_page(callback)

            # Should show error
            callback.message.edit_text.assert_called()
            call_args = callback.message.edit_text.call_args
            assert "error" in call_args[0][0].lower() or "agent" in call_args[0][0].lower()


class TestNavigationLocalization:
    """Test navigation button localization."""

    def test_next_button_localization_ru(self):
        """Test Next button text is localized in Russian."""
        text = get_text("btn_page_next", "ru")
        assert "➡" in text or "вперед" in text.lower()

    def test_next_button_localization_en(self):
        """Test Next button text is localized in English."""
        text = get_text("btn_page_next", "en")
        assert "➡" in text or "next" in text.lower()

    def test_prev_button_localization_ru(self):
        """Test Previous button text is localized in Russian."""
        text = get_text("btn_page_prev", "ru")
        assert "⬅" in text or "назад" in text.lower()

    def test_prev_button_localization_en(self):
        """Test Previous button text is localized in English."""
        text = get_text("btn_page_prev", "en")
        assert "⬅" in text or "previous" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
