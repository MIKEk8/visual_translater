"""
Built-in pyttsx3 TTS plugin for Screen Translator v2.0.
Wraps the existing TTSProcessor as a plugin.
"""

from typing import Any, Dict, List

from src.plugins.base_plugin import PluginMetadata, PluginType, TTSPlugin
from src.utils.logger import logger


class Pyttsx3TTSPlugin(TTSPlugin):
    """Plugin wrapper for pyttsx3 TTS engine."""

    def __init__(self):
        super().__init__()
        self._tts_engine = None

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="pyttsx3_tts",
            version="1.0.0",
            description="pyttsx3 TTS engine plugin for speech synthesis",
            author="Screen Translator Team",
            plugin_type=PluginType.TTS,
            dependencies=["pyttsx3"],
            config_schema={
                "rate": {
                    "type": "number",
                    "description": "Speech rate (words per minute)",
                    "default": 200,
                    "min": 50,
                    "max": 400,
                },
                "volume": {
                    "type": "number",
                    "description": "Speech volume (0.0 to 1.0)",
                    "default": 0.8,
                    "min": 0.0,
                    "max": 1.0,
                },
                "voice_id": {"type": "string", "description": "Voice ID to use", "default": ""},
            },
        )

    def is_available(self) -> bool:
        """Check if pyttsx3 dependencies are available."""
        try:
            return True
        except ImportError:
            return False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the pyttsx3 TTS plugin."""
        try:
            if not self.is_available():
                logger.error("pyttsx3 TTS dependencies not available")
                return False

            # Import here to avoid import errors if dependencies missing
            from src.core.tts_engine import TTSProcessor
            from src.models.config import TTSConfig

            # Create TTS config from plugin config
            tts_config = TTSConfig(
                enabled=True,
                rate=config.get("rate", 200),
                voice_id=config.get("voice_id", ""),
                audio_device="",
            )

            # Create TTS processor instance
            self._tts_engine = TTSProcessor(tts_config)

            self._config = config
            self._initialized = True

            logger.info("pyttsx3 TTS plugin initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize pyttsx3 TTS plugin", error=e)
            return False

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        if self._tts_engine:
            # Stop any ongoing speech
            try:
                self._tts_engine.stop_speech()
            except (RuntimeError, Exception):
                pass

        self._tts_engine = None
        self._initialized = False
        logger.info("pyttsx3 TTS plugin cleaned up")

    def speak(self, text: str, language: str, voice_id: Optional[str] = None) -> bool:
        """
        Speak text using pyttsx3.

        Args:
            text: Text to speak
            language: Language code (not used by pyttsx3)
            voice_id: Optional specific voice ID

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self._tts_engine:
            raise RuntimeError("Plugin not initialized")

        try:
            # Set voice if specified
            if voice_id:
                self.set_voice(voice_id)

            # Use the existing TTS processor
            success = self._tts_engine.speak_text(text)

            logger.debug(f"pyttsx3 TTS spoke {len(text)} characters: {success}")
            return success

        except Exception as e:
            logger.error("pyttsx3 TTS speech failed", error=e)
            return False

    def get_available_voices(self, language: str) -> List[Dict[str, str]]:
        """
        Get available voices for a language.

        Args:
            language: Language code (pyttsx3 returns all system voices)

        Returns:
            List of voice info dicts with keys: id, name, gender, quality
        """
        if not self._initialized or not self._tts_engine:
            return []

        try:
            # Get system voices through TTS engine
            voices = self._tts_engine.get_available_voices()

            # Convert to plugin format
            voice_list = []
            for voice in voices:
                voice_info = {
                    "id": voice.get("id", ""),
                    "name": voice.get("name", "Unknown"),
                    "gender": voice.get("gender", "Unknown"),
                    "quality": "System",  # pyttsx3 uses system voices
                }
                voice_list.append(voice_info)

            logger.debug(f"Found {len(voice_list)} available voices")
            return voice_list

        except Exception as e:
            logger.error("Failed to get available voices", error=e)
            return []

    def set_speech_rate(self, rate: int) -> None:
        """Set speech rate."""
        if not self._initialized or not self._tts_engine:
            return

        try:
            # Update TTS engine configuration
            self._tts_engine.set_rate(rate)
            self._config["rate"] = rate

            logger.debug(f"Set speech rate to {rate}")

        except Exception as e:
            logger.error("Failed to set speech rate", error=e)

    def set_volume(self, volume: float) -> None:
        """Set volume level 0.0-1.0."""
        if not self._initialized or not self._tts_engine:
            return

        try:
            # Update TTS engine configuration
            self._tts_engine.set_volume(volume)
            self._config["volume"] = volume

            logger.debug(f"Set volume to {volume}")

        except Exception as e:
            logger.error("Failed to set volume", error=e)

    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice to use.

        Args:
            voice_id: Voice ID to set

        Returns:
            True if successful
        """
        if not self._initialized or not self._tts_engine:
            return False

        try:
            # Update TTS engine voice
            success = self._tts_engine.set_voice(voice_id)
            if success:
                self._config["voice_id"] = voice_id

            logger.debug(f"Set voice to {voice_id}: {success}")
            return success

        except Exception as e:
            logger.error("Failed to set voice", error=e)
            return False

    def test_voice(self, voice_id: str, test_text: str = "This is a voice test.") -> bool:
        """
        Test a voice with sample text.

        Args:
            voice_id: Voice ID to test
            test_text: Text to speak for testing

        Returns:
            True if test successful
        """
        if not self._initialized:
            return False

        try:
            # Save current voice
            current_voice = self._config.get("voice_id", "")

            # Set test voice and speak
            if self.set_voice(voice_id):
                success = self.speak(test_text, "en")

                # Restore original voice
                if current_voice:
                    self.set_voice(current_voice)

                return success

            return False

        except Exception as e:
            logger.error("Voice test failed", error=e)
            return False
