"""
Comprehensive tests for Security components (encryption, audit, rate limiting, etc.).
"""

import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from src.security.audit import AuditLogger, SecurityEvent, SecurityLevel
from src.security.auth import AuthLevel, AuthManager, AuthToken
from src.security.encryption import EncryptionManager
from src.security.rate_limiter import RateLimiter, RateLimitExceeded
from src.security.sanitizer import DataSanitizer, SanitizationLevel


class TestEncryptionManager:
    """Test EncryptionManager class"""

    @pytest.fixture
    def encryption_manager(self):
        """Create encryption manager with test key file"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_key_file:
            temp_key_file.close()
            manager = EncryptionManager(key_file=temp_key_file.name)
            yield manager
            # Cleanup
            if os.path.exists(temp_key_file.name):
                os.unlink(temp_key_file.name)

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            encrypted_file = Path(temp_dir) / "test.enc"
            decrypted_file = Path(temp_dir) / "test_decrypted.txt"

            yield {
                "test_file": test_file,
                "encrypted_file": encrypted_file,
                "decrypted_file": decrypted_file,
            }

    def test_encryption_manager_initialization(self):
        """Test encryption manager initialization"""
        # With default key file
        manager = EncryptionManager()
        manager = EncryptionManager(encryption_key=test_key)
        assert manager.encryption_key == test_key

        # With generated key
        manager2 = EncryptionManager()
        assert manager2.encryption_key is not None
        assert len(manager2.encryption_key) == 32

    def test_string_encryption_decryption(self, encryption_manager):
        """Test string encryption and decryption"""
        original_text = "This is a secret message with special chars: äöü@#$%"

        # Encrypt
        encrypted = encryption_manager.encrypt_string(original_text)

        assert encrypted != original_text
        assert len(encrypted) > len(original_text)
        assert isinstance(encrypted, str)

        # Decrypt
        decrypted = encryption_manager.decrypt_string(encrypted)
        assert decrypted == original_text

    def test_string_encryption_empty_string(self, encryption_manager):
        """Test encryption of empty string"""
        empty_text = ""

        encrypted = encryption_manager.encrypt_string(empty_text)
        assert encrypted != empty_text

        decrypted = encryption_manager.decrypt_string(encrypted)
        assert decrypted == empty_text

    def test_string_encryption_unicode(self, encryption_manager):
        """Test encryption of unicode strings"""
        unicode_text = "Hello 世界 🌍 Привет мир"

        encrypted = encryption_manager.encrypt_string(unicode_text)
        decrypted = encryption_manager.decrypt_string(encrypted)

        assert decrypted == unicode_text

    def test_api_key_encryption(self, encryption_manager):
        """Test API key encryption with additional security"""
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"

        encrypted_key = encryption_manager.encrypt_api_key(api_key)
        assert encrypted_key != api_key
        assert len(encrypted_key) > len(api_key)

        decrypted_key = encryption_manager.decrypt_api_key(encrypted_key)
        assert decrypted_key == api_key

    def test_file_encryption_decryption(self, encryption_manager, temp_files):
        """Test file encryption and decryption"""
        test_content = "This is test file content\\nWith multiple lines\\nAnd special chars: äöü"

        # Create test file
        temp_files["test_file"].write_text(test_content, encoding="utf-8")

        # Encrypt file
        encryption_manager.encrypt_file(
            str(temp_files["test_file"]), str(temp_files["encrypted_file"])
        )

        assert temp_files["encrypted_file"].exists()

        # Encrypted content should be different
        encrypted_content = temp_files["encrypted_file"].read_bytes()
        assert encrypted_content != test_content.encode("utf-8")

        # Decrypt file
        encryption_manager.decrypt_file(
            str(temp_files["encrypted_file"]), str(temp_files["decrypted_file"])
        )

        # Decrypted content should match original
        decrypted_content = temp_files["decrypted_file"].read_text(encoding="utf-8")
        assert decrypted_content == test_content

    def test_file_encryption_binary(self, encryption_manager, temp_files):
        """Test encryption of binary files"""
        binary_content = b"\\x00\\x01\\x02\\x03\\xFF\\xFE\\xFD"

        # Create binary test file
        temp_files["test_file"].write_bytes(binary_content)

        # Encrypt and decrypt
        encryption_manager.encrypt_file(
            str(temp_files["test_file"]), str(temp_files["encrypted_file"])
        )

        encryption_manager.decrypt_file(
            str(temp_files["encrypted_file"]), str(temp_files["decrypted_file"])
        )

        # Check binary content preserved
        decrypted_content = temp_files["decrypted_file"].read_bytes()
        assert decrypted_content == binary_content

    def test_encryption_key_derivation(self, encryption_manager):
        """Test key derivation from password"""
        password = "test_password_123"
        salt = b"test_salt_16bytes"

        derived_key = encryption_manager.derive_key_from_password(password, salt)

        assert len(derived_key) == 32  # 256 bits
        assert isinstance(derived_key, bytes)

        # Same password and salt should produce same key
        derived_key2 = encryption_manager.derive_key_from_password(password, salt)
        assert derived_key == derived_key2

        # Different salt should produce different key
        different_salt = b"different_salt16"
        derived_key3 = encryption_manager.derive_key_from_password(password, different_salt)
        assert derived_key != derived_key3

    def test_secure_key_storage(self, encryption_manager):
        """Test secure key storage and retrieval"""
        key_id = "test_api_key"
        api_key = "secret_api_key_value"

        # Store key securely
        stored_key_data = encryption_manager.store_key_securely(key_id, api_key)
        assert stored_key_data != api_key

        # Retrieve key
        retrieved_key = encryption_manager.retrieve_key_securely(key_id, stored_key_data)
        assert retrieved_key == api_key

    def test_encryption_integrity(self, encryption_manager):
        """Test encryption integrity verification"""
        original_text = "Important data that must not be tampered with"

        # Encrypt with integrity check
        encrypted_with_hmac = encryption_manager.encrypt_with_integrity(original_text)

        # Verify and decrypt
        decrypted_text = encryption_manager.decrypt_with_integrity(encrypted_with_hmac)
        assert decrypted_text == original_text

        # Test tampered data
        tampered_data = encrypted_with_hmac[:-10] + b"tampered!!"

        with pytest.raises(ValueError, match="integrity"):
            encryption_manager.decrypt_with_integrity(tampered_data)

    def test_encryption_error_handling(self, encryption_manager):
        """Test encryption error handling"""
        # Invalid encrypted data
        with pytest.raises(ValueError):
            encryption_manager.decrypt_string("invalid_encrypted_data")

        # File not found
        with pytest.raises(FileNotFoundError):
            encryption_manager.encrypt_file("/nonexistent/file.txt", "/tmp/output.enc")

        # Invalid key format
        with pytest.raises(ValueError):
            EncryptionManager(encryption_key=b"too_short_key")


class TestAuditLogger:
    """Test AuditLogger class"""

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger with temporary file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as temp_file:
            logger = AuditLogger(log_file=temp_file.name)
            yield logger
            # Cleanup
            try:
                os.unlink(temp_file.name)
            except:
                pass

    def test_audit_logger_initialization(self, audit_logger):
        """Test audit logger initialization"""
        assert audit_logger.log_file is not None
        assert os.path.exists(audit_logger.log_file)

    def test_authentication_logging(self, audit_logger):
        """Test authentication event logging"""
        audit_logger.log_authentication(
            success=True,
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
        )

        # Read log file
        with open(audit_logger.log_file, "r") as f:
            log_content = f.read()

        # Parse JSON log entry
        log_lines = [line for line in log_content.strip().split("\\n") if line]
        assert len(log_lines) >= 1

        log_entry = json.loads(log_lines[-1])

        assert log_entry["event_type"] == "authentication"
        assert log_entry["success"] == True
        assert log_entry["user_id"] == "test_user"
        assert log_entry["ip_address"] == "192.168.1.100"
        assert log_entry["user_agent"] == "TestAgent/1.0"
        assert "timestamp" in log_entry
        assert "event_id" in log_entry

    def test_data_access_logging(self, audit_logger):
        """Test data access event logging"""
        audit_logger.log_data_access(
            resource="translation_history",
            action="read",
            user_id="test_user",
            record_count=15,
            filters={"language": "en-es"},
        )

        with open(audit_logger.log_file, "r") as f:
            log_content = f.read()

        log_entry = json.loads(log_content.strip().split("\\n")[-1])

        assert log_entry["event_type"] == "data_access"
        assert log_entry["resource"] == "translation_history"
        assert log_entry["action"] == "read"
        assert log_entry["user_id"] == "test_user"
        assert log_entry["record_count"] == 15
        assert log_entry["filters"] == {"language": "en-es"}

    def test_system_event_logging(self, audit_logger):
        """Test system event logging"""
        audit_logger.log_system_event(
            event="application_start",
            level=SecurityLevel.INFO,
            details={"version": "2.0", "config_file": "/path/to/config.json", "startup_time": 2.5},
        )

        with open(audit_logger.log_file, "r") as f:
            log_content = f.read()

        log_entry = json.loads(log_content.strip().split("\\n")[-1])

        assert log_entry["event_type"] == "system_event"
        assert log_entry["event"] == "application_start"
        assert log_entry["level"] == "INFO"
        assert log_entry["details"]["version"] == "2.0"

    def test_security_event_logging(self, audit_logger):
        """Test security event logging"""
        audit_logger.log_security_event(
            event="suspicious_activity",
            level=SecurityLevel.WARNING,
            user_id="suspicious_user",
            ip_address="10.0.0.1",
            details={"attempts": 5, "time_window": "1 minute", "blocked": True},
        )

        with open(audit_logger.log_file, "r") as f:
            log_content = f.read()

        log_entry = json.loads(log_content.strip().split("\\n")[-1])

        assert log_entry["event_type"] == "security_event"
        assert log_entry["event"] == "suspicious_activity"
        assert log_entry["level"] == "WARNING"
        assert log_entry["user_id"] == "suspicious_user"
        assert log_entry["details"]["blocked"] == True

    def test_audit_event_class(self):
        """Test SecurityEvent data class"""
        event = SecurityEvent(
            event_type="test_event",
            level=SecurityLevel.INFO,
            user_id="test_user",
            details={"key": "value"},
        )

        assert event.event_type == "test_event"
        assert event.level == SecurityLevel.INFO
        assert event.user_id == "test_user"
        assert event.details == {"key": "value"}
        assert isinstance(event.timestamp, datetime)
        assert event.event_id.startswith("audit_")

    def test_audit_level_enum(self):
        """Test SecurityLevel enum"""
        assert SecurityLevel.DEBUG.value == "DEBUG"
        assert SecurityLevel.INFO.value == "INFO"
        assert SecurityLevel.WARNING.value == "WARNING"
        assert SecurityLevel.ERROR.value == "ERROR"
        assert SecurityLevel.CRITICAL.value == "CRITICAL"

    def test_audit_log_rotation(self, audit_logger):
        """Test audit log rotation"""
        # Set small max file size for testing
        audit_logger.max_file_size = 1024  # 1KB

        # Generate enough log entries to trigger rotation
        for i in range(100):
            audit_logger.log_system_event(
                event=f"test_event_{i}",
                level=SecurityLevel.INFO,
                details={"data": "x" * 50},  # Some bulk data
            )

        # Check if rotation occurred (backup files created)
        backup_files = [
            f
            for f in os.listdir(os.path.dirname(audit_logger.log_file))
            if f.startswith(os.path.basename(audit_logger.log_file)) and f.endswith(".bak")
        ]

        assert len(backup_files) > 0  # At least one backup should exist

    def test_audit_log_filtering(self, audit_logger):
        """Test audit log filtering by level"""
        # Set minimum level to WARNING
        audit_logger.min_level = SecurityLevel.WARNING

        # Log events at different levels
        audit_logger.log_system_event("debug_event", SecurityLevel.DEBUG)
        audit_logger.log_system_event("info_event", SecurityLevel.INFO)
        audit_logger.log_system_event("warning_event", SecurityLevel.WARNING)
        audit_logger.log_system_event("error_event", SecurityLevel.ERROR)

        with open(audit_logger.log_file, "r") as f:
            log_content = f.read()

        log_lines = [line for line in log_content.strip().split("\\n") if line]

        # Only WARNING and ERROR events should be logged
        assert len(log_lines) == 2

        log_entries = [json.loads(line) for line in log_lines]
        assert log_entries[0]["event"] == "warning_event"
        assert log_entries[1]["event"] == "error_event"


class TestRateLimiter:
    """Test RateLimiter class"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        return RateLimiter(max_requests=5, time_window=60, burst_limit=3)  # 1 minute

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization"""
        assert rate_limiter.max_requests == 5
        assert rate_limiter.time_window == 60
        assert rate_limiter.burst_limit == 3

    def test_rate_limiting_allow(self, rate_limiter):
        """Test rate limiting allows requests within limit"""
        client_id = "test_client"

        # Should allow up to max_requests
        for i in range(5):
            assert rate_limiter.is_allowed(client_id) == True

        # 6th request should be denied
        assert rate_limiter.is_allowed(client_id) == False

    def test_rate_limiting_time_window(self, rate_limiter):
        """Test rate limiting time window reset"""
        client_id = "test_client"

        # Use up the limit
        for i in range(5):
            rate_limiter.is_allowed(client_id)

        # Should be denied
        assert rate_limiter.is_allowed(client_id) == False

        # Mock time advancement
        with patch("time.time", return_value=time.time() + 61):  # Advance past window
            # Should be allowed again
            assert rate_limiter.is_allowed(client_id) == True

    def test_rate_limiting_burst_limit(self, rate_limiter):
        """Test burst limit functionality"""
        client_id = "test_client"

        # Burst limit should allow quick succession up to burst_limit
        burst_start = time.time()
        burst_requests = 0

        for i in range(10):
            if rate_limiter.is_allowed(client_id, check_burst=True):
                burst_requests += 1
            else:
                break

        # Should allow up to burst_limit in quick succession
        assert burst_requests <= rate_limiter.burst_limit

    def test_rate_limiting_per_client(self, rate_limiter):
        """Test rate limiting is per-client"""
        client1 = "client_1"
        client2 = "client_2"

        # Use up limit for client1
        for i in range(5):
            rate_limiter.is_allowed(client1)

        # client1 should be denied
        assert rate_limiter.is_allowed(client1) == False

        # client2 should still be allowed
        assert rate_limiter.is_allowed(client2) == True

    def test_rate_limiting_exception(self, rate_limiter):
        """Test RateLimitExceeded exception"""
        client_id = "test_client"

        # Use up the limit
        for i in range(5):
            rate_limiter.check_rate_limit(client_id)

        # Should raise exception
        with pytest.raises(RateLimitExceeded) as exc_info:
            rate_limiter.check_rate_limit(client_id)

        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.client_id == client_id
        assert exc_info.value.retry_after > 0

    def test_rate_limiting_reset(self, rate_limiter):
        """Test rate limiting reset functionality"""
        client_id = "test_client"

        # Use up the limit
        for i in range(5):
            rate_limiter.is_allowed(client_id)

        assert rate_limiter.is_allowed(client_id) == False

        # Reset for client
        rate_limiter.reset_client(client_id)

        # Should be allowed again
        assert rate_limiter.is_allowed(client_id) == True

    def test_rate_limiting_statistics(self, rate_limiter):
        """Test rate limiting statistics"""
        client_id = "test_client"

        # Make some requests
        for i in range(3):
            rate_limiter.is_allowed(client_id)

        stats = rate_limiter.get_statistics(client_id)

        assert stats["requests_made"] == 3
        assert stats["requests_remaining"] == 2
        assert stats["reset_time"] > time.time()
        assert "burst_tokens" in stats


class TestDataSanitizer:
    """Test DataSanitizer class"""

    @pytest.fixture
    def sanitizer(self):
        """Create data sanitizer for testing"""
        return DataSanitizer()

    def test_email_sanitization(self, sanitizer):
        """Test email sanitization"""
        text_with_emails = "Contact us at support@example.com or admin@test.org"

        sanitized = sanitizer.sanitize_emails(text_with_emails)

        assert "support@example.com" not in sanitized
        assert "admin@test.org" not in sanitized
        assert "[EMAIL]" in sanitized or "***" in sanitized

    def test_phone_sanitization(self, sanitizer):
        """Test phone number sanitization"""
        text_with_phones = "Call us at +1-555-123-4567 or (555) 987-6543"

        sanitized = sanitizer.sanitize_phone_numbers(text_with_phones)

        assert "555-123-4567" not in sanitized
        assert "987-6543" not in sanitized
        assert "[PHONE]" in sanitized or "***" in sanitized

    def test_credit_card_sanitization(self, sanitizer):
        """Test credit card sanitization"""
        text_with_cc = "My card number is 4532-1234-5678-9012"

        sanitized = sanitizer.sanitize_credit_cards(text_with_cc)

        assert "4532-1234-5678-9012" not in sanitized
        assert "[CREDIT_CARD]" in sanitized or "****-****-****-9012" in sanitized

    def test_ssn_sanitization(self, sanitizer):
        """Test SSN sanitization"""
        text_with_ssn = "My SSN is 123-45-6789"

        sanitized = sanitizer.sanitize_ssn(text_with_ssn)

        assert "123-45-6789" not in sanitized
        assert "[SSN]" in sanitized or "***-**-6789" in sanitized

    def test_ip_address_sanitization(self, sanitizer):
        """Test IP address sanitization"""
        text_with_ip = "Server IP is 192.168.1.100 and external is 203.0.113.1"

        sanitized = sanitizer.sanitize_ip_addresses(text_with_ip)

        assert "192.168.1.100" not in sanitized
        assert "203.0.113.1" not in sanitized
        assert "[IP]" in sanitized or "192.168.1.***" in sanitized

    def test_comprehensive_sanitization(self, sanitizer):
        """Test comprehensive sanitization with multiple PII types"""
        sensitive_text = """
        Contact John Doe at john.doe@company.com or call (555) 123-4567.
        His SSN is 123-45-6789 and credit card 4532-1234-5678-9012.
        Server logs from 192.168.1.100 show the issue.
        """

        sanitized = sanitizer.sanitize_all(sensitive_text, level=SanitizationLevel.STRICT)

        # All sensitive data should be removed/masked
        assert "john.doe@company.com" not in sanitized
        assert "(555) 123-4567" not in sanitized
        assert "123-45-6789" not in sanitized
        assert "4532-1234-5678-9012" not in sanitized
        assert "192.168.1.100" not in sanitized

        # Structure should be preserved
        assert "Contact" in sanitized
        assert "Server logs" in sanitized

    def test_sanitization_levels(self, sanitizer):
        """Test different sanitization levels"""
        text = "Email me at test@example.com"

        # Minimal - might keep partial info
        minimal = sanitizer.sanitize_all(text, level=SanitizationLevel.MINIMAL)

        # Standard - balanced approach
        standard = sanitizer.sanitize_all(text, level=SanitizationLevel.STANDARD)

        # Strict - maximum sanitization
        strict = sanitizer.sanitize_all(text, level=SanitizationLevel.STRICT)

        # Strict should be most sanitized
        assert len(strict) <= len(standard) <= len(minimal)

    def test_custom_patterns(self, sanitizer):
        """Test custom sanitization patterns"""
        # Add custom pattern for employee IDs
        employee_pattern = r"EMP\\d{6}"
        sanitizer.add_custom_pattern("employee_id", employee_pattern, "[EMPLOYEE_ID]")

        text = "Employee EMP123456 needs access"
        sanitized = sanitizer.sanitize_all(text)

        assert "EMP123456" not in sanitized
        assert "[EMPLOYEE_ID]" in sanitized

    def test_whitelist_functionality(self, sanitizer):
        """Test whitelist functionality"""
        # Add email to whitelist
        sanitizer.add_to_whitelist("public@example.com")

        text = "Contact public@example.com or private@secret.com"
        sanitized = sanitizer.sanitize_emails(text)

        # Whitelisted email should remain
        assert "public@example.com" in sanitized

        # Non-whitelisted should be sanitized
        assert "private@secret.com" not in sanitized


class TestAuthManager:
    """Test AuthManager class"""

    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing"""
        return AuthManager(secret_key="test_secret_key_12345")

    def test_auth_manager_initialization(self, auth_manager):
        """Test auth manager initialization"""
        assert auth_manager.secret_key == "test_secret_key_12345"
        assert auth_manager.token_expiry == 3600  # Default 1 hour

    def test_token_generation(self, auth_manager):
        """Test authentication token generation"""
        user_id = "test_user"
        auth_level = AuthLevel.USER

        token = auth_manager.generate_token(user_id, auth_level)

        assert isinstance(token, AuthToken)
        assert token.user_id == user_id
        assert token.auth_level == auth_level
        assert isinstance(token.token_value, str)
        assert len(token.token_value) > 0
        assert token.expires_at > datetime.now()

    def test_token_validation(self, auth_manager):
        """Test token validation"""
        user_id = "test_user"
        auth_level = AuthLevel.USER

        # Generate token
        token = auth_manager.generate_token(user_id, auth_level)

        # Validate token
        is_valid = auth_manager.validate_token(token.token_value)
        assert is_valid == True

        # Test invalid token
        invalid_is_valid = auth_manager.validate_token("invalid_token")
        assert invalid_is_valid == False

    def test_token_expiration(self, auth_manager):
        """Test token expiration"""
        user_id = "test_user"
        auth_level = AuthLevel.USER

        # Generate token with short expiry
        auth_manager.token_expiry = 1  # 1 second
        token = auth_manager.generate_token(user_id, auth_level)

        # Should be valid immediately
        assert auth_manager.validate_token(token.token_value) == True

        # Wait for expiration
        time.sleep(2)

        # Should be invalid after expiration
        assert auth_manager.validate_token(token.token_value) == False

    def test_token_refresh(self, auth_manager):
        """Test token refresh"""
        user_id = "test_user"
        auth_level = AuthLevel.USER

        # Generate initial token
        original_token = auth_manager.generate_token(user_id, auth_level)

        # Refresh token
        new_token = auth_manager.refresh_token(original_token.token_value)

        assert new_token is not None
        assert new_token.user_id == user_id
        assert new_token.auth_level == auth_level
        assert new_token.token_value != original_token.token_value
        assert new_token.expires_at > original_token.expires_at

    def test_auth_levels(self, auth_manager):
        """Test different authentication levels"""
        user_id = "test_user"

        # Generate tokens with different levels
        guest_token = auth_manager.generate_token(user_id, AuthLevel.GUEST)
        user_token = auth_manager.generate_token(user_id, AuthLevel.USER)
        admin_token = auth_manager.generate_token(user_id, AuthLevel.ADMIN)

        # All should be valid
        assert auth_manager.validate_token(guest_token.token_value) == True
        assert auth_manager.validate_token(user_token.token_value) == True
        assert auth_manager.validate_token(admin_token.token_value) == True

        # Test authorization levels
        assert auth_manager.check_authorization(guest_token.token_value, AuthLevel.GUEST) == True
        assert auth_manager.check_authorization(guest_token.token_value, AuthLevel.USER) == False
        assert auth_manager.check_authorization(admin_token.token_value, AuthLevel.USER) == True

    def test_token_revocation(self, auth_manager):
        """Test token revocation"""
        user_id = "test_user"
        auth_level = AuthLevel.USER

        token = auth_manager.generate_token(user_id, auth_level)

        # Should be valid initially
        assert auth_manager.validate_token(token.token_value) == True

        # Revoke token
        auth_manager.revoke_token(token.token_value)

        # Should be invalid after revocation
        assert auth_manager.validate_token(token.token_value) == False

    def test_session_management(self, auth_manager):
        """Test session management"""
        user_id = "test_user"

        # Create session
        session_id = auth_manager.create_session(user_id)
        assert session_id is not None

        # Validate session
        assert auth_manager.validate_session(session_id) == True

        # Get session info
        session_info = auth_manager.get_session_info(session_id)
        assert session_info["user_id"] == user_id
        assert "created_at" in session_info
        assert "last_activity" in session_info

        # End session
        auth_manager.end_session(session_id)
        assert auth_manager.validate_session(session_id) == False


