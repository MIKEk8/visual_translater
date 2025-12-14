/*!
Smart Text Region Detection

Advanced text region detection using hybrid ML algorithms for enhanced OCR accuracy.
Combines multiple detection methods for optimal text region identification.

Methods:
- Contour-based detection
- Edge detection
- Text-specific detection
- ML-based region classification
- Confidence scoring and region merging
*/

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Text region detection method
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DetectionMethod {
    Contour,         // Contour-based detection
    Edge,            // Edge detection algorithm
    TextSpecific,    // Text-specific pattern detection
    MachineLearning, // ML-based region classification
    Hybrid,          // Combination of multiple methods
}

impl DetectionMethod {
    pub fn name(&self) -> &'static str {
        match self {
            DetectionMethod::Contour => "Contour",
            DetectionMethod::Edge => "Edge",
            DetectionMethod::TextSpecific => "Text-Specific",
            DetectionMethod::MachineLearning => "Machine Learning",
            DetectionMethod::Hybrid => "Hybrid",
        }
    }
}

/// Detected text region with confidence
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextRegion {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
    pub confidence: f32, // 0.0 - 1.0
    pub method: DetectionMethod,
    pub text_likelihood: f32, // Probability this region contains text
    pub rotation_angle: f32,  // Detected text rotation in degrees
}

impl TextRegion {
    /// Check if two regions overlap significantly
    pub fn overlaps_with(&self, other: &TextRegion, threshold: f32) -> bool {
        let x_overlap = (self.x.max(other.x) as i32
            - (self.x + self.width).min(other.x + other.width) as i32)
            .abs() as f32;
        let y_overlap = (self.y.max(other.y) as i32
            - (self.y + self.height).min(other.y + other.height) as i32)
            .abs() as f32;

        let overlap_area = x_overlap * y_overlap;
        let self_area = (self.width * self.height) as f32;
        let other_area = (other.width * other.height) as f32;
        let min_area = self_area.min(other_area);

        overlap_area / min_area > threshold
    }

    /// Get region area
    pub fn area(&self) -> u32 {
        self.width * self.height
    }

    /// Get region center point
    pub fn center(&self) -> (u32, u32) {
        (self.x + self.width / 2, self.y + self.height / 2)
    }
}

/// Smart region detection result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionResult {
    pub regions: Vec<TextRegion>,
    pub method_used: DetectionMethod,
    pub processing_time_ms: u64,
    pub total_regions_found: usize,
    pub merged_regions: usize,
    pub confidence_threshold: f32,
}

/// Configuration for smart detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionConfig {
    pub min_region_width: u32,
    pub min_region_height: u32,
    pub max_region_width: u32,
    pub max_region_height: u32,
    pub confidence_threshold: f32,
    pub overlap_threshold: f32,
    pub enable_rotation_detection: bool,
    pub enable_ml_classification: bool,
    pub cache_results: bool,
}

impl Default for DetectionConfig {
    fn default() -> Self {
        Self {
            min_region_width: 10,
            min_region_height: 8,
            max_region_width: 2000,
            max_region_height: 1000,
            confidence_threshold: 0.3,
            overlap_threshold: 0.5,
            enable_rotation_detection: true,
            enable_ml_classification: false, // Disabled until ML model is implemented
            cache_results: true,
        }
    }
}

/// Smart text area detector
pub struct SmartAreaDetector {
    config: DetectionConfig,
    /// Cache for repeated detections
    detection_cache: HashMap<Vec<u8>, (DetectionResult, Instant)>,
    /// Cache TTL
    cache_ttl: Duration,
    /// Performance metrics
    performance_stats: HashMap<DetectionMethod, (u64, u32)>, // (total_time_ms, call_count)
}

impl SmartAreaDetector {
    /// Create new smart area detector
    pub fn new(config: DetectionConfig) -> Self {
        Self {
            config,
            detection_cache: HashMap::new(),
            cache_ttl: Duration::from_secs(60), // 1 minute cache
            performance_stats: HashMap::new(),
        }
    }

