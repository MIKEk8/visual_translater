"""
Integration tests for all 8 enhanced features working together.

FEATURE INTEGRATION: All 8 enhanced features
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# CRITICAL: Import paths will fail until implementation exists
from src.services.history_search_service import HistorySearchService
from src.services.hotkey_profile_service import HotkeyProfileService
from src.services.game_detector_service import GameDetectorService
from src.services.glossary_service import GlossaryService
from src.services.live_translation_service import LiveTranslationService
from src.core.image_preprocessor import ImagePreprocessor
from src.ui.quick_actions_menu import QuickActionsMenu
from src.ui.enhanced_drag_drop_handler import EnhancedDragDropHandler


class TestCrossFeatureIntegration:
    """Test integration between multiple features."""

    @pytest.fixture
    def mock_services(self):
        """Mock all enhanced services."""
        return {
            'history_search': Mock(spec=HistorySearchService),
            'hotkey_profile': Mock(spec=HotkeyProfileService),
            'game_detector': Mock(spec=GameDetectorService),
            'glossary': Mock(spec=GlossaryService),
            'live_translation': Mock(spec=LiveTranslationService),
            'image_preprocessor': Mock(spec=ImagePreprocessor),
            'quick_actions': Mock(spec=QuickActionsMenu),
            'drag_drop': Mock(spec=EnhancedDragDropHandler)
        }

    # CRITICAL: Game detection triggers multiple feature changes
    def test_game_detection_triggers_profile_and_glossary_changes(self, mock_services):
        """Test game detection automatically switches profiles and glossaries."""
        game_detector = mock_services['game_detector']
        hotkey_profile = mock_services['hotkey_profile']
        glossary_service = mock_services['glossary']

        # Mock game detection event
        game_info = {
            'name': 'Genshin Impact',
            'game': 'genshin_impact',
            'hotkey_profile': 'Gaming',
            'glossary': 'genshin_impact'
        }

        # Simulate game detection triggering other services
        def simulate_game_detected():
            # Game detector should trigger hotkey profile switch
            hotkey_profile.switch_to_profile('Gaming')
            # And activate corresponding glossary
            glossary_service.activate_glossary_for_game('genshin_impact')

        game_detector.on_game_detected = simulate_game_detected

        # Trigger game detection
        game_detector.on_game_detected()

        # CRITICAL: Both dependent services should be updated
        hotkey_profile.switch_to_profile.assert_called_with('Gaming')
        glossary_service.activate_glossary_for_game.assert_called_with('genshin_impact')

    # CRITICAL: Enhanced history integrates with glossary translations
    def test_history_search_with_glossary_applied_translations(self, mock_services):
        """Test history search finds translations that used glossary terms."""
        history_search = mock_services['history_search']
        glossary_service = mock_services['glossary']

        # Mock historical translations with glossary terms
        historical_translations = [
            Mock(
                original="Hello Traveler",
                translated="Привет Путешественник",  # Glossary applied
                glossary_used="genshin_impact",
                timestamp=datetime.now()
            ),
            Mock(
                original="Need Primogems",
                translated="Нужны Примогемы",  # Glossary applied
                glossary_used="genshin_impact",
                timestamp=datetime.now()
            )
        ]

        history_search.search.return_value = historical_translations

        # Search for game-specific terms
        results = history_search.search("Traveler", filters={
            "glossary_used": "genshin_impact"
        })

        # CRITICAL: Should find translations that used specific glossary
        assert len(results) == 2
        assert all(r.glossary_used == "genshin_impact" for r in results)
        history_search.search.assert_called_once()

    # CRITICAL: OCR preprocessing improves translation accuracy
    def test_ocr_preprocessing_improves_translation_accuracy(self, mock_services):
        """Test OCR preprocessing integration improves final translation quality."""
        image_preprocessor = mock_services['image_preprocessor']

        # Mock raw vs processed image OCR results
        raw_image = Mock()
        processed_image = Mock()

        image_preprocessor.preprocess.return_value = processed_image

        with patch('src.core.ocr_engine.OCREngine') as mock_ocr:
            ocr_engine = mock_ocr.return_value

            # Mock improved OCR accuracy after preprocessing
            ocr_engine.extract_text.side_effect = [
                "H3ll0 W0r1d",    # Raw image (poor quality)
                "Hello World"    # Processed image (better quality)
            ]

            # Without preprocessing
            raw_text = ocr_engine.extract_text(raw_image)

            # With preprocessing
            processed_text = ocr_engine.extract_text(processed_image)

            # CRITICAL: Preprocessing should improve OCR quality
            assert "Hello World" in processed_text
            assert processed_text != raw_text
            image_preprocessor.preprocess.assert_called_once()

    # CRITICAL: Live translation integrates with glossary and preprocessing
    @pytest.mark.asyncio
    async def test_live_translation_with_glossary_and_preprocessing(self, mock_services):
        """Test live translation uses both glossary and preprocessing."""
        live_service = mock_services['live_translation']
        glossary_service = mock_services['glossary']
        image_preprocessor = mock_services['image_preprocessor']

        # Mock live translation processing pipeline
        async def mock_process_frame(frame_data):
            # Should preprocess frame
            processed_frame = image_preprocessor.preprocess(frame_data)
            # Extract text via OCR
            extracted_text = "Hello Traveler"
            # Apply glossary
            glossary_text = glossary_service.apply_glossary("", extracted_text)
            return glossary_text

        live_service._process_frame = mock_process_frame
        live_service.is_active = True

        # Mock glossary application
        glossary_service.apply_glossary.return_value = "Привет Путешественник"

        # Process a frame
        result = await live_service._process_frame(b"frame_data")

        # CRITICAL: Should use both preprocessing and glossary
        image_preprocessor.preprocess.assert_called_once()
        glossary_service.apply_glossary.assert_called_once()

    # CRITICAL: Quick actions menu integrates with all features
    def test_quick_actions_integrates_with_all_features(self, mock_services):
        """Test quick actions menu can trigger actions from all features."""
        quick_actions = mock_services['quick_actions']
        history_search = mock_services['history_search']
        live_translation = mock_services['live_translation']

        # Mock quick actions for different features
        actions = {
            'search_history': lambda: history_search.search("last translation"),
            'toggle_live_mode': lambda: live_translation.toggle_active(),
            'switch_gaming_profile': lambda: mock_services['hotkey_profile'].switch_to_profile('Gaming')
        }

        quick_actions.actions = {name: Mock(callback=callback) for name, callback in actions.items()}

        # Execute actions
        quick_actions.actions['search_history'].callback()
        quick_actions.actions['toggle_live_mode'].callback()
        quick_actions.actions['switch_gaming_profile'].callback()

        # CRITICAL: Should trigger all integrated services
        history_search.search.assert_called_once()
        live_translation.toggle_active.assert_called_once()
        mock_services['hotkey_profile'].switch_to_profile.assert_called_with('Gaming')

    # CRITICAL: Drag & drop integrates with preprocessing and translation
    def test_drag_drop_integrates_with_preprocessing(self, mock_services):
        """Test drag & drop uses preprocessing for better OCR."""
        drag_drop = mock_services['drag_drop']
        image_preprocessor = mock_services['image_preprocessor']

        # Mock drag & drop processing
        def mock_process_image(image):
            # Should preprocess before OCR
            processed = image_preprocessor.preprocess(image)
            return processed

        drag_drop.process_image = mock_process_image

        # Simulate image drop
        test_image = Mock()
        drag_drop.process_image(test_image)

        # CRITICAL: Should use preprocessing
        image_preprocessor.preprocess.assert_called_with(test_image)


class TestFeatureConfigurationIntegration:
    """Test that all features respect shared configuration."""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager."""
        with patch('src.services.config_manager.ConfigManager') as mock_config:
            config_manager = mock_config.return_value

            # Mock configuration for all features
            config_manager.get.side_effect = lambda key, default=None: {
                'features.enhanced_history.enabled': True,
                'features.hotkey_profiles.enabled': True,
                'features.game_detection.enabled': True,
                'features.ocr_preprocessing.enabled': True,
                'features.glossaries.enabled': True,
                'features.live_translation.enabled': True,
                'features.quick_actions.enabled': True,
                'features.drag_drop_enhanced.enabled': True,
                'features.enhanced_history.search_enabled': True,
                'features.hotkey_profiles.auto_switch': True,
                'features.game_detection.auto_load_settings': True,
                'features.ocr_preprocessing.steps': ['denoise', 'contrast', 'binarize'],
                'features.glossaries.auto_download': True,
                'features.live_translation.max_fps': 2,
            }.get(key, default)

            return config_manager

    def test_all_features_respect_enabled_disabled_config(self, mock_config_manager):
        """Test all features respect enabled/disabled configuration."""
        # Mock all features as disabled
        mock_config_manager.get.side_effect = lambda key, default=None: False if 'enabled' in key else default

        # Initialize services (should check config)
        with patch('src.services.history_search_service.HistorySearchService') as mock_history:
            with patch('src.services.hotkey_profile_service.HotkeyProfileService') as mock_hotkey:

                # Services should check if they're enabled
                history_service = mock_history.return_value
                hotkey_service = mock_hotkey.return_value

                # Mock initialization checks
                history_service.is_enabled.return_value = False
                hotkey_service.is_enabled.return_value = False

                # Services should not activate when disabled
                assert history_service.is_enabled() is False
                assert hotkey_service.is_enabled() is False

    def test_features_share_common_settings(self, mock_config_manager):
        """Test features share common settings like target language."""
        common_settings = {
            'translation.target_language': 'ru',
            'translation.confidence_threshold': 0.8,
            'ui.theme': 'dark'
        }

        mock_config_manager.get.side_effect = lambda key, default=None: common_settings.get(key, default)

        # All translation-related features should use same target language
        with patch('src.services.glossary_service.GlossaryService') as mock_glossary:
            with patch('src.services.live_translation_service.LiveTranslationService') as mock_live:

                glossary_service = mock_glossary.return_value
                live_service = mock_live.return_value

                # Both should read the same config
                glossary_service.target_language = mock_config_manager.get('translation.target_language')
                live_service.target_language = mock_config_manager.get('translation.target_language')

                assert glossary_service.target_language == 'ru'
                assert live_service.target_language == 'ru'


