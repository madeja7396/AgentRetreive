#!/usr/bin/env python3
"""Generate paper figure assets from FIGURE_SOURCES.v1.json.

Usage:
    python3 scripts/papers/generate_figure_assets.py [--run-id RUN_ID] [--strict]

Examples:
    # Use specific run_id for run-dependent figures
    python3 scripts/papers/generate_figure_assets.py --run-id run_20260228_154238_exp001_raw
    
    # Fail if any input artifact is missing
    python3 scripts/papers/generate_figure_assets.py --strict
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_figure_sources() -> dict[str, Any]:
    """Load figure sources configuration."""
    config_path = (
        Path(__file__).resolve().parents[2] / "docs" / "papers" / "FIGURE_SOURCES.v1.json"
    )
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_input_artifacts(patterns: list[str], project_root: Path, run_id: str | None) -> dict[str, Path]:
    """Resolve input artifact patterns to actual files."""
    resolved: dict[str, Path] = {}
    for pattern in patterns:
        # Replace {run_id} placeholder
        resolved_pattern = pattern
        if "{run_id}" in pattern:
            if run_id is None:
                continue
            resolved_pattern = pattern.replace("{run_id}", run_id)
        
        # Handle glob patterns
        if "*" in resolved_pattern:
            parent = (project_root / resolved_pattern).parent
            if parent.exists():
                matched = list(parent.glob(Path(resolved_pattern).name))
                for m in matched:
                    key = f"comparison_{m.stem.split('_')[-1]}" if "comparison_" in pattern else m.stem
                    resolved[key] = m
        else:
            path = project_root / resolved_pattern
            if path.exists():
                key = path.stem.replace(".json", "").replace("_summary", "").replace("_results", "")
                resolved[key] = path
    
    return resolved


def generate_retrieval_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate retrieval recall table from final_summary.json."""
    final_summary = json.loads(input_files["final"].read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    # Extract per-repo metrics
    for repo_metrics in final_summary.get("per_repo", []):
        rows.append({
            "repository": repo_metrics.get("repo_id", "unknown"),
            "recall_at_k": repo_metrics.get("recall", 0.0),
            "mrr": repo_metrics.get("mrr", 0.0),
            "mean_latency_ms": repo_metrics.get("mean_latency_ms", 0.0),
        })
    
    # Add overall summary
    overall = final_summary.get("overall", {})
    if overall:
        rows.append({
            "repository": "OVERALL",
            "recall_at_k": overall.get("recall", 0.0),
            "mrr": overall.get("mrr", 0.0),
            "mean_latency_ms": overall.get("mean_latency_ms", 0.0),
        })
    
    _write_csv(output_path, rows)


def generate_latency_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate latency table from final_summary.json."""
    final_summary = json.loads(input_files["final"].read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    for repo_metrics in final_summary.get("per_repo", []):
        rows.append({
            "repository": repo_metrics.get("repo_id", "unknown"),
            "mean_latency_ms": round(repo_metrics.get("mean_latency_ms", 0.0), 2),
            "median_latency_ms": round(repo_metrics.get("median_latency_ms", 0.0), 2),
            "p95_latency_ms": round(repo_metrics.get("p95_latency_ms", 0.0), 2),
            "p99_latency_ms": round(repo_metrics.get("p99_latency_ms", 0.0), 2),
        })
    
    _write_csv(output_path, rows)


def generate_toolcall_comparison(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate tool call comparison table from comparison_*.json files."""
    # Aggregate comparison data across repos
    tool_calls: dict[str, list[float]] = {"agentretrieve": [], "ripgrep": [], "git_grep": []}
    
    for key, path in input_files.items():
        if not key.startswith("comparison_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for tool, metrics in data.get("tool_metrics", {}).items():
            if tool in tool_calls:
                tool_calls[tool].append(metrics.get("avg_tool_calls", 0.0))
    
    rows: list[dict[str, Any]] = []
    for tool, values in tool_calls.items():
        if values:
            avg_calls = sum(values) / len(values)
            rows.append({
                "tool": tool,
                "avg_tool_calls_per_task": round(avg_calls, 2),
                "sample_repos": len(values),
            })
    
    # Add reduction rates
    if rows:
        ar_avg = next((r["avg_tool_calls_per_task"] for r in rows if r["tool"] == "agentretrieve"), None)
        rg_avg = next((r["avg_tool_calls_per_task"] for r in rows if r["tool"] == "ripgrep"), None)
        if ar_avg is not None and rg_avg and rg_avg > 0:
            rows.append({
                "tool": "reduction_vs_ripgrep",
                "avg_tool_calls_per_task": f"{round((1 - ar_avg / rg_avg) * 100, 1)}%",
                "sample_repos": len(tool_calls["agentretrieve"]),
            })
    
    _write_csv(output_path, rows)


def generate_micro_summary(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate micro benchmark summary from micro_benchmark.json."""
    data = json.loads(input_files["micro_benchmark"].read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    # Aggregate metrics
    build_times = data.get("build_times_sec", [])
    query_latencies = data.get("query_latencies_ms", [])
    
    if build_times:
        rows.append({
            "metric": "build_time_p50_sec",
            "value": round(sorted(build_times)[len(build_times) // 2], 2) if build_times else 0,
        })
    if query_latencies:
        sorted_lat = sorted(query_latencies)
        rows.append({"metric": "query_latency_p50_ms", "value": round(sorted_lat[len(sorted_lat) // 2], 2)})
        rows.append({"metric": "query_latency_p95_ms", "value": round(sorted_lat[int(len(sorted_lat) * 0.95)], 2)})
    
    rows.append({"metric": "index_size_mb", "value": round(data.get("index_size_mb", 0), 2)})
    rows.append({"metric": "peak_rss_mb", "value": round(data.get("peak_rss_mb", 0), 2)})
    
    _write_csv(output_path, rows)


def generate_ablation_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate ablation study table from ablation.json."""
    data = json.loads(input_files["ablation"].read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    for config_name, metrics in data.get("results", {}).items():
        rows.append({
            "configuration": config_name,
            "recall": round(metrics.get("recall", 0.0), 4),
            "mrr": round(metrics.get("mrr", 0.0), 4),
            "mean_latency_ms": round(metrics.get("mean_latency_ms", 0.0), 2),
        })
    
    _write_csv(output_path, rows)


def generate_stability_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate stability analysis table from stability.json."""
    data = json.loads(input_files["stability"].read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    for metric_name, stats in data.get("repeatability", {}).items():
        ci = stats.get("ci_95", [0, 0])
        rows.append({
            "metric": metric_name,
            "mean": round(stats.get("mean", 0.0), 4),
            "std": round(stats.get("std", 0.0), 4),
            "cv": round(stats.get("cv", 0.0), 4),
            "ci_95_lower": round(ci[0], 4) if len(ci) > 0 else 0,
            "ci_95_upper": round(ci[1], 4) if len(ci) > 1 else 0,
        })
    
    _write_csv(output_path, rows)


def generate_cross_env_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate cross-environment reproducibility table from cross-env report."""
    # Use the cross_env_repro_report file
    report_file = input_files.get("cross_env_repro_report") or next(iter(input_files.values()), None)
    if report_file is None or not report_file.exists():
        print(f"Warning: No cross-env report found", file=sys.stderr)
        return
    
    data = json.loads(report_file.read_text(encoding="utf-8"))
    
    rows: list[dict[str, Any]] = []
    
    for exp_id, result in data.get("experiments", {}).items():
        rows.append({
            "experiment": exp_id,
            "status": "pass" if result.get("passed") else "fail",
            "quality_match": result.get("quality_match", False),
            "latency_match": result.get("latency_match", False),
            "notes": result.get("notes", ""),
        })
    
    # Add summary row
    summary = data.get("summary", {})
    if summary:
        rows.append({
            "experiment": "SUMMARY",
            "status": "pass" if summary.get("all_passed") else "fail",
            "quality_match": "",
            "latency_match": "",
            "notes": f"total={summary.get('total', 0)}, passed={summary.get('passed', 0)}",
        })
    
    _write_csv(output_path, rows)


def generate_coverage_table(input_files: dict[str, Path], output_path: Path) -> None:
    """Generate symbol extraction coverage table from index metrics."""
    # Use first available index file
    index_file = next(iter(input_files.values()), None)
    if index_file is None:
        print("Warning: No index files found for coverage table", file=sys.stderr)
        return
    
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from agentretrieve.index.inverted import InvertedIndex
    
    index = InvertedIndex.load(index_file)
    
    # Aggregate by language
    lang_stats: dict[str, dict[str, Any]] = {}
    for doc in index.documents.values():
        lang = (doc.lang or "unknown").lower()
        if lang not in lang_stats:
            lang_stats[lang] = {
                "file_count": 0,
                "symbol_regions": 0,
                "block_regions": 0,
            }
        lang_stats[lang]["file_count"] += 1
        lang_stats[lang]["symbol_regions"] += len(doc.symbol_regions)
        lang_stats[lang]["block_regions"] += len(doc.block_regions)
    
    rows: list[dict[str, Any]] = []
    for lang, stats in sorted(lang_stats.items()):
        symbol_rate = stats["symbol_regions"] / max(stats["block_regions"], 1)
        rows.append({
            "language": lang,
            "file_count": stats["file_count"],
            "avg_symbol_regions": round(stats["symbol_regions"] / stats["file_count"], 2),
            "symbol_to_block_ratio": round(symbol_rate, 4),
        })
    
    _write_csv(output_path, rows)


def _write_csv(output_path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paper figure assets")
    parser.add_argument("--run-id", help="Run ID for run-dependent figures")
    parser.add_argument("--strict", action="store_true", help="Fail if any input artifact is missing")
    parser.add_argument("--only", help="Comma-separated list of figure names to generate")
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parents[2]
    sources = load_figure_sources()
    figures = sources.get("figures", {})
    
    only_set = set(args.only.split(",")) if args.only else None
    
    generators: dict[str, tuple[Any, list[str]]] = {
        "retrieval_recall_by_repo": (generate_retrieval_table, ["final"]),
        "retrieval_latency_by_repo": (generate_latency_table, ["final"]),
        "tool_call_comparison": (generate_toolcall_comparison, []),
        "micro_benchmark_summary": (generate_micro_summary, ["micro_benchmark"]),
        "ablation_study": (generate_ablation_table, ["ablation"]),
        "stability_analysis": (generate_stability_table, ["stability"]),
        "cross_env_reproducibility": (generate_cross_env_table, []),
        "symbol_extraction_coverage": (generate_coverage_table, []),
    }
    
    generated = 0
    skipped = 0
    
    for name, config in figures.items():
        if only_set and name not in only_set:
            continue
        
        print(f"Generating: {name}")
        
        output_path = project_root / config["output_path"]
        input_patterns = config.get("generator", {}).get("input_artifacts", [])
        
        # Resolve input artifacts
        input_files = resolve_input_artifacts(input_patterns, project_root, args.run_id)
        
        # Check generator availability
        gen_info = generators.get(name)
        if gen_info is None or gen_info[0] is None:
            print(f"  [skip] Generator not implemented for {name}")
            skipped += 1
            continue
        
        generator_fn, required_keys = gen_info
        
        # Generate
        try:
            generator_fn(input_files, output_path)
            print(f"  [ok] {output_path}")
            generated += 1
        except Exception as e:
            print(f"  [error] {e}")
            if args.strict:
                return 1
            skipped += 1
    
    print(f"\nSummary: {generated} generated, {skipped} skipped")
    return 0 if not args.strict or skipped == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
