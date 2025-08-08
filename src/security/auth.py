"""
Basic authentication manager for application security.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set

from src.security.audit import SecurityEventType, get_audit_logger
from src.security.encryption import get_encryption_manager
from src.utils.logger import logger


class AuthLevel(Enum):
    """Authentication levels."""

    NONE = "none"
    BASIC = "basic"
    ELEVATED = "elevated"
    ADMIN = "admin"


@dataclass
class AuthToken:
    """Authentication token."""

    token_id: str
    user_id: str
    issued_at: float
    expires_at: float
    auth_level: AuthLevel = AuthLevel.BASIC

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return time.time() < self.expires_at


@dataclass
class UserSession:
    """User session information."""

    user_id: str
    session_id: str
    created_at: float
    last_accessed: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True

    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session is expired."""
        return (time.time() - self.last_accessed) > timeout_seconds

    def refresh(self) -> None:
        """Refresh session access time."""
        self.last_accessed = time.time()


@dataclass
class APIKey:
    """API key information."""

    key_id: str
    key_hash: str  # Hashed version of the actual key
    name: str
    created_at: float
    last_used: Optional[float] = None
    usage_count: int = 0
    is_active: bool = True
    permissions: Optional[Set[str]] = None
    expires_at: Optional[float] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()

    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def has_permission(self, permission: str) -> bool:
        """Check if API key has specific permission."""
        return permission in self.permissions or "admin" in self.permissions


