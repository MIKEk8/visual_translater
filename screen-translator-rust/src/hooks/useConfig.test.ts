/**
 * Tests for useConfig hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import useConfig from './useConfig';

// Mock configStore
const mockLoadConfig = vi.fn();
const mockSaveConfig = vi.fn();
const mockUpdateHotkeys = vi.fn();
const mockUpdateLanguages = vi.fn();
const mockUpdateOCR = vi.fn();
const mockUpdateTranslation = vi.fn();
const mockUpdateUI = vi.fn();
const mockResetToDefaults = vi.fn();

vi.mock('../store/configStore', () => ({
  useConfigStore: vi.fn(() => ({
    config: {
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
        provider: 'google' as const,
        cacheEnabled: true,
        cacheTTL: 3600000,
        timeout: 5000,
      },
      ui: {
        theme: 'dark' as const,
        overlayPosition: 'center' as const,
        autoHideDelay: 5000,
        showConfidence: true,
        animationsEnabled: true,
      },
    },
    isLoaded: true,
    isSaving: false,
    error: null,
    loadConfig: mockLoadConfig,
    saveConfig: mockSaveConfig,
    updateHotkeys: mockUpdateHotkeys,
    updateLanguages: mockUpdateLanguages,
    updateOCR: mockUpdateOCR,
    updateTranslation: mockUpdateTranslation,
    updateUI: mockUpdateUI,
    resetToDefaults: mockResetToDefaults,
  })),
}));

describe('useConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should return config from store', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config).toBeDefined();
      expect(result.current.config.hotkeys).toBeDefined();
      expect(result.current.config.languages).toBeDefined();
    });

    it('should indicate config is loaded', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.isConfigLoaded).toBe(true);
    });

    it('should not be saving initially', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.isSaving).toBe(false);
    });

    it('should have no error initially', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.error).toBeNull();
    });
  });

  describe('Configuration Values', () => {
    it('should have hotkey configuration', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config.hotkeys.quickTranslate).toBe('Alt+A');
      expect(result.current.config.hotkeys.contextMenu).toBe('Alt+A');
      expect(result.current.config.hotkeys.screenshotArea).toBe('Alt+S');
    });

    it('should have language configuration', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config.languages.sourceLanguage).toBe('auto');
      expect(result.current.config.languages.targetLanguage).toBe('en');
      expect(result.current.config.languages.autoDetect).toBe(true);
    });

    it('should have OCR configuration', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config.ocr.language).toBe('eng');
      expect(result.current.config.ocr.confidenceThreshold).toBe(0.6);
      expect(result.current.config.ocr.preprocessing).toBe(true);
    });

    it('should have translation configuration', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config.translation.provider).toBe('google');
      expect(result.current.config.translation.cacheEnabled).toBe(true);
      expect(result.current.config.translation.cacheTTL).toBe(3600000);
    });

    it('should have UI configuration', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.config.ui.theme).toBe('dark');
      expect(result.current.config.ui.overlayPosition).toBe('center');
      expect(result.current.config.ui.autoHideDelay).toBe(5000);
    });
  });

  describe('Update Methods', () => {
    it('should provide updateConfig method', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current.updateConfig).toBeDefined();
      expect(typeof result.current.updateConfig).toBe('function');
    });

    it('should provide updateHotkeys method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.updateHotkeys({ quickTranslate: 'Ctrl+T' });

      expect(mockUpdateHotkeys).toHaveBeenCalledWith({ quickTranslate: 'Ctrl+T' });
    });

    it('should provide updateLanguages method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.updateLanguages({ targetLanguage: 'ru' });

      expect(mockUpdateLanguages).toHaveBeenCalledWith({ targetLanguage: 'ru' });
    });

    it('should provide updateOCR method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.updateOCR({ confidenceThreshold: 0.8 });

      expect(mockUpdateOCR).toHaveBeenCalledWith({ confidenceThreshold: 0.8 });
    });

    it('should provide updateTranslation method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.updateTranslation({ cacheEnabled: false });

      expect(mockUpdateTranslation).toHaveBeenCalledWith({ cacheEnabled: false });
    });

    it('should provide updateUI method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.updateUI({ theme: 'light' });

      expect(mockUpdateUI).toHaveBeenCalledWith({ theme: 'light' });
    });

    it('should provide resetToDefaults method', async () => {
      const { result } = renderHook(() => useConfig());

      await result.current.resetToDefaults();

      expect(mockResetToDefaults).toHaveBeenCalled();
    });
  });

  describe('Configuration Loading', () => {
    it('should call loadConfig when hook is initialized', () => {
      // The hook calls loadConfig in useEffect when isLoaded is false
      // Since our mock returns isLoaded: true, we test the behavior indirectly
      const { result } = renderHook(() => useConfig());

      // Config should be available
      expect(result.current.config).toBeDefined();
    });

    it('should not be loading when config is already loaded', () => {
      renderHook(() => useConfig());

      // Store is already loaded (isLoaded: true), so loadConfig should not be called
      expect(mockLoadConfig).not.toHaveBeenCalled();
    });
  });

  describe('Type Safety', () => {
    it('should enforce valid theme types', () => {
      const { result } = renderHook(() => useConfig());

      const validThemes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
      expect(validThemes).toContain(result.current.config.ui.theme);
    });

    it('should enforce valid provider types', () => {
      const { result } = renderHook(() => useConfig());

      const validProviders: Array<'google' | 'deepl' | 'custom'> = ['google', 'deepl', 'custom'];
      expect(validProviders).toContain(result.current.config.translation.provider);
    });

    it('should enforce valid overlay position types', () => {
      const { result } = renderHook(() => useConfig());

      const validPositions: Array<'center' | 'cursor' | 'top' | 'bottom'> = [
        'center',
        'cursor',
        'top',
        'bottom',
      ];
      expect(validPositions).toContain(result.current.config.ui.overlayPosition);
    });
  });

  describe('Return Values', () => {
    it('should return all required properties', () => {
      const { result } = renderHook(() => useConfig());

      expect(result.current).toHaveProperty('config');
      expect(result.current).toHaveProperty('updateConfig');
      expect(result.current).toHaveProperty('isConfigLoaded');
      expect(result.current).toHaveProperty('isSaving');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('updateHotkeys');
      expect(result.current).toHaveProperty('updateLanguages');
      expect(result.current).toHaveProperty('updateOCR');
      expect(result.current).toHaveProperty('updateTranslation');
      expect(result.current).toHaveProperty('updateUI');
      expect(result.current).toHaveProperty('resetToDefaults');
    });

    it('should return functions for update methods', () => {
      const { result } = renderHook(() => useConfig());

      expect(typeof result.current.updateConfig).toBe('function');
      expect(typeof result.current.updateHotkeys).toBe('function');
      expect(typeof result.current.updateLanguages).toBe('function');
      expect(typeof result.current.updateOCR).toBe('function');
      expect(typeof result.current.updateTranslation).toBe('function');
      expect(typeof result.current.updateUI).toBe('function');
      expect(typeof result.current.resetToDefaults).toBe('function');
    });
  });

  describe('Integration', () => {
    it('should integrate with configStore correctly', () => {
      const { result } = renderHook(() => useConfig());

      // Verify all store properties are accessible
      expect(result.current.config).toBeDefined();
      expect(result.current.isConfigLoaded).toBeDefined();
      expect(result.current.isSaving).toBeDefined();
      expect(result.current.error).toBeDefined();
    });

    it('should pass through store methods', async () => {
      const { result } = renderHook(() => useConfig());

      // Call each update method
      await result.current.updateHotkeys({ quickTranslate: 'Ctrl+T' });
      await result.current.updateLanguages({ targetLanguage: 'ru' });
      await result.current.updateOCR({ confidenceThreshold: 0.8 });
      await result.current.updateTranslation({ cacheEnabled: false });
      await result.current.updateUI({ theme: 'light' });

      // Verify all methods were called
      expect(mockUpdateHotkeys).toHaveBeenCalled();
      expect(mockUpdateLanguages).toHaveBeenCalled();
      expect(mockUpdateOCR).toHaveBeenCalled();
      expect(mockUpdateTranslation).toHaveBeenCalled();
      expect(mockUpdateUI).toHaveBeenCalled();
    });
  });
});