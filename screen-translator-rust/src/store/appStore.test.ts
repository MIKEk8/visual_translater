// [CRITICAL] MVP App Store Tests
// These tests should FAIL initially per TDD approach

import { renderHook, act } from '@testing-library/react';
import { useTranslationStore } from './appStore';

// Mock Tauri API
jest.mock('@tauri-apps/api/core', () => ({
  invoke: jest.fn(),
}));

const { invoke } = require('@tauri-apps/api/core');

describe('Translation Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    useTranslationStore.getState().reset?.();
    jest.clearAllMocks();
  });

  test('[CRITICAL] initial state is correct', () => {
    // This test will FAIL initially - store doesn't exist yet
    const { result } = renderHook(() => useTranslationStore());

    expect(result.current.isTranslating).toBe(false);
    expect(result.current.currentTranslation).toBe(null);
    expect(result.current.targetLanguage).toBe('en'); // Default target language
    expect(result.current.history).toEqual([]);
    expect(result.current.error).toBe(null);
  });

  test('[CRITICAL] translateText calls Tauri command and updates state', async () => {
    const mockTranslationResult = {
      original_text: 'Hello world',
      translated_text: 'Привет мир',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.95,
      cached: false,
      processing_time_ms: 1200,
    };

    invoke.mockResolvedValue(mockTranslationResult);

    const { result } = renderHook(() => useTranslationStore());

    await act(async () => {
      await result.current.translateText('Hello world', 'ru');
    });

    expect(invoke).toHaveBeenCalledWith('translate_text', {
      text: 'Hello world',
      source_lang: null, // Auto-detect
      target_lang: 'ru',
      context: null,
    });

    expect(result.current.currentTranslation).toEqual(mockTranslationResult);
    expect(result.current.isTranslating).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('[CRITICAL] translateFromClipboard calls correct Tauri command', async () => {
    const mockTranslationResult = {
      original_text: 'Clipboard text',
      translated_text: 'Текст буфера',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.90,
      cached: false,
      processing_time_ms: 800,
    };

    invoke.mockResolvedValue(mockTranslationResult);

    const { result } = renderHook(() => useTranslationStore());

    await act(async () => {
      await result.current.translateFromClipboard('ru');
    });

    expect(invoke).toHaveBeenCalledWith('translate_from_clipboard', {
      source_lang: 'auto',
      target_lang: 'ru',
    });

    expect(result.current.currentTranslation).toEqual(mockTranslationResult);
  });

  test('sets loading state during translation', async () => {
    // Simulate slow translation
    invoke.mockImplementation(() => new Promise(resolve =>
      setTimeout(() => resolve({
        original_text: 'Test',
        translated_text: 'Тест',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        cached: false,
      }), 100)
    ));

    const { result } = renderHook(() => useTranslationStore());

    const translatePromise = act(async () => {
      await result.current.translateText('Test', 'ru');
    });

    // Should be loading immediately
    expect(result.current.isTranslating).toBe(true);

    await translatePromise;

    // Should finish loading
    expect(result.current.isTranslating).toBe(false);
  });

  test('handles translation errors gracefully', async () => {
    const mockError = new Error('Translation API failed');
    invoke.mockRejectedValue(mockError);

    const { result } = renderHook(() => useTranslationStore());

    await act(async () => {
      await result.current.translateText('Test', 'ru');
    });

    expect(result.current.isTranslating).toBe(false);
    expect(result.current.currentTranslation).toBe(null);
    expect(result.current.error).toBe('Translation API failed');
  });

  test('[CRITICAL] adds successful translations to history', async () => {
    const mockTranslationResult = {
      original_text: 'History test',
      translated_text: 'Тест истории',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.95,
      cached: false,
      processing_time_ms: 1000,
    };

    invoke.mockResolvedValue(mockTranslationResult);

    const { result } = renderHook(() => useTranslationStore());

    await act(async () => {
      await result.current.translateText('History test', 'ru');
    });

    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0]).toMatchObject({
      original_text: 'History test',
      translated_text: 'Тест истории',
      source_lang: 'en',
      target_lang: 'ru',
    });
    expect(result.current.history[0].timestamp).toBeDefined();
  });

  test('setTargetLanguage updates target language', () => {
    const { result } = renderHook(() => useTranslationStore());

    act(() => {
      result.current.setTargetLanguage('fr');
    });

    expect(result.current.targetLanguage).toBe('fr');
  });

  test('clearError clears error state', async () => {
    const mockError = new Error('Test error');
    invoke.mockRejectedValue(mockError);

    const { result } = renderHook(() => useTranslationStore());

    // Generate error
    await act(async () => {
      await result.current.translateText('Test', 'ru');
    });

    expect(result.current.error).toBe('Test error');

    // Clear error
    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });

  test('prevents concurrent translations', async () => {
    invoke.mockImplementation(() => new Promise(resolve =>
      setTimeout(() => resolve({
        original_text: 'Concurrent test',
        translated_text: 'Тест одновременности',
        source_lang: 'en',
        target_lang: 'ru',
        confidence: 0.95,
        cached: false,
      }), 100)
    ));

    const { result } = renderHook(() => useTranslationStore());

    // Start first translation
    const firstTranslation = act(async () => {
      await result.current.translateText('First', 'ru');
    });

    // Try to start second translation while first is running
    await act(async () => {
      await result.current.translateText('Second', 'ru');
    });

    // Second call should be ignored (no second invoke call)
    expect(invoke).toHaveBeenCalledTimes(1);

    await firstTranslation;
  });
});