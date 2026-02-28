#!/usr/bin/env python3
"""Check whether taskset gold files are present in repository indices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _load_taskset(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (base_dir / path).resolve()


def _build_gold_by_repo(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_repo: dict[str, list[str]] = {}
    for task in tasks:
        repo = task.get("repo")
        gold = task.get("gold", {}).get("file")
        if not isinstance(repo, str) or not repo:
            continue
        if not isinstance(gold, str) or not gold:
            continue
        by_repo.setdefault(repo, []).append(gold)
    return by_repo


def _load_doc_paths(index_path: Path) -> set[str]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    docs = payload.get("documents", [])
    paths: set[str] = set()
    for doc in docs:
        path = doc.get("path")
        if isinstance(path, str) and path:
            paths.add(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate gold file coverage against configured indices."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Pipeline YAML config path",
    )
    parser.add_argument(
        "--taskset",
        default="",
        help="Optional taskset JSONL path (defaults to config.tasksets.v2_full)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output JSON path for the coverage summary",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config_root = config_path.parent
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    if args.taskset:
        taskset_path = _resolve_path(config_root, args.taskset)
    else:
        taskset_rel = config_data.get("tasksets", {}).get("v2_full")
        if not isinstance(taskset_rel, str) or not taskset_rel:
            raise SystemExit("taskset path is missing in config.tasksets.v2_full")
        taskset_path = _resolve_path(config_root, taskset_rel)

    tasks = _load_taskset(taskset_path)
    gold_by_repo = _build_gold_by_repo(tasks)

    config_repos = {
        item.get("id"): item
        for item in config_data.get("repositories", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    missing_repo_configs: list[str] = []
    missing_indices: list[str] = []
    per_repo: dict[str, Any] = {}
    all_missing_gold: dict[str, list[str]] = {}

    for repo_id in sorted(gold_by_repo.keys()):
        repo_entry = config_repos.get(repo_id)
        if repo_entry is None:
            missing_repo_configs.append(repo_id)
            continue

        raw_index = repo_entry.get("index")
        if not isinstance(raw_index, str) or not raw_index:
            missing_indices.append(repo_id)
            continue

        index_path = _resolve_path(config_root, raw_index)
        if not index_path.exists():
            missing_indices.append(repo_id)
            continue

        doc_paths = _load_doc_paths(index_path)
        gold_paths = gold_by_repo[repo_id]
        missing_gold_by_task = [g for g in gold_paths if g not in doc_paths]
        present_count = len(gold_paths) - len(missing_gold_by_task)
        missing_gold_unique = sorted(set(missing_gold_by_task))

        per_repo[repo_id] = {
            "index": str(index_path),
            "gold_total": len(gold_paths),
            "gold_present": present_count,
            "gold_missing": len(missing_gold_by_task),
            "gold_unique_total": len(set(gold_paths)),
            "index_documents": len(doc_paths),
            "sample_missing": missing_gold_unique[:5],
        }
        if missing_gold_by_task:
            all_missing_gold[repo_id] = missing_gold_unique

    coverage_ok = not (missing_repo_configs or missing_indices or all_missing_gold)
    summary = {
        "config": str(config_path),
        "taskset": str(taskset_path),
        "repositories_with_tasks": sorted(gold_by_repo.keys()),
        "missing_repo_configs": missing_repo_configs,
        "missing_indices": missing_indices,
        "per_repository": per_repo,
        "missing_gold": all_missing_gold,
        "coverage_ok": coverage_ok,
    }

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Coverage summary: {output_path}")

    print("gold coverage check")
    print(f"  config: {config_path}")
    print(f"  taskset: {taskset_path}")
    for repo_id in sorted(per_repo.keys()):
        row = per_repo[repo_id]
        print(
            f"  {repo_id}: present={row['gold_present']}/{row['gold_total']} "
            f"docs={row['index_documents']}"
        )

    if missing_repo_configs:
        print(f"missing repository config entries: {', '.join(missing_repo_configs)}")
    if missing_indices:
        print(f"missing index files: {', '.join(missing_indices)}")
    if all_missing_gold:
        for repo_id, missing in all_missing_gold.items():
            sample = ", ".join(missing[:3])
            print(f"{repo_id}: missing gold files ({len(missing)}), sample: {sample}")
        return 1
    if missing_repo_configs or missing_indices:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
