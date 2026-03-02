#!/usr/bin/env python3
"""Build deterministic L1/L2/L3 benchmark tier manifest from taskset v2."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _tier(task: dict) -> str:
    dsl = task.get("query_dsl", {})
    near = dsl.get("near") or []
    symbol = dsl.get("symbol") or []
    if near:
        return "L3"
    if symbol:
        return "L2"
    return "L1"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--taskset", default="docs/benchmarks/taskset.v2.full.jsonl")
    p.add_argument("--output", default="artifacts/experiments/benchmark_tiers.v2.json")
    args = p.parse_args()

    taskset_path = Path(args.taskset).resolve()
    output_path = Path(args.output).resolve()

    tasks = _load_jsonl(taskset_path)
    tiers: dict[str, list[str]] = defaultdict(list)
    repo_counter: dict[str, Counter] = {"L1": Counter(), "L2": Counter(), "L3": Counter()}

    for task in tasks:
        tid = task.get("id", "")
        repo = task.get("repo", "unknown")
        t = _tier(task)
        tiers[t].append(tid)
        repo_counter[t][repo] += 1

    payload = {
        "version": "benchmark_tiers.v2",
        "taskset": str(taskset_path),
        "counts": {k: len(v) for k, v in tiers.items()},
        "tiers": {k: sorted(v) for k, v in tiers.items()},
        "repo_distribution": {k: dict(c) for k, c in repo_counter.items()},
        "rules": [
            "near present -> L3",
            "symbol present (without near) -> L2",
            "otherwise -> L1",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
