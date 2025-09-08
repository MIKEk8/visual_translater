from src.services.translation_service import (
    TranslationConfig,
    TranslationProvider,
    TranslationService,
)


def test_translate_fallback_no_cache(monkeypatch):
    cfg = TranslationConfig(cache_enabled=True, offline_fallback=True)
    svc = TranslationService(cfg)

    # Force primary backend to raise on first call to trigger fallback
    class Boom:
        def translate(self, *a, **k):
            raise RuntimeError("fail")

    monkeypatch.setattr(svc, "primary_backend", Boom())

    # First call -> fallback to offline, not cached in fallback path
    res1 = svc.translate("hello", source_lang="en", target_lang="ru")
    assert res1.provider == TranslationProvider.OFFLINE
    assert svc.get_cache_size() == 0

    # Second call -> вновь fallback (нет кэша)
    res2 = svc.translate("hello", source_lang="en", target_lang="ru")
    assert res2.provider == TranslationProvider.OFFLINE
    assert svc.get_cache_size() == 0


def test_translate_empty_returns_identity():
    svc = TranslationService(TranslationConfig())
    res = svc.translate("   ", target_lang="ru")
    assert res.translated_text.strip() == ""
    assert res.provider == TranslationProvider.OFFLINE


def test_detect_language_without_backend():
    svc = TranslationService(TranslationConfig())
    svc.primary_backend = None
    assert svc.detect_language("hello") == "unknown"


def test_translate_primary_success_caches():
    # Primary OFFLINE backend succeeds -> caches result
    svc = TranslationService(TranslationConfig(cache_enabled=True))
    res1 = svc.translate("world", source_lang="en", target_lang="ru")
    assert svc.get_cache_size() == 1
    # Second call returns same cached instance
    res2 = svc.translate("world", source_lang="en", target_lang="ru")
    assert res2 is res1


