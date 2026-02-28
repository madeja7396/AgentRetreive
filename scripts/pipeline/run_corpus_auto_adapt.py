#!/usr/bin/env python3
"""One-command automation: corpus sync, index build, model fitting, and parameter adaptation."""

from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from typing import Any

import yaml

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentretrieve.bench.corpus import Corpus, CorpusManager
from agentretrieve.index.inverted import InvertedIndex


_LANG_MAP: dict[str, str] = {
    "rust": "rust",
    "go": "go",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "haskell": "haskell",
    "elixir": "elixir",
    "php": "php",
    "ruby": "ruby",
    "kotlin": "kotlin",
    "swift": "swift",
    "dart": "dart",
}

_MAJOR_LANGS: set[str] = {
    "rust",
    "go",
    "c",
    "cpp",
    "csharp",
    "python",
    "javascript",
    "typescript",
    "java",
    "haskell",
    "elixir",
    "php",
    "ruby",
    "kotlin",
    "swift",
    "dart",
}

_SUFFIX_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".rs": "rust",
    ".go": "go",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".dart": "dart",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".ex": "elixir",
    ".exs": "elixir",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
}

_SKIP_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    ".venv",
    "venv",
}


@dataclass(frozen=True)
class CodeFile:
    rel_path: str
    lang: str
    size: int
    suffix: str
    depth: int


def _normalize_lang(value: str) -> str:
    return _LANG_MAP.get(value.strip().lower(), value.strip().lower())


def _load_taskset_repos(taskset_path: Path) -> set[str]:
    repos: set[str] = set()
    with taskset_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            repo = task.get("repo")
            if isinstance(repo, str) and repo:
                repos.add(repo)
    return repos


def _select_corpora(
    corpora: list[Corpus],
    repos_filter: set[str] | None,
    task_repos: set[str],
    index_all: bool,
) -> list[Corpus]:
    selected: list[Corpus] = []
    for corpus in corpora:
        if repos_filter is not None and corpus.id not in repos_filter:
            continue
        if repos_filter is None and not index_all and corpus.id not in task_repos:
            continue
        selected.append(corpus)
    return selected


