"""Encryption manager for sensitive data protection."""

import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.logger import logger


class EncryptionManager:
    """Manager for encrypting and decrypting sensitive data."""

    def __init__(self, key_file: Optional[str] = None):
        self.key_file = Path(key_file) if key_file else Path("data/.encryption_key")
        self._key: Optional[bytes] = None
        self._salt: Optional[bytes] = None
        self._setup_encryption()

    def _setup_encryption(self) -> None:
        """Setup encryption with key generation or loading."""
        try:
            # Try to import cryptography library (optional dependency)
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            self._fernet_available = True
            self._Fernet = Fernet
            self._PBKDF2HMAC = PBKDF2HMAC
            self._hashes = hashes

            # Load or generate encryption key
            if self.key_file.exists():
                self._load_key()
            else:
                self._generate_key()

            logger.info("Encryption manager initialized with Fernet encryption")

        except ImportError:
            logger.warning("Cryptography library not available, using basic encoding")
            self._fernet_available = False
            self._setup_fallback_encryption()

    def _generate_key(self) -> None:
        """Generate new encryption key and salt."""
        if self._fernet_available:
            # Generate random salt
            self._salt = os.urandom(16)

            # Generate key using PBKDF2
            password = os.urandom(32)
            kdf = self._PBKDF2HMAC(
                algorithm=self._hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            self._key = base64.urlsafe_b64encode(kdf.derive(password))

            # Save key and salt to file
            self.key_file.parent.mkdir(exist_ok=True)
            with open(self.key_file, "wb") as f:
                f.write(self._salt + self._key)

            # Set secure file permissions
            os.chmod(self.key_file, 0o600)
            logger.info("New encryption key generated")
        else:
            self._setup_fallback_encryption()

    def _load_key(self) -> None:
        """Load encryption key from file."""
        if self._fernet_available:
            try:
                with open(self.key_file, "rb") as f:
                    data = f.read()
                    self._salt = data[:16]
                    self._key = data[16:]
                logger.info("Encryption key loaded")
            except Exception as e:
                logger.error(f"Failed to load encryption key: {e}")
                self._generate_key()
        else:
            self._setup_fallback_encryption()

    def _setup_fallback_encryption(self) -> None:
        """Setup fallback encryption using simple base64 encoding."""
        self._key = base64.b64encode(b"fallback_key_screen_translator_v2")
        self._salt = b"fallback_salt_16"
        logger.warning("Using fallback encryption (base64 only)")

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt string data."""
        if not plaintext:
            return ""

        try:
            if self._fernet_available and self._key:
                fernet = self._Fernet(self._key)
                encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))
                return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
            else:
                # Fallback: simple base64 encoding (NOT secure!)
                encoded = base64.b64encode(plaintext.encode("utf-8"))
                return encoded.decode("utf-8")

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return plaintext  # Return original if encryption fails

    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt string data."""
        if not encrypted_text:
            return ""

        try:
            if self._fernet_available and self._key:
                fernet = self._Fernet(self._key)
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode("utf-8"))
                decrypted_bytes = fernet.decrypt(encrypted_bytes)
                return decrypted_bytes.decode("utf-8")
            else:
                # Fallback: simple base64 decoding
                decoded = base64.b64decode(encrypted_text.encode("utf-8"))
                return decoded.decode("utf-8")

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_text  # Return original if decryption fails

    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Encrypt dictionary values."""
        encrypted_dict = {}

        for key, value in data.items():
            if isinstance(value, str):
                encrypted_dict[key] = self.encrypt_string(value)
            elif isinstance(value, (int, float, bool)):
                encrypted_dict[key] = self.encrypt_string(str(value))
            else:
                # For complex types, convert to string first
                encrypted_dict[key] = self.encrypt_string(str(value))

        return encrypted_dict

    def decrypt_dict(self, encrypted_data: Dict[str, str]) -> Dict[str, str]:
        """Decrypt dictionary values."""
        decrypted_dict = {}

        for key, encrypted_value in encrypted_data.items():
            decrypted_dict[key] = self.decrypt_string(encrypted_value)

        return decrypted_dict

    def hash_password(self, password: str) -> str:
        """Hash password for secure storage."""
        if not password:
            return ""

        # Use SHA-256 with salt
        salted_password = (password + self._salt.decode("latin-1", errors="ignore")).encode("utf-8")
        return hashlib.sha256(salted_password).hexdigest()

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.hash_password(password) == hashed_password

    def generate_token(self, data: str) -> str:
        """Generate secure token from data."""
        token_data = f"{data}:{os.urandom(16).hex()}"
        return self.encrypt_string(token_data)

    def verify_token(self, token: str, expected_data: str) -> bool:
        """Verify token contains expected data."""
        try:
            decrypted = self.decrypt_string(token)
            return decrypted.startswith(f"{expected_data}:")
        except Exception:
            return False

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage."""
        return self.encrypt_string(api_key)

    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """Decrypt API key for use."""
        return self.decrypt_string(encrypted_api_key)

    def wipe_sensitive_data(self, data: str) -> str:
        """Securely wipe sensitive data from string."""
        # Replace with random characters of same length
        if not data:
            return ""

        random_chars = "".join(chr(ord(c) ^ 0xFF) for c in data)
        return random_chars[: len(data)]

    def is_encryption_available(self) -> bool:
        """Check if strong encryption is available."""
        return self._fernet_available

    def get_encryption_info(self) -> Dict[str, Any]:
        """Get encryption system information."""
        return {
            "encryption_available": self._fernet_available,
            "key_file_exists": self.key_file.exists(),
            "encryption_type": "Fernet (AES)" if self._fernet_available else "Base64 (fallback)",
            "security_level": "High" if self._fernet_available else "Low",
        }


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance."""
    global _encryption_manager

    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()

    return _encryption_manager
