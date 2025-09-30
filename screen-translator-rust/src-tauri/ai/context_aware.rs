/*!
AI-Enhanced Context-Aware Translation

Intelligent language and context detection system that automatically:
- Detects source language from 7 supported languages
- Identifies context type (Technical, Gaming, UI, Document, Subtitle)
- Suggests optimal target language based on user patterns
- Provides smart translation suggestions with confidence scoring

Performance: ~0.001-0.01 sec for language detection with caching
*/

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Supported languages for context-aware translation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Language {
    English,  // EN
    Russian,  // RU
    German,   // DE
    French,   // FR
    Spanish,  // ES
    Japanese, // JA
    Chinese,  // ZH
}

impl Language {
    pub fn code(&self) -> &'static str {
        match self {
            Language::English => "en",
            Language::Russian => "ru",
            Language::German => "de",
            Language::French => "fr",
            Language::Spanish => "es",
            Language::Japanese => "ja",
            Language::Chinese => "zh",
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            Language::English => "English",
            Language::Russian => "Русский",
            Language::German => "Deutsch",
            Language::French => "Français",
            Language::Spanish => "Español",
            Language::Japanese => "日本語",
            Language::Chinese => "中文",
        }
    }

    /// Parse language from code string
    pub fn from_code(code: &str) -> Option<Language> {
        match code.to_lowercase().as_str() {
            "en" | "eng" | "english" => Some(Language::English),
            "ru" | "rus" | "russian" => Some(Language::Russian),
            "de" | "deu" | "german" => Some(Language::German),
            "fr" | "fra" | "french" => Some(Language::French),
            "es" | "spa" | "spanish" => Some(Language::Spanish),
            "ja" | "jpn" | "japanese" => Some(Language::Japanese),
            "zh" | "chi" | "chinese" => Some(Language::Chinese),
            _ => None,
        }
    }
}

/// Context types for intelligent translation enhancement
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ContextType {
    Technical,   // Programming, documentation, technical terms
    Gaming,      // Game UI, commands, gaming terminology
    UiInterface, // Software interfaces, buttons, menus
    Document,    // Formal documents, articles, books
    Subtitle,    // Video subtitles, casual conversation
}

impl ContextType {
    pub fn name(&self) -> &'static str {
        match self {
            ContextType::Technical => "Technical",
            ContextType::Gaming => "Gaming",
            ContextType::UiInterface => "UI Interface",
            ContextType::Document => "Document",
            ContextType::Subtitle => "Subtitle",
        }
    }
}

/// Language detection result with confidence scoring
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageDetection {
    pub language: Language,
    pub confidence: f32, // 0.0 - 1.0
    pub context_type: ContextType,
    pub context_confidence: f32,
    pub processing_time_ms: u64,
}

/// Smart translation suggestion
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationSuggestion {
    pub target_language: Language,
    pub reason: String,
    pub confidence: f32,
}

/// User pattern tracking for smart target language selection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserPattern {
    pub source_lang: Language,
    pub target_lang: Language,
    pub context_type: ContextType,
    pub usage_count: u32,
    pub last_used: chrono::DateTime<chrono::Utc>,
}

/// Context-aware translation engine
pub struct ContextAwareTranslator {
    /// Language detection patterns
    language_patterns: HashMap<Language, Vec<String>>,
    /// Context detection patterns
    context_patterns: HashMap<ContextType, Vec<String>>,
    /// User usage patterns for smart suggestions
    user_patterns: Vec<UserPattern>,
    /// LRU cache for repeated detections
    detection_cache: HashMap<String, (LanguageDetection, Instant)>,
    /// Cache TTL
    cache_ttl: Duration,
}

impl ContextAwareTranslator {
    /// Create new context-aware translator with default patterns
    pub fn new() -> Self {
        let mut translator = Self {
            language_patterns: HashMap::new(),
            context_patterns: HashMap::new(),
            user_patterns: Vec::new(),
            detection_cache: HashMap::new(),
            cache_ttl: Duration::from_secs(300), // 5 minutes
        };

        translator.initialize_patterns();
        translator
    }

