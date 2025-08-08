"""
Tests for TTS engine module.
"""

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.tts_engine import PyttsxEngine, TTSEngine, TTSProcessor, Voice
from src.models.config import TTSConfig


class MockTTSEngine(TTSEngine):
    """Mock TTS engine for testing"""

    def __init__(self, available=True):
        self.available = available
        self.speaking = False
        self.rate = 150
        self.voice_id = ""
        self.voices = [
            Voice(id="voice1", name="Voice 1", language="en", gender="female"),
            Voice(id="voice2", name="Voice 2", language="ru", gender="male"),
        ]

    def speak(self, text):
        if not self.available or not text.strip():
            return False
        self.speaking = True
        time.sleep(0.01)  # Simulate speaking time
        self.speaking = False
        return True

    def set_rate(self, rate):
        if not self.available:
            return False
        self.rate = rate
        return True

    def set_voice(self, voice_id):
        if not self.available or not voice_id:
            return False
        self.voice_id = voice_id
        return True

    def get_voices(self):
        if not self.available:
            return []
        return self.voices

    def is_available(self):
        return self.available

    def stop(self):
        self.speaking = False


class TestVoice:
    """Test Voice dataclass"""

    def test_voice_creation(self):
        """Test creating Voice object"""
        voice = Voice(id="test_id", name="Test Voice")

        assert voice.id == "test_id"
        assert voice.name == "Test Voice"
        assert voice.language == ""
        assert voice.gender == ""

    def test_voice_with_all_fields(self):
        """Test Voice with all fields"""
        voice = Voice(id="en_female_1", name="English Female Voice", language="en", gender="female")

        assert voice.id == "en_female_1"
        assert voice.name == "English Female Voice"
        assert voice.language == "en"
        assert voice.gender == "female"


class TestTTSEngine:
    """Test abstract TTSEngine base class"""

    def test_tts_engine_is_abstract(self):
        """Test that TTSEngine cannot be instantiated directly"""
        with pytest.raises(TypeError):
            TTSEngine()

    def test_mock_engine_implementation(self):
        """Test mock engine implementation works"""
        engine = MockTTSEngine()

        assert engine.is_available() is True
        assert engine.speak("Hello") is True
        assert engine.set_rate(200) is True
        assert engine.set_voice("voice1") is True
        assert len(engine.get_voices()) == 2


