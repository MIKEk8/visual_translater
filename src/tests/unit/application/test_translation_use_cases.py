import asyncio
from types import SimpleNamespace

import pytest

from src.application.use_cases.translation_use_cases import (
    GetTranslationHistoryUseCase,
    TranslateScreenshotUseCase,
    TranslateTextUseCase,
)
from src.application.dto.translation_dto import TranslationRequest
from src.domain.value_objects.language import Language, LanguagePair


class DummyTranslationService:
    async def translate(self, text, language_pair):
        if text == "":
            return ""
        if text == "error":
            raise RuntimeError("fail")
        return f"{text}-to-{language_pair.target.code}"


class DummyCache:
    def __init__(self):
        self.calls = SimpleNamespace(get=0, cache=0)

    def get_cached_translation(self, text, lang_pair):
        self.calls.get += 1
        if text == "cached":
            return SimpleNamespace(
                translated=SimpleNamespace(content="cached-text", confidence=0.9)
            )
        return None

    def cache_translation(self, text, translated_text, lang_pair):
        self.calls.cache += 1


@pytest.mark.asyncio
async def test_translate_text_use_case_cache_hit():
    uc = TranslateTextUseCase(DummyTranslationService(), cache_service=DummyCache())
    req = TranslationRequest(text="cached", source_language="en", target_language="ru")
    resp = await uc.execute(req)
    assert resp is not None and resp.is_cached is True
    assert resp.translated_text == "cached-text"


@pytest.mark.asyncio
async def test_translate_text_use_case_service_used_and_cached():
    cache = DummyCache()
    uc = TranslateTextUseCase(DummyTranslationService(), cache_service=cache)
    req = TranslationRequest(text="hello", source_language="en", target_language="ru")
    resp = await uc.execute(req)
    assert resp is not None and resp.is_cached is False
    assert resp.translated_text.endswith("-to-ru")
    assert cache.calls.cache == 1


@pytest.mark.asyncio
async def test_translate_text_use_case_error_and_none():
    uc = TranslateTextUseCase(DummyTranslationService())
    req = TranslationRequest(text="error", source_language="en", target_language="ru")
    resp = await uc.execute(req)
    assert resp is None


@pytest.mark.asyncio
async def test_translate_text_use_case_empty_result_none():
    uc = TranslateTextUseCase(DummyTranslationService())
    req = TranslationRequest(text="", source_language="en", target_language="ru")
    resp = await uc.execute(req)
    assert resp is None


class DummyWorkflow:
    async def process_screenshot(self, screenshot, language_pair, auto_tts=False):
        if getattr(screenshot, "bad", False):
            raise RuntimeError("fail")
        return SimpleNamespace(to_dict=lambda: {"ok": True, "lang": language_pair.target.code})


@pytest.mark.asyncio
async def test_translate_screenshot_use_case_success():
    uc = TranslateScreenshotUseCase(DummyWorkflow())
    screenshot = SimpleNamespace()
    pair = LanguagePair(Language("en"), Language("ru"))
    resp = await uc.execute(screenshot, pair)
    assert resp == {"ok": True, "lang": "ru"}


@pytest.mark.asyncio
async def test_translate_screenshot_use_case_errors_to_none():
    uc = TranslateScreenshotUseCase(DummyWorkflow())
    screenshot = SimpleNamespace(bad=True)
    pair = LanguagePair(Language("en"), Language("ru"))
    resp = await uc.execute(screenshot, pair)
    assert resp is None


@pytest.mark.asyncio
async def test_translate_text_use_case_cache_miss_then_cache_store():
    class Cache:
        def __init__(self):
            self.stored = []

        def get_cached_translation(self, text, lp):
            return None

        def cache_translation(self, text, translated_text, lp):
            self.stored.append((text, translated_text, lp))

    cache = Cache()
    uc = TranslateTextUseCase(DummyTranslationService(), cache_service=cache)
    req = TranslationRequest(text="hi", source_language="en", target_language="ru")
    resp = await uc.execute(req)
    assert resp is not None and resp.is_cached is False
    assert cache.stored and cache.stored[0][0] == "hi"


@pytest.mark.asyncio
async def test_translate_screenshot_use_case_no_to_dict_returns_none():
    class WF:
        async def process_screenshot(self, s, lp, auto_tts=False):
            return object()  # no to_dict

    uc = TranslateScreenshotUseCase(WF())
    screenshot = SimpleNamespace()
    pair = LanguagePair(Language("en"), Language("ru"))
    resp = await uc.execute(screenshot, pair)
    assert resp is None


class DummyRepo:
    def __init__(self):
        self.requested = None

    async def get_recent(self, limit):
        self.requested = limit
        return ["a", "b"]


@pytest.mark.asyncio
async def test_get_history_use_case_pass_through():
    repo = DummyRepo()
    uc = GetTranslationHistoryUseCase(repo)
    items = await uc.execute(limit=5)
    assert items == ["a", "b"]
    assert repo.requested == 5