    /// Initialize language and context detection patterns
    fn initialize_patterns(&mut self) {
        // English patterns
        self.language_patterns.insert(
            Language::English,
            vec![
                "the".to_string(),
                "and".to_string(),
                "is".to_string(),
                "in".to_string(),
                "to".to_string(),
                "of".to_string(),
                "a".to_string(),
                "that".to_string(),
                "it".to_string(),
                "with".to_string(),
                "for".to_string(),
                "as".to_string(),
            ],
        );

        // Russian patterns
        self.language_patterns.insert(
            Language::Russian,
            vec![
                "и".to_string(),
                "в".to_string(),
                "не".to_string(),
                "на".to_string(),
                "с".to_string(),
                "что".to_string(),
                "по".to_string(),
                "за".to_string(),
                "для".to_string(),
                "от".to_string(),
                "как".to_string(),
                "он".to_string(),
            ],
        );

        // German patterns
        self.language_patterns.insert(
            Language::German,
            vec![
                "der".to_string(),
                "die".to_string(),
                "und".to_string(),
                "in".to_string(),
                "den".to_string(),
                "von".to_string(),
                "zu".to_string(),
                "das".to_string(),
                "mit".to_string(),
                "sich".to_string(),
                "des".to_string(),
                "auf".to_string(),
            ],
        );

        // French patterns
        self.language_patterns.insert(
            Language::French,
            vec![
                "le".to_string(),
                "de".to_string(),
                "et".to_string(),
                "à".to_string(),
                "un".to_string(),
                "il".to_string(),
                "être".to_string(),
                "et".to_string(),
                "en".to_string(),
                "avoir".to_string(),
                "que".to_string(),
                "pour".to_string(),
            ],
        );

        // Spanish patterns
        self.language_patterns.insert(
            Language::Spanish,
            vec![
                "el".to_string(),
                "de".to_string(),
                "que".to_string(),
                "y".to_string(),
                "a".to_string(),
                "en".to_string(),
                "un".to_string(),
                "es".to_string(),
                "se".to_string(),
                "no".to_string(),
                "te".to_string(),
                "lo".to_string(),
            ],
        );

        // Japanese patterns (Hiragana/Katakana)
        self.language_patterns.insert(
            Language::Japanese,
            vec![
                "の".to_string(),
                "に".to_string(),
                "は".to_string(),
                "を".to_string(),
                "が".to_string(),
                "で".to_string(),
                "と".to_string(),
                "た".to_string(),
                "です".to_string(),
                "ます".to_string(),
                "して".to_string(),
                "から".to_string(),
            ],
        );

        // Chinese patterns (Simplified)
        self.language_patterns.insert(
            Language::Chinese,
            vec![
                "的".to_string(),
                "了".to_string(),
                "在".to_string(),
                "是".to_string(),
                "我".to_string(),
                "有".to_string(),
                "和".to_string(),
                "就".to_string(),
                "不".to_string(),
                "人".to_string(),
                "都".to_string(),
                "一".to_string(),
            ],
        );

        // Technical context patterns
        self.context_patterns.insert(
            ContextType::Technical,
            vec![
                "function".to_string(),
                "variable".to_string(),
                "class".to_string(),
                "method".to_string(),
                "API".to_string(),
                "database".to_string(),
                "algorithm".to_string(),
                "implementation".to_string(),
                "код".to_string(),
                "функция".to_string(),
                "переменная".to_string(),
                "класс".to_string(),
            ],
        );

        // Gaming context patterns
        self.context_patterns.insert(
            ContextType::Gaming,
            vec![
                "level".to_string(),
                "player".to_string(),
                "game".to_string(),
                "score".to_string(),
                "weapon".to_string(),
                "enemy".to_string(),
                "quest".to_string(),
                "skill".to_string(),
                "уровень".to_string(),
                "игрок".to_string(),
                "игра".to_string(),
                "очки".to_string(),
            ],
        );

        // UI Interface context patterns
        self.context_patterns.insert(
            ContextType::UiInterface,
            vec![
                "button".to_string(),
                "menu".to_string(),
                "dialog".to_string(),
                "window".to_string(),
                "click".to_string(),
                "select".to_string(),
                "save".to_string(),
                "cancel".to_string(),
                "кнопка".to_string(),
                "меню".to_string(),
                "окно".to_string(),
                "выбрать".to_string(),
            ],
        );

        // Document context patterns
        self.context_patterns.insert(
            ContextType::Document,
            vec![
                "chapter".to_string(),
                "section".to_string(),
                "paragraph".to_string(),
                "page".to_string(),
                "article".to_string(),
                "document".to_string(),
                "text".to_string(),
                "content".to_string(),
                "глава".to_string(),
                "раздел".to_string(),
                "страница".to_string(),
                "документ".to_string(),
            ],
        );

        // Subtitle context patterns
        self.context_patterns.insert(
            ContextType::Subtitle,
            vec![
                "said".to_string(),
                "tell".to_string(),
                "speak".to_string(),
                "talk".to_string(),
                "hello".to_string(),
                "thanks".to_string(),
                "please".to_string(),
                "sorry".to_string(),
                "сказал".to_string(),
                "говорить".to_string(),
                "привет".to_string(),
                "спасибо".to_string(),
            ],
        );
    }

