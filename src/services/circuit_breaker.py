"""
Circuit Breaker pattern implementation for external service resilience.

This module provides circuit breaker functionality to handle external service
failures gracefully and prevent cascading failures.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from src.utils.logger import logger

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures to open circuit
    recovery_timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close circuit in half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: Exception = Exception  # Exception type that triggers circuit


class CircuitBreakerError(Exception):
    """Circuit breaker specific exception."""

    def __init__(self, message: str, state: CircuitState):
        super().__init__(message)
        self.state = state


class CircuitBreaker:
    """Circuit breaker implementation for external services."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self._lock = asyncio.Lock()

        logger.info(f"Circuit breaker '{name}' initialized with config: {config}")

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Move to half-open if enough time has passed (before fail fast check)
            if self._should_attempt_reset():
                self._move_to_half_open()

            # Check if we should fail fast
            if self._should_fail_fast():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN - failing fast", self.state
                )

        # Execute the function
        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                self._execute_function(func, *args, **kwargs), timeout=self.config.timeout
            )
            await self._on_success()
            return result

        except asyncio.TimeoutError as e:
            await self._on_failure(f"Timeout after {self.config.timeout}s")
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' - operation timed out", self.state
            ) from e

        except Exception as e:
            # Check if this is an expected exception type
            if isinstance(e, self.config.expected_exception):
                await self._on_failure(str(e))
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' - service failure: {str(e)}", self.state
                ) from e
            else:
                # Unexpected exception, don't trigger circuit breaker
                raise

    async def _execute_function(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function, handling both sync and async functions."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # Run synchronous function in thread pool
                return await asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)
        except Exception as e:
            logger.debug(f"Circuit breaker '{self.name}' caught exception: {type(e).__name__}: {e}")
            raise

    def _should_fail_fast(self) -> bool:
        """Check if circuit should fail fast."""
        return self.state == CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset to half-open."""
        if self.state == CircuitState.OPEN:
            time_since_failure = time.time() - self.last_failure_time
            return time_since_failure >= self.config.recovery_timeout
        return False

    def _move_to_half_open(self) -> None:
        """Move circuit to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN state")

    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' success in HALF_OPEN: {self.success_count}/{self.config.success_threshold}"
                )

                if self.success_count >= self.config.success_threshold:
                    self._close_circuit()
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _on_failure(self, error_message: str) -> None:
        """Handle failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(
                f"Circuit breaker '{self.name}' failure #{self.failure_count}: {error_message}"
            )

            if self.state == CircuitState.CLOSED or self.state == CircuitState.HALF_OPEN:
                if self.failure_count >= self.config.failure_threshold:
                    self._open_circuit()

    def _close_circuit(self) -> None:
        """Close the circuit (normal operation)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' moved to CLOSED state")

    def _open_circuit(self) -> None:
        """Open the circuit (fail fast mode)."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.last_failure_time = time.time()
        logger.error(
            f"Circuit breaker '{self.name}' moved to OPEN state after {self.failure_count} failures"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED state")


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()

    def create_circuit_breaker(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Create or get existing circuit breaker."""
        if name not in self._circuit_breakers:
            config = config or self._default_config
            self._circuit_breakers[name] = CircuitBreaker(name, config)
            logger.debug(f"Created new circuit breaker: {name}")

        return self._circuit_breakers[name]

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get existing circuit breaker."""
        return self._circuit_breakers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {name: breaker.get_metrics() for name, breaker in self._circuit_breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._circuit_breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")

    def get_unhealthy_services(self) -> Dict[str, str]:
        """Get list of services with open circuits."""
        unhealthy = {}
        for name, breaker in self._circuit_breakers.items():
            if breaker.state == CircuitState.OPEN:
                unhealthy[name] = (
                    f"Circuit OPEN - last failure: {time.ctime(breaker.last_failure_time)}"
                )
            elif breaker.state == CircuitState.HALF_OPEN:
                unhealthy[name] = f"Circuit HALF_OPEN - testing recovery"
        return unhealthy


# Singleton instance for global access
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance."""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> Callable:
    """Decorator for applying circuit breaker to functions."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        manager = get_circuit_breaker_manager()
        breaker = manager.create_circuit_breaker(name, config)

        async def wrapper(*args, **kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)

        # For sync functions, create async wrapper
        if not asyncio.iscoroutinefunction(func):

            def sync_wrapper(*args, **kwargs) -> T:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(wrapper(*args, **kwargs))

            return sync_wrapper

        return wrapper

    return decorator


# Predefined configurations for common services
TRANSLATION_SERVICE_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    success_threshold=2,
    timeout=15.0,
    expected_exception=Exception,
)

OCR_SERVICE_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=20,
    success_threshold=3,
    timeout=10.0,
    expected_exception=Exception,
)

TTS_SERVICE_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=15,
    success_threshold=2,
    timeout=5.0,
    expected_exception=Exception,
)