class TestSecurityIntegration:
    """Integration tests for security components"""

    def test_end_to_end_security_flow(self):
        """Test complete security flow"""
        # Initialize components
        encryption_manager = EncryptionManager()
        audit_logger = AuditLogger()
        rate_limiter = RateLimiter(max_requests=10, time_window=60)
        sanitizer = DataSanitizer()
        auth_manager = AuthManager(secret_key="integration_test_key")

        # 1. Authentication
        user_id = "integration_test_user"
        token = auth_manager.generate_token(user_id, AuthLevel.USER)

        audit_logger.log_authentication(success=True, user_id=user_id, ip_address="127.0.0.1")

        # 2. Rate limiting
        assert rate_limiter.is_allowed(user_id) == True

        # 3. Data sanitization
        sensitive_data = "My email is user@example.com and phone is 555-1234"
        sanitized_data = sanitizer.sanitize_all(sensitive_data)

        # 4. Data encryption
        encrypted_data = encryption_manager.encrypt_string(sanitized_data)

        # 5. Audit logging
        audit_logger.log_data_access(
            resource="user_data", action="encrypt", user_id=user_id, record_count=1
        )

        # 6. Data decryption
        decrypted_data = encryption_manager.decrypt_string(encrypted_data)

        # Verify flow
        assert auth_manager.validate_token(token.token_value) == True
        assert decrypted_data == sanitized_data
        assert "user@example.com" not in sanitized_data  # Should be sanitized

    def test_security_error_scenarios(self):
        """Test security error scenarios"""
        encryption_manager = EncryptionManager()
        auth_manager = AuthManager(secret_key="test_key")
        rate_limiter = RateLimiter(max_requests=2, time_window=60)

        # Rate limiting exceeded
        user_id = "test_user"
        rate_limiter.is_allowed(user_id)  # 1st request
        rate_limiter.is_allowed(user_id)  # 2nd request

        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit(user_id)  # 3rd request should fail

        # Invalid token
        assert auth_manager.validate_token("invalid_token") == False

        # Tampered encrypted data
        original_data = "test data"
        encrypted = encryption_manager.encrypt_string(original_data)
        tampered = encrypted[:-5] + "tampr"  # Tamper with encrypted data

        with pytest.raises(ValueError):
            encryption_manager.decrypt_string(tampered)
