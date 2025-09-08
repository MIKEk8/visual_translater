"""
Domain exceptions - business rule violations.
"""


class DomainException(Exception):
    """Base domain exception."""


class InvalidLanguageError(DomainException):
    """Invalid language code."""


class TranslationError(DomainException):
    """Translation failed."""


class OCRError(DomainException):
    """OCR processing failed."""


class InvalidCoordinatesError(DomainException):
    """Invalid screen coordinates."""


class TextTooLongError(DomainException):
    """Text exceeds maximum length."""


class ServiceUnavailableError(DomainException):
    """Required service is unavailable."""
