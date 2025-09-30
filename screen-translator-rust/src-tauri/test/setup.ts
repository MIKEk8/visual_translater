import '@testing-library/jest-dom'

// Mock Tauri API for testing
window.__TAURI_METADATA__ = {}
window.__TAURI__ = {
  invoke: vi.fn().mockResolvedValue({}),
  event: {
    listen: vi.fn(),
    emit: vi.fn(),
  },
  window: {
    appWindow: {
      listen: vi.fn(),
      emit: vi.fn(),
    },
  },
  os: {
    platform: vi.fn().mockResolvedValue('win32'),
  },
}

// Mock console for cleaner test output
global.console = {
  ...console,
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}