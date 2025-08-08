"""
Text-to-speech service implementation.
"""

import threading
from typing import Optional

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    pyttsx3 = None
    TTS_AVAILABLE = False

from ...domain.protocols.services import TTSService
from ...domain.value_objects.language import Language
from ...utils.logger import logger


class PyttsxTTSService(TTSService):
    """pyttsx3 TTS service implementation."""

    def __init__(self):
        self._engine = None
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self):
        """Initialize TTS engine."""
        try:
            with self._lock:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 150)
                self._engine.setProperty("volume", 1.0)

            logger.info("pyttsx3 TTS service initialized")

        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3 TTS: {e}")

    async def speak(self, text: str, language: Language) -> None:
        """Convert text to speech."""
        if not self._engine or not text.strip():
            return

        try:
            with self._lock:
                # Set language-appropriate voice if available
                voices = self._engine.getProperty("voices")
                if voices:
                    # Simple language matching
                    target_voice = None
                    if language.code == "en":
                        target_voice = next(
                            (v for v in voices if "english" in v.name.lower()), None
                        )
                    elif language.code == "ru":
                        target_voice = next(
                            (v for v in voices if "russian" in v.name.lower()), None
                        )

                    if target_voice:
                        self._engine.setProperty("voice", target_voice.id)

                self._engine.say(text)
                self._engine.runAndWait()

            logger.info(f"TTS completed", text_length=len(text), language=language.code)

        except Exception as e:
            logger.error(f"TTS failed: {e}")
            # Try to reinitialize engine
            self._initialize()

    def is_available(self) -> bool:
        """Check if TTS service is available."""
        return self._engine is not None

    def set_voice(self, voice_id: str) -> None:
        """Set TTS voice."""
        if not self._engine:
            return

        try:
            with self._lock:
                self._engine.setProperty("voice", voice_id)
        except Exception as e:
            logger.error(f"Failed to set TTS voice: {e}")

    def set_rate(self, rate: int) -> None:
        """Set speech rate."""
        if not self._engine:
            return

        try:
            with self._lock:
                self._engine.setProperty("rate", rate)
        except Exception as e:
            logger.error(f"Failed to set TTS rate: {e}")
