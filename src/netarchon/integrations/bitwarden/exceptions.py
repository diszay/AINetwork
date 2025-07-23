"""
BitWarden Integration Exceptions

Custom exception classes for BitWarden integration error handling.
"""

from netarchon.utils.exceptions import NetArchonError


class BitWardenError(NetArchonError):
    """Base exception for BitWarden integration errors."""
    pass


class BitWardenAuthenticationError(BitWardenError):
    """Raised when BitWarden authentication fails."""
    
    def __init__(self, message: str = "BitWarden authentication failed"):
        super().__init__(message)
        self.error_type = "authentication_error"


class BitWardenNotFoundError(BitWardenError):
    """Raised when requested credential or item is not found."""
    
    def __init__(self, search_term: str):
        message = f"BitWarden item not found: {search_term}"
        super().__init__(message)
        self.error_type = "item_not_found"
        self.search_term = search_term


class BitWardenSyncError(BitWardenError):
    """Raised when vault synchronization fails."""
    
    def __init__(self, message: str = "BitWarden vault synchronization failed"):
        super().__init__(message)
        self.error_type = "sync_error"


class BitWardenTimeoutError(BitWardenError):
    """Raised when BitWarden CLI operations timeout."""
    
    def __init__(self, operation: str, timeout: int):
        message = f"BitWarden operation '{operation}' timed out after {timeout} seconds"
        super().__init__(message)
        self.error_type = "timeout_error"
        self.operation = operation
        self.timeout = timeout


class BitWardenLockError(BitWardenError):
    """Raised when vault is locked and operation requires unlocked state."""
    
    def __init__(self, message: str = "BitWarden vault is locked"):
        super().__init__(message)
        self.error_type = "vault_locked"