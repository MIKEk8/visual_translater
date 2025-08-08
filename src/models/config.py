import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class HotkeyConfig:
    area_select: str = "alt+a"
    quick_center: str = "alt+q"
    quick_bottom: str = "alt+w"
    repeat_last: str = "alt+s"
    switch_language: str = "alt+l"


@dataclass
class LanguageConfig:
    target_languages: List[str] = field(default_factory=lambda: ["ru", "en", "ja"])
    ocr_languages: str = "eng+rus+jpn"
    default_target: int = 0


@dataclass
class TTSConfig:
    enabled: bool = True
    rate: int = 150
    voice_id: str = ""
    audio_device: str = ""


@dataclass
class FeaturesConfig:
    copy_to_clipboard: bool = True
    cache_translations: bool = True
    save_debug_screenshots: bool = False


@dataclass
class ImageProcessingConfig:
    upscale_factor: float = 2.0
    contrast_enhance: float = 1.5
    sharpness_enhance: float = 2.0
    ocr_confidence_threshold: float = 0.7  # Minimum confidence to accept OCR results
    enable_preprocessing: bool = True  # Enable image preprocessing for better OCR
    noise_reduction: bool = True  # Apply noise reduction filters


@dataclass
class AppConfig:
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    image_processing: ImageProcessingConfig = field(default_factory=ImageProcessingConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""

        def _dataclass_to_dict(obj: Any) -> Any:
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _dataclass_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [_dataclass_to_dict(item) for item in obj]
            else:
                return obj

        result = _dataclass_to_dict(self)
        return result if isinstance(result, dict) else {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create config from dictionary"""
        try:
            return cls(
                hotkeys=HotkeyConfig(**data.get("hotkeys", {})),
                languages=LanguageConfig(**data.get("languages", {})),
                tts=TTSConfig(**data.get("tts", {})),
                features=FeaturesConfig(**data.get("features", {})),
                image_processing=ImageProcessingConfig(**data.get("image_processing", {})),
            )
        except (TypeError, ValueError):
            # Return default config if parsing fails
            return cls()

    @classmethod
    def load_from_file(cls, file_path: str) -> "AppConfig":
        """Load config from JSON file"""
        if not os.path.exists(file_path):
            return cls()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return cls()

    def save_to_file(self, file_path: str) -> bool:
        """Save config to JSON file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False


# Constants
DEFAULT_CONFIG_PATH = "config.json"
ICON_PATH = "icon.ico"
DEBUG_MODE = False
MIN_AREA_SIZE = 50
