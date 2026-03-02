//! Inverted index with FST term dictionary and BM25 scoring.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use fst::{Map, MapBuilder};
use globset::{Glob, GlobSet, GlobSetBuilder};
use memmap2::MmapOptions;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use walkdir::WalkDir;

use crate::bm25;
use crate::symbol::{extract_symbols, SymbolSpan};
use crate::tokenizer::tokenize;

pub const DEFAULT_PATTERN_CSV: &str = "*.py,*.pyi,*.js,*.jsx,*.mjs,*.cjs,*.ts,*.tsx,*.mts,*.cts,*.rs,*.go,*.cs,*.php,*.rb,*.kt,*.kts,*.swift,*.dart,*.hs,*.lhs,*.ex,*.exs,*.c,*.h,*.cpp,*.cc,*.cxx,*.hpp,*.java,*.md";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Posting {
    pub doc_id: u32,
    pub tf: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentMeta {
    pub id: u32,
    pub path: String,
    pub lang: Option<String>,
    pub length: u32,
    #[serde(default = "default_line_count")]
    pub line_count: u32,
    pub content_hash: String,
    pub symbols: Vec<SymbolSpan>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PersistedIndex {
    version: u32,
    docs: Vec<DocumentMeta>,
    postings: BTreeMap<String, Vec<Posting>>,
    total_terms: u64,
    avg_doc_len: f64,
    fst_bytes: Vec<u8>,
}

#[derive(Debug)]
pub struct InvertedIndex {
    docs: Vec<DocumentMeta>,
    postings: BTreeMap<String, Vec<Posting>>,
    total_terms: u64,
    avg_doc_len: f64,
    fst_bytes: Vec<u8>,
    term_fst: Map<Vec<u8>>,
    pub k1: f64,
    pub b: f64,
}

#[derive(Debug, Clone)]
pub struct SearchQuery {
    pub must: Vec<String>,
    pub should: Vec<String>,
    pub not_terms: Vec<String>,
    pub symbol: Vec<String>,
    pub max_results: usize,
    pub min_match: usize,
}

impl Default for SearchQuery {
    fn default() -> Self {
        Self {
            must: Vec::new(),
            should: Vec::new(),
            not_terms: Vec::new(),
            symbol: Vec::new(),
            max_results: 10,
            min_match: 0,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct SearchHit {
    pub doc_id: u32,
    pub path: String,
    pub score: f64,
    pub matched_symbols: Vec<String>,
    pub digest: String,
    pub bounds: LineBounds,
}

#[derive(Debug, Clone, Serialize)]
pub struct LineBounds {
    pub start: u32,
    pub end: u32,
}

#[derive(Debug, Clone, Serialize)]
pub struct IndexStats {
    pub total_docs: usize,
    pub unique_terms: usize,
    pub total_terms: u64,
    pub avg_doc_len: f64,
}

impl InvertedIndex {
    pub fn build_from_dir(root: &Path, pattern_csv: &str) -> Result<Self> {
        let files = collect_files(root, pattern_csv)?;
        Self::build_from_files(root, files)
    }

    pub fn build_from_files(root: &Path, files: Vec<PathBuf>) -> Result<Self> {
        let mut docs: Vec<DocumentMeta> = Vec::new();
        let mut postings: BTreeMap<String, Vec<Posting>> = BTreeMap::new();
        let mut total_terms: u64 = 0;

        for (doc_idx, path) in files.iter().enumerate() {
            let bytes = fs::read(path)
                .with_context(|| format!("failed to read source file: {}", path.display()))?;
            let content = String::from_utf8_lossy(&bytes).to_string();

            let rel = path
                .strip_prefix(root)
                .with_context(|| format!("failed to relativize path: {}", path.display()))?
                .to_string_lossy()
                .replace('\\', "/");

            let tokens = tokenize(&content);
            let mut tf_map: HashMap<String, u32> = HashMap::new();
            for token in tokens {
                *tf_map.entry(token).or_insert(0) += 1;
            }

            let doc_id = doc_idx as u32;
            let doc_len: u32 = tf_map.values().copied().sum();
            let line_count: u32 = (content.bytes().filter(|b| *b == b'\n').count() as u32) + 1;
            total_terms += doc_len as u64;

            for (term, tf) in tf_map {
                postings
                    .entry(term)
                    .or_default()
                    .push(Posting { doc_id, tf });
            }

            let mut hasher = Sha256::new();
            hasher.update(&bytes);
            let digest = format!("{:x}", hasher.finalize());

            let lang = detect_lang(path.extension().and_then(|e| e.to_str()));
            let symbols = extract_symbols(lang.as_deref(), &content);

            docs.push(DocumentMeta {
                id: doc_id,
                path: rel,
                lang,
                length: doc_len,
                line_count,
                content_hash: digest,
                symbols,
            });
        }

        for entries in postings.values_mut() {
            entries.sort_by_key(|p| p.doc_id);
        }

        let avg_doc_len = if docs.is_empty() {
            0.0
        } else {
            total_terms as f64 / docs.len() as f64
        };

        let (fst_bytes, term_fst) = build_fst(&postings)?;

        Ok(Self {
            docs,
            postings,
            total_terms,
            avg_doc_len,
            fst_bytes,
            term_fst,
            k1: 0.8,
            b: 0.3,
        })
    }

    pub fn save(&self, output_path: &Path) -> Result<()> {
        let persisted = PersistedIndex {
            version: 1,
            docs: self.docs.clone(),
            postings: self.postings.clone(),
            total_terms: self.total_terms,
            avg_doc_len: self.avg_doc_len,
            fst_bytes: self.fst_bytes.clone(),
        };

        let payload = bincode::serialize(&persisted).context("failed to serialize index")?;
        if let Some(parent) = output_path.parent() {
            fs::create_dir_all(parent).with_context(|| {
                format!("failed to create index directory: {}", parent.display())
            })?;
        }
        fs::write(output_path, payload)
            .with_context(|| format!("failed to write index: {}", output_path.display()))?;
        Ok(())
    }

    pub fn load(index_path: &Path) -> Result<Self> {
        let file = fs::File::open(index_path)
            .with_context(|| format!("failed to open index: {}", index_path.display()))?;
        // SAFETY: read-only mapping of an immutable index artifact.
        let mmap = unsafe { MmapOptions::new().map(&file) }
            .with_context(|| format!("failed to mmap index: {}", index_path.display()))?;
        let persisted: PersistedIndex =
            bincode::deserialize(&mmap).context("failed to deserialize index")?;
        let term_fst = Map::new(persisted.fst_bytes.clone()).context("failed to load fst map")?;

        Ok(Self {
            docs: persisted.docs,
            postings: persisted.postings,
            total_terms: persisted.total_terms,
            avg_doc_len: persisted.avg_doc_len,
            fst_bytes: persisted.fst_bytes,
            term_fst,
            k1: 0.8,
            b: 0.3,
        })
    }

    pub fn stats(&self) -> IndexStats {
        IndexStats {
            total_docs: self.docs.len(),
            unique_terms: self.postings.len(),
            total_terms: self.total_terms,
            avg_doc_len: self.avg_doc_len,
        }
    }

    pub fn documents(&self) -> &[DocumentMeta] {
        &self.docs
    }

    pub fn search(&self, query: &SearchQuery) -> Vec<SearchHit> {
        let must = normalize_terms(&query.must);
        let should = normalize_terms(&query.should);
        let not_terms = normalize_terms(&query.not_terms);
        let symbol_terms = normalize_terms(&query.symbol);

        let mut candidate_docs: BTreeSet<u32> = BTreeSet::new();
        for term in must.iter().chain(should.iter()) {
            if let Some(postings) = self.postings_for_term(term) {
                for posting in postings {
                    candidate_docs.insert(posting.doc_id);
                }
            }
        }
        if candidate_docs.is_empty() {
            for doc in &self.docs {
                candidate_docs.insert(doc.id);
            }
        }

        let mut excluded: HashSet<u32> = HashSet::new();
        for term in &not_terms {
            if let Some(postings) = self.postings_for_term(term) {
                for posting in postings {
                    excluded.insert(posting.doc_id);
                }
            }
        }

        let mut hits: Vec<SearchHit> = Vec::new();
        let mut scored_terms: Vec<String> = must.clone();
        for term in &should {
            if !scored_terms.contains(term) {
                scored_terms.push(term.clone());
            }
        }

        for doc_id in candidate_docs {
            if excluded.contains(&doc_id) {
                continue;
            }

            let doc = match self.docs.get(doc_id as usize) {
                Some(d) => d,
                None => continue,
            };

            if must.iter().any(|term| self.term_tf(term, doc_id) == 0) {
                continue;
            }

            let should_matches = should
                .iter()
                .filter(|term| self.term_tf(term, doc_id) > 0)
                .count();
            if !should.is_empty() && should_matches < query.min_match {
                continue;
            }

            let mut matched_symbols: Vec<String> = Vec::new();
            if !symbol_terms.is_empty() {
                let symbol_set: HashSet<String> =
                    doc.symbols.iter().map(|s| s.name.to_lowercase()).collect();
                for term in &symbol_terms {
                    if symbol_set.contains(term) {
                        matched_symbols.push(term.clone());
                    }
                }
                if matched_symbols.is_empty() {
                    continue;
                }
            }

            let mut score = 0.0;
            for term in &scored_terms {
                let tf = self.term_tf(term, doc_id);
                if tf == 0 {
                    continue;
                }
                let df = self.postings_for_term(term).map_or(0usize, |v| v.len());
                score += bm25::score(
                    tf,
                    doc.length as f64,
                    self.avg_doc_len,
                    df,
                    self.docs.len(),
                    self.k1,
                    self.b,
                );
            }
            if !matched_symbols.is_empty() {
                score += matched_symbols.len() as f64 * 2.0;
            }

            hits.push(SearchHit {
                doc_id,
                path: doc.path.clone(),
                score,
                matched_symbols,
                digest: doc.content_hash.clone(),
                bounds: LineBounds {
                    start: 1,
                    end: doc.line_count.max(1),
                },
            });
        }

        hits.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.doc_id.cmp(&b.doc_id))
        });

        let max_results = if query.max_results == 0 {
            10
        } else {
            query.max_results
        };
        hits.truncate(max_results);
        hits
    }

    fn postings_for_term(&self, term: &str) -> Option<&Vec<Posting>> {
        if self.term_fst.get(term).is_none() {
            return None;
        }
        self.postings.get(term)
    }

    fn term_tf(&self, term: &str, doc_id: u32) -> u32 {
        let Some(postings) = self.postings_for_term(term) else {
            return 0;
        };

        match postings.binary_search_by_key(&doc_id, |p| p.doc_id) {
            Ok(i) => postings[i].tf,
            Err(_) => 0,
        }
    }
}

fn normalize_terms(terms: &[String]) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for raw in terms {
        let normalized = raw.trim().to_lowercase();
        if normalized.is_empty() || out.contains(&normalized) {
            continue;
        }
        out.push(normalized);
    }
    out
}

fn default_line_count() -> u32 {
    1
}

fn build_fst(postings: &BTreeMap<String, Vec<Posting>>) -> Result<(Vec<u8>, Map<Vec<u8>>)> {
    let mut builder = MapBuilder::memory();
    for (ord, term) in postings.keys().enumerate() {
        builder
            .insert(term, ord as u64)
            .with_context(|| format!("failed to insert term into fst: {term}"))?;
    }
    let fst_bytes = builder.into_inner().context("failed to finalize fst")?;
    let term_fst = Map::new(fst_bytes.clone()).context("failed to construct fst map")?;
    Ok((fst_bytes, term_fst))
}

fn collect_files(root: &Path, pattern_csv: &str) -> Result<Vec<PathBuf>> {
    let globset = build_globset(pattern_csv)?;
    let mut out: Vec<PathBuf> = Vec::new();

    for entry in WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if !entry.file_type().is_file() {
            continue;
        }
        let rel = match path.strip_prefix(root) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let rel_normalized = rel.to_string_lossy().replace('\\', "/");
        if globset.is_match(&rel_normalized) {
            out.push(path.to_path_buf());
        }
    }

    out.sort_by(|a, b| {
        let a_rel = a.strip_prefix(root).unwrap_or(a).to_string_lossy();
        let b_rel = b.strip_prefix(root).unwrap_or(b).to_string_lossy();
        a_rel.cmp(&b_rel)
    });
    Ok(out)
}

