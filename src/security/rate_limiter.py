"""
Rate limiting for API and resource protection.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple

from src.utils.logger import logger


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, identifier: str, limit: int, window_seconds: int, retry_after: float):
        self.identifier = identifier
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {identifier}: {limit} requests per {window_seconds}s"
        )


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_window: int = 100
    window_seconds: int = 60
    burst_limit: Optional[int] = None  # Allow bursts up to this limit
    burst_window_seconds: int = 10

    def __post_init__(self):
        """Set default burst limit if not specified."""
        if self.burst_limit is None:
            self.burst_limit = min(self.requests_per_window * 2, 1000)


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket. Returns True if successful."""
        with self.lock:
            now = time.time()

            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    def get_tokens_available(self) -> float:
        """Get current number of tokens available."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.capacity, self.tokens + elapsed * self.refill_rate)

    def time_until_available(self, tokens: int = 1) -> float:
        """Get time in seconds until requested tokens are available."""
        with self.lock:
            available = self.get_tokens_available()
            if available >= tokens:
                return 0.0

            tokens_needed = tokens - available
            return tokens_needed / self.refill_rate


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""

    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = Lock()

    def add_request(self, timestamp: Optional[float] = None) -> None:
        """Add a request timestamp."""
        if timestamp is None:
            timestamp = time.time()

        with self.lock:
            self.requests.append(timestamp)
            self._cleanup_old_requests(timestamp)

    def get_request_count(self, timestamp: Optional[float] = None) -> int:
        """Get number of requests in current window."""
        if timestamp is None:
            timestamp = time.time()

        with self.lock:
            self._cleanup_old_requests(timestamp)
            return len(self.requests)

    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside the current window."""
        cutoff_time = current_time - self.window_seconds
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()


