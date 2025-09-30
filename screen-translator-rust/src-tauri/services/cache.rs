/*!
Translation History & Cache Service

High-performance caching system with:
- LRU cache with TTL for translation results
- Persistent history storage with search capabilities
- Performance metrics and statistics
- Export functionality for translation history
*/

use anyhow::{anyhow, Result};
use lru::LruCache;
use serde::{Deserialize, Serialize};
use std::num::NonZeroUsize;
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime};

/// Translation entry for history and cache
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationEntry {
    pub id: String, // Unique identifier
    pub original_text: String,
    pub translated_text: String,
    pub source_language: String,
    pub target_language: String,
    pub confidence: f32,
    pub translation_service: String, // "google", "deepl", "openai", etc.
    pub context_type: Option<String>, // AI-detected context
    pub source_type: String,         // "selected_text", "clipboard", "screenshot", etc.
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub processing_time_ms: u64,
    pub coordinates: Option<(u32, u32, u32, u32)>, // For screenshot translations
    pub tags: Vec<String>,                         // User-defined tags
    pub favorite: bool,                            // User-marked favorites
    pub usage_count: u32,                          // How many times this translation was accessed
}

/// Search filters for translation history
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HistorySearchFilter {
    pub text_query: Option<String>,
    pub source_language: Option<String>,
    pub target_language: Option<String>,
    pub context_type: Option<String>,
    pub source_type: Option<String>,
    pub date_from: Option<chrono::DateTime<chrono::Utc>>,
    pub date_to: Option<chrono::DateTime<chrono::Utc>>,
    pub tags: Vec<String>,
    pub favorites_only: bool,
    pub min_confidence: Option<f32>,
}

/// Pagination parameters for history queries
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginationParams {
    pub page: usize,
    pub per_page: usize,
    pub sort_by: String, // "timestamp", "confidence", "usage_count", "text_length"
    pub sort_order: String, // "asc", "desc"
}

impl Default for PaginationParams {
    fn default() -> Self {
        Self {
            page: 1,
            per_page: 50,
            sort_by: "timestamp".to_string(),
            sort_order: "desc".to_string(),
        }
    }
}

/// Search results for translation history
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistorySearchResult {
    pub entries: Vec<TranslationEntry>,
    pub total_count: usize,
    pub page: usize,
    pub per_page: usize,
    pub total_pages: usize,
    pub search_time_ms: u64,
}

/// Cache statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub cache_size: usize,
    pub cache_capacity: usize,
    pub hit_count: u64,
    pub miss_count: u64,
    pub hit_rate: f64,
    pub history_size: usize,
    pub oldest_entry: Option<chrono::DateTime<chrono::Utc>>,
    pub newest_entry: Option<chrono::DateTime<chrono::Utc>>,
    pub total_translations: u64,
}

/// Cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub cache_capacity: usize,       // LRU cache size
    pub cache_ttl_hours: u64,        // Cache TTL in hours
    pub history_max_entries: usize,  // Maximum history entries
    pub auto_cleanup_enabled: bool,  // Automatic cleanup of old entries
    pub cleanup_interval_hours: u64, // Cleanup interval
    pub export_format: String,       // "json", "csv", "txt"
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            cache_capacity: 1000,
            cache_ttl_hours: 24,
            history_max_entries: 10000,
            auto_cleanup_enabled: true,
            cleanup_interval_hours: 168, // 1 week
            export_format: "json".to_string(),
        }
    }
}

/// Cached translation item
#[derive(Debug, Clone)]
struct CachedItem {
    entry: TranslationEntry,
    expires_at: SystemTime,
}

/// Translation cache and history manager
pub struct TranslationCacheService {
    /// LRU cache for fast lookups
    cache: Arc<Mutex<LruCache<String, CachedItem>>>,
    /// Persistent history storage
    history: Arc<Mutex<Vec<TranslationEntry>>>,
    /// Configuration
    config: CacheConfig,
    /// Performance statistics
    stats: Arc<Mutex<CacheStats>>,
    /// Cache key generation strategy
    key_strategy: CacheKeyStrategy,
}

/// Strategy for generating cache keys
#[derive(Debug, Clone, Copy)]
#[allow(clippy::enum_variant_names)]
pub enum CacheKeyStrategy {
    TextOnly,             // Hash of original text only
    TextAndLanguages,     // Hash of text + source + target languages
    TextLanguagesContext, // Hash of text + languages + context type
}

