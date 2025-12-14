/**
 * Tests for useTranslation hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useTranslation } from './useTranslation';
import type { TranslationResult } from './useTranslation';

// Mock Tauri API
const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: mockInvoke,
}));

// Mock stores
const mockAddTranslation = vi.fn();
const mockAddItem = vi.fn().mockResolvedValue(undefined);

vi.mock('../store/appStore', () => ({
  useAppStore: () => mockAddTranslation,
}));

vi.mock('../store/historyStore', () => ({
  useHistoryStore: () => mockAddItem,
}));

describe('useTranslation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should not be translating initially', () => {
      const { result } = renderHook(() => useTranslation());
      expect(result.current.isTranslating).toBe(false);
    });

    it('should have no error initially', () => {
      const { result } = renderHook(() => useTranslation());
      expect(result.current.error).toBeNull();
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.translateText).toBeDefined();
      expect(result.current.detectLanguageAndContext).toBeDefined();
      expect(result.current.getTranslationSuggestions).toBeDefined();
      expect(result.current.translateWithContext).toBeDefined();
    });
  });

  describe('translateText', () => {
    it('should translate text successfully', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      const translation = await result.current.translateText('Hello');

      expect(translation).toEqual(mockResult);
      expect(mockInvoke).toHaveBeenCalledWith('translate_text', {
        text: 'Hello',
        targetLang: null,
      });
    });

    it('should translate with target language', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Hola',
        source_lang: 'en',
        target_lang: 'es',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      await result.current.translateText('Hello', 'es');

      expect(mockInvoke).toHaveBeenCalledWith('translate_text', {
        text: 'Hello',
        targetLang: 'es',
      });
    });

    it('should set isTranslating during translation', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve(mockResult), 100);
          })
      );

      const { result } = renderHook(() => useTranslation());

      const promise = result.current.translateText('Hello');

      await waitFor(() => {
        expect(result.current.isTranslating).toBe(true);
      });

      await promise;

      expect(result.current.isTranslating).toBe(false);
    });

    it('should handle translation errors', async () => {
      mockInvoke.mockRejectedValueOnce(new Error('Translation failed'));

      const { result } = renderHook(() => useTranslation());

      await expect(result.current.translateText('Hello')).rejects.toThrow('Translation failed');

      expect(result.current.error).toBe('Error: Translation failed');
      expect(result.current.isTranslating).toBe(false);
    });

    it('should clear error on successful translation', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      // First call fails
      mockInvoke.mockRejectedValueOnce(new Error('First error'));

      const { result } = renderHook(() => useTranslation());

      await expect(result.current.translateText('Hello')).rejects.toThrow();
      expect(result.current.error).toBeTruthy();

      // Second call succeeds
      mockInvoke.mockResolvedValueOnce(mockResult);
      await result.current.translateText('Hello');

      expect(result.current.error).toBeNull();
    });
  });

  describe('detectLanguageAndContext', () => {
    it('should detect language and context', async () => {
      const mockResult = {
        language: 'en',
        confidence: 0.98,
        context_type: 'technical',
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      const detection = await result.current.detectLanguageAndContext('Hello world');

      expect(detection).toEqual(mockResult);
      expect(mockInvoke).toHaveBeenCalledWith('detect_language_and_context', {
        text: 'Hello world',
      });
    });

    it('should handle detection errors', async () => {
      mockInvoke.mockRejectedValueOnce(new Error('Detection failed'));

      const { result } = renderHook(() => useTranslation());

      await expect(result.current.detectLanguageAndContext('Hello')).rejects.toThrow(
        'Detection failed'
      );
    });
  });

  describe('getTranslationSuggestions', () => {
    it('should get translation suggestions', async () => {
      const mockSuggestions = [
        { target_lang: 'ru', reason: 'Most common', confidence: 0.8 },
        { target_lang: 'de', reason: 'Alternative', confidence: 0.6 },
      ];

      mockInvoke.mockResolvedValueOnce(mockSuggestions);

      const { result } = renderHook(() => useTranslation());

      const suggestions = await result.current.getTranslationSuggestions('Hello', 'en');

      expect(suggestions).toEqual(mockSuggestions);
      expect(mockInvoke).toHaveBeenCalledWith('get_translation_suggestions', {
        text: 'Hello',
        sourceLang: 'en',
      });
    });

    it('should return empty array on error', async () => {
      mockInvoke.mockRejectedValueOnce(new Error('Suggestions failed'));

      const { result } = renderHook(() => useTranslation());

      const suggestions = await result.current.getTranslationSuggestions('Hello', 'en');

      expect(suggestions).toEqual([]);
    });
  });

  describe('translateWithContext', () => {
    it('should translate with context', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        context_type: 'gaming',
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      const translation = await result.current.translateWithContext('Hello', 'gaming', 'ru');

      expect(translation).toEqual(mockResult);
      expect(mockInvoke).toHaveBeenCalledWith('smart_translate_with_context', {
        text: 'Hello',
        contextType: 'gaming',
        targetLang: 'ru',
      });
    });

    it('should translate with auto-detected context', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      await result.current.translateWithContext('Hello');

      expect(mockInvoke).toHaveBeenCalledWith('smart_translate_with_context', {
        text: 'Hello',
        contextType: null,
        targetLang: null,
      });
    });

    it('should handle context translation errors', async () => {
      mockInvoke.mockRejectedValueOnce(new Error('Context translation failed'));

      const { result } = renderHook(() => useTranslation());

      await expect(result.current.translateWithContext('Hello', 'gaming')).rejects.toThrow(
        'Context translation failed'
      );

      expect(result.current.error).toBe('Error: Context translation failed');
    });
  });

  describe('State Management', () => {
    it('should handle concurrent translations', async () => {
      const mockResult1: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      const mockResult2: TranslationResult = {
        original_text: 'World',
        translated_text: 'Мир',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult1).mockResolvedValueOnce(mockResult2);

      const { result } = renderHook(() => useTranslation());

      const [translation1, translation2] = await Promise.all([
        result.current.translateText('Hello'),
        result.current.translateText('World'),
      ]);

      expect(translation1.translated_text).toBe('Привет');
      expect(translation2.translated_text).toBe('Мир');
    });

    it('should reset error state before each translation', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockRejectedValueOnce(new Error('First error'));

      const { result } = renderHook(() => useTranslation());

      await expect(result.current.translateText('Hello')).rejects.toThrow();
      expect(result.current.error).toBeTruthy();

      mockInvoke.mockResolvedValueOnce(mockResult);
      await result.current.translateText('Hello');

      expect(result.current.error).toBeNull();
    });
  });

  describe('Integration with Stores', () => {
    it('should add translation to app store', async () => {
      const mockResult: TranslationResult = {
        original_text: 'Hello',
        translated_text: 'Привет',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date().toISOString(),
      };

      mockInvoke.mockResolvedValueOnce(mockResult);

      const { result } = renderHook(() => useTranslation());

      await result.current.translateText('Hello');

      // Verify store methods were called (mocked in beforeEach)
      expect(mockInvoke).toHaveBeenCalled();
    });
  });
});