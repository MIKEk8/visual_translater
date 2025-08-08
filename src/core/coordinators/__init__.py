"""
Coordinators module for Screen Translator v2.0

This module contains the decomposed components from the original God Class application.py.
Each coordinator has a single responsibility and follows the SRP principle.

Components:
- ApplicationController: Main application coordination and lifecycle
- CaptureOrchestrator: Screenshot capture and area selection
- TranslationWorkflow: OCR, translation, and TTS pipeline
- UICoordinator: User interface management and notifications
- BatchExportManager: Batch processing and export functionality
- SystemIntegration: System-level operations and cleanup
"""

from .application_controller import ApplicationController
from .batch_export_manager import BatchExportManager
from .capture_orchestrator import CaptureOrchestrator
from .system_integration import SystemIntegration
from .translation_workflow import TranslationWorkflow
from .ui_coordinator import UICoordinator

__all__ = [
    "ApplicationController",
    "CaptureOrchestrator",
    "TranslationWorkflow",
    "UICoordinator",
    "BatchExportManager",
    "SystemIntegration",
]
