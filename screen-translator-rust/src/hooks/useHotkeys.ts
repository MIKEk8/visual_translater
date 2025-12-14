/**
 * Hotkey Management Hook
 *
 * React hook for managing intelligent hotkey system with time-based detection
 * Integrates with Rust backend for Alt+A system functionality
 */

import { useState, useEffect, useCallback } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

export interface HotkeyEvent {
  action: 'QuickTranslate' | 'ContextMenu';
  timestamp: number;
}

export interface SmartTranslationRequest {
  source: 'SelectedText' | 'ClipboardText' | 'ClipboardImage' | 'PreviousArea' | 'NewSelection';
  content: string;
  timestamp: string;
  coordinates?: [number, number, number, number];
}

export interface HotkeyPerformanceStats {
  quick_presses: number;
  long_presses: number;
  total_translations: number;
  context_menu_opens: number;
  average_detection_time_ms: number;
  source_usage: [string, number][];
}

export interface UseHotkeysOptions {
  onQuickTranslation?: (request: SmartTranslationRequest) => void;
  onContextMenu?: () => void;
  onScreenSelection?: () => void;
  quickPressThreshold?: number; // milliseconds
}

export const useHotkeys = (options: UseHotkeysOptions = {}) => {
  const [isContextMenuVisible, setIsContextMenuVisible] = useState(false);
  const [currentTranslationRequest, setCurrentTranslationRequest] = useState<SmartTranslationRequest | null>(null);
  const [performanceStats, setPerformanceStats] = useState<HotkeyPerformanceStats | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize intelligent hotkey system
  const initializeHotkeys = useCallback(async () => {
    try {
      await invoke('initialize_intelligent_hotkey');
      setIsInitialized(true);
      console.log('Intelligent hotkey system initialized');
    } catch (error) {
      console.error('Failed to initialize hotkey system:', error);
    }
  }, []);

  // Handle hotkey long press (context menu)
  const handleLongPress = useCallback(() => {
    console.log('Long press detected - showing context menu');
    setIsContextMenuVisible(true);
    if (options.onContextMenu) {
      options.onContextMenu();
    }
  }, [options]);

  // Handle smart translation request
  const handleTranslationRequest = useCallback((request: SmartTranslationRequest) => {
    console.log('Smart translation request:', request);
    setCurrentTranslationRequest(request);
    if (options.onQuickTranslation) {
      options.onQuickTranslation(request);
    }
  }, [options]);

  // Handle screen selection start
  const handleScreenSelection = useCallback(() => {
    console.log('Starting screen selection');
    if (options.onScreenSelection) {
      options.onScreenSelection();
    }
  }, [options]);

  // Close context menu
  const closeContextMenu = useCallback(() => {
    setIsContextMenuVisible(false);
  }, []);

  // Execute context action
  const executeContextAction = useCallback(async (action: string) => {
    try {
      await invoke('execute_context_action', { action });
      console.log('Executed context action:', action);
    } catch (error) {
      console.error('Failed to execute context action:', error);
    }
  }, []);

  // Get performance statistics
  const getPerformanceStats = useCallback(async () => {
    try {
      const stats: HotkeyPerformanceStats = await invoke('get_hotkey_performance_stats');
      setPerformanceStats(stats);
      return stats;
    } catch (error) {
      console.error('Failed to get performance stats:', error);
      return null;
    }
  }, []);

  // Update quick press threshold
  const updateQuickPressThreshold = useCallback(async (thresholdMs: number) => {
    try {
      await invoke('update_quick_press_threshold', { thresholdMs });
      console.log('Updated quick press threshold to', thresholdMs, 'ms');
    } catch (error) {
      console.error('Failed to update quick press threshold:', error);
    }
  }, []);

  // Get previous areas
  const getPreviousAreas = useCallback(async (limit: number = 5) => {
    try {
      const areas = await invoke('get_previous_areas', { limit });
      return areas;
    } catch (error) {
      console.error('Failed to get previous areas:', error);
      return [];
    }
  }, []);

  // Clear previous areas
  const clearPreviousAreas = useCallback(async () => {
    try {
      await invoke('clear_previous_areas');
      console.log('Cleared previous areas');
    } catch (error) {
      console.error('Failed to clear previous areas:', error);
    }
  }, []);

  // Set up event listeners
  useEffect(() => {
    let unlistenLongPress: UnlistenFn | null = null;
    let unlistenTranslationRequest: UnlistenFn | null = null;
    let unlistenScreenSelection: UnlistenFn | null = null;

    const setupListeners = async () => {
      try {
        // Listen for long press events (context menu)
        unlistenLongPress = await listen('hotkey-long-press', (event) => {
          console.log('Received long press event:', event);
          handleLongPress();
        });

        // Listen for smart translation requests
        unlistenTranslationRequest = await listen('smart-translation-request', (event) => {
          console.log('Received translation request event:', event);
          const request = event.payload as SmartTranslationRequest;
          handleTranslationRequest(request);
        });

        // Listen for screen selection events
        unlistenScreenSelection = await listen('start-screen-selection', (event) => {
          console.log('Received screen selection event:', event);
          handleScreenSelection();
        });

        console.log('Hotkey event listeners set up');
      } catch (error) {
        console.error('Failed to set up event listeners:', error);
      }
    };

    setupListeners();

    // Cleanup listeners on unmount
    return () => {
      if (unlistenLongPress) unlistenLongPress();
      if (unlistenTranslationRequest) unlistenTranslationRequest();
      if (unlistenScreenSelection) unlistenScreenSelection();
    };
  }, [handleLongPress, handleTranslationRequest, handleScreenSelection]);

  // Initialize on mount
  useEffect(() => {
    initializeHotkeys();
  }, [initializeHotkeys]);

  // Update threshold when option changes
  useEffect(() => {
    if (options.quickPressThreshold && isInitialized) {
      updateQuickPressThreshold(options.quickPressThreshold);
    }
  }, [options.quickPressThreshold, isInitialized, updateQuickPressThreshold]);

  return {
    // State
    isContextMenuVisible,
    currentTranslationRequest,
    performanceStats,
    isInitialized,

    // Actions
    closeContextMenu,
    executeContextAction,
    getPerformanceStats,
    updateQuickPressThreshold,
    getPreviousAreas,
    clearPreviousAreas,

    // Utilities
    initializeHotkeys
  };
};

export default useHotkeys;