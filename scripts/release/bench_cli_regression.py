#!/usr/bin/env python3
"""Compare query latency between baseline and candidate CLI binaries."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def _run_checked(cmd: list[str], *, op: str) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
        raise RuntimeError(f"{op} failed: {detail}")
    return proc.stdout


def _prepare_fixture(root: Path, file_count: int = 160) -> Path:
    repo_dir = root / "fixture_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    for i in range(file_count):
        text = (
            f"# fixture {i}\n"
            "def alpha_parser_config():\n"
            "    retry_backoff = True\n"
            "    return 'alpha beta parser config'\n"
        )
        (repo_dir / f"module_{i:04d}.py").write_text(text, encoding="utf-8")
    return repo_dir


def _build_index(binary: Path, repo_dir: Path, index_path: Path) -> None:
    _run_checked(
        [
            str(binary),
            "ix",
            "build",
            "--dir",
            str(repo_dir),
            "--output",
            str(index_path),
            "--pattern",
            "*.py",
        ],
        op=f"index build ({binary.name})",
    )


def _measure_query_p50_ms(
    binary: Path,
    index_path: Path,
    *,
    warmup: int,
    iterations: int,
) -> float:
    timings_ms: list[float] = []
    cmd = [
        str(binary),
        "q",
        "--index",
        str(index_path),
        "--must",
        "alpha,parser",
        "--should",
        "config,retry",
        "--max-results",
        "20",
        "--max-hits",
        "5",
    ]

    for i in range(warmup + iterations):
        start = time.perf_counter()
        stdout = _run_checked(cmd, op=f"query ({binary.name})")
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid query output JSON ({binary.name}): {exc}") from exc
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise RuntimeError(f"unexpected query payload ({binary.name})")
        if i >= warmup:
            timings_ms.append(elapsed_ms)

    return statistics.median(timings_ms)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-bin", required=True)
    parser.add_argument("--candidate-bin", required=True)
    parser.add_argument("--allowed-regression-ratio", type=float, default=0.05)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=15)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    baseline_bin = Path(args.baseline_bin)
    candidate_bin = Path(args.candidate_bin)
    if not baseline_bin.exists():
        raise FileNotFoundError(f"baseline binary not found: {baseline_bin}")
    if not candidate_bin.exists():
        raise FileNotFoundError(f"candidate binary not found: {candidate_bin}")

    with tempfile.TemporaryDirectory(prefix="ar_cli_regress_") as td:
        root = Path(td)
        repo_dir = _prepare_fixture(root)
        baseline_index = root / "baseline.index.bin"
        candidate_index = root / "candidate.index.bin"

        _build_index(baseline_bin, repo_dir, baseline_index)
        _build_index(candidate_bin, repo_dir, candidate_index)

        baseline_p50 = _measure_query_p50_ms(
            baseline_bin,
            baseline_index,
            warmup=max(0, args.warmup),
            iterations=max(5, args.iterations),
        )
        candidate_p50 = _measure_query_p50_ms(
            candidate_bin,
            candidate_index,
            warmup=max(0, args.warmup),
            iterations=max(5, args.iterations),
        )

    regression_ratio = (candidate_p50 - baseline_p50) / baseline_p50 if baseline_p50 > 0 else 0.0
    passed = regression_ratio <= float(args.allowed_regression_ratio) + 1e-12
    report = {
        "baseline_bin": str(baseline_bin),
        "candidate_bin": str(candidate_bin),
        "baseline_p50_ms": baseline_p50,
        "candidate_p50_ms": candidate_p50,
        "regression_ratio": regression_ratio,
        "allowed_regression_ratio": float(args.allowed_regression_ratio),
        "pass": passed,
    }

    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")

    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
