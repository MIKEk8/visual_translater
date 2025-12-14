pub mod context_aware;
pub mod smart_detection;

pub use context_aware::*;
pub use smart_detection::*;

// Include test module when testing
#[cfg(test)]
pub mod tests;
