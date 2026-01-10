"""
Test Telegram WebApp initData validation.

Tests the verify_telegram_init_data function in security module.
"""

import pytest
import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import urlencode, quote
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.security import verify_telegram_init_data, TelegramInitData


class TestTelegramInitDataValidation:
    """Test Telegram initData verification."""

    def create_valid_init_data(self, bot_token: str, user_id: int = 123456789, username: str = "testuser") -> str:
        """
        Create a valid initData string for testing.

        This creates a properly signed initData that should pass verification.
        """
        user_data = {
            "id": user_id,
            "first_name": "Test",
            "last_name": "User",
            "username": username,
            "language_code": "en"
        }

        auth_date = int(datetime.utcnow().timestamp())

        # Build data pairs
        data_pairs = {
            "user": json.dumps(user_data),
            "auth_date": str(auth_date),
            "query_id": "test_query_id",
        }

        # Build data-check-string
        sorted_pairs = sorted(data_pairs.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

        # Create secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Build query string
        data_pairs["hash"] = calculated_hash
        return urlencode(data_pairs)

    def test_valid_init_data_verification(self, monkeypatch):
        """Test that valid initData passes verification."""
        # Set up a known bot token
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        # Mock the settings
        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # Create valid initData
        init_data = self.create_valid_init_data(test_token)

        # Verify
        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is True
        assert data is not None
        assert data.user.id == 123456789
        assert data.user.username == "testuser"
        assert data.user.first_name == "Test"
        assert error is None

    def test_invalid_signature_rejected(self, monkeypatch):
        """Test that invalid signature is rejected."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # Create initData with wrong hash
        user_data = json.dumps({"id": 123, "first_name": "Test"})
        init_data = f"user={quote(user_data)}&auth_date=1234567890&hash=invalidhash123"

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is False
        assert data is None
        assert "Invalid signature" in error

    def test_empty_init_data_rejected(self, monkeypatch):
        """Test that empty initData is rejected."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        is_valid, data, error = verify_telegram_init_data("")

        assert is_valid is False
        assert data is None
        assert "empty" in error.lower()

    def test_missing_hash_rejected(self, monkeypatch):
        """Test that initData without hash is rejected."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # initData without hash
        user_data = json.dumps({"id": 123, "first_name": "Test"})
        init_data = f"user={quote(user_data)}&auth_date=1234567890"

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is False
        assert data is None
        assert "hash" in error.lower()

    def test_missing_user_data_rejected(self, monkeypatch):
        """Test that initData without user is rejected."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # Create valid hash but without user data
        data_check_string = "auth_date=1234567890"
        secret_key = hmac.new(b"WebAppData", test_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        init_data = f"auth_date=1234567890&hash={calculated_hash}"

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is False
        assert data is None
        assert "user" in error.lower()

    def test_missing_bot_token_rejected(self, monkeypatch):
        """Test that missing bot token causes rejection."""
        class MockSettings:
            TELEGRAM_BOT_TOKEN = None

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        is_valid, data, error = verify_telegram_init_data("some_init_data")

        assert is_valid is False
        assert data is None
        assert "not configured" in error.lower()

    def test_invalid_json_in_user_rejected(self, monkeypatch):
        """Test that invalid JSON in user field is rejected."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # Create initData with invalid JSON in user
        invalid_json = "not{valid}json"
        data_check_string = f"auth_date=1234567890\nuser={invalid_json}"
        secret_key = hmac.new(b"WebAppData", test_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        init_data = f"auth_date=1234567890&user={invalid_json}&hash={calculated_hash}"

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is False
        assert data is None
        assert "json" in error.lower()

    def test_extracts_all_user_fields(self, monkeypatch):
        """Test that all user fields are properly extracted."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        # Create user with all fields
        user_data = {
            "id": 999888777,
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe",
            "language_code": "ru",
            "is_premium": True
        }

        auth_date = int(datetime.utcnow().timestamp())
        data_pairs = {
            "user": json.dumps(user_data),
            "auth_date": str(auth_date),
        }

        sorted_pairs = sorted(data_pairs.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

        secret_key = hmac.new(b"WebAppData", test_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        data_pairs["hash"] = calculated_hash
        init_data = urlencode(data_pairs)

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is True
        assert data.user.id == 999888777
        assert data.user.first_name == "John"
        assert data.user.last_name == "Doe"
        assert data.user.username == "johndoe"
        assert data.user.language_code == "ru"
        assert data.user.is_premium is True

    def test_extracts_optional_fields(self, monkeypatch):
        """Test that optional fields like start_param are extracted."""
        test_token = "123456789:ABCDEFghijklmnopqrstuvwxyz1234567890"

        class MockSettings:
            TELEGRAM_BOT_TOKEN = test_token

        monkeypatch.setattr("app.core.security.settings", MockSettings())

        user_data = {"id": 123, "first_name": "Test"}
        auth_date = int(datetime.utcnow().timestamp())

        data_pairs = {
            "user": json.dumps(user_data),
            "auth_date": str(auth_date),
            "start_param": "agent_12345",
            "chat_instance": "12345678901234567890",
        }

        sorted_pairs = sorted(data_pairs.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

        secret_key = hmac.new(b"WebAppData", test_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        data_pairs["hash"] = calculated_hash
        init_data = urlencode(data_pairs)

        is_valid, data, error = verify_telegram_init_data(init_data)

        assert is_valid is True
        assert data.start_param == "agent_12345"
        assert data.chat_instance == "12345678901234567890"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
