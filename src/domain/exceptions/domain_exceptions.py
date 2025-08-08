"""
Domain exceptions - business rule violations.
"""


class DomainException(Exception):
    """Base domain exception."""

    pass


class InvalidLanguageError(DomainException):
    """Invalid language code."""

    pass


class TranslationError(DomainException):
    """Translation failed."""

    pass


class OCRError(DomainException):
    """OCR processing failed."""

    pass


class InvalidCoordinatesError(DomainException):
    """Invalid screen coordinates."""

    pass


class TextTooLongError(DomainException):
    """Text exceeds maximum length."""

    pass


class ServiceUnavailableError(DomainException):
    """Required service is unavailable."""

    pass
