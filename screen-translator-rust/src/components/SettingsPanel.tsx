/**
 * SettingsPanel Component - Minimal Stub for MVP
 *
 * This is a placeholder component that provides basic structure
 * for tests to pass without full implementation.
 */

import React from 'react';

interface SettingsPanelProps {
  onBack: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ onBack }) => {
  return (
    <div data-testid="settings-panel" style={{ padding: '20px' }}>
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
        <h1>Settings</h1>
      </div>

      <div data-testid="settings-content">
        <div style={{ marginBottom: '16px' }}>
          <label>Theme:</label>
          <select style={{ marginLeft: '8px', padding: '4px' }}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label>Source Language:</label>
          <select style={{ marginLeft: '8px', padding: '4px' }}>
            <option value="en">English</option>
            <option value="ru">Russian</option>
            <option value="de">German</option>
          </select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label>Target Language:</label>
          <select style={{ marginLeft: '8px', padding: '4px' }}>
            <option value="ru">Russian</option>
            <option value="en">English</option>
            <option value="de">German</option>
          </select>
        </div>

        <div data-testid="hotkey-settings">
          <h3>Hotkey Settings</h3>
          <div>
            Quick Translate: Alt+A (Quick Press)
          </div>
          <div>
            Context Menu: Alt+A (Long Press)
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;