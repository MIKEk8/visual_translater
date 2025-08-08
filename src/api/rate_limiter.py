"""
Rate limiting module for Screen Translator API.

This module provides rate limiting functionality to prevent API abuse.
"""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class RateLimiter:
    """Simple in-memory rate limiter using sliding window algorithm."""

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, client_id: str) -> None:
        """Remove requests older than 1 minute."""
        current_time = time.time()
        minute_ago = current_time - 60

        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] if req_time > minute_ago
        ]

    def check_rate_limit(self, client_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if client has exceeded rate limit.

        Args:
            client_id: Unique client identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        self._clean_old_requests(client_id)

        if len(self.requests[client_id]) >= self.requests_per_minute:
            # Calculate when the oldest request will expire
            oldest_request = min(self.requests[client_id])
            retry_after = int(60 - (current_time - oldest_request)) + 1
            return False, retry_after

        # Add current request
        self.requests[client_id].append(current_time)
        return True, None

    def get_client_id(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        # Try to get API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_{api_key}"

        # Fall back to IP address
        client_host = request.client.host if request.client else "unknown"
        return f"ip_{client_host}"


# Global rate limiter instances
default_limiter = RateLimiter(requests_per_minute=60)
strict_limiter = RateLimiter(requests_per_minute=10)


async def rate_limit_dependency(request: Request, limiter: RateLimiter = default_limiter) -> None:
    """
    Fast API dependency for rate limiting.

    Args:
        request: Fast API request object
        limiter: RateLimiter instance to use

    Raises:
        HTTPException: If rate limit exceeded
    """
    client_id = limiter.get_client_id(request)
    is_allowed, retry_after = limiter.check_rate_limit(client_id)

    if not is_allowed:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


async def strict_rate_limit(request: Request) -> None:
    """Strict rate limit for sensitive endpoints."""
    await rate_limit_dependency(request, strict_limiter)


class RateLimitConfig:
    """Configuration for rate limiting."""

    def __init__(
        self,
        default_limit: int = 60,
        strict_limit: int = 10,
        window_minutes: int = 1,
    ):
        """
        Initialize rate limit configuration.

        Args:
            default_limit: Default requests per window
            strict_limit: Strict requests per window for sensitive endpoints
            window_minutes: Time window in minutes
        """
        self.default_limit = default_limit
        self.strict_limit = strict_limit
        self.window_minutes = window_minutes

    def create_limiter(self, is_strict: bool = False) -> RateLimiter:
        """Create a rate limiter with current configuration."""
        limit = self.strict_limit if is_strict else self.default_limit
        return RateLimiter(requests_per_minute=limit)
