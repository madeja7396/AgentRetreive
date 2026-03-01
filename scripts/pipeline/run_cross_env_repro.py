#!/usr/bin/env python3
"""Re-run key experiments on another Python runtime and compare tolerances."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REPOS = ["ripgrep", "fd", "fzf", "curl", "fmt", "pytest", "cli"]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _aggregate_retrieval_metrics(paths: list[Path]) -> dict[str, float]:
    total_tasks = 0
    found = 0
    mrr_weighted = 0.0
    lat_weighted = 0.0
    for p in paths:
        d = _load_json(p)
        m = d.get("metrics", {})
        n = int(m.get("num_tasks", 0))
        total_tasks += n
        found += int(m.get("found_count", 0))
        mrr_weighted += float(m.get("mrr", 0.0)) * n
        lat_weighted += float(m.get("mean_latency_ms", 0.0)) * n
    return {
        "tasks": total_tasks,
        "recall": (found / total_tasks) if total_tasks else 0.0,
        "mrr": (mrr_weighted / total_tasks) if total_tasks else 0.0,
        "latency_ms_mean": (lat_weighted / total_tasks) if total_tasks else 0.0,
    }


def _aggregate_comparison_agentretrieve(paths: list[Path]) -> dict[str, float]:
    total = 0
    found = 0
    reciprocal = 0.0
    lat_sum = 0.0
    out_sum = 0.0
    for p in paths:
        d = _load_json(p)
        for c in d.get("comparisons", []):
            total += 1
            for r in c.get("results", []):
                if r.get("tool") != "agentretrieve":
                    continue
                rank = r.get("rank")
                if rank is not None:
                    found += 1
                    reciprocal += 1.0 / float(rank)
                lat_sum += float(r.get("latency_ms", 0.0))
                out_sum += float(r.get("stdout_bytes", 0.0))
                break
    return {
        "tasks": total,
        "recall": (found / total) if total else 0.0,
        "mrr": (reciprocal / total) if total else 0.0,
        "latency_ms_mean": (lat_sum / total) if total else 0.0,
        "stdout_bytes_mean": (out_sum / total) if total else 0.0,
    }


def _diff_ok(base: float, cand: float, abs_tol: float, rel_tol: float) -> tuple[float, float, bool]:
    abs_diff = abs(cand - base)
    rel_diff = abs_diff / abs(base) if base != 0 else (0.0 if cand == 0 else 1.0)
    ok = abs_diff <= abs_tol or rel_diff <= rel_tol
    return abs_diff, rel_diff, ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-environment reproducibility check")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--python-exec", default="python3.11")
    parser.add_argument("--taskset", default="docs/benchmarks/taskset.v2.full.jsonl")
    parser.add_argument(
        "--constraints",
        default="docs/benchmarks/run_constraints.v2.json",
        help="Run constraints JSON (v2 preferred) for tolerance defaults",
    )
    parser.add_argument(
        "--final-config",
        default="artifacts/experiments/pipeline/generated_experiment_pipeline.final_raw.yaml",
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=None,
        help="absolute tolerance for quality metrics (recall/mrr)",
    )
    parser.add_argument(
        "--rel-latency-tol",
        type=float,
        default=None,
        help="relative tolerance for latency metrics",
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Optional suffix for output filename (e.g. tol30)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    base_dir = root / "artifacts" / "experiments" / "runs" / args.run_id
    cross_dir = base_dir / "cross_env_py311"
    cross_dir.mkdir(parents=True, exist_ok=True)

    constraints_path = (root / args.constraints).resolve()
    constraints = {}
    if constraints_path.exists():
        constraints = _load_json(constraints_path)
    repro = constraints.get("reproducibility", {})
    abs_tol = (
        float(args.abs_tol)
        if args.abs_tol is not None
        else float(repro.get("quality_abs_tolerance", 0.01))
    )
    rel_latency_tol = (
        float(args.rel_latency_tol)
        if args.rel_latency_tol is not None
        else float(repro.get("latency_rel_tolerance", 0.10))
    )

    py = args.python_exec

    # 1) final evaluation
    final_out = cross_dir / "final_eval"
    final_out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [py, "scripts/pipeline/run_final_evaluation.py", "-c", args.final_config, "-o", str(final_out)],
        cwd=str(root),
        check=True,
    )

    # 2) retrieval + comparison
    retrieval_paths: list[Path] = []
    comparison_paths: list[Path] = []
    for repo in REPOS:
        ret = cross_dir / f"retrieval_{repo}.json"
        cmp = cross_dir / f"comparison_{repo}.json"
        subprocess.run(
            [
                py,
                "scripts/benchmark/evaluate_taskset.py",
                "--index",
                f"artifacts/datasets/{repo}.index.json",
                "--taskset",
                args.taskset,
                "--repo",
                repo,
                "-o",
                str(ret),
            ],
            cwd=str(root),
            check=True,
        )
        subprocess.run(
            [
                py,
                "scripts/benchmark/run_comparison.py",
                "--repo-name",
                repo,
                "--repo-path",
                f"artifacts/datasets/raw/{repo}",
                "--index",
                f"artifacts/datasets/{repo}.index.json",
                "--taskset",
                args.taskset,
                "-o",
                str(cmp),
            ],
            cwd=str(root),
            check=True,
        )
        retrieval_paths.append(ret)
        comparison_paths.append(cmp)

    # baseline metrics
    base_final = _load_json(base_dir / "final_summary.json").get("overall", {})
    base_retrieval = _aggregate_retrieval_metrics([base_dir / f"retrieval_{r}.json" for r in REPOS])
    base_comp = _aggregate_comparison_agentretrieve([base_dir / f"comparison_{r}.json" for r in REPOS])

    # candidate metrics
    cand_final = _load_json(final_out / "final_summary.json").get("overall", {})
    cand_retrieval = _aggregate_retrieval_metrics(retrieval_paths)
    cand_comp = _aggregate_comparison_agentretrieve(comparison_paths)

    checks: list[dict] = []

    def add_check(name: str, b: float, c: float, abs_tol: float, rel_tol: float) -> None:
        abs_diff, rel_diff, ok = _diff_ok(b, c, abs_tol=abs_tol, rel_tol=rel_tol)
        checks.append(
            {
                "metric": name,
                "baseline": b,
                "cross_env": c,
                "abs_diff": abs_diff,
                "rel_diff": rel_diff,
                "abs_tol": abs_tol,
                "rel_tol": rel_tol,
                "ok": ok,
            }
        )

    add_check("final.recall", float(base_final.get("recall", 0.0)), float(cand_final.get("recall", 0.0)), abs_tol, 0.0)
    add_check("final.avg_mrr", float(base_final.get("avg_mrr", 0.0)), float(cand_final.get("avg_mrr", 0.0)), abs_tol, 0.0)
    add_check(
        "final.avg_latency_ms",
        float(base_final.get("avg_latency_ms", 0.0)),
        float(cand_final.get("avg_latency_ms", 0.0)),
        0.0,
        rel_latency_tol,
    )
    add_check("retrieval.recall", base_retrieval["recall"], cand_retrieval["recall"], abs_tol, 0.0)
    add_check("retrieval.mrr", base_retrieval["mrr"], cand_retrieval["mrr"], abs_tol, 0.0)
    add_check("comparison_ar.recall", base_comp["recall"], cand_comp["recall"], abs_tol, 0.0)
    add_check("comparison_ar.mrr", base_comp["mrr"], cand_comp["mrr"], abs_tol, 0.0)
    add_check(
        "comparison_ar.latency_ms_mean",
        base_comp["latency_ms_mean"],
        cand_comp["latency_ms_mean"],
        0.0,
        rel_latency_tol,
    )

    out = {
        "version": "cross_env_repro.v1",
        "run_id": args.run_id,
        "python_exec": py,
        "baseline": {
            "final": base_final,
            "retrieval": base_retrieval,
            "comparison_agentretrieve": base_comp,
        },
        "cross_env": {
            "final": cand_final,
            "retrieval": cand_retrieval,
            "comparison_agentretrieve": cand_comp,
        },
        "checks": checks,
        "all_passed": all(c["ok"] for c in checks),
    }
    output_name = "cross_env_repro_report"
    if args.output_suffix:
        output_name += f".{args.output_suffix}"
    out_path = cross_dir / f"{output_name}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(out_path)
    print(f"all_passed={out['all_passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
