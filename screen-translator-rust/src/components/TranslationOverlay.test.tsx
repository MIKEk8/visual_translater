/**
 * Tests for TranslationOverlay component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TranslationOverlay from './TranslationOverlay';
import type { SmartTranslationRequest } from '../hooks/useHotkeys';

describe('TranslationOverlay', () => {
  const mockOnClose = vi.fn();

  const mockTranslation: SmartTranslationRequest = {
    source: 'ClipboardText',
    content: 'Hello, world!',
    timestamp: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should not render when not visible', () => {
      const { container } = render(
        <TranslationOverlay isVisible={false} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should not render when translation is null', () => {
      const { container } = render(
        <TranslationOverlay isVisible={true} translation={null} onClose={mockOnClose} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render when visible with translation', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('translation-overlay')).toBeInTheDocument();
    });

    it('should display translation result section', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('translation-result')).toBeInTheDocument();
    });

    it('should display original text', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('original-text')).toHaveTextContent('Hello, world!');
    });

    it('should display translated text placeholder', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('translated-text')).toBeInTheDocument();
    });
  });

  describe('Close Button', () => {
    it('should render close button', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });

    it('should call onClose when close button is clicked', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Styling', () => {
    it('should have fixed positioning', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const overlay = screen.getByTestId('translation-overlay');
      expect(overlay).toHaveStyle({ position: 'fixed' });
    });

    it('should be centered on screen', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const overlay = screen.getByTestId('translation-overlay');
      expect(overlay).toHaveStyle({
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      });
    });

    it('should have high z-index', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const overlay = screen.getByTestId('translation-overlay');
      expect(overlay).toHaveStyle({ zIndex: 10000 });
    });
  });

  describe('Content', () => {
    it('should display Translation Result heading', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByText('Translation Result')).toBeInTheDocument();
    });

    it('should display original label', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByText(/Original:/)).toBeInTheDocument();
    });

    it('should display translated label', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByText(/Translated:/)).toBeInTheDocument();
    });
  });

  describe('Different Translation Sources', () => {
    it('should render for ClipboardText source', () => {
      const translation: SmartTranslationRequest = {
        source: 'ClipboardText',
        content: 'Clipboard content',
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('original-text')).toHaveTextContent('Clipboard content');
    });

    it('should render for SelectedText source', () => {
      const translation: SmartTranslationRequest = {
        source: 'SelectedText',
        content: 'Selected text',
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('original-text')).toHaveTextContent('Selected text');
    });

    it('should render for ClipboardImage source', () => {
      const translation: SmartTranslationRequest = {
        source: 'ClipboardImage',
        content: 'base64imagedata',
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('translation-overlay')).toBeInTheDocument();
    });

    it('should render for PreviousArea source', () => {
      const translation: SmartTranslationRequest = {
        source: 'PreviousArea',
        content: 'Previous area text',
        timestamp: new Date().toISOString(),
        coordinates: [0, 0, 100, 100],
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('translation-overlay')).toBeInTheDocument();
    });

    it('should render for NewSelection source', () => {
      const translation: SmartTranslationRequest = {
        source: 'NewSelection',
        content: 'New selection text',
        timestamp: new Date().toISOString(),
        coordinates: [0, 0, 100, 100],
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('translation-overlay')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty content', () => {
      const translation: SmartTranslationRequest = {
        source: 'ClipboardText',
        content: '',
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('original-text')).toHaveTextContent('');
    });

    it('should handle very long content', () => {
      const longContent = 'A'.repeat(1000);
      const translation: SmartTranslationRequest = {
        source: 'ClipboardText',
        content: longContent,
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      expect(screen.getByTestId('original-text')).toHaveTextContent(longContent);
    });

    it('should handle special characters in content', () => {
      const translation: SmartTranslationRequest = {
        source: 'ClipboardText',
        content: '<script>alert("xss")</script>',
        timestamp: new Date().toISOString(),
      };

      render(<TranslationOverlay isVisible={true} translation={translation} onClose={mockOnClose} />);

      // Content should be escaped
      expect(screen.getByTestId('original-text')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible close button', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const closeButton = screen.getByRole('button');
      expect(closeButton).toBeInTheDocument();
    });

    it('should allow keyboard interaction with close button', () => {
      render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      const closeButton = screen.getByRole('button');
      fireEvent.keyDown(closeButton, { key: 'Enter' });

      // Button should still be focusable and interactive
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe('State Changes', () => {
    it('should update when translation changes', () => {
      const { rerender } = render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('original-text')).toHaveTextContent('Hello, world!');

      const newTranslation: SmartTranslationRequest = {
        source: 'ClipboardText',
        content: 'New content',
        timestamp: new Date().toISOString(),
      };

      rerender(
        <TranslationOverlay isVisible={true} translation={newTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('original-text')).toHaveTextContent('New content');
    });

    it('should unmount when visibility changes to false', () => {
      const { rerender, container } = render(
        <TranslationOverlay isVisible={true} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(screen.getByTestId('translation-overlay')).toBeInTheDocument();

      rerender(
        <TranslationOverlay isVisible={false} translation={mockTranslation} onClose={mockOnClose} />
      );

      expect(container.firstChild).toBeNull();
    });
  });
});