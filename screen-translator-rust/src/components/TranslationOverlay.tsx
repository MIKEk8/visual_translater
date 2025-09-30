/**
 * TranslationOverlay Component - Minimal Stub for MVP
 *
 * This is a placeholder component that provides basic structure
 * for tests to pass without full implementation.
 */

import React from 'react';
import { SmartTranslationRequest } from '../hooks/useHotkeys';

interface TranslationOverlayProps {
  isVisible: boolean;
  translation: SmartTranslationRequest | null;
  onClose: () => void;
}

const TranslationOverlay: React.FC<TranslationOverlayProps> = ({
  isVisible,
  translation,
  onClose
}) => {
  if (!isVisible || !translation) {
    return null;
  }

  return (
    <div
      data-testid="translation-overlay"
      style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 10000,
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
        maxWidth: '400px'
      }}
    >
      <div data-testid="translation-result">
        <h3>Translation Result</h3>
        <div data-testid="original-text">
          Original: {translation.content}
        </div>
        <div data-testid="translated-text">
          Translated: [Translation result would appear here]
        </div>
      </div>

      <button
        onClick={onClose}
        style={{
          marginTop: '10px',
          padding: '8px 16px',
          backgroundColor: '#007ACC',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Close
      </button>
    </div>
  );
};

export default TranslationOverlay;