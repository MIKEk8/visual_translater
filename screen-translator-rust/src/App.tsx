/**
 * Main Application Component
 *
 * Integrates all Screen Translator v3.0 features:
 * - AI-Enhanced Context-Aware Translation
 * - Intelligent Alt+A Hotkey System with time-based detection
 * - Translation History & Cache with search
 * - Animated Context Menu with keyboard navigation
 * - React + TypeScript + Tailwind CSS + Framer Motion
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { invoke } from '@tauri-apps/api/core';

// Components
import ContextMenu from './components/ContextMenu';
import TranslationOverlay from './components/TranslationOverlay';
import HistoryWindow from './components/HistoryWindow';
import SettingsPanel from './components/SettingsPanel';

// Hooks
import useHotkeys, { SmartTranslationRequest } from './hooks/useHotkeys';
import useTranslation from './hooks/useTranslation';
import useConfig from './hooks/useConfig';

// Types
interface AppState {
  currentView: 'main' | 'history' | 'settings';
  showTranslationOverlay: boolean;
  currentTranslation: SmartTranslationRequest | null;
  isLoading: boolean;
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>({
    currentView: 'main',
    showTranslationOverlay: false,
    currentTranslation: null,
    isLoading: true
  });

  // Custom hooks
  const {
    isContextMenuVisible,
    currentTranslationRequest,
    closeContextMenu,
    executeContextAction,
    getPerformanceStats,
    isInitialized: hotkeyInitialized
  } = useHotkeys({
    onQuickTranslation: handleQuickTranslation,
    onContextMenu: handleContextMenu,
    onScreenSelection: handleScreenSelection,
    quickPressThreshold: 1000 // 1 second
  });

  const {
    translateText,
    detectLanguageAndContext,
    getTranslationSuggestions,
    isTranslating
  } = useTranslation();

  const {
    config,
    updateConfig,
    isConfigLoaded
  } = useConfig();

  // Handle quick translation from intelligent hotkey
  async function handleQuickTranslation(request: SmartTranslationRequest) {
    console.log('Processing quick translation:', request);

    setAppState(prev => ({
      ...prev,
      currentTranslation: request,
      showTranslationOverlay: true
    }));

    try {
      let translationResult;

      switch (request.source) {
        case 'SelectedText':
        case 'ClipboardText':
          // Direct text translation with AI context detection
          translationResult = await translateText(request.content);
          break;

        case 'ClipboardImage':
          // OCR + Translation pipeline
          translationResult = await processImageTranslation(request.content);
          break;

        case 'PreviousArea':
        case 'NewSelection':
          // Screenshot + OCR + Translation pipeline
          if (request.coordinates) {
            translationResult = await processScreenshotTranslation(request.coordinates);
          }
          break;

        default:
          console.warn('Unknown translation source:', request.source);
          return;
      }

      // Show translation result
      if (translationResult) {
        displayTranslationResult(translationResult);
      }
    } catch (error) {
      console.error('Translation failed:', error);
      showError('Translation failed. Please try again.');
    }
  }

  // Handle context menu appearance
  function handleContextMenu() {
    console.log('Context menu triggered');
    // Menu visibility is handled by the useHotkeys hook
  }

  // Handle screen selection
  function handleScreenSelection() {
    console.log('Starting screen area selection');
    setAppState(prev => ({ ...prev, currentView: 'main' }));
    // TODO: Implement screen selection UI
  }

  // Process image translation (OCR + AI translation)
  async function processImageTranslation(imageData: string): Promise<any> {
    try {
      // Step 1: Perform OCR
      const ocrResult = await invoke<{ text: string; confidence: number }>('perform_ocr', { imageData });
      console.log('OCR result:', ocrResult);

      // Step 2: AI-enhanced translation
      const translationResult = await invoke('smart_translate_with_context', {
        text: ocrResult.text,
        contextType: null, // Let AI detect
        targetLang: null   // Use smart suggestions
      });

      return translationResult;
    } catch (error) {
      console.error('Image translation failed:', error);
      throw error;
    }
  }

  // Process screenshot translation (Capture + OCR + AI translation)
  async function processScreenshotTranslation(coordinates: [number, number, number, number]): Promise<any> {
    try {
      // Step 1: Capture screenshot
      const screenshotResult = await invoke<{ imageData: string }>('capture_screenshot', {
        area: {
          x: coordinates[0],
          y: coordinates[1],
          width: coordinates[2],
          height: coordinates[3]
        }
      });

      // Step 2: Process with AI
      return await processImageTranslation(screenshotResult.imageData);
    } catch (error) {
      console.error('Screenshot translation failed:', error);
      throw error;
    }
  }

  // Display translation result in overlay
  function displayTranslationResult(result: any) {
    console.log('Displaying translation result:', result);
    // TODO: Update translation overlay with result
  }

  // Show error message
  function showError(message: string) {
    console.error('Error:', message);
    // TODO: Implement error display
  }

  // Handle context menu actions
  async function handleContextAction(action: string) {
    console.log('Context action selected:', action);

    switch (action) {
      case 'screenshot_area':
        handleScreenSelection();
        break;

      case 'translate_clipboard':
        // Get clipboard content and translate
        try {
          // TODO: Get clipboard content
          const clipboardText = 'Sample clipboard text'; // Mock
          await handleQuickTranslation({
            source: 'ClipboardText',
            content: clipboardText,
            timestamp: new Date().toISOString()
          });
        } catch (error) {
          showError('Failed to translate clipboard content');
        }
        break;

      case 'smart_region':
        // Start AI-powered region detection
        // TODO: Implement smart region detection
        console.log('Starting smart region detection');
        break;

      case 'repeat_last':
        // Repeat last translation
        if (appState.currentTranslation) {
          await handleQuickTranslation(appState.currentTranslation);
        }
        break;

      case 'show_history':
        setAppState(prev => ({ ...prev, currentView: 'history' }));
        break;

      case 'show_settings':
        setAppState(prev => ({ ...prev, currentView: 'settings' }));
        break;

      default:
        console.warn('Unknown context action:', action);
    }
  }

  // Navigation functions
  const navigateToMain = () => setAppState(prev => ({ ...prev, currentView: 'main' }));
  const navigateToHistory = () => setAppState(prev => ({ ...prev, currentView: 'history' }));
  const navigateToSettings = () => setAppState(prev => ({ ...prev, currentView: 'settings' }));

  // Close translation overlay
  const closeTranslationOverlay = () => {
    setAppState(prev => ({ ...prev, showTranslationOverlay: false }));
  };

  // Initialize app
  useEffect(() => {
    const initializeApp = async () => {
      try {
        console.log('Initializing Screen Translator v3.0...');

        // Wait for all systems to initialize
        const initPromises: Promise<void>[] = [
          // Additional initialization can be added here
        ];

        await Promise.all(initPromises);

        setAppState(prev => ({ ...prev, isLoading: false }));
        console.log('Screen Translator v3.0 initialized successfully');
      } catch (error) {
        console.error('Failed to initialize app:', error);
        setAppState(prev => ({ ...prev, isLoading: false }));
      }
    };

    if (hotkeyInitialized && isConfigLoaded) {
      initializeApp();
    }
  }, [hotkeyInitialized, isConfigLoaded]);

  // Loading screen
  if (appState.isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">🌐</span>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-6">
            Screen Translator v3.0
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Initializing AI-powered translation system...
          </p>
          <div className="mt-4 space-y-1 text-sm text-gray-500 dark:text-gray-500">
            <div className={hotkeyInitialized ? 'text-green-600' : ''}>
              {hotkeyInitialized ? '✓' : '⏳'} Intelligent hotkey system
            </div>
            <div className={isConfigLoaded ? 'text-green-600' : ''}>
              {isConfigLoaded ? '✓' : '⏳'} Configuration loaded
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Main Application Content */}
      <AnimatePresence mode="wait">
        {appState.currentView === 'main' && (
          <motion.div
            key="main"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="min-h-screen flex flex-col"
          >
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center py-4">
                  <div className="flex items-center space-x-3">
                    <span className="text-3xl">🌐</span>
                    <div>
                      <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                        Screen Translator v3.0
                      </h1>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        AI-powered translation with intelligent hotkeys
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={navigateToHistory}
                      className="flex items-center space-x-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      <span>📚</span>
                      <span>History</span>
                    </button>
                    <button
                      onClick={navigateToSettings}
                      className="flex items-center space-x-2 px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg transition-colors"
                    >
                      <span>⚙️</span>
                      <span>Settings</span>
                    </button>
                  </div>
                </div>
              </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex items-center justify-center p-8">
              <div className="text-center max-w-2xl">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.2 }}
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8"
                >
                  <div className="text-6xl mb-6">🚀</div>
                  <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                    Intelligent Translation Ready
                  </h2>
                  <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
                    Press <kbd className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded font-mono text-sm">Alt+A</kbd> for smart translation
                  </p>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                      <div className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
                        ⚡ Quick Press (&lt;1s)
                      </div>
                      <div className="text-blue-700 dark:text-blue-400">
                        Smart translation with AI context detection
                      </div>
                    </div>
                    <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                      <div className="font-semibold text-purple-900 dark:text-purple-300 mb-2">
                        🕐 Long Press (≥1s)
                      </div>
                      <div className="text-purple-700 dark:text-purple-400">
                        Animated context menu with 6 actions
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </main>
          </motion.div>
        )}

        {appState.currentView === 'history' && (
          <HistoryWindow key="history" onBack={navigateToMain} />
        )}

        {appState.currentView === 'settings' && (
          <SettingsPanel key="settings" onBack={navigateToMain} />
        )}
      </AnimatePresence>

      {/* Context Menu Overlay */}
      <ContextMenu
        isVisible={isContextMenuVisible}
        onClose={closeContextMenu}
        onAction={handleContextAction}
      />

      {/* Translation Result Overlay */}
      <TranslationOverlay
        isVisible={appState.showTranslationOverlay}
        translation={appState.currentTranslation}
        onClose={closeTranslationOverlay}
      />
    </div>
  );
};

export default App;