"""
NetArchon BitWarden Integration

Secure password manager integration providing automated credential management
for network devices and services. Supports CLI-based authentication, encrypted
caching, and seamless integration with NetArchon's device management system.
"""

from .manager import BitWardenManager
from .models import BitWardenCredential, BitWardenItem, CredentialMapping
from .exceptions import BitWardenError, BitWardenAuthenticationError, BitWardenNotFoundError

__all__ = [
    "BitWardenManager",
    "BitWardenCredential", 
    "BitWardenItem",
    "CredentialMapping",
    "BitWardenError",
    "BitWardenAuthenticationError", 
    "BitWardenNotFoundError"
]