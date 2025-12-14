/**
 * Tests for historyStore
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useHistoryStore } from './historyStore';
import type { TranslationHistoryItem } from './historyStore';

// Mock Tauri API
vi.mock('@tauri-apps/api/tauri', () => ({
  invoke: vi.fn(),
}));

describe('historyStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { clearHistory } = useHistoryStore.getState();
    clearHistory();
  });

  describe('Initial State', () => {
    it('should have empty items array', () => {
      const { items } = useHistoryStore.getState();
      expect(items).toEqual([]);
    });

    it('should have empty filtered items array', () => {
      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toEqual([]);
    });

    it('should have empty filters object', () => {
      const { filters } = useHistoryStore.getState();
      expect(filters).toEqual({});
    });

    it('should not be loading initially', () => {
      const { isLoading } = useHistoryStore.getState();
      expect(isLoading).toBe(false);
    });

    it('should have no error initially', () => {
      const { error } = useHistoryStore.getState();
      expect(error).toBeNull();
    });
  });

  describe('Adding Items', () => {
    it('should add a translation item', async () => {
      const { addItem, items } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const updatedItems = useHistoryStore.getState().items;
      expect(updatedItems).toHaveLength(1);
      expect(updatedItems[0].originalText).toBe('Hello');
      expect(updatedItems[0].translatedText).toBe('Привет');
      expect(updatedItems[0].isFavorite).toBe(false);
    });

    it('should generate unique IDs for items', async () => {
      const { addItem } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'World',
        translatedText: 'Мир',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      expect(items[0].id).not.toBe(items[1].id);
    });

    it('should prepend new items to the beginning', async () => {
      const { addItem } = useHistoryStore.getState();

      await addItem({
        originalText: 'First',
        translatedText: 'Первый',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'Second',
        translatedText: 'Второй',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      expect(items[0].originalText).toBe('Second');
      expect(items[1].originalText).toBe('First');
    });

    it('should limit history to 1000 items', async () => {
      const { addItem } = useHistoryStore.getState();

      // Add 1001 items
      for (let i = 0; i < 1001; i++) {
        await addItem({
          originalText: `Text ${i}`,
          translatedText: `Текст ${i}`,
          sourceLang: 'en',
          targetLang: 'ru',
          confidence: 0.95,
          provider: 'Google',
          timestamp: new Date(),
        });
      }

      const { items } = useHistoryStore.getState();
      expect(items).toHaveLength(1000);
      expect(items[0].originalText).toBe('Text 1000');
    });
  });

  describe('Removing Items', () => {
    it('should remove an item by ID', async () => {
      const { addItem, removeItem } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      const itemId = items[0].id;

      await removeItem(itemId);

      const updatedItems = useHistoryStore.getState().items;
      expect(updatedItems).toHaveLength(0);
    });

    it('should not affect other items when removing', async () => {
      const { addItem, removeItem } = useHistoryStore.getState();

      await addItem({
        originalText: 'First',
        translatedText: 'Первый',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'Second',
        translatedText: 'Второй',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      const firstItemId = items[0].id;

      await removeItem(firstItemId);

      const updatedItems = useHistoryStore.getState().items;
      expect(updatedItems).toHaveLength(1);
      expect(updatedItems[0].originalText).toBe('First');
    });
  });

  describe('Clearing History', () => {
    it('should clear all items', async () => {
      const { addItem, clearHistory } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await clearHistory();

      const { items } = useHistoryStore.getState();
      expect(items).toEqual([]);
    });

    it('should clear filtered items', async () => {
      const { addItem, clearHistory } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await clearHistory();

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toEqual([]);
    });
  });

  describe('Favorites', () => {
    it('should toggle favorite status', async () => {
      const { addItem, toggleFavorite } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      const itemId = items[0].id;

      await toggleFavorite(itemId);

      const updatedItems = useHistoryStore.getState().items;
      expect(updatedItems[0].isFavorite).toBe(true);

      await toggleFavorite(itemId);

      const finalItems = useHistoryStore.getState().items;
      expect(finalItems[0].isFavorite).toBe(false);
    });

    it('should get all favorites', async () => {
      const { addItem, toggleFavorite, getFavorites } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'World',
        translatedText: 'Мир',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      await toggleFavorite(items[0].id);

      const favorites = getFavorites();
      expect(favorites).toHaveLength(1);
      expect(favorites[0].originalText).toBe('World');
    });
  });

  describe('Filters', () => {
    beforeEach(async () => {
      const { addItem } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello World',
        translatedText: 'Привет Мир',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'Goodbye',
        translatedText: 'До свидания',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      await addItem({
        originalText: 'Guten Tag',
        translatedText: 'Good Day',
        sourceLang: 'de',
        targetLang: 'en',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });
    });

    it('should filter by search query', () => {
      const { setFilters, filteredItems } = useHistoryStore.getState();

      setFilters({ searchQuery: 'hello' });

      const filtered = useHistoryStore.getState().filteredItems;
      expect(filtered).toHaveLength(1);
      expect(filtered[0].originalText).toBe('Hello World');
    });

    it('should filter by source language', () => {
      const { setFilters } = useHistoryStore.getState();

      setFilters({ sourceLang: 'de' });

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
      expect(filteredItems[0].originalText).toBe('Guten Tag');
    });

    it('should filter by target language', () => {
      const { setFilters } = useHistoryStore.getState();

      setFilters({ targetLang: 'en' });

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
      expect(filteredItems[0].translatedText).toBe('Good Day');
    });

    it('should combine multiple filters', () => {
      const { setFilters } = useHistoryStore.getState();

      setFilters({ searchQuery: 'hello', sourceLang: 'en' });

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
      expect(filteredItems[0].originalText).toBe('Hello World');
    });

    it('should search in both original and translated text', () => {
      const { setFilters } = useHistoryStore.getState();

      setFilters({ searchQuery: 'мир' });

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
      expect(filteredItems[0].translatedText).toContain('Мир');
    });

    it('should filter favorites only', async () => {
      const { toggleFavorite, setFilters, items } = useHistoryStore.getState();

      await toggleFavorite(items[0].id);

      setFilters({ favoritesOnly: true });

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
      expect(filteredItems[0].isFavorite).toBe(true);
    });
  });

  describe('Search', () => {
    it('should search history', async () => {
      const { addItem, searchHistory } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      searchHistory('hello');

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
    });

    it('should be case-insensitive', async () => {
      const { addItem, searchHistory } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello World',
        translatedText: 'Привет Мир',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      searchHistory('WORLD');

      const { filteredItems } = useHistoryStore.getState();
      expect(filteredItems).toHaveLength(1);
    });
  });

  describe('Computed Getters', () => {
    it('should get recent items with default limit', async () => {
      const { addItem, getRecentItems } = useHistoryStore.getState();

      for (let i = 0; i < 15; i++) {
        await addItem({
          originalText: `Text ${i}`,
          translatedText: `Текст ${i}`,
          sourceLang: 'en',
          targetLang: 'ru',
          confidence: 0.95,
          provider: 'Google',
          timestamp: new Date(Date.now() + i * 1000),
        });
      }

      const recent = getRecentItems();
      expect(recent).toHaveLength(10);
      expect(recent[0].originalText).toBe('Text 14');
    });

    it('should get recent items with custom limit', async () => {
      const { addItem, getRecentItems } = useHistoryStore.getState();

      for (let i = 0; i < 10; i++) {
        await addItem({
          originalText: `Text ${i}`,
          translatedText: `Текст ${i}`,
          sourceLang: 'en',
          targetLang: 'ru',
          confidence: 0.95,
          provider: 'Google',
          timestamp: new Date(Date.now() + i * 1000),
        });
      }

      const recent = getRecentItems(5);
      expect(recent).toHaveLength(5);
    });

    it('should get item by ID', async () => {
      const { addItem, getItemById } = useHistoryStore.getState();

      await addItem({
        originalText: 'Hello',
        translatedText: 'Привет',
        sourceLang: 'en',
        targetLang: 'ru',
        confidence: 0.95,
        provider: 'Google',
        timestamp: new Date(),
      });

      const { items } = useHistoryStore.getState();
      const item = getItemById(items[0].id);

      expect(item).toBeDefined();
      expect(item?.originalText).toBe('Hello');
    });

    it('should return undefined for non-existent ID', () => {
      const { getItemById } = useHistoryStore.getState();

      const item = getItemById('non-existent-id');
      expect(item).toBeUndefined();
    });
  });
});