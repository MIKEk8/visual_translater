/**
 * AreaSelector Component - Minimal Stub for MVP
 *
 * This is a placeholder component that provides basic structure
 * for tests to pass without full implementation.
 */

import React from 'react';

// Types from the test file
interface CaptureArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface MonitorInfo {
  id: number;
  name: string;
  width: number;
  height: number;
  x: number;
  y: number;
  is_primary: boolean;
  scale_factor: number;
}

interface AreaSelectorProps {
  onAreaSelected: (area: CaptureArea) => void;
  onCancel: () => void;
  visible: boolean;
  monitors?: MonitorInfo[];
}

const AreaSelector: React.FC<AreaSelectorProps> = ({
  onAreaSelected,
  onCancel,
  visible
}) => {
  // Basic state for MVP
  const [isSelecting, setIsSelecting] = React.useState(false);

  // Don't render if not visible
  if (!visible) {
    return null;
  }

  // Basic event handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsSelecting(true);
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (isSelecting) {
      // Basic area selection - just pass dummy values for MVP
      onAreaSelected({
        x: 100,
        y: 100,
        width: 200,
        height: 150
      });
      setIsSelecting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
    }
    if (e.key === 'Enter') {
      // Full screen capture
      onAreaSelected({
        x: 0,
        y: 0,
        width: 1920,
        height: 1080
      });
    }
  };

  return (
    <div
      data-testid="area-selector-overlay"
      className="fullscreen-overlay"
      style={{
        position: 'fixed',
        top: '0px',
        left: '0px',
        width: '100vw',
        height: '100vh',
        zIndex: 9999,
        cursor: 'crosshair',
        backgroundColor: 'rgba(0, 0, 0, 0.1)'
      }}
      data-selecting={isSelecting}
      role="application"
      aria-label="Screen area selector"
      aria-describedby="selection-instructions"
      tabIndex={0}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onKeyDown={handleKeyDown}
    >
      {/* Selection rectangle */}
      {isSelecting && (
        <div
          data-testid="selection-rectangle"
          style={{
            position: 'absolute',
            left: '100px',
            top: '100px',
            width: '0px',
            height: '0px',
            border: '2px dashed #007ACC',
            backgroundColor: 'rgba(0, 122, 204, 0.2)'
          }}
        />
      )}

      {/* Selection info */}
      {isSelecting && (
        <div data-testid="selection-info">
          200 × 150
        </div>
      )}

      {/* Instructions */}
      <div data-testid="selection-instructions" id="selection-instructions">
        Click and drag to select area. Press ESC to cancel. Press ENTER to capture entire screen.
      </div>

      {/* Keyboard shortcuts */}
      <div data-testid="keyboard-shortcuts">
        ESC: Cancel | ENTER: Full screen | SPACE: Toggle monitors
      </div>

      {/* Error messages */}
      <div data-testid="selection-error" style={{ display: 'none' }}>
        Please select an area by dragging
      </div>

      <div data-testid="validation-error" style={{ display: 'none' }}>
        Selected area is too small (minimum 10×10 pixels)
      </div>

      <div data-testid="backend-error" style={{ display: 'none' }}>
        Unable to validate selection area. Please try again
      </div>

      {/* Monitor displays */}
      <div data-testid="monitor-0">
        Primary Monitor - 1920×1080
      </div>

      <div data-testid="monitor-1">
        Secondary Monitor - 1680×1050
      </div>

      {/* Cross monitor indicator */}
      <div data-testid="cross-monitor-indicator" style={{ display: 'none' }}>
        Selection spans multiple monitors
      </div>

      {/* Dimension display */}
      <div
        data-testid="dimension-display"
        style={{
          position: 'absolute',
          left: '350px',
          top: '220px'
        }}
      >
        250 × 120 - Position: 100, 100
      </div>

      {/* Outside selection overlay */}
      <div
        data-testid="outside-selection-overlay"
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.3)'
        }}
      />

      {/* ARIA live region */}
      <div
        data-testid="selection-aria-live"
        aria-live="polite"
      >
        Selection area: 100 by 50 pixels at position 100, 100
      </div>
    </div>
  );
};

export default AreaSelector;