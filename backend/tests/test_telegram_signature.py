"""
Tests for Telegram initData signature verification.

This test verifies that:
1. Valid initData with correct signature is accepted
2. Tampered initData with invalid signature is rejected
3. Missing or empty data is properly handled
"""

import hashlib
import hmac
import json
from urllib.parse import quote

import pytest


# Mock the settings to test with a known bot token
class MockSettings:
    TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789"


def create_test_init_data(bot_token: str, user_data: dict, tamper: bool = False) -> str:
    """
    Create a test initData string with valid signature (or tampered).

    This follows Telegram's WebApp initData signing algorithm:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    import time

    # Prepare data
    user_json = json.dumps(user_data, separators=(',', ':'))
    auth_date = str(int(time.time()))

    # Build data pairs (excluding hash)
    data_pairs = [
        f"auth_date={auth_date}",
        f"user={user_json}",
    ]
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)

    # Create secret key using HMAC-SHA256 of bot token with "WebAppData" as key
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

    if tamper:
        # Tamper with the hash
        calculated_hash = "tampered_" + calculated_hash[:50]

    # Build the query string
    init_data = f"auth_date={auth_date}&user={quote(user_json)}&hash={calculated_hash}"

    return init_data


def test_verify_valid_signature(monkeypatch):
    """Test that valid initData with correct signature is accepted."""
    # Patch the settings
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    # Create valid initData
    user_data = {
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en"
    }
    init_data = create_test_init_data(MockSettings.TELEGRAM_BOT_TOKEN, user_data, tamper=False)

    # Verify
    is_valid, data, error = security.verify_telegram_init_data(init_data)

    assert is_valid is True, f"Expected valid signature, got error: {error}"
    assert data is not None
    assert data.user.id == 123456789
    assert data.user.first_name == "Test"
    assert data.user.username == "testuser"


def test_reject_tampered_signature(monkeypatch):
    """Test that tampered initData with invalid signature is rejected."""
    # Patch the settings
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    # Create tampered initData
    user_data = {
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
    }
    init_data = create_test_init_data(MockSettings.TELEGRAM_BOT_TOKEN, user_data, tamper=True)

    # Verify
    is_valid, data, error = security.verify_telegram_init_data(init_data)

    assert is_valid is False, "Expected rejection of tampered signature"
    assert data is None
    assert "Invalid signature" in error


def test_reject_modified_user_data(monkeypatch):
    """Test that modifying user data after signing is rejected."""
    # Patch the settings
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    # Create valid initData
    user_data = {
        "id": 123456789,
        "first_name": "Test",
    }
    init_data = create_test_init_data(MockSettings.TELEGRAM_BOT_TOKEN, user_data, tamper=False)

    # Modify the user data after signing (change ID)
    modified_user = json.dumps({"id": 987654321, "first_name": "Hacker"}, separators=(',', ':'))
    parts = init_data.split('&')
    new_parts = []
    for part in parts:
        if part.startswith('user='):
            new_parts.append(f"user={quote(modified_user)}")
        else:
            new_parts.append(part)
    modified_init_data = '&'.join(new_parts)

    # Verify - should fail because data was modified after signing
    is_valid, data, error = security.verify_telegram_init_data(modified_init_data)

    assert is_valid is False, "Expected rejection of modified user data"
    assert "Invalid signature" in error


def test_reject_empty_init_data(monkeypatch):
    """Test that empty initData is rejected."""
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    is_valid, data, error = security.verify_telegram_init_data("")

    assert is_valid is False
    assert "empty" in error.lower()


def test_reject_missing_hash(monkeypatch):
    """Test that initData without hash is rejected."""
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    user_json = quote(json.dumps({"id": 123, "first_name": "Test"}))
    init_data = f"auth_date=1704067200&user={user_json}"

    is_valid, data, error = security.verify_telegram_init_data(init_data)

    assert is_valid is False
    assert "hash" in error.lower()


def test_reject_missing_user(monkeypatch):
    """Test that initData without user data is rejected."""
    from app.core import security
    monkeypatch.setattr(security, 'settings', MockSettings())

    init_data = "auth_date=1704067200&hash=somehash"

    is_valid, data, error = security.verify_telegram_init_data(init_data)

    assert is_valid is False
    assert "user" in error.lower()


def test_reject_no_bot_token_configured(monkeypatch):
    """Test that verification fails when bot token is not configured."""
    from app.core import security

    class NoTokenSettings:
        TELEGRAM_BOT_TOKEN = ""

    monkeypatch.setattr(security, 'settings', NoTokenSettings())

    init_data = "user=%7B%22id%22%3A123%7D&auth_date=1704067200&hash=somehash"

    is_valid, data, error = security.verify_telegram_init_data(init_data)

    assert is_valid is False
    assert "not configured" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
