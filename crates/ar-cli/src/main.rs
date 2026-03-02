use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use ar_core::wal::{WalEntry, WalManager};
use ar_core::{
    healthcheck, InvertedIndex, SearchHit, SearchQuery, DEFAULT_PATTERN_CSV, ENGINE_VERSION,
};
use clap::{Args, Parser, Subcommand};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

#[derive(Parser, Debug)]
#[command(name = env!("CARGO_BIN_NAME"), about = "AgentRetrieve Rust CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    Ix {
        #[command(subcommand)]
        command: IxCommands,
    },
    Q(QueryArgs),
}

#[derive(Subcommand, Debug)]
enum IxCommands {
    Build(IxBuildArgs),
    Update(IxUpdateArgs),
}

#[derive(Args, Debug)]
struct IxBuildArgs {
    #[arg(long)]
    dir: PathBuf,
    #[arg(short, long)]
    output: PathBuf,
    #[arg(long, default_value = DEFAULT_PATTERN_CSV)]
    pattern: String,
}

#[derive(Args, Debug)]
struct IxUpdateArgs {
    #[arg(long)]
    index: PathBuf,
    #[arg(long)]
    dir: PathBuf,
    #[arg(short, long)]
    output: Option<PathBuf>,
    #[arg(long, default_value = DEFAULT_PATTERN_CSV)]
    pattern: String,
    #[arg(long)]
    wal: Option<PathBuf>,
    #[arg(long)]
    snapshot_dir: Option<PathBuf>,
    #[arg(long, default_value_t = 1000)]
    compact_threshold: u64,
    #[arg(long, default_value_t = false)]
    compact_now: bool,
}

#[derive(Args, Debug)]
struct QueryArgs {
    #[arg(long)]
    index: PathBuf,
    #[arg(long, default_value = "")]
    must: String,
    #[arg(long, default_value = "")]
    should: String,
    #[arg(long = "not", default_value = "")]
    not_terms: String,
    #[arg(long, default_value = "")]
    symbol: String,
    #[arg(long)]
    json: Option<PathBuf>,
    #[arg(long, default_value_t = 10)]
    max_results: usize,
    #[arg(long, default_value_t = 0)]
    min_match: usize,
    #[arg(long, default_value_t = 10)]
    max_hits: usize,
    #[arg(long, default_value_t = 8192)]
    max_bytes: usize,
    #[arg(long, default_value_t = 256)]
    max_excerpt: usize,
    #[arg(long, default_value_t = 0.8)]
    k1: f64,
    #[arg(long, default_value_t = 0.3)]
    b: f64,
}

#[derive(Debug, Deserialize, Default)]
struct DslV2Budget {
    #[serde(default)]
    max_results: Option<usize>,
    #[serde(default)]
    max_hits: Option<usize>,
    #[serde(default)]
    max_bytes: Option<usize>,
    #[serde(default)]
    max_excerpt: Option<usize>,
}

#[derive(Debug, Deserialize, Default)]
struct DslV2Query {
    #[serde(default)]
    v: Option<String>,
    #[serde(default)]
    must: Vec<String>,
    #[serde(default)]
    should: Vec<String>,
    #[serde(default, rename = "not")]
    not_terms: Vec<String>,
    #[serde(default)]
    near: Vec<serde_json::Value>,
    #[serde(default)]
    symbol: Vec<String>,
    #[serde(default)]
    min_match: Option<usize>,
    #[serde(default)]
    budget: Option<DslV2Budget>,
}

#[derive(Debug, Clone)]
struct QueryRuntimeConfig {
    must: Vec<String>,
    should: Vec<String>,
    not_terms: Vec<String>,
    symbol: Vec<String>,
    min_match: usize,
    max_results: usize,
    max_hits: usize,
    max_bytes: usize,
    max_excerpt: usize,
    k1: f64,
    b: f64,
}

#[derive(Debug, Serialize)]
struct QueryOutputV3 {
    v: &'static str,
    ok: bool,
    cap: Capability,
    r: Vec<ResultEntryV3>,
    t: bool,
    cur: Option<String>,
    lim: Limits,
}

#[derive(Debug, Serialize)]
struct Capability {
    epoch: String,
    index_hash: String,
    engine: &'static str,
    engine_version: &'static str,
    health: &'static str,
}

