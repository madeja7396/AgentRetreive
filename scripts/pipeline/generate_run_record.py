#!/usr/bin/env python3
"""Generate run_record v1/v2 and append run registries."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    if not path.exists():
        return "0" * 64
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _git_meta(root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
    )
    return commit, dirty


def _tool_version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, text=True, capture_output=True, check=True).stdout.strip()
    except Exception:
        return None
    return out.splitlines()[0] if out else None


def _environment_info() -> dict[str, Any]:
    cpu = platform.processor() or platform.machine()
    ram_gb = 0.0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = float(line.split()[1])
                    ram_gb = round(kb / (1024 * 1024), 2)
                    break
    except Exception:
        ram_gb = 0.0

    toolchain: dict[str, str] = {"python": platform.python_version()}
    pytest_ver = _tool_version(["pytest", "--version"])
    if pytest_ver:
        toolchain["pytest"] = pytest_ver
    return {
        "os": platform.platform(),
        "cpu": cpu,
        "ram_gb": ram_gb if ram_gb > 0 else 0.01,
        "toolchain": toolchain,
    }


def _read_existing_record(run_dir: Path) -> dict[str, Any] | None:
    for name in ("run_record.v2.json", "run_record.json"):
        p = run_dir / name
        if p.exists():
            try:
                return _load_json(p)
            except Exception:
                continue
    return None


def _rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


def _replace_registry_entry(path: Path, run_id: str, entry: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("run_id") == run_id:
                continue
            rows.append(obj)
    rows.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate run_record and update registries.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-id", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--config-path",
        default="artifacts/experiments/pipeline/generated_experiment_pipeline.final_raw.yaml",
    )
    parser.add_argument("--runs-root", default="artifacts/experiments/runs")
    parser.add_argument("--registry-root", default="artifacts/experiments")
    parser.add_argument("--notes", default="")
    parser.add_argument("--status", choices=["success", "partial", "failed"], default="")
    parser.add_argument(
        "--create-run-dir",
        action="store_true",
        help="Create run directory when missing",
    )
    parser.add_argument("--write-v1", action="store_true", default=True)
    parser.add_argument("--write-v2", action="store_true", default=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    run_dir = (root / args.runs_root / args.run_id).resolve()
    if not run_dir.exists():
        if args.create_run_dir:
            run_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise SystemExit(f"run directory not found: {run_dir}")

    config_path = (root / args.config_path).resolve()
    output_dir_from_config = config_path.parent
    summary_candidates = [
        run_dir / "final_summary.json",
        run_dir / "summary.json",  # backward compatibility
        output_dir_from_config / "final_summary.json",
        (root / "artifacts/experiments/pipeline/final_summary.json").resolve(),
    ]
    summary_path = next((p for p in summary_candidates if p.exists()), None)
    if summary_path is None:
        raise SystemExit("final_summary.json not found in run/output locations")
    summary = _load_json(summary_path)
    overall = summary.get("overall", {})

    e2e_path = run_dir / "e2e_metrics.json"
    e2e = _load_json(e2e_path) if e2e_path.exists() else {}
    ttfc = e2e.get("ttfc_ms", {})

    existing = _read_existing_record(run_dir)
    dataset_id = args.dataset_id or (existing or {}).get("dataset_id") or "ds_unknown"
    created_at = _utc_now()

    start_utc = created_at
    end_utc = created_at
    if existing:
        timing = existing.get("timing", {})
        start_utc = timing.get("start_utc", start_utc)
        end_utc = timing.get("end_utc", end_utc)
    elif (run_dir / "logs.txt").exists():
        mtime = datetime.fromtimestamp((run_dir / "logs.txt").stat().st_mtime, tz=UTC)
        end_utc = mtime.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    commit, dirty = _git_meta(root)

    metrics = {
        "mrr_at_10": float(overall.get("avg_mrr", 0.0)),
        "ndcg_at_10": 0.0,
        "recall_at_10": float(overall.get("recall", 0.0)),
        "tool_calls_per_task": float(e2e.get("tool_calls_per_task", 0.0)),
        "stdout_bytes_per_task": float(e2e.get("stdout_bytes_per_task", 0.0)),
        "ttfc_ms_p50": float(ttfc.get("p50", 0.0)),
        "ttfc_ms_p95": float(ttfc.get("p95", 0.0)),
        "ttfc_ms_p99": float(ttfc.get("p99", 0.0)),
        "avg_latency_ms": float(overall.get("avg_latency_ms", 0.0)),
    }

    status = args.status
    if not status:
        required = [summary_path.exists(), e2e_path.exists()]
        status = "success" if all(required) else "partial"

    logs_path = run_dir / "logs.txt"
    run_summary_path = run_dir / "RUN_SUMMARY.md"

    artifacts_v2: dict[str, str] = {
        "raw_metrics_path": _rel(summary_path, root),
        "logs_path": _rel(logs_path, root) if logs_path.exists() else _rel(run_dir, root),
        "summary_path": _rel(run_summary_path, root) if run_summary_path.exists() else _rel(run_dir, root),
        "retrieval_glob": _rel(run_dir / "retrieval_*.json", root),
        "comparison_glob": _rel(run_dir / "comparison_*.json", root),
    }
    optional_map = {
        "micro_path": run_dir / "micro_benchmark.json",
        "e2e_path": e2e_path,
        "ablation_path": run_dir / "ablation.json",
        "stability_path": run_dir / "stability.json",
    }
    for key, path in optional_map.items():
        if path.exists():
            artifacts_v2[key] = _rel(path, root)

    record_v2 = {
        "version": "run_record.v2",
        "run_id": args.run_id,
        "created_at_utc": created_at,
        "git": {"commit": commit, "dirty": dirty},
        "dataset_id": dataset_id,
        "config": {"path": _rel(config_path, root), "sha256": _sha256(config_path)},
        "seed": args.seed,
        "environment": _environment_info(),
        "timing": {"start_utc": start_utc, "end_utc": end_utc},
        "metrics": metrics,
        "artifacts": artifacts_v2,
        "status": status,
        "notes": args.notes or "Generated by scripts/pipeline/generate_run_record.py",
    }

    record_v1 = {
        "version": "run_record.v1",
        "run_id": args.run_id,
        "created_at_utc": created_at,
        "git": {"commit": commit, "dirty": dirty},
        "dataset_id": dataset_id,
        "config": {"path": _rel(config_path, root), "sha256": _sha256(config_path)},
        "seed": args.seed,
        "environment": record_v2["environment"],
        "timing": {"start_utc": start_utc, "end_utc": end_utc},
        "metrics": {
            "mrr_at_10": metrics["mrr_at_10"],
            "ndcg_at_10": metrics["ndcg_at_10"],
            "recall_at_10": metrics["recall_at_10"],
            "tool_calls_per_task": metrics["tool_calls_per_task"],
            "stdout_bytes_per_task": metrics["stdout_bytes_per_task"],
            "ttfc_ms_p50": metrics["ttfc_ms_p50"],
            "ttfc_ms_p95": metrics["ttfc_ms_p95"],
        },
        "artifacts": {
            "raw_metrics_path": artifacts_v2["raw_metrics_path"],
            "logs_path": artifacts_v2["logs_path"],
            "summary_path": artifacts_v2["summary_path"],
        },
        "status": status,
        "notes": record_v2["notes"],
    }

    if args.write_v2:
        v2_path = run_dir / "run_record.v2.json"
        v2_path.write_text(json.dumps(record_v2, ensure_ascii=False, indent=2), encoding="utf-8")
        _replace_registry_entry(
            (root / args.registry_root / "run_registry.v2.jsonl").resolve(),
            args.run_id,
            record_v2,
        )
        print(v2_path)
    if args.write_v1:
        v1_path = run_dir / "run_record.json"
        v1_path.write_text(json.dumps(record_v1, ensure_ascii=False, indent=2), encoding="utf-8")
        _replace_registry_entry(
            (root / args.registry_root / "run_registry.v1.jsonl").resolve(),
            args.run_id,
            record_v1,
        )
        print(v1_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