class AuthenticationManager:
    """Basic authentication manager for Screen Translator."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Session management
        self.active_sessions: Dict[str, UserSession] = {}
        self.session_timeout = 3600  # 1 hour default

        # API key management
        self.api_keys: Dict[str, APIKey] = {}
        self.api_keys_file = self.data_dir / "api_keys.json"

        # Simple user storage (for demo purposes)
        self.users: Dict[str, Dict] = {}
        self.users_file = self.data_dir / "users.json"

        # Security settings
        self.max_login_attempts = 5
        self.login_attempt_window = 300  # 5 minutes
        self.login_attempts: Dict[str, list] = {}  # ip -> [timestamps]

        # Load existing data
        self._load_users()
        self._load_api_keys()

        # Get dependencies
        self.encryption_manager = get_encryption_manager()
        self.audit_logger = get_audit_logger()

        # Create default admin user if none exists
        if not self.users:
            self._create_default_admin()

        logger.info("Authentication manager initialized")

    def _create_default_admin(self) -> None:
        """Create default admin user."""
        admin_password = secrets.token_urlsafe(16)

        self.create_user(
            user_id="admin",
            password=admin_password,
            permissions={"admin", "api_access", "config_change"},
        )

        logger.warning(f"Default admin user created with password: {admin_password}")
        logger.warning("Please change the admin password immediately!")

        # Also create an API key for the admin
        api_key = self.create_api_key("admin", "Default Admin Key", {"admin"})
        logger.warning(f"Default admin API key created: {api_key}")

    def create_user(
        self, user_id: str, password: str, permissions: Optional[Set[str]] = None
    ) -> bool:
        """Create a new user."""
        if user_id in self.users:
            logger.warning(f"User already exists: {user_id}")
            return False

        if permissions is None:
            permissions = {"basic_access"}

        # Hash password
        password_hash = self._hash_password(password)

        # Create user
        user_data = {
            "user_id": user_id,
            "password_hash": password_hash,
            "permissions": list(permissions),
            "created_at": time.time(),
            "last_login": None,
            "login_count": 0,
            "is_active": True,
        }

        self.users[user_id] = user_data
        self._save_users()

        # Log audit event
        self.audit_logger.log_event(
            self.audit_logger.SecurityEvent(
                event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
                description=f"User created: {user_id}",
                user_id=user_id,
                metadata={"permissions": list(permissions)},
            )
        )

        logger.info(f"User created: {user_id}")
        return True

    def authenticate_user(
        self, user_id: str, password: str, ip_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Authenticate user and create session.
        Returns session_id if successful, None if failed.
        """
        # Check for too many login attempts
        if self._is_login_rate_limited(ip_address):
            self.audit_logger.log_authentication(False, user_id, ip_address)
            return None

        # Check user exists and is active
        user = self.users.get(user_id)
        if not user or not user["is_active"]:
            self._record_login_attempt(ip_address)
            self.audit_logger.log_authentication(False, user_id, ip_address)
            return None

        # Verify password
        if not self._verify_password(password, user["password_hash"]):
            self._record_login_attempt(ip_address)
            self.audit_logger.log_authentication(False, user_id, ip_address)
            return None

        # Create session
        session_id = self._generate_session_id()
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            created_at=time.time(),
            last_accessed=time.time(),
            ip_address=ip_address,
        )

        self.active_sessions[session_id] = session

        # Update user stats
        user["last_login"] = time.time()
        user["login_count"] += 1
        self._save_users()

        # Clear login attempts for this IP
        if ip_address and ip_address in self.login_attempts:
            del self.login_attempts[ip_address]

        # Log successful authentication
        self.audit_logger.log_authentication(True, user_id, ip_address)

        logger.info(f"User authenticated: {user_id}")
        return session_id

    def validate_session(self, session_id: str) -> Optional[UserSession]:
        """Validate session and return session info if valid."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        if session.is_expired(self.session_timeout):
            self.logout_session(session_id)
            return None

        # Refresh session
        session.refresh()
        return session

    def logout_session(self, session_id: str) -> bool:
        """Logout session."""
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        # Log logout
        self.audit_logger.log_event(
            self.audit_logger.SecurityEvent(
                event_type=SecurityEventType.AUTH_LOGOUT,
                description="User logged out",
                user_id=session.user_id,
                session_id=session_id,
            )
        )

        del self.active_sessions[session_id]
        logger.info(f"Session logged out: {session_id}")
        return True

    def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[Set[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Create API key for user."""
        if user_id not in self.users:
            raise ValueError(f"User not found: {user_id}")

        if permissions is None:
            permissions = {"api_access"}

        # Generate API key
        api_key = f"st_{secrets.token_urlsafe(32)}"
        key_id = secrets.token_urlsafe(16)
        key_hash = self._hash_api_key(api_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 24 * 3600)

        # Create API key record
        api_key_record = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=time.time(),
            permissions=permissions,
            expires_at=expires_at,
        )

        self.api_keys[key_id] = api_key_record
        self._save_api_keys()

        # Log API key creation
        self.audit_logger.log_event(
            self.audit_logger.SecurityEvent(
                event_type=SecurityEventType.API_KEY_CREATED,
                description=f"API key created: {name}",
                user_id=user_id,
                metadata={"key_id": key_id, "permissions": list(permissions)},
            )
        )

        logger.info(f"API key created for {user_id}: {name}")
        return api_key  # Return the actual key only once

    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key and return key info if valid."""
        key_hash = self._hash_api_key(api_key)

        for key_record in self.api_keys.values():
            if key_record.key_hash == key_hash:
                if not key_record.is_active or key_record.is_expired():
                    return None

                # Update usage stats
                key_record.last_used = time.time()
                key_record.usage_count += 1
                self._save_api_keys()

                # Log API key usage
                self.audit_logger.log_api_access(key_record.key_id, "api_call", True)

                return key_record

        return None

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        if key_id not in self.api_keys:
            return False

        self.api_keys[key_id].is_active = False
        self._save_api_keys()

        # Log API key revocation
        self.audit_logger.log_event(
            self.audit_logger.SecurityEvent(
                event_type=SecurityEventType.API_KEY_REVOKED,
                description=f"API key revoked: {key_id}",
                metadata={"key_id": key_id},
            )
        )

        logger.info(f"API key revoked: {key_id}")
        return True

    def change_user_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.users.get(user_id)
        if not user or not user["is_active"]:
            return False

        # Verify old password
        if not self._verify_password(old_password, user["password_hash"]):
            return False

        # Hash new password
        new_password_hash = self._hash_password(new_password)
        user["password_hash"] = new_password_hash
        self._save_users()

        # Log password change
        self.audit_logger.log_event(
            self.audit_logger.SecurityEvent(
                event_type=SecurityEventType.CONFIG_CHANGE,
                description="Password changed",
                user_id=user_id,
                resource="password",
            )
        )

        logger.info(f"Password changed for user: {user_id}")
        return True

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${password_hash}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, password_hash = stored_hash.split("$", 1)
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return computed_hash == password_hash
        except ValueError:
            return False

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)

    def _is_login_rate_limited(self, ip_address: str) -> bool:
        """Check if IP is rate limited for login attempts."""
        if not ip_address:
            return False

        attempts = self.login_attempts.get(ip_address, [])
        current_time = time.time()

        # Remove old attempts
        recent_attempts = [
            timestamp
            for timestamp in attempts
            if current_time - timestamp < self.login_attempt_window
        ]

        self.login_attempts[ip_address] = recent_attempts
        return len(recent_attempts) >= self.max_login_attempts

    def _record_login_attempt(self, ip_address: str) -> None:
        """Record failed login attempt."""
        if not ip_address:
            return

        if ip_address not in self.login_attempts:
            self.login_attempts[ip_address] = []

        self.login_attempts[ip_address].append(time.time())

    def _load_users(self) -> None:
        """Load users from file."""
        if not self.users_file.exists():
            return

        try:
            import json

            with open(self.users_file, "r", encoding="utf-8") as f:
                encrypted_data = json.load(f)
                decrypted_data = self.encryption_manager.decrypt_dict(encrypted_data)
                self.users = json.loads(decrypted_data.get("users", "{}"))
            logger.info("Users loaded from file")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")

    def _save_users(self) -> None:
        """Save users to file."""
        try:
            import json

            data_to_encrypt = {"users": json.dumps(self.users)}
            encrypted_data = self.encryption_manager.encrypt_dict(data_to_encrypt)

            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save users: {e}")

    def _load_api_keys(self) -> None:
        """Load API keys from file."""
        if not self.api_keys_file.exists():
            return

        try:
            import json

            with open(self.api_keys_file, "r", encoding="utf-8") as f:
                encrypted_data = json.load(f)
                decrypted_data = self.encryption_manager.decrypt_dict(encrypted_data)
                api_keys_data = json.loads(decrypted_data.get("api_keys", "{}"))

                # Convert to APIKey objects
                for key_id, key_data in api_keys_data.items():
                    self.api_keys[key_id] = APIKey(
                        key_id=key_data["key_id"],
                        key_hash=key_data["key_hash"],
                        name=key_data["name"],
                        created_at=key_data["created_at"],
                        last_used=key_data.get("last_used"),
                        usage_count=key_data.get("usage_count", 0),
                        is_active=key_data.get("is_active", True),
                        permissions=set(key_data.get("permissions", [])),
                        expires_at=key_data.get("expires_at"),
                    )
            logger.info("API keys loaded from file")
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")

    def _save_api_keys(self) -> None:
        """Save API keys to file."""
        try:
            import json

            api_keys_data = {}

            for key_id, key_record in self.api_keys.items():
                api_keys_data[key_id] = {
                    "key_id": key_record.key_id,
                    "key_hash": key_record.key_hash,
                    "name": key_record.name,
                    "created_at": key_record.created_at,
                    "last_used": key_record.last_used,
                    "usage_count": key_record.usage_count,
                    "is_active": key_record.is_active,
                    "permissions": list(key_record.permissions),
                    "expires_at": key_record.expires_at,
                }

            data_to_encrypt = {"api_keys": json.dumps(api_keys_data)}
            encrypted_data = self.encryption_manager.encrypt_dict(data_to_encrypt)

            with open(self.api_keys_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns number of sessions cleaned."""
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            if session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def get_auth_stats(self) -> Dict[str, any]:
        """Get authentication statistics."""
        active_sessions_count = len(self.active_sessions)
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u["is_active"]])
        total_api_keys = len(self.api_keys)
        active_api_keys = len([k for k in self.api_keys.values() if k.is_active])

        return {
            "active_sessions": active_sessions_count,
            "total_users": total_users,
            "active_users": active_users,
            "total_api_keys": total_api_keys,
            "active_api_keys": active_api_keys,
            "session_timeout_seconds": self.session_timeout,
            "max_login_attempts": self.max_login_attempts,
            "login_attempt_window_seconds": self.login_attempt_window,
        }


# Global authentication manager instance
_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager instance."""
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = AuthenticationManager()

    return _auth_manager


# Aliases for backwards compatibility
AuthManager = AuthenticationManager
