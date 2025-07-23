"""
NetArchon Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily disabling failing operations.
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass

from .exceptions import NetArchonError
from .logger import get_logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: int = 60          # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: int = 30                   # Operation timeout in seconds


class CircuitBreakerError(NetArchonError):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration parameters
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = get_logger(f"{__name__}.CircuitBreaker.{name}")
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original function exceptions when circuit is closed/half-open
        """
        self.total_calls += 1
        
        # Check if circuit should transition states
        self._update_state()
        
        if self.state == CircuitState.OPEN:
            self.logger.warning(f"Circuit breaker {self.name} is OPEN - failing fast")
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open",
                {"state": self.state.value, "failure_count": self.failure_count}
            )
        
        try:
            # Execute the function
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success
            self._record_success(execution_time)
            return result
            
        except Exception as e:
            # Record failure
            self._record_failure(e)
            raise
    
    def _update_state(self) -> None:
        """Update circuit breaker state based on current conditions."""
        now = datetime.utcnow()
        
        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if (self.last_failure_time and 
                now - self.last_failure_time >= timedelta(seconds=self.config.recovery_timeout)):
                self._transition_to_half_open()
                
        elif self.state == CircuitState.HALF_OPEN:
            # Check if we should close (enough successes) or open (any failure)
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
    
    def _record_success(self, execution_time: float) -> None:
        """Record successful operation."""
        self.total_successes += 1
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.logger.debug(f"Circuit breaker {self.name} success in HALF_OPEN state",
                            success_count=self.success_count,
                            execution_time=execution_time)
            # Check if we should close the circuit
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self, exception: Exception) -> None:
        """Record failed operation."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        self.logger.warning(f"Circuit breaker {self.name} recorded failure",
                          failure_count=self.failure_count,
                          exception=str(exception))
        
        # Check if we should open the circuit
        if self.failure_count >= self.config.failure_threshold:
            self._transition_to_open()
        
        # In half-open state, any failure opens the circuit
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.logger.error(f"Circuit breaker {self.name} transitioned to OPEN",
                        failure_count=self.failure_count,
                        threshold=self.config.failure_threshold)
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.logger.info(f"Circuit breaker {self.name} transitioned to HALF_OPEN")
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(f"Circuit breaker {self.name} transitioned to CLOSED")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status.
        
        Returns:
            Dictionary with current status information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": self.total_failures / max(self.total_calls, 1),
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        self.logger.info(f"Circuit breaker {self.name} manually reset")
    
    def force_open(self) -> None:
        """Force circuit breaker to OPEN state."""
        self.state = CircuitState.OPEN
        self.logger.warning(f"Circuit breaker {self.name} manually forced to OPEN")
    
    def force_closed(self) -> None:
        """Force circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(f"Circuit breaker {self.name} manually forced to CLOSED")


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = get_logger(f"{__name__}.CircuitBreakerManager")
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration (only used for new circuit breakers)
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
            self.logger.info(f"Created new circuit breaker: {name}")
        
        return self.circuit_breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers.
        
        Returns:
            Dictionary mapping circuit breaker names to their status
        """
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb.reset()
        self.logger.info("Reset all circuit breakers")


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to add circuit breaker protection to a function.
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cb = circuit_breaker_manager.get_circuit_breaker(name, config)
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator