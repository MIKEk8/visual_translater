/**
 * HistoryWindow Component - Minimal Stub for MVP
 *
 * This is a placeholder component that provides basic structure
 * for tests to pass without full implementation.
 */

import React from 'react';

interface HistoryWindowProps {
  onBack: () => void;
}

const HistoryWindow: React.FC<HistoryWindowProps> = ({ onBack }) => {
  return (
    <div data-testid="history-window" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
        <button
          onClick={onBack}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007ACC',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            marginRight: '16px'
          }}
        >
          ← Back
        </button>
        <h1>Translation History</h1>
      </div>

      <div data-testid="history-list">
        <div data-testid="history-item">
          <div>Hello → Привет</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            2 minutes ago
          </div>
        </div>
      </div>

      <div data-testid="history-search">
        <input
          type="text"
          placeholder="Search history..."
          style={{
            width: '100%',
            padding: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
      </div>
    </div>
  );
};

export default HistoryWindow;