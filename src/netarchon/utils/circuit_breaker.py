"""
NetArchon Circuit Breaker Pattern Implementation

Provides circuit breaker functionality for fault tolerance and resilience.
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
    OPEN = "open"          # Circuit breaker active, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Number of failures to trigger open state
    success_threshold: int = 3          # Number of successes to close from half-open
    timeout_seconds: int = 60           # Time to wait before trying half-open
    reset_timeout_seconds: int = 300    # Time to reset failure count
    excluded_exceptions: tuple = ()     # Exception types to not count as failures


class CircuitBreakerError(NetArchonError):
    """Circuit breaker specific errors."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration for circuit breaker behavior
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = get_logger(f"{__name__}.CircuitBreaker.{name}")
        
        # Circuit state tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state_changed_time = datetime.now()
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_transitions: Dict[str, int] = {
            state.value: 0 for state in CircuitState
        }
    
    def execute_with_circuit_breaker(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection.
        
        Args:
            operation: Function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result from the operation
            
        Raises:
            CircuitBreakerError: If circuit is open and rejecting calls
            Exception: Any exception raised by the operation
        """
        self._total_calls += 1
        
        # Check if circuit should be opened due to timeout
        self._check_state_transitions()
        
        # Reject calls if circuit is open
        if self._state == CircuitState.OPEN:
            self.logger.warning(f"Circuit breaker {self.name} is OPEN, rejecting call")
            raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
        
        try:
            # Execute the operation
            start_time = time.time()
            result = operation(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success
            self._record_success(execution_time)
            return result
            
        except Exception as e:
            # Check if this exception should be counted as failure
            if not isinstance(e, self.config.excluded_exceptions):
                self._record_failure(e)
            
            # Re-raise the original exception
            raise
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status and statistics.
        
        Returns:
            Dictionary containing circuit status information
        """
        self._check_state_transitions()
        
        return {
            'name': self.name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'success_count': self._success_count,
            'total_calls': self._total_calls,
            'total_failures': self._total_failures,
            'total_successes': self._total_successes,
            'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
            'state_changed_time': self._state_changed_time.isoformat(),
            'time_in_current_state': (datetime.now() - self._state_changed_time).total_seconds(),
            'state_transitions': self._state_transitions.copy(),
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold,
                'timeout_seconds': self.config.timeout_seconds,
                'reset_timeout_seconds': self.config.reset_timeout_seconds
            }
        }
    
    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to closed state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._state_changed_time = datetime.now()
        
        self.logger.info(f"Circuit breaker {self.name} manually reset from {old_state.value} to CLOSED")
        self._record_state_transition(CircuitState.CLOSED)
    
    def force_open(self) -> None:
        """Manually force circuit breaker to open state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._state_changed_time = datetime.now()
        
        self.logger.warning(f"Circuit breaker {self.name} manually forced from {old_state.value} to OPEN")
        self._record_state_transition(CircuitState.OPEN)
    
    def _record_success(self, execution_time: float) -> None:
        """Record successful operation execution."""
        self._total_successes += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self.logger.debug(f"Circuit breaker {self.name} recorded success in HALF_OPEN state "
                            f"({self._success_count}/{self.config.success_threshold})")
            
            # Close circuit if enough successes
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            if self._failure_count > 0:
                self.logger.debug(f"Circuit breaker {self.name} resetting failure count after success")
                self._failure_count = 0
    
    def _record_failure(self, exception: Exception) -> None:
        """Record failed operation execution."""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        self.logger.warning(f"Circuit breaker {self.name} recorded failure: {type(exception).__name__}: {str(exception)}")
        
        if self._state == CircuitState.CLOSED:
            # Open circuit if failure threshold reached
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # Go back to open on any failure in half-open state
            self._transition_to_open()
    
    def _check_state_transitions(self) -> None:
        """Check if circuit state should transition based on time."""
        now = datetime.now()
        time_in_state = (now - self._state_changed_time).total_seconds()
        
        if self._state == CircuitState.OPEN and time_in_state >= self.config.timeout_seconds:
            self._transition_to_half_open()
        
        elif (self._state == CircuitState.CLOSED and 
              self._last_failure_time and
              (now - self._last_failure_time).total_seconds() >= self.config.reset_timeout_seconds):
            # Reset failure count if enough time has passed since last failure
            if self._failure_count > 0:
                self.logger.debug(f"Circuit breaker {self.name} resetting failure count due to timeout")
                self._failure_count = 0
    
    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self._state = CircuitState.OPEN
        self._state_changed_time = datetime.now()
        self._success_count = 0
        
        self.logger.error(f"Circuit breaker {self.name} transitioned to OPEN state "
                         f"(failures: {self._failure_count}/{self.config.failure_threshold})")
        self._record_state_transition(CircuitState.OPEN)
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._state_changed_time = datetime.now()
        self._success_count = 0
        
        self.logger.info(f"Circuit breaker {self.name} transitioned to HALF_OPEN state "
                        f"(testing service recovery)")
        self._record_state_transition(CircuitState.HALF_OPEN)
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._state_changed_time = datetime.now()
        self._failure_count = 0
        self._success_count = 0
        
        self.logger.info(f"Circuit breaker {self.name} transitioned to CLOSED state "
                        f"(service recovered)")
        self._record_state_transition(CircuitState.CLOSED)
    
    def _record_state_transition(self, new_state: CircuitState) -> None:
        """Record state transition for statistics."""
        self._state_transitions[new_state.value] += 1
    
    def __str__(self) -> str:
        """String representation of circuit breaker."""
        return f"CircuitBreaker(name={self.name}, state={self._state.value}, failures={self._failure_count})"
    
    def __repr__(self) -> str:
        """Detailed representation of circuit breaker."""
        return (f"CircuitBreaker(name='{self.name}', state={self._state.value}, "
                f"failures={self._failure_count}, successes={self._success_count}, "
                f"total_calls={self._total_calls})")


class CircuitBreakerManager:
    """Global manager for circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = get_logger(f"{__name__}.CircuitBreakerManager")
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker by name.
        
        Args:
            name: Circuit breaker name
            config: Configuration for new circuit breaker
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name, config)
            self.logger.info(f"Created new circuit breaker: {name}")
        
        return self._circuit_breakers[name]
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers.
        
        Returns:
            Dictionary mapping circuit breaker names to their statuses
        """
        return {name: cb.get_circuit_status() for name, cb in self._circuit_breakers.items()}
    
    def reset_all_circuits(self) -> None:
        """Reset all circuit breakers to closed state."""
        for name, circuit_breaker in self._circuit_breakers.items():
            circuit_breaker.reset_circuit()
        
        self.logger.info(f"Reset {len(self._circuit_breakers)} circuit breakers")


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()