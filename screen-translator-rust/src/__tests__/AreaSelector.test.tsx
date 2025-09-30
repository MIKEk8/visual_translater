// [CRITICAL] Screenshot Capture Flow Tests - Screen Translator v3.0
// These tests define the expected behavior for area selection and screenshot capture (Plan Module 4)

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import AreaSelector from '../components/AreaSelector';
import { BrowserRouter } from 'react-router-dom';

// Mock Tauri API
const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: mockInvoke,
}));

// Mock Tauri window API
vi.mock('@tauri-apps/api/window', () => ({
  appWindow: {
    listen: vi.fn(),
    emit: vi.fn(),
    hide: vi.fn(),
    show: vi.fn(),
  },
}));

describe('AreaSelector Component - Screenshot Capture Flow (Plan Module 4)', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] AreaSelector must connect to capture_screenshot command (plan requirement)
  it('should connect to capture_screenshot Tauri command', async () => {
    const mockScreenshotData = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY...';
    mockInvoke.mockResolvedValue(mockScreenshotData);

    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    await waitFor(() => {
      // Expected: Should call capture_screenshot command
      expect(mockInvoke).toHaveBeenCalledWith('capture_screenshot', {
        area: expect.objectContaining({
          x: expect.any(Number),
          y: expect.any(Number),
          width: expect.any(Number),
          height: expect.any(Number),
        })
      });
    });
  });

  // [CRITICAL] AreaSelector must implement drag-to-select functionality (plan requirement)
  it('should implement drag-to-select area functionality', async () => {
    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    // Start drag selection
    fireEvent.mouseDown(selectionOverlay, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 300, clientY: 200 });
    fireEvent.mouseUp(selectionOverlay, { clientX: 300, clientY: 200 });

    await waitFor(() => {
      // Expected: Should call onAreaSelected with correct coordinates
      expect(onAreaSelected).toHaveBeenCalledWith({
        x: 100,
        y: 100,
        width: 200,
        height: 100,
      });
    });
  });

  // [CRITICAL] AreaSelector must validate area coordinates (plan invariant)
  it('should validate area coordinates before capture', async () => {
    mockInvoke.mockRejectedValue(new Error('Invalid coordinates'));

    render(<AreaSelector onAreaSelected={vi.fn()} />);

    // Try to select invalid area (negative coordinates)
    const selectionOverlay = screen.getByTestId('selection-overlay');
    fireEvent.mouseDown(selectionOverlay, { clientX: -50, clientY: -50 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 0, clientY: 0 });
    fireEvent.mouseUp(selectionOverlay, { clientX: 0, clientY: 0 });

    await waitFor(() => {
      // Expected: Should show error for invalid coordinates
      expect(screen.getByTestId('coordinate-error')).toBeInTheDocument();
    });
  });

  // [CRITICAL] AreaSelector must handle screen bounds (plan invariant)
  it('should constrain selection to screen bounds', async () => {
    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} screenBounds={{ width: 1920, height: 1080 }} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    // Try to select area beyond screen bounds
    fireEvent.mouseDown(selectionOverlay, { clientX: 1800, clientY: 1000 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 2100, clientY: 1200 }); // Beyond bounds
    fireEvent.mouseUp(selectionOverlay, { clientX: 2100, clientY: 1200 });

    await waitFor(() => {
      // Expected: Should constrain to screen bounds
      expect(onAreaSelected).toHaveBeenCalledWith({
        x: 1800,
        y: 1000,
        width: 120, // Constrained to screen width
        height: 80,  // Constrained to screen height
      });
    });
  });

  // [CRITICAL] AreaSelector must provide visual feedback during selection
  it('should provide visual feedback during area selection', () => {
    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    // Start selection
    fireEvent.mouseDown(selectionOverlay, { clientX: 100, clientY: 100 });

    // Expected: Should show selection rectangle
    expect(screen.getByTestId('selection-rectangle')).toBeInTheDocument();

    // Continue drag
    fireEvent.mouseMove(selectionOverlay, { clientX: 200, clientY: 150 });

    // Expected: Selection rectangle should update
    const rect = screen.getByTestId('selection-rectangle');
    expect(rect).toHaveStyle({
      left: '100px',
      top: '100px',
      width: '100px',
      height: '50px',
    });
  });

  // [CRITICAL] AreaSelector must support keyboard shortcuts
  it('should support keyboard shortcuts for selection', async () => {
    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} />);

    // Test Escape key to cancel selection
    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByTestId('selection-rectangle')).not.toBeInTheDocument();
    });

    // Test Enter key to confirm selection
    const selectionOverlay = screen.getByTestId('selection-overlay');
    fireEvent.mouseDown(selectionOverlay, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 200, clientY: 200 });
    fireEvent.keyDown(document, { key: 'Enter' });

    await waitFor(() => {
      expect(onAreaSelected).toHaveBeenCalled();
    });
  });

  // [CRITICAL] AreaSelector must handle multiple monitor support
  it('should support multiple monitor selection', async () => {
    const monitors = [
      { id: '0', name: 'Primary', x: 0, y: 0, width: 1920, height: 1080 },
      { id: '1', name: 'Secondary', x: 1920, y: 0, width: 1920, height: 1080 }
    ];

    render(<AreaSelector onAreaSelected={vi.fn()} monitors={monitors} />);

    // Test selection on secondary monitor
    const monitorSelector = screen.getByTestId('monitor-selector');
    fireEvent.change(monitorSelector, { target: { value: '1' } });

    await waitFor(() => {
      expect(screen.getByText(/secondary/i)).toBeInTheDocument();
    });
  });
});