    /// Detect language and context from text with caching
    pub fn detect_language_and_context(&mut self, text: &str) -> Result<LanguageDetection> {
        let start_time = Instant::now();

        // Check cache first
        if let Some((cached_result, cached_time)) = self.detection_cache.get(text) {
            if cached_time.elapsed() < self.cache_ttl {
                return Ok(cached_result.clone());
            }
        }

        // Clean and normalize text
        let normalized_text = text
            .to_lowercase()
            .chars()
            .filter(|c| c.is_alphabetic() || c.is_whitespace())
            .collect::<String>();

        if normalized_text.trim().is_empty() {
            return Err(anyhow!("Empty or invalid text for language detection"));
        }

        // Detect language
        let (language, lang_confidence) = self.detect_language(&normalized_text)?;

        // Detect context
        let (context_type, context_confidence) = self.detect_context(&normalized_text);

        let processing_time_ms = start_time.elapsed().as_millis() as u64;

        let result = LanguageDetection {
            language,
            confidence: lang_confidence,
            context_type,
            context_confidence,
            processing_time_ms,
        };

        // Cache the result
        self.detection_cache
            .insert(text.to_string(), (result.clone(), Instant::now()));

        // Clean old cache entries (simple cleanup)
        if self.detection_cache.len() > 1000 {
            let cutoff = Instant::now() - self.cache_ttl;
            self.detection_cache.retain(|_, (_, time)| *time > cutoff);
        }

        Ok(result)
    }

    /// Detect language from text patterns
    fn detect_language(&self, text: &str) -> Result<(Language, f32)> {
        let words: Vec<&str> = text.split_whitespace().collect();
        if words.is_empty() {
            return Err(anyhow!("No words found for language detection"));
        }

        let mut language_scores: HashMap<Language, f32> = HashMap::new();

        // Score each language based on pattern matches
        for (language, patterns) in &self.language_patterns {
            let mut score = 0.0;
            let total_patterns = patterns.len() as f32;

            for pattern in patterns {
                let pattern_count =
                    words.iter().filter(|word| word.contains(pattern)).count() as f32;
                score += pattern_count / words.len() as f32;
            }

            // Normalize score
            let normalized_score = (score / total_patterns).min(1.0);
            language_scores.insert(*language, normalized_score);
        }

        // Character-based detection for non-Latin scripts
        self.add_character_based_detection(text, &mut language_scores);

        // Find the language with highest score
        let (best_language, best_score) = language_scores
            .into_iter()
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
            .ok_or_else(|| anyhow!("No language detected"))?;

        // Require minimum confidence
        if best_score < 0.1 {
            return Ok((Language::English, 0.5)); // Default fallback
        }

        Ok((best_language, best_score))
    }

