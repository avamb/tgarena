"""
Rate Limiting Configuration

Simple in-memory rate limiter for login attempts.
Uses a dictionary to track attempts per IP address.
No external dependencies required.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status


# Configuration
LOGIN_MAX_ATTEMPTS = 5  # Maximum login attempts
LOGIN_WINDOW_SECONDS = 60  # Time window in seconds
LOGIN_BLOCK_SECONDS = 60  # Block duration after exceeding limit


class RateLimiter:
    """Simple in-memory rate limiter for login attempts."""

    def __init__(self):
        # Store: {ip: [timestamp1, timestamp2, ...]}
        self._attempts: Dict[str, List[float]] = defaultdict(list)
        # Store: {ip: block_until_timestamp}
        self._blocked: Dict[str, float] = {}

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxy headers."""
        # Check for X-Forwarded-For header (common in proxy setups)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client address
        if request.client:
            return request.client.host
        return "unknown"

    def _clean_old_attempts(self, ip: str, current_time: float) -> None:
        """Remove attempts older than the time window."""
        cutoff = current_time - LOGIN_WINDOW_SECONDS
        self._attempts[ip] = [ts for ts in self._attempts[ip] if ts > cutoff]

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked."""
        if ip in self._blocked:
            if time.time() < self._blocked[ip]:
                return True
            # Block expired, remove it
            del self._blocked[ip]
        return False

    def get_remaining_block_time(self, ip: str) -> int:
        """Get remaining seconds until IP is unblocked."""
        if ip in self._blocked:
            remaining = self._blocked[ip] - time.time()
            return max(0, int(remaining))
        return 0

    def check_rate_limit(self, request: Request) -> Optional[HTTPException]:
        """
        Check if the request should be rate limited.
        Returns HTTPException if rate limited, None otherwise.
        """
        ip = self._get_client_ip(request)

        # Check if blocked
        if self.is_blocked(ip):
            remaining = self.get_remaining_block_time(ip)
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Please try again in {remaining} seconds.",
                headers={"Retry-After": str(remaining)}
            )

        return None

    def record_attempt(self, request: Request) -> Optional[HTTPException]:
        """
        Record a login attempt and check if rate limit is exceeded.
        Call this AFTER a failed login attempt.
        Returns HTTPException if rate limit exceeded, None otherwise.
        """
        ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old attempts
        self._clean_old_attempts(ip, current_time)

        # Record this attempt
        self._attempts[ip].append(current_time)

        # Check if limit exceeded
        if len(self._attempts[ip]) >= LOGIN_MAX_ATTEMPTS:
            # Block the IP
            self._blocked[ip] = current_time + LOGIN_BLOCK_SECONDS
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Please try again in {LOGIN_BLOCK_SECONDS} seconds.",
                headers={"Retry-After": str(LOGIN_BLOCK_SECONDS)}
            )

        return None

    def clear_attempts(self, request: Request) -> None:
        """Clear attempts for an IP (call on successful login)."""
        ip = self._get_client_ip(request)
        if ip in self._attempts:
            del self._attempts[ip]
        if ip in self._blocked:
            del self._blocked[ip]


# Global rate limiter instance
login_rate_limiter = RateLimiter()