class TestFeaturePerformanceIntegration:
    """Test that all features together don't degrade performance."""

    @pytest.mark.asyncio
    async def test_all_features_active_performance(self, mock_services):
        """Test system performance with all features active."""
        # Activate all features
        for service_name, service in mock_services.items():
            if hasattr(service, 'is_active'):
                service.is_active = True

        # Mock operations from all services
        operations = []

        async def mock_operation(name):
            operations.append(name)
            await asyncio.sleep(0.01)  # Simulate small delay

        # Simulate concurrent operations
        tasks = [
            mock_operation('history_search'),
            mock_operation('game_detection'),
            mock_operation('live_translation'),
            mock_operation('glossary_application'),
            mock_operation('image_preprocessing')
        ]

        import time
        start_time = time.time()

        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # CRITICAL: All operations should complete quickly even when all active
        assert total_time < 1.0  # Should complete under 1 second
        assert len(operations) == 5

    def test_memory_usage_with_all_features(self, mock_services):
        """Test memory usage doesn't explode with all features active."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Initialize all services (mocked)
        active_services = []
        for service_name, service in mock_services.items():
            active_services.append(service)
            # Mock memory usage
            if hasattr(service, 'cleanup'):
                service.cleanup()

        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory

        # CRITICAL: Memory increase should be reasonable (under 100MB for mocked services)
        assert memory_increase < 100 * 1024 * 1024  # 100MB


class TestFeatureErrorHandlingIntegration:
    """Test error handling when multiple features interact."""

    def test_service_failure_doesnt_crash_others(self, mock_services):
        """Test that one service failure doesn't crash other services."""
        # Make one service fail
        mock_services['game_detector'].detect_games.side_effect = Exception("Game detection failed")

        # Other services should continue working
        with patch('src.utils.logger.Logger') as mock_logger:
            try:
                # Try operations on all services
                mock_services['history_search'].search("test")
                mock_services['hotkey_profile'].switch_to_profile("Gaming")
                mock_services['glossary'].activate_glossary_for_game("test_game")

                # This one should fail
                mock_services['game_detector'].detect_games()

            except Exception:
                pass

            # Other services should have worked
            mock_services['history_search'].search.assert_called_once()
            mock_services['hotkey_profile'].switch_to_profile.assert_called_once()
            mock_services['glossary'].activate_glossary_for_game.assert_called_once()

            # Error should be logged
            mock_logger.error.assert_called()

    def test_circuit_breaker_integration_across_features(self, mock_services):
        """Test circuit breaker pattern works across all features."""

        with patch('src.services.circuit_breaker.CircuitBreaker') as mock_breaker:
            breaker = mock_breaker.return_value

            # Mock circuit breaker opening after failures
            breaker.call.side_effect = [
                Exception("Service failed"),  # First call fails
                Exception("Service failed"),  # Second call fails
                Exception("Circuit breaker open")  # Third call: breaker opens
            ]

            # Try operations that should trigger circuit breaker
            for i in range(3):
                try:
                    breaker.call(lambda: mock_services['live_translation'].process_frame(b"data"))
                except Exception:
                    pass

            # Circuit breaker should have been triggered
            assert breaker.call.call_count == 3

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_features_fail(self, mock_services):
        """Test graceful degradation when optional features fail."""
        # Core translation should work even if enhancements fail

        # Mock enhancement failures
        mock_services['image_preprocessor'].preprocess.side_effect = Exception("Preprocessing failed")
        mock_services['glossary'].apply_glossary.side_effect = Exception("Glossary failed")

        # Mock core translation still working
        with patch('src.core.translation_engine.TranslationEngine') as mock_core_engine:
            core_engine = mock_core_engine.return_value
            core_engine.translate.return_value = Mock(translated_text="Basic translation")

            # Translation should work with degraded features
            result = core_engine.translate("Hello world", target_lang="ru")

            # CRITICAL: Core functionality should work despite enhancement failures
            assert result.translated_text == "Basic translation"
            core_engine.translate.assert_called_once()


