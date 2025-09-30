// [CRITICAL] MVP Translation Panel Component Tests
// These tests should FAIL initially per TDD approach

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TranslationPanel } from './TranslationPanel';
import { useTranslationStore } from '../store/appStore';

// Mock Tauri API
jest.mock('@tauri-apps/api/core', () => ({
  invoke: jest.fn(),
}));

// Mock store
jest.mock('../store/appStore');

const mockUseTranslationStore = useTranslationStore as jest.MockedFunction<typeof useTranslationStore>;

describe('TranslationPanel', () => {
  beforeEach(() => {
    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: null,
      translateText: jest.fn(),
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('[CRITICAL] renders translation input and translate button', () => {
    // This test will FAIL initially - TranslationPanel component doesn't exist yet
    render(<TranslationPanel />);

    expect(screen.getByPlaceholderText(/enter text to translate/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /translate/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/target language/i)).toBeInTheDocument();
  });

  test('[CRITICAL] calls translateText when translate button clicked', async () => {
    const mockTranslateText = jest.fn();
    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: null,
      translateText: mockTranslateText,
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    const input = screen.getByPlaceholderText(/enter text to translate/i);
    const button = screen.getByRole('button', { name: /translate/i });

    fireEvent.change(input, { target: { value: 'Hello world' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockTranslateText).toHaveBeenCalledWith('Hello world', 'ru');
    });
  });

  test('[CRITICAL] displays translation result when available', () => {
    const mockTranslation = {
      original_text: 'Hello world',
      translated_text: 'Привет мир',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.95,
      cached: false,
    };

    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: mockTranslation,
      translateText: jest.fn(),
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByText('Привет мир')).toBeInTheDocument();
    expect(screen.getByText(/confidence: 95%/i)).toBeInTheDocument();
  });

  test('shows loading state during translation', () => {
    mockUseTranslationStore.mockReturnValue({
      isTranslating: true,
      currentTranslation: null,
      translateText: jest.fn(),
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    expect(screen.getByText(/translating/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /translate/i })).toBeDisabled();
  });

  test('[CRITICAL] translates from clipboard when clipboard button clicked', async () => {
    const mockTranslateFromClipboard = jest.fn();
    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: null,
      translateText: jest.fn(),
      translateFromClipboard: mockTranslateFromClipboard,
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    const clipboardButton = screen.getByRole('button', { name: /from clipboard/i });
    fireEvent.click(clipboardButton);

    await waitFor(() => {
      expect(mockTranslateFromClipboard).toHaveBeenCalledWith('ru');
    });
  });

  test('changes target language when selector changed', () => {
    const mockSetTargetLanguage = jest.fn();
    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: null,
      translateText: jest.fn(),
      translateFromClipboard: jest.fn(),
      setTargetLanguage: mockSetTargetLanguage,
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    const languageSelect = screen.getByLabelText(/target language/i);
    fireEvent.change(languageSelect, { target: { value: 'en' } });

    expect(mockSetTargetLanguage).toHaveBeenCalledWith('en');
  });

  test('validates input is not empty before translation', async () => {
    const mockTranslateText = jest.fn();
    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: null,
      translateText: mockTranslateText,
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    const button = screen.getByRole('button', { name: /translate/i });
    fireEvent.click(button);

    expect(mockTranslateText).not.toHaveBeenCalled();
    expect(screen.getByText(/please enter text to translate/i)).toBeInTheDocument();
  });

  test('copies translation result to clipboard when copy button clicked', async () => {
    // Mock clipboard API
    const mockWriteText = jest.fn();
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    });

    const mockTranslation = {
      original_text: 'Hello world',
      translated_text: 'Привет мир',
      source_lang: 'en',
      target_lang: 'ru',
      confidence: 0.95,
      cached: false,
    };

    mockUseTranslationStore.mockReturnValue({
      isTranslating: false,
      currentTranslation: mockTranslation,
      translateText: jest.fn(),
      translateFromClipboard: jest.fn(),
      setTargetLanguage: jest.fn(),
      targetLanguage: 'ru',
    });

    render(<TranslationPanel />);

    const copyButton = screen.getByRole('button', { name: /copy/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith('Привет мир');
    });
  });
});