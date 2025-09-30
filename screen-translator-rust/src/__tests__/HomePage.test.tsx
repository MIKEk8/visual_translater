// [CRITICAL] OCR Processing Pipeline Tests - Screen Translator v3.0
// These tests define the expected behavior for OCR processing and translation integration (Plan Module 5 & 6)

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import HomePage from '../components/pages/HomePage';
import { BrowserRouter } from 'react-router-dom';

// Mock Tauri API
const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: mockInvoke,
}));

// Mock file API for image uploads
Object.defineProperty(window, 'File', {
  value: vi.fn((chunks, filename, options) => ({
    chunks,
    filename,
    options,
    size: chunks.reduce((acc, chunk) => acc + chunk.length, 0),
    type: options.type || 'application/octet-stream',
  })),
});

describe('HomePage Component - OCR Processing Pipeline (Plan Module 5)', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] HomePage must connect image upload to perform_ocr command (plan requirement)
  it('should connect image upload to perform_ocr command', async () => {
    const mockOcrResult = {
      text: 'Hello World',
      confidence: 0.95,
      processing_time_ms: 1500,
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Upload an image
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should call perform_ocr command with base64 image data
      expect(mockInvoke).toHaveBeenCalledWith('perform_ocr', expect.stringMatching(/^data:image/));
    });
  });

  // [CRITICAL] HomePage must display OCR extracted text (plan requirement)
  it('should display extracted OCR text in UI', async () => {
    const mockOcrResult = {
      text: 'Extracted text from image',
      confidence: 0.88,
      processing_time_ms: 2100,
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Upload and process image
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should display extracted text
      expect(screen.getByTestId('extracted-text')).toBeInTheDocument();
      expect(screen.getByText('Extracted text from image')).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must show OCR confidence score (plan interface requirement)
  it('should display OCR confidence score', async () => {
    const mockOcrResult = {
      text: 'Test text',
      confidence: 0.92,
      processing_time_ms: 1800,
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should display confidence score
      expect(screen.getByTestId('confidence-score')).toBeInTheDocument();
      expect(screen.getByText(/92%/)).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must validate confidence range (plan invariant: 0.0-1.0)
  it('should validate OCR confidence is within valid range', async () => {
    const mockOcrResult = {
      text: 'Test text',
      confidence: 1.5, // Invalid: > 1.0
      processing_time_ms: 1500,
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should show validation error
      expect(screen.getByTestId('confidence-error')).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must handle OCR processing failures gracefully
  it('should handle OCR processing failures', async () => {
    mockInvoke.mockRejectedValue(new Error('OCR processing failed'));

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should show error message
      expect(screen.getByTestId('ocr-error')).toBeInTheDocument();
      expect(screen.getByText(/ocr processing failed/i)).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must show processing time (plan interface requirement)
  it('should display OCR processing time', async () => {
    const mockOcrResult = {
      text: 'Test text',
      confidence: 0.90,
      processing_time_ms: 2500,
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Should display processing time
      expect(screen.getByTestId('processing-time')).toBeInTheDocument();
      expect(screen.getByText(/2.5 seconds/i)).toBeInTheDocument();
    });
  });
});

describe('Translation Integration Tests (Plan Module 6)', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] HomePage must connect OCR text to translate_text command (plan requirement)
  it('should connect OCR text to translation service', async () => {
    // Mock OCR result
    const mockOcrResult = {
      text: 'Hello World',
      confidence: 0.95,
      processing_time_ms: 1500,
    };

    // Mock translation result
    const mockTranslationResult = {
      original_text: 'Hello World',
      translated_text: 'Привет мир',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.98,
    };

    mockInvoke
      .mockResolvedValueOnce(mockOcrResult) // First call: perform_ocr
      .mockResolvedValueOnce(mockTranslationResult); // Second call: translate_text

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Upload image for OCR
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    // Trigger translation
    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      // Expected: Should call translate_text with OCR result
      expect(mockInvoke).toHaveBeenCalledWith('translate_text', {
        text: 'Hello World',
        source_lang: 'auto',
        target_lang: 'ru',
      });
    });
  });

  // [CRITICAL] HomePage must display translation results (plan requirement)
  it('should display translation results', async () => {
    const mockOcrResult = {
      text: 'Good morning',
      confidence: 0.92,
      processing_time_ms: 1200,
    };

    const mockTranslationResult = {
      original_text: 'Good morning',
      translated_text: 'Доброе утро',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.96,
    };

    mockInvoke
      .mockResolvedValueOnce(mockOcrResult)
      .mockResolvedValueOnce(mockTranslationResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Process image and translate
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(screen.getByText('Good morning')).toBeInTheDocument();
    });

    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      // Expected: Should display translated text
      expect(screen.getByTestId('translated-text')).toBeInTheDocument();
      expect(screen.getByText('Доброе утро')).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must validate translation requests (plan invariant)
  it('should validate translation requests for non-empty text', async () => {
    const mockOcrResult = {
      text: '', // Empty text
      confidence: 0.50,
      processing_time_ms: 800,
    };

    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      // Expected: Translate button should be disabled for empty text
      const translateButton = screen.getByTestId('translate-button');
      expect(translateButton).toBeDisabled();
    });
  });

  // [CRITICAL] HomePage must handle translation failures gracefully
  it('should handle translation service failures', async () => {
    const mockOcrResult = {
      text: 'Test text',
      confidence: 0.85,
      processing_time_ms: 1600,
    };

    mockInvoke
      .mockResolvedValueOnce(mockOcrResult)
      .mockRejectedValueOnce(new Error('Translation service unavailable'));

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Process image
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(screen.getByText('Test text')).toBeInTheDocument();
    });

    // Try translation
    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      // Expected: Should show translation error
      expect(screen.getByTestId('translation-error')).toBeInTheDocument();
      expect(screen.getByText(/translation service unavailable/i)).toBeInTheDocument();
    });
  });
});