impl TranslationCacheService {
    /// Create new translation cache service
    pub fn new(config: CacheConfig) -> Result<Self> {
        let cache_capacity = NonZeroUsize::new(config.cache_capacity)
            .ok_or_else(|| anyhow!("Cache capacity must be greater than 0"))?;

        Ok(Self {
            cache: Arc::new(Mutex::new(LruCache::new(cache_capacity))),
            history: Arc::new(Mutex::new(Vec::new())),
            config,
            stats: Arc::new(Mutex::new(CacheStats {
                cache_size: 0,
                cache_capacity: cache_capacity.get(),
                hit_count: 0,
                miss_count: 0,
                hit_rate: 0.0,
                history_size: 0,
                oldest_entry: None,
                newest_entry: None,
                total_translations: 0,
            })),
            key_strategy: CacheKeyStrategy::TextAndLanguages,
        })
    }

    /// Set cache key generation strategy
    pub fn set_key_strategy(&mut self, strategy: CacheKeyStrategy) {
        self.key_strategy = strategy;
    }

    /// Generate cache key based on strategy
    fn generate_cache_key(&self, entry: &TranslationEntry) -> String {
        match self.key_strategy {
            CacheKeyStrategy::TextOnly => {
                format!("{:x}", md5::compute(&entry.original_text))
            }
            CacheKeyStrategy::TextAndLanguages => {
                let key_data = format!(
                    "{}|{}|{}",
                    entry.original_text, entry.source_language, entry.target_language
                );
                format!("{:x}", md5::compute(key_data))
            }
            CacheKeyStrategy::TextLanguagesContext => {
                let context = entry.context_type.as_deref().unwrap_or("none");
                let key_data = format!(
                    "{}|{}|{}|{}",
                    entry.original_text, entry.source_language, entry.target_language, context
                );
                format!("{:x}", md5::compute(key_data))
            }
        }
    }

    /// Check if item is expired
    fn is_expired(&self, item: &CachedItem) -> bool {
        SystemTime::now() > item.expires_at
    }

    /// Get translation from cache
    pub fn get_cached_translation(
        &self,
        text: &str,
        source_lang: &str,
        target_lang: &str,
    ) -> Option<TranslationEntry> {
        let temp_entry = TranslationEntry {
            id: String::new(),
            original_text: text.to_string(),
            translated_text: String::new(),
            source_language: source_lang.to_string(),
            target_language: target_lang.to_string(),
            confidence: 0.0,
            translation_service: String::new(),
            context_type: None,
            source_type: String::new(),
            timestamp: chrono::Utc::now(),
            processing_time_ms: 0,
            coordinates: None,
            tags: Vec::new(),
            favorite: false,
            usage_count: 0,
        };

        let key = self.generate_cache_key(&temp_entry);

        if let Ok(mut cache) = self.cache.lock() {
            if let Some(cached_item) = cache.get(&key) {
                if !self.is_expired(cached_item) {
                    // Cache hit
                    let mut entry = cached_item.entry.clone();
                    entry.usage_count += 1;

                    // Update stats
                    if let Ok(mut stats) = self.stats.lock() {
                        stats.hit_count += 1;
                        stats.hit_rate =
                            stats.hit_count as f64 / (stats.hit_count + stats.miss_count) as f64;
                    }

                    return Some(entry);
                } else {
                    // Item expired, remove it
                    cache.pop(&key);
                }
            }
        }

        // Cache miss
        if let Ok(mut stats) = self.stats.lock() {
            stats.miss_count += 1;
            stats.hit_rate = stats.hit_count as f64 / (stats.hit_count + stats.miss_count) as f64;
        }

        None
    }

    /// Add translation to cache and history
    pub fn add_translation(&self, mut entry: TranslationEntry) -> Result<()> {
        // Generate unique ID if not provided
        if entry.id.is_empty() {
            entry.id = uuid::Uuid::new_v4().to_string();
        }

        let key = self.generate_cache_key(&entry);

        // Calculate expiration time
        let expires_at =
            SystemTime::now() + Duration::from_secs(self.config.cache_ttl_hours * 3600);

        // Add to cache
        if let Ok(mut cache) = self.cache.lock() {
            cache.put(
                key,
                CachedItem {
                    entry: entry.clone(),
                    expires_at,
                },
            );
        }

        // Add to history
        if let Ok(mut history) = self.history.lock() {
            history.push(entry.clone());

            // Enforce history size limit
            if history.len() > self.config.history_max_entries {
                // Remove oldest entries (keep most recent)
                history.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
                history.truncate(self.config.history_max_entries);
            }
        }

        // Update statistics
        self.update_stats()?;

        log::debug!("Added translation to cache and history: {}", entry.id);
        Ok(())
    }

