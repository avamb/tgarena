"""
Security and Authentication utilities for TG-Ticket-Agent.

Provides JWT token creation/validation, password hashing, and Telegram initData verification.
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class AdminUser(BaseModel):
    """Admin user model for dependency injection."""
    id: int
    username: str
    role: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 24 hours
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.ADMIN_JWT_SECRET,
        algorithm="HS256"
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.ADMIN_JWT_SECRET,
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")

        if username is None:
            return None

        return TokenData(username=username, user_id=user_id, role=role)
    except JWTError:
        return None


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AdminUser:
    """
    Dependency to get the current authenticated admin user.

    Raises HTTPException 401 if token is invalid or missing.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = decode_access_token(token)

    if token_data is None:
        raise credentials_exception

    # In a real application, you would fetch the user from the database here
    # For now, we return the data from the token
    return AdminUser(
        id=token_data.user_id or 0,
        username=token_data.username or "",
        role=token_data.role or "super_admin"
    )


# Alias for convenience
get_current_user = get_current_admin_user


# =============================================================================
# Telegram WebApp InitData Verification
# =============================================================================


class TelegramUser(BaseModel):
    """Telegram user data extracted from initData."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None


class TelegramInitData(BaseModel):
    """Parsed and verified Telegram initData."""
    user: TelegramUser
    chat_instance: Optional[str] = None
    chat_type: Optional[str] = None
    auth_date: int
    hash: str
    query_id: Optional[str] = None
    start_param: Optional[str] = None


def verify_telegram_init_data(init_data: str) -> Tuple[bool, Optional[TelegramInitData], Optional[str]]:
    """
    Verify Telegram WebApp initData signature.

    Implements the verification algorithm described in:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        init_data: The raw initData string from Telegram WebApp

    Returns:
        Tuple of (is_valid, parsed_data, error_message)
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, None, "TELEGRAM_BOT_TOKEN not configured"

    if not init_data:
        return False, None, "init_data is empty"

    try:
        # Parse the query string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Extract hash and remove it from data for verification
        received_hash = parsed.get('hash', [''])[0]
        if not received_hash:
            return False, None, "No hash in init_data"

        # Build the data-check-string
        # Sort all key=value pairs alphabetically by key, excluding hash
        data_pairs = []
        for key, values in parsed.items():
            if key != 'hash':
                # Use the first value if multiple
                value = values[0] if values else ''
                data_pairs.append(f"{key}={value}")

        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)

        # Create secret key using HMAC-SHA256 of bot token with "WebAppData" as key
        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate expected hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify hash matches
        if not hmac.compare_digest(calculated_hash, received_hash):
            return False, None, "Invalid signature"

        # Parse user data
        user_json = parsed.get('user', [''])[0]
        if not user_json:
            return False, None, "No user data in init_data"

        user_data = json.loads(unquote(user_json))
        user = TelegramUser(**user_data)

        # Build TelegramInitData object
        auth_date = int(parsed.get('auth_date', ['0'])[0])

        telegram_data = TelegramInitData(
            user=user,
            chat_instance=parsed.get('chat_instance', [None])[0],
            chat_type=parsed.get('chat_type', [None])[0],
            auth_date=auth_date,
            hash=received_hash,
            query_id=parsed.get('query_id', [None])[0],
            start_param=parsed.get('start_param', [None])[0],
        )

        # Optional: Check if auth_date is not too old (e.g., within 24 hours)
        # current_time = int(datetime.utcnow().timestamp())
        # if current_time - auth_date > 86400:  # 24 hours
        #     return False, None, "init_data has expired"

        return True, telegram_data, None

    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON in user data: {e}"
    except Exception as e:
        return False, None, f"Error parsing init_data: {e}"


def require_valid_telegram_init_data(init_data: str) -> TelegramInitData:
    """
    Verify Telegram initData and raise HTTPException if invalid.

    Use this as a dependency or call directly in route handlers.

    Args:
        init_data: The raw initData string from Telegram WebApp

    Returns:
        Parsed TelegramInitData if valid

    Raises:
        HTTPException 401 if verification fails
    """
    is_valid, data, error = verify_telegram_init_data(init_data)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Telegram authentication: {error}"
        )

    return data
