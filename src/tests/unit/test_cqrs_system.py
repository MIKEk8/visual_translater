"""
Comprehensive tests for CQRS (Command Query Responsibility Segregation) system.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.commands.app_commands import BackupDataCommand, UpdateConfigCommand
from src.commands.base_command import Command, CommandResult
from src.commands.screenshot_commands import CaptureAreaCommand, CaptureScreenCommand
from src.commands.translation_commands import BatchTranslateCommand, TranslateTextCommand
from src.commands.tts_commands import ConfigureTTSCommand, SpeakTextCommand
from src.handlers.base_handler import CommandHandler, QueryHandler
from src.queries.base_query import Query, QueryResult
from src.queries.translation_queries import (
    GetTranslationHistoryQuery,
    GetTranslationStatsQuery,
    SearchTranslationsQuery,
)


class TestBaseCommand:
    """Test base Command class functionality"""

    def test_command_creation(self):
        """Test basic command creation"""
        cmd = TranslateTextCommand(text="Hello", target_language="es")

        assert cmd.text == "Hello"
        assert cmd.target_language == "es"
        assert cmd.source_language == "auto"  # default
        assert cmd.command_id.startswith("cmd_")
        assert isinstance(cmd.timestamp, datetime)

    def test_command_validation_success(self):
        """Test successful command validation"""
        cmd = TranslateTextCommand(text="Hello world", target_language="es")
        assert cmd.validate() == True

    def test_command_validation_failure(self):
        """Test command validation failure"""
        # Empty text should fail validation
        cmd = TranslateTextCommand(text="", target_language="es")
        assert cmd.validate() == False

        # Missing target language should fail
        cmd = TranslateTextCommand(text="Hello", target_language="")
        assert cmd.validate() == False

    def test_command_type(self):
        """Test command type identification"""
        cmd = TranslateTextCommand(text="Hello", target_language="es", source_language="en")

        command_type = cmd.get_command_type()

        assert command_type == "TranslateTextCommand"
        assert cmd.text == "Hello"
        assert cmd.target_language == "es"
        assert cmd.source_language == "en"
        assert cmd.command_id.startswith("cmd_")
        assert isinstance(cmd.timestamp, datetime)

    def test_command_metadata(self):
        """Test command metadata handling"""
        cmd = TranslateTextCommand(
            text="Hello", target_language="es", source_language="en", metadata={"test": "data"}
        )

        assert cmd.text == "Hello"
        assert cmd.target_language == "es"
        assert cmd.source_language == "en"
        assert cmd.metadata == {"test": "data"}
        assert cmd.user_id is None  # default


class TestScreenshotCommands:
    """Test screenshot-related commands"""

    def test_capture_area_command(self):
        """Test capture area command"""
        cmd = CaptureAreaCommand(x=10, y=20, width=100, height=50)

        assert cmd.x == 10
        assert cmd.y == 20
        assert cmd.width == 100
        assert cmd.height == 50
        assert cmd.validate() == True

    def test_capture_area_command_validation(self):
        """Test capture area command validation"""
        # Valid command
        valid_cmd = CaptureAreaCommand(x=0, y=0, width=100, height=50)
        assert valid_cmd.validate() == True

        # Invalid dimensions
        invalid_cmd = CaptureAreaCommand(x=10, y=20, width=0, height=50)
        assert invalid_cmd.validate() == False

        # Negative coordinates should be valid (multi-monitor)
        negative_cmd = CaptureAreaCommand(x=-100, y=-50, width=200, height=100)
        assert negative_cmd.validate() == True

    def test_capture_screen_command(self):
        """Test capture screen command"""
        cmd = CaptureScreenCommand(capture_type="full")

        assert cmd.capture_type == "full"
        assert cmd.validate() == True

        # Default capture
        default_cmd = CaptureScreenCommand()
        assert default_cmd.capture_type == "full"
        assert default_cmd.validate() == True

    def test_screenshot_command_coordinates_property(self):
        """Test coordinates property of area command"""
        cmd = CaptureAreaCommand(x=10, y=20, width=100, height=50)
        coordinates = cmd.coordinates

        assert coordinates == (10, 20, 110, 70)  # x1, y1, x2, y2

    def test_screenshot_command_area_property(self):
        """Test area property of area command"""
        cmd = CaptureAreaCommand(x=10, y=20, width=100, height=50)
        area = cmd.area

        assert area == 5000  # width * height


class TestTranslationCommands:
    """Test translation-related commands"""

    def test_translate_text_command(self):
        """Test basic text translation command"""
        cmd = TranslateTextCommand(text="Hello world", target_language="es", source_language="en")

        assert cmd.text == "Hello world"
        assert cmd.target_language == "es"
        assert cmd.source_language == "en"
        assert cmd.validate() == True

    def test_translate_text_command_auto_detection(self):
        """Test translation command with auto language detection"""
        cmd = TranslateTextCommand(text="Hello world", target_language="es")

        assert cmd.source_language == "auto"
        assert cmd.validate() == True

    def test_batch_translate_command(self):
        """Test batch translation command"""
        texts = ["Hello", "World", "How are you?"]
        cmd = BatchTranslateCommand(texts=texts, target_language="es", source_language="en")

        assert cmd.texts == texts
        assert cmd.target_language == "es"
        assert cmd.source_language == "en"
        assert cmd.validate() == True

    def test_batch_translate_command_validation(self):
        """Test batch translation command validation"""
        # Valid batch
        valid_cmd = BatchTranslateCommand(texts=["Hello", "World"], target_language="es")
        assert valid_cmd.validate() == True

        # Empty batch should fail
        empty_cmd = BatchTranslateCommand(texts=[], target_language="es")
        assert empty_cmd.validate() == False

        # Texts with empty strings should fail
        invalid_cmd = BatchTranslateCommand(texts=["Hello", "", "World"], target_language="es")
        assert invalid_cmd.validate() == False

    def test_translate_command_length_limits(self):
        """Test translation command text length limits"""
        # Normal text should pass
        normal_cmd = TranslateTextCommand(text="Hello world", target_language="es")
        assert normal_cmd.validate() == True

        # Very long text should fail
        long_text = "A" * 10000  # 10k characters
        long_cmd = TranslateTextCommand(text=long_text, target_language="es")
        assert long_cmd.validate() == False


class TestTTSCommands:
    """Test TTS-related commands"""

    def test_speak_text_command(self):
        """Test speak text command"""
        cmd = SpeakTextCommand(text="Hello world", voice_id="voice_1", rate=150, volume=0.8)

        assert cmd.text == "Hello world"
        assert cmd.voice_id == "voice_1"
        assert cmd.rate == 150
        assert cmd.volume == 0.8
        assert cmd.validate() == True

    def test_speak_text_command_defaults(self):
        """Test speak text command with defaults"""
        cmd = SpeakTextCommand(text="Hello world")

        assert cmd.text == "Hello world"
        assert cmd.voice_id is None  # Use default voice
        assert cmd.rate is None  # Default rate (uses 200 in estimation)
        assert cmd.volume is None  # Default volume
        assert cmd.language == "en"  # Default language
        assert cmd.validate() == True

    def test_speak_text_command_validation(self):
        """Test speak text command validation"""
        # Valid command
        valid_cmd = SpeakTextCommand(text="Hello", rate=150, volume=0.5)
        assert valid_cmd.validate() == True

        # Empty text should fail
        empty_cmd = SpeakTextCommand(text="")
        assert empty_cmd.validate() == False

        # Invalid rate should fail
        invalid_rate_cmd = SpeakTextCommand(text="Hello", rate=-50)
        assert invalid_rate_cmd.validate() == False

        # Invalid volume should fail
        invalid_volume_cmd = SpeakTextCommand(text="Hello", volume=1.5)
        assert invalid_volume_cmd.validate() == False

    def test_configure_tts_command(self):
        """Test configure TTS command"""
        cmd = ConfigureTTSCommand(enabled=True, rate=200, volume=1.0)

        assert cmd.enabled == True
        assert cmd.rate == 200
        assert cmd.volume == 1.0
        assert cmd.validate() == True

    def test_configure_tts_command_validation(self):
        """Test configure TTS command validation"""
        # Valid command
        valid_cmd = ConfigureTTSCommand(enabled=True, rate=150)
        assert valid_cmd.validate() == True

        # Invalid rate should fail
        invalid_cmd = ConfigureTTSCommand(rate=500)
        assert invalid_cmd.validate() == False


class TestAppCommands:
    """Test application-level commands"""

    def test_update_config_command(self):
        """Test update configuration command"""
        config_updates = {
            "hotkeys": {"capture": "Ctrl+Shift+S"},
            "languages": {"source": "en", "target": "es"},
        }

        cmd = UpdateConfigCommand(config_updates=config_updates)

        assert cmd.config_updates == config_updates
        assert cmd.merge_with_existing == True
        assert cmd.validate() == True

    def test_update_config_command_validation(self):
        """Test update configuration command validation"""
        # Valid command
        valid_cmd = UpdateConfigCommand(config_updates={"test": "data"})
        assert valid_cmd.validate() == True

        # Empty config should fail
        empty_cmd = UpdateConfigCommand()
        empty_cmd.config_updates = {}
        assert empty_cmd.validate() == False

    def test_backup_data_command(self):
        """Test backup data command"""
        cmd = BackupDataCommand(backup_path="/path/to/backup.zip")

        assert cmd.backup_path == "/path/to/backup.zip"
        assert cmd.include_config == True
        assert cmd.validate() == True

    def test_backup_data_command_validation(self):
        """Test backup data command validation"""
        # Valid command
        valid_cmd = BackupDataCommand(backup_path="/valid/path.zip")
        assert valid_cmd.validate() == True

        # Empty path should fail
        empty_cmd = BackupDataCommand(backup_path="")
        assert empty_cmd.validate() == False


class TestBaseQuery:
    """Test base Query class functionality"""

    def test_query_creation(self):
        """Test basic query creation"""
        query = GetTranslationHistoryQuery(limit=50, include_failed=True)

        assert query.limit == 50
        assert query.include_failed == True
        assert query.query_id.startswith("qry_")
        assert isinstance(query.timestamp, datetime)

    def test_query_validation(self):
        """Test query validation"""
        # Valid query
        valid_query = GetTranslationHistoryQuery(limit=10)
        assert valid_query.validate() == True

        # Invalid limit should fail
        invalid_query = GetTranslationHistoryQuery(limit=-5)
        assert invalid_query.validate() == False

    def test_query_type(self):
        """Test query type identification"""
        query = GetTranslationHistoryQuery(limit=25, include_failed=False)

        query_type = query.get_query_type()

        assert query_type == "GetTranslationHistoryQuery"
        assert query.limit == 25
        assert query.include_failed == False
        assert query.query_id.startswith("qry_")
        assert isinstance(query.timestamp, datetime)


class TestTranslationQueries:
    """Test translation-related queries"""

    def test_get_translation_history_query(self):
        """Test translation history query"""
        query = GetTranslationHistoryQuery(limit=100, include_failed=True, language_filter="en")

        assert query.limit == 100
        assert query.include_failed == True
        assert query.language_filter == "en"
        assert query.validate() == True

    def test_search_translations_query(self):
        """Test search translations query"""
        query = SearchTranslationsQuery(search_text="hello", search_in="both", min_confidence=0.8)

        assert query.search_text == "hello"
        assert query.search_in == "both"
        assert query.min_confidence == 0.8
        assert query.validate() == True

    def test_search_translations_query_validation(self):
        """Test search translations query validation"""
        # Valid query
        valid_query = SearchTranslationsQuery(search_text="hello")
        assert valid_query.validate() == True

        # Empty search term should fail
        empty_query = SearchTranslationsQuery(search_text="")
        assert empty_query.validate() == False

        # Invalid confidence range should fail
        invalid_query = SearchTranslationsQuery(search_text="hello", min_confidence=1.5)
        assert invalid_query.validate() == False

    def test_get_translation_stats_query(self):
        """Test translation statistics query"""
        query = GetTranslationStatsQuery(time_range_days=30, group_by="day")

        assert query.time_range_days == 30
        assert query.group_by == "day"
        assert query.validate() == True

    def test_translation_stats_query_validation(self):
        """Test translation statistics query validation"""
        # Valid group_by values
        for group_by in ["hour", "day", "week", "month"]:
            query = GetTranslationStatsQuery(group_by=group_by)
            assert query.validate() == True

        # Invalid group_by should fail
        invalid_query = GetTranslationStatsQuery(group_by="invalid")
        assert invalid_query.validate() == False


class TestCommandResult:
    """Test CommandResult class"""

    def test_command_result_success(self):
        """Test successful command result"""
        result = CommandResult(
            success=True, data={"translated_text": "Hola"}, execution_time_ms=500.0
        )

        assert result.success == True
        assert result.data == {"translated_text": "Hola"}
        assert result.execution_time_ms == 500.0
        assert result.error is None

    def test_command_result_failure(self):
        """Test failed command result"""
        result = CommandResult(
            success=False, error="Translation API unavailable", execution_time_ms=2000.0
        )

        assert result.success == False
        assert result.error == "Translation API unavailable"
        assert result.execution_time_ms == 2000.0
        assert result.data is None


class TestQueryResult:
    """Test QueryResult class"""

    def test_query_result_success(self):
        """Test successful query result"""
        translations = [
            {"original": "Hello", "translated": "Hola"},
            {"original": "World", "translated": "Mundo"},
        ]

        result = QueryResult(
            success=True, data=translations, total_count=2, execution_time_ms=100.0
        )

        assert result.success == True
        assert result.data == translations
        assert result.total_count == 2
        assert result.execution_time_ms == 100.0
        assert result.error is None

    def test_query_result_failure(self):
        """Test failed query result"""
        result = QueryResult(
            success=False, error="Database connection failed", execution_time_ms=5000.0
        )

        assert result.success == False
        assert result.error == "Database connection failed"
        assert result.execution_time_ms == 5000.0
        assert result.data is None
        assert result.total_count is None


class TestCommandHandler:
    """Test CommandHandler base class"""

    @pytest.fixture
    def mock_handler(self):
        """Create mock command handler"""

        class MockCommandHandler(CommandHandler):
            def __init__(self):
                super().__init__("MockCommandHandler")

            async def _execute(self, command: Command) -> CommandResult:
                return CommandResult.success_result(
                    data={"result": f"Handled {command.__class__.__name__}"}
                )

        return MockCommandHandler()

    @pytest.mark.asyncio
    async def test_command_handler_execution(self, mock_handler):
        """Test command handler execution"""
        command = TranslateTextCommand(text="Hello", target_language="es")

        result = await mock_handler.handle(command)

        assert result.success == True
        assert result.data == {"result": "Handled TranslateTextCommand"}
        assert result.execution_time_ms > 0  # Should have some execution time

    @pytest.mark.asyncio
    async def test_command_handler_validation(self, mock_handler):
        """Test command handler validates commands"""
        # Valid command should work
        valid_command = TranslateTextCommand(text="Hello", target_language="es")
        result = await mock_handler.handle(valid_command)
        assert result.success == True

        # Invalid command should fail
        invalid_command = TranslateTextCommand(text="", target_language="es")
        result = await mock_handler.handle(invalid_command)
        assert result.success == False
        assert "Invalid command" in result.error


class TestQueryHandler:
    """Test QueryHandler base class"""

    @pytest.fixture
    def mock_handler(self):
        """Create mock query handler"""

        class MockQueryHandler(QueryHandler):
            def __init__(self):
                super().__init__("MockQueryHandler")

            async def _execute(self, query: Query) -> QueryResult:
                return QueryResult.success_result(data=[{"mock": "data"}], total_count=1)

        return MockQueryHandler()

    @pytest.mark.asyncio
    async def test_query_handler_execution(self, mock_handler):
        """Test query handler execution"""
        query = GetTranslationHistoryQuery(limit=10)

        result = await mock_handler.handle(query)

        assert result.success == True
        assert result.data == [{"mock": "data"}]
        assert result.total_count == 1
        assert result.execution_time_ms > 0  # Should have some execution time

    @pytest.mark.asyncio
    async def test_query_handler_validation(self, mock_handler):
        """Test query handler validates queries"""
        # Valid query should work
        valid_query = GetTranslationHistoryQuery(limit=10)
        result = await mock_handler.handle(valid_query)
        assert result.success == True

        # Invalid query should fail
        invalid_query = GetTranslationHistoryQuery(limit=-5)
        result = await mock_handler.handle(invalid_query)
        assert result.success == False
        assert "Invalid query" in result.error


class TestCQRSIntegration:
    """Integration tests for CQRS system"""

    @pytest.mark.asyncio
    async def test_command_query_separation(self):
        """Test that commands and queries are properly separated"""
        # Commands modify state
        translate_command = TranslateTextCommand(text="Hello", target_language="es")
        update_command = UpdateConfigCommand(config_updates={"test": "data"})

        # Queries read state
        history_query = GetTranslationHistoryQuery(limit=10)
        search_query = SearchTranslationsQuery(search_text="hello")

        # Commands should have different interface than queries
        assert hasattr(translate_command, "validate")
        assert hasattr(update_command, "validate")
        assert hasattr(history_query, "validate")
        assert hasattr(search_query, "validate")

        # Commands and queries should have different types
        assert isinstance(translate_command, Command)
        assert isinstance(update_command, Command)
        assert isinstance(history_query, Query)
        assert isinstance(search_query, Query)

    @pytest.mark.asyncio
    async def test_command_query_flow(self):
        """Test typical command -> query flow"""
        # 1. Execute command to modify state
        translate_command = TranslateTextCommand(text="Hello", target_language="es")

        # Mock command execution
        command_result = CommandResult(
            success=True, data={"translated": "Hola", "confidence": 0.95}, execution_time_ms=300.0
        )

        # 2. Query to read modified state
        history_query = GetTranslationHistoryQuery(limit=1)

        # Mock query execution
        query_result = QueryResult(
            success=True,
            data=[
                {
                    "original": "Hello",
                    "translated": "Hola",
                    "confidence": 0.95,
                    "timestamp": datetime.now(),
                }
            ],
            total_count=1,
            execution_time_ms=50.0,
        )

        # Verify results
        assert command_result.success == True
        assert query_result.success == True
        assert query_result.data[0]["translated"] == "Hola"


class TestCQRSPerformance:
    """Test CQRS system performance characteristics"""

    @pytest.mark.asyncio
    async def test_command_creation_performance(self):
        """Test performance of creating many commands"""
        start_time = time.time()

        commands = []
        for i in range(1000):
            cmd = TranslateTextCommand(text=f"Text {i}", target_language="es", source_language="en")
            commands.append(cmd)

        end_time = time.time()

        # Should create 1000 commands quickly
        assert end_time - start_time < 1.0
        assert len(commands) == 1000

        # All commands should be valid
        for cmd in commands[:10]:  # Check first 10
            assert cmd.validate() == True

    @pytest.mark.asyncio
    async def test_query_creation_performance(self):
        """Test performance of creating many queries"""
        start_time = time.time()

        queries = []
        for i in range(1000):
            query = GetTranslationHistoryQuery(limit=10 + i % 100, include_failed=i % 2 == 0)
            queries.append(query)

        end_time = time.time()

        # Should create 1000 queries quickly
        assert end_time - start_time < 1.0
        assert len(queries) == 1000

        # All queries should be valid
        for query in queries[:10]:  # Check first 10
            assert query.validate() == True