    /// Search translation history
    pub fn search_history(
        &self,
        filter: &HistorySearchFilter,
        pagination: &PaginationParams,
    ) -> Result<HistorySearchResult> {
        let search_start = std::time::Instant::now();

        let history = self
            .history
            .lock()
            .map_err(|e| anyhow!("Failed to lock history: {}", e))?;

        // Apply filters
        let mut filtered_entries: Vec<&TranslationEntry> = history
            .iter()
            .filter(|entry| self.matches_filter(entry, filter))
            .collect();

        // Sort results
        self.sort_entries(
            &mut filtered_entries,
            &pagination.sort_by,
            &pagination.sort_order,
        );

        // Calculate pagination
        let total_count = filtered_entries.len();
        let total_pages = total_count.div_ceil(pagination.per_page);
        let start_index = (pagination.page - 1) * pagination.per_page;
        let end_index = std::cmp::min(start_index + pagination.per_page, total_count);

        // Get page results
        let page_entries = if start_index < total_count {
            filtered_entries[start_index..end_index]
                .iter()
                .map(|&entry| entry.clone())
                .collect()
        } else {
            Vec::new()
        };

        let search_time_ms = search_start.elapsed().as_millis() as u64;

        Ok(HistorySearchResult {
            entries: page_entries,
            total_count,
            page: pagination.page,
            per_page: pagination.per_page,
            total_pages,
            search_time_ms,
        })
    }

    /// Check if entry matches filter
    fn matches_filter(&self, entry: &TranslationEntry, filter: &HistorySearchFilter) -> bool {
        // Text query
        if let Some(ref query) = filter.text_query {
            let query_lower = query.to_lowercase();
            if !entry.original_text.to_lowercase().contains(&query_lower)
                && !entry.translated_text.to_lowercase().contains(&query_lower)
            {
                return false;
            }
        }

        // Language filters
        if let Some(ref source_lang) = filter.source_language {
            if entry.source_language != *source_lang {
                return false;
            }
        }

        if let Some(ref target_lang) = filter.target_language {
            if entry.target_language != *target_lang {
                return false;
            }
        }

        // Context type
        if let Some(ref context) = filter.context_type {
            if entry.context_type.as_ref() != Some(context) {
                return false;
            }
        }

        // Source type
        if let Some(ref source_type) = filter.source_type {
            if entry.source_type != *source_type {
                return false;
            }
        }

        // Date range
        if let Some(date_from) = filter.date_from {
            if entry.timestamp < date_from {
                return false;
            }
        }

        if let Some(date_to) = filter.date_to {
            if entry.timestamp > date_to {
                return false;
            }
        }

        // Tags
        if !filter.tags.is_empty() && !filter.tags.iter().any(|tag| entry.tags.contains(tag)) {
            return false;
        }

        // Favorites
        if filter.favorites_only && !entry.favorite {
            return false;
        }

        // Confidence
        if let Some(min_confidence) = filter.min_confidence {
            if entry.confidence < min_confidence {
                return false;
            }
        }

        true
    }

    /// Sort entries based on criteria
    fn sort_entries(&self, entries: &mut Vec<&TranslationEntry>, sort_by: &str, sort_order: &str) {
        let ascending = sort_order == "asc";

        entries.sort_by(|a, b| {
            let ordering = match sort_by {
                "timestamp" => a.timestamp.cmp(&b.timestamp),
                "confidence" => a
                    .confidence
                    .partial_cmp(&b.confidence)
                    .unwrap_or(std::cmp::Ordering::Equal),
                "usage_count" => a.usage_count.cmp(&b.usage_count),
                "text_length" => a.original_text.len().cmp(&b.original_text.len()),
                _ => a.timestamp.cmp(&b.timestamp), // Default to timestamp
            };

            if ascending {
                ordering
            } else {
                ordering.reverse()
            }
        });
    }

