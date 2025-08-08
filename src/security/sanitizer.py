"""
Data sanitization for privacy and security.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from src.utils.logger import logger


class SanitizationLevel(Enum):
    """Data sanitization levels."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


class DataSanitizer:
    """Data sanitizer for removing sensitive information."""

    def __init__(self):
        # Compile regex patterns for better performance
        self.patterns = {
            # Personal information patterns
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(r"(\+?1[-.\s]?)?(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})"),
            "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
            "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
            # Network information
            "ipv4": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
            "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
            "mac_address": re.compile(r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b"),
            # URLs and domains
            "url": re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
            "domain": re.compile(
                r"\b[a-zA-Z0-9]([a-zA-Z0-9-]{1,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+\b"
            ),
            # API keys and tokens (generic patterns)
            "api_key": re.compile(r"\b[A-Za-z0-9]{32,}\b"),
            "jwt_token": re.compile(r"\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b"),
            # File paths
            "windows_path": re.compile(r'\b[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*'),
            "unix_path": re.compile(r"\b/(?:[^/\s]+/)*[^/\s]*"),
            # Database connection strings
            "connection_string": re.compile(
                r'(?:mongodb|mysql|postgresql|sqlite)://[^\s<>"{}|\\^`\[\]]+'
            ),
            # Passwords in common formats
            "password_field": re.compile(
                r'(?i)(?:password|passwd|pwd)\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE
            ),
        }

        # Sensitive keywords to look for
        self.sensitive_keywords = {
            "password",
            "passwd",
            "pwd",
            "secret",
            "token",
            "key",
            "api_key",
            "private_key",
            "auth",
            "authorization",
            "credential",
            "login",
        }

        # Custom sanitization rules
        self.custom_rules: List[Tuple[re.Pattern, str]] = []

        # Statistics
        self.sanitization_stats = {pattern_name: 0 for pattern_name in self.patterns.keys()}
        self.total_sanitizations = 0

        logger.info("Data sanitizer initialized")

    def add_custom_rule(self, pattern: str, replacement: str = "[REDACTED]") -> None:
        """Add custom sanitization rule."""
        try:
            compiled_pattern = re.compile(pattern)
            self.custom_rules.append((compiled_pattern, replacement))
            logger.info(f"Custom sanitization rule added: {pattern}")
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern} - {e}")

    def sanitize_text(self, text: str, aggressive: bool = False) -> str:
        """
        Sanitize text by removing sensitive information.

        Args:
            text: Text to sanitize
            aggressive: If True, apply more aggressive sanitization
        """
        if not text:
            return text

        sanitized = text
        replacements_made = 0

        # Apply built-in patterns
        for pattern_name, pattern in self.patterns.items():
            if pattern_name in ["domain", "url"] and not aggressive:
                # Skip domain/URL sanitization unless aggressive mode
                continue

            matches = pattern.findall(sanitized)
            if matches:
                replacement = self._get_replacement(pattern_name, aggressive)
                sanitized = pattern.sub(replacement, sanitized)
                replacements_made += len(matches)
                self.sanitization_stats[pattern_name] += len(matches)

        # Apply custom rules
        for custom_pattern, replacement in self.custom_rules:
            matches = custom_pattern.findall(sanitized)
            if matches:
                sanitized = custom_pattern.sub(replacement, sanitized)
                replacements_made += len(matches)

        # Additional aggressive sanitization
        if aggressive:
            sanitized = self._aggressive_sanitize(sanitized)

        if replacements_made > 0:
            self.total_sanitizations += replacements_made
            logger.debug(f"Sanitized {replacements_made} sensitive items from text")

        return sanitized

    def _get_replacement(self, pattern_name: str, aggressive: bool = False) -> str:
        """Get appropriate replacement text for pattern."""
        replacements = {
            "email": "[EMAIL]",
            "phone": "[PHONE]",
            "ssn": "[SSN]",
            "credit_card": "[CREDIT_CARD]",
            "ipv4": "[IPv4]",
            "ipv6": "[IPv6]",
            "mac_address": "[MAC_ADDRESS]",
            "url": "[URL]" if aggressive else r"[REDACTED_URL]",
            "domain": "[DOMAIN]" if aggressive else r"[REDACTED_DOMAIN]",
            "api_key": "[API_KEY]",
            "jwt_token": "[JWT_TOKEN]",
            "windows_path": "[WINDOWS_PATH]",
            "unix_path": "[UNIX_PATH]",
            "connection_string": "[CONNECTION_STRING]",
            "password_field": r"\1[PASSWORD]",
        }
        return replacements.get(pattern_name, "[REDACTED]")

    def _aggressive_sanitize(self, text: str) -> str:
        """Apply aggressive sanitization."""
        # Look for potential sensitive data patterns
        lines = text.split("\n")
        sanitized_lines = []

        for line in lines:
            line_lower = line.lower()

            # Check for sensitive keywords
            for keyword in self.sensitive_keywords:
                if keyword in line_lower:
                    # If line contains sensitive keyword, redact the value part
                    if ":" in line or "=" in line:
                        # Try to preserve the key but redact the value
                        for separator in [":", "="]:
                            if separator in line:
                                parts = line.split(separator, 1)
                                if len(parts) == 2:
                                    line = f"{parts[0]}{separator}[REDACTED]"
                                break
                    break

            sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    def sanitize_dict(self, data: Dict, keys_to_sanitize: Optional[Set[str]] = None) -> Dict:
        """
        Sanitize dictionary values.

        Args:
            data: Dictionary to sanitize
            keys_to_sanitize: Specific keys to sanitize (if None, sanitize all string values)
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if key should be sanitized
            should_sanitize = (
                keys_to_sanitize is None
                or key in keys_to_sanitize
                or any(sensitive in key_lower for sensitive in self.sensitive_keywords)
            )

            if isinstance(value, str) and should_sanitize:
                sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, keys_to_sanitize)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value, keys_to_sanitize)
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_list(self, data: List, keys_to_sanitize: Optional[Set[str]] = None) -> List:
        """Sanitize list items."""
        if not isinstance(data, list):
            return data

        sanitized = []

        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_text(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item, keys_to_sanitize))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item, keys_to_sanitize))
            else:
                sanitized.append(item)

        return sanitized

    def detect_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """
        Detect sensitive data in text without sanitizing.
        Returns dictionary of pattern_name -> list of matches.
        """
        if not text:
            return {}

        detected = {}

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                detected[pattern_name] = matches

        return detected

    def is_sensitive_data(self, text: str) -> bool:
        """Check if text contains sensitive data."""
        detected = self.detect_sensitive_data(text)
        return len(detected) > 0

    def sanitize_ocr_output(self, ocr_text: str) -> str:
        """Specifically sanitize OCR output text."""
        # OCR might pick up sensitive information from screenshots
        sanitized = self.sanitize_text(ocr_text, aggressive=True)

        # Additional OCR-specific sanitization
        # Remove potential credit card numbers that might be partially recognized
        sanitized = re.sub(r"\b\d{4}[\s-]?\*+[\s-]?\*+[\s-]?\d{4}\b", "[CARD_NUMBER]", sanitized)

        # Remove potential account numbers
        sanitized = re.sub(
            r"\b(?:Account|Acct)[\s#:]*\d+\b", "[ACCOUNT_NUMBER]", sanitized, flags=re.IGNORECASE
        )

        return sanitized

    def sanitize_user_input(self, user_input: str) -> str:
        """Sanitize user input for logging or storage."""
        # Less aggressive sanitization for user input
        return self.sanitize_text(user_input, aggressive=False)

    def sanitize_log_message(self, log_message: str) -> str:
        """Sanitize log messages to prevent sensitive data leakage."""
        return self.sanitize_text(log_message, aggressive=True)

    def get_sanitization_stats(self) -> Dict[str, any]:
        """Get sanitization statistics."""
        return {
            "total_sanitizations": self.total_sanitizations,
            "by_pattern": dict(self.sanitization_stats),
            "custom_rules_count": len(self.custom_rules),
            "patterns_available": list(self.patterns.keys()),
        }

    def reset_stats(self) -> None:
        """Reset sanitization statistics."""
        self.sanitization_stats = {pattern_name: 0 for pattern_name in self.patterns.keys()}
        self.total_sanitizations = 0
        logger.info("Sanitization statistics reset")

    def export_detected_patterns(self, text: str, output_file: str) -> bool:
        """Export detected sensitive patterns to file for analysis."""
        try:
            detected = self.detect_sensitive_data(text)

            import json

            export_data = {
                "timestamp": str(__import__("datetime").datetime.now()),
                "text_length": len(text),
                "detected_patterns": detected,
                "pattern_counts": {pattern: len(matches) for pattern, matches in detected.items()},
                "total_sensitive_items": sum(len(matches) for matches in detected.values()),
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Detected patterns exported to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export detected patterns: {e}")
            return False


# Global data sanitizer instance
_data_sanitizer: Optional[DataSanitizer] = None


def get_data_sanitizer() -> DataSanitizer:
    """Get global data sanitizer instance."""
    global _data_sanitizer

    if _data_sanitizer is None:
        _data_sanitizer = DataSanitizer()

    return _data_sanitizer