    /// Detect text regions in image data using hybrid approach
    pub fn detect_text_regions(&mut self, image_data: &[u8]) -> Result<DetectionResult> {
        let start_time = Instant::now();

        // Check cache first
        if self.config.cache_results {
            if let Some((cached_result, cached_time)) = self.detection_cache.get(image_data) {
                if cached_time.elapsed() < self.cache_ttl {
                    return Ok(cached_result.clone());
                }
            }
        }

        // Use hybrid detection for best results
        let result = self.hybrid_detection(image_data)?;

        // Cache the result
        if self.config.cache_results {
            self.detection_cache
                .insert(image_data.to_vec(), (result.clone(), Instant::now()));
            self.cleanup_cache();
        }

        // Update performance stats
        let total_time = start_time.elapsed().as_millis() as u64;
        let (time, count) = self
            .performance_stats
            .entry(result.method_used)
            .or_insert((0, 0));
        *time += total_time;
        *count += 1;

        Ok(result)
    }

    /// Hybrid detection combining multiple methods
    fn hybrid_detection(&self, image_data: &[u8]) -> Result<DetectionResult> {
        let start_time = Instant::now();

        // Step 1: Try contour-based detection first (fastest)
        let mut all_regions = self.contour_detection(image_data)?;

        // Step 2: Add edge-based detection for missed regions
        let edge_regions = self.edge_detection(image_data)?;
        all_regions.extend(edge_regions);

        // Step 3: Add text-specific detection for fine-grained regions
        let text_regions = self.text_specific_detection(image_data)?;
        all_regions.extend(text_regions);

        // Step 4: ML-based classification (if enabled)
        if self.config.enable_ml_classification {
            let ml_regions = self.ml_detection(image_data)?;
            all_regions.extend(ml_regions);
        }

        // Step 5: Filter by confidence threshold
        all_regions.retain(|region| region.confidence >= self.config.confidence_threshold);

        // Step 6: Filter by size constraints
        all_regions.retain(|region| {
            region.width >= self.config.min_region_width
                && region.height >= self.config.min_region_height
                && region.width <= self.config.max_region_width
                && region.height <= self.config.max_region_height
        });

        // Step 7: Merge overlapping regions
        let total_regions = all_regions.len();
        let merged_regions = self.merge_overlapping_regions(&mut all_regions);

        // Step 8: Sort by confidence (best first)
        all_regions.sort_by(|a, b| {
            b.confidence
                .partial_cmp(&a.confidence)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let processing_time_ms = start_time.elapsed().as_millis() as u64;

        Ok(DetectionResult {
            regions: all_regions,
            method_used: DetectionMethod::Hybrid,
            processing_time_ms,
            total_regions_found: total_regions,
            merged_regions,
            confidence_threshold: self.config.confidence_threshold,
        })
    }

    /// Contour-based text region detection
    fn contour_detection(&self, _image_data: &[u8]) -> Result<Vec<TextRegion>> {
        // Mock implementation - in real world this would use image processing
        // to find contours that might contain text
        let regions = vec![
            TextRegion {
                x: 100,
                y: 50,
                width: 200,
                height: 30,
                confidence: 0.7,
                method: DetectionMethod::Contour,
                text_likelihood: 0.8,
                rotation_angle: 0.0,
            },
            TextRegion {
                x: 150,
                y: 200,
                width: 180,
                height: 25,
                confidence: 0.6,
                method: DetectionMethod::Contour,
                text_likelihood: 0.7,
                rotation_angle: 2.5,
            },
        ];

        Ok(regions)
    }

    /// Edge-based text region detection
    fn edge_detection(&self, _image_data: &[u8]) -> Result<Vec<TextRegion>> {
        // Mock implementation - would use edge detection algorithms
        // like Canny edge detection to find text boundaries
        let regions = vec![TextRegion {
            x: 320,
            y: 120,
            width: 160,
            height: 28,
            confidence: 0.65,
            method: DetectionMethod::Edge,
            text_likelihood: 0.75,
            rotation_angle: 0.0,
        }];

        Ok(regions)
    }

    /// Text-specific pattern detection
    fn text_specific_detection(&self, _image_data: &[u8]) -> Result<Vec<TextRegion>> {
        // Mock implementation - would use text-specific patterns
        // like character recognition, line detection, etc.
        let regions = vec![TextRegion {
            x: 80,
            y: 300,
            width: 240,
            height: 35,
            confidence: 0.8,
            method: DetectionMethod::TextSpecific,
            text_likelihood: 0.9,
            rotation_angle: -1.2,
        }];

        Ok(regions)
    }

    /// Machine learning-based region classification
    fn ml_detection(&self, _image_data: &[u8]) -> Result<Vec<TextRegion>> {
        // Mock implementation - would use trained ML model
        // for text region classification
        let mut regions = Vec::new();

        if self.config.enable_ml_classification {
            regions.push(TextRegion {
                x: 400,
                y: 400,
                width: 300,
                height: 40,
                confidence: 0.85,
                method: DetectionMethod::MachineLearning,
                text_likelihood: 0.95,
                rotation_angle: 0.0,
            });
        }

        Ok(regions)
    }

    /// Merge overlapping regions to reduce duplicates
    fn merge_overlapping_regions(&self, regions: &mut Vec<TextRegion>) -> usize {
        let original_count = regions.len();
        let mut merged = Vec::new();
        let mut used = vec![false; regions.len()];

        for i in 0..regions.len() {
            if used[i] {
                continue;
            }

            let mut base_region = regions[i].clone();
            used[i] = true;
            let mut merged_count = 1;
            let mut total_confidence = base_region.confidence;

            // Find overlapping regions
            for j in (i + 1)..regions.len() {
                if used[j] {
                    continue;
                }

                if base_region.overlaps_with(&regions[j], self.config.overlap_threshold) {
                    // Merge regions by expanding bounding box
                    let min_x = base_region.x.min(regions[j].x);
                    let min_y = base_region.y.min(regions[j].y);
                    let max_x =
                        (base_region.x + base_region.width).max(regions[j].x + regions[j].width);
                    let max_y =
                        (base_region.y + base_region.height).max(regions[j].y + regions[j].height);

                    base_region.x = min_x;
                    base_region.y = min_y;
                    base_region.width = max_x - min_x;
                    base_region.height = max_y - min_y;

                    // Average confidence and text likelihood
                    total_confidence += regions[j].confidence;
                    merged_count += 1;
                    base_region.text_likelihood =
                        (base_region.text_likelihood + regions[j].text_likelihood) / 2.0;

                    // Use highest confidence method
                    if regions[j].confidence > base_region.confidence {
                        base_region.method = regions[j].method;
                    }

                    used[j] = true;
                }
            }

            // Update average confidence
            base_region.confidence = total_confidence / merged_count as f32;
            merged.push(base_region);
        }

        *regions = merged;
        original_count - regions.len()
    }

    /// Detect rotation angle for a specific region
    pub fn detect_rotation(&self, _image_data: &[u8], _region: &TextRegion) -> Result<f32> {
        // Mock implementation - would analyze text line angles
        // using Hough transform or similar techniques
        Ok(0.0) // No rotation detected in mock
    }

    /// Get optimal OCR preprocessing suggestions for detected regions
    pub fn get_preprocessing_suggestions(&self, regions: &[TextRegion]) -> Vec<String> {
        let mut suggestions = Vec::new();

        for region in regions {
            // Suggest preprocessing based on region characteristics
            if region.confidence < 0.5 {
                suggestions.push(format!(
                    "Low confidence region at ({}, {}): Try image enhancement",
                    region.x, region.y
                ));
            }

            if region.rotation_angle.abs() > 2.0 {
                suggestions.push(format!(
                    "Rotated text at ({}, {}): Apply {:.1}° rotation correction",
                    region.x, region.y, -region.rotation_angle
                ));
            }

            if region.width < 50 || region.height < 15 {
                suggestions.push(format!(
                    "Small text region at ({}, {}): Try image upscaling",
                    region.x, region.y
                ));
            }

            if region.text_likelihood < 0.6 {
                suggestions.push(format!(
                    "Uncertain text region at ({}, {}): Manual verification recommended",
                    region.x, region.y
                ));
            }
        }

        suggestions
    }

    /// Clean up old cache entries
    fn cleanup_cache(&mut self) {
        if self.detection_cache.len() > 100 {
            let cutoff = Instant::now() - self.cache_ttl;
            self.detection_cache.retain(|_, (_, time)| *time > cutoff);
        }
    }

    /// Get performance statistics
    pub fn get_performance_stats(&self) -> HashMap<DetectionMethod, (f64, u32)> {
        self.performance_stats
            .iter()
            .map(|(method, (total_time, count))| {
                let avg_time = if *count > 0 {
                    *total_time as f64 / *count as f64
                } else {
                    0.0
                };
                (*method, (avg_time, *count))
            })
            .collect()
    }

    /// Clear all caches and reset stats
    pub fn clear_cache(&mut self) {
        self.detection_cache.clear();
        self.performance_stats.clear();
    }

    /// Update detection configuration
    pub fn update_config(&mut self, config: DetectionConfig) {
        self.config = config;
        // Clear cache when config changes
        if !self.config.cache_results {
            self.detection_cache.clear();
        }
    }
}

impl Default for SmartAreaDetector {
    fn default() -> Self {
        Self::new(DetectionConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_region_overlap_detection() {
        let region1 = TextRegion {
            x: 100,
            y: 100,
            width: 200,
            height: 50,
            confidence: 0.8,
            method: DetectionMethod::Contour,
            text_likelihood: 0.9,
            rotation_angle: 0.0,
        };

        let region2 = TextRegion {
            x: 150,
            y: 120,
            width: 150,
            height: 40,
            confidence: 0.7,
            method: DetectionMethod::Edge,
            text_likelihood: 0.8,
            rotation_angle: 0.0,
        };

        assert!(region1.overlaps_with(&region2, 0.3));
    }

    #[test]
    fn test_hybrid_detection() {
        let mut detector = SmartAreaDetector::default();
        let mock_image = vec![0u8; 1000]; // Mock image data

        let result = detector.detect_text_regions(&mock_image).unwrap();

        assert_eq!(result.method_used, DetectionMethod::Hybrid);
        assert!(!result.regions.is_empty());
        assert!(result.processing_time_ms > 0);
    }

    #[test]
    fn test_region_filtering() {
        let mut detector = SmartAreaDetector::default();
        detector.config.min_region_width = 100;
        detector.config.confidence_threshold = 0.7;

        let mock_image = vec![0u8; 1000];
        let result = detector.detect_text_regions(&mock_image).unwrap();

        // All returned regions should meet the criteria
        for region in &result.regions {
            assert!(region.width >= 100);
            assert!(region.confidence >= 0.7);
        }
    }

    #[test]
    fn test_cache_functionality() {
        let mut detector = SmartAreaDetector::default();
        let mock_image = vec![0u8; 500];

        let result1 = detector.detect_text_regions(&mock_image).unwrap();
        let result2 = detector.detect_text_regions(&mock_image).unwrap();

        // Second call should be from cache (same result, potentially faster)
        assert_eq!(result1.regions.len(), result2.regions.len());
    }

    #[test]
    fn test_performance_stats() {
        let mut detector = SmartAreaDetector::default();
        let mock_image = vec![0u8; 500];

        detector.detect_text_regions(&mock_image).unwrap();
        let stats = detector.get_performance_stats();

        assert!(stats.contains_key(&DetectionMethod::Hybrid));
        assert!(stats[&DetectionMethod::Hybrid].1 > 0); // Call count > 0
    }
}
