"""
BitWarden Manager

Core BitWarden integration class providing secure credential management
and device authentication for NetArchon.
"""

import json
import subprocess
import time
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
from threading import Lock
import hashlib

from netarchon.utils.exceptions import NetArchonError
from netarchon.utils.logger import get_logger
from netarchon.web.utils.security import SecurityManager

from .models import (
    BitWardenItem, BitWardenCredential, CredentialMapping, 
    BitWardenVaultStatus, CredentialType
)
from .exceptions import (
    BitWardenError, BitWardenAuthenticationError, BitWardenNotFoundError,
    BitWardenSyncError, BitWardenTimeoutError, BitWardenLockError
)


class BitWardenManager:
    """
    Secure BitWarden integration for NetArchon credential management.
    
    Provides automated credential retrieval, caching, and device mapping
    for seamless network device authentication.
    """
    
    def __init__(self, config_dir: str = "config"):
        """Initialize BitWarden manager."""
        self.logger = get_logger("BitWardenManager")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Security manager for encryption
        self.security_manager = SecurityManager(str(self.config_dir))
        
        # Session management
        self._session_key: Optional[str] = None
        self._session_expires: Optional[datetime] = None
        self._session_lock = Lock()
        
        # Credential cache
        self._credential_cache: Dict[str, BitWardenCredential] = {}
        self._device_mappings: Dict[str, CredentialMapping] = {}
        self._cache_expires: Optional[datetime] = None
        
        # Configuration files
        self._config_file = self.config_dir / "bitwarden_config.json"
        self._mappings_file = self.config_dir / "device_mappings.json"
        self._cache_file = self.config_dir / "credential_cache.enc"
        
        # Load existing configuration
        self._load_configuration()
        self._load_device_mappings()
        
        # BitWarden CLI timeout settings
        self.cli_timeout = 30
        self.session_timeout = 3600  # 1 hour
        
    def _load_configuration(self) -> None:
        """Load BitWarden configuration from encrypted storage."""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r') as f:
                    config = json.load(f)
                    
                self.server_url = config.get('server_url')
                self.client_id = config.get('client_id')
                # Client secret is encrypted separately
                encrypted_secret = config.get('encrypted_client_secret')
                if encrypted_secret:
                    self.client_secret = self.security_manager.decrypt_credentials(encrypted_secret).get('client_secret')
                    
        except Exception as e:
            self.logger.warning(f"Failed to load BitWarden configuration: {e}")
            self.server_url = None
            self.client_id = None
            self.client_secret = None
    
    def _save_configuration(self) -> None:
        """Save BitWarden configuration with encryption."""
        try:
            config = {
                'server_url': self.server_url,
                'client_id': self.client_id,
                'encrypted_client_secret': self.security_manager.encrypt_credentials({
                    'client_secret': self.client_secret
                }) if self.client_secret else None,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self._config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save BitWarden configuration: {e}")
    
    def _load_device_mappings(self) -> None:
        """Load device-credential mappings."""
        try:
            if self._mappings_file.exists():
                with open(self._mappings_file, 'r') as f:
                    mappings_data = json.load(f)
                    
                for device_ip, mapping_data in mappings_data.items():
                    self._device_mappings[device_ip] = CredentialMapping.from_dict(mapping_data)
                    
        except Exception as e:
            self.logger.warning(f"Failed to load device mappings: {e}")
    
    def _save_device_mappings(self) -> None:
        """Save device-credential mappings."""
        try:
            mappings_data = {}
            for device_ip, mapping in self._device_mappings.items():
                mappings_data[device_ip] = mapping.to_dict()
                
            with open(self._mappings_file, 'w') as f:
                json.dump(mappings_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save device mappings: {e}")
    
    def configure_api_access(self, client_id: str, client_secret: str, 
                           server_url: Optional[str] = None) -> None:
        """Configure BitWarden API access credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.server_url = server_url
        
        self._save_configuration()
        self.logger.info("BitWarden API access configured")
    
    def _run_cli_command(self, command: List[str], input_data: Optional[str] = None,
                        timeout: Optional[int] = None) -> Tuple[bool, str, str]:
        """
        Execute BitWarden CLI command securely.
        
        Returns: (success, stdout, stderr)
        """
        if timeout is None:
            timeout = self.cli_timeout
            
        try:
            # Ensure session key is added if available
            if self._session_key and '--session' not in command:
                command.extend(['--session', self._session_key])
            
            process = subprocess.run(
                command,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=timeout
            )
            
            return process.returncode == 0, process.stdout, process.stderr
            
        except subprocess.TimeoutExpired:
            raise BitWardenTimeoutError(' '.join(command), timeout)
        except Exception as e:
            raise BitWardenError(f"CLI command failed: {e}")
    
    def _ensure_session(self) -> bool:
        """Ensure we have a valid session key."""
        with self._session_lock:
            # Check if current session is still valid
            if (self._session_key and self._session_expires and 
                datetime.now() < self._session_expires):
                return True
            
            # Need to authenticate/unlock
            return self._authenticate_and_unlock()
    
    def _authenticate_and_unlock(self) -> bool:
        """Authenticate with BitWarden and unlock vault."""
        if not all([self.client_id, self.client_secret]):
            raise BitWardenAuthenticationError("API credentials not configured")
        
        try:
            # Login with API key
            success, stdout, stderr = self._run_cli_command(
                ['bw', 'login', '--apikey', '--raw'],
                input_data=f"{self.client_id}\\n{self.client_secret}\\n"
            )
            
            if not success:
                self.logger.error(f"BitWarden login failed: {stderr}")
                raise BitWardenAuthenticationError(f"Login failed: {stderr}")
            
            # Get master password (this would need to be configured securely)
            master_password = self._get_master_password()
            if not master_password:
                raise BitWardenAuthenticationError("Master password not available")
            
            # Unlock vault
            success, stdout, stderr = self._run_cli_command(
                ['bw', 'unlock', '--raw'],
                input_data=master_password
            )
            
            if not success:
                self.logger.error(f"BitWarden unlock failed: {stderr}")
                raise BitWardenAuthenticationError(f"Unlock failed: {stderr}")
            
            # Store session key
            self._session_key = stdout.strip()
            self._session_expires = datetime.now() + timedelta(seconds=self.session_timeout)
            
            self.logger.info("BitWarden authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"BitWarden authentication failed: {e}")
            raise BitWardenAuthenticationError(str(e))
    
    def _get_master_password(self) -> Optional[str]:
        """
        Get master password from secure storage.
        
        Note: In production, this should prompt user or use secure keyring.
        """
        # This is a placeholder - in production you would:
        # 1. Prompt user for master password
        # 2. Use system keyring (keyring library)
        # 3. Use secure environment variable
        # 4. Integrate with system authentication
        
        master_password = os.environ.get('BITWARDEN_MASTER_PASSWORD')
        if not master_password:
            self.logger.warning("Master password not available - please set BITWARDEN_MASTER_PASSWORD environment variable")
        
        return master_password
    
    def sync_vault(self) -> bool:
        """Synchronize vault with BitWarden server."""
        try:
            if not self._ensure_session():
                return False
            
            success, stdout, stderr = self._run_cli_command(['bw', 'sync'])
            
            if success:
                self.logger.info("BitWarden vault synchronized")
                # Clear cache to force refresh
                self._credential_cache.clear()
                self._cache_expires = None
                return True
            else:
                raise BitWardenSyncError(f"Sync failed: {stderr}")
                
        except Exception as e:
            self.logger.error(f"Vault sync failed: {e}")
            raise BitWardenSyncError(str(e))
    
    def get_vault_status(self) -> BitWardenVaultStatus:
        """Get current vault status."""
        try:
            # Check authentication status
            success, stdout, stderr = self._run_cli_command(['bw', 'status'])
            
            if success:
                status_data = json.loads(stdout)
                return BitWardenVaultStatus(
                    is_authenticated=status_data.get('status') != 'unauthenticated',
                    is_unlocked=status_data.get('status') == 'unlocked',
                    server_url=status_data.get('serverUrl'),
                    user_email=status_data.get('userEmail'),
                    last_sync=datetime.now() if status_data.get('lastSync') else None
                )
            else:
                return BitWardenVaultStatus(
                    is_authenticated=False,
                    is_unlocked=False
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get vault status: {e}")
            return BitWardenVaultStatus(
                is_authenticated=False,
                is_unlocked=False
            )
    
    def search_items(self, search_term: str) -> List[BitWardenItem]:
        """Search for items in the vault."""
        try:
            if not self._ensure_session():
                return []
            
            success, stdout, stderr = self._run_cli_command([
                'bw', 'list', 'items', '--search', search_term
            ])
            
            if success:
                items_data = json.loads(stdout)
                return [BitWardenItem.from_json(item) for item in items_data]
            else:
                self.logger.warning(f"Search failed: {stderr}")
                return []
                
        except Exception as e:
            self.logger.error(f"Item search failed: {e}")
            return []
    
    def get_item_by_id(self, item_id: str) -> Optional[BitWardenItem]:
        """Get specific item by ID."""
        try:
            if not self._ensure_session():
                return None
            
            success, stdout, stderr = self._run_cli_command([
                'bw', 'get', 'item', item_id
            ])
            
            if success:
                item_data = json.loads(stdout)
                return BitWardenItem.from_json(item_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get item {item_id}: {e}")
            return None
    
    def get_device_credentials(self, device_ip: str, device_type: str = None) -> Optional[BitWardenCredential]:
        """
        Get credentials for a specific device.
        
        First checks device mappings, then searches vault.
        """
        try:
            # Check device mappings first
            if device_ip in self._device_mappings:
                mapping = self._device_mappings[device_ip]
                item = self.get_item_by_id(mapping.bitwarden_item_id)
                
                if item and item.login:
                    return BitWardenCredential(
                        username=item.login.username,
                        password=item.login.password,
                        device_ip=device_ip,
                        device_type=mapping.device_type,
                        credential_type=mapping.credential_type,
                        enable_password=self._extract_enable_password(item.notes),
                        totp=item.login.totp,
                        notes=item.notes,
                        source_item_id=item.id,
                        source_item_name=item.name,
                        last_updated=item.revision_date
                    )
            
            # Search for credentials using common patterns
            search_terms = self._generate_search_terms(device_ip, device_type)
            
            for term in search_terms:
                items = self.search_items(term)
                
                for item in items:
                    if item.login and self._matches_device(item, device_ip, device_type):
                        # Create and cache mapping for future use
                        mapping = CredentialMapping(
                            device_ip=device_ip,
                            device_hostname=device_ip,  # Could be improved
                            device_type=device_type or "unknown",
                            bitwarden_item_id=item.id,
                            bitwarden_item_name=item.name,
                            credential_type=CredentialType.SSH_PASSWORD,  # Default
                            search_terms=[term],
                            auto_discovered=True,
                            last_verified=datetime.now()
                        )
                        
                        self._device_mappings[device_ip] = mapping
                        self._save_device_mappings()
                        
                        return BitWardenCredential(
                            username=item.login.username,
                            password=item.login.password,
                            device_ip=device_ip,
                            device_type=device_type or "unknown",
                            credential_type=CredentialType.SSH_PASSWORD,
                            enable_password=self._extract_enable_password(item.notes),
                            totp=item.login.totp,
                            notes=item.notes,
                            source_item_id=item.id,
                            source_item_name=item.name,
                            last_updated=item.revision_date
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get credentials for {device_ip}: {e}")
            return None
    
    def _generate_search_terms(self, device_ip: str, device_type: Optional[str]) -> List[str]:
        """Generate search terms for finding device credentials."""
        terms = [
            device_ip,
            f"network-{device_ip}",
            f"device-{device_ip}",
            device_ip.replace('.', '-'),
            f"router-{device_ip}",
            f"switch-{device_ip}",
        ]
        
        if device_type:
            terms.extend([
                f"{device_type}-{device_ip}",
                f"{device_type.lower()}-{device_ip}",
                device_type.lower()
            ])
        
        # Add network range terms
        ip_parts = device_ip.split('.')
        if len(ip_parts) == 4:
            network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
            terms.append(network)
        
        return terms
    
    def _matches_device(self, item: BitWardenItem, device_ip: str, device_type: Optional[str]) -> bool:
        """Check if a BitWarden item matches the target device."""
        # Check URIs
        if item.login and item.login.uris:
            for uri in item.login.uris:
                if device_ip in uri.uri:
                    return True
        
        # Check name and notes
        search_text = f"{item.name} {item.notes or ''}".lower()
        if device_ip in search_text:
            return True
        
        if device_type and device_type.lower() in search_text:
            return True
        
        return False
    
    def _extract_enable_password(self, notes: Optional[str]) -> Optional[str]:
        """Extract enable password from notes field."""
        if not notes:
            return None
        
        # Look for common enable password patterns
        for line in notes.split('\\n'):
            line = line.strip().lower()
            if any(keyword in line for keyword in ['enable', 'privilege', 'admin']):
                # Extract password after colon or equals
                for separator in [':', '=']:
                    if separator in line:
                        parts = line.split(separator, 1)
                        if len(parts) > 1:
                            return parts[1].strip()
        
        return None
    
    def create_device_mapping(self, device_ip: str, device_hostname: str, 
                            device_type: str, bitwarden_item_id: str,
                            credential_type: CredentialType = CredentialType.SSH_PASSWORD) -> bool:
        """Create manual device-credential mapping."""
        try:
            # Verify the BitWarden item exists
            item = self.get_item_by_id(bitwarden_item_id)
            if not item:
                raise BitWardenNotFoundError(bitwarden_item_id)
            
            mapping = CredentialMapping(
                device_ip=device_ip,
                device_hostname=device_hostname,
                device_type=device_type,
                bitwarden_item_id=bitwarden_item_id,
                bitwarden_item_name=item.name,
                credential_type=credential_type,
                auto_discovered=False,
                last_verified=datetime.now()
            )
            
            self._device_mappings[device_ip] = mapping
            self._save_device_mappings()
            
            self.logger.info(f"Created device mapping: {device_ip} -> {item.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create device mapping: {e}")
            return False
    
    def get_all_device_mappings(self) -> Dict[str, CredentialMapping]:
        """Get all device-credential mappings."""
        return self._device_mappings.copy()
    
    def remove_device_mapping(self, device_ip: str) -> bool:
        """Remove device-credential mapping."""
        if device_ip in self._device_mappings:
            del self._device_mappings[device_ip]
            self._save_device_mappings()
            self.logger.info(f"Removed device mapping for {device_ip}")
            return True
        return False
    
    def lock_vault(self) -> bool:
        """Lock the BitWarden vault."""
        try:
            success, stdout, stderr = self._run_cli_command(['bw', 'lock'])
            
            if success:
                with self._session_lock:
                    self._session_key = None
                    self._session_expires = None
                
                self.logger.info("BitWarden vault locked")
                return True
            else:
                self.logger.warning(f"Failed to lock vault: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to lock vault: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources and lock vault."""
        self.lock_vault()
        self._credential_cache.clear()
        self.logger.info("BitWarden manager cleaned up")