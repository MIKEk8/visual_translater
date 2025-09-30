/**
 * Config Store - Configuration State Management
 *
 * Zustand store for managing application configuration:
 * - User preferences
 * - Hotkey settings
 * - Language preferences
 * - UI settings
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { invoke } from '@tauri-apps/api/core';

export interface HotkeyConfig {
  quickTranslate: string;
  contextMenu: string;
  screenshotArea: string;
  showHide: string;
}

export interface LanguageConfig {
  sourceLanguage: string;
  targetLanguage: string;
  autoDetect: boolean;
  supportedLanguages: string[];
}

export interface OCRConfig {
  language: string;
  confidenceThreshold: number;
  preprocessing: boolean;
  enhanceImage: boolean;
}

export interface TranslationConfig {
  provider: 'google' | 'deepl' | 'custom';
  cacheEnabled: boolean;
  cacheTTL: number;
  timeout: number;
}

export interface UIConfig {
  theme: 'light' | 'dark' | 'system';
  overlayPosition: 'center' | 'cursor' | 'top' | 'bottom';
  autoHideDelay: number;
  showConfidence: boolean;
  animationsEnabled: boolean;
}

export interface AppConfig {
  hotkeys: HotkeyConfig;
  languages: LanguageConfig;
  ocr: OCRConfig;
  translation: TranslationConfig;
  ui: UIConfig;
}

export interface ConfigState {
  config: AppConfig;
  isLoaded: boolean;
  isSaving: boolean;
  error: string | null;

  // Actions
  loadConfig: () => Promise<void>;
  saveConfig: (config: Partial<AppConfig>) => Promise<void>;
  updateHotkeys: (hotkeys: Partial<HotkeyConfig>) => Promise<void>;
  updateLanguages: (languages: Partial<LanguageConfig>) => Promise<void>;
  updateOCR: (ocr: Partial<OCRConfig>) => Promise<void>;
  updateTranslation: (translation: Partial<TranslationConfig>) => Promise<void>;
  updateUI: (ui: Partial<UIConfig>) => Promise<void>;
  resetToDefaults: () => Promise<void>;
  setError: (error: string | null) => void;
}

const defaultConfig: AppConfig = {
  hotkeys: {
    quickTranslate: 'Alt+A',
    contextMenu: 'Alt+A',
    screenshotArea: 'Alt+S',
    showHide: 'Alt+T',
  },
  languages: {
    sourceLanguage: 'auto',
    targetLanguage: 'en',
    autoDetect: true,
    supportedLanguages: ['en', 'ru', 'de', 'fr', 'es', 'ja', 'zh'],
  },
  ocr: {
    language: 'eng',
    confidenceThreshold: 0.6,
    preprocessing: true,
    enhanceImage: true,
  },
  translation: {
    provider: 'google',
    cacheEnabled: true,
    cacheTTL: 3600000, // 1 hour in ms
    timeout: 5000,
  },
  ui: {
    theme: 'dark',
    overlayPosition: 'center',
    autoHideDelay: 5000,
    showConfidence: true,
    animationsEnabled: true,
  },
};

export const useConfigStore = create<ConfigState>()(
  devtools(
    persist(
      (set, get) => ({
        config: defaultConfig,
        isLoaded: false,
        isSaving: false,
        error: null,

        loadConfig: async () => {
          try {
            const loadedConfig = await invoke<AppConfig>('get_app_config');
            set({ config: { ...defaultConfig, ...loadedConfig }, isLoaded: true, error: null });
          } catch (error) {
            console.error('Failed to load config:', error);
            set({ config: defaultConfig, isLoaded: true, error: String(error) });
          }
        },

        saveConfig: async (configUpdate) => {
          set({ isSaving: true, error: null });
          try {
            const newConfig = { ...get().config, ...configUpdate };
            await invoke('set_app_config', { config: newConfig });
            set({ config: newConfig, isSaving: false });
          } catch (error) {
            console.error('Failed to save config:', error);
            set({ isSaving: false, error: String(error) });
          }
        },

        updateHotkeys: async (hotkeys) => {
          const current = get().config;
          await get().saveConfig({ hotkeys: { ...current.hotkeys, ...hotkeys } });
        },

        updateLanguages: async (languages) => {
          const current = get().config;
          await get().saveConfig({ languages: { ...current.languages, ...languages } });
        },

        updateOCR: async (ocr) => {
          const current = get().config;
          await get().saveConfig({ ocr: { ...current.ocr, ...ocr } });
        },

        updateTranslation: async (translation) => {
          const current = get().config;
          await get().saveConfig({ translation: { ...current.translation, ...translation } });
        },

        updateUI: async (ui) => {
          const current = get().config;
          await get().saveConfig({ ui: { ...current.ui, ...ui } });
        },

        resetToDefaults: async () => {
          await get().saveConfig(defaultConfig);
        },

        setError: (error) => set({ error }),
      }),
      {
        name: 'config-store',
        partialize: (state) => ({ config: state.config }),
      }
    ),
    { name: 'ConfigStore' }
  )
);

export default useConfigStore;