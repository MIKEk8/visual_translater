/**
 * Animated Context Menu Component
 *
 * Beautiful floating menu that appears on Alt+A long press (>= 1 second)
 * Features:
 * - Fade-in/fade-out animations with 0.95 transparency
 * - Keyboard navigation (arrows, numbers, Enter, Esc)
 * - 6 main actions with icons and descriptions
 * - Smart positioning at screen center
 * - Smooth transitions using Framer Motion
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

interface ContextMenuItem {
  id: string;
  label: string;
  description: string;
  icon: string;
  shortcut?: string;
  action: string;
}

interface ContextMenuProps {
  isVisible: boolean;
  onClose: () => void;
  onAction: (action: string) => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ isVisible, onClose, onAction }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [menuItems, setMenuItems] = useState<ContextMenuItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load menu items from Rust backend
  useEffect(() => {
    const loadMenuItems = async () => {
      try {
        const items: ContextMenuItem[] = await invoke('get_context_menu_items');
        setMenuItems(items);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to load context menu items:', error);
        setIsLoading(false);
        // Fallback to default items
        setMenuItems(getDefaultMenuItems());
      }
    };

    if (isVisible) {
      loadMenuItems();
    }
  }, [isVisible]);

  // Keyboard event handler
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!isVisible) return;

    switch (event.key) {
      case 'Escape':
        event.preventDefault();
        onClose();
        break;

      case 'ArrowDown':
      case 'ArrowRight':
        event.preventDefault();
        setSelectedIndex(prev => (prev + 1) % menuItems.length);
        break;

      case 'ArrowUp':
      case 'ArrowLeft':
        event.preventDefault();
        setSelectedIndex(prev => (prev - 1 + menuItems.length) % menuItems.length);
        break;

      case 'Enter':
      case ' ':
        event.preventDefault();
        if (menuItems[selectedIndex]) {
          handleItemAction(menuItems[selectedIndex].action);
        }
        break;

      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6': {
        event.preventDefault();
        const index = parseInt(event.key) - 1;
        if (index >= 0 && index < menuItems.length) {
          setSelectedIndex(index);
          handleItemAction(menuItems[index].action);
        }
        break;
      }

      default:
        break;
    }
  }, [isVisible, menuItems, selectedIndex, onClose]);

  // Set up keyboard listeners
  useEffect(() => {
    if (isVisible) {
      document.addEventListener('keydown', handleKeyDown);
      // Focus the menu for accessibility
      const menuElement = document.getElementById('context-menu');
      if (menuElement) {
        menuElement.focus();
      }
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isVisible, handleKeyDown]);

  // Handle item action
  const handleItemAction = async (action: string) => {
    try {
      await invoke('execute_context_action', { action });
      onAction(action);
      onClose();
    } catch (error) {
      console.error('Failed to execute action:', action, error);
    }
  };

  // Handle mouse click
  const handleItemClick = (item: ContextMenuItem, index: number) => {
    setSelectedIndex(index);
    handleItemAction(item.action);
  };

  // Handle mouse hover
  const handleItemHover = (index: number) => {
    setSelectedIndex(index);
  };

  // Default menu items (fallback)
  const getDefaultMenuItems = (): ContextMenuItem[] => [
    {
      id: 'screenshot',
      label: 'Screenshot Area',
      description: 'Select screen area for translation',
      icon: '📷',
      shortcut: '1',
      action: 'screenshot_area'
    },
    {
      id: 'clipboard',
      label: 'Clipboard Translation',
      description: 'Translate clipboard content',
      icon: '📋',
      shortcut: '2',
      action: 'translate_clipboard'
    },
    {
      id: 'region',
      label: 'Smart Region Selection',
      description: 'AI-powered text region detection',
      icon: '🎯',
      shortcut: '3',
      action: 'smart_region'
    },
    {
      id: 'repeat',
      label: 'Repeat Last',
      description: 'Repeat last translation',
      icon: '🔄',
      shortcut: '4',
      action: 'repeat_last'
    },
    {
      id: 'history',
      label: 'Translation History',
      description: 'View recent translations',
      icon: '📚',
      shortcut: '5',
      action: 'show_history'
    },
    {
      id: 'settings',
      label: 'Settings',
      description: 'Open application settings',
      icon: '⚙️',
      shortcut: '6',
      action: 'show_settings'
    }
  ];

  // Animation variants
  const menuVariants = {
    hidden: {
      opacity: 0,
      scale: 0.8,
      y: 20,
      transition: {
        duration: 0.2,
        ease: 'easeOut'
      }
    },
    visible: {
      opacity: 0.95,
      scale: 1,
      y: 0,
      transition: {
        duration: 0.3,
        ease: 'easeOut',
        staggerChildren: 0.05
      }
    },
    exit: {
      opacity: 0,
      scale: 0.9,
      y: -10,
      transition: {
        duration: 0.2,
        ease: 'easeIn'
      }
    }
  };

  const itemVariants = {
    hidden: {
      opacity: 0,
      x: -20
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        duration: 0.2,
        ease: 'easeOut'
      }
    }
  };

  if (isLoading) {
    return (
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.95 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50"
            onClick={onClose}
          >
            <div className="bg-white rounded-lg p-6 shadow-2xl">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">Loading menu...</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50"
          onClick={onClose}
        >
          <motion.div
            id="context-menu"
            variants={menuVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 p-2 min-w-[320px] max-w-[400px] focus:outline-none"
            onClick={(e) => e.stopPropagation()}
            tabIndex={-1}
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Quick Actions
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Use arrow keys or numbers to select
              </p>
            </div>

            {/* Menu Items */}
            <div className="py-2">
              {menuItems.map((item, index) => (
                <motion.button
                  key={item.id}
                  variants={itemVariants}
                  className={`w-full flex items-center px-4 py-3 text-left rounded-lg transition-all duration-200 ${
                    selectedIndex === index
                      ? 'bg-blue-500 text-white shadow-md transform scale-[1.02]'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  onClick={() => handleItemClick(item, index)}
                  onMouseEnter={() => handleItemHover(index)}
                >
                  <div className="flex items-center space-x-3 flex-1">
                    <span className="text-2xl">{item.icon}</span>
                    <div className="flex-1">
                      <div className="font-medium">{item.label}</div>
                      <div className={`text-sm ${
                        selectedIndex === index
                          ? 'text-blue-100'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {item.description}
                      </div>
                    </div>
                    {item.shortcut && (
                      <span className={`text-xs px-2 py-1 rounded-md font-mono ${
                        selectedIndex === index
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                      }`}>
                        {item.shortcut}
                      </span>
                    )}
                  </div>
                </motion.button>
              ))}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
                <span>Press ESC to close</span>
                <span>Enter to select</span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ContextMenu;