#[derive(Debug, Serialize)]
struct Limits {
    max_bytes: usize,
    emitted_bytes: usize,
    max_results: usize,
    max_hits: usize,
}

#[derive(Debug, Serialize)]
struct ResultEntryV3 {
    id: String,
    s: i32,
    h: Vec<HitEntryV3>,
    rng: [u32; 2],
    proof: ProofV3,
    next: Vec<String>,
    path: String,
}

#[derive(Debug, Serialize)]
struct HitEntryV3 {
    ln: u32,
    txt: String,
    sc: i32,
}

#[derive(Debug, Serialize)]
struct ProofV3 {
    digest: String,
    bounds: [u32; 2],
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Ix { command } => match command {
            IxCommands::Build(args) => cmd_ix_build(args),
            IxCommands::Update(args) => cmd_ix_update(args),
        },
        Commands::Q(args) => cmd_query(args),
    }
}

fn cmd_ix_build(args: IxBuildArgs) -> Result<()> {
    let idx = InvertedIndex::build_from_dir(&args.dir, &args.pattern)?;
    idx.save(&args.output)?;
    let stats = idx.stats();
    println!(
        "index_saved={} docs={} terms={} total_tokens={} avg_doc_len={:.2} engine={} status={}",
        args.output.display(),
        stats.total_docs,
        stats.unique_terms,
        stats.total_terms,
        stats.avg_doc_len,
        ENGINE_VERSION,
        healthcheck(),
    );
    Ok(())
}

fn cmd_ix_update(args: IxUpdateArgs) -> Result<()> {
    let old_idx = InvertedIndex::load(&args.index)
        .with_context(|| format!("failed to load existing index: {}", args.index.display()))?;
    let new_idx = InvertedIndex::build_from_dir(&args.dir, &args.pattern)?;

    let output_path = args.output.unwrap_or_else(|| args.index.clone());
    let tmp_path = output_path.with_extension("tmp");
    new_idx.save(&tmp_path)?;
    fs::rename(&tmp_path, &output_path).with_context(|| {
        format!(
            "failed to atomically replace index {}",
            output_path.display()
        )
    })?;

    let wal_path = args
        .wal
        .unwrap_or_else(|| output_path.with_extension("wal"));
    let snapshot_dir = args.snapshot_dir.unwrap_or_else(|| {
        let base = output_path
            .file_name()
            .map(|v| v.to_string_lossy().into_owned())
            .unwrap_or_else(|| "index".to_string());
        output_path
            .parent()
            .unwrap_or(Path::new("."))
            .join(format!("{base}.snapshots"))
    });

    let mut wal = WalManager::new_with_threshold(&wal_path, &snapshot_dir, args.compact_threshold)?;
    let mut appended = 0u64;

    let old_docs: HashMap<&str, _> = old_idx
        .documents()
        .iter()
        .map(|doc| (doc.path.as_str(), doc))
        .collect();
    let new_docs: HashMap<&str, _> = new_idx
        .documents()
        .iter()
        .map(|doc| (doc.path.as_str(), doc))
        .collect();

    for (path, new_doc) in &new_docs {
        match old_docs.get(path) {
            Some(old_doc) if old_doc.content_hash == new_doc.content_hash => {}
            _ => {
                wal.append(&WalEntry::Upsert {
                    doc_id: new_doc.id,
                    path: (*path).to_string(),
                    content_hash: new_doc.content_hash.clone(),
                    tokens: Vec::new(),
                })?;
                appended += 1;
            }
        }
    }

    for (path, old_doc) in &old_docs {
        if !new_docs.contains_key(path) {
            wal.append(&WalEntry::Delete { doc_id: old_doc.id })?;
            appended += 1;
        }
    }

    wal.create_snapshot_marker()?;
    let compacted = if args.compact_now || wal.should_compact() {
        let snapshot = wal.compact()?;
        Some(snapshot)
    } else {
        None
    };

    let old_stats = old_idx.stats();
    let new_stats = new_idx.stats();
    println!(
        "index_updated={} docs={} terms={} total_tokens={} avg_doc_len={:.2} delta_docs={} wal_entries={} wal={}{}",
        output_path.display(),
        new_stats.total_docs,
        new_stats.unique_terms,
        new_stats.total_terms,
        new_stats.avg_doc_len,
        new_stats.total_docs as isize - old_stats.total_docs as isize,
        appended,
        wal_path.display(),
        compacted
            .as_ref()
            .map(|p| format!(" compacted_snapshot={}", p.display()))
            .unwrap_or_default(),
    );
    Ok(())
}

