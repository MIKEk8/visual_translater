import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.models.config import TTSConfig
from src.utils.logger import logger


@dataclass
class Voice:
    id: str
    name: str
    language: str = ""
    gender: str = ""


class TTSEngine(ABC):
    """Abstract base class for TTS engines"""

    @abstractmethod
    def speak(self, text: str) -> bool:
        """Speak the given text"""

    @abstractmethod
    def set_rate(self, rate: int) -> bool:
        """Set speech rate"""

    @abstractmethod
    def set_voice(self, voice_id: str) -> bool:
        """Set voice by ID"""

    @abstractmethod
    def get_voices(self) -> List[Voice]:
        """Get available voices"""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS engine is available"""

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech"""


class PyttsxEngine(TTSEngine):
    """pyttsx3 TTS engine implementation"""

    def __init__(self):
        self._lock = threading.Lock()
        with self._lock:
            self.engine = None
            self.is_speaking = False
        self._initialize()

        if self.is_available():
            logger.info("pyttsx3 TTS Engine initialized")
        else:
            logger.error("pyttsx3 TTS Engine not available")

    def _initialize(self):
        """Initialize pyttsx3 engine"""
        try:
            import pyttsx3

            with self._lock:
                self.engine = pyttsx3.init()
            # Set default properties
            with self._lock:
                self.engine.setProperty("rate", 150)
        except Exception as e:
            logger.error("Failed to initialize pyttsx3", error=e)

    def speak(self, text: str) -> bool:
        """Speak text using pyttsx3"""
        if not self.engine or not text.strip():
            return False

        with self._lock:
            try:
                self.is_speaking = True
                self.engine.say(text)
                self.engine.runAndWait()
                return True
            except Exception as e:
                logger.error("TTS speech failed", error=e, text_length=len(text))
                # Try to reinitialize engine
                self._reinitialize()
                return False
            finally:
                # Always reset is_speaking state
                self.is_speaking = False

    def _reinitialize(self):
        """Reinitialize TTS engine after failure"""
        try:
            import pyttsx3

            # Use lock if available (might not be available in test environments)
            if hasattr(self, '_lock'):
                with self._lock:
                    self.engine = pyttsx3.init()
            else:
                self.engine = pyttsx3.init()
            logger.info("TTS engine reinitialized")
        except Exception as e:
            logger.error("TTS engine reinitialization failed", error=e)

    def set_rate(self, rate: int) -> bool:
        """Set speech rate"""
        if not self.engine:
            return False

        try:
            with self._lock:
                self.engine.setProperty("rate", rate)
            return True
        except Exception as e:
            logger.error("Failed to set TTS rate", error=e, rate=rate)
            return False

    def set_voice(self, voice_id: str) -> bool:
        """Set voice by ID"""
        if not self.engine or not voice_id:
            return False

        try:
            with self._lock:
                self.engine.setProperty("voice", voice_id)
            return True
        except Exception as e:
            logger.error("Failed to set TTS voice", error=e, voice_id=voice_id)
            return False

    def get_voices(self) -> List[Voice]:
        """Get available voices"""
        if not self.engine:
            return []

        try:
            with self._lock:
                voices = self.engine.getProperty("voices")
            if not voices:
                return []

            voice_list = []
            for voice in voices:
                name = getattr(voice, "name", voice.id)
                language = ""
                if hasattr(voice, "languages") and voice.languages:
                    language = voice.languages[0][:2] if voice.languages[0] else ""

                voice_list.append(Voice(id=voice.id, name=name, language=language))

            return voice_list
        except Exception as e:
            logger.error("Failed to get TTS voices", error=e)
            return []

    def is_available(self) -> bool:
        """Check if pyttsx3 is available"""
        return self.engine is not None

    def stop(self) -> None:
        """Stop current speech"""
        if self.engine and self.is_speaking:
            try:
                with self._lock:
                    self.engine.stop()
                with self._lock:
                    self.is_speaking = False
            except Exception as e:
                logger.error("Failed to stop TTS", error=e)


class TTSProcessor:
    """Main TTS processing class"""

    def __init__(self, config: TTSConfig):
        self._lock = threading.Lock()
        with self._lock:
            self.config = config
            self.engines = [PyttsxEngine()]  # Can add more engines
            self.active_engine = self._get_available_engine()
            self.is_enabled = config.enabled
        self.last_text = ""

        if self.active_engine:
            self._apply_config()
            logger.info(f"TTS processor initialized with {type(self.active_engine).__name__}")
        else:
            logger.error("No TTS engines available")

    def _get_available_engine(self) -> Optional[TTSEngine]:
        """Get first available TTS engine"""
        for engine in self.engines:
            if engine.is_available():
                return engine
        return None

    def _apply_config(self):
        """Apply current configuration to engine"""
        if not self.active_engine:
            return

        with self._lock:
            # Set rate
            self.active_engine.set_rate(self.config.rate)

            # Set voice if specified
            if self.config.voice_id:
                self.active_engine.set_voice(self.config.voice_id)

    def speak_text(self, text: str) -> bool:
        """Speak text if TTS is enabled"""
        if not self.is_enabled or not self.active_engine or not text.strip():
            return False

        start_time = time.time()

        # Run in separate thread to avoid blocking
        def _speak():
            success = self.active_engine.speak(text)
            duration = time.time() - start_time

            if success:
                logger.log_tts(
                    text_length=len(text), voice_id=self.config.voice_id, duration=duration
                )

            return success

        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()

        with self._lock:
            # Store last text for repeat functionality
            self.last_text = text
        return True

    def repeat_last(self) -> bool:
        """Repeat last spoken text"""
        if self.last_text:
            return self.speak_text(self.last_text)
        return False

    def stop_speaking(self) -> None:
        """Stop current speech"""
        with self._lock:
            if self.active_engine:
                self.active_engine.stop()

    def update_config(self, config: TTSConfig) -> None:
        """Update TTS configuration"""
        with self._lock:
            old_enabled = self.is_enabled
            self.config = config
        self.is_enabled = config.enabled

        if self.active_engine and self.is_enabled:
            self._apply_config()

        if old_enabled != self.is_enabled:
            status = "enabled" if self.is_enabled else "disabled"
            logger.info(f"TTS {status}")

    def get_available_voices(self) -> List[Voice]:
        """Get available voices"""
        if not self.active_engine:
            return []
        return self.active_engine.get_voices()

    def test_voice(self, voice_id: str, test_text: str = "Test voice") -> bool:
        """Test specific voice"""
        if not self.active_engine:
            return False

        with self._lock:
            # Temporarily set voice
            original_voice = self.config.voice_id

            if self.active_engine.set_voice(voice_id):
                success = self.active_engine.speak(test_text)
                # Restore original voice
                if original_voice:
                    self.active_engine.set_voice(original_voice)
                return success

        return False

    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self.active_engine is not None

    def get_engine_info(self) -> dict:
        """Get information about active TTS engine"""
        if not self.active_engine:
            return {"engine": "None", "available": False}

        with self._lock:
            return {
                "engine": type(self.active_engine).__name__,
                "available": True,
                "enabled": self.is_enabled,
                "voices_count": len(self.get_available_voices()),
                "current_voice": self.config.voice_id or "default",
                "rate": self.config.rate,
            }
