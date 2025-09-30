import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Translation {
  id: string
  originalText: string
  translatedText: string
  sourceLang: string
  targetLang: string
  confidence: number
  contextType?: string
  provider: string
  timestamp: Date
}

export interface AppConfig {
  hotkeys: {
    quickTranslate: string
    screenshotArea: string
    showHide: string
  }
  ocr: {
    language: string
    confidenceThreshold: number
    preprocessing: boolean
  }
  translation: {
    sourceLang: string
    targetLang: string
    autoDetect: boolean
    cacheEnabled: boolean
  }
  ui: {
    theme: 'light' | 'dark' | 'system'
    overlayPosition: string
    autoHideDelay: number
  }
}

export interface AppState {
  // UI State
  showContextMenu: boolean
  showTranslationOverlay: boolean
  showAreaSelector: boolean
  showSettings: boolean
  isLoading: boolean
  currentPage: 'home' | 'history' | 'settings'

  // Data State
  translations: Translation[]
  currentTranslation: Translation | null
  config: AppConfig | null

  // Actions
  setShowContextMenu: (show: boolean) => void
  setShowTranslationOverlay: (show: boolean) => void
  setShowAreaSelector: (show: boolean) => void
  setShowSettings: (show: boolean) => void
  setIsLoading: (loading: boolean) => void
  setCurrentPage: (page: 'home' | 'history' | 'settings') => void

  addTranslation: (translation: any) => void
  setCurrentTranslation: (translation: any) => void
  clearTranslations: () => void
  updateConfig: (config: Partial<AppConfig>) => void

  // Computed/Helper functions
  getRecentTranslations: (limit?: number) => Translation[]
  searchTranslations: (query: string) => Translation[]
}

const defaultConfig: AppConfig = {
  hotkeys: {
    quickTranslate: 'Alt+A',
    screenshotArea: 'Alt+S',
    showHide: 'Alt+T'
  },
  ocr: {
    language: 'eng',
    confidenceThreshold: 0.6,
    preprocessing: true
  },
  translation: {
    sourceLang: 'auto',
    targetLang: 'en',
    autoDetect: true,
    cacheEnabled: true
  },
  ui: {
    theme: 'dark',
    overlayPosition: 'center',
    autoHideDelay: 5000
  }
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Initial UI State
      showContextMenu: false,
      showTranslationOverlay: false,
      showAreaSelector: false,
      showSettings: false,
      isLoading: false,
      currentPage: 'home',

      // Initial Data State
      translations: [],
      currentTranslation: null,
      config: defaultConfig,

      // UI Actions
      setShowContextMenu: (show) => set({ showContextMenu: show }),
      setShowTranslationOverlay: (show) => set({ showTranslationOverlay: show }),
      setShowAreaSelector: (show) => set({ showAreaSelector: show }),
      setShowSettings: (show) => set({ showSettings: show }),
      setIsLoading: (loading) => set({ isLoading: loading }),
      setCurrentPage: (page) => set({ currentPage: page }),

      // Data Actions
      addTranslation: (translationData) => {
        const translation: Translation = {
          id: crypto.randomUUID(),
          originalText: translationData.original_text || translationData.originalText,
          translatedText: translationData.translated_text || translationData.translatedText,
          sourceLang: translationData.source_lang || translationData.sourceLang,
          targetLang: translationData.target_lang || translationData.targetLang,
          confidence: translationData.confidence || 0.9,
          contextType: translationData.context_type || translationData.contextType,
          provider: translationData.provider || 'Unknown',
          timestamp: new Date(translationData.timestamp || Date.now())
        }

        set((state) => ({
          translations: [translation, ...state.translations.slice(0, 99)] // Keep last 100
        }))
      },

      setCurrentTranslation: (translationData) => {
        if (!translationData) {
          set({ currentTranslation: null })
          return
        }

        const translation: Translation = {
          id: crypto.randomUUID(),
          originalText: translationData.original_text || translationData.originalText,
          translatedText: translationData.translated_text || translationData.translatedText,
          sourceLang: translationData.source_lang || translationData.sourceLang,
          targetLang: translationData.target_lang || translationData.targetLang,
          confidence: translationData.confidence || 0.9,
          contextType: translationData.context_type || translationData.contextType,
          provider: translationData.provider || 'Unknown',
          timestamp: new Date(translationData.timestamp || Date.now())
        }

        set({ currentTranslation: translation })
      },

      clearTranslations: () => set({ translations: [] }),

      updateConfig: (configUpdate) => {
        set((state) => ({
          config: state.config ? { ...state.config, ...configUpdate } : { ...defaultConfig, ...configUpdate }
        }))
      },

      // Helper functions
      getRecentTranslations: (limit = 10) => {
        const state = get()
        return state.translations
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, limit)
      },

      searchTranslations: (query) => {
        const state = get()
        const searchTerm = query.toLowerCase()
        return state.translations.filter(
          (translation) =>
            translation.originalText.toLowerCase().includes(searchTerm) ||
            translation.translatedText.toLowerCase().includes(searchTerm)
        )
      }
    }),
    {
      name: 'screen-translator-store'
    }
  )
)