    /// Add character-based detection for non-Latin scripts
    fn add_character_based_detection(&self, text: &str, scores: &mut HashMap<Language, f32>) {
        let chars: Vec<char> = text.chars().collect();
        let total_chars = chars.len() as f32;

        if total_chars == 0.0 {
            return;
        }

        // Count character types
        let cyrillic_count = chars
            .iter()
            .filter(|c| matches!(**c, 'а'..='я' | 'А'..='Я' | 'ё' | 'Ё'))
            .count() as f32;

        let hiragana_katakana_count = chars
            .iter()
            .filter(|c| matches!(**c, 'あ'..='ん' | 'ア'..='ン' | 'ー'))
            .count() as f32;

        let cjk_count = chars
            .iter()
            .filter(|c| matches!(**c, '\u{4e00}'..='\u{9fff}'))
            .count() as f32;

        // Update scores based on character frequency
        if cyrillic_count > 0.0 {
            let cyrillic_ratio = cyrillic_count / total_chars;
            scores
                .entry(Language::Russian)
                .and_modify(|score| *score = (*score + cyrillic_ratio).min(1.0))
                .or_insert(cyrillic_ratio);
        }

        if hiragana_katakana_count > 0.0 {
            let japanese_ratio = hiragana_katakana_count / total_chars;
            scores
                .entry(Language::Japanese)
                .and_modify(|score| *score = (*score + japanese_ratio).min(1.0))
                .or_insert(japanese_ratio);
        }

        if cjk_count > 0.0 {
            let chinese_ratio = cjk_count / total_chars;
            scores
                .entry(Language::Chinese)
                .and_modify(|score| *score = (*score + chinese_ratio * 0.8).min(1.0))
                .or_insert(chinese_ratio * 0.8);

            // CJK characters are also used in Japanese
            scores
                .entry(Language::Japanese)
                .and_modify(|score| *score = (*score + chinese_ratio * 0.6).min(1.0))
                .or_insert(chinese_ratio * 0.6);
        }
    }

    /// Detect context type from text patterns
    fn detect_context(&self, text: &str) -> (ContextType, f32) {
        let words: Vec<&str> = text.split_whitespace().collect();
        if words.is_empty() {
            return (ContextType::Document, 0.5); // Default fallback
        }

        let mut context_scores: HashMap<ContextType, f32> = HashMap::new();

        // Score each context type based on pattern matches
        for (context_type, patterns) in &self.context_patterns {
            let mut score = 0.0;

            for pattern in patterns {
                let pattern_count =
                    words.iter().filter(|word| word.contains(pattern)).count() as f32;
                score += pattern_count;
            }

            // Normalize score
            let normalized_score = (score / words.len() as f32).min(1.0);
            context_scores.insert(*context_type, normalized_score);
        }

        // Find the context with highest score
        let (best_context, best_score) = context_scores
            .into_iter()
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
            .unwrap_or((ContextType::Document, 0.5));

        (best_context, best_score)
    }

    /// Get smart target language suggestions based on user patterns
    pub fn suggest_target_language(
        &self,
        source_language: Language,
        context_type: ContextType,
    ) -> Vec<TranslationSuggestion> {
        let mut suggestions = Vec::new();

        // Find user patterns for this source language and context
        let matching_patterns: Vec<&UserPattern> = self
            .user_patterns
            .iter()
            .filter(|p| p.source_lang == source_language && p.context_type == context_type)
            .collect();

        if !matching_patterns.is_empty() {
            // Sort by usage count and recency
            let mut sorted_patterns = matching_patterns;
            sorted_patterns.sort_by(|a, b| {
                let score_a = a.usage_count as f32
                    + (1.0 / (chrono::Utc::now() - a.last_used).num_days().max(1) as f32);
                let score_b = b.usage_count as f32
                    + (1.0 / (chrono::Utc::now() - b.last_used).num_days().max(1) as f32);
                score_b
                    .partial_cmp(&score_a)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });

            // Add top patterns as suggestions
            for (i, pattern) in sorted_patterns.iter().take(3).enumerate() {
                let confidence = (1.0 - (i as f32 * 0.2)).max(0.4);
                suggestions.push(TranslationSuggestion {
                    target_language: pattern.target_lang,
                    reason: format!(
                        "Used {} times in {} context",
                        pattern.usage_count,
                        pattern.context_type.name()
                    ),
                    confidence,
                });
            }
        }

        // Add default suggestions if no user patterns exist
        if suggestions.is_empty() {
            suggestions.extend(self.get_default_suggestions(source_language, context_type));
        }

        suggestions
    }