    /// Update entry tags
    pub fn update_entry_tags(&self, entry_id: &str, tags: Vec<String>) -> Result<()> {
        if let Ok(mut history) = self.history.lock() {
            if let Some(entry) = history.iter_mut().find(|e| e.id == entry_id) {
                entry.tags = tags;
                log::debug!("Updated tags for entry: {}", entry_id);
                return Ok(());
            }
        }
        Err(anyhow!("Entry not found: {}", entry_id))
    }

    /// Toggle favorite status
    pub fn toggle_favorite(&self, entry_id: &str) -> Result<bool> {
        if let Ok(mut history) = self.history.lock() {
            if let Some(entry) = history.iter_mut().find(|e| e.id == entry_id) {
                entry.favorite = !entry.favorite;
                log::debug!(
                    "Toggled favorite for entry: {} -> {}",
                    entry_id,
                    entry.favorite
                );
                return Ok(entry.favorite);
            }
        }
        Err(anyhow!("Entry not found: {}", entry_id))
    }

    /// Delete entry from history
    pub fn delete_entry(&self, entry_id: &str) -> Result<()> {
        if let Ok(mut history) = self.history.lock() {
            if let Some(index) = history.iter().position(|e| e.id == entry_id) {
                history.remove(index);
                log::info!("Deleted entry from history: {}", entry_id);
                return Ok(());
            }
        }
        Err(anyhow!("Entry not found: {}", entry_id))
    }

    /// Clear all history (keeping favorites optionally)
    pub fn clear_history(&self, keep_favorites: bool) -> Result<()> {
        if let Ok(mut history) = self.history.lock() {
            if keep_favorites {
                history.retain(|entry| entry.favorite);
                log::info!("Cleared non-favorite entries from history");
            } else {
                history.clear();
                log::info!("Cleared all entries from history");
            }
        }

        // Also clear cache
        if let Ok(mut cache) = self.cache.lock() {
            cache.clear();
        }

        self.update_stats()?;
        Ok(())
    }

    /// Export history to various formats
    pub fn export_history(
        &self,
        filter: Option<&HistorySearchFilter>,
        format: &str,
    ) -> Result<String> {
        let default_filter = HistorySearchFilter::default();
        let filter = filter.unwrap_or(&default_filter);
        let pagination = PaginationParams {
            page: 1,
            per_page: usize::MAX, // Get all results
            ..Default::default()
        };

        let results = self.search_history(filter, &pagination)?;

        match format.to_lowercase().as_str() {
            "json" => serde_json::to_string_pretty(&results.entries)
                .map_err(|e| anyhow!("JSON export failed: {}", e)),
            "csv" => self.export_to_csv(&results.entries),
            "txt" => self.export_to_txt(&results.entries),
            _ => Err(anyhow!("Unsupported export format: {}", format)),
        }
    }

    /// Export to CSV format
    fn export_to_csv(&self, entries: &[TranslationEntry]) -> Result<String> {
        let mut csv = String::new();

        // Header
        csv.push_str("ID,Original Text,Translated Text,Source Language,Target Language,Confidence,Service,Context,Source Type,Timestamp,Processing Time (ms),Tags,Favorite,Usage Count\n");

        // Data rows
        for entry in entries {
            csv.push_str(&format!(
                "\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",{},{},\"{}\",\"{}\",\"{}\",{},\"{}\",{},{}\n",
                entry.id.replace("\"", "\"\""),
                entry.original_text.replace("\"", "\"\""),
                entry.translated_text.replace("\"", "\"\""),
                entry.source_language,
                entry.target_language,
                entry.confidence,
                entry.translation_service,
                entry.context_type.as_deref().unwrap_or(""),
                entry.source_type,
                entry.timestamp.format("%Y-%m-%d %H:%M:%S UTC"),
                entry.processing_time_ms,
                entry.tags.join("; "),
                entry.favorite,
                entry.usage_count
            ));
        }

        Ok(csv)
    }