fn cmd_query(args: QueryArgs) -> Result<()> {
    let mut idx = InvertedIndex::load(&args.index)
        .with_context(|| format!("failed to load index: {}", args.index.display()))?;
    let runtime = load_query_runtime(&args)?;
    idx.k1 = runtime.k1;
    idx.b = runtime.b;

    let query = SearchQuery {
        must: runtime.must.clone(),
        should: runtime.should.clone(),
        not_terms: runtime.not_terms.clone(),
        symbol: runtime.symbol.clone(),
        max_results: runtime.max_results,
        min_match: runtime.min_match,
    };

    let hits = idx.search(&query);
    let mut entries = hits_to_entries(hits, runtime.max_hits, runtime.max_excerpt);

    if entries.len() > runtime.max_results {
        entries.truncate(runtime.max_results);
    }

    let index_hash = sha256_hex_file(&args.index)?;
    let mut payload = QueryOutputV3 {
        v: "result.v3",
        ok: true,
        cap: Capability {
            epoch: index_hash.chars().take(8).collect(),
            index_hash: format!("sha256:{index_hash}"),
            engine: "rust",
            engine_version: ENGINE_VERSION,
            health: healthcheck(),
        },
        r: Vec::new(),
        t: false,
        cur: None,
        lim: Limits {
            max_bytes: runtime.max_bytes,
            emitted_bytes: 0,
            max_results: runtime.max_results,
            max_hits: runtime.max_hits,
        },
    };

    apply_budget_enforcer(&mut payload, entries, runtime.max_bytes)?;
    let rendered = serde_json::to_string_pretty(&payload)?;
    println!("{rendered}");
    Ok(())
}

fn load_query_runtime(args: &QueryArgs) -> Result<QueryRuntimeConfig> {
    let mut cfg = QueryRuntimeConfig {
        must: parse_csv(&args.must),
        should: parse_csv(&args.should),
        not_terms: parse_csv(&args.not_terms),
        symbol: parse_csv(&args.symbol),
        min_match: args.min_match,
        max_results: args.max_results,
        max_hits: args.max_hits,
        max_bytes: args.max_bytes,
        max_excerpt: args.max_excerpt,
        k1: args.k1,
        b: args.b,
    };

    if let Some(json_path) = &args.json {
        let raw = fs::read_to_string(json_path)
            .with_context(|| format!("failed to read query json: {}", json_path.display()))?;
        let q: DslV2Query = serde_json::from_str(&raw)
            .with_context(|| format!("failed to parse query json: {}", json_path.display()))?;

        if let Some(v) = q.v.as_deref() {
            if v != "query.v2" {
                anyhow::bail!("unsupported query version: {v}");
            }
        }

        cfg.must = q.must;
        cfg.should = q.should;
        cfg.not_terms = q.not_terms;
        cfg.symbol = q.symbol;
        cfg.min_match = q.min_match.unwrap_or(cfg.min_match);

        if let Some(budget) = q.budget {
            if let Some(v) = budget.max_results {
                cfg.max_results = v;
            }
            if let Some(v) = budget.max_hits {
                cfg.max_hits = v;
            }
            if let Some(v) = budget.max_bytes {
                cfg.max_bytes = v;
            }
            if let Some(v) = budget.max_excerpt {
                cfg.max_excerpt = v;
            }
        }

        // v2 keeps near clause in contract; current rust core ignores it in scoring for now.
        let _ = q.near;
    }

    if cfg.max_results == 0 {
        cfg.max_results = 1;
    }
    if cfg.max_hits == 0 {
        cfg.max_hits = 1;
    }
    if cfg.max_bytes < 256 {
        cfg.max_bytes = 256;
    }
    if cfg.max_excerpt == 0 {
        cfg.max_excerpt = 64;
    }

    Ok(cfg)
}