def _build_index(source_root: Path, index_path: Path) -> dict[str, int]:
    idx = InvertedIndex()
    idx.source_root = str(source_root.resolve())

    indexed_files = 0
    skipped_files = 0
    read_errors = 0
    for root_dir, dirnames, filenames in os.walk(source_root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        root_path = Path(root_dir)
        for filename in filenames:
            path = root_path / filename
            lang = _SUFFIX_TO_LANG.get(path.suffix.lower())
            if lang is None:
                skipped_files += 1
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                read_errors += 1
                continue
            rel_path = str(path.relative_to(source_root)).replace("\\", "/")
            idx.add_document(rel_path, content, lang=lang)
            indexed_files += 1

    index_path.parent.mkdir(parents=True, exist_ok=True)
    idx.save(index_path)
    return {
        "indexed_files": indexed_files,
        "skipped_files": skipped_files,
        "read_errors": read_errors,
        "documents": idx.total_docs,
        "terms": len(idx.index),
    }


def _stable_key(path_str: str) -> str:
    return hashlib.sha256(path_str.encode("utf-8")).hexdigest()


def _scan_code_files(source_root: Path) -> list[CodeFile]:
    files: list[CodeFile] = []

    # Fast path: git object metadata includes file sizes without per-file stat calls.
    listed_tree = subprocess.run(
        ["git", "ls-tree", "-rl", "--long", "HEAD"],
        cwd=str(source_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if listed_tree.returncode == 0:
        for line in listed_tree.stdout.splitlines():
            if "\t" not in line:
                continue
            left, rel_path = line.split("\t", 1)
            parts = left.split()
            if len(parts) < 4:
                continue
            lang = _SUFFIX_TO_LANG.get(Path(rel_path).suffix.lower())
            if lang is None:
                continue
            try:
                size = int(parts[3])
            except Exception:
                continue
            normalized = rel_path.replace("\\", "/")
            depth = normalized.count("/")
            files.append(
                CodeFile(
                    rel_path=normalized,
                    lang=lang,
                    size=size,
                    suffix=Path(rel_path).suffix.lower(),
                    depth=depth,
                )
            )
        if files:
            return files

    # Fallback: git-indexed paths + stat for environments where ls-tree is unavailable.
    listed = subprocess.run(
        ["git", "ls-files"],
        cwd=str(source_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode == 0:
        for rel_path in listed.stdout.splitlines():
            rel_path = rel_path.strip()
            if not rel_path:
                continue
            path = source_root / rel_path
            lang = _SUFFIX_TO_LANG.get(path.suffix.lower())
            if lang is None:
                continue
            try:
                size = int(path.stat().st_size)
            except Exception:
                continue
            normalized = rel_path.replace("\\", "/")
            depth = normalized.count("/")
            files.append(
                CodeFile(
                    rel_path=normalized,
                    lang=lang,
                    size=size,
                    suffix=path.suffix.lower(),
                    depth=depth,
                )
            )
        return files

    for root_dir, dirnames, filenames in os.walk(source_root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        root_path = Path(root_dir)
        for filename in filenames:
            path = root_path / filename
            lang = _SUFFIX_TO_LANG.get(path.suffix.lower())
            if lang is None:
                continue
            try:
                size = int(path.stat().st_size)
            except Exception:
                continue
            rel_path = str(path.relative_to(source_root)).replace("\\", "/")
            depth = rel_path.count("/")
            files.append(
                CodeFile(
                    rel_path=rel_path,
                    lang=lang,
                    size=size,
                    suffix=path.suffix.lower(),
                    depth=depth,
                )
            )
    return files


def _zscore(value: float, values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    if variance <= 0:
        return 0.0
    return (value - mean) / (variance ** 0.5)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    clamped_q = min(1.0, max(0.0, q))
    idx = int(round(clamped_q * (len(sorted_values) - 1)))
    return float(sorted_values[idx])


def _shannon_entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _select_balanced_entries(
    entries: list[CodeFile],
    target_files: int,
    target_bytes: int,
) -> list[CodeFile]:
    if target_files <= 0:
        raise RuntimeError("target_files must be > 0")
    if len(entries) < target_files:
        raise RuntimeError(
            f"Cannot sample {target_files} files from repository with only {len(entries)} files"
        )

    stable_ranked = sorted(entries, key=lambda item: _stable_key(item.rel_path))
    if len(stable_ranked) == target_files:
        return stable_ranked

    # Statistical target per file: derive from corpus-level target bytes.
    target_per_file = float(target_bytes) / float(target_files)
    closest_ranked = sorted(
        stable_ranked,
        key=lambda item: (abs(float(item.size) - target_per_file), _stable_key(item.rel_path)),
    )
    selected = list(closest_ranked[:target_files])
    selected_paths = {item.rel_path for item in selected}
    unselected = [item for item in stable_ranked if item.rel_path not in selected_paths]
    current_bytes = sum(entry.size for entry in selected)
    best_diff = abs(current_bytes - target_bytes)
    if not unselected:
        return selected

    # Deterministic single-swap correction to reduce byte deviation.
    unselected_sorted = sorted(unselected, key=lambda item: (item.size, item.rel_path))
    unselected_sizes = [item.size for item in unselected_sorted]
    best_swap: tuple[int, CodeFile] | None = None
    for sel_idx, selected_entry in enumerate(selected):
        desired_size = target_bytes - (current_bytes - selected_entry.size)
        pos = bisect_left(unselected_sizes, desired_size)
        for candidate_pos in [pos - 1, pos, pos + 1]:
            if candidate_pos < 0 or candidate_pos >= len(unselected_sorted):
                continue
            candidate_entry = unselected_sorted[candidate_pos]
            candidate_bytes = current_bytes - selected_entry.size + candidate_entry.size
            candidate_diff = abs(candidate_bytes - target_bytes)
            if candidate_diff < best_diff:
                best_diff = candidate_diff
                best_swap = (sel_idx, candidate_entry)

    if best_swap is not None:
        sel_idx, candidate_entry = best_swap
        selected[sel_idx] = candidate_entry
    return sorted(selected, key=lambda item: _stable_key(item.rel_path))


def _prepare_balanced_views(
    root: Path,
    selected: list[Corpus],
    raw_source_dirs: dict[str, Path],
    balanced_root: Path,
) -> tuple[dict[str, Path], dict[str, Any], str]:
    profiles: dict[str, dict[str, Any]] = {}
    for corpus in selected:
        repo_id = corpus.id
        source_dir = raw_source_dirs[repo_id]
        print(f"[balance] scanning {repo_id}...")
        code_files = _scan_code_files(source_dir)
        if not code_files:
            raise RuntimeError(f"No supported code files found for corpus: {repo_id}")
        total_bytes = sum(item.size for item in code_files)
        lang_counter = Counter(item.lang for item in code_files)
        lang_diversity = len(lang_counter)
        suffix_diversity = len({item.suffix for item in code_files})
        path_depths = [item.depth for item in code_files]
        file_sizes = [item.size for item in code_files]
        avg_file_size = (total_bytes / len(file_sizes)) if file_sizes else 0.0
        file_size_cv = (
            statistics.pstdev(file_sizes) / avg_file_size
            if len(file_sizes) > 1 and avg_file_size > 0
            else 0.0
        )
        profiles[repo_id] = {
            "source": source_dir,
            "files": code_files,
            "code_file_count": len(code_files),
            "code_bytes": total_bytes,
            "language_diversity": lang_diversity,
            "extension_diversity": suffix_diversity,
            "language_entropy": _shannon_entropy(lang_counter),
            "path_depth_p90": _percentile([float(v) for v in path_depths], 0.9),
            "file_size_cv": file_size_cv,
        }
        print(
            f"[balance] scanned {repo_id}: files={len(code_files)} bytes={total_bytes} langs={lang_diversity}"
        )

    target_files = min(int(p["code_file_count"]) for p in profiles.values())
    if target_files <= 0:
        raise RuntimeError("Failed to derive balanced target files (target_files <= 0)")
    expected_bytes = [
        (float(p["code_bytes"]) / float(p["code_file_count"])) * float(target_files)
        for p in profiles.values()
    ]
    target_bytes = int(round(statistics.median(expected_bytes)))
    if target_bytes <= 0:
        raise RuntimeError("Failed to derive balanced target bytes (target_bytes <= 0)")

    if balanced_root.exists():
        shutil.rmtree(balanced_root)
    balanced_root.mkdir(parents=True, exist_ok=True)

    balanced_dirs: dict[str, Path] = {}
    raw_file_counts = [float(p["code_file_count"]) for p in profiles.values()]
    raw_sizes = [float(p["code_bytes"]) for p in profiles.values()]
    raw_log_file_counts = [math.log1p(v) for v in raw_file_counts]
    raw_log_sizes = [math.log1p(v) for v in raw_sizes]
    raw_diversity = [float(p["language_diversity"]) for p in profiles.values()]
    raw_extension_diversity = [float(p["extension_diversity"]) for p in profiles.values()]
    raw_entropy = [float(p["language_entropy"]) for p in profiles.values()]
    raw_depth_p90 = [float(p["path_depth_p90"]) for p in profiles.values()]
    raw_file_size_cv = [float(p["file_size_cv"]) for p in profiles.values()]

    balanced_stats: dict[str, Any] = {}
    for corpus in selected:
        repo_id = corpus.id
        profile = profiles[repo_id]
        source_dir = profile["source"]
        entries: list[CodeFile] = profile["files"]
        selected_entries = _select_balanced_entries(
            entries=entries,
            target_files=target_files,
            target_bytes=target_bytes,
        )

        out_dir = balanced_root / repo_id
        out_dir.mkdir(parents=True, exist_ok=True)
        selected_bytes = 0
        selected_lang_counter = Counter()
        for entry in selected_entries:
            src = source_dir / entry.rel_path
            dst = out_dir / entry.rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            selected_bytes += entry.size
            selected_lang_counter[entry.lang] += 1

        balanced_dirs[repo_id] = out_dir
        size_deviation_ratio = (
            abs(selected_bytes - target_bytes) / float(target_bytes)
            if target_bytes > 0
            else 0.0
        )
        balanced_stats[repo_id] = {
            "raw_code_files": int(profile["code_file_count"]),
            "raw_code_bytes": int(profile["code_bytes"]),
            "raw_language_diversity": int(profile["language_diversity"]),
            "balanced_code_files": len(selected_entries),
            "balanced_code_bytes": selected_bytes,
            "balanced_language_diversity": len(selected_lang_counter),
            "balanced_size_deviation_ratio": size_deviation_ratio,
        }

    complex_scores: dict[str, float] = {}
    for repo_id, profile in profiles.items():
        score = (
            _zscore(math.log1p(float(profile["code_file_count"])), raw_log_file_counts)
            + _zscore(math.log1p(float(profile["code_bytes"])), raw_log_sizes)
            + _zscore(float(profile["language_diversity"]), raw_diversity)
            + _zscore(float(profile["extension_diversity"]), raw_extension_diversity)
            + _zscore(float(profile["language_entropy"]), raw_entropy)
            + _zscore(float(profile["path_depth_p90"]), raw_depth_p90)
            + _zscore(float(profile["file_size_cv"]), raw_file_size_cv)
        )
        complex_scores[repo_id] = score
    complex_repo = max(complex_scores.items(), key=lambda kv: kv[1])[0]

    balanced_bytes = [int(v["balanced_code_bytes"]) for v in balanced_stats.values()]
    balanced_files = [int(v["balanced_code_files"]) for v in balanced_stats.values()]
    bytes_mean = statistics.mean(balanced_bytes) if balanced_bytes else 0.0
    files_mean = statistics.mean(balanced_files) if balanced_files else 0.0
    bytes_cv = (statistics.pstdev(balanced_bytes) / bytes_mean) if bytes_mean else 0.0
    files_cv = (statistics.pstdev(balanced_files) / files_mean) if files_mean else 0.0

    fairness_summary = {
        "method": "statistical_balancing_common_count_plus_median_target_bytes",
        "target_code_files_per_repo": int(target_files),
        "target_code_bytes_per_repo": int(target_bytes),
        "balanced_code_files_min": min(balanced_files),
        "balanced_code_files_max": max(balanced_files),
        "balanced_code_bytes_min": min(
            int(v["balanced_code_bytes"]) for v in balanced_stats.values()
        ),
        "balanced_code_bytes_max": max(
            int(v["balanced_code_bytes"]) for v in balanced_stats.values()
        ),
        "balanced_code_files_cv": files_cv,
        "balanced_code_bytes_cv": bytes_cv,
        "per_repo": balanced_stats,
        "complex_repo_selection": {
            "repo": complex_repo,
            "scores": complex_scores,
            "metrics": {
                "code_file_count": profiles[complex_repo]["code_file_count"],
                "code_bytes": profiles[complex_repo]["code_bytes"],
                "language_diversity": profiles[complex_repo]["language_diversity"],
                "extension_diversity": profiles[complex_repo]["extension_diversity"],
                "language_entropy": profiles[complex_repo]["language_entropy"],
                "path_depth_p90": profiles[complex_repo]["path_depth_p90"],
                "file_size_cv": profiles[complex_repo]["file_size_cv"],
            },
            "raw_source": str((raw_source_dirs[complex_repo]).relative_to(root)).replace("\\", "/"),
        },
    }
    return balanced_dirs, fairness_summary, complex_repo


def _run(cmd: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _as_config_path(path: Path, root: Path) -> str:
    if path.is_absolute() and path.is_relative_to(root):
        return str(path.relative_to(root)).replace("\\", "/")
    return str(path).replace("\\", "/")


def _build_pipeline_config(
    base_config: dict[str, Any],
    selected: list[Corpus],
    taskset_path: Path,
    source_paths: dict[str, str],
    index_paths: dict[str, str],
) -> dict[str, Any]:
    repos = []
    for corpus in selected:
        source_path = source_paths.get(corpus.id, f"artifacts/datasets/raw/{corpus.id}")
        index_path = index_paths.get(corpus.id, f"artifacts/datasets/{corpus.id}.index.json")
        repos.append(
            {
                "id": corpus.id,
                "language": _normalize_lang(corpus.primary_language),
                "index": index_path,
                "source": source_path,
            }
        )

    generated = dict(base_config)
    generated["repositories"] = repos
    tasksets = dict(generated.get("tasksets", {}))
    tasksets["v2_full"] = str(taskset_path)
    generated["tasksets"] = tasksets
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run corpus-added auto adaptation in one command.",
    )
    parser.add_argument(
        "--manifest",
        default="docs/benchmarks/corpus.v1.1.json",
        help="Corpus manifest JSON path",
    )
    parser.add_argument(
        "--taskset",
        default="docs/benchmarks/taskset.v2.full.jsonl",
        help="Taskset JSONL path",
    )
    parser.add_argument(
        "--base-config",
        default="configs/experiment_pipeline.yaml",
        help="Base pipeline config YAML path",
    )
    parser.add_argument(
        "--generated-config",
        default="artifacts/experiments/pipeline/generated_experiment_pipeline.auto.yaml",
        help="Generated pipeline config path",
    )
    parser.add_argument(
        "--symbol-weights-output",
        default="configs/symbol_language_weights.v1.json",
        help="Output path for learned symbol language weights",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/experiments/pipeline",
        help="Pipeline output directory",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Worker count for parameter search pipeline",
    )
    parser.add_argument(
        "--repos",
        default="",
        help="Optional comma-separated repo IDs to target",
    )
    parser.add_argument(
        "--index-all",
        action="store_true",
        help="Index all corpora in manifest (default: only repos used in taskset).",
    )
    parser.add_argument(
        "--no-balance",
        action="store_true",
        help="Disable statistical corpus balancing and use raw repositories directly.",
    )
    parser.add_argument(
        "--balanced-root",
        default="artifacts/datasets/balanced_raw",
        help="Balanced corpus root directory.",
    )
    parser.add_argument(
        "--raw-index-root",
        default="artifacts/datasets",
        help="Output root for raw indices (official evaluation).",
    )
    parser.add_argument(
        "--balanced-index-root",
        default="artifacts/datasets/balanced_index",
        help="Output root for balanced indices (parameter search).",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Skip corpus clone/update step.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip index rebuild step.",
    )
    parser.add_argument(
        "--skip-symbol-fit",
        action="store_true",
        help="Skip symbol language weight fitting.",
    )
    parser.add_argument(
        "--skip-parameter-search",
        action="store_true",
        help="Skip parameter adaptation (run_full_pipeline).",
    )
    parser.add_argument(
        "--allow-missing-major-languages",
        action="store_true",
        help="Allow manifest that does not cover all major languages.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without executing clone/index/fit/pipeline.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    manifest_path = (root / args.manifest).resolve()
    taskset_path = (root / args.taskset).resolve()
    base_config_path = (root / args.base_config).resolve()
    generated_config_path = (root / args.generated_config).resolve()
    symbol_output_path = (root / args.symbol_weights_output).resolve()
    output_dir = (root / args.output_dir).resolve()
    balanced_root = (root / args.balanced_root).resolve()
    raw_index_root = (root / args.raw_index_root).resolve()
    balanced_index_root = (root / args.balanced_index_root).resolve()

    manager = CorpusManager(root)
    corpora = manager.load_corpus_manifest(manifest_path)
    task_repos = _load_taskset_repos(taskset_path)

    repos_filter = (
        {r.strip() for r in args.repos.split(",") if r.strip()} if args.repos else None
    )
    selected = _select_corpora(
        corpora=corpora,
        repos_filter=repos_filter,
        task_repos=task_repos,
        index_all=args.index_all,
    )
    if not selected:
        raise RuntimeError("No corpora selected for processing.")
    selected_repo_ids = [c.id for c in selected]
    selected_with_tasks = sorted(set(selected_repo_ids) & task_repos)

    lang_coverage = {_normalize_lang(c.primary_language) for c in corpora}
    missing_major = sorted(_MAJOR_LANGS - lang_coverage)
    if missing_major and not args.allow_missing_major_languages:
        raise RuntimeError(
            "Manifest is missing major languages: "
            + ", ".join(missing_major)
            + " (pass --allow-missing-major-languages to override)"
        )

    print("=" * 80)
    print("CORPUS AUTO ADAPT PIPELINE")
    print("=" * 80)
    print(f"Manifest: {manifest_path}")
    print(f"Taskset: {taskset_path}")
    print(f"Selected repos: {selected_repo_ids}")
    print(f"Repos with tasks: {selected_with_tasks}")
    print(f"Generated config: {generated_config_path}")
    print(f"Missing major languages: {missing_major or 'none'}")

    index_stats: dict[str, dict[str, int]] = {}
    raw_index_stats: dict[str, dict[str, int]] = {}
    raw_source_dirs: dict[str, Path] = {
        corpus.id: root / f"artifacts/datasets/raw/{corpus.id}" for corpus in selected
    }
    source_dirs: dict[str, Path] = dict(raw_source_dirs)
    source_paths: dict[str, str] = {
        corpus.id: f"artifacts/datasets/raw/{corpus.id}" for corpus in selected
    }
    raw_index_abs_paths: dict[str, Path] = {
        corpus.id: raw_index_root / f"{corpus.id}.index.json" for corpus in selected
    }
    search_index_abs_paths: dict[str, Path] = dict(raw_index_abs_paths)
    fairness_summary: dict[str, Any] = {"enabled": not args.no_balance}
    complex_repo_id = ""
    index_mode = "raw_only" if args.no_balance else "balanced_search_raw_eval"

    if args.dry_run and not args.no_balance:
        for corpus in selected:
            source_paths[corpus.id] = f"artifacts/datasets/balanced_raw/{corpus.id}"
            search_index_abs_paths[corpus.id] = balanced_index_root / f"{corpus.id}.index.json"
        fairness_summary["planned"] = True

    if not args.skip_clone:
        for corpus in selected:
            repo_path = manager.clone_or_update_corpus(corpus)
            print(f"[clone] {corpus.id}: {repo_path}")

    if not args.no_balance and not args.dry_run:
        balanced_dirs, fairness_info, complex_repo_id = _prepare_balanced_views(
            root=root,
            selected=selected,
            raw_source_dirs=raw_source_dirs,
            balanced_root=balanced_root,
        )
        source_dirs = balanced_dirs
        for repo_id, path in balanced_dirs.items():
            source_paths[repo_id] = str(path.relative_to(root)).replace("\\", "/")
            search_index_abs_paths[repo_id] = balanced_index_root / f"{repo_id}.index.json"
        fairness_summary.update(fairness_info)
        print(
            f"[balance] target_files={fairness_info['target_code_files_per_repo']} "
            f"target_bytes={fairness_info['target_code_bytes_per_repo']} "
            f"balanced_bytes_range="
            f"{fairness_info['balanced_code_bytes_min']}..{fairness_info['balanced_code_bytes_max']}"
        )
        print(
            f"[balance] cv(files)={fairness_info['balanced_code_files_cv']:.4f} "
            f"cv(bytes)={fairness_info['balanced_code_bytes_cv']:.4f}"
        )
        print(f"[balance] complex_repo={complex_repo_id}")

    search_index_paths: dict[str, str] = {
        repo_id: _as_config_path(index_path, root)
        for repo_id, index_path in search_index_abs_paths.items()
    }
    raw_index_paths: dict[str, str] = {
        repo_id: _as_config_path(index_path, root)
        for repo_id, index_path in raw_index_abs_paths.items()
    }

    base_config = yaml.safe_load(base_config_path.read_text(encoding="utf-8"))
    generated_config = _build_pipeline_config(
        base_config=base_config,
        selected=selected,
        taskset_path=taskset_path,
        source_paths=source_paths,
        index_paths=search_index_paths,
    )
    generated_config_path.parent.mkdir(parents=True, exist_ok=True)
    generated_config_path.write_text(
        yaml.safe_dump(generated_config, sort_keys=False),
        encoding="utf-8",
    )

    if args.dry_run:
        return 0

    if not args.skip_index:
        for corpus in selected:
            source_dir = source_dirs[corpus.id]
            if not source_dir.exists():
                raise RuntimeError(f"Source directory not found: {source_dir}")
            index_path = search_index_abs_paths[corpus.id]
            stats = _build_index(source_dir, index_path)
            index_stats[corpus.id] = stats
            print(
                f"[index][search] {corpus.id}: docs={stats['documents']} terms={stats['terms']} files={stats['indexed_files']}"
            )

            raw_index_path = raw_index_abs_paths[corpus.id]
            raw_source_dir = raw_source_dirs[corpus.id]
            if raw_index_path != index_path:
                if not raw_source_dir.exists():
                    raise RuntimeError(f"Raw source directory not found: {raw_source_dir}")
                raw_stats = _build_index(raw_source_dir, raw_index_path)
                raw_index_stats[corpus.id] = raw_stats
                print(
                    f"[index][raw] {corpus.id}: docs={raw_stats['documents']} terms={raw_stats['terms']} files={raw_stats['indexed_files']}"
                )

    did_symbol_fit = False
    if not args.skip_symbol_fit:
        if selected_with_tasks:
            _run(
                [
                    "python3",
                    "scripts/benchmark/fit_symbol_language_weights.py",
                    "--config",
                    str(generated_config_path),
                    "--taskset",
                    str(taskset_path),
                    "--output",
                    str(symbol_output_path),
                ],
                cwd=root,
            )
            did_symbol_fit = True
        else:
            print("[fit] skipped: no selected repositories have taskset entries.")

    if not args.skip_parameter_search:
        output_dir.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "python3",
                "scripts/pipeline/run_full_pipeline.py",
                "-c",
                str(generated_config_path),
                "-o",
                str(output_dir),
                "-w",
                str(args.workers),
            ],
            cwd=root,
        )

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "taskset": str(taskset_path),
        "generated_config": str(generated_config_path),
        "selected_repos": [c.id for c in selected],
        "selected_repos_with_tasks": selected_with_tasks,
        "missing_major_languages": missing_major,
        "fairness": fairness_summary,
        "index_mode": index_mode,
        "search_index_paths": search_index_paths,
        "raw_index_paths": raw_index_paths,
        "complex_repo": complex_repo_id or None,
        "index_stats": index_stats,
        "raw_index_stats": raw_index_stats,
        "steps": {
            "clone": not args.skip_clone,
            "index": not args.skip_index,
            "fit_symbol_weights": did_symbol_fit,
            "parameter_search": not args.skip_parameter_search,
        },
    }
    summary_path = output_dir / "auto_adapt_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
