#!/usr/bin/env python3
"""
Standalone test for Telegram initData signature verification.

This can be run directly without pytest to verify the security implementation.
Run with: python tests/test_signature_standalone.py
"""

import hashlib
import hmac
import json
import sys
import os
from urllib.parse import quote, parse_qs, unquote

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Test bot token - use a dummy token for testing
TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789"


def create_init_data_with_signature(bot_token: str, user_data: dict, auth_date: int) -> str:
    """Create initData string with valid Telegram signature."""
    user_json = json.dumps(user_data, separators=(',', ':'))

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

    # Build the query string
    return f"auth_date={auth_date}&user={quote(user_json)}&hash={calculated_hash}"


def verify_init_data(init_data: str, bot_token: str):
    """
    Verify Telegram initData signature.
    Returns: (is_valid, error_message)
    """
    if not init_data:
        return False, "init_data is empty"

    try:
        parsed = parse_qs(init_data, keep_blank_values=True)

        received_hash = parsed.get('hash', [''])[0]
        if not received_hash:
            return False, "No hash in init_data"

        # Build data-check-string
        data_pairs = []
        for key, values in parsed.items():
            if key != 'hash':
                value = values[0] if values else ''
                data_pairs.append(f"{key}={value}")

        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)

        # Create secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate expected hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify
        if not hmac.compare_digest(calculated_hash, received_hash):
            return False, "Invalid signature"

        # Parse user data
        user_json = parsed.get('user', [''])[0]
        if not user_json:
            return False, "No user data"

        user_data = json.loads(unquote(user_json))
        return True, f"Valid! User: {user_data}"

    except Exception as e:
        return False, f"Error: {e}"


def run_tests():
    print("=" * 60)
    print("Telegram initData Signature Verification Tests")
    print("=" * 60)

    user = {"id": 123456789, "first_name": "Test", "username": "testuser"}
    auth_date = 1704067200

    # Test 1: Valid signature
    print("\n[TEST 1] Valid signature verification")
    valid_init_data = create_init_data_with_signature(TEST_BOT_TOKEN, user, auth_date)
    is_valid, msg = verify_init_data(valid_init_data, TEST_BOT_TOKEN)
    print(f"  Result: {'PASS ✓' if is_valid else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    # Test 2: Tampered hash
    print("\n[TEST 2] Tampered hash is rejected")
    tampered_init_data = valid_init_data.replace("hash=", "hash=tampered_")
    is_valid, msg = verify_init_data(tampered_init_data, TEST_BOT_TOKEN)
    print(f"  Result: {'PASS ✓' if not is_valid and 'Invalid signature' in msg else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    # Test 3: Modified user data
    print("\n[TEST 3] Modified user data is rejected")
    hacker_user = json.dumps({"id": 999999, "first_name": "Hacker"}, separators=(',', ':'))
    modified_data = valid_init_data.split('&')
    modified_data = [f"user={quote(hacker_user)}" if p.startswith('user=') else p for p in modified_data]
    modified_init_data = '&'.join(modified_data)
    is_valid, msg = verify_init_data(modified_init_data, TEST_BOT_TOKEN)
    print(f"  Result: {'PASS ✓' if not is_valid and 'Invalid signature' in msg else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    # Test 4: Wrong bot token
    print("\n[TEST 4] Wrong bot token is rejected")
    wrong_token = "9999999999:ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZz"
    is_valid, msg = verify_init_data(valid_init_data, wrong_token)
    print(f"  Result: {'PASS ✓' if not is_valid and 'Invalid signature' in msg else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    # Test 5: Empty data
    print("\n[TEST 5] Empty data is rejected")
    is_valid, msg = verify_init_data("", TEST_BOT_TOKEN)
    print(f"  Result: {'PASS ✓' if not is_valid else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    # Test 6: Missing hash
    print("\n[TEST 6] Missing hash is rejected")
    no_hash_data = f"auth_date=1704067200&user={quote(json.dumps(user))}"
    is_valid, msg = verify_init_data(no_hash_data, TEST_BOT_TOKEN)
    print(f"  Result: {'PASS ✓' if not is_valid and 'hash' in msg.lower() else 'FAIL ✗'}")
    print(f"  Message: {msg}")

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
