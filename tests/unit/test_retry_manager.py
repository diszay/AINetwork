"""
Tests for NetArchon Retry Manager Implementation
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.netarchon.utils.retry_manager import (
    RetryManager, RetryConfig, RetryStrategy, RetryExhaustedError,
    with_retry, RetryManagerRegistry, retry_manager_registry,
    create_network_retry_config, create_database_retry_config,
    create_api_retry_config, create_file_operation_retry_config
)


class TestRetryConfig:
    """Test RetryConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.jitter is True
        assert config.backoff_multiplier == 2.0
        assert config.retryable_exceptions is None
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            strategy=RetryStrategy.FIXED_DELAY,
            jitter=False,
            backoff_multiplier=1.5,
            retryable_exceptions=[ValueError, TypeError]
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.strategy == RetryStrategy.FIXED_DELAY
        assert config.jitter is False
        assert config.backoff_multiplier == 1.5
        assert config.retryable_exceptions == [ValueError, TypeError]


class TestRetryManager:
    """Test RetryManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Short delay for testing
            max_delay=1.0,
            jitter=False  # Disable jitter for predictable tests
        )
        self.retry_manager = RetryManager("test_retry", self.config)
    
    def test_successful_execution_first_attempt(self):
        """Test successful execution on first attempt."""
        def success_func():
            return "success"
        
        result = self.retry_manager.execute(success_func)
        
        assert result == "success"
        assert self.retry_manager.total_attempts == 1
        assert self.retry_manager.total_successes == 1
        assert self.retry_manager.total_failures == 0
        assert self.retry_manager.total_retries == 0
    
    def test_successful_execution_after_retries(self):
        """Test successful execution after some failures."""
        call_count = 0
        
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = self.retry_manager.execute(flaky_func)
        
        assert result == "success"
        assert self.retry_manager.total_attempts == 3
        assert self.retry_manager.total_successes == 1
        assert self.retry_manager.total_failures == 2
        assert self.retry_manager.total_retries == 2
    
    def test_retry_exhausted(self):
        """Test retry exhaustion when all attempts fail."""
        def always_fail():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError, match="exhausted all 3 attempts"):
            self.retry_manager.execute(always_fail)
        
        assert self.retry_manager.total_attempts == 3
        assert self.retry_manager.total_successes == 0
        assert self.retry_manager.total_failures == 3
        assert self.retry_manager.total_retries == 2
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=[ValueError]  # Only retry ValueError
        )
        retry_manager = RetryManager("test_non_retryable", config)
        
        def fail_with_type_error():
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError, match="Not retryable"):
            retry_manager.execute(fail_with_type_error)
        
        # Should only attempt once
        assert retry_manager.total_attempts == 1
        assert retry_manager.total_retries == 0
    
    def test_retryable_exception_filtering(self):
        """Test that only specified exceptions are retried."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=[ValueError]
        )
        retry_manager = RetryManager("test_retryable", config)
        
        def fail_with_value_error():
            raise ValueError("Retryable error")
        
        with pytest.raises(RetryExhaustedError):
            retry_manager.execute(fail_with_value_error)
        
        # Should attempt all retries
        assert retry_manager.total_attempts == 3
        assert retry_manager.total_retries == 2
    
    def test_fixed_delay_strategy(self):
        """Test fixed delay strategy."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            strategy=RetryStrategy.FIXED_DELAY,
            jitter=False
        )
        retry_manager = RetryManager("test_fixed", config)
        
        delays = []
        for attempt in range(1, 3):  # Test attempts 1 and 2
            delay = retry_manager._calculate_delay(attempt)
            delays.append(delay)
        
        # All delays should be the same
        assert all(delay == 0.1 for delay in delays)
    
    def test_exponential_backoff_strategy(self):
        """Test exponential backoff strategy."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            backoff_multiplier=2.0,
            jitter=False
        )
        retry_manager = RetryManager("test_exponential", config)
        
        delays = []
        for attempt in range(1, 4):  # Test attempts 1, 2, 3
            delay = retry_manager._calculate_delay(attempt)
            delays.append(delay)
        
        # Should be 1.0, 2.0, 4.0
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
    
    def test_linear_backoff_strategy(self):
        """Test linear backoff strategy."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            jitter=False
        )
        retry_manager = RetryManager("test_linear", config)
        
        delays = []
        for attempt in range(1, 4):  # Test attempts 1, 2, 3
            delay = retry_manager._calculate_delay(attempt)
            delays.append(delay)
        
        # Should be 1.0, 2.0, 3.0
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 3.0
    
    def test_max_delay_limit(self):
        """Test that delays are capped at max_delay."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=10.0,
            max_delay=5.0,  # Lower than what exponential would produce
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False
        )
        retry_manager = RetryManager("test_max_delay", config)
        
        delay = retry_manager._calculate_delay(3)  # Would be 40.0 without limit
        assert delay == 5.0
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            base_delay=1.0,
            jitter=True
        )
        retry_manager = RetryManager("test_jitter", config)
        
        delays = []
        for _ in range(10):
            delay = retry_manager._calculate_delay(1)
            delays.append(delay)
        
        # All delays should be different due to jitter
        assert len(set(delays)) > 1
        # All delays should be >= base_delay
        assert all(delay >= 1.0 for delay in delays)
        # All delays should be <= base_delay + 25% jitter
        assert all(delay <= 1.25 for delay in delays)
    
    def test_get_statistics(self):
        """Test get_statistics method."""
        def success_func():
            return "success"
        
        def fail_func():
            raise ValueError("Test error")
        
        # Execute some operations
        self.retry_manager.execute(success_func)
        try:
            self.retry_manager.execute(fail_func)
        except RetryExhaustedError:
            pass
        
        stats = self.retry_manager.get_statistics()
        
        assert stats["name"] == "test_retry"
        assert stats["total_attempts"] == 4  # 1 success + 3 failed attempts
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 3
        assert stats["total_retries"] == 2
        assert stats["success_rate"] == 0.25
        assert stats["retry_rate"] == 0.5
        assert "config" in stats
    
    def test_reset_statistics(self):
        """Test reset_statistics method."""
        def success_func():
            return "success"
        
        # Execute operation
        self.retry_manager.execute(success_func)
        
        # Reset statistics
        self.retry_manager.reset_statistics()
        
        assert self.retry_manager.total_attempts == 0
        assert self.retry_manager.total_successes == 0
        assert self.retry_manager.total_failures == 0
        assert self.retry_manager.total_retries == 0


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        @with_retry("decorator_test", RetryConfig(max_attempts=3, base_delay=0.01))
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
        
        # Check statistics
        stats = success_func.retry_manager.get_statistics()
        assert stats["total_successes"] == 1
    
    def test_decorator_with_retries(self):
        """Test decorator with function that needs retries."""
        call_count = 0
        
        @with_retry("decorator_retry_test", RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        
        # Check statistics
        stats = flaky_func.retry_manager.get_statistics()
        assert stats["total_attempts"] == 3
        assert stats["total_successes"] == 1
        assert stats["total_retries"] == 2
    
    def test_decorator_exhausted(self):
        """Test decorator when retries are exhausted."""
        @with_retry("decorator_exhausted_test", RetryConfig(max_attempts=2, base_delay=0.01))
        def always_fail():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            always_fail()
        
        # Check statistics
        stats = always_fail.retry_manager.get_statistics()
        assert stats["total_attempts"] == 2
        assert stats["total_successes"] == 0


class TestRetryManagerRegistry:
    """Test RetryManagerRegistry functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = RetryManagerRegistry()
    
    def test_get_retry_manager_creates_new(self):
        """Test getting a new retry manager creates it."""
        rm = self.registry.get_retry_manager("test_rm")
        
        assert rm.name == "test_rm"
        assert "test_rm" in self.registry.retry_managers
    
    def test_get_retry_manager_returns_existing(self):
        """Test getting existing retry manager returns same instance."""
        rm1 = self.registry.get_retry_manager("test_rm")
        rm2 = self.registry.get_retry_manager("test_rm")
        
        assert rm1 is rm2
    
    def test_get_retry_manager_with_config(self):
        """Test creating retry manager with custom config."""
        config = RetryConfig(max_attempts=5)
        rm = self.registry.get_retry_manager("test_rm", config)
        
        assert rm.config.max_attempts == 5
    
    def test_get_all_statistics(self):
        """Test getting statistics for all retry managers."""
        rm1 = self.registry.get_retry_manager("rm1")
        rm2 = self.registry.get_retry_manager("rm2")
        
        # Execute some operations
        rm1.execute(lambda: "success")
        rm2.execute(lambda: "success")
        
        stats = self.registry.get_all_statistics()
        
        assert "rm1" in stats
        assert "rm2" in stats
        assert stats["rm1"]["total_successes"] == 1
        assert stats["rm2"]["total_successes"] == 1
    
    def test_reset_all_statistics(self):
        """Test resetting statistics for all retry managers."""
        rm1 = self.registry.get_retry_manager("rm1")
        rm2 = self.registry.get_retry_manager("rm2")
        
        # Execute operations
        rm1.execute(lambda: "success")
        rm2.execute(lambda: "success")
        
        # Reset all
        self.registry.reset_all_statistics()
        
        assert rm1.total_successes == 0
        assert rm2.total_successes == 0


class TestRetryConfigFactories:
    """Test retry configuration factory functions."""
    
    def test_network_retry_config(self):
        """Test network retry configuration."""
        config = create_network_retry_config()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.jitter is True
        assert config.backoff_multiplier == 2.0
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions
        assert OSError in config.retryable_exceptions
    
    def test_database_retry_config(self):
        """Test database retry configuration."""
        config = create_database_retry_config()
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 10.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.backoff_multiplier == 1.5
    
    def test_api_retry_config(self):
        """Test API retry configuration."""
        config = create_api_retry_config()
        
        assert config.max_attempts == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
    
    def test_file_operation_retry_config(self):
        """Test file operation retry configuration."""
        config = create_file_operation_retry_config()
        
        assert config.max_attempts == 3
        assert config.base_delay == 0.1
        assert config.max_delay == 5.0
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.jitter is False
        assert OSError in config.retryable_exceptions
        assert IOError in config.retryable_exceptions
        assert PermissionError in config.retryable_exceptions


class TestRetryIntegration:
    """Integration tests for retry functionality."""
    
    def test_realistic_network_operation(self):
        """Test realistic network operation with retries."""
        attempt_count = 0
        
        def simulate_network_call():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count <= 2:
                raise ConnectionError("Network unreachable")
            return {"status": "success", "data": "response"}
        
        config = create_network_retry_config()
        config.base_delay = 0.01  # Speed up test
        retry_manager = RetryManager("network_test", config)
        
        result = retry_manager.execute(simulate_network_call)
        
        assert result["status"] == "success"
        assert retry_manager.total_attempts == 3
        assert retry_manager.total_successes == 1
        assert retry_manager.total_retries == 2
    
    @patch('time.sleep')
    def test_delay_calculation_in_practice(self, mock_sleep):
        """Test that delays are calculated and applied correctly."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False
        )
        retry_manager = RetryManager("delay_test", config)
        
        def always_fail():
            raise ValueError("Test error")
        
        with pytest.raises(RetryExhaustedError):
            retry_manager.execute(always_fail)
        
        # Check that sleep was called with correct delays
        assert mock_sleep.call_count == 2  # 2 retries
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 1.0  # First retry delay
        assert calls[1][0][0] == 2.0  # Second retry delay