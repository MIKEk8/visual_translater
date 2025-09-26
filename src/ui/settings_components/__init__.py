"""Settings window components for modular architecture."""

from .base_settings_tab import BaseSettingsTab
from .hotkeys_tab import HotkeysTab
from .general_tab import GeneralTab
from .ocr_tab import OCRTab
from .tts_tab import TTSTab
from .batch_processing_tab import BatchProcessingTab
from .advanced_tab import AdvancedTab

__all__ = [
    'BaseSettingsTab',
    'HotkeysTab',
    'GeneralTab',
    'OCRTab',
    'TTSTab',
    'BatchProcessingTab',
    'AdvancedTab'
]