class RateLimiter:
    """Advanced rate limiter with multiple algorithms and configurations."""

    def __init__(self):
        self.configs: Dict[str, RateLimitConfig] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self.request_counts: Dict[str, Dict[str, int]] = defaultdict(
            dict
        )  # identifier -> window -> count
        self.blocked_until: Dict[str, float] = {}  # identifier -> unblock_time
        self.lock = Lock()

        # Default configurations
        self._setup_default_configs()

        logger.info("Rate limiter initialized")

    def _setup_default_configs(self) -> None:
        """Setup default rate limit configurations."""
        self.configs.update(
            {
                # API endpoints
                "api_default": RateLimitConfig(requests_per_window=100, window_seconds=60),
                "api_translation": RateLimitConfig(requests_per_window=50, window_seconds=60),
                "api_ocr": RateLimitConfig(requests_per_window=30, window_seconds=60),
                # User actions
                "user_screenshot": RateLimitConfig(requests_per_window=20, window_seconds=60),
                "user_translation": RateLimitConfig(requests_per_window=100, window_seconds=60),
                "user_tts": RateLimitConfig(requests_per_window=50, window_seconds=60),
                # System operations
                "config_change": RateLimitConfig(requests_per_window=10, window_seconds=60),
                "file_export": RateLimitConfig(
                    requests_per_window=5, window_seconds=300
                ),  # 5 per 5 minutes
                # Security operations
                "login_attempt": RateLimitConfig(
                    requests_per_window=5, window_seconds=300
                ),  # 5 per 5 minutes
                "password_reset": RateLimitConfig(
                    requests_per_window=3, window_seconds=3600
                ),  # 3 per hour
            }
        )

    def add_config(self, identifier: str, config: RateLimitConfig) -> None:
        """Add or update rate limit configuration."""
        with self.lock:
            self.configs[identifier] = config

            # Initialize token bucket for this identifier
            refill_rate = config.requests_per_window / config.window_seconds
            self.token_buckets[identifier] = TokenBucket(config.requests_per_window, refill_rate)

            # Initialize sliding window counter
            self.sliding_windows[identifier] = SlidingWindowCounter(config.window_seconds)

            logger.info(
                f"Rate limit config added: {identifier} ({config.requests_per_window}/{config.window_seconds}s)"
            )

    def check_rate_limit(
        self, identifier: str, resource_id: str = "default"
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit.
        Returns (allowed, retry_after_seconds).
        """
        full_identifier = f"{identifier}:{resource_id}"

        with self.lock:
            # Check if currently blocked
            if full_identifier in self.blocked_until:
                unblock_time = self.blocked_until[full_identifier]
                if time.time() < unblock_time:
                    retry_after = unblock_time - time.time()
                    return False, retry_after
                else:
                    # Block period expired
                    del self.blocked_until[full_identifier]

            # Get configuration
            config = self.configs.get(identifier, self.configs["api_default"])

            # Use token bucket algorithm
            bucket = self.token_buckets.get(identifier)
            if not bucket:
                # Create bucket if not exists
                refill_rate = config.requests_per_window / config.window_seconds
                bucket = TokenBucket(config.requests_per_window, refill_rate)
                self.token_buckets[identifier] = bucket

            # Check token bucket
            if not bucket.consume(1):
                retry_after = bucket.time_until_available(1)

                # Log rate limit exceeded
                from src.security.audit import get_audit_logger

                audit_logger = get_audit_logger()
                audit_logger.log_rate_limit_exceeded(full_identifier, config.requests_per_window)

                return False, retry_after

            # Also check sliding window for burst protection
            window = self.sliding_windows.get(identifier)
            if not window:
                window = SlidingWindowCounter(config.burst_window_seconds)
                self.sliding_windows[identifier] = window

            window.add_request()
            current_count = window.get_request_count()

            if current_count > config.burst_limit:
                # Block for burst window duration
                self.blocked_until[full_identifier] = time.time() + config.burst_window_seconds
                retry_after = config.burst_window_seconds

                logger.warning(
                    f"Burst limit exceeded for {full_identifier}: {current_count}/{config.burst_limit}"
                )
                return False, retry_after

            return True, None

    def consume_rate_limit(
        self, identifier: str, resource_id: str = "default", _amount: int = 1
    ) -> None:
        """Consume rate limit tokens (call after successful operation)."""
        allowed, retry_after = self.check_rate_limit(identifier, resource_id)
        if not allowed:
            raise RateLimitExceeded(
                identifier=f"{identifier}:{resource_id}",
                limit=self.configs.get(identifier, self.configs["api_default"]).requests_per_window,
                window_seconds=self.configs.get(
                    identifier, self.configs["api_default"]
                ).window_seconds,
                retry_after=retry_after or 0,
            )

    def reset_rate_limit(self, identifier: str, resource_id: str = "default") -> None:
        """Reset rate limit for specific identifier."""
        full_identifier = f"{identifier}:{resource_id}"

        with self.lock:
            # Remove from blocked list
            if full_identifier in self.blocked_until:
                del self.blocked_until[full_identifier]

            # Reset token bucket
            if identifier in self.token_buckets:
                config = self.configs.get(identifier, self.configs["api_default"])
                self.token_buckets[identifier].tokens = float(config.requests_per_window)

            # Reset sliding window
            if identifier in self.sliding_windows:
                self.sliding_windows[identifier].requests.clear()

            logger.info(f"Rate limit reset for {full_identifier}")

    def get_rate_limit_status(
        self, identifier: str, resource_id: str = "default"
    ) -> Dict[str, any]:
        """Get current rate limit status."""
        full_identifier = f"{identifier}:{resource_id}"
        config = self.configs.get(identifier, self.configs["api_default"])

        with self.lock:
            # Check if blocked
            is_blocked = full_identifier in self.blocked_until
            retry_after = 0.0
            if is_blocked:
                retry_after = max(0, self.blocked_until[full_identifier] - time.time())

            # Get token bucket status
            bucket = self.token_buckets.get(identifier)
            tokens_available = (
                bucket.get_tokens_available() if bucket else config.requests_per_window
            )

            # Get sliding window status
            window = self.sliding_windows.get(identifier)
            current_requests = window.get_request_count() if window else 0

            return {
                "identifier": full_identifier,
                "config": {
                    "requests_per_window": config.requests_per_window,
                    "window_seconds": config.window_seconds,
                    "burst_limit": config.burst_limit,
                    "burst_window_seconds": config.burst_window_seconds,
                },
                "status": {
                    "is_blocked": is_blocked,
                    "retry_after_seconds": retry_after,
                    "tokens_available": tokens_available,
                    "current_requests_in_burst_window": current_requests,
                    "requests_remaining": max(0, config.requests_per_window - current_requests),
                },
            }

    def cleanup_expired_data(self) -> None:
        """Clean up expired rate limit data."""
        current_time = time.time()

        with self.lock:
            # Remove expired blocks
            expired_blocks = [
                identifier
                for identifier, unblock_time in self.blocked_until.items()
                if current_time >= unblock_time
            ]
            for identifier in expired_blocks:
                del self.blocked_until[identifier]

            # Clean up sliding windows
            for window in self.sliding_windows.values():
                window._cleanup_old_requests(current_time)

            if expired_blocks:
                logger.debug(f"Cleaned up {len(expired_blocks)} expired rate limit blocks")

    def get_statistics(self) -> Dict[str, any]:
        """Get rate limiter statistics."""
        with self.lock:
            return {
                "total_configs": len(self.configs),
                "active_token_buckets": len(self.token_buckets),
                "active_sliding_windows": len(self.sliding_windows),
                "currently_blocked": len(self.blocked_until),
                "configurations": {
                    name: {
                        "requests_per_window": config.requests_per_window,
                        "window_seconds": config.window_seconds,
                        "burst_limit": config.burst_limit,
                    }
                    for name, config in self.configs.items()
                },
            }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter()

    return _rate_limiter
