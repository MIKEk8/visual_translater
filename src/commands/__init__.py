"""
Command pattern implementations for CQRS architecture.

This module provides command objects that represent user intentions
to modify application state.
"""

from .app_commands import ChangeLanguageCommand, ExportHistoryCommand
from .base_command import Command, CommandResult
from .screenshot_commands import CaptureAreaCommand, CaptureScreenCommand
from .translation_commands import SaveTranslationCommand, TranslateTextCommand
from .tts_commands import ConfigureTTSCommand, SpeakTextCommand

__all__ = [
    "Command",
    "CommandResult",
    "CaptureAreaCommand",
    "CaptureScreenCommand",
    "TranslateTextCommand",
    "SaveTranslationCommand",
    "SpeakTextCommand",
    "ConfigureTTSCommand",
    "ChangeLanguageCommand",
    "ExportHistoryCommand",
]
