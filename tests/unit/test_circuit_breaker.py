"""
Tests for NetArchon Circuit Breaker Implementation
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.netarchon.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerError,
    CircuitBreakerManager, with_circuit_breaker, circuit_breaker_manager
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.success_threshold == 3
        assert config.timeout == 30
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=15
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30
        assert config.success_threshold == 2
        assert config.timeout == 15


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            success_threshold=2,
            timeout=5
        )
        self.cb = CircuitBreaker("test_circuit", self.config)
    
    def test_initial_state(self):
        """Test circuit breaker initial state."""
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0
        assert self.cb.success_count == 0
        assert self.cb.total_calls == 0
        assert self.cb.total_failures == 0
        assert self.cb.total_successes == 0
    
    def test_successful_call(self):
        """Test successful function call."""
        def success_func():
            return "success"
        
        result = self.cb.call(success_func)
        
        assert result == "success"
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.total_calls == 1
        assert self.cb.total_successes == 1
        assert self.cb.failure_count == 0
    
    def test_failed_call(self):
        """Test failed function call."""
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            self.cb.call(failing_func)
        
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.total_calls == 1
        assert self.cb.total_failures == 1
        assert self.cb.failure_count == 1
    
    def test_circuit_opens_after_threshold_failures(self):
        """Test circuit opens after reaching failure threshold."""
        def failing_func():
            raise ValueError("Test error")
        
        # Fail up to threshold
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                self.cb.call(failing_func)
        
        assert self.cb.state == CircuitState.OPEN
        assert self.cb.failure_count == self.config.failure_threshold
    
    def test_circuit_fails_fast_when_open(self):
        """Test circuit fails fast when open."""
        # Force circuit to open
        self.cb.force_open()
        
        def any_func():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerError, match="Circuit breaker 'test_circuit' is open"):
            self.cb.call(any_func)
        
        assert self.cb.total_calls == 1  # Call was counted but not executed
    
    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        # Force circuit to open
        self.cb.force_open()
        self.cb.last_failure_time = datetime.utcnow() - timedelta(seconds=2)  # Past timeout
        
        def success_func():
            return "success"
        
        # This should transition to half-open and succeed
        result = self.cb.call(success_func)
        
        assert result == "success"
        assert self.cb.state == CircuitState.HALF_OPEN
        assert self.cb.success_count == 1
    
    def test_circuit_closes_from_half_open_after_successes(self):
        """Test circuit closes from half-open after enough successes."""
        # Set to half-open state
        self.cb.state = CircuitState.HALF_OPEN
        
        def success_func():
            return "success"
        
        # Execute successful calls up to success threshold
        for i in range(self.config.success_threshold):
            result = self.cb.call(success_func)
            assert result == "success"
        
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0
        assert self.cb.success_count == 0  # Reset after closing
    
    def test_circuit_opens_from_half_open_on_failure(self):
        """Test circuit opens from half-open on any failure."""
        # Set to half-open state
        self.cb.state = CircuitState.HALF_OPEN
        
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            self.cb.call(failing_func)
        
        assert self.cb.state == CircuitState.OPEN
    
    def test_get_status(self):
        """Test get_status method."""
        # Execute some calls
        def success_func():
            return "success"
        
        def failing_func():
            raise ValueError("Test error")
        
        self.cb.call(success_func)
        try:
            self.cb.call(failing_func)
        except ValueError:
            pass
        
        status = self.cb.get_status()
        
        assert status["name"] == "test_circuit"
        assert status["state"] == CircuitState.CLOSED.value
        assert status["total_calls"] == 2
        assert status["total_successes"] == 1
        assert status["total_failures"] == 1
        assert status["failure_rate"] == 0.5
        assert "config" in status
    
    def test_reset(self):
        """Test reset functionality."""
        # Make some calls and force open
        def failing_func():
            raise ValueError("Test error")
        
        try:
            self.cb.call(failing_func)
        except ValueError:
            pass
        
        self.cb.force_open()
        
        # Reset
        self.cb.reset()
        
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0
        assert self.cb.success_count == 0
        assert self.cb.last_failure_time is None
        assert self.cb.last_success_time is None
    
    def test_force_open(self):
        """Test force_open functionality."""
        self.cb.force_open()
        assert self.cb.state == CircuitState.OPEN
    
    def test_force_closed(self):
        """Test force_closed functionality."""
        self.cb.force_open()
        self.cb.force_closed()
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0
        assert self.cb.success_count == 0


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CircuitBreakerManager()
    
    def test_get_circuit_breaker_creates_new(self):
        """Test getting a new circuit breaker creates it."""
        cb = self.manager.get_circuit_breaker("test_cb")
        
        assert cb.name == "test_cb"
        assert "test_cb" in self.manager.circuit_breakers
    
    def test_get_circuit_breaker_returns_existing(self):
        """Test getting existing circuit breaker returns same instance."""
        cb1 = self.manager.get_circuit_breaker("test_cb")
        cb2 = self.manager.get_circuit_breaker("test_cb")
        
        assert cb1 is cb2
    
    def test_get_circuit_breaker_with_config(self):
        """Test creating circuit breaker with custom config."""
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = self.manager.get_circuit_breaker("test_cb", config)
        
        assert cb.config.failure_threshold == 10
    
    def test_get_all_status(self):
        """Test getting status of all circuit breakers."""
        cb1 = self.manager.get_circuit_breaker("cb1")
        cb2 = self.manager.get_circuit_breaker("cb2")
        
        status = self.manager.get_all_status()
        
        assert "cb1" in status
        assert "cb2" in status
        assert status["cb1"]["name"] == "cb1"
        assert status["cb2"]["name"] == "cb2"
    
    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        cb1 = self.manager.get_circuit_breaker("cb1")
        cb2 = self.manager.get_circuit_breaker("cb2")
        
        # Force both to open
        cb1.force_open()
        cb2.force_open()
        
        # Reset all
        self.manager.reset_all()
        
        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        @with_circuit_breaker("decorator_test")
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
        
        # Check circuit breaker was created
        cb = circuit_breaker_manager.get_circuit_breaker("decorator_test")
        assert cb.total_successes == 1
    
    def test_decorator_failure(self):
        """Test decorator with failing function."""
        @with_circuit_breaker("decorator_test_fail")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_func()
        
        # Check circuit breaker recorded failure
        cb = circuit_breaker_manager.get_circuit_breaker("decorator_test_fail")
        assert cb.total_failures == 1
    
    def test_decorator_with_config(self):
        """Test decorator with custom configuration."""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        @with_circuit_breaker("decorator_config_test", config)
        def test_func():
            return "test"
        
        test_func()
        
        cb = circuit_breaker_manager.get_circuit_breaker("decorator_config_test")
        assert cb.config.failure_threshold == 2
    
    def test_decorator_circuit_opens(self):
        """Test decorator opens circuit after failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        @with_circuit_breaker("decorator_open_test", config)
        def failing_func():
            raise ValueError("Test error")
        
        # Fail enough times to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_func()
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerError):
            failing_func()


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""
    
    def test_realistic_failure_recovery_scenario(self):
        """Test realistic failure and recovery scenario."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,
            success_threshold=2
        )
        cb = CircuitBreaker("integration_test", config)
        
        call_count = 0
        
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("Service unavailable")
            return "success"
        
        # Phase 1: Failures cause circuit to open
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(flaky_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Phase 2: Circuit fails fast
        with pytest.raises(CircuitBreakerError):
            cb.call(flaky_func)
        
        # Phase 3: Wait for recovery timeout
        time.sleep(1.1)
        
        # Phase 4: Circuit goes half-open and succeeds
        result = cb.call(flaky_func)
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN
        
        # Phase 5: Another success closes circuit
        result = cb.call(flaky_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_concurrent_access_safety(self):
        """Test circuit breaker behavior under concurrent access."""
        import threading
        
        cb = CircuitBreaker("concurrent_test")
        results = []
        errors = []
        
        def worker():
            try:
                result = cb.call(lambda: "success")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 10
        assert len(errors) == 0
        assert cb.total_successes == 10