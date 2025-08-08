"""
Unit tests for circuit breaker implementation.
"""

import asyncio
import time

import pytest

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
    get_circuit_breaker_manager,
)


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    @pytest.fixture
    def config(self):
        """Create test circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            success_threshold=2,
            timeout=0.5,
            expected_exception=Exception,
        )

    @pytest.fixture
    def circuit_breaker(self, config):
        """Create circuit breaker for testing."""
        return CircuitBreaker("test_service", config)

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self, circuit_breaker):
        """Test successful operation through circuit breaker."""

        async def successful_operation():
            return "success"

        # Should start in CLOSED state
        assert circuit_breaker.state == CircuitState.CLOSED

        # Call should succeed
        result = await circuit_breaker.call(successful_operation)
        assert result == "success"
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_count(self, circuit_breaker):
        """Test failure counting and circuit opening."""

        async def failing_operation():
            raise Exception("Service unavailable")

        # Perform multiple failing operations
        for i in range(2):
            with pytest.raises(CircuitBreakerError):
                await circuit_breaker.call(failing_operation)

            # Should still be closed
            assert circuit_breaker.state == CircuitState.CLOSED
            assert circuit_breaker.failure_count == i + 1

        # Third failure should open circuit
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_operation)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self, circuit_breaker):
        """Test circuit breaker in OPEN state fails fast."""

        async def any_operation():
            return "should not be called"

        # Force circuit to OPEN state
        circuit_breaker._open_circuit()

        # Any call should fail fast without executing the function
        with pytest.raises(CircuitBreakerError) as exc_info:
            await circuit_breaker.call(any_operation)

        assert "is OPEN - failing fast" in str(exc_info.value)
        assert exc_info.value.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self, circuit_breaker):
        """Test circuit breaker recovery through HALF_OPEN state."""

        async def successful_operation():
            return "recovered"

        # Force circuit to OPEN state
        circuit_breaker._open_circuit()
        circuit_breaker.last_failure_time = time.time() - 2  # Past recovery timeout

        # First call should move to HALF_OPEN and succeed
        result = await circuit_breaker.call(successful_operation)
        assert result == "recovered"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        assert circuit_breaker.success_count == 1

        # Second successful call should close the circuit
        result = await circuit_breaker.call(successful_operation)
        assert result == "recovered"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout(self, circuit_breaker):
        """Test circuit breaker timeout functionality."""

        async def slow_operation():
            await asyncio.sleep(1)  # Longer than timeout
            return "too slow"

        # Should timeout and trigger circuit breaker
        with pytest.raises(CircuitBreakerError) as exc_info:
            await circuit_breaker.call(slow_operation)

        assert "timed out" in str(exc_info.value)
        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_sync_function(self, circuit_breaker):
        """Test circuit breaker with synchronous functions."""

        def sync_function():
            return "sync_result"

        result = await circuit_breaker.call(sync_function)
        assert result == "sync_result"

    def test_circuit_breaker_metrics(self, circuit_breaker):
        """Test circuit breaker metrics collection."""
        metrics = circuit_breaker.get_metrics()

        expected_keys = [
            "name",
            "state",
            "failure_count",
            "success_count",
            "last_failure_time",
            "last_success_time",
            "config",
        ]

        for key in expected_keys:
            assert key in metrics

        assert metrics["name"] == "test_service"
        assert metrics["state"] == CircuitState.CLOSED.value

    def test_circuit_breaker_reset(self, circuit_breaker):
        """Test manual circuit breaker reset."""
        # Force some state
        circuit_breaker._open_circuit()
        circuit_breaker.failure_count = 5

        # Reset should restore to initial state
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager functionality."""

    def test_create_circuit_breaker(self):
        """Test creating circuit breakers."""
        manager = CircuitBreakerManager()

        # Create new circuit breaker
        breaker1 = manager.create_circuit_breaker("service1")
        assert breaker1.name == "service1"

        # Getting same name should return existing instance
        breaker2 = manager.create_circuit_breaker("service1")
        assert breaker1 is breaker2

        # Different name should create new instance
        breaker3 = manager.create_circuit_breaker("service2")
        assert breaker3 is not breaker1

    def test_get_circuit_breaker(self):
        """Test getting existing circuit breakers."""
        manager = CircuitBreakerManager()

        # Non-existent should return None
        assert manager.get_circuit_breaker("nonexistent") is None

        # Create and then get
        created = manager.create_circuit_breaker("test")
        retrieved = manager.get_circuit_breaker("test")
        assert created is retrieved

    def test_get_all_metrics(self):
        """Test getting metrics for all circuit breakers."""
        manager = CircuitBreakerManager()

        # Empty manager
        assert manager.get_all_metrics() == {}

        # Add some circuit breakers
        manager.create_circuit_breaker("service1")
        manager.create_circuit_breaker("service2")

        metrics = manager.get_all_metrics()
        assert len(metrics) == 2
        assert "service1" in metrics
        assert "service2" in metrics

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        manager = CircuitBreakerManager()

        # Create and modify circuit breakers
        breaker1 = manager.create_circuit_breaker("service1")
        breaker2 = manager.create_circuit_breaker("service2")

        breaker1._open_circuit()
        breaker2._open_circuit()

        # Reset all
        manager.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED

    def test_get_unhealthy_services(self):
        """Test getting unhealthy services."""
        manager = CircuitBreakerManager()

        # All healthy initially
        assert manager.get_unhealthy_services() == {}

        # Create circuit breakers in different states
        healthy = manager.create_circuit_breaker("healthy")
        degraded = manager.create_circuit_breaker("degraded")
        failed = manager.create_circuit_breaker("failed")

        degraded._move_to_half_open()
        failed._open_circuit()

        unhealthy = manager.get_unhealthy_services()

        assert "healthy" not in unhealthy
        assert "degraded" in unhealthy
        assert "failed" in unhealthy
        assert "HALF_OPEN" in unhealthy["degraded"]
        assert "OPEN" in unhealthy["failed"]


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        from src.services.circuit_breaker import circuit_breaker

        call_count = 0

        @circuit_breaker("decorated_service", CircuitBreakerConfig(failure_threshold=2))
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Failing")
            return "success"

        # First two calls should fail
        with pytest.raises(Exception):
            await test_function()

        with pytest.raises(Exception):
            await test_function()

        # Circuit should be open now, third call should fail fast
        with pytest.raises(Exception):
            await test_function()

        # Function should not have been called the third time
        assert call_count == 2


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with other components."""

    def test_singleton_manager(self):
        """Test singleton circuit breaker manager."""
        manager1 = get_circuit_breaker_manager()
        manager2 = get_circuit_breaker_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_real_world_scenario(self):
        """Test realistic failure and recovery scenario."""
        manager = CircuitBreakerManager()
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.1, success_threshold=1
        )

        breaker = manager.create_circuit_breaker("external_api", config)

        failure_count = 0

        async def unreliable_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Only first 2 calls fail
                raise Exception("Service down")
            return "service recovered"

        # Fail enough times to open circuit
        for _ in range(2):
            with pytest.raises(CircuitBreakerError):
                await breaker.call(unreliable_service)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Service should have recovered, circuit should close
        result = await breaker.call(unreliable_service)
        assert result == "service recovered"
        assert breaker.state == CircuitState.CLOSED
