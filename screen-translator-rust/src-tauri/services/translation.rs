// Translation service with multiple providers and caching

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, SystemTime};

/// Helper function to capitalize first letter
fn capitalize_first_letter(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TranslationRequest {
    pub text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub context: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TranslationResult {
    pub original_text: String,
    pub translated_text: String,
    pub source_lang: String,
    pub target_lang: String,
    pub confidence: f32,
    pub context_type: Option<String>,
    pub provider: String,
    pub timestamp: SystemTime,
}

#[derive(Debug, Clone)]
pub struct CachedTranslation {
    pub result: TranslationResult,
    pub expiry: SystemTime,
}

#[derive(Default, Clone)]
pub struct TranslationService {
    cache: HashMap<String, CachedTranslation>,
    cache_ttl: Duration,
    default_provider: TranslationProvider,
}

#[derive(Debug, Clone, Default)]
pub enum TranslationProvider {
    Google,
    Microsoft,
    DeepL,
    Yandex,
    #[default]
    Mock, // For development/testing
}

impl TranslationService {
    pub fn new() -> Self {
        Self {
            cache: HashMap::new(),
            cache_ttl: Duration::from_secs(24 * 60 * 60), // 24 hours
            default_provider: TranslationProvider::Google,
        }
    }

    pub fn with_provider(provider: TranslationProvider) -> Self {
        Self {
            cache: HashMap::new(),
            cache_ttl: Duration::from_secs(24 * 60 * 60), // 24 hours
            default_provider: provider,
        }
    }

    pub async fn translate(
        &mut self,
        request: TranslationRequest,
    ) -> Result<TranslationResult, String> {
        // Check cache first
        let cache_key = self.generate_cache_key(&request);

        if let Some(cached) = self.cache.get(&cache_key) {
            if cached.expiry > SystemTime::now() {
                return Ok(cached.result.clone());
            } else {
                // Remove expired entry
                self.cache.remove(&cache_key);
            }
        }

        // Perform translation
        let result = self
            .translate_with_provider(&request, &self.default_provider.clone())
            .await?;

        // Cache the result
        let cached_translation = CachedTranslation {
            result: result.clone(),
            expiry: SystemTime::now() + self.cache_ttl,
        };
        self.cache.insert(cache_key, cached_translation);

        Ok(result)
    }

    async fn translate_with_provider(
        &self,
        request: &TranslationRequest,
        provider: &TranslationProvider,
    ) -> Result<TranslationResult, String> {
        match provider {
            TranslationProvider::Google => self.translate_with_google(request).await,
            TranslationProvider::Microsoft => self.translate_with_microsoft(request).await,
            TranslationProvider::DeepL => self.translate_with_deepl(request).await,
            TranslationProvider::Yandex => self.translate_with_yandex(request).await,
            TranslationProvider::Mock => self.translate_with_mock(request).await,
        }
    }

    async fn translate_with_google(
        &self,
        request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        log::info!(
            "Google Translate: {} -> {} ({})",
            request.source_lang,
            request.target_lang,
            request.text
        );

        // Try real Google Translate API first, fallback to intelligent mock
        #[cfg(feature = "network")]
        {
            match self.call_google_translate_api(request).await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    log::warn!("Google Translate API failed: {}, using intelligent mock", e);
                }
            }
        }

        // Intelligent mock translation
        let translated_text = self.intelligent_mock_translate(
            &request.text,
            &request.source_lang,
            &request.target_lang,
        );

        Ok(TranslationResult {
            original_text: request.text.clone(),
            translated_text,
            source_lang: request.source_lang.clone(),
            target_lang: request.target_lang.clone(),
            confidence: 0.85, // Lower confidence for mock
            context_type: request.context.clone(),
            provider: "Google (Mock)".to_string(),
            timestamp: SystemTime::now(),
        })
    }

    #[cfg(feature = "network")]
    async fn call_google_translate_api(
        &self,
        _request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        use reqwest;

        // Google Translate API endpoint (would need API key in production)
        let _client = reqwest::Client::new();

        // For demo purposes, we'll simulate a network call
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        // In a real implementation, this would make an actual HTTP request:
        // let response = client
        //     .post("https://translation.googleapis.com/language/translate/v2")
        //     .json(&json!({
        //         "q": request.text,
        //         "source": request.source_lang,
        //         "target": request.target_lang,
        //         "key": api_key
        //     }))
        //     .send()
        //     .await?;

        // For now, return an error to trigger fallback
        Err("API key not configured".to_string())
    }

    /// Intelligent mock translation using simple rules
    fn intelligent_mock_translate(
        &self,
        text: &str,
        source_lang: &str,
        target_lang: &str,
    ) -> String {
        // Basic translation patterns for common text
        let text_lower = text.to_lowercase();

        // Simple dictionary for demonstration
        let translations = match (source_lang, target_lang) {
            ("en", "ru") => vec![
                ("hello", "привет"),
                ("world", "мир"),
                ("text", "текст"),
                ("image", "изображение"),
                ("screen", "экран"),
                ("translate", "переводить"),
                ("detected", "обнаружен"),
                ("region", "область"),
                ("found", "найден"),
                ("area", "зона"),
                ("button", "кнопка"),
                ("menu", "меню"),
                ("file", "файл"),
                ("window", "окно"),
            ],
            ("ru", "en") => vec![
                ("привет", "hello"),
                ("мир", "world"),
                ("текст", "text"),
                ("изображение", "image"),
                ("экран", "screen"),
                ("переводить", "translate"),
                ("обнаружен", "detected"),
                ("область", "region"),
                ("найден", "found"),
                ("зона", "area"),
                ("кнопка", "button"),
                ("меню", "menu"),
                ("файл", "file"),
                ("окно", "window"),
            ],
            ("en", "de") => vec![
                ("hello", "hallo"),
                ("world", "welt"),
                ("text", "text"),
                ("image", "bild"),
                ("screen", "bildschirm"),
                ("detected", "erkannt"),
                ("region", "region"),
                ("found", "gefunden"),
            ],
            _ => vec![], // Add more language pairs as needed
        };

        // Try to translate individual words
        let mut result = text.to_string();
        for (source_word, target_word) in translations {
            if text_lower.contains(source_word) {
                result = result.replace(source_word, target_word);
                result = result.replace(&source_word.to_uppercase(), &target_word.to_uppercase());
                result = result.replace(
                    &capitalize_first_letter(source_word),
                    &capitalize_first_letter(target_word),
                );
            }
        }

        // If no translation found, add language indicator
        if result == text {
            result = format!(
                "[{}→{}] {}",
                source_lang.to_uppercase(),
                target_lang.to_uppercase(),
                text
            );
        }

        result
    }

    async fn translate_with_microsoft(
        &self,
        request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        // TODO: Implement Microsoft Translator API
        log::info!(
            "Microsoft Translate: {} -> {} ({})",
            request.source_lang,
            request.target_lang,
            request.text
        );

        Ok(TranslationResult {
            original_text: request.text.clone(),
            translated_text: format!("[MICROSOFT] {}", request.text),
            source_lang: request.source_lang.clone(),
            target_lang: request.target_lang.clone(),
            confidence: 0.88,
            context_type: request.context.clone(),
            provider: "Microsoft".to_string(),
            timestamp: SystemTime::now(),
        })
    }

    async fn translate_with_deepl(
        &self,
        request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        // TODO: Implement DeepL API
        log::info!(
            "DeepL Translate: {} -> {} ({})",
            request.source_lang,
            request.target_lang,
            request.text
        );

        Ok(TranslationResult {
            original_text: request.text.clone(),
            translated_text: format!("[DEEPL] {}", request.text),
            source_lang: request.source_lang.clone(),
            target_lang: request.target_lang.clone(),
            confidence: 0.95,
            context_type: request.context.clone(),
            provider: "DeepL".to_string(),
            timestamp: SystemTime::now(),
        })
    }

    async fn translate_with_yandex(
        &self,
        request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        // TODO: Implement Yandex Translate API
        log::info!(
            "Yandex Translate: {} -> {} ({})",
            request.source_lang,
            request.target_lang,
            request.text
        );

        Ok(TranslationResult {
            original_text: request.text.clone(),
            translated_text: format!("[YANDEX] {}", request.text),
            source_lang: request.source_lang.clone(),
            target_lang: request.target_lang.clone(),
            confidence: 0.85,
            context_type: request.context.clone(),
            provider: "Yandex".to_string(),
            timestamp: SystemTime::now(),
        })
    }

    async fn translate_with_mock(
        &self,
        request: &TranslationRequest,
    ) -> Result<TranslationResult, String> {
        // Mock translation for development
        log::info!(
            "Mock Translate: {} -> {} ({})",
            request.source_lang,
            request.target_lang,
            request.text
        );

        // Simulate translation patterns based on language pairs
        let translated_text = match (request.source_lang.as_str(), request.target_lang.as_str()) {
            ("en", "ru") => format!("Переведено: {}", request.text),
            ("ru", "en") => format!("Translated: {}", request.text),
            ("en", "de") => format!("Übersetzt: {}", request.text),
            ("de", "en") => format!("Translated: {}", request.text),
            ("en", "fr") => format!("Traduit: {}", request.text),
            ("fr", "en") => format!("Translated: {}", request.text),
            ("en", "es") => format!("Traducido: {}", request.text),
            ("es", "en") => format!("Translated: {}", request.text),
            ("en", "ja") => format!("翻訳済み: {}", request.text),
            ("ja", "en") => format!("Translated: {}", request.text),
            ("en", "zh") => format!("已翻译: {}", request.text),
            ("zh", "en") => format!("Translated: {}", request.text),
            _ => format!(
                "[{}→{}] {}",
                request.source_lang, request.target_lang, request.text
            ),
        };

        // Simulate AI context detection
        let context_type = self.detect_context(&request.text);

        Ok(TranslationResult {
            original_text: request.text.clone(),
            translated_text,
            source_lang: request.source_lang.clone(),
            target_lang: request.target_lang.clone(),
            confidence: 0.90,
            context_type: Some(context_type),
            provider: "Mock".to_string(),
            timestamp: SystemTime::now(),
        })
    }

    fn detect_context(&self, text: &str) -> String {
        // Simple context detection based on patterns
        // This mimics the AI context detection from Python version

        let text_lower = text.to_lowercase();

        if text_lower.contains("function")
            || text_lower.contains("variable")
            || text_lower.contains("class")
            || text_lower.contains("method")
        {
            "Technical".to_string()
        } else if text_lower.contains("player")
            || text_lower.contains("level")
            || text_lower.contains("score")
            || text_lower.contains("game")
        {
            "Gaming".to_string()
        } else if text_lower.contains("button")
            || text_lower.contains("menu")
            || text_lower.contains("click")
            || text_lower.contains("window")
        {
            "UI Interface".to_string()
        } else if text_lower.len() > 100 {
            "Document".to_string()
        } else if text_lower.contains("subtitle") || text_lower.contains("caption") {
            "Subtitle".to_string()
        } else {
            "General".to_string()
        }
    }

    fn generate_cache_key(&self, request: &TranslationRequest) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        request.text.hash(&mut hasher);
        request.source_lang.hash(&mut hasher);
        request.target_lang.hash(&mut hasher);

        format!("{:x}", hasher.finish())
    }

    pub fn clear_cache(&mut self) {
        self.cache.clear();
    }

    pub fn clean_expired_cache(&mut self) {
        let now = SystemTime::now();
        self.cache.retain(|_, cached| cached.expiry > now);
    }

    pub fn set_provider(&mut self, provider: TranslationProvider) {
        self.default_provider = provider;
    }

    pub fn get_cache_stats(&self) -> (usize, usize) {
        let total = self.cache.len();
        let now = SystemTime::now();
        let valid = self
            .cache
            .values()
            .filter(|cached| cached.expiry > now)
            .count();

        (valid, total)
    }
}
