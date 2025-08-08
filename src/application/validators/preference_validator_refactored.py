"""
Refactored Preference Validator - Low Complexity Components
Extracted from complex UpdatePreferencesUseCase
"""

import re
from typing import Dict, List, Tuple


class LanguageValidator:
    """Single responsibility: Validate language codes"""

    SUPPORTED_LANGUAGES = {
        "auto",
        "en",
        "ru",
        "ja",
        "de",
        "fr",
        "es",
        "it",
        "pt",
        "zh",
        "ko",
        "ar",
        "hi",
        "th",
        "vi",
        "pl",
        "nl",
    }

    def is_valid(self, language: str) -> bool:
        """Check if language is supported - complexity 1"""
        return language in self.SUPPORTED_LANGUAGES

    def validate(self, language: str) -> Tuple[bool, str]:
        """Validate language with error message - complexity 2"""
        if not language:  # +1
            return False, "Language code cannot be empty"

        if not self.is_valid(language):  # +1
            return False, f"Unsupported language: {language}"

        return True, ""


class HotkeyValidator:
    """Single responsibility: Validate hotkey combinations"""

    VALID_PATTERNS = [
        r"^ctrl\+[a-z0-9]$",
        r"^alt\+[a-z0-9]$",
        r"^shift\+[a-z0-9]$",
        r"^ctrl\+shift\+[a-z0-9]$",
    ]

    def is_valid_format(self, hotkey: str) -> bool:
        """Check hotkey format - complexity 3"""
        if not hotkey:  # +1
            return False

        normalized = hotkey.lower().strip()
        for pattern in self.VALID_PATTERNS:  # +1
            if re.match(pattern, normalized):  # +1
                return True

        return False

    def validate(self, hotkey: str) -> Tuple[bool, str]:
        """Validate hotkey with error message - complexity 2"""
        if not hotkey:  # +1
            return False, "Hotkey cannot be empty"

        if not self.is_valid_format(hotkey):  # +1
            return False, f"Invalid hotkey format: {hotkey}"

        return True, ""


class PreferenceValidator:
    """Composed validator with low complexity - complexity 4"""

    def __init__(self):
        self.language_validator = LanguageValidator()
        self.hotkey_validator = HotkeyValidator()

    def validate_all(self, preferences: Dict) -> Tuple[bool, List[str]]:
        """Validate all preferences - complexity 4"""
        errors = []

        # Validate language if present
        if "source_language" in preferences:  # +1
            valid, error = self.language_validator.validate(preferences["source_language"])
            if not valid:  # +1
                errors.append(f"Source language: {error}")

        if "target_language" in preferences:  # +1
            valid, error = self.language_validator.validate(preferences["target_language"])
            if not valid:  # +1
                errors.append(f"Target language: {error}")

        # Validate hotkeys
        for hotkey_name in ["screenshot_hotkey", "translate_hotkey"]:
            if hotkey_name in preferences:
                valid, error = self.hotkey_validator.validate(preferences[hotkey_name])
                if not valid:
                    errors.append(f"{hotkey_name}: {error}")

        return len(errors) == 0, errors
