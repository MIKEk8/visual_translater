"""
AI/ML components for Screen Translator.

This module provides artificial intelligence and machine learning
capabilities including smart area detection, text recognition
enhancement, and intelligent translation optimization.
"""

from .smart_area_detection import (
    DetectionConfig,
    DetectionMethod,
    SmartAreaDetector,
    TextRegion,
)

__all__ = [
    "SmartAreaDetector",
    "TextRegion",
    "DetectionMethod",
    "DetectionConfig",
]
