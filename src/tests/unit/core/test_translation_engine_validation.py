import pytest

from src.core.translation_engine import GoogleTranslationEngine
from src.utils.exceptions import (
    TranslationEngineNotAvailableError,
    TranslationFailedError,
    UnsupportedLanguageError,
)


def test_validate_raises_not_available(monkeypatch):
    eng = GoogleTranslationEngine()
    # Force translator None
    monkeypatch.setattr(eng, "translator", None)
    with pytest.raises(TranslationEngineNotAvailableError):
        eng._validate_translation_request("hi", "en", "auto")


def test_validate_raises_empty_text(monkeypatch):
    eng = GoogleTranslationEngine()
    # Ensure translator exists to pass first check
    monkeypatch.setattr(eng, "translator", object())
    with pytest.raises(TranslationFailedError):
        eng._validate_translation_request("   ", "en", "auto")


def test_validate_raises_unsupported_lang(monkeypatch):
    eng = GoogleTranslationEngine()
    monkeypatch.setattr(eng, "translator", object())
    # Limit supported languages to small set
    monkeypatch.setattr(eng, "get_supported_languages", lambda: ["en", "ru"])  # type: ignore
    with pytest.raises(UnsupportedLanguageError):
        eng._validate_translation_request("x", "zz", "en")


