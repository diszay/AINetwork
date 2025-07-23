"""
BitWarden Integration Data Models

Data structures for BitWarden items, credentials, and device mappings.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ItemType(Enum):
    """BitWarden item types."""
    LOGIN = 1
    SECURE_NOTE = 2
    CARD = 3
    IDENTITY = 4


class CredentialType(Enum):
    """Types of credentials for device authentication."""
    SSH_PASSWORD = "ssh_password"
    SSH_KEY = "ssh_key"
    SNMP_COMMUNITY = "snmp_community"
    WEB_LOGIN = "web_login"
    API_KEY = "api_key"
    ENABLE_PASSWORD = "enable_password"


@dataclass
class BitWardenUri:
    """BitWarden URI information."""
    uri: str
    match_type: Optional[int] = None


@dataclass
class BitWardenLogin:
    """BitWarden login information."""
    username: str
    password: str
    totp: Optional[str] = None
    uris: List[BitWardenUri] = field(default_factory=list)


@dataclass
class BitWardenItem:
    """Complete BitWarden item structure."""
    id: str
    name: str
    item_type: ItemType
    login: Optional[BitWardenLogin] = None
    notes: Optional[str] = None
    favorite: bool = False
    folder_id: Optional[str] = None
    organization_id: Optional[str] = None
    collection_ids: List[str] = field(default_factory=list)
    revision_date: Optional[datetime] = None
    creation_date: Optional[datetime] = None
    deleted_date: Optional[datetime] = None
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'BitWardenItem':
        """Create BitWardenItem from JSON data."""
        login_data = data.get('login')
        login = None
        
        if login_data:
            uris = []
            for uri_data in login_data.get('uris', []):
                uris.append(BitWardenUri(
                    uri=uri_data.get('uri', ''),
                    match_type=uri_data.get('match')
                ))
            
            login = BitWardenLogin(
                username=login_data.get('username', ''),
                password=login_data.get('password', ''),
                totp=login_data.get('totp'),
                uris=uris
            )
        
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            item_type=ItemType(data.get('type', 1)),
            login=login,
            notes=data.get('notes'),
            favorite=data.get('favorite', False),
            folder_id=data.get('folderId'),
            organization_id=data.get('organizationId'),
            collection_ids=data.get('collectionIds', []),
            revision_date=datetime.fromisoformat(data['revisionDate'].replace('Z', '+00:00')) if data.get('revisionDate') else None,
            creation_date=datetime.fromisoformat(data['creationDate'].replace('Z', '+00:00')) if data.get('creationDate') else None,
            deleted_date=datetime.fromisoformat(data['deletedDate'].replace('Z', '+00:00')) if data.get('deletedDate') else None
        )


@dataclass
class BitWardenCredential:
    """Extracted credential information for NetArchon use."""
    username: str
    password: str
    device_ip: str
    device_type: str
    credential_type: CredentialType
    enable_password: Optional[str] = None
    totp: Optional[str] = None
    notes: Optional[str] = None
    source_item_id: Optional[str] = None
    source_item_name: Optional[str] = None
    last_updated: Optional[datetime] = None


@dataclass
class CredentialMapping:
    """Mapping between NetArchon devices and BitWarden items."""
    device_ip: str
    device_hostname: str
    device_type: str
    bitwarden_item_id: str
    bitwarden_item_name: str
    credential_type: CredentialType
    search_terms: List[str] = field(default_factory=list)
    auto_discovered: bool = False
    last_verified: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'device_ip': self.device_ip,
            'device_hostname': self.device_hostname,
            'device_type': self.device_type,
            'bitwarden_item_id': self.bitwarden_item_id,
            'bitwarden_item_name': self.bitwarden_item_name,
            'credential_type': self.credential_type.value,
            'search_terms': self.search_terms,
            'auto_discovered': self.auto_discovered,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialMapping':
        """Create from dictionary."""
        return cls(
            device_ip=data['device_ip'],
            device_hostname=data['device_hostname'],
            device_type=data['device_type'],
            bitwarden_item_id=data['bitwarden_item_id'],
            bitwarden_item_name=data['bitwarden_item_name'],
            credential_type=CredentialType(data['credential_type']),
            search_terms=data.get('search_terms', []),
            auto_discovered=data.get('auto_discovered', False),
            last_verified=datetime.fromisoformat(data['last_verified']) if data.get('last_verified') else None
        )


@dataclass
class BitWardenVaultStatus:
    """Current status of BitWarden vault."""
    is_authenticated: bool
    is_unlocked: bool
    server_url: Optional[str] = None
    user_email: Optional[str] = None
    last_sync: Optional[datetime] = None
    total_items: int = 0
    session_expires: Optional[datetime] = None