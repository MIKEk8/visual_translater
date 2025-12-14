/**
 * useTranslation Hook - Translation Service Integration
 *
 * React hook for translation functionality with Tauri backend integration:
 * - AI-powered context-aware translation
 * - Language detection
 * - Translation suggestions
 * - Cache management
 * - History tracking
 */

import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useAppStore } from '../store/appStore';
import { useHistoryStore } from '../store/historyStore';

export interface TranslationResult {
  original_text: string;
  translated_text: string;
  source_lang: string;
  target_lang: string;
  confidence: number;
  context_type?: string;
  provider: string;
  timestamp: string;
}

export interface LanguageDetectionResult {
  language: string;
  confidence: number;
  context_type?: string;
}

export interface TranslationSuggestion {
  target_lang: string;
  reason: string;
  confidence: number;
}

interface UseTranslationReturn {
  translateText: (text: string, targetLang?: string) => Promise<TranslationResult>;
  detectLanguageAndContext: (text: string) => Promise<LanguageDetectionResult>;
  getTranslationSuggestions: (text: string, sourceLang: string) => Promise<TranslationSuggestion[]>;
  translateWithContext: (text: string, contextType?: string, targetLang?: string) => Promise<TranslationResult>;
  isTranslating: boolean;
  error: string | null;
}

const useTranslation = (): UseTranslationReturn => {
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addTranslation = useAppStore((state) => state.addTranslation);
  const addHistoryItem = useHistoryStore((state) => state.addItem);

  const translateText = useCallback(async (text: string, targetLang?: string): Promise<TranslationResult> => {
    setIsTranslating(true);
    setError(null);

    try {
      const result = await invoke<TranslationResult>('translate_text', {
        text,
        targetLang: targetLang || null,
      });

      // Add to store and history
      addTranslation(result);
      await addHistoryItem({
        originalText: result.original_text,
        translatedText: result.translated_text,
        sourceLang: result.source_lang,
        targetLang: result.target_lang,
        confidence: result.confidence,
        contextType: result.context_type,
        provider: result.provider,
        timestamp: new Date(result.timestamp),
      });

      return result;
    } catch (err) {
      const errorMessage = String(err);
      setError(errorMessage);
      console.error('Translation failed:', err);
      throw new Error(errorMessage);
    } finally {
      setIsTranslating(false);
    }
  }, [addTranslation, addHistoryItem]);

  const detectLanguageAndContext = useCallback(async (text: string): Promise<LanguageDetectionResult> => {
    try {
      const result = await invoke<LanguageDetectionResult>('detect_language_and_context', { text });
      return result;
    } catch (err) {
      console.error('Language detection failed:', err);
      throw new Error(String(err));
    }
  }, []);

  const getTranslationSuggestions = useCallback(
    async (text: string, sourceLang: string): Promise<TranslationSuggestion[]> => {
      try {
        const suggestions = await invoke<TranslationSuggestion[]>('get_translation_suggestions', {
          text,
          sourceLang,
        });
        return suggestions;
      } catch (err) {
        console.error('Failed to get translation suggestions:', err);
        return [];
      }
    },
    []
  );

  const translateWithContext = useCallback(
    async (text: string, contextType?: string, targetLang?: string): Promise<TranslationResult> => {
      setIsTranslating(true);
      setError(null);

      try {
        const result = await invoke<TranslationResult>('smart_translate_with_context', {
          text,
          contextType: contextType || null,
          targetLang: targetLang || null,
        });

        // Add to store and history
        addTranslation(result);
        await addHistoryItem({
          originalText: result.original_text,
          translatedText: result.translated_text,
          sourceLang: result.source_lang,
          targetLang: result.target_lang,
          confidence: result.confidence,
          contextType: result.context_type,
          provider: result.provider,
          timestamp: new Date(result.timestamp),
        });

        return result;
      } catch (err) {
        const errorMessage = String(err);
        setError(errorMessage);
        console.error('Context-aware translation failed:', err);
        throw new Error(errorMessage);
      } finally {
        setIsTranslating(false);
      }
    },
    [addTranslation, addHistoryItem]
  );

  return {
    translateText,
    detectLanguageAndContext,
    getTranslationSuggestions,
    translateWithContext,
    isTranslating,
    error,
  };
};

export default useTranslation;