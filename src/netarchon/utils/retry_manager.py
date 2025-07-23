"""
NetArchon Retry Manager Implementation

Provides configurable retry logic with exponential backoff and jitter.
"""

import time
import random
from datetime import datetime
from enum import Enum
from typing import Callable, Any, Optional, List, Type
from dataclasses import dataclass

from .exceptions import NetArchonError
from .logger import get_logger


class RetryStrategy(Enum):
    """Retry strategy types."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3                    # Maximum number of retry attempts
    base_delay: float = 1.0                  # Base delay in seconds
    max_delay: float = 60.0                  # Maximum delay in seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True                      # Add random jitter to delays
    backoff_multiplier: float = 2.0          # Multiplier for exponential backoff
    retryable_exceptions: Optional[List[Type[Exception]]] = None  # Exceptions to retry on


class RetryExhaustedError(NetArchonError):
    """Raised when all retry attempts are exhausted."""
    pass


class RetryManager:
    """Manages retry logic for operations."""
    
    def __init__(self, name: str, config: Optional[RetryConfig] = None):
        """Initialize retry manager.
        
        Args:
            name: Unique name for this retry manager
            config: Retry configuration
        """
        self.name = name
        self.config = config or RetryConfig()
        self.logger = get_logger(f"{__name__}.RetryManager.{name}")
        
        # Statistics
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_retries = 0
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            Exception: The last exception if retries are exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self.total_attempts += 1
            
            try:
                self.logger.debug(f"Retry manager {self.name} attempt {attempt}/{self.config.max_attempts}")
                
                # Execute the function
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record success
                self.total_successes += 1
                if attempt > 1:
                    self.logger.info(f"Retry manager {self.name} succeeded on attempt {attempt}",
                                   attempt=attempt, execution_time=execution_time)
                
                return result
                
            except Exception as e:
                last_exception = e
                self.total_failures += 1
                
                # Check if this exception should be retried
                if not self._should_retry(e):
                    self.logger.warning(f"Retry manager {self.name} not retrying exception: {type(e).__name__}",
                                      exception=str(e))
                    raise
                
                # If this is the last attempt, don't wait
                if attempt == self.config.max_attempts:
                    break
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                self.total_retries += 1
                
                self.logger.warning(f"Retry manager {self.name} attempt {attempt} failed, retrying in {delay:.2f}s",
                                  attempt=attempt, exception=str(e), delay=delay)
                
                time.sleep(delay)
        
        # All attempts exhausted
        self.logger.error(f"Retry manager {self.name} exhausted all {self.config.max_attempts} attempts",
                        total_attempts=self.config.max_attempts)
        
        raise RetryExhaustedError(
            f"Retry manager '{self.name}' exhausted all {self.config.max_attempts} attempts",
            {"last_exception": str(last_exception), "attempts": self.config.max_attempts}
        ) from last_exception
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            True if the exception should be retried
        """
        # If no specific exceptions are configured, retry all
        if not self.config.retryable_exceptions:
            return True
        
        # Check if exception type is in the retryable list
        return any(isinstance(exception, exc_type) for exc_type in self.config.retryable_exceptions)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
            
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
            
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            # Add up to 25% random jitter
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount
        
        return delay
    
    def get_statistics(self) -> dict:
        """Get retry manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "name": self.name,
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_retries": self.total_retries,
            "success_rate": self.total_successes / max(self.total_attempts, 1),
            "retry_rate": self.total_retries / max(self.total_attempts, 1),
            "config": {
                "max_attempts": self.config.max_attempts,
                "base_delay": self.config.base_delay,
                "max_delay": self.config.max_delay,
                "strategy": self.config.strategy.value,
                "jitter": self.config.jitter,
                "backoff_multiplier": self.config.backoff_multiplier
            }
        }
    
    def reset_statistics(self) -> None:
        """Reset retry manager statistics."""
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_retries = 0
        self.logger.info(f"Retry manager {self.name} statistics reset")


def with_retry(name: str, config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to a function.
    
    Args:
        name: Retry manager name
        config: Retry configuration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        retry_manager = RetryManager(name, config)
        
        def wrapper(*args, **kwargs):
            return retry_manager.execute(func, *args, **kwargs)
        
        # Attach retry manager to wrapper for access to statistics
        wrapper.retry_manager = retry_manager
        return wrapper
    return decorator


class RetryManagerRegistry:
    """Registry for managing multiple retry managers."""
    
    def __init__(self):
        """Initialize retry manager registry."""
        self.retry_managers: dict[str, RetryManager] = {}
        self.logger = get_logger(f"{__name__}.RetryManagerRegistry")
    
    def get_retry_manager(self, name: str, config: Optional[RetryConfig] = None) -> RetryManager:
        """Get or create a retry manager.
        
        Args:
            name: Retry manager name
            config: Configuration (only used for new retry managers)
            
        Returns:
            RetryManager instance
        """
        if name not in self.retry_managers:
            self.retry_managers[name] = RetryManager(name, config)
            self.logger.info(f"Created new retry manager: {name}")
        
        return self.retry_managers[name]
    
    def get_all_statistics(self) -> dict[str, dict]:
        """Get statistics for all retry managers.
        
        Returns:
            Dictionary mapping retry manager names to their statistics
        """
        return {name: rm.get_statistics() for name, rm in self.retry_managers.items()}
    
    def reset_all_statistics(self) -> None:
        """Reset statistics for all retry managers."""
        for rm in self.retry_managers.values():
            rm.reset_statistics()
        self.logger.info("Reset statistics for all retry managers")


# Global retry manager registry
retry_manager_registry = RetryManagerRegistry()


# Convenience functions for common retry patterns
def create_network_retry_config() -> RetryConfig:
    """Create retry configuration optimized for network operations."""
    return RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
        backoff_multiplier=2.0,
        retryable_exceptions=[ConnectionError, TimeoutError, OSError]
    )


def create_database_retry_config() -> RetryConfig:
    """Create retry configuration optimized for database operations."""
    return RetryConfig(
        max_attempts=5,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
        backoff_multiplier=1.5
    )


def create_api_retry_config() -> RetryConfig:
    """Create retry configuration optimized for API calls."""
    return RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
        backoff_multiplier=2.0
    )


def create_file_operation_retry_config() -> RetryConfig:
    """Create retry configuration optimized for file operations."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=5.0,
        strategy=RetryStrategy.LINEAR_BACKOFF,
        jitter=False,
        retryable_exceptions=[OSError, IOError, PermissionError]
    )