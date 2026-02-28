#!/usr/bin/env python3
"""Generate a Markdown report from pipeline summary artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_summary(summary: dict[str, Any]) -> dict[str, Any]:
    if "overall" in summary:
        return summary

    # Backward-compatible fallback: allow aggregate_results.json as input.
    results = summary.get("results", {})
    total_tasks = sum(item.get("total", 0) for item in results.values())
    total_found = sum(item.get("found", 0) for item in results.values())
    avg_mrr = (
        sum(item.get("mrr", 0.0) for item in results.values()) / len(results)
        if results
        else 0.0
    )

    return {
        "timestamp": summary.get("timestamp"),
        "config": {},
        "overall": {
            "repositories": len(results),
            "total_tasks": total_tasks,
            "found": total_found,
            "recall": (total_found / total_tasks) if total_tasks else 0.0,
            "avg_mrr": avg_mrr,
            "avg_latency_ms": None,
        },
        "by_difficulty": {},
        "by_task_type": {},
        "per_repository": {
            repo_id: {
                "recall": metrics.get("recall", 0.0),
                "mrr": metrics.get("mrr", 0.0),
                "latency_ms": None,
            }
            for repo_id, metrics in results.items()
        },
    }


def _render_report(
    summary: dict[str, Any],
    aggregate: dict[str, Any] | None,
    title: str,
) -> str:
    overall = summary["overall"]
    config = summary.get("config", {})
    by_difficulty = summary.get("by_difficulty", {})
    by_task_type = summary.get("by_task_type", {})
    per_repo = summary.get("per_repository", {})

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Timestamp: `{summary.get('timestamp', 'unknown')}`")
    lines.append(
        "- Overall: "
        f"Recall `{overall.get('found', 0)}/{overall.get('total_tasks', 0)}` "
        f"({_pct(overall.get('recall', 0.0))}), "
        f"MRR `{overall.get('avg_mrr', 0.0):.3f}`"
    )
    if overall.get("avg_latency_ms") is not None:
        lines.append(f"- Avg latency: `{overall['avg_latency_ms']:.1f} ms`")
    lines.append("")

    lines.append("## Configuration")
    lines.append("")
    if config:
        lines.append("| k1 | b | min_match_ratio | max_terms |")
        lines.append("|---|---|---|---|")
        lines.append(
            f"| {config.get('k1')} | {config.get('b')} | "
            f"{config.get('min_match_ratio')} | {config.get('max_terms')} |"
        )
    else:
        lines.append("- Not available in source artifact.")
    lines.append("")

    lines.append("## Overall")
    lines.append("")
    lines.append("| Repositories | Tasks | Found | Recall | MRR | Avg Latency (ms) |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    latency_value = overall.get("avg_latency_ms")
    latency_str = f"{latency_value:.1f}" if latency_value is not None else "N/A"
    lines.append(
        f"| {overall.get('repositories', 0)} | {overall.get('total_tasks', 0)} | "
        f"{overall.get('found', 0)} | {_pct(overall.get('recall', 0.0))} | "
        f"{overall.get('avg_mrr', 0.0):.3f} | {latency_str} |"
    )
    lines.append("")

    if by_difficulty:
        lines.append("## By Difficulty")
        lines.append("")
        lines.append("| Difficulty | Found | Total | Recall |")
        lines.append("|---|---:|---:|---:|")
        for difficulty in ["easy", "medium", "hard"]:
            if difficulty not in by_difficulty:
                continue
            item = by_difficulty[difficulty]
            lines.append(
                f"| {difficulty} | {item.get('found', 0)} | {item.get('total', 0)} | "
                f"{_pct(item.get('recall', 0.0))} |"
            )
        lines.append("")

    if by_task_type:
        lines.append("## By Task Type")
        lines.append("")
        lines.append("| Type | Found | Total | Recall |")
        lines.append("|---|---:|---:|---:|")
        for task_type in sorted(by_task_type.keys()):
            item = by_task_type[task_type]
            lines.append(
                f"| {task_type} | {item.get('found', 0)} | {item.get('total', 0)} | "
                f"{_pct(item.get('recall', 0.0))} |"
            )
        lines.append("")

    if per_repo:
        lines.append("## Per Repository")
        lines.append("")
        lines.append("| Repository | Recall | MRR | Latency (ms) |")
        lines.append("|---|---:|---:|---:|")
        for repo_id in sorted(per_repo.keys()):
            item = per_repo[repo_id]
            repo_latency = item.get("latency_ms")
            repo_latency_str = f"{repo_latency:.1f}" if repo_latency is not None else "N/A"
            lines.append(
                f"| {repo_id} | {_pct(item.get('recall', 0.0))} | "
                f"{item.get('mrr', 0.0):.3f} | {repo_latency_str} |"
            )
        lines.append("")

    if aggregate and aggregate.get("optimal_configs"):
        lines.append("## Parameter Search Optima")
        lines.append("")
        lines.append("| Repository | k1 | b | min_match_ratio | max_terms |")
        lines.append("|---|---:|---:|---:|---:|")
        for repo_id in sorted(aggregate["optimal_configs"].keys()):
            cfg = aggregate["optimal_configs"][repo_id]
            lines.append(
                f"| {repo_id} | {cfg.get('k1')} | {cfg.get('b')} | "
                f"{cfg.get('min_match_ratio')} | {cfg.get('max_terms')} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final pipeline Markdown report")
    parser.add_argument(
        "--summary",
        default="",
        help="Path to final_summary.json (preferred source of truth)",
    )
    parser.add_argument(
        "--aggregate",
        default="",
        help="Optional path to aggregate_results.json for optimal parameter table",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Legacy alias. If --summary is omitted, this path is used as summary input.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output Markdown path",
    )
    parser.add_argument(
        "--title",
        default="Final Pipeline Report",
        help="Report title",
    )
    args = parser.parse_args()

    summary_input = args.summary or args.input
    if not summary_input:
        raise SystemExit("either --summary or --input must be provided")

    summary_path = Path(summary_input)
    if not summary_path.exists():
        raise SystemExit(f"summary input not found: {summary_path}")

    summary_raw = _load_json(summary_path)
    summary = _format_summary(summary_raw)

    aggregate_data: dict[str, Any] | None = None
    if args.aggregate:
        aggregate_path = Path(args.aggregate)
        if aggregate_path.exists():
            aggregate_data = _load_json(aggregate_path)

    report = _render_report(summary=summary, aggregate=aggregate_data, title=args.title)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
