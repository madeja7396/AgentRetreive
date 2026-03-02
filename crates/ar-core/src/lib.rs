//! Core primitives for AgentRetrieve Rust engine.

pub mod bm25;
pub mod index;
pub mod symbol;
pub mod tokenizer;
pub mod wal;

pub use index::{IndexStats, InvertedIndex, SearchHit, SearchQuery, DEFAULT_PATTERN_CSV};
pub use symbol::SymbolSpan;

/// Workspace-level semver for the Rust engine surface.
pub const ENGINE_VERSION: &str = "0.1.0";

/// Returns a stable health string used by thin integration checks.
pub fn healthcheck() -> &'static str {
    "ok"
}
