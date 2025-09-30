/**
 * useConfig Hook - Configuration Management
 *
 * React hook for managing application configuration with Zustand store integration:
 * - Load/save configuration from/to Tauri backend
 * - Real-time configuration updates
 * - Hotkey management
 * - UI preferences
 * - Language settings
 */

import { useEffect } from 'react';
import { useConfigStore } from '../store/configStore';
import type { AppConfig } from '../store/configStore';

interface UseConfigReturn {
  config: AppConfig;
  updateConfig: (updates: Partial<AppConfig>) => Promise<void>;
  isConfigLoaded: boolean;
  isSaving: boolean;
  error: string | null;

  // Convenience methods for updating specific sections
  updateHotkeys: (hotkeys: Partial<AppConfig['hotkeys']>) => Promise<void>;
  updateLanguages: (languages: Partial<AppConfig['languages']>) => Promise<void>;
  updateOCR: (ocr: Partial<AppConfig['ocr']>) => Promise<void>;
  updateTranslation: (translation: Partial<AppConfig['translation']>) => Promise<void>;
  updateUI: (ui: Partial<AppConfig['ui']>) => Promise<void>;
  resetToDefaults: () => Promise<void>;
}

const useConfig = (): UseConfigReturn => {
  const {
    config,
    isLoaded,
    isSaving,
    error,
    loadConfig,
    saveConfig,
    updateHotkeys,
    updateLanguages,
    updateOCR,
    updateTranslation,
    updateUI,
    resetToDefaults,
  } = useConfigStore();

  // Load configuration on mount
  useEffect(() => {
    if (!isLoaded) {
      loadConfig();
    }
  }, [isLoaded, loadConfig]);

  return {
    config,
    updateConfig: saveConfig,
    isConfigLoaded: isLoaded,
    isSaving,
    error,
    updateHotkeys,
    updateLanguages,
    updateOCR,
    updateTranslation,
    updateUI,
    resetToDefaults,
  };
};

export default useConfig;