describe('Screenshot Data Handling Tests', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] Must receive screenshot data as base64 (plan interface)
  it('should receive and handle base64 screenshot data', async () => {
    const mockBase64Data = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY...';
    mockInvoke.mockResolvedValue(mockBase64Data);

    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} />);

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    await waitFor(() => {
      // Expected: Should receive valid base64 data
      expect(onAreaSelected).toHaveBeenCalledWith(
        expect.objectContaining({
          imageData: mockBase64Data,
        })
      );
    });
  });

  // [CRITICAL] Must handle screenshot command failures gracefully
  it('should handle screenshot capture failures', async () => {
    mockInvoke.mockRejectedValue(new Error('Screenshot failed'));

    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    await waitFor(() => {
      // Expected: Should show error message
      expect(screen.getByTestId('capture-error')).toBeInTheDocument();
      expect(screen.getByText(/screenshot failed/i)).toBeInTheDocument();
    });
  });

  // [CRITICAL] Must validate screenshot data format
  it('should validate screenshot data format', async () => {
    const invalidData = 'invalid-base64-data';
    mockInvoke.mockResolvedValue(invalidData);

    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} />);

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    await waitFor(() => {
      // Expected: Should show format error
      expect(screen.getByTestId('format-error')).toBeInTheDocument();
    });
  });
});

describe('Area Selection UI Tests', () => {
  // [CRITICAL] UI must show selection coordinates in real-time
  it('should display selection coordinates in real-time', () => {
    render(<AreaSelector onAreaSelected={vi.fn()} showCoordinates={true} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    // Start selection
    fireEvent.mouseDown(selectionOverlay, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 250, clientY: 200 });

    // Expected: Should show current coordinates
    expect(screen.getByTestId('coordinates-display')).toBeInTheDocument();
    expect(screen.getByText(/x: 100, y: 100/i)).toBeInTheDocument();
    expect(screen.getByText(/width: 150, height: 100/i)).toBeInTheDocument();
  });

  // [CRITICAL] UI must provide crosshair cursor during selection
  it('should show crosshair cursor during selection mode', () => {
    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    // Expected: Should have crosshair cursor in selection mode
    expect(selectionOverlay).toHaveClass('cursor-crosshair');
  });

  // [CRITICAL] UI must highlight selected area
  it('should highlight the selected area visually', () => {
    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');

    fireEvent.mouseDown(selectionOverlay, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(selectionOverlay, { clientX: 200, clientY: 150 });

    const selectionRect = screen.getByTestId('selection-rectangle');

    // Expected: Should have proper highlight styling
    expect(selectionRect).toHaveClass('border-blue-500');
    expect(selectionRect).toHaveClass('bg-blue-200');
    expect(selectionRect).toHaveClass('bg-opacity-30');
  });
});

describe('Performance Tests', () => {
  // Performance test - Area selection should be responsive
  it('should handle rapid mouse movements during selection', async () => {
    const onAreaSelected = vi.fn();
    render(<AreaSelector onAreaSelected={onAreaSelected} />);

    const selectionOverlay = screen.getByTestId('selection-overlay');
    const startTime = performance.now();

    // Simulate rapid mouse movements
    fireEvent.mouseDown(selectionOverlay, { clientX: 0, clientY: 0 });
    for (let i = 0; i < 100; i++) {
      fireEvent.mouseMove(selectionOverlay, { clientX: i * 2, clientY: i });
    }
    fireEvent.mouseUp(selectionOverlay, { clientX: 200, clientY: 100 });

    const responseTime = performance.now() - startTime;

    // Expected: Should handle rapid movements within 50ms
    expect(responseTime).toBeLessThan(50);
  });

  // Performance test - Screenshot capture should be fast
  it('should capture screenshots within performance targets', async () => {
    const mockScreenshotData = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY...';
    mockInvoke.mockResolvedValue(mockScreenshotData);

    render(<AreaSelector onAreaSelected={vi.fn()} />);

    const startTime = performance.now();
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    await waitFor(() => {
      expect(mockInvoke).toHaveBeenCalled();
    });

    const captureTime = performance.now() - startTime;

    // Expected: Screenshot should complete within 1 second (plan requirement)
    expect(captureTime).toBeLessThan(1000);
  });
});