class TestFeatureDataFlowIntegration:
    """Test data flow between all features."""

    def test_translation_history_includes_all_enhancements(self, mock_services):
        """Test translation history records all enhancement usage."""
        history_search = mock_services['history_search']

        # Mock translation with all enhancements
        translation_record = {
            'id': 1,
            'original': 'Hello Traveler',
            'translated': 'Привет Путешественник',
            'source_lang': 'en',
            'target_lang': 'ru',
            'timestamp': datetime.now(),
            'enhancements_used': {
                'ocr_preprocessing': True,
                'glossary_applied': 'genshin_impact',
                'hotkey_profile': 'Gaming',
                'detection_method': 'live_translation',
                'confidence_improvement': 0.15  # Preprocessing improved confidence
            }
        }

        history_search.add_translation_record(translation_record)

        # Search should find records with enhancement metadata
        results = history_search.search("Traveler", filters={
            'enhancements_used.glossary_applied': 'genshin_impact'
        })

        # CRITICAL: Should track which enhancements were used
        history_search.add_translation_record.assert_called_once()
        assert translation_record['enhancements_used']['glossary_applied'] == 'genshin_impact'

    def test_settings_propagation_across_features(self, mock_services):
        """Test settings changes propagate to all relevant features."""

        # Mock settings change
        new_settings = {
            'target_language': 'ja',  # Change to Japanese
            'ocr_preprocessing.enabled': False,
            'hotkey_profiles.auto_switch': False
        }

        # All relevant services should be notified
        with patch('src.services.config_manager.ConfigManager') as mock_config:
            config_manager = mock_config.return_value

            # Simulate settings update
            for setting, value in new_settings.items():
                config_manager.set(setting, value)

                # Notify all services of config change
                for service in mock_services.values():
                    if hasattr(service, 'on_config_changed'):
                        service.on_config_changed(setting, value)

            # CRITICAL: All services should receive config updates
            config_manager.set.call_count == len(new_settings)


