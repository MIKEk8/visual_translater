// [CRITICAL] React App Entry Point Tests - Screen Translator v3.0
// These tests define the expected behavior for React application according to docs/plan.md

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import App from '../App';
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
  },
}));

describe('App Component - Core UI Components (Plan Module 3)', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] App must load MainWindow component with navigation (plan requirement)
  it('should load MainWindow component with navigation', () => {
    // This test will fail until MainWindow is properly integrated
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Expected: MainWindow component should be rendered
    expect(screen.getByTestId('main-window')).toBeInTheDocument();

    // Expected: Navigation should be present
    expect(screen.getByTestId('navigation')).toBeInTheDocument();
  });

  // [CRITICAL] App must have tab navigation for Capture/History/Settings (plan requirement)
  it('should have navigation tabs for main sections', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Expected: Should have tabs for all main sections
    expect(screen.getByRole('tab', { name: /capture/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /history/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /settings/i })).toBeInTheDocument();
  });

  // [CRITICAL] React Router must work for page navigation (plan requirement)
  it('should navigate between different sections', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Navigate to History page
    const historyTab = screen.getByRole('tab', { name: /history/i });
    fireEvent.click(historyTab);

    await waitFor(() => {
      expect(screen.getByTestId('history-page')).toBeInTheDocument();
    });

    // Navigate to Settings page
    const settingsTab = screen.getByRole('tab', { name: /settings/i });
    fireEvent.click(settingsTab);

    await waitFor(() => {
      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    });
  });

  // [CRITICAL] App must not contain placeholder content (plan requirement)
  it('should not contain static placeholder content', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Expected: Should not have placeholder content
    expect(screen.queryByText(/app is working! 🎉/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/rust \+ tauri \+ react application/i)).not.toBeInTheDocument();
  });

  // [CRITICAL] App must connect to Tauri backend commands (plan requirement)
  it('should initialize connection to Tauri backend', async () => {
    mockInvoke.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Expected: Should call initialization commands
      expect(mockInvoke).toHaveBeenCalledWith('get_app_config');
    });
  });

  // [CRITICAL] App must handle Tauri command failures gracefully
  it('should handle backend connection failures gracefully', async () => {
    mockInvoke.mockRejectedValue(new Error('Backend not available'));

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Expected: Should show error state but not crash
      expect(screen.getByTestId('connection-error')).toBeInTheDocument();
    });
  });
});

describe('MainWindow Component - Core UI Layout (Plan Module 3)', () => {
  // [CRITICAL] MainWindow must implement main application layout
  it('should render main application layout', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Expected: Main layout structure should be present
    expect(screen.getByTestId('main-window')).toBeInTheDocument();
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('content-area')).toBeInTheDocument();
  });

  // [CRITICAL] MainWindow must support window management via Tauri APIs
  it('should support window management operations', async () => {
    mockInvoke.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Test minimize functionality
    const minimizeButton = screen.getByTestId('minimize-button');
    fireEvent.click(minimizeButton);

    await waitFor(() => {
      expect(mockInvoke).toHaveBeenCalledWith('minimize_window');
    });
  });

  // [CRITICAL] MainWindow must be styled with Tailwind CSS
  it('should use Tailwind CSS styling', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    const mainWindow = screen.getByTestId('main-window');

    // Expected: Should have Tailwind classes
    expect(mainWindow).toHaveClass('h-screen');
    expect(mainWindow).toHaveClass('bg-gradient-to-br');
  });
});

describe('Navigation Component Tests (Plan Module 3)', () => {
  // [CRITICAL] Navigation must switch between pages
  it('should switch between application pages', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Start on capture page (default)
    expect(screen.getByTestId('capture-page')).toBeInTheDocument();

    // Navigate to history
    fireEvent.click(screen.getByRole('tab', { name: /history/i }));
    await waitFor(() => {
      expect(screen.getByTestId('history-page')).toBeInTheDocument();
      expect(screen.queryByTestId('capture-page')).not.toBeInTheDocument();
    });
  });

  // [CRITICAL] Navigation must show active tab state
  it('should show active tab state', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    const captureTab = screen.getByRole('tab', { name: /capture/i });

    // Expected: Active tab should have active styling
    expect(captureTab).toHaveAttribute('aria-selected', 'true');
    expect(captureTab).toHaveClass('active');
  });
});

describe('Performance Tests', () => {
  // Performance test - React app should load quickly
  it('should render within performance targets', async () => {
    const startTime = performance.now();

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('main-window')).toBeInTheDocument();
    });

    const renderTime = performance.now() - startTime;

    // Expected: Initial render should complete within 100ms
    expect(renderTime).toBeLessThan(100);
  });

  // Memory test - App should not create memory leaks
  it('should clean up resources on unmount', () => {
    const { unmount } = render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Expected: Should unmount cleanly without errors
    expect(() => unmount()).not.toThrow();
  });
});

// Integration tests for React + Tauri communication
describe('React-Tauri Integration Tests', () => {
  // [CRITICAL] React components must call Tauri commands correctly
  it('should call Tauri commands with correct parameters', async () => {
    mockInvoke.mockResolvedValue({
      hotkeys: { quick_translate: 'Alt+A' },
      ocr: { language: 'eng', confidence_threshold: 0.8 },
      translation: { source_lang: 'auto', target_lang: 'en' }
    });

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Expected: Should call config command on startup
      expect(mockInvoke).toHaveBeenCalledWith('get_app_config');
    });
  });

  // [CRITICAL] React must handle Tauri command responses
  it('should handle Tauri command responses correctly', async () => {
    const mockConfig = {
      hotkeys: { quick_translate: 'Alt+A' },
      ocr: { language: 'eng' },
      translation: { source_lang: 'auto', target_lang: 'en' }
    };

    mockInvoke.mockResolvedValue(mockConfig);

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Expected: Should display config data in UI
      expect(screen.getByText(/Alt\+A/)).toBeInTheDocument();
    });
  });

  // [CRITICAL] React must handle Tauri errors gracefully
  it('should handle Tauri command errors gracefully', async () => {
    mockInvoke.mockRejectedValue(new Error('Command failed'));

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Expected: Should show error state
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByText(/command failed/i)).toBeInTheDocument();
    });
  });
});