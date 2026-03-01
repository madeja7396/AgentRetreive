use std::path::PathBuf;

use anyhow::Result;
use ar_core::{
    healthcheck, InvertedIndex, SearchHit, SearchQuery, DEFAULT_PATTERN_CSV, ENGINE_VERSION,
};
use clap::{Args, Parser, Subcommand};
use serde::Serialize;

#[derive(Parser, Debug)]
#[command(name = "ar", about = "AgentRetrieve Rust CLI")]
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
    #[arg(long, default_value_t = 10)]
    max_results: usize,
    #[arg(long, default_value_t = 0)]
    min_match: usize,
}

#[derive(Debug, Serialize)]
struct QueryOutput {
    v: &'static str,
    ok: bool,
    engine: &'static str,
    engine_version: &'static str,
    status: &'static str,
    r: Vec<QueryHit>,
}

#[derive(Debug, Serialize)]
struct QueryHit {
    doc_id: u32,
    path: String,
    score: f64,
    symbol: Vec<String>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Ix { command } => match command {
            IxCommands::Build(args) => cmd_ix_build(args),
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

fn cmd_query(args: QueryArgs) -> Result<()> {
    let idx = InvertedIndex::load(&args.index)?;
    let query = SearchQuery {
        must: parse_csv(&args.must),
        should: parse_csv(&args.should),
        not_terms: parse_csv(&args.not_terms),
        symbol: parse_csv(&args.symbol),
        max_results: args.max_results,
        min_match: args.min_match,
    };

    let hits = idx.search(&query);
    let payload = QueryOutput {
        v: "result.v3",
        ok: true,
        engine: "rust",
        engine_version: ENGINE_VERSION,
        status: healthcheck(),
        r: hits_to_output(hits),
    };

    println!("{}", serde_json::to_string_pretty(&payload)?);
    Ok(())
}

fn parse_csv(raw: &str) -> Vec<String> {
    raw.split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(ToString::to_string)
        .collect()
}

fn hits_to_output(hits: Vec<SearchHit>) -> Vec<QueryHit> {
    hits.into_iter()
        .map(|h| QueryHit {
            doc_id: h.doc_id,
            path: h.path,
            score: h.score,
            symbol: h.matched_symbols,
        })
        .collect()
}
