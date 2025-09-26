"""AI-powered OCR engine for Screen Translator v2.0.

This module provides a clean interface to the refactored AI OCR components.
The original 812-line God Class has been broken down into modular components.
"""

# Re-export the main classes for backward compatibility
from src.core.text_detection import TextDetector, TextRegion
from src.core.image_enhancement import ImageEnhancer
from src.core.ai_ocr_plugin import AIEnhancedOCRPlugin, AIEnhancedOCR

__all__ = [
    'TextDetector',
    'TextRegion',
    'ImageEnhancer',
    'AIEnhancedOCRPlugin',
    'AIEnhancedOCR'
]