    /// Export to TXT format
    fn export_to_txt(&self, entries: &[TranslationEntry]) -> Result<String> {
        let mut txt = String::new();
        txt.push_str("Translation History Export\n");
        txt.push_str("========================\n\n");

        for (i, entry) in entries.iter().enumerate() {
            txt.push_str(&format!("Entry #{}\n", i + 1));
            txt.push_str(&format!("ID: {}\n", entry.id));
            txt.push_str(&format!("Original: {}\n", entry.original_text));
            txt.push_str(&format!("Translated: {}\n", entry.translated_text));
            txt.push_str(&format!(
                "Languages: {} → {}\n",
                entry.source_language, entry.target_language
            ));
            txt.push_str(&format!("Confidence: {:.1}%\n", entry.confidence * 100.0));
            txt.push_str(&format!("Service: {}\n", entry.translation_service));
            if let Some(ref context) = entry.context_type {
                txt.push_str(&format!("Context: {}\n", context));
            }
            txt.push_str(&format!("Source: {}\n", entry.source_type));
            txt.push_str(&format!(
                "Timestamp: {}\n",
                entry.timestamp.format("%Y-%m-%d %H:%M:%S UTC")
            ));
            txt.push_str(&format!(
                "Processing Time: {}ms\n",
                entry.processing_time_ms
            ));
            if !entry.tags.is_empty() {
                txt.push_str(&format!("Tags: {}\n", entry.tags.join(", ")));
            }
            if entry.favorite {
                txt.push_str("Favorite: Yes\n");
            }
            txt.push_str(&format!("Usage Count: {}\n", entry.usage_count));
            txt.push_str("\n---\n\n");
        }

        Ok(txt)
    }

    /// Get cache statistics
    pub fn get_stats(&self) -> Result<CacheStats> {
        self.stats
            .lock()
            .map(|stats| stats.clone())
            .map_err(|e| anyhow!("Failed to get stats: {}", e))
    }

    /// Update internal statistics
    fn update_stats(&self) -> Result<()> {
        if let (Ok(cache), Ok(history), Ok(mut stats)) =
            (self.cache.lock(), self.history.lock(), self.stats.lock())
        {
            stats.cache_size = cache.len();
            stats.history_size = history.len();
            stats.total_translations = stats.hit_count + stats.miss_count;

            // Find oldest and newest entries
            if !history.is_empty() {
                let mut sorted_history = history.clone();
                sorted_history.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
                stats.oldest_entry = Some(sorted_history.first().unwrap().timestamp);
                stats.newest_entry = Some(sorted_history.last().unwrap().timestamp);
            }
        }
        Ok(())
    }

    /// Cleanup expired cache entries
    pub fn cleanup_expired(&self) -> Result<usize> {
        let mut removed_count = 0;

        if let Ok(mut cache) = self.cache.lock() {
            let current_time = SystemTime::now();
            let keys_to_remove: Vec<String> = cache
                .iter()
                .filter_map(|(key, item)| {
                    if current_time > item.expires_at {
                        Some(key.clone())
                    } else {
                        None
                    }
                })
                .collect();

            for key in keys_to_remove {
                cache.pop(&key);
                removed_count += 1;
            }
        }

        if removed_count > 0 {
            log::debug!("Cleaned up {} expired cache entries", removed_count);
            self.update_stats()?;
        }

        Ok(removed_count)
    }

    /// Get similar translations (fuzzy matching)
    pub fn get_similar_translations(
        &self,
        text: &str,
        limit: usize,
    ) -> Result<Vec<TranslationEntry>> {
        let history = self
            .history
            .lock()
            .map_err(|e| anyhow!("Failed to lock history: {}", e))?;

        let text_lower = text.to_lowercase();
        let mut similar_entries: Vec<(TranslationEntry, f64)> = history
            .iter()
            .filter_map(|entry| {
                let similarity =
                    self.calculate_similarity(&text_lower, &entry.original_text.to_lowercase());
                if similarity > 0.5 {
                    // Threshold for similarity
                    Some((entry.clone(), similarity))
                } else {
                    None
                }
            })
            .collect();

        // Sort by similarity (highest first)
        similar_entries.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Return top results
        Ok(similar_entries
            .into_iter()
            .take(limit)
            .map(|(entry, _)| entry)
            .collect())
    }

    /// Calculate text similarity using Levenshtein distance
    fn calculate_similarity(&self, text1: &str, text2: &str) -> f64 {
        let distance = levenshtein::levenshtein(text1, text2);
        let max_len = text1.len().max(text2.len());

        if max_len == 0 {
            1.0
        } else {
            1.0 - (distance as f64 / max_len as f64)
        }
    }
}

impl Default for TranslationCacheService {
    fn default() -> Self {
        Self::new(CacheConfig::default()).unwrap()
    }
}
