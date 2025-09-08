import pytest

from src.commands.base_command import Command, CommandResult
from src.handlers.command_handlers import (
    AppCommandHandler,
    ScreenshotCommandHandler,
    TTSCommandHandler,
    TranslationCommandHandler,
)


class ValidCommand(Command):
    def validate(self) -> bool:
        return True


class InvalidCommand(Command):
    def validate(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_screenshot_handler_success_and_invalid():
    h = ScreenshotCommandHandler()
    ok = await h.handle(ValidCommand())
    assert ok.success and ok.data == {"screenshot": "captured"}
    bad = await h.handle(InvalidCommand())
    assert bad.success is False


@pytest.mark.asyncio
async def test_translation_handler_success():
    h = TranslationCommandHandler()
    ok = await h.handle(ValidCommand())
    assert ok.success and ok.data == {"translation": "completed"}


@pytest.mark.asyncio
async def test_tts_handler_success():
    h = TTSCommandHandler()
    ok = await h.handle(ValidCommand())
    assert ok.success and ok.data == {"speech": "played"}


@pytest.mark.asyncio
async def test_app_handler_success():
    h = AppCommandHandler()
    ok = await h.handle(ValidCommand())
    assert ok.success and ok.data == {"app": "updated"}