fn build_globset(pattern_csv: &str) -> Result<GlobSet> {
    let mut builder = GlobSetBuilder::new();
    for pattern in pattern_csv
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
    {
        builder.add(Glob::new(pattern).with_context(|| format!("invalid glob: {pattern}"))?);
    }
    builder.build().context("failed to build globset")
}

fn detect_lang(ext: Option<&str>) -> Option<String> {
    let ext = ext.map(|e| format!(".{}", e.to_lowercase()))?;
    let lang = match ext.as_str() {
        ".py" | ".pyi" => "python",
        ".js" | ".jsx" | ".mjs" | ".cjs" => "javascript",
        ".ts" | ".tsx" | ".mts" | ".cts" => "typescript",
        ".rs" => "rust",
        ".go" => "go",
        ".cs" => "csharp",
        ".php" => "php",
        ".rb" => "ruby",
        ".kt" | ".kts" => "kotlin",
        ".swift" => "swift",
        ".dart" => "dart",
        ".hs" | ".lhs" => "haskell",
        ".ex" | ".exs" => "elixir",
        ".c" | ".h" => "c",
        ".cpp" | ".cc" | ".cxx" | ".hpp" => "cpp",
        ".java" => "java",
        ".md" => "markdown",
        _ => return None,
    };
    Some(lang.to_string())
}

#[cfg(test)]
mod tests {
    use super::{InvertedIndex, SearchQuery, DEFAULT_PATTERN_CSV};
    use std::fs;

    #[test]
    fn builds_and_queries_index() {
        let temp = tempfile::tempdir().expect("tempdir");
        let root = temp.path();
        fs::write(root.join("a.py"), "def handle_request():\n    token = 1\n").expect("write a");
        fs::write(root.join("b.py"), "def parse_token():\n    return True\n").expect("write b");

        let idx = InvertedIndex::build_from_dir(root, DEFAULT_PATTERN_CSV).expect("build index");
        let query = SearchQuery {
            must: vec!["token".to_string()],
            should: vec![],
            not_terms: vec![],
            symbol: vec![],
            max_results: 5,
            min_match: 0,
        };
        let hits = idx.search(&query);
        assert!(!hits.is_empty());
    }
}
