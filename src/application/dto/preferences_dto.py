"""Preferences Data Transfer Objects."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from ...domain.entities.preferences import UserPreferences


@dataclass
class PreferencesRequest:
    """Request for preferences operations."""

    target_language: Optional[str] = None
    ocr_language: Optional[str] = None
    auto_tts: Optional[bool] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[int] = None
    tts_volume: Optional[float] = None
    cache_enabled: Optional[bool] = None
    theme: Optional[str] = None
    hotkeys: Optional[Dict[str, str]] = None


@dataclass
class PreferencesResponse:
    """Response for preferences operations."""

    success: bool
    preferences: Optional[UserPreferences] = None
    errors: List[str] = None

    @classmethod
    def success(cls, preferences: UserPreferences) -> "PreferencesResponse":
        """Create success response."""
        return cls(success=True, preferences=preferences)

    @classmethod
    def error(cls, errors: List[str]) -> "PreferencesResponse":
        """Create error response."""
        return cls(success=False, errors=errors or [])
