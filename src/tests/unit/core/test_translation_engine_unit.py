from types import SimpleNamespace

from src.core.translation_engine import TranslationProcessor, TranslationEngine


class StubEngine(TranslationEngine):
    def __init__(self, available=True):
        self._available = available

    def translate(self, text: str, target_language: str, source_language: str = "auto"):
        return f"{text}|{source_language}->{target_language}"

    def get_supported_languages(self):
        return ["en", "ru"]

    def is_available(self) -> bool:
        return self._available


def test_processor_uses_cache_and_engine(monkeypatch):
    # Prepare processor with stub engine injected
    proc = TranslationProcessor(cache_enabled=True)
    proc.engines = [StubEngine(available=True)]
    proc.active_engine = proc._get_available_engine()

    # First call fills cache
    t1 = proc.translate_text("Hello", "ru", "en")
    assert t1 is not None and t1.cached is False

    # Second call hits cache
    t2 = proc.translate_text("Hello", "ru", "en")
    assert t2 is not None and t2.cached is True


def test_processor_returns_none_when_no_engine():
    proc = TranslationProcessor(cache_enabled=False)
    proc.engines = []
    proc.active_engine = proc._get_available_engine()
    assert proc.translate_text("x", "ru") is None


