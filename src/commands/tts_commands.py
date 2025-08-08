"""Text-to-Speech related commands for CQRS pattern."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base_command import Command


@dataclass
class SpeakTextCommand(Command):
    """Command to speak text using TTS."""

    text: str = ""
    language: str = "en"
    rate: Optional[int] = None
    volume: Optional[float] = None
    voice_id: Optional[str] = None
    audio_device: Optional[str] = None

    def validate(self) -> bool:
        """Validate speak text command."""
        if not self.text or not self.text.strip():
            return False

        if len(self.text) > 2000:  # Max TTS text length
            return False

        if not self.language:
            return False

        if self.rate is not None:
            if not (50 <= self.rate <= 300):  # WPM range
                return False

        if self.volume is not None:
            if not (0.0 <= self.volume <= 1.0):
                return False

        return True

    @property
    def estimated_duration_seconds(self) -> float:
        """Estimate speech duration based on text length and rate."""
        words = len(self.text.split())
        rate_wpm = self.rate or 200  # Default rate
        return (words / rate_wpm) * 60  # Convert to seconds


@dataclass
class StopSpeechCommand(Command):
    """Command to stop current TTS playback."""

    force_stop: bool = False

    def validate(self) -> bool:
        """Always valid command."""
        return True


@dataclass
class ConfigureTTSCommand(Command):
    """Command to configure TTS settings."""

    enabled: bool = True
    rate: int = 200
    volume: float = 0.8
    voice_id: Optional[str] = None
    audio_device: str = "default"
    language_voices: Optional[Dict[str, str]] = None

    def validate(self) -> bool:
        """Validate TTS configuration."""
        if not (50 <= self.rate <= 300):
            return False

        if not (0.0 <= self.volume <= 1.0):
            return False

        if not self.audio_device:
            return False

        return True


@dataclass
class GetAvailableVoicesCommand(Command):
    """Command to get available TTS voices."""

    language_filter: Optional[str] = None
    include_system_info: bool = False

    def validate(self) -> bool:
        """Always valid command."""
        return True


@dataclass
class TestTTSCommand(Command):
    """Command to test TTS configuration."""

    test_text: str = "This is a test of the text-to-speech system."
    language: str = "en"
    rate: Optional[int] = None
    volume: Optional[float] = None
    voice_id: Optional[str] = None

    def validate(self) -> bool:
        """Validate TTS test command."""
        if not self.test_text:
            return False

        if len(self.test_text) > 500:  # Keep test short
            return False

        if self.rate is not None:
            if not (50 <= self.rate <= 300):
                return False

        if self.volume is not None:
            if not (0.0 <= self.volume <= 1.0):
                return False

        return True


@dataclass
class QueueSpeechCommand(Command):
    """Command to queue multiple TTS items."""

    speech_items: Optional[list[Dict[str, Any]]] = None  # List of text/settings combinations
    auto_play: bool = True
    clear_existing_queue: bool = False

    def __post_init__(self):
        if self.speech_items is None:
            self.speech_items = []

    def validate(self) -> bool:
        """Validate speech queue command."""
        if not self.speech_items:
            return False

        if len(self.speech_items) > 50:  # Max queue size
            return False

        for item in self.speech_items:
            if not isinstance(item, dict):
                return False

            if "text" not in item:
                return False

            if not item["text"] or not item["text"].strip():
                return False

            if len(item["text"]) > 2000:
                return False

        return True

    @property
    def total_items(self) -> int:
        """Get total queue items."""
        return len(self.speech_items)

    @property
    def estimated_total_duration(self) -> float:
        """Estimate total queue duration."""
        if self.speech_items is None:
            return 0.0
        total_words = sum(len(item["text"].split()) for item in self.speech_items)
        avg_rate = 200  # WPM
        return (total_words / avg_rate) * 60
