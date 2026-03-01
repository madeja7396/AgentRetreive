#!/usr/bin/env python3
"""Export symbol extraction support metrics by language from an index.

This script analyzes an index file and reports:
- File count and coverage by language
- Symbol region extraction success rate
- Fallback rate (symbol_regions falling back to block_regions)
- Overall extraction quality metrics

Usage:
    python3 scripts/benchmark/export_symbol_support_metrics.py \
        --index artifacts/datasets/fd.index.json \
        --output artifacts/experiments/pipeline/symbol_support_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentretrieve.index.inverted import InvertedIndex


def load_extraction_config() -> dict[str, Any]:
    """Load symbol extraction support configuration."""
    config_path = (
        Path(__file__).resolve().parents[2] / "configs" / "symbol_extraction_support.v1.json"
    )
    if not config_path.exists():
        return {"languages": {}}
    return json.loads(config_path.read_text(encoding="utf-8"))


def analyze_index(index: InvertedIndex) -> dict[str, Any]:
    """Analyze symbol extraction metrics from an index."""
    config = load_extraction_config()
    supported_langs = set(config.get("languages", {}).keys())
    
    # Aggregate by language
    lang_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "file_count": 0,
            "total_lines": 0,
            "symbol_regions": 0,
            "block_regions": 0,
            "files_with_symbol_fallback": 0,
        }
    )
    
    for doc in index.documents.values():
        lang = (doc.lang or "unknown").lower()
        stats = lang_stats[lang]
        stats["file_count"] += 1
        stats["total_lines"] += doc.line_count
        stats["symbol_regions"] += len(doc.symbol_regions)
        stats["block_regions"] += len(doc.block_regions)
        
        # Detect fallback: symbol_regions equals block_regions (or very similar)
        # This indicates symbol extraction didn't find additional structure
        if len(doc.symbol_regions) == len(doc.block_regions) and len(doc.block_regions) > 0:
            # Further check: if they're identical, it's a clear fallback
            if doc.symbol_regions == doc.block_regions:
                stats["files_with_symbol_fallback"] += 1
    
    # Calculate derived metrics
    results: dict[str, Any] = {
        "by_language": {},
        "summary": {
            "total_files": 0,
            "total_languages": 0,
            "supported_languages_found": [],
            "unsupported_languages_found": [],
        },
    }
    
    for lang, stats in sorted(lang_stats.items()):
        file_count = stats["file_count"]
        fallback_rate = (
            stats["files_with_symbol_fallback"] / file_count if file_count > 0 else 0.0
        )
        
        # Determine extraction mode and reliability
        lang_config = config.get("languages", {}).get(lang, {})
        mode = lang_config.get("mode", "unknown")
        reliability = config.get("extraction_modes", {}).get(mode, {}).get("reliability", "unknown")
        
        results["by_language"][lang] = {
            "file_count": file_count,
            "total_lines": stats["total_lines"],
            "symbol_regions": stats["symbol_regions"],
            "block_regions": stats["block_regions"],
            "files_with_symbol_fallback": stats["files_with_symbol_fallback"],
            "fallback_rate": round(fallback_rate, 4),
            "extraction_mode": mode,
            "reliability": reliability,
            "avg_symbol_regions_per_file": round(stats["symbol_regions"] / file_count, 2)
            if file_count > 0
            else 0.0,
        }
        
        results["summary"]["total_files"] += file_count
        if lang in supported_langs:
            results["summary"]["supported_languages_found"].append(lang)
        else:
            results["summary"]["unsupported_languages_found"].append(lang)
    
    results["summary"]["total_languages"] = len(lang_stats)
    results["summary"]["supported_languages_found"] = sorted(
        set(results["summary"]["supported_languages_found"])
    )
    results["summary"]["unsupported_languages_found"] = sorted(
        set(results["summary"]["unsupported_languages_found"])
    )
    
    # Calculate overall fallback rate
    total_files = results["summary"]["total_files"]
    total_fallback_files = sum(
        s["files_with_symbol_fallback"] for s in lang_stats.values()
    )
    results["summary"]["overall_fallback_rate"] = round(
        total_fallback_files / total_files, 4
    ) if total_files > 0 else 0.0
    
    # Check thresholds
    thresholds = config.get("thresholds", {})
    warnings: list[dict[str, Any]] = []
    
    for lang, data in results["by_language"].items():
        fallback_rate = data["fallback_rate"]
        if fallback_rate >= thresholds.get("fallback_rate_critical", 0.5):
            warnings.append(
                {
                    "level": "critical",
                    "language": lang,
                    "metric": "fallback_rate",
                    "value": fallback_rate,
                    "threshold": thresholds.get("fallback_rate_critical"),
                }
            )
        elif fallback_rate >= thresholds.get("fallback_rate_warning", 0.3):
            warnings.append(
                {
                    "level": "warning",
                    "language": lang,
                    "metric": "fallback_rate",
                    "value": fallback_rate,
                    "threshold": thresholds.get("fallback_rate_warning"),
                }
            )
    
    results["threshold_checks"] = {
        "warnings": warnings,
        "warning_count": len([w for w in warnings if w["level"] == "warning"]),
        "critical_count": len([w for w in warnings if w["level"] == "critical"]),
    }
    
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export symbol extraction support metrics from an index"
    )
    parser.add_argument("--index", required=True, help="Index file path")
    parser.add_argument("-o", "--output", help="Output JSON path")
    parser.add_argument(
        "--summary-only", action="store_true", help="Output only summary, not per-language details"
    )
    args = parser.parse_args()
    
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index not found: {args.index}", file=sys.stderr)
        return 1
    
    print(f"Loading index: {args.index}", file=sys.stderr)
    index = InvertedIndex.load(index_path)
    print(f"  Documents: {index.total_docs}", file=sys.stderr)
    
    print("Analyzing symbol extraction metrics...", file=sys.stderr)
    results = analyze_index(index)
    
    # Add metadata
    results["metadata"] = {
        "index_path": str(index_path),
        "total_docs": index.total_docs,
        "version": "symbol_support.v1",
    }
    
    if args.summary_only:
        output = {"summary": results["summary"], "threshold_checks": results["threshold_checks"]}
    else:
        output = results
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"Results saved to: {args.output}", file=sys.stderr)
    
    print(json.dumps(output, indent=2))
    
    # Return non-zero if critical thresholds exceeded
    if results["threshold_checks"]["critical_count"] > 0:
        return 2
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
