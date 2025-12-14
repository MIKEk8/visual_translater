// Async wrapper for translation service to make integration tests work

use crate::services::translation::{TranslationRequest, TranslationResult, TranslationService};
use async_trait::async_trait;

#[async_trait]
pub trait AsyncTranslationService: Send + Sync {
    async fn translate(
        &mut self,
        text: &str,
        source_lang: &str,
        target_lang: &str,
    ) -> Result<TranslationResult, String>;
}

#[async_trait]
impl AsyncTranslationService for TranslationService {
    async fn translate(
        &mut self,
        text: &str,
        source_lang: &str,
        target_lang: &str,
    ) -> Result<TranslationResult, String> {
        let request = TranslationRequest {
            text: text.to_string(),
            source_lang: source_lang.to_string(),
            target_lang: target_lang.to_string(),
            context: None,
        };

        // Wrap the synchronous translate call in spawn_blocking for async compatibility
        let service_clone = self.clone();
        let result = tokio::task::spawn_blocking(move || {
            let mut service_inner = service_clone;
            tokio::runtime::Handle::current().block_on(service_inner.translate(request))
        })
        .await
        .map_err(|e| format!("Task join error: {}", e))?;

        result
    }
}
