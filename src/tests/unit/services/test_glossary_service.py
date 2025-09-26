"""
Tests for Context Glossaries functionality (game-specific translations).

FEATURE: Context Glossaries (Game-specific Terms)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from typing import Dict, List, Optional

# CRITICAL: Import paths will fail until implementation exists
from src.services.glossary_service import (
    GlossaryService,
    Glossary,
    GlossaryTerm,
    TermReplacementError
)
from src.domain.entities.glossary import Glossary as GlossaryEntity


class TestGlossaryTerm:
    """Test GlossaryTerm data structure."""

    def test_glossary_term_creation(self):
        """Test GlossaryTerm creation with context."""
        term = GlossaryTerm(
            original="Traveler",
            translation="Путешественник",
            context="character",
            priority=1
        )

        assert term.original == "Traveler"
        assert term.translation == "Путешественник"
        assert term.context == "character"
        assert term.priority == 1

    def test_glossary_term_case_sensitivity(self):
        """Test case sensitivity handling in terms."""
        term = GlossaryTerm(
            original="Primogem",
            translation="Примогем",
            case_sensitive=False
        )

        assert term.matches("primogem") is True
        assert term.matches("PRIMOGEM") is True
        assert term.matches("PrimoGem") is True

        case_sensitive_term = GlossaryTerm(
            original="Resin",
            translation="Смола",
            case_sensitive=True
        )

        assert case_sensitive_term.matches("resin") is False
        assert case_sensitive_term.matches("Resin") is True

    def test_glossary_term_priority_comparison(self):
        """Test term priority for replacement order."""
        high_priority = GlossaryTerm("test", "тест1", priority=1)
        low_priority = GlossaryTerm("test", "тест2", priority=5)

        # Higher priority (lower number) should come first
        assert high_priority < low_priority
        assert not (low_priority < high_priority)


class TestGlossary:
    """Test Glossary container class."""

    def test_glossary_creation(self):
        """Test Glossary creation with metadata."""
        terms = [
            GlossaryTerm("Traveler", "Путешественник"),
            GlossaryTerm("Primogem", "Примогем")
        ]

        glossary = Glossary(
            name="Genshin Impact",
            version="1.0",
            game="genshin_impact",
            terms=terms,
            language_pair=("en", "ru")
        )

        assert glossary.name == "Genshin Impact"
        assert glossary.version == "1.0"
        assert glossary.game == "genshin_impact"
        assert len(glossary.terms) == 2
        assert glossary.language_pair == ("en", "ru")

    def test_glossary_term_lookup(self):
        """Test efficient term lookup in glossary."""
        terms = [
            GlossaryTerm("Traveler", "Путешественник"),
            GlossaryTerm("Vision", "Видение"),
            GlossaryTerm("Resin", "Смола")
        ]

        glossary = Glossary("Test", "1.0", "test_game", terms)

        # Test direct lookup
        assert glossary.get_term("Traveler") is not None
        assert glossary.get_term("Traveler").translation == "Путешественник"

        # Test non-existent term
        assert glossary.get_term("NonExistent") is None

    def test_glossary_validation(self):
        """Test glossary validation rules."""
        # Test empty name
        with pytest.raises(ValueError, match="Glossary name cannot be empty"):
            Glossary("", "1.0", "test", [])

        # Test invalid language pair
        with pytest.raises(ValueError, match="Invalid language pair"):
            Glossary("Test", "1.0", "test", [], language_pair=("invalid",))


class TestGlossaryService:
    """Test suite for GlossaryService."""

    @pytest.fixture
    def mock_glossaries_path(self, tmp_path):
        """Create temporary glossaries directory."""
        glossaries_dir = tmp_path / "glossaries"
        glossaries_dir.mkdir()
        return glossaries_dir

    @pytest.fixture
    def glossary_service(self, mock_glossaries_path):
        """Create GlossaryService with temporary directory."""
        return GlossaryService(glossaries_path=mock_glossaries_path)

    @pytest.fixture
    def sample_glossary_data(self):
        """Sample glossary JSON data."""
        return {
            "name": "Genshin Impact",
            "version": "1.0",
            "game": "genshin_impact",
            "language_pair": ["en", "ru"],
            "terms": [
                {
                    "original": "Traveler",
                    "translation": "Путешественник",
                    "context": "character",
                    "priority": 1
                },
                {
                    "original": "Primogem",
                    "translation": "Примогем",
                    "context": "currency",
                    "priority": 2
                },
                {
                    "original": "Original Resin",
                    "translation": "Изначальная смола",
                    "context": "resource",
                    "priority": 1
                }
            ]
        }

    # CRITICAL: Service initialization and glossary loading
    def test_service_initialization(self, glossary_service, mock_glossaries_path):
        """Test service initializes with glossaries directory."""
        assert glossary_service.glossaries_path == mock_glossaries_path
        assert glossary_service.active_glossary is None
        assert glossary_service.available_glossaries == []

    def test_load_glossary_from_file(self, glossary_service, mock_glossaries_path, sample_glossary_data):
        """Test loading glossary from JSON file."""
        # Create sample glossary file
        glossary_file = mock_glossaries_path / "genshin_impact.json"
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(sample_glossary_data, f, ensure_ascii=False)

        loaded_glossary = glossary_service.load_glossary("genshin_impact.json")

        assert loaded_glossary is not None
        assert loaded_glossary.name == "Genshin Impact"
        assert loaded_glossary.game == "genshin_impact"
        assert len(loaded_glossary.terms) == 3

    def test_load_nonexistent_glossary(self, glossary_service):
        """Test loading non-existent glossary fails gracefully."""
        result = glossary_service.load_glossary("nonexistent.json")

        assert result is None

    def test_discover_available_glossaries(self, glossary_service, mock_glossaries_path, sample_glossary_data):
        """Test discovery of available glossary files."""
        # Create multiple glossary files
        for game in ["genshin_impact", "honkai_star_rail", "final_fantasy"]:
            glossary_data = sample_glossary_data.copy()
            glossary_data["game"] = game
            glossary_data["name"] = game.replace("_", " ").title()

            glossary_file = mock_glossaries_path / f"{game}.json"
            with open(glossary_file, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f)

        glossary_service.discover_glossaries()

        # CRITICAL: Should find all glossary files
        assert len(glossary_service.available_glossaries) == 3
        game_names = [g.game for g in glossary_service.available_glossaries]
        assert "genshin_impact" in game_names
        assert "honkai_star_rail" in game_names
        assert "final_fantasy" in game_names

    # CRITICAL: Term replacement functionality
    def test_apply_glossary_basic_replacement(self, glossary_service):
        """Test basic term replacement functionality."""
        terms = [
            GlossaryTerm("Traveler", "Путешественник"),
            GlossaryTerm("Primogem", "Примогем")
        ]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        original_text = "Hello, I am Traveler"
        translated_text = "Привет, я Traveler"

        result = glossary_service.apply_glossary(original_text, translated_text)

        # CRITICAL: Should replace game-specific terms
        assert "Путешественник" in result
        assert "Traveler" not in result

    def test_apply_glossary_multiple_terms(self, glossary_service):
        """Test replacement of multiple terms in one text."""
        terms = [
            GlossaryTerm("Traveler", "Путешественник"),
            GlossaryTerm("Primogem", "Примогем"),
            GlossaryTerm("Resin", "Смола")
        ]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        original_text = "Traveler needs Primogem and Resin"
        translated_text = "Traveler нужен Primogem и Resin"

        result = glossary_service.apply_glossary(original_text, translated_text)

        # CRITICAL: Should replace all matching terms
        assert "Путешественник" in result
        assert "Примогем" in result
        assert "Смола" in result
        assert "Traveler" not in result
        assert "Primogem" not in result
        assert "Resin" not in result

    def test_apply_glossary_priority_ordering(self, glossary_service):
        """Test term replacement respects priority ordering."""
        terms = [
            GlossaryTerm("Original Resin", "Изначальная смола", priority=1),  # Higher priority
            GlossaryTerm("Resin", "Смола", priority=2)  # Lower priority
        ]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        original_text = "You need Original Resin"
        translated_text = "Тебе нужна Original Resin"

        result = glossary_service.apply_glossary(original_text, translated_text)

        # CRITICAL: Should use higher priority term (longer match)
        assert "Изначальная смола" in result
        assert "Original Resin" not in result

    def test_apply_glossary_case_insensitive(self, glossary_service):
        """Test case-insensitive term replacement."""
        terms = [
            GlossaryTerm("primogem", "Примогем", case_sensitive=False)
        ]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        test_cases = [
            ("Need primogem", "Нужен primogem"),
            ("Need PRIMOGEM", "Нужен PRIMOGEM"),
            ("Need PrimoGem", "Нужен PrimoGem")
        ]

        for original, translated in test_cases:
            result = glossary_service.apply_glossary(original, translated)
            assert "Примогем" in result

    def test_apply_glossary_context_awareness(self, glossary_service):
        """Test context-aware term replacement."""
        terms = [
            GlossaryTerm("Vision", "Видение", context="game_mechanic"),
            GlossaryTerm("vision", "зрение", context="general")  # Different context
        ]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        # When game context is active, should use game-specific term
        game_text = "Получил новое Vision"
        result = glossary_service.apply_glossary_with_context("", game_text, "game_mechanic")

        assert "Видение" in result

    def test_apply_glossary_no_active_glossary(self, glossary_service):
        """Test that no replacement occurs when no glossary is active."""
        original_text = "Hello Traveler"
        translated_text = "Привет Traveler"

        result = glossary_service.apply_glossary(original_text, translated_text)

        # CRITICAL: Should return unchanged text when no glossary active
        assert result == translated_text

    # CRITICAL: Glossary management
    def test_activate_glossary_by_game(self, glossary_service, mock_glossaries_path, sample_glossary_data):
        """Test activating glossary by game name."""
        # Create glossary file
        glossary_file = mock_glossaries_path / "genshin_impact.json"
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(sample_glossary_data, f)

        glossary_service.discover_glossaries()

        result = glossary_service.activate_glossary_for_game("genshin_impact")

        assert result is True
        assert glossary_service.active_glossary is not None
        assert glossary_service.active_glossary.game == "genshin_impact"

    def test_activate_nonexistent_glossary(self, glossary_service):
        """Test activating non-existent glossary fails gracefully."""
        result = glossary_service.activate_glossary_for_game("nonexistent_game")

        assert result is False
        assert glossary_service.active_glossary is None

    def test_deactivate_glossary(self, glossary_service):
        """Test deactivating current glossary."""
        # Set up active glossary
        terms = [GlossaryTerm("test", "тест")]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        glossary_service.deactivate_glossary()

        assert glossary_service.active_glossary is None

    # CRITICAL: Performance with large glossaries
    def test_large_glossary_performance(self, glossary_service):
        """Test performance with large glossaries (1000+ terms)."""
        # Create large glossary
        terms = []
        for i in range(1000):
            terms.append(GlossaryTerm(f"term{i}", f"термин{i}"))

        large_glossary = Glossary("Large Test", "1.0", "test", terms)
        glossary_service.active_glossary = large_glossary

        # Test text with multiple terms
        original_text = "This contains term1, term500, and term999"
        translated_text = "Это содержит term1, term500, и term999"

        import time
        start_time = time.time()

        result = glossary_service.apply_glossary(original_text, translated_text)

        processing_time = time.time() - start_time

        # CRITICAL: Large glossary processing should complete under 100ms
        assert processing_time < 0.1
        assert "термин1" in result
        assert "термин500" in result
        assert "термин999" in result

    # CRITICAL: Error handling and validation
    def test_malformed_glossary_file_handling(self, glossary_service, mock_glossaries_path):
        """Test handling of malformed JSON glossary files."""
        # Create malformed JSON file
        bad_file = mock_glossaries_path / "malformed.json"
        with open(bad_file, 'w') as f:
            f.write('{"invalid": json content}')

        with patch('src.utils.logger.Logger') as mock_logger:
            result = glossary_service.load_glossary("malformed.json")

            assert result is None
            mock_logger.error.assert_called()

    def test_glossary_validation_on_load(self, glossary_service, mock_glossaries_path):
        """Test validation of glossary data on load."""
        # Create glossary with missing required fields
        invalid_data = {
            "name": "",  # Empty name
            "terms": [
                {"original": "", "translation": "test"}  # Empty original
            ]
        }

        invalid_file = mock_glossaries_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            json.dump(invalid_data, f)

        with pytest.raises(ValueError):
            glossary_service.load_glossary("invalid.json")

    def test_term_replacement_error_handling(self, glossary_service):
        """Test error handling during term replacement."""
        terms = [GlossaryTerm("test", "тест")]
        glossary = Glossary("Test", "1.0", "test", terms)
        glossary_service.active_glossary = glossary

        # Mock replacement function to fail
        with patch.object(glossary_service, '_replace_term') as mock_replace:
            mock_replace.side_effect = Exception("Replacement failed")

            with patch('src.utils.logger.Logger') as mock_logger:
                result = glossary_service.apply_glossary("test", "test")

                # Should return original text and log error
                assert result == "test"
                mock_logger.error.assert_called()

    # CRITICAL: Integration with game detection
    def test_auto_glossary_switching_on_game_detection(self, glossary_service, mock_glossaries_path):
        """Test automatic glossary switching when game is detected."""
        # Create glossary for specific game
        sample_data = {
            "name": "Genshin Impact",
            "game": "genshin_impact",
            "version": "1.0",
            "terms": [{"original": "Traveler", "translation": "Путешественник"}]
        }

        glossary_file = mock_glossaries_path / "genshin_impact.json"
        with open(glossary_file, 'w') as f:
            json.dump(sample_data, f)

        glossary_service.discover_glossaries()

        # Mock game detection event
        with patch('src.services.game_detector_service.GameDetectorService') as mock_detector:
            detector = mock_detector.return_value

            # Register for game detection events
            glossary_service.enable_auto_switching(detector)

            # Simulate game detection
            game_info = {"game": "genshin_impact", "name": "Genshin Impact"}
            glossary_service._on_game_detected(game_info)

            # Should auto-activate corresponding glossary
            assert glossary_service.active_glossary is not None
            assert glossary_service.active_glossary.game == "genshin_impact"

    def test_download_community_glossaries(self, glossary_service, mock_glossaries_path):
        """Test downloading community-maintained glossaries."""
        community_glossary_data = {
            "name": "Community Genshin Impact",
            "version": "2.0",
            "game": "genshin_impact",
            "terms": [
                {"original": "Traveler", "translation": "Путешественник"},
                {"original": "Abyss", "translation": "Бездна"}
            ]
        }

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = community_glossary_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            success = glossary_service.download_community_glossary("genshin_impact")

            assert success is True

            # Should save downloaded glossary
            saved_file = mock_glossaries_path / "genshin_impact.json"
            assert saved_file.exists()


# CRITICAL: Integration tests
class TestGlossaryIntegration:
    """Integration tests for complete glossary workflow."""

    def test_translation_engine_glossary_integration(self):
        """Test integration with translation engine."""
        # This test will fail until translation engine integration exists

        with patch('src.core.translation_engine.TranslationEngine') as mock_engine:
            with patch('src.services.glossary_service.GlossaryService') as mock_glossary:

                engine = mock_engine.return_value
                glossary_service = mock_glossary.return_value

                # Mock translation with glossary application
                engine.translate.return_value = "Raw translation with Traveler"
                glossary_service.apply_glossary.return_value = "Raw translation with Путешественник"

                # Simulate translation workflow
                original_text = "Hello, Traveler!"
                result = engine.translate_with_glossary(original_text, "en", "ru")

                # Should apply glossary after translation
                glossary_service.apply_glossary.assert_called()
                assert "Путешественник" in result

    def test_ui_glossary_management_integration(self):
        """Test UI integration for glossary management."""
        # This test will fail until UI integration exists

        with patch('src.ui.glossary_manager_window.GlossaryManagerWindow') as mock_ui:
            window = mock_ui.return_value

            glossary_service = GlossaryService(Path("test"))

            # Mock UI interactions
            window.get_selected_glossary.return_value = "genshin_impact"
            window.show_glossary_terms.return_value = None

            # Simulate UI workflow
            selected_game = window.get_selected_glossary()
            glossary_service.activate_glossary_for_game(selected_game)

            # Should update UI with active glossary
            assert glossary_service.active_glossary is not None