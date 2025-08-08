"""
Tests for configuration model classes.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.models.config import (
    DEBUG_MODE,
    DEFAULT_CONFIG_PATH,
    ICON_PATH,
    MIN_AREA_SIZE,
    AppConfig,
    FeaturesConfig,
    HotkeyConfig,
    ImageProcessingConfig,
    LanguageConfig,
    TTSConfig,
)


class TestHotkeyConfig:
    """Test HotkeyConfig dataclass."""

    def test_default_values(self):
        """Test default hotkey configuration."""
        config = HotkeyConfig()

        assert config.area_select == "alt+a"
        assert config.quick_center == "alt+q"
        assert config.quick_bottom == "alt+w"
        assert config.repeat_last == "alt+s"
        assert config.switch_language == "alt+l"

    def test_custom_values(self):
        """Test custom hotkey configuration."""
        config = HotkeyConfig(
            area_select="ctrl+a",
            quick_center="ctrl+q",
            quick_bottom="ctrl+w",
            repeat_last="ctrl+s",
            switch_language="ctrl+l",
        )

        assert config.area_select == "ctrl+a"
        assert config.quick_center == "ctrl+q"
        assert config.quick_bottom == "ctrl+w"
        assert config.repeat_last == "ctrl+s"
        assert config.switch_language == "ctrl+l"


class TestLanguageConfig:
    """Test LanguageConfig dataclass."""

    def test_default_values(self):
        """Test default language configuration."""
        config = LanguageConfig()

        assert config.target_languages == ["ru", "en", "ja"]
        assert config.ocr_languages == "eng+rus+jpn"
        assert config.default_target == 0

    def test_custom_values(self):
        """Test custom language configuration."""
        config = LanguageConfig(
            target_languages=["en", "fr", "es"], ocr_languages="eng+fra+spa", default_target=1
        )

        assert config.target_languages == ["en", "fr", "es"]
        assert config.ocr_languages == "eng+fra+spa"
        assert config.default_target == 1


class TestTTSConfig:
    """Test TTSConfig dataclass."""

    def test_default_values(self):
        """Test default TTS configuration."""
        config = TTSConfig()

        assert config.enabled is True
        assert config.rate == 150
        assert config.voice_id == ""
        assert config.audio_device == ""

    def test_custom_values(self):
        """Test custom TTS configuration."""
        config = TTSConfig(
            enabled=False, rate=200, voice_id="en-US-Female", audio_device="device_1"
        )

        assert config.enabled is False
        assert config.rate == 200
        assert config.voice_id == "en-US-Female"
        assert config.audio_device == "device_1"


class TestFeaturesConfig:
    """Test FeaturesConfig dataclass."""

    def test_default_values(self):
        """Test default features configuration."""
        config = FeaturesConfig()

        assert config.copy_to_clipboard is True
        assert config.cache_translations is True
        assert config.save_debug_screenshots is False

    def test_custom_values(self):
        """Test custom features configuration."""
        config = FeaturesConfig(
            copy_to_clipboard=False, cache_translations=False, save_debug_screenshots=True
        )

        assert config.copy_to_clipboard is False
        assert config.cache_translations is False
        assert config.save_debug_screenshots is True


class TestImageProcessingConfig:
    """Test ImageProcessingConfig dataclass."""

    def test_default_values(self):
        """Test default image processing configuration."""
        config = ImageProcessingConfig()

        assert config.upscale_factor == 2.0
        assert config.contrast_enhance == 1.5
        assert config.sharpness_enhance == 2.0
        assert config.ocr_confidence_threshold == 0.7
        assert config.enable_preprocessing is True
        assert config.noise_reduction is True

    def test_custom_values(self):
        """Test custom image processing configuration."""
        config = ImageProcessingConfig(
            upscale_factor=3.0,
            contrast_enhance=2.0,
            sharpness_enhance=1.5,
            ocr_confidence_threshold=0.8,
            enable_preprocessing=False,
            noise_reduction=False,
        )

        assert config.upscale_factor == 3.0
        assert config.contrast_enhance == 2.0
        assert config.sharpness_enhance == 1.5
        assert config.ocr_confidence_threshold == 0.8
        assert config.enable_preprocessing is False
        assert config.noise_reduction is False


class TestAppConfig:
    """Test main AppConfig dataclass."""

    def test_default_initialization(self):
        """Test default app configuration initialization."""
        config = AppConfig()

        assert isinstance(config.hotkeys, HotkeyConfig)
        assert isinstance(config.languages, LanguageConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.features, FeaturesConfig)
        assert isinstance(config.image_processing, ImageProcessingConfig)

    def test_to_dict_conversion(self):
        """Test converting config to dictionary."""
        config = AppConfig()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert "hotkeys" in data
        assert "languages" in data
        assert "tts" in data
        assert "features" in data
        assert "image_processing" in data

        # Check nested structure
        assert isinstance(data["hotkeys"], dict)
        assert "area_select" in data["hotkeys"]
        assert data["hotkeys"]["area_select"] == "alt+a"

    def test_to_dict_with_list_values(self):
        """Test to_dict with list values."""
        config = AppConfig()
        data = config.to_dict()

        # Check that lists are properly converted
        assert isinstance(data["languages"]["target_languages"], list)
        assert data["languages"]["target_languages"] == ["ru", "en", "ja"]

    def test_from_dict_creation(self):
        """Test creating config from dictionary."""
        data = {
            "hotkeys": {"area_select": "ctrl+a", "quick_center": "ctrl+q"},
            "languages": {"target_languages": ["en", "fr"], "default_target": 1},
            "tts": {"enabled": False, "rate": 200},
        }

        config = AppConfig.from_dict(data)

        assert config.hotkeys.area_select == "ctrl+a"
        assert config.hotkeys.quick_center == "ctrl+q"
        assert config.languages.target_languages == ["en", "fr"]
        assert config.languages.default_target == 1
        assert config.tts.enabled is False
        assert config.tts.rate == 200

    def test_from_dict_partial_data(self):
        """Test creating config from partial dictionary."""
        data = {
            "hotkeys": {"area_select": "ctrl+a"}
            # Missing other sections
        }

        config = AppConfig.from_dict(data)

        # Should have custom hotkey
        assert config.hotkeys.area_select == "ctrl+a"
        # Should have defaults for missing hotkeys
        assert config.hotkeys.quick_center == "alt+q"
        # Should have default configs for missing sections
        assert config.languages.target_languages == ["ru", "en", "ja"]

    def test_from_dict_invalid_data(self):
        """Test creating config from invalid dictionary."""
        # Test with invalid data types
        invalid_data = {"hotkeys": "not_a_dict", "languages": 123}

        config = AppConfig.from_dict(invalid_data)

        # Should return default config when parsing fails
        assert config.hotkeys.area_select == "alt+a"
        assert config.languages.target_languages == ["ru", "en", "ja"]

    def test_load_from_nonexistent_file(self):
        """Test loading from nonexistent file."""
        config = AppConfig.load_from_file("nonexistent_file.json")

        # Should return default config
        assert isinstance(config, AppConfig)
        assert config.hotkeys.area_select == "alt+a"

    def test_load_from_valid_file(self):
        """Test loading from valid JSON file."""
        data = {"hotkeys": {"area_select": "ctrl+a"}, "tts": {"enabled": False}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            config = AppConfig.load_from_file(temp_path)

            assert config.hotkeys.area_select == "ctrl+a"
            assert config.tts.enabled is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_invalid_json_file(self):
        """Test loading from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name

        try:
            config = AppConfig.load_from_file(temp_path)

            # Should return default config on JSON parse error
            assert isinstance(config, AppConfig)
            assert config.hotkeys.area_select == "alt+a"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_to_file_success(self):
        """Test successfully saving config to file."""
        config = AppConfig()
        config.hotkeys.area_select = "ctrl+a"
        config.tts.enabled = False

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = config.save_to_file(temp_path)

            assert result is True
            assert Path(temp_path).exists()

            # Verify content
            with open(temp_path, "r") as f:
                data = json.load(f)

            assert data["hotkeys"]["area_select"] == "ctrl+a"
            assert data["tts"]["enabled"] is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_to_file_failure(self):
        """Test saving config to invalid path."""
        config = AppConfig()

        # Try to save to invalid path
        invalid_path = "/root/nonexistent/config.json"
        result = config.save_to_file(invalid_path)

        assert result is False

    def test_round_trip_serialization(self):
        """Test complete round-trip serialization."""
        # Create config with custom values
        original_config = AppConfig()
        original_config.hotkeys.area_select = "ctrl+shift+a"
        original_config.languages.target_languages = ["en", "de", "fr"]
        original_config.tts.rate = 180
        original_config.features.copy_to_clipboard = False
        original_config.image_processing.upscale_factor = 3.5

        # Convert to dict and back
        data = original_config.to_dict()
        restored_config = AppConfig.from_dict(data)

        # Verify all values preserved
        assert restored_config.hotkeys.area_select == "ctrl+shift+a"
        assert restored_config.languages.target_languages == ["en", "de", "fr"]
        assert restored_config.tts.rate == 180
        assert restored_config.features.copy_to_clipboard is False
        assert restored_config.image_processing.upscale_factor == 3.5


class TestConstants:
    """Test module constants."""

    def test_constants_exist(self):
        """Test that all constants are defined."""
        assert DEFAULT_CONFIG_PATH == "config.json"
        assert ICON_PATH == "icon.ico"
        assert DEBUG_MODE is False
        assert MIN_AREA_SIZE == 50

    def test_constants_types(self):
        """Test that constants have correct types."""
        assert isinstance(DEFAULT_CONFIG_PATH, str)
        assert isinstance(ICON_PATH, str)
        assert isinstance(DEBUG_MODE, bool)
        assert isinstance(MIN_AREA_SIZE, int)
