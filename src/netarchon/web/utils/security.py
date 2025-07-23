"""
NetArchon Security Utilities

Secure authentication, credential management, and access control for the web interface.
"""

import streamlit as st
import hashlib
import hmac
import secrets
import os
import json
import time
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import ipaddress
import re
import logging

class SecurityManager:
    """Comprehensive security management for NetArchon web interface."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize security manager."""
        self.config_dir = config_dir
        self.logger = logging.getLogger("SecurityManager")
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        # Security configuration
        self.session_timeout = 3600  # 1 hour
        self.max_login_attempts = 3
        self.lockout_duration = 300  # 5 minutes
        
        # In-memory storage for session data
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        if 'authenticated_users' not in st.session_state:
            st.session_state.authenticated_users = {}
        
        # Load or create security keys
        self._initialize_encryption_key()
    
    def _initialize_encryption_key(self):
        """Initialize or load encryption key."""
        key_file = os.path.join(self.config_dir, ".encryption_key")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                self.fernet = Fernet(key)
            except Exception as e:
                self.logger.error(f"Failed to load encryption key: {e}")
                self._generate_new_key(key_file)
        else:
            self._generate_new_key(key_file)
    
    def _generate_new_key(self, key_file: str):
        """Generate new encryption key."""
        key = Fernet.generate_key()
        
        # Secure file permissions (owner read-write only)
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        
        self.fernet = Fernet(key)
        self.logger.info("Generated new encryption key")
    
    def create_password_hash(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """Create secure password hash using PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        hash_value = base64.b64encode(key).decode()
        salt_value = base64.b64encode(salt).decode()
        
        return hash_value, salt_value
    
    def verify_password(self, password: str, hash_value: str, salt_value: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt = base64.b64decode(salt_value.encode())
            expected_hash = base64.b64decode(hash_value.encode())
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            kdf.verify(password.encode(), expected_hash)
            return True
        except Exception:
            return False
    
    def create_default_admin(self) -> Dict[str, str]:
        """Create default admin user if none exists."""
        users_file = os.path.join(self.config_dir, "users.json")
        
        if os.path.exists(users_file):
            return {}
        
        # Generate secure random password
        temp_password = secrets.token_urlsafe(16)
        hash_value, salt_value = self.create_password_hash(temp_password)
        
        admin_user = {
            "username": "admin",
            "password_hash": hash_value,
            "salt": salt_value,
            "role": "administrator",
            "created": datetime.now().isoformat(),
            "last_login": None,
            "failed_attempts": 0,
            "locked_until": None,
            "allowed_ips": ["127.0.0.1", "::1", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
        }
        
        users_data = {"admin": admin_user}
        
        # Save encrypted user data
        encrypted_data = self.fernet.encrypt(json.dumps(users_data).encode())
        
        with open(users_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(users_file, 0o600)
        
        return {"username": "admin", "temp_password": temp_password}
    
    def load_users(self) -> Dict[str, Dict]:
        """Load user data from encrypted file."""
        users_file = os.path.join(self.config_dir, "users.json")
        
        if not os.path.exists(users_file):
            # Create default admin
            default_admin = self.create_default_admin()
            if default_admin:
                st.warning(f"⚠️ Default admin created. Username: {default_admin['username']}, Password: {default_admin['temp_password']}")
                st.info("Please change the default password immediately after login.")
        
        try:
            with open(users_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            self.logger.error(f"Failed to load users: {e}")
            return {}
    
    def save_users(self, users_data: Dict[str, Dict]):
        """Save user data to encrypted file."""
        users_file = os.path.join(self.config_dir, "users.json")
        
        try:
            encrypted_data = self.fernet.encrypt(json.dumps(users_data).encode())
            
            with open(users_file, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(users_file, 0o600)
            
        except Exception as e:
            self.logger.error(f"Failed to save users: {e}")
    
    def get_client_ip(self) -> str:
        """Get client IP address from Streamlit context."""
        # In a real deployment, this would get the actual client IP
        # For local development, return localhost
        return "127.0.0.1"
    
    def is_ip_allowed(self, username: str, client_ip: str) -> bool:
        """Check if client IP is allowed for user."""
        users_data = self.load_users()
        
        if username not in users_data:
            return False
        
        allowed_ips = users_data[username].get("allowed_ips", [])
        
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            
            for allowed in allowed_ips:
                try:
                    if '/' in allowed:
                        # CIDR notation
                        if client_ip_obj in ipaddress.ip_network(allowed, strict=False):
                            return True
                    else:
                        # Single IP
                        if client_ip_obj == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    continue
            
            return False
            
        except ValueError:
            return False
    
    def is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        users_data = self.load_users()
        
        if username not in users_data:
            return False
        
        user = users_data[username]
        locked_until = user.get("locked_until")
        
        if locked_until:
            if datetime.fromisoformat(locked_until) > datetime.now():
                return True
            else:
                # Unlock account
                user["locked_until"] = None
                user["failed_attempts"] = 0
                self.save_users(users_data)
        
        return False
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user credentials."""
        client_ip = self.get_client_ip()
        
        # Load users
        users_data = self.load_users()
        
        if username not in users_data:
            return False
        
        user = users_data[username]
        
        # Check IP restrictions
        if not self.is_ip_allowed(username, client_ip):
            self.logger.warning(f"Login attempt from unauthorized IP: {client_ip} for user: {username}")
            return False
        
        # Check account lockout
        if self.is_account_locked(username):
            return False
        
        # Verify password
        if self.verify_password(password, user["password_hash"], user["salt"]):
            # Successful login
            user["last_login"] = datetime.now().isoformat()
            user["failed_attempts"] = 0
            user["locked_until"] = None
            
            # Create session
            session_id = secrets.token_urlsafe(32)
            st.session_state.authenticated_users[session_id] = {
                "username": username,
                "role": user["role"],
                "login_time": datetime.now(),
                "last_activity": datetime.now(),
                "client_ip": client_ip
            }
            
            st.session_state.session_id = session_id
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.user_role = user["role"]
            
            self.save_users(users_data)
            self.logger.info(f"Successful login: {username} from {client_ip}")
            return True
        else:
            # Failed login
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1
            
            if user["failed_attempts"] >= self.max_login_attempts:
                # Lock account
                user["locked_until"] = (datetime.now() + timedelta(seconds=self.lockout_duration)).isoformat()
                self.logger.warning(f"Account locked: {username} after {user['failed_attempts']} failed attempts")
            
            self.save_users(users_data)
            self.logger.warning(f"Failed login attempt: {username} from {client_ip}")
            return False
    
    def logout_user(self):
        """Logout current user."""
        if hasattr(st.session_state, 'session_id') and st.session_state.session_id:
            # Remove session
            if st.session_state.session_id in st.session_state.authenticated_users:
                del st.session_state.authenticated_users[st.session_state.session_id]
            
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.session_id = None
            st.session_state.username = None
            st.session_state.user_role = None
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid."""
        if not hasattr(st.session_state, 'session_id') or not st.session_state.session_id:
            return False
        
        session_id = st.session_state.session_id
        
        if session_id not in st.session_state.authenticated_users:
            return False
        
        session = st.session_state.authenticated_users[session_id]
        
        # Check session timeout
        if datetime.now() - session["last_activity"] > timedelta(seconds=self.session_timeout):
            del st.session_state.authenticated_users[session_id]
            return False
        
        # Update last activity
        session["last_activity"] = datetime.now()
        return True
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        users_data = self.load_users()
        
        if username not in users_data:
            return False
        
        user = users_data[username]
        
        # Verify old password
        if not self.verify_password(old_password, user["password_hash"], user["salt"]):
            return False
        
        # Validate new password
        if not self.validate_password_strength(new_password):
            return False
        
        # Update password
        hash_value, salt_value = self.create_password_hash(new_password)
        user["password_hash"] = hash_value
        user["salt"] = salt_value
        user["password_changed"] = datetime.now().isoformat()
        
        self.save_users(users_data)
        self.logger.info(f"Password changed for user: {username}")
        return True
    
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength."""
        if len(password) < 8:
            return False
        
        # Must contain uppercase, lowercase, digit, and special character
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        
        return True
    
    def encrypt_credentials(self, credentials: Dict[str, str]) -> str:
        """Encrypt device credentials."""
        try:
            json_data = json.dumps(credentials)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt credentials: {e}")
            return ""
    
    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, str]:
        """Decrypt device credentials."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            self.logger.error(f"Failed to decrypt credentials: {e}")
            return {}
    
    def mask_sensitive_data(self, data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask sensitive data for logging."""
        if len(data) <= visible_chars:
            return mask_char * len(data)
        
        return data[:visible_chars] + mask_char * (len(data) - visible_chars)
    
    def sanitize_log_data(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize log data to remove sensitive information."""
        sensitive_keys = ['password', 'secret', 'key', 'token', 'credential', 'auth']
        sanitized = {}
        
        for key, value in log_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 50:
                # Potentially sensitive long strings
                sanitized[key] = self.mask_sensitive_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


def require_authentication(func):
    """Decorator to require authentication for Streamlit functions."""
    def wrapper(*args, **kwargs):
        security_manager = SecurityManager()
        
        if not security_manager.is_session_valid():
            render_login_page()
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def render_login_page():
    """Render secure login page."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 15px;
        margin: 50px auto;
        max-width: 400px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    ">
        <h1 style="margin: 0;">🔒 NetArchon Security</h1>
        <p style="margin: 20px 0 0 0; opacity: 0.9;">
            Secure Access Required
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    security_manager = SecurityManager()
    
    with st.form("login_form"):
        st.subheader("🔐 Login")
        
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            login_button = st.form_submit_button("🔓 Login", type="primary")
        
        with col2:
            if st.form_submit_button("❓ Need Help?"):
                st.info("""
                **Default Credentials:**
                - Username: admin
                - Password: [Generated on first run]
                
                **Security Features:**
                - Account lockout after 3 failed attempts
                - IP address restrictions
                - Session timeout (1 hour)
                - Encrypted credential storage
                """)
        
        if login_button:
            if username and password:
                # Check for account lockout
                if security_manager.is_account_locked(username):
                    st.error("🔒 Account is locked due to multiple failed login attempts. Please try again later.")
                else:
                    if security_manager.authenticate_user(username, password):
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials or unauthorized access")
            else:
                st.error("Please enter both username and password")
    
    # Security notices
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; opacity: 0.7; font-size: 0.8em;">
        <p><strong>🛡️ Security Notice:</strong></p>
        <p>This system monitors all access attempts and maintains audit logs.</p>
        <p>Unauthorized access is prohibited and may be reported.</p>
    </div>
    """, unsafe_allow_html=True)


def render_user_settings():
    """Render user settings and password change interface."""
    if not st.session_state.get('authenticated', False):
        st.error("Authentication required")
        return
    
    st.subheader("👤 User Settings")
    
    security_manager = SecurityManager()
    username = st.session_state.get('username', '')
    
    # User information
    st.markdown("### 📋 Account Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Username**: {username}")
        st.write(f"**Role**: {st.session_state.get('user_role', 'unknown')}")
    
    with col2:
        st.write(f"**Session Active**: ✅")
        st.write(f"**Client IP**: {security_manager.get_client_ip()}")
    
    # Password change
    st.markdown("### 🔑 Change Password")
    
    with st.form("change_password_form"):
        old_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("🔄 Change Password"):
            if not all([old_password, new_password, confirm_password]):
                st.error("All fields are required")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            elif not security_manager.validate_password_strength(new_password):
                st.error("""
                Password must be at least 8 characters and contain:
                - Uppercase letter
                - Lowercase letter  
                - Number
                - Special character
                """)
            else:
                if security_manager.change_password(username, old_password, new_password):
                    st.success("✅ Password changed successfully")
                else:
                    st.error("❌ Failed to change password. Check current password.")
    
    # Logout
    st.markdown("### 🚪 Session Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚪 Logout", type="secondary"):
            security_manager.logout_user()
            st.success("Logged out successfully")
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh Session"):
            st.success("Session refreshed")


def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    if 'security_manager' not in st.session_state:
        st.session_state.security_manager = SecurityManager()
    
    return st.session_state.security_manager