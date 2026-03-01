#!/usr/bin/env python3
"""Complete Phase 3 pending metrics (EXP-005/006/007/008)."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


REPOS = ["ripgrep", "fd", "fzf", "curl", "fmt", "pytest", "cli"]


def _quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "count": 0.0}
    ordered = sorted(values)

    def pct(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        pos = (len(ordered) - 1) * p
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return ordered[lo]
        frac = pos - lo
        return ordered[lo] * (1 - frac) + ordered[hi] * frac

    return {
        "p50": pct(0.50),
        "p95": pct(0.95),
        "p99": pct(0.99),
        "mean": statistics.mean(ordered),
        "count": float(len(ordered)),
    }


def _load_taskset(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def _normalize_terms(raw_terms: list[str]) -> list[str]:
    out: list[str] = []
    for t in raw_terms:
        out.extend(re.findall(r"[a-z]+|[0-9]+", t.lower()))
    return out


def _compute_retrieval_metrics(paths: list[Path]) -> dict[str, float]:
    total_tasks = 0
    found = 0
    mrr_sum = 0.0
    latency: list[float] = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        metrics = data.get("metrics", {})
        results = data.get("results", [])
        total_tasks += int(metrics.get("num_tasks", len(results)))
        found += int(metrics.get("found_count", 0))
        mrr_sum += float(metrics.get("mrr", 0.0)) * max(1, int(metrics.get("num_tasks", len(results))))
        for r in results:
            latency.append(float(r.get("latency_ms", 0.0)))

    recall = found / total_tasks if total_tasks else 0.0
    mrr = mrr_sum / total_tasks if total_tasks else 0.0
    return {
        "tasks": total_tasks,
        "found": found,
        "recall": recall,
        "mrr": mrr,
        "latency_ms_mean": statistics.mean(latency) if latency else 0.0,
    }


def _compute_comparison_agentretrieve_metrics(paths: list[Path]) -> dict[str, float]:
    total_tasks = 0
    found = 0
    reciprocal_sum = 0.0
    latencies: list[float] = []
    stdout_bytes: list[float] = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        for comp in data.get("comparisons", []):
            total_tasks += 1
            for r in comp.get("results", []):
                if r.get("tool") != "agentretrieve":
                    continue
                rank = r.get("rank")
                if rank is not None:
                    found += 1
                    reciprocal_sum += 1.0 / float(rank)
                latencies.append(float(r.get("latency_ms", 0.0)))
                stdout_bytes.append(float(r.get("stdout_bytes", 0.0)))
                break
    return {
        "tasks": total_tasks,
        "found": found,
        "recall": (found / total_tasks) if total_tasks else 0.0,
        "mrr": (reciprocal_sum / total_tasks) if total_tasks else 0.0,
        "latency_ms_mean": statistics.mean(latencies) if latencies else 0.0,
        "stdout_bytes_total": float(sum(stdout_bytes)),
        "stdout_bytes_mean": statistics.mean(stdout_bytes) if stdout_bytes else 0.0,
    }


def _build_index_with_rss(
    root: Path,
    repo: str,
    output_index: Path,
) -> dict[str, float]:
    source_dir = root / "artifacts" / "datasets" / "raw" / repo
    output_index.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "/usr/bin/time",
        "-f",
        "%M",
        "python3",
        "-m",
        "agentretrieve.cli",
        "ix",
        "build",
        str(source_dir),
        "-o",
        str(output_index),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    build_timeout_sec = int(os.getenv("AR_MICRO_BUILD_TIMEOUT_SEC", "45"))
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=build_timeout_sec,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
    except subprocess.TimeoutExpired:
        return {
            "build_latency_ms": float(build_timeout_sec) * 1000.0,
            "peak_rss_kb": 0.0,
            "index_size_bytes": 0.0,
            "timed_out": 1.0,
        }

    rss_kb = 0.0
    for line in proc.stderr.splitlines()[::-1]:
        line = line.strip()
        if line.isdigit():
            rss_kb = float(line)
            break

    index_size = float(output_index.stat().st_size) if output_index.exists() else 0.0
    return {
        "build_latency_ms": elapsed_ms,
        "peak_rss_kb": rss_kb,
        "index_size_bytes": index_size,
        "timed_out": 0.0,
    }


def _measure_update_latency(root: Path, index_path: Path) -> float:
    cmd = [
        "python3",
        "-m",
        "agentretrieve.cli",
        "ix",
        "update",
        str(index_path),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    started = time.perf_counter()
    subprocess.run(
        cmd,
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return (time.perf_counter() - started) * 1000


def run_micro_benchmark(root: Path, run_dir: Path) -> dict[str, Any]:
    micro_dir = run_dir / "micro_indexes"
    micro_dir.mkdir(parents=True, exist_ok=True)

    build_latencies: list[float] = []
    update_latencies: list[float] = []
    rss_values: list[float] = []
    size_values: list[float] = []
    query_latencies: list[float] = []

    by_repo: dict[str, Any] = {}
    for repo in REPOS:
        print(f"[micro] {repo}")
        index_path = micro_dir / f"{repo}.index.json"
        built = _build_index_with_rss(root=root, repo=repo, output_index=index_path)
        try:
            update_ms = _measure_update_latency(root=root, index_path=index_path)
        except Exception:
            update_ms = 60000.0
        retrieval_path = run_dir / f"retrieval_{repo}.json"
        retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
        q_lat = [float(r.get("latency_ms", 0.0)) for r in retrieval.get("results", [])]
        query_latencies.extend(q_lat)

        build_latencies.append(float(built["build_latency_ms"]))
        update_latencies.append(update_ms)
        rss_values.append(float(built["peak_rss_kb"]))
        size_values.append(float(built["index_size_bytes"]))

        by_repo[repo] = {
            **built,
            "update_latency_ms": update_ms,
            "query_latency_ms": _quantiles(q_lat),
        }

    return {
        "run_id": run_dir.name,
        "by_repo": by_repo,
        "aggregate": {
            "build_latency_ms": _quantiles(build_latencies),
            "update_latency_ms": _quantiles(update_latencies),
            "query_latency_ms": _quantiles(query_latencies),
            "peak_rss_kb": _quantiles(rss_values),
            "index_size_bytes": _quantiles(size_values),
        },
    }


def run_e2e_metrics(run_dir: Path) -> dict[str, Any]:
    ar_latencies: list[float] = []
    ar_stdout: list[float] = []
    task_count = 0
    for repo in REPOS:
        data = json.loads((run_dir / f"comparison_{repo}.json").read_text(encoding="utf-8"))
        for comp in data.get("comparisons", []):
            task_count += 1
            for r in comp.get("results", []):
                if r.get("tool") == "agentretrieve":
                    ar_latencies.append(float(r.get("latency_ms", 0.0)))
                    ar_stdout.append(float(r.get("stdout_bytes", 0.0)))
                    break

    return {
        "run_id": run_dir.name,
        "task_count": task_count,
        "tool_calls_per_task": 1.0,
        "stdout_bytes_per_task": statistics.mean(ar_stdout) if ar_stdout else 0.0,
        "stdout_bytes_total": sum(ar_stdout),
        "ttfc_ms": _quantiles(ar_latencies),
    }


def _evaluate_variant_for_repo(
    index_path: Path,
    repo_tasks: list[dict[str, Any]],
    variant: str,
) -> dict[str, float]:
    idx = InvertedIndex.load(index_path)
    engine = QueryEngine(idx)
    found = 0
    mrr_sum = 0.0
    latencies: list[float] = []
    total = len(repo_tasks)

    for task in repo_tasks:
        query = task.get("query_dsl", {})
        must_raw = query.get("must", [])
        norm = _normalize_terms(must_raw)[:3]
        if not norm:
            continue
        symbol: list[str] = []
        near: list[dict[str, Any]] = []
        should: list[str] = []
        min_match = 0

        if variant in {"plus_symbol", "plus_near", "plus_prior"}:
            symbol = [must_raw[0]] if must_raw else []
        if variant in {"plus_near", "plus_prior"} and len(norm) >= 2:
            near = [{"terms": norm[:2], "scope": "line_window", "window": 20}]
        if variant in {"plus_prior"}:
            split = max(1, len(norm) // 2)
            should = norm[split:]
            min_match = 1 if should else 0

        started = time.perf_counter()
        results = engine.search(
            must=norm,
            should=should,
            not_terms=[],
            max_results=max(int(query.get("k", 1)), 10),
            max_hits=5,
            min_match=min_match,
            symbol=symbol,
            near=near,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)

        gold_file = task.get("gold", {}).get("file", "")
        rank = None
        for i, r in enumerate(results):
            if gold_file and gold_file in r.path:
                rank = i + 1
                break
        if rank is not None:
            found += 1
            mrr_sum += 1.0 / rank

    return {
        "tasks": float(total),
        "found": float(found),
        "recall": (found / total) if total else 0.0,
        "mrr": (mrr_sum / total) if total else 0.0,
        "latency_ms_mean": statistics.mean(latencies) if latencies else 0.0,
    }


def run_ablation(root: Path, taskset_path: Path) -> dict[str, Any]:
    tasks = _load_taskset(taskset_path)
    by_repo_tasks: dict[str, list[dict[str, Any]]] = {repo: [] for repo in REPOS}
    for t in tasks:
        repo = t.get("repo")
        if repo in by_repo_tasks:
            by_repo_tasks[repo].append(t)

    variants = ["bm25_only", "plus_symbol", "plus_near", "plus_prior"]
    by_repo: dict[str, Any] = {}
    aggregate: dict[str, dict[str, float]] = {
        v: {"tasks": 0.0, "found": 0.0, "mrr_sum": 0.0, "latency_weighted_sum": 0.0}
        for v in variants
    }

    for repo in REPOS:
        repo_out: dict[str, Any] = {}
        index_path = root / "artifacts" / "datasets" / f"{repo}.index.json"
        repo_tasks = by_repo_tasks[repo]
        for variant in variants:
            metrics = _evaluate_variant_for_repo(index_path=index_path, repo_tasks=repo_tasks, variant=variant)
            repo_out[variant] = metrics
            aggregate[variant]["tasks"] += metrics["tasks"]
            aggregate[variant]["found"] += metrics["found"]
            aggregate[variant]["mrr_sum"] += metrics["mrr"] * metrics["tasks"]
            aggregate[variant]["latency_weighted_sum"] += metrics["latency_ms_mean"] * metrics["tasks"]
        by_repo[repo] = repo_out

    final_agg: dict[str, Any] = {}
    for variant in variants:
        total = aggregate[variant]["tasks"]
        recall = aggregate[variant]["found"] / total if total else 0.0
        mrr = aggregate[variant]["mrr_sum"] / total if total else 0.0
        lat = aggregate[variant]["latency_weighted_sum"] / total if total else 0.0
        final_agg[variant] = {
            "tasks": total,
            "recall": recall,
            "mrr": mrr,
            "latency_ms_mean": lat,
        }

    base = final_agg["bm25_only"]
    delta: dict[str, Any] = {}
    for variant in variants:
        cur = final_agg[variant]
        delta[variant] = {
            "delta_recall": cur["recall"] - base["recall"],
            "delta_mrr": cur["mrr"] - base["mrr"],
            "delta_latency_ms": cur["latency_ms_mean"] - base["latency_ms_mean"],
        }

    return {"by_repo": by_repo, "aggregate": final_agg, "delta_vs_bm25_only": delta}


def _parse_overall_summary(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    overall = data.get("overall", {})
    return {
        "recall": float(overall.get("recall", 0.0)),
        "mrr": float(overall.get("avg_mrr", 0.0)),
        "latency_ms": float(overall.get("avg_latency_ms", 0.0)),
    }


def _run_repeat(
    root: Path,
    run_dir: Path,
    repeat_idx: int,
    taskset_path: Path,
    final_config: Path,
) -> dict[str, Any]:
    rep_dir = run_dir / "repeats" / f"repeat_{repeat_idx:02d}"
    rep_dir.mkdir(parents=True, exist_ok=True)

    # EXP-001 (final evaluation).
    final_out = rep_dir / "final_eval"
    final_out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "python3",
            "scripts/pipeline/run_final_evaluation.py",
            "-c",
            str(final_config),
            "-o",
            str(final_out),
        ],
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    exp001 = _parse_overall_summary(final_out / "final_summary.json")

    # EXP-003/004.
    retrieval_paths: list[Path] = []
    comparison_paths: list[Path] = []
    for repo in REPOS:
        ret_path = rep_dir / f"retrieval_{repo}.json"
        cmp_path = rep_dir / f"comparison_{repo}.json"
        subprocess.run(
            [
                "python3",
                "scripts/benchmark/evaluate_taskset.py",
                "--index",
                f"artifacts/datasets/{repo}.index.json",
                "--taskset",
                str(taskset_path),
                "--repo",
                repo,
                "-o",
                str(ret_path),
            ],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        subprocess.run(
            [
                "python3",
                "scripts/benchmark/run_comparison.py",
                "--repo-name",
                repo,
                "--repo-path",
                f"artifacts/datasets/raw/{repo}",
                "--index",
                f"artifacts/datasets/{repo}.index.json",
                "--taskset",
                str(taskset_path),
                "-o",
                str(cmp_path),
            ],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        retrieval_paths.append(ret_path)
        comparison_paths.append(cmp_path)

    exp003 = _compute_retrieval_metrics(retrieval_paths)
    exp004 = _compute_comparison_agentretrieve_metrics(comparison_paths)
    return {"repeat": repeat_idx, "exp001": exp001, "exp003": exp003, "exp004": exp004}


def _ci95(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "ci95_half_width": 0.0}
    if len(values) == 1:
        return {"mean": values[0], "std": 0.0, "ci95_half_width": 0.0}
    std = statistics.stdev(values)
    hw = 1.96 * std / math.sqrt(len(values))
    return {"mean": statistics.mean(values), "std": std, "ci95_half_width": hw}


def run_stability(
    root: Path,
    run_dir: Path,
    taskset_path: Path,
    final_config: Path,
    repeats: int,
) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")

    per_repeat: list[dict[str, Any]] = []

    # First sample from existing artifacts (repeat_00 baseline).
    exp001 = _parse_overall_summary(run_dir / "final_summary.json")
    retrieval_paths = [run_dir / f"retrieval_{repo}.json" for repo in REPOS]
    comparison_paths = [run_dir / f"comparison_{repo}.json" for repo in REPOS]
    exp003 = _compute_retrieval_metrics(retrieval_paths)
    exp004 = _compute_comparison_agentretrieve_metrics(comparison_paths)
    per_repeat.append({"repeat": 0, "exp001": exp001, "exp003": exp003, "exp004": exp004})

    for i in range(1, repeats):
        per_repeat.append(
            _run_repeat(
                root=root,
                run_dir=run_dir,
                repeat_idx=i,
                taskset_path=taskset_path,
                final_config=final_config,
            )
        )

    def series(selector: str) -> list[float]:
        out: list[float] = []
        section, key = selector.split(".")
        for r in per_repeat:
            out.append(float(r[section][key]))
        return out

    return {
        "repeats": repeats,
        "per_repeat": per_repeat,
        "summary": {
            "exp001_recall": _ci95(series("exp001.recall")),
            "exp001_mrr": _ci95(series("exp001.mrr")),
            "exp001_latency_ms": _ci95(series("exp001.latency_ms")),
            "exp003_recall": _ci95(series("exp003.recall")),
            "exp003_mrr": _ci95(series("exp003.mrr")),
            "exp003_latency_ms_mean": _ci95(series("exp003.latency_ms_mean")),
            "exp004_ar_recall": _ci95(series("exp004.recall")),
            "exp004_ar_mrr": _ci95(series("exp004.mrr")),
            "exp004_ar_latency_ms_mean": _ci95(series("exp004.latency_ms_mean")),
            "exp004_ar_stdout_bytes_mean": _ci95(series("exp004.stdout_bytes_mean")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete remaining Phase 3 metrics.")
    parser.add_argument("--run-id", required=True, help="Run ID under artifacts/experiments/runs/")
    parser.add_argument(
        "--taskset",
        default="docs/benchmarks/taskset.v2.full.jsonl",
        help="Taskset JSONL path",
    )
    parser.add_argument(
        "--final-config",
        default="artifacts/experiments/pipeline/generated_experiment_pipeline.final_raw.yaml",
        help="Final evaluation config path",
    )
    parser.add_argument("--repeats", type=int, default=5, help="Number of repeats for stability")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    run_dir = root / "artifacts" / "experiments" / "runs" / args.run_id
    taskset_path = (root / args.taskset).resolve()
    final_config = (root / args.final_config).resolve()

    print("[phase3] micro benchmark")
    micro = run_micro_benchmark(root=root, run_dir=run_dir)
    (run_dir / "micro_benchmark.json").write_text(json.dumps(micro, indent=2), encoding="utf-8")

    print("[phase3] e2e metrics")
    e2e = run_e2e_metrics(run_dir=run_dir)
    (run_dir / "e2e_metrics.json").write_text(json.dumps(e2e, indent=2), encoding="utf-8")

    print("[phase3] ablation")
    ablation = run_ablation(root=root, taskset_path=taskset_path)
    (run_dir / "ablation.json").write_text(json.dumps(ablation, indent=2), encoding="utf-8")

    print("[phase3] stability")
    stability = run_stability(
        root=root,
        run_dir=run_dir,
        taskset_path=taskset_path,
        final_config=final_config,
        repeats=args.repeats,
    )
    (run_dir / "stability.json").write_text(json.dumps(stability, indent=2), encoding="utf-8")

    print(f"generated: {run_dir / 'micro_benchmark.json'}")
    print(f"generated: {run_dir / 'e2e_metrics.json'}")
    print(f"generated: {run_dir / 'ablation.json'}")
    print(f"generated: {run_dir / 'stability.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    build_timeout_sec = int(os.getenv("AR_MICRO_BUILD_TIMEOUT_SEC", "45"))
