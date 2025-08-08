"""
Screen Translator v2.0 - Domain Layer

This package contains the core business logic and domain models.
"""

from .entities.preferences import UserPreferences
from .entities.screenshot import Screenshot

# Entities
from .entities.translation import Translation

# Domain Events
from .events.domain_events import DomainEvent, ScreenshotCaptured, TextExtracted, TranslationCreated

# Domain Exceptions
from .exceptions.domain_exceptions import (
    DomainException,
    InvalidCoordinatesError,
    InvalidLanguageError,
    OCRError,
    ServiceUnavailableError,
    TextTooLongError,
    TranslationError,
)
from .value_objects.coordinates import ScreenCoordinates
from .value_objects.domain_id import DomainId

# Value Objects
from .value_objects.language import Language, LanguagePair
from .value_objects.text import Text, TranslatedText

# Domain Services (pure domain logic only)


__all__ = [
    # Value Objects
    "Language",
    "LanguagePair",
    "Text",
    "TranslatedText",
    "ScreenCoordinates",
    "DomainId",
    # Entities
    "Translation",
    "Screenshot",
    "UserPreferences",
    # Events
    "DomainEvent",
    "TranslationCreated",
    "ScreenshotCaptured",
    "TextExtracted",
    # Exceptions
    "DomainException",
    "InvalidLanguageError",
    "TranslationError",
    "OCRError",
    "InvalidCoordinatesError",
    "TextTooLongError",
    "ServiceUnavailableError",
]