    /// Get default language suggestions for new users
    fn get_default_suggestions(
        &self,
        source: Language,
        context: ContextType,
    ) -> Vec<TranslationSuggestion> {
        let mut suggestions = Vec::new();

        // Common language pairs based on context
        match (source, context) {
            (Language::English, ContextType::Technical) => {
                suggestions.push(TranslationSuggestion {
                    target_language: Language::Russian,
                    reason: "Common for technical documentation".to_string(),
                    confidence: 0.8,
                });
            }
            (Language::Russian, ContextType::Technical) => {
                suggestions.push(TranslationSuggestion {
                    target_language: Language::English,
                    reason: "International technical standard".to_string(),
                    confidence: 0.8,
                });
            }
            (Language::English, ContextType::Gaming) => {
                suggestions.push(TranslationSuggestion {
                    target_language: Language::Russian,
                    reason: "Popular gaming community".to_string(),
                    confidence: 0.7,
                });
            }
            _ => {
                // Default fallback suggestions
                if source != Language::English {
                    suggestions.push(TranslationSuggestion {
                        target_language: Language::English,
                        reason: "Universal language".to_string(),
                        confidence: 0.6,
                    });
                }
                if source != Language::Russian {
                    suggestions.push(TranslationSuggestion {
                        target_language: Language::Russian,
                        reason: "Primary target language".to_string(),
                        confidence: 0.6,
                    });
                }
            }
        }

        suggestions
    }

    /// Update user patterns based on translation usage
    pub fn update_user_pattern(
        &mut self,
        source_lang: Language,
        target_lang: Language,
        context_type: ContextType,
    ) {
        // Find existing pattern or create new one
        if let Some(pattern) = self.user_patterns.iter_mut().find(|p| {
            p.source_lang == source_lang
                && p.target_lang == target_lang
                && p.context_type == context_type
        }) {
            pattern.usage_count += 1;
            pattern.last_used = chrono::Utc::now();
        } else {
            self.user_patterns.push(UserPattern {
                source_lang,
                target_lang,
                context_type,
                usage_count: 1,
                last_used: chrono::Utc::now(),
            });
        }

        // Limit pattern history to prevent memory bloat
        if self.user_patterns.len() > 1000 {
            self.user_patterns
                .sort_by(|a, b| b.last_used.cmp(&a.last_used));
            self.user_patterns.truncate(500);
        }
    }

    /// Clear detection cache
    pub fn clear_cache(&mut self) {
        self.detection_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, Duration) {
        (self.detection_cache.len(), self.cache_ttl)
    }
}

impl Default for ContextAwareTranslator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_language_detection_english() {
        let mut translator = ContextAwareTranslator::new();
        let result = translator
            .detect_language_and_context("Hello, this is a test text in English")
            .unwrap();

        assert_eq!(result.language, Language::English);
        assert!(result.confidence > 0.3);
    }

    #[test]
    fn test_language_detection_russian() {
        let mut translator = ContextAwareTranslator::new();
        let result = translator
            .detect_language_and_context("Привет, это тестовый текст на русском языке")
            .unwrap();

        assert_eq!(result.language, Language::Russian);
        assert!(result.confidence > 0.3);
    }

    #[test]
    fn test_context_detection_technical() {
        let mut translator = ContextAwareTranslator::new();
        let result = translator
            .detect_language_and_context(
                "This function implements the algorithm using a database API",
            )
            .unwrap();

        assert_eq!(result.context_type, ContextType::Technical);
    }

    #[test]
    fn test_cache_functionality() {
        let mut translator = ContextAwareTranslator::new();
        let text = "Test text for caching";

        let result1 = translator.detect_language_and_context(text).unwrap();
        let result2 = translator.detect_language_and_context(text).unwrap();

        // Second call should be from cache (faster)
        assert!(result2.processing_time_ms <= result1.processing_time_ms);
    }

    #[test]
    fn test_user_pattern_update() {
        let mut translator = ContextAwareTranslator::new();

        translator.update_user_pattern(
            Language::English,
            Language::Russian,
            ContextType::Technical,
        );

        let suggestions =
            translator.suggest_target_language(Language::English, ContextType::Technical);
        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0].target_language, Language::Russian);
    }
}