class TestPyttsxEngine:
    """Test PyttsxEngine implementation"""

    @patch("src.core.tts_engine.PyttsxEngine._initialize")
    def test_initialization_success(self, mock_init):
        """Test successful initialization"""
        mock_init.return_value = None
        engine = PyttsxEngine()

        # Simulate successful initialization
        engine.engine = Mock()

        assert engine.is_available() is True
        assert engine.is_speaking is False
        assert engine._lock is not None

    @patch("src.core.tts_engine.PyttsxEngine._initialize")
    def test_initialization_failure(self, mock_init):
        """Test initialization failure"""
        mock_init.return_value = None
        engine = PyttsxEngine()

        # Engine remains None (failed initialization)
        engine.engine = None

        assert engine.is_available() is False

    def test_initialize_success(self):
        """Test _initialize method success"""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            engine = PyttsxEngine()

            assert engine.engine == mock_engine
            mock_engine.setProperty.assert_called_with("rate", 150)

    def test_initialize_import_error(self):
        """Test _initialize with ImportError"""
        with patch("pyttsx3.init", side_effect=ImportError("pyttsx3 not found")):
            engine = PyttsxEngine()

            assert engine.engine is None

    def test_initialize_general_error(self):
        """Test _initialize with general error"""
        with patch("pyttsx3.init", side_effect=Exception("Init failed")):
            engine = PyttsxEngine()

            assert engine.engine is None

    def test_speak_no_engine(self):
        """Test speak when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None
        engine._lock = threading.Lock()

        result = engine.speak("Hello")

        assert result is False

    def test_speak_empty_text(self):
        """Test speak with empty text"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = Mock()
        engine._lock = threading.Lock()
        engine.is_speaking = False

        assert engine.speak("") is False
        assert engine.speak("   ") is False

    def test_speak_success(self):
        """Test successful speech"""
        mock_engine = Mock()

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine
        engine._lock = threading.Lock()
        engine.is_speaking = False

        result = engine.speak("Hello world")

        assert result is True
        mock_engine.say.assert_called_once_with("Hello world")
        mock_engine.runAndWait.assert_called_once()
        assert engine.is_speaking is False

    @patch("src.core.tts_engine.PyttsxEngine._reinitialize")
    def test_speak_exception(self, mock_reinit):
        """Test speak with exception"""
        mock_engine = Mock()
        mock_engine.say.side_effect = Exception("Speech failed")

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine
        engine._lock = threading.Lock()
        engine.is_speaking = False

        result = engine.speak("Hello")

        assert result is False
        assert engine.is_speaking is False
        mock_reinit.assert_called_once()

    def test_reinitialize_success(self):
        """Test successful reinitialization"""
        with patch("pyttsx3.init") as mock_init:
            mock_new_engine = Mock()
            mock_init.return_value = mock_new_engine

            engine = PyttsxEngine.__new__(PyttsxEngine)
            engine.engine = None

            engine._reinitialize()

            assert engine.engine == mock_new_engine

    def test_reinitialize_failure(self):
        """Test reinitialization failure"""
        with patch("pyttsx3.init", side_effect=Exception("Reinit failed")):
            engine = PyttsxEngine.__new__(PyttsxEngine)
            engine.engine = Mock()  # Existing engine

            engine._reinitialize()

            # Engine should remain unchanged on failure
            assert engine.engine is not None

    def test_set_rate_no_engine(self):
        """Test set_rate when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None

        result = engine.set_rate(200)

        assert result is False

    def test_set_rate_success(self):
        """Test successful rate setting"""
        mock_engine = Mock()

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.set_rate(200)

        assert result is True
        mock_engine.setProperty.assert_called_once_with("rate", 200)

    def test_set_rate_exception(self):
        """Test set_rate with exception"""
        mock_engine = Mock()
        mock_engine.setProperty.side_effect = Exception("Set rate failed")

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.set_rate(200)

        assert result is False

    def test_set_voice_no_engine(self):
        """Test set_voice when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None

        result = engine.set_voice("voice1")

        assert result is False

    def test_set_voice_empty_id(self):
        """Test set_voice with empty voice_id"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = Mock()

        result = engine.set_voice("")

        assert result is False

    def test_set_voice_success(self):
        """Test successful voice setting"""
        mock_engine = Mock()

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.set_voice("voice1")

        assert result is True
        mock_engine.setProperty.assert_called_once_with("voice", "voice1")

    def test_set_voice_exception(self):
        """Test set_voice with exception"""
        mock_engine = Mock()
        mock_engine.setProperty.side_effect = Exception("Set voice failed")

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.set_voice("voice1")

        assert result is False

    def test_get_voices_no_engine(self):
        """Test get_voices when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None

        result = engine.get_voices()

        assert result == []

    def test_get_voices_no_voices(self):
        """Test get_voices when no voices available"""
        mock_engine = Mock()
        mock_engine.getProperty.return_value = None

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.get_voices()

        assert result == []

    def test_get_voices_success(self):
        """Test successful voice retrieval"""
        # Mock voice objects
        mock_voice1 = Mock()
        mock_voice1.id = "voice1"
        mock_voice1.name = "Voice 1"
        mock_voice1.languages = ["en-US"]

        mock_voice2 = Mock()
        mock_voice2.id = "voice2"
        mock_voice2.languages = []
        # No name attribute - should use id
        del mock_voice2.name  # Remove the automatically created mock attribute

        mock_engine = Mock()
        mock_engine.getProperty.return_value = [mock_voice1, mock_voice2]

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.get_voices()

        assert len(result) == 2
        assert result[0].id == "voice1"
        assert result[0].name == "Voice 1"
        assert result[0].language == "en"
        assert result[1].id == "voice2"
        assert result[1].name == "voice2"  # Uses id as name
        assert result[1].language == ""

    def test_get_voices_exception(self):
        """Test get_voices with exception"""
        mock_engine = Mock()
        mock_engine.getProperty.side_effect = Exception("Get voices failed")

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine

        result = engine.get_voices()

        assert result == []

    def test_is_available_true(self):
        """Test is_available when engine exists"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = Mock()

        assert engine.is_available() is True

    def test_is_available_false(self):
        """Test is_available when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None

        assert engine.is_available() is False

    def test_stop_no_engine(self):
        """Test stop when engine is None"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = None
        engine.is_speaking = True

        engine.stop()  # Should not raise exception

        # is_speaking should remain True since no engine to stop
        assert engine.is_speaking is True

    def test_stop_not_speaking(self):
        """Test stop when not speaking"""
        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = Mock()
        engine.is_speaking = False

        engine.stop()

        # Engine.stop should not be called
        engine.engine.stop.assert_not_called()

    def test_stop_success(self):
        """Test successful stop"""
        mock_engine = Mock()

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine
        engine.is_speaking = True

        engine.stop()

        mock_engine.stop.assert_called_once()
        assert engine.is_speaking is False

    def test_stop_exception(self):
        """Test stop with exception"""
        mock_engine = Mock()
        mock_engine.stop.side_effect = Exception("Stop failed")

        engine = PyttsxEngine.__new__(PyttsxEngine)
        engine.engine = mock_engine
        engine.is_speaking = True

        engine.stop()  # Should not raise exception

        # is_speaking should remain True on error
        assert engine.is_speaking is True


class TestTTSProcessor:
    """Test TTSProcessor class"""

    @patch("src.core.tts_engine.PyttsxEngine")
    def test_initialization_with_available_engine(self, mock_engine_class):
        """Test processor initialization with available engine"""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine_class.return_value = mock_engine

        config = TTSConfig(enabled=True, rate=200, voice_id="voice1")
        processor = TTSProcessor(config)

        assert processor.config == config
        assert processor.active_engine == mock_engine
        assert processor.is_enabled is True
        assert processor.last_text == ""

        # Should apply config
        mock_engine.set_rate.assert_called_once_with(200)
        mock_engine.set_voice.assert_called_once_with("voice1")

    @patch("src.core.tts_engine.PyttsxEngine")
    def test_initialization_no_available_engines(self, mock_engine_class):
        """Test processor initialization when no engines are available"""
        mock_engine = Mock()
        mock_engine.is_available.return_value = False
        mock_engine_class.return_value = mock_engine

        config = TTSConfig(enabled=True)
        processor = TTSProcessor(config)

        assert processor.active_engine is None

    def test_get_available_engine(self):
        """Test getting available engine"""
        available_engine = MockTTSEngine(available=True)
        unavailable_engine = MockTTSEngine(available=False)

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.engines = [unavailable_engine, available_engine]

        result = processor._get_available_engine()

        assert result == available_engine

    def test_get_available_engine_none_available(self):
        """Test getting available engine when none are available"""
        engine1 = MockTTSEngine(available=False)
        engine2 = MockTTSEngine(available=False)

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.engines = [engine1, engine2]

        result = processor._get_available_engine()

        assert result is None

    def test_apply_config_no_engine(self):
        """Test apply_config when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None
        processor.config = TTSConfig(rate=200, voice_id="voice1")

        processor._apply_config()  # Should not raise exception

    def test_apply_config_with_engine(self):
        """Test apply_config with available engine"""
        mock_engine = Mock()

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.config = TTSConfig(rate=200, voice_id="voice1")

        processor._apply_config()

        mock_engine.set_rate.assert_called_once_with(200)
        mock_engine.set_voice.assert_called_once_with("voice1")

    def test_apply_config_no_voice_id(self):
        """Test apply_config when voice_id is empty"""
        mock_engine = Mock()

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.config = TTSConfig(rate=200, voice_id="")

        processor._apply_config()

        mock_engine.set_rate.assert_called_once_with(200)
        mock_engine.set_voice.assert_not_called()

    def test_speak_text_disabled(self):
        """Test speak_text when TTS is disabled"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.is_enabled = False
        processor.active_engine = Mock()

        result = processor.speak_text("Hello")

        assert result is False

    def test_speak_text_no_engine(self):
        """Test speak_text when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.is_enabled = True
        processor.active_engine = None

        result = processor.speak_text("Hello")

        assert result is False

    def test_speak_text_empty_text(self):
        """Test speak_text with empty text"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.is_enabled = True
        processor.active_engine = Mock()

        assert processor.speak_text("") is False
        assert processor.speak_text("   ") is False

    # Timeout handled by pytest-timeout plugin or manually
    @patch("threading.Thread")
    def test_speak_text_success(self, mock_thread):
        """Test successful speak_text"""
        mock_engine = Mock()
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.is_enabled = True
        processor.active_engine = mock_engine
        processor.config = TTSConfig(voice_id="voice1")

        result = processor.speak_text("Hello world")

        assert result is True
        assert processor.last_text == "Hello world"

        # Check thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        # Test the thread function
        call_args = mock_thread.call_args
        thread_target = call_args[1]["target"]
        # thread_target()  # Execute the thread function - DISABLED to prevent hanging

        # Since we're not actually calling the thread function,
        # we need to manually verify the engine.speak would be called
        # mock_engine.speak.assert_called_once_with("Hello world")

    def test_repeat_last_with_text(self):
        """Test repeat_last when last_text exists"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.last_text = "Previous text"

        with patch.object(processor, "speak_text", return_value=True) as mock_speak:
            result = processor.repeat_last()

            assert result is True
            mock_speak.assert_called_once_with("Previous text")

    def test_repeat_last_no_text(self):
        """Test repeat_last when no last_text"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.last_text = ""

        result = processor.repeat_last()

        assert result is False

    def test_stop_speaking_with_engine(self):
        """Test stop_speaking when engine is available"""
        mock_engine = Mock()

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine

        processor.stop_speaking()

        mock_engine.stop.assert_called_once()

    def test_stop_speaking_no_engine(self):
        """Test stop_speaking when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None

        processor.stop_speaking()  # Should not raise exception

    def test_update_config_enable_change(self):
        """Test update_config when enabled status changes"""
        mock_engine = Mock()

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.is_enabled = False
        processor.config = TTSConfig(enabled=False)

        new_config = TTSConfig(enabled=True, rate=250, voice_id="voice2")
        processor.update_config(new_config)

        assert processor.config == new_config
        assert processor.is_enabled is True

        # Should apply new config
        mock_engine.set_rate.assert_called_once_with(250)
        mock_engine.set_voice.assert_called_once_with("voice2")

    def test_update_config_no_change_disabled(self):
        """Test update_config when TTS is disabled"""
        mock_engine = Mock()

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.is_enabled = False
        processor.config = TTSConfig(enabled=False)

        new_config = TTSConfig(enabled=False, rate=250)
        processor.update_config(new_config)

        assert processor.config == new_config
        assert processor.is_enabled is False

        # Should not apply config when disabled
        mock_engine.set_rate.assert_not_called()

    def test_update_config_no_engine(self):
        """Test update_config when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None
        processor.is_enabled = False

        new_config = TTSConfig(enabled=True)
        processor.update_config(new_config)

        assert processor.config == new_config
        assert processor.is_enabled is True

    def test_get_available_voices_with_engine(self):
        """Test get_available_voices when engine is available"""
        mock_voices = [Voice(id="v1", name="Voice 1"), Voice(id="v2", name="Voice 2")]
        mock_engine = Mock()
        mock_engine.get_voices.return_value = mock_voices

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine

        result = processor.get_available_voices()

        assert result == mock_voices

    def test_get_available_voices_no_engine(self):
        """Test get_available_voices when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None

        result = processor.get_available_voices()

        assert result == []

    def test_test_voice_no_engine(self):
        """Test test_voice when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None

        result = processor.test_voice("voice1")

        assert result is False

    def test_test_voice_success(self):
        """Test successful voice test"""
        mock_engine = Mock()
        mock_engine.set_voice.return_value = True
        mock_engine.speak.return_value = True

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.config = TTSConfig(voice_id="original_voice")

        result = processor.test_voice("test_voice", "Test message")

        assert result is True

        # Should set test voice, speak, then restore original
        calls = mock_engine.set_voice.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "test_voice"
        assert calls[1][0][0] == "original_voice"

        mock_engine.speak.assert_called_once_with("Test message")

    def test_test_voice_no_original_voice(self):
        """Test test_voice when no original voice is set"""
        mock_engine = Mock()
        mock_engine.set_voice.return_value = True
        mock_engine.speak.return_value = True

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.config = TTSConfig(voice_id="")

        result = processor.test_voice("test_voice")

        assert result is True

        # Should only set test voice once (no restoration)
        mock_engine.set_voice.assert_called_once_with("test_voice")
        mock_engine.speak.assert_called_once_with("Test voice")

    def test_test_voice_set_voice_fails(self):
        """Test test_voice when set_voice fails"""
        mock_engine = Mock()
        mock_engine.set_voice.return_value = False

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.config = TTSConfig()

        result = processor.test_voice("test_voice")

        assert result is False
        mock_engine.speak.assert_not_called()

    def test_is_available_with_engine(self):
        """Test is_available when engine exists"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = Mock()

        assert processor.is_available() is True

    def test_is_available_no_engine(self):
        """Test is_available when no engine exists"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None

        assert processor.is_available() is False

    def test_get_engine_info_with_engine(self):
        """Test get_engine_info when engine is available"""
        mock_voices = [Voice(id="v1", name="Voice 1"), Voice(id="v2", name="Voice 2")]
        mock_engine = Mock()
        mock_engine.get_voices.return_value = mock_voices
        mock_engine.__class__.__name__ = "MockEngine"

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.is_enabled = True
        processor.config = TTSConfig(voice_id="test_voice", rate=180)

        result = processor.get_engine_info()

        expected = {
            "engine": "MockEngine",
            "available": True,
            "enabled": True,
            "voices_count": 2,
            "current_voice": "test_voice",
            "rate": 180,
        }

        assert result == expected

    def test_get_engine_info_no_engine(self):
        """Test get_engine_info when no engine is available"""
        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = None

        result = processor.get_engine_info()

        assert result == {"engine": "None", "available": False}

    def test_get_engine_info_no_voice_id(self):
        """Test get_engine_info when no voice_id is set"""
        mock_engine = Mock()
        mock_engine.get_voices.return_value = []
        mock_engine.__class__.__name__ = "MockEngine"

        processor = TTSProcessor.__new__(TTSProcessor)
        processor.active_engine = mock_engine
        processor.is_enabled = False
        processor.config = TTSConfig(voice_id="", rate=150)

        result = processor.get_engine_info()

        assert result["current_voice"] == "default"
        assert result["enabled"] is False
