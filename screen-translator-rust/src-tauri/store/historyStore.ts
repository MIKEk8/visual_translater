/**
 * History Store - Translation History Management
 *
 * Zustand store for managing translation history:
 * - Recent translations
 * - Search and filter
 * - Favorites
 * - Export functionality
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { invoke } from '@tauri-apps/api/tauri';

export interface TranslationHistoryItem {
  id: string;
  originalText: string;
  translatedText: string;
  sourceLang: string;
  targetLang: string;
  confidence: number;
  contextType?: string;
  provider: string;
  timestamp: Date;
  isFavorite: boolean;
}

export interface HistoryFilters {
  searchQuery?: string;
  sourceLang?: string;
  targetLang?: string;
  contextType?: string;
  dateFrom?: Date;
  dateTo?: Date;
  favoritesOnly?: boolean;
}

export interface HistoryState {
  items: TranslationHistoryItem[];
  filteredItems: TranslationHistoryItem[];
  filters: HistoryFilters;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadHistory: () => Promise<void>;
  addItem: (item: Omit<TranslationHistoryItem, 'id' | 'isFavorite'>) => Promise<void>;
  removeItem: (id: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  toggleFavorite: (id: string) => Promise<void>;
  setFilters: (filters: HistoryFilters) => void;
  searchHistory: (query: string) => void;
  exportHistory: (format: 'json' | 'csv' | 'txt') => Promise<void>;

  // Computed
  getRecentItems: (limit?: number) => TranslationHistoryItem[];
  getFavorites: () => TranslationHistoryItem[];
  getItemById: (id: string) => TranslationHistoryItem | undefined;
}

export const useHistoryStore = create<HistoryState>()(
  devtools(
    persist(
      (set, get) => ({
        items: [],
        filteredItems: [],
        filters: {},
        isLoading: false,
        error: null,

        loadHistory: async () => {
          set({ isLoading: true, error: null });
          try {
            const history = await invoke<TranslationHistoryItem[]>('load_translation_history');
            const parsedHistory = history.map(item => ({
              ...item,
              timestamp: new Date(item.timestamp),
              isFavorite: item.isFavorite || false,
            }));
            set({ items: parsedHistory, filteredItems: parsedHistory, isLoading: false });
          } catch (error) {
            console.error('Failed to load history:', error);
            set({ isLoading: false, error: String(error) });
          }
        },

        addItem: async (itemData) => {
          try {
            const newItem: TranslationHistoryItem = {
              id: crypto.randomUUID(),
              ...itemData,
              isFavorite: false,
              timestamp: new Date(),
            };

            await invoke('add_translation_to_history', { item: newItem });

            set((state) => {
              const newItems = [newItem, ...state.items].slice(0, 1000); // Keep last 1000
              return {
                items: newItems,
                filteredItems: applyFilters(newItems, state.filters),
              };
            });
          } catch (error) {
            console.error('Failed to add history item:', error);
            set({ error: String(error) });
          }
        },

        removeItem: async (id) => {
          try {
            await invoke('remove_translation_from_history', { id });
            set((state) => {
              const newItems = state.items.filter((item) => item.id !== id);
              return {
                items: newItems,
                filteredItems: applyFilters(newItems, state.filters),
              };
            });
          } catch (error) {
            console.error('Failed to remove history item:', error);
            set({ error: String(error) });
          }
        },

        clearHistory: async () => {
          try {
            await invoke('clear_translation_history');
            set({ items: [], filteredItems: [], error: null });
          } catch (error) {
            console.error('Failed to clear history:', error);
            set({ error: String(error) });
          }
        },

        toggleFavorite: async (id) => {
          try {
            const item = get().items.find((i) => i.id === id);
            if (!item) return;

            const updatedItem = { ...item, isFavorite: !item.isFavorite };
            await invoke('update_translation_favorite', { id, isFavorite: updatedItem.isFavorite });

            set((state) => {
              const newItems = state.items.map((i) => (i.id === id ? updatedItem : i));
              return {
                items: newItems,
                filteredItems: applyFilters(newItems, state.filters),
              };
            });
          } catch (error) {
            console.error('Failed to toggle favorite:', error);
            set({ error: String(error) });
          }
        },

        setFilters: (filters) => {
          set((state) => ({
            filters,
            filteredItems: applyFilters(state.items, filters),
          }));
        },

        searchHistory: (query) => {
          get().setFilters({ searchQuery: query });
        },

        exportHistory: async (format) => {
          try {
            await invoke('export_translation_history', { format });
          } catch (error) {
            console.error('Failed to export history:', error);
            set({ error: String(error) });
          }
        },

        // Computed getters
        getRecentItems: (limit = 10) => {
          return get()
            .items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
            .slice(0, limit);
        },

        getFavorites: () => {
          return get().items.filter((item) => item.isFavorite);
        },

        getItemById: (id) => {
          return get().items.find((item) => item.id === id);
        },
      }),
      {
        name: 'history-store',
        partialize: (state) => ({
          items: state.items.slice(0, 100), // Persist only last 100 items
        }),
      }
    ),
    { name: 'HistoryStore' }
  )
);

// Helper function to apply filters
function applyFilters(items: TranslationHistoryItem[], filters: HistoryFilters): TranslationHistoryItem[] {
  let filtered = items;

  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (item) =>
        item.originalText.toLowerCase().includes(query) ||
        item.translatedText.toLowerCase().includes(query)
    );
  }

  if (filters.sourceLang) {
    filtered = filtered.filter((item) => item.sourceLang === filters.sourceLang);
  }

  if (filters.targetLang) {
    filtered = filtered.filter((item) => item.targetLang === filters.targetLang);
  }

  if (filters.contextType) {
    filtered = filtered.filter((item) => item.contextType === filters.contextType);
  }

  if (filters.dateFrom) {
    filtered = filtered.filter((item) => item.timestamp >= filters.dateFrom!);
  }

  if (filters.dateTo) {
    filtered = filtered.filter((item) => item.timestamp <= filters.dateTo!);
  }

  if (filters.favoritesOnly) {
    filtered = filtered.filter((item) => item.isFavorite);
  }

  return filtered;
}

export default useHistoryStore;