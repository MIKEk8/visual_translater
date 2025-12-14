/**
 * Tests for configStore
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useConfigStore } from './configStore';
import type { AppConfig } from './configStore';

// Mock Tauri API
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

describe('configStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { resetToDefaults } = useConfigStore.getState();
    resetToDefaults();
  });

  describe('Initial State', () => {
    it('should have default configuration', () => {
      const { config } = useConfigStore.getState();

      expect(config).toBeDefined();
      expect(config.hotkeys).toBeDefined();
      expect(config.languages).toBeDefined();
      expect(config.ocr).toBeDefined();
      expect(config.translation).toBeDefined();
      expect(config.ui).toBeDefined();
    });

    it('should have default hotkeys', () => {
      const { config } = useConfigStore.getState();

      expect(config.hotkeys.quickTranslate).toBe('Alt+A');
      expect(config.hotkeys.contextMenu).toBe('Alt+A');
      expect(config.hotkeys.screenshotArea).toBe('Alt+S');
      expect(config.hotkeys.showHide).toBe('Alt+T');
    });

    it('should have default language settings', () => {
      const { config } = useConfigStore.getState();

      expect(config.languages.sourceLanguage).toBe('auto');
      expect(config.languages.targetLanguage).toBe('en');
      expect(config.languages.autoDetect).toBe(true);
      expect(config.languages.supportedLanguages).toContain('en');
      expect(config.languages.supportedLanguages).toContain('ru');
    });

    it('should have default UI settings', () => {
      const { config } = useConfigStore.getState();

      expect(config.ui.theme).toBe('dark');
      expect(config.ui.overlayPosition).toBe('center');
      expect(config.ui.autoHideDelay).toBe(5000);
      expect(config.ui.showConfidence).toBe(true);
      expect(config.ui.animationsEnabled).toBe(true);
    });

    it('should not be loaded initially', () => {
      const { isLoaded } = useConfigStore.getState();
      expect(isLoaded).toBe(false);
    });

    it('should not be saving initially', () => {
      const { isSaving } = useConfigStore.getState();
      expect(isSaving).toBe(false);
    });

    it('should have no error initially', () => {
      const { error } = useConfigStore.getState();
      expect(error).toBeNull();
    });
  });

  describe('Configuration Updates', () => {
    it('should update hotkeys', async () => {
      const { updateHotkeys, config } = useConfigStore.getState();

      await updateHotkeys({ quickTranslate: 'Ctrl+T' });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.hotkeys.quickTranslate).toBe('Ctrl+T');
      expect(updatedConfig.hotkeys.contextMenu).toBe(config.hotkeys.contextMenu);
    });

    it('should update languages', async () => {
      const { updateLanguages } = useConfigStore.getState();

      await updateLanguages({ targetLanguage: 'ru', autoDetect: false });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.languages.targetLanguage).toBe('ru');
      expect(updatedConfig.languages.autoDetect).toBe(false);
    });

    it('should update OCR settings', async () => {
      const { updateOCR } = useConfigStore.getState();

      await updateOCR({ confidenceThreshold: 0.8, preprocessing: false });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.ocr.confidenceThreshold).toBe(0.8);
      expect(updatedConfig.ocr.preprocessing).toBe(false);
    });

    it('should update translation settings', async () => {
      const { updateTranslation } = useConfigStore.getState();

      await updateTranslation({ cacheEnabled: false, timeout: 10000 });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.translation.cacheEnabled).toBe(false);
      expect(updatedConfig.translation.timeout).toBe(10000);
    });

    it('should update UI settings', async () => {
      const { updateUI } = useConfigStore.getState();

      await updateUI({ theme: 'light', animationsEnabled: false });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.ui.theme).toBe('light');
      expect(updatedConfig.ui.animationsEnabled).toBe(false);
    });

    it('should update partial config', async () => {
      const { saveConfig } = useConfigStore.getState();

      const partialConfig: Partial<AppConfig> = {
        hotkeys: {
          quickTranslate: 'Ctrl+Q',
          contextMenu: 'Ctrl+M',
          screenshotArea: 'Ctrl+S',
          showHide: 'Ctrl+H',
        },
      };

      await saveConfig(partialConfig);

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.hotkeys.quickTranslate).toBe('Ctrl+Q');
    });
  });

  describe('Error Handling', () => {
    it('should set error when provided', () => {
      const { setError } = useConfigStore.getState();

      setError('Test error message');

      const { error } = useConfigStore.getState();
      expect(error).toBe('Test error message');
    });

    it('should clear error', () => {
      const { setError } = useConfigStore.getState();

      setError('Test error');
      setError(null);

      const { error } = useConfigStore.getState();
      expect(error).toBeNull();
    });
  });

  describe('State Management', () => {
    it('should preserve other config sections when updating one', async () => {
      const { config, updateHotkeys } = useConfigStore.getState();
      const originalLanguages = { ...config.languages };

      await updateHotkeys({ quickTranslate: 'Ctrl+T' });

      const updatedConfig = useConfigStore.getState().config;
      expect(updatedConfig.languages).toEqual(originalLanguages);
    });

    it('should handle multiple sequential updates', async () => {
      const { updateHotkeys, updateUI } = useConfigStore.getState();

      await updateHotkeys({ quickTranslate: 'Ctrl+Q' });
      await updateUI({ theme: 'light' });

      const { config } = useConfigStore.getState();
      expect(config.hotkeys.quickTranslate).toBe('Ctrl+Q');
      expect(config.ui.theme).toBe('light');
    });
  });

  describe('Type Safety', () => {
    it('should enforce theme type constraints', () => {
      const { config } = useConfigStore.getState();

      // TypeScript should prevent invalid theme values
      const validThemes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
      expect(validThemes).toContain(config.ui.theme);
    });

    it('should enforce provider type constraints', () => {
      const { config } = useConfigStore.getState();

      const validProviders: Array<'google' | 'deepl' | 'custom'> = ['google', 'deepl', 'custom'];
      expect(validProviders).toContain(config.translation.provider);
    });

    it('should enforce overlay position type constraints', () => {
      const { config } = useConfigStore.getState();

      const validPositions: Array<'center' | 'cursor' | 'top' | 'bottom'> = [
        'center',
        'cursor',
        'top',
        'bottom',
      ];
      expect(validPositions).toContain(config.ui.overlayPosition);
    });
  });

  describe('Default Values', () => {
    it('should have sensible default values for OCR', () => {
      const { config } = useConfigStore.getState();

      expect(config.ocr.confidenceThreshold).toBeGreaterThan(0);
      expect(config.ocr.confidenceThreshold).toBeLessThanOrEqual(1);
      expect(typeof config.ocr.preprocessing).toBe('boolean');
      expect(typeof config.ocr.enhanceImage).toBe('boolean');
    });

    it('should have sensible default values for translation', () => {
      const { config } = useConfigStore.getState();

      expect(config.translation.cacheTTL).toBeGreaterThan(0);
      expect(config.translation.timeout).toBeGreaterThan(0);
      expect(typeof config.translation.cacheEnabled).toBe('boolean');
    });

    it('should have sensible default values for UI', () => {
      const { config } = useConfigStore.getState();

      expect(config.ui.autoHideDelay).toBeGreaterThan(0);
      expect(typeof config.ui.showConfidence).toBe('boolean');
      expect(typeof config.ui.animationsEnabled).toBe('boolean');
    });
  });
});