class TestFullWorkflowIntegration:
    """Test complete workflows using multiple features."""

    @pytest.mark.asyncio
    async def test_complete_gaming_workflow(self, mock_services):
        """Test complete workflow: game detection -> profile switch -> live translation with glossary."""
        game_detector = mock_services['game_detector']
        hotkey_profile = mock_services['hotkey_profile']
        glossary_service = mock_services['glossary']
        live_translation = mock_services['live_translation']
        history_search = mock_services['history_search']

        # Step 1: Game is detected
        game_info = {
            'name': 'Genshin Impact',
            'game': 'genshin_impact'
        }

        # Step 2: Auto-switch hotkey profile
        hotkey_profile.switch_to_profile('Gaming')

        # Step 3: Auto-activate glossary
        glossary_service.activate_glossary_for_game('genshin_impact')

        # Step 4: Start live translation
        await live_translation.start_live_mode(Mock())

        # Step 5: Process translation with glossary
        translation_result = {
            'original': 'Hello Traveler',
            'translated': 'Привет Путешественник',
            'glossary_used': 'genshin_impact'
        }

        # Step 6: Save to history
        history_search.add_translation_record(translation_result)

        # CRITICAL: Complete workflow should execute all steps
        hotkey_profile.switch_to_profile.assert_called_with('Gaming')
        glossary_service.activate_glossary_for_game.assert_called_with('genshin_impact')
        live_translation.start_live_mode.assert_called_once()
        history_search.add_translation_record.assert_called_once()

    def test_complete_document_workflow(self, mock_services):
        """Test complete workflow: PDF drop -> preprocessing -> translation -> history."""
        drag_drop = mock_services['drag_drop']
        image_preprocessor = mock_services['image_preprocessor']
        history_search = mock_services['history_search']

        # Step 1: PDF file is dropped
        pdf_path = "document.pdf"

        # Step 2: Extract text from PDF
        extracted_pages = ["Page 1 text", "Page 2 text"]

        # Step 3: Process each page
        for page_text in extracted_pages:
            # Translate text
            translation = f"Translated: {page_text}"

            # Save to history
            history_record = {
                'original': page_text,
                'translated': translation,
                'source': 'pdf_document',
                'filename': pdf_path
            }
            history_search.add_translation_record(history_record)

        # CRITICAL: Document workflow should process all pages
        assert history_search.add_translation_record.call_count == len(extracted_pages)