describe('Smart Translation Integration (Plan AI Features)', () => {
  beforeEach(() => {
    mockInvoke.mockClear();
  });

  // [CRITICAL] HomePage must support smart_translate_with_context command
  it('should use smart translation with context detection', async () => {
    const mockOcrResult = {
      text: 'import pandas as pd\ndf.head()',
      confidence: 0.94,
      processing_time_ms: 1800,
    };

    const mockSmartTranslationResult = {
      original_text: 'import pandas as pd\ndf.head()',
      translated_text: 'импорт pandas как pd\ndf.head()',
      source_language: 'en',
      target_language: 'ru',
      context_type: 'Technical',
      detection_confidence: 0.96,
      context_confidence: 0.89,
      processing_time_ms: 2200,
    };

    mockInvoke
      .mockResolvedValueOnce(mockOcrResult)
      .mockResolvedValueOnce(mockSmartTranslationResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Enable smart translation
    const smartToggle = screen.getByTestId('smart-translation-toggle');
    fireEvent.click(smartToggle);

    // Process image
    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'code.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(screen.getByText(/import pandas/)).toBeInTheDocument();
    });

    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      // Expected: Should call smart translation command
      expect(mockInvoke).toHaveBeenCalledWith('smart_translate_with_context', {
        text: 'import pandas as pd\ndf.head()',
        context_type: null, // Auto-detect
        target_lang: null,  // Auto-suggest
      });

      // Expected: Should show context information
      expect(screen.getByTestId('context-info')).toBeInTheDocument();
      expect(screen.getByText(/technical/i)).toBeInTheDocument();
    });
  });

  // [CRITICAL] HomePage must show AI detection confidence
  it('should display AI detection and context confidence', async () => {
    const mockSmartTranslationResult = {
      original_text: 'Test text',
      translated_text: 'Тестовый текст',
      source_language: 'en',
      target_language: 'ru',
      context_type: 'Document',
      detection_confidence: 0.87,
      context_confidence: 0.92,
      processing_time_ms: 1900,
    };

    mockInvoke.mockResolvedValue(mockSmartTranslationResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Mock existing OCR text
    const textArea = screen.getByTestId('ocr-text-area');
    fireEvent.change(textArea, { target: { value: 'Test text' } });

    const smartToggle = screen.getByTestId('smart-translation-toggle');
    fireEvent.click(smartToggle);

    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      // Expected: Should show AI confidence scores
      expect(screen.getByTestId('detection-confidence')).toBeInTheDocument();
      expect(screen.getByText(/87%/)).toBeInTheDocument(); // Detection confidence

      expect(screen.getByTestId('context-confidence')).toBeInTheDocument();
      expect(screen.getByText(/92%/)).toBeInTheDocument(); // Context confidence
    });
  });
});

describe('Performance Tests', () => {
  // Performance test - OCR processing should meet time requirements
  it('should complete OCR processing within performance targets', async () => {
    const mockOcrResult = {
      text: 'Performance test text',
      confidence: 0.91,
      processing_time_ms: 1800, // Within 2 second target
    };
    mockInvoke.mockResolvedValue(mockOcrResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    const startTime = performance.now();

    const fileInput = screen.getByTestId('image-upload-input');
    const mockFile = new File(['mock-image-data'], 'test.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(screen.getByText('Performance test text')).toBeInTheDocument();
    });

    const totalTime = performance.now() - startTime;

    // Expected: Complete workflow within 2 seconds (plan requirement)
    expect(totalTime).toBeLessThan(2000);
  });

  // Performance test - Translation should be fast
  it('should complete translation within performance targets', async () => {
    const mockTranslationResult = {
      original_text: 'Speed test',
      translated_text: 'Тест скорости',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.95,
    };
    mockInvoke.mockResolvedValue(mockTranslationResult);

    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );

    // Mock existing OCR text
    const textArea = screen.getByTestId('ocr-text-area');
    fireEvent.change(textArea, { target: { value: 'Speed test' } });

    const startTime = performance.now();

    const translateButton = screen.getByTestId('translate-button');
    fireEvent.click(translateButton);

    await waitFor(() => {
      expect(screen.getByText('Тест скорости')).toBeInTheDocument();
    });

    const translationTime = performance.now() - startTime;

    // Expected: Translation within 1 second for cached results (plan requirement)
    expect(translationTime).toBeLessThan(3000); // 3 seconds for API calls
  });
});