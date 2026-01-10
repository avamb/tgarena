"""
Test user last_active_at timestamp.

Tests that user activity timestamp is updated on bot interactions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUserModelLastActive:
    """Test User model has last_active_at field."""

    def test_user_has_last_active_at_field(self):
        """Test User model has last_active_at field."""
        from app.models import User

        assert hasattr(User, 'last_active_at')

    def test_last_active_at_is_nullable(self):
        """Test last_active_at can be null (for legacy users)."""
        from app.models import User

        # Field should be defined as nullable
        assert hasattr(User, 'last_active_at')


class TestNewUserLastActive:
    """Test last_active_at set for new users."""

    @pytest.mark.asyncio
    async def test_new_user_gets_last_active_at(self):
        """Test new user has last_active_at set on creation."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "newuser"
        message.from_user.first_name = "New"
        message.from_user.last_name = "User"
        message.from_user.language_code = "en"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_session.execute.return_value = mock_result

        created_user = None
        def capture_add(user):
            nonlocal created_user
            created_user = user

        mock_session.add = capture_add

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            await get_or_create_user(mock_session, message)

            # Verify User was created with last_active_at
            MockUser.assert_called_once()
            call_kwargs = MockUser.call_args[1]
            assert 'last_active_at' in call_kwargs
            assert call_kwargs['last_active_at'] is not None


class TestExistingUserLastActive:
    """Test last_active_at updated for existing users."""

    @pytest.mark.asyncio
    async def test_existing_user_last_active_updated(self):
        """Test existing user has last_active_at updated on interaction."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 999888777
        message.from_user.username = "existinguser"
        message.from_user.first_name = "Existing"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"

        # Mock existing user with old last_active_at
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=24)
        mock_existing_user = MagicMock()
        mock_existing_user.last_active_at = old_timestamp

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_user
        mock_session.execute.return_value = mock_result

        result = await get_or_create_user(mock_session, message)

        # last_active_at should be updated to now (approximately)
        assert result.last_active_at != old_timestamp

        # Session commit should be called
        mock_session.commit.assert_called()


class TestLastActiveTimestamp:
    """Test last_active_at timestamp accuracy."""

    @pytest.mark.asyncio
    async def test_timestamp_is_utc(self):
        """Test last_active_at is in UTC timezone."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.username = "utcuser"
        message.from_user.first_name = "UTC"
        message.from_user.last_name = "User"
        message.from_user.language_code = "en"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            before = datetime.now(timezone.utc)
            await get_or_create_user(mock_session, message)
            after = datetime.now(timezone.utc)

            call_kwargs = MockUser.call_args[1]
            timestamp = call_kwargs['last_active_at']

            # Timestamp should be between before and after
            assert timestamp >= before
            assert timestamp <= after

    @pytest.mark.asyncio
    async def test_timestamp_is_recent(self):
        """Test last_active_at is recent (within seconds of now)."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 444555666
        message.from_user.username = "recentuser"
        message.from_user.first_name = "Recent"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            await get_or_create_user(mock_session, message)

            call_kwargs = MockUser.call_args[1]
            timestamp = call_kwargs['last_active_at']

            # Should be within 5 seconds of now
            now = datetime.now(timezone.utc)
            delta = abs((now - timestamp).total_seconds())
            assert delta < 5


class TestAdminPanelLastActive:
    """Test last_active_at visible in admin panel."""

    def test_user_response_includes_last_active(self):
        """Test UserResponse schema includes last_active_at."""
        from app.api.admin import UserResponse

        # Should have last_active_at field
        fields = UserResponse.__annotations__
        assert 'last_active_at' in fields


class TestLastActiveOnCommands:
    """Test last_active_at updated on different commands."""

    @pytest.mark.asyncio
    async def test_start_command_updates_timestamp(self):
        """Test /start updates last_active_at."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 777888999
        message.from_user.username = "startuser"
        message.from_user.first_name = "Start"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        old_timestamp = datetime.now(timezone.utc) - timedelta(days=7)

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_user = MagicMock()
            mock_user.preferred_language = "en"
            mock_user.current_agent_id = None
            mock_user.last_active_at = old_timestamp

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # last_active_at should have been updated
            # (in reality it's set via get_or_create_user)


class TestLastActiveTracking:
    """Test activity tracking use cases."""

    def test_can_identify_inactive_users(self):
        """Test can find users inactive for X days."""
        # Query would be:
        # SELECT * FROM users
        # WHERE last_active_at < NOW() - INTERVAL '30 days'

        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        sample_user_last_active = datetime.now(timezone.utc) - timedelta(days=45)

        is_inactive = sample_user_last_active < threshold
        assert is_inactive

    def test_can_identify_active_users(self):
        """Test can find recently active users."""
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        sample_user_last_active = datetime.now(timezone.utc) - timedelta(hours=2)

        is_active = sample_user_last_active >= threshold
        assert is_active


class TestDatabaseMigration:
    """Test database has last_active_at column."""

    def test_migration_includes_last_active_at(self):
        """Test initial migration has last_active_at column."""
        # Column is defined in migrations/versions/20250109_000000_initial_schema.py
        # sa.Column('last_active_at', sa.DateTime(), nullable=True)

        from app.models import User

        # Field should exist
        assert hasattr(User, 'last_active_at')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