fn parse_csv(raw: &str) -> Vec<String> {
    raw.split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(ToString::to_string)
        .collect()
}

fn hits_to_entries(
    hits: Vec<SearchHit>,
    max_hits: usize,
    max_excerpt: usize,
) -> Vec<ResultEntryV3> {
    hits.into_iter()
        .map(|h| {
            let score = normalize_score(h.score);
            let mut hit_entries = Vec::with_capacity(max_hits.max(1));
            let symbol_text = if h.matched_symbols.is_empty() {
                String::from("lexical")
            } else {
                format!("symbol:{}", h.matched_symbols.join("|"))
            };
            hit_entries.push(HitEntryV3 {
                ln: h.bounds.start,
                txt: truncate_excerpt(&format!("{} [{symbol_text}]", h.path), max_excerpt),
                sc: score,
            });

            ResultEntryV3 {
                id: format!("d{}_s1", h.doc_id),
                s: score,
                h: hit_entries,
                rng: [h.bounds.start, h.bounds.end],
                proof: ProofV3 {
                    digest: format!("sha256:{}", h.digest),
                    bounds: [h.bounds.start, h.bounds.end],
                },
                next: Vec::new(),
                path: h.path,
            }
        })
        .collect()
}

fn normalize_score(raw: f64) -> i32 {
    let scaled = (raw * 100.0).round() as i32;
    scaled.clamp(0, 1000)
}

fn truncate_excerpt(s: &str, max_excerpt: usize) -> String {
    let mut chars = s.chars();
    let mut out = String::new();
    for _ in 0..max_excerpt {
        if let Some(ch) = chars.next() {
            out.push(ch);
        } else {
            return out;
        }
    }
    if chars.next().is_some() {
        out.push('…');
    }
    out
}

fn apply_budget_enforcer(
    payload: &mut QueryOutputV3,
    entries: Vec<ResultEntryV3>,
    max_bytes: usize,
) -> Result<()> {
    payload.r.clear();
    payload.t = false;

    for entry in entries {
        payload.r.push(entry);
        let probe_bytes = serde_json::to_vec(payload)?;
        if probe_bytes.len() <= max_bytes {
            payload.lim.emitted_bytes = probe_bytes.len();
            continue;
        }

        payload.r.pop();
        payload.t = true;
        break;
    }

    let final_bytes = serde_json::to_vec(payload)?;
    payload.lim.emitted_bytes = final_bytes.len();
    if payload.lim.emitted_bytes > max_bytes {
        payload.t = true;
    }
    Ok(())
}

fn sha256_hex_file(path: &Path) -> Result<String> {
    let bytes =
        fs::read(path).with_context(|| format!("failed to read file: {}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!("{:x}", hasher.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ix_update_matches_full_rebuild_fingerprint() {
        let temp = tempfile::tempdir().expect("tempdir");
        let source_dir = temp.path().join("src");
        fs::create_dir_all(&source_dir).expect("create source");
        fs::write(source_dir.join("a.rs"), "fn main() { println!(\"a\"); }\n").expect("write a");

        let index_path = temp.path().join("repo.index.bin");
        let initial = InvertedIndex::build_from_dir(&source_dir, DEFAULT_PATTERN_CSV).expect("build initial");
        initial.save(&index_path).expect("save initial");

        fs::write(
            source_dir.join("a.rs"),
            "fn main() { println!(\"b\"); }\nfn helper() { println!(\"x\"); }\n",
        )
        .expect("rewrite a");

        let args = IxUpdateArgs {
            index: index_path.clone(),
            dir: source_dir.clone(),
            output: None,
            pattern: DEFAULT_PATTERN_CSV.to_string(),
            wal: Some(temp.path().join("repo.index.wal")),
            snapshot_dir: Some(temp.path().join("repo.index.snapshots")),
            compact_threshold: 10_000,
            compact_now: false,
        };
        cmd_ix_update(args).expect("ix update");

        let updated = InvertedIndex::load(&index_path).expect("load updated");
        let rebuilt = InvertedIndex::build_from_dir(&source_dir, DEFAULT_PATTERN_CSV).expect("build rebuilt");
        assert_eq!(
            updated.deterministic_fingerprint(),
            rebuilt.deterministic_fingerprint()
        );
    }
}
