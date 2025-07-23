"""
NetArchon Retry Manager Implementation

Provides intelligent retry mechanisms with various backoff strategies.
"""

import time
import random
from datetime import datetime
from enum import Enum
from typing import Callable, Any, Optional, Type, Tuple, List
from dataclasses import dataclass

from .exceptions import NetArchonError
from .logger import get_logger


class RetryStrategy(Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"              # Fixed delay between retries
    LINEAR = "linear"            # Linearly increasing delay
    EXPONENTIAL = "exponential"  # Exponentially increasing delay
    EXPONENTIAL_JITTER = "exponential_jitter"  # Exponential with random jitter


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    jitter_max_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


class RetryExhaustedError(NetArchonError):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay_seconds: float
    exception: Optional[Exception]
    execution_time_seconds: float
    timestamp: datetime


class RetryManager:
    """Manages retry logic with configurable strategies."""
    
    def __init__(self, name: str = "default"):
        """Initialize retry manager.
        
        Args:
            name: Name for this retry manager instance
        """
        self.name = name
        self.logger = get_logger(f"{__name__}.RetryManager.{name}")
    
    def execute_with_retry(self, operation: Callable, config: RetryConfig, *args, **kwargs) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Function to execute
            config: Retry configuration
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result from the successful operation
            
        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            Exception: Non-retryable exceptions are re-raised immediately
        """
        attempts: List[RetryAttempt] = []
        last_exception: Optional[Exception] = None
        
        for attempt in range(config.max_attempts):
            try:
                start_time = time.time()
                
                self.logger.debug(f"Retry manager {self.name}: Attempt {attempt + 1}/{config.max_attempts}")
                
                # Execute the operation
                result = operation(*args, **kwargs)
                
                execution_time = time.time() - start_time
                
                # Record successful attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt + 1,
                    delay_seconds=0.0,
                    exception=None,
                    execution_time_seconds=execution_time,
                    timestamp=datetime.now()
                ))
                
                if attempt > 0:
                    self.logger.info(f"Retry manager {self.name}: Operation succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                last_exception = e
                
                # Check if this exception is retryable
                if not self._is_retryable_exception(e, config):
                    self.logger.warning(f"Retry manager {self.name}: Non-retryable exception {type(e).__name__}, not retrying")
                    raise
                
                # Calculate delay for next attempt
                delay = self.calculate_backoff_delay(attempt, config)
                
                # Record failed attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt + 1,
                    delay_seconds=delay,
                    exception=e,
                    execution_time_seconds=execution_time,
                    timestamp=datetime.now()
                ))
                
                self.logger.warning(f"Retry manager {self.name}: Attempt {attempt + 1} failed with {type(e).__name__}: {str(e)}")
                
                # Don't delay after the last attempt
                if attempt < config.max_attempts - 1:
                    self.logger.debug(f"Retry manager {self.name}: Waiting {delay:.2f}s before next attempt")
                    time.sleep(delay)
        
        # All attempts exhausted
        error_message = (f"Retry manager {self.name}: All {config.max_attempts} attempts failed. "
                        f"Last error: {type(last_exception).__name__}: {str(last_exception)}")
        
        self.logger.error(error_message)
        
        raise RetryExhaustedError(
            message=error_message,
            attempts=len(attempts),
            last_exception=last_exception
        )
    
    def calculate_backoff_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt based on strategy.
        
        Args:
            attempt: Zero-based attempt number
            config: Retry configuration
            
        Returns:
            Delay in seconds for the next attempt
        """
        if config.strategy == RetryStrategy.FIXED:
            delay = config.base_delay_seconds
            
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay_seconds * (attempt + 1)
            
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay_seconds * (config.backoff_multiplier ** attempt)
            
        elif config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            base_delay = config.base_delay_seconds * (config.backoff_multiplier ** attempt)
            jitter = random.uniform(0, config.jitter_max_seconds)
            delay = base_delay + jitter
            
        else:
            # Default to exponential
            delay = config.base_delay_seconds * (config.backoff_multiplier ** attempt)
        
        # Ensure delay doesn't exceed maximum
        return min(delay, config.max_delay_seconds)
    
    def _is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """Check if an exception is retryable based on configuration.
        
        Args:
            exception: Exception to check
            config: Retry configuration
            
        Returns:
            True if the exception should trigger a retry
        """
        # Check non-retryable exceptions first (higher priority)
        if config.non_retryable_exceptions:
            for exc_type in config.non_retryable_exceptions:
                if isinstance(exception, exc_type):
                    return False
        
        # Check retryable exceptions
        if config.retryable_exceptions:
            for exc_type in config.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True
        
        # Default: don't retry if no match
        return False
    
    def create_retry_decorator(self, config: RetryConfig):
        """Create a decorator for automatic retry functionality.
        
        Args:
            config: Retry configuration
            
        Returns:
            Decorator function that adds retry logic
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                return self.execute_with_retry(func, config, *args, **kwargs)
            
            wrapper.__name__ = f"retry_{func.__name__}"
            wrapper.__doc__ = f"Retry-wrapped version of {func.__name__}"
            return wrapper
        
        return decorator


# Convenience functions for common retry patterns

def with_exponential_backoff(max_attempts: int = 3, 
                           base_delay: float = 1.0,
                           max_delay: float = 60.0,
                           retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """Decorator for exponential backoff retry pattern.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorator function
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=retryable_exceptions
    )
    
    retry_manager = RetryManager("exponential_backoff")
    return retry_manager.create_retry_decorator(config)


def with_fixed_delay(max_attempts: int = 3,
                    delay: float = 1.0,
                    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """Decorator for fixed delay retry pattern.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Fixed delay in seconds between attempts
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorator function
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_seconds=delay,
        max_delay_seconds=delay,
        strategy=RetryStrategy.FIXED,
        retryable_exceptions=retryable_exceptions
    )
    
    retry_manager = RetryManager("fixed_delay")
    return retry_manager.create_retry_decorator(config)


def execute_with_circuit_breaker_and_retry(operation: Callable,
                                         circuit_breaker,
                                         retry_config: RetryConfig,
                                         *args, **kwargs) -> Any:
    """Execute operation with both circuit breaker and retry protection.
    
    Args:
        operation: Function to execute
        circuit_breaker: CircuitBreaker instance
        retry_config: Retry configuration
        *args: Arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result from the successful operation
    """
    retry_manager = RetryManager("circuit_breaker_retry")
    
    def protected_operation(*op_args, **op_kwargs):
        return circuit_breaker.execute_with_circuit_breaker(operation, *op_args, **op_kwargs)
    
    return retry_manager.execute_with_retry(protected_operation, retry_config, *args, **kwargs)