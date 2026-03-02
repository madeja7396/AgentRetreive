#!/usr/bin/env python3
"""Final evaluation across repositories with configurable selection strategy."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from agentretrieve.backends import SUPPORTED_ENGINES, create_backend, resolve_backend_name
from agentretrieve.index.tokenizer import tokenize_identifier


@dataclass(frozen=True)
class SearchConfig:
    k1: float = 1.2
    b: float = 0.75
    min_match_ratio: float = 0.5
    max_terms: int = 3


@dataclass(frozen=True)
class PathCandidate:
    path: str
    score: int


_COMPOUND_SUFFIXES = (
    "list",
    "config",
    "option",
    "error",
    "path",
    "url",
    "version",
    "main",
    "test",
    "type",
    "name",
    "file",
    "line",
    "data",
    "item",
)

_COMPOUND_PREFIXES = (
    "https",
    "http",
    "json",
    "yaml",
    "url",
    "api",
    "xml",
    "tls",
    "ssl",
    "tcp",
    "udp",
)

_CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".hh",
    ".go",
    ".rs",
    ".py",
    ".java",
    ".kt",
    ".swift",
    ".js",
    ".ts",
}

_NON_CODE_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".cmake",
    ".m4",
    ".in",
}

_TERM_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "http": ("client", "request"),
    "retry": ("backoff", "attempt"),
    "parse": ("parser", "glob", "token"),
    "completion": ("complete", "shell"),
    "config": ("cfg",),
    "auth": ("login", "credential", "token"),
}

_LOW_SIGNAL_PATH_SEGMENTS = (
    "/mock/",
    "/mocks/",
    "/stub/",
    "/stubs/",
    "/fixtures/",
    "/samples/",
)

_GENERATED_PATH_SEGMENTS = (
    "/generated/",
    "/gen/",
    "/vendor/",
    "/third_party/",
    "/third-party/",
)

_PATH_BONUS_WEIGHT = 250.0


def _split_compound_token(token: str) -> list[str]:
    for suffix in sorted(_COMPOUND_SUFFIXES, key=len, reverse=True):
        if not token.endswith(suffix):
            continue
        head = token[: -len(suffix)]
        if len(head) >= 3 and head.isalpha():
            return [head, suffix]
    for prefix in _COMPOUND_PREFIXES:
        if not token.startswith(prefix):
            continue
        tail = token[len(prefix) :]
        if len(tail) >= 3 and tail.isalpha():
            return [prefix, tail]
    return [token]


def _normalize_query_terms(query_terms: list[str], max_terms: int) -> list[str]:
    normalized: list[str] = []
    for raw in query_terms:
        for piece in re.findall(r"[A-Za-z0-9_]+", str(raw)):
            if not piece:
                continue
            base = piece.lower()
            parts = tokenize_identifier(piece)
            if parts == [base]:
                split = _split_compound_token(base)
                if split != [base]:
                    parts = split

            seen_piece: list[str] = []
            for part in parts:
                if part and part not in seen_piece:
                    seen_piece.append(part)

            for part in seen_piece[:2]:
                if part not in normalized:
                    normalized.append(part)
            if len(normalized) >= max(1, max_terms):
                return normalized[: max(1, max_terms)]
    return normalized[: max(1, max_terms)]


def _build_query_variants(
    normalized_terms: list[str], min_match_ratio: float
) -> list[tuple[list[str], list[str], int]]:
    if not normalized_terms:
        return [([], [], 0)]

    if len(normalized_terms) >= 2:
        split_point = max(1, int(len(normalized_terms) * (1 - min_match_ratio)))
        primary_must = normalized_terms[:split_point]
        primary_should = normalized_terms[split_point:]
        primary_min_match = 1 if primary_should else 0
    else:
        primary_must = normalized_terms
        primary_should = []
        primary_min_match = 0

    variants: list[tuple[list[str], list[str], int]] = [
        (primary_must, primary_should, primary_min_match),
    ]

    if primary_should and primary_min_match > 0:
        variants.append((primary_must, primary_should, 0))

    for must_count in range(len(primary_must) - 1, 0, -1):
        variants.append((normalized_terms[:must_count], normalized_terms[must_count:], 0))

    variants.append(([], normalized_terms, 0))

    unique: list[tuple[list[str], list[str], int]] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...], int]] = set()
    for must_terms, should_terms, min_match in variants:
        dedup_must: list[str] = []
        for term in must_terms:
            if term and term not in dedup_must:
                dedup_must.append(term)

        dedup_should: list[str] = []
        for term in should_terms:
            if term and term not in dedup_must and term not in dedup_should:
                dedup_should.append(term)

        key = (tuple(dedup_must), tuple(dedup_should), int(min_match))
        if key in seen:
            continue
        seen.add(key)
        unique.append((dedup_must, dedup_should, int(min_match)))

    return unique


def _expand_query_terms(query_terms: list[str], limit: int = 4) -> list[str]:
    expanded: list[str] = []
    for term in query_terms:
        for extra in _TERM_EXPANSIONS.get(term, ()):
            if extra not in query_terms and extra not in expanded:
                expanded.append(extra)
            if len(expanded) >= limit:
                return expanded
    return expanded


def _path_bonus(_repo_id: str, path: str, query_terms: list[str]) -> float:
    path_norm = path.lower()
    path_marked = f"/{path_norm}"
    base = Path(path).name.lower()
    stem = Path(path).stem.lower()
    ext = Path(path).suffix.lower()
    tokens = _path_tokens_from_relpath(path_norm)

    bonus = 0.0
    if path_norm.startswith("src/"):
        bonus += 0.24
    elif path_norm.startswith("internal/"):
        bonus += 0.10
    elif path_norm.startswith("crates/"):
        bonus += 0.14
    elif path_norm.startswith("include/"):
        bonus += 0.10
    elif path_norm.startswith("pkg/"):
        bonus += 0.12
    elif path_norm.startswith("api/"):
        bonus += 0.12
    elif path_norm.startswith("lib/"):
        bonus += 0.02
    if path_norm.startswith("api/"):
        bonus += 0.14
    if path_norm.startswith(
        (
            "doc/",
            "docs/",
            "test/",
            "tests/",
            "testing/",
            "examples/",
            "bench/",
            "benchmark/",
            "m4/",
            "cmake/",
            ".github/",
        )
    ):
        bonus -= 0.18
    if (
        "_test." in base
        or base.startswith("test_")
        or "-test." in base
        or ".test." in base
    ):
        bonus -= 0.25
    if any(segment in path_marked for segment in _LOW_SIGNAL_PATH_SEGMENTS):
        bonus -= 0.22
    if any(segment in path_marked for segment in _GENERATED_PATH_SEGMENTS):
        bonus -= 0.12
    if ext in _CODE_EXTENSIONS:
        bonus += 0.15
    if ext in _NON_CODE_EXTENSIONS:
        bonus -= 0.35

    for term in query_terms:
        if not term:
            continue
        if term in base:
            bonus += 0.09
        if term == stem:
            bonus += 0.22
        if term in tokens:
            bonus += 0.06
        elif any(term in tok or tok in term for tok in tokens):
            bonus += 0.03

    stem_parts = [part for part in re.split(r"[_\\-]", stem) if part]
    stem_match_count = sum(1 for term in query_terms if term in stem_parts or term == stem)
    if stem_match_count >= 2:
        bonus += 0.12
    elif stem_match_count == 1 and len(query_terms) <= 2:
        bonus += 0.04

    if "config" in query_terms:
        if "cfg" in stem or "cfg" in tokens:
            bonus += 0.14
        if ext in {".h", ".hpp", ".hh"}:
            bonus += 0.08
    if "auth" in query_terms:
        if any(term in stem for term in ("login", "credential", "token", "oauth")):
            bonus += 0.10
        if {"login", "credential", "token"} & tokens:
            bonus += 0.06
    if "main" in query_terms and (
        stem == "main" or stem.startswith("main_") or stem.endswith("_main")
    ):
        bonus += 0.10

    if len(query_terms) >= 3:
        if len(stem) >= 10:
            bonus += 0.12
        elif len(stem) <= 4:
            bonus -= 0.08
        if "_" in stem or "-" in stem:
            bonus += 0.05
        if stem_match_count <= 1 and len(stem_parts) == 1:
            bonus -= 0.15

    return bonus


def _rerank_results(repo_id: str, query_terms: list[str], results: list[Any]) -> list[Any]:
    ranked: list[tuple[float, int, Any]] = []
    for idx, item in enumerate(results):
        raw_score = float(getattr(item, "score", 0.0))
        adjusted = raw_score + (_path_bonus(repo_id, item.path, query_terms) * _PATH_BONUS_WEIGHT)
        ranked.append((-adjusted, idx, item))
    ranked.sort()
    return [item for _, _, item in ranked]


def _path_tokens_from_relpath(rel_path: str) -> set[str]:
    tokens: set[str] = set()
    parts = re.split(r"[\\/._\\-]", rel_path.lower())
    for part in parts:
        if not part:
            continue
        tokens.add(part)
        ident_parts = tokenize_identifier(part)
        if ident_parts:
            tokens.update(ident_parts)
        split_parts = _split_compound_token(part)
        tokens.update(split_parts)
    return {t for t in tokens if t}


def _collect_code_paths(source_root: Path) -> list[tuple[str, set[str]]]:
    rows: list[tuple[str, set[str]]] = []
    skip_dirs = {
        ".git",
        ".hg",
        ".svn",
        "target",
        "node_modules",
        ".venv",
        "artifacts",
        "vendor",
        "third_party",
        "dist",
        "build",
        "out",
    }
    if not source_root.exists():
        return rows
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(source_root)).replace("\\", "/")
        parts = set(rel.split("/"))
        if parts & skip_dirs:
            continue
        rows.append((rel, _path_tokens_from_relpath(rel)))
    return rows


def _score_path_match(query_terms: list[str], path_tokens: set[str]) -> float:
    score = 0.0
    for term in query_terms:
        if term in path_tokens:
            score += 2.0
            continue
        for token in path_tokens:
            if term in token or token in term:
                score += 0.8
                break
    return score


def _path_fallback_candidates(
    repo_id: str,
    query_terms: list[str],
    source_rows: list[tuple[str, set[str]]],
    limit: int = 30,
) -> list[PathCandidate]:
    scored: list[tuple[float, str]] = []
    for rel_path, tokens in source_rows:
        path_score = _score_path_match(query_terms, tokens)
        if path_score <= 0.0:
            continue
        adjusted = path_score + (_path_bonus(repo_id, rel_path, query_terms) * 10.0)
        if adjusted <= 0.0:
            continue
        scored.append((adjusted, rel_path))

    scored.sort(key=lambda item: (-item[0], item[1]))
    candidates: list[PathCandidate] = []
    score_scale = 20.0
    for score, rel_path in scored[:limit]:
        candidates.append(PathCandidate(path=rel_path, score=int(score * score_scale)))
    return candidates


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _config_key(config: SearchConfig) -> tuple[float, float, float, int]:
    return (
        round(float(config.k1), 6),
        round(float(config.b), 6),
        round(float(config.min_match_ratio), 6),
        int(config.max_terms),
    )


def _config_payload(config: SearchConfig | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(config, SearchConfig):
        return asdict(config)
    if isinstance(config, dict):
        return dict(config)
    return {}


def _load_optimal_configs(path: Path) -> dict[str, SearchConfig]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw_optimal = payload.get("optimal_configs")
    if not isinstance(raw_optimal, dict):
        return {}

    parsed: dict[str, SearchConfig] = {}
    for repo_id, raw in raw_optimal.items():
        if not isinstance(repo_id, str) or not isinstance(raw, dict):
            continue
        parsed[repo_id] = SearchConfig(
            k1=_coerce_float(raw.get("k1"), 1.2),
            b=_coerce_float(raw.get("b"), 0.75),
            min_match_ratio=_coerce_float(raw.get("min_match_ratio"), 0.5),
            max_terms=max(1, _coerce_int(raw.get("max_terms"), 3)),
        )
    return parsed


def _fuse_candidate_results(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    rrf_k: int = 60,
) -> dict[str, Any]:
    second_by_id = {row["task_id"]: row for row in secondary.get("task_results", [])}
    fused_tasks: list[dict[str, Any]] = []
    latencies: list[float] = []

    for row in primary.get("task_results", []):
        task_id = row["task_id"]
        other = second_by_id.get(task_id, {})

        list_a = list(row.get("top_paths", []))
        list_b = list(other.get("top_paths", []))
        scores: dict[str, float] = {}
        for arr in (list_a, list_b):
            for idx, path in enumerate(arr, start=1):
                scores[path] = scores.get(path, 0.0) + (1.0 / (rrf_k + idx))
        fused_paths = [
            path for path, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ][:10]

        gold_file = str(row.get("gold_file", ""))
        rank = next((i + 1 for i, path in enumerate(fused_paths) if gold_file in path), None)

        latency = float(row.get("latency_ms", 0.0)) + float(other.get("latency_ms", 0.0))
        latencies.append(latency)
        fused_tasks.append(
            {
                "task_id": task_id,
                "difficulty": row.get("difficulty", "unknown"),
                "task_type": row.get("task_type", "unknown"),
                "found": rank is not None,
                "rank": rank,
                "latency_ms": latency,
                "result_count": len(fused_paths),
                "query_terms": row.get("query_terms", []),
                "search_variant": "fusion_rrf",
                "gold_file": gold_file,
                "top_paths": fused_paths,
            }
        )

    total = len(fused_tasks)
    found = sum(1 for row in fused_tasks if row["found"])
    ranks = [row["rank"] for row in fused_tasks if row["rank"]]
    mrr = sum(1.0 / rank for rank in ranks) / total if total else 0.0

    diff_metrics: dict[str, dict[str, Any]] = {}
    for diff in ["easy", "medium", "hard"]:
        diff_tasks = [row for row in fused_tasks if row["difficulty"] == diff]
        if diff_tasks:
            d_found = sum(1 for row in diff_tasks if row["found"])
            d_mrr = sum(1.0 / row["rank"] for row in diff_tasks if row["rank"]) / len(diff_tasks)
            diff_metrics[diff] = {
                "count": len(diff_tasks),
                "found": d_found,
                "recall": d_found / len(diff_tasks),
                "mrr": d_mrr,
            }

    type_metrics: dict[str, dict[str, Any]] = {}
    type_names = sorted({row["task_type"] for row in fused_tasks})
    for task_type in type_names:
        task_rows = [row for row in fused_tasks if row["task_type"] == task_type]
        found_rows = sum(1 for row in task_rows if row["found"])
        type_metrics[task_type] = {
            "count": len(task_rows),
            "found": found_rows,
            "recall": found_rows / len(task_rows),
        }

    return {
        "repo": primary.get("repo", secondary.get("repo", "")),
        "config": {"mode": "fusion_rrf", "rrf_k": rrf_k},
        "total": total,
        "found": found,
        "recall": (found / total) if total else 0.0,
        "mrr": mrr,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
        "by_difficulty": diff_metrics,
        "by_task_type": type_metrics,
        "task_results": fused_tasks,
    }


def evaluate_repository(
    repo_id: str,
    idx: Any,
    tasks: list[dict[str, Any]],
    config: SearchConfig,
    backend: Any,
    source_rows: list[tuple[str, set[str]]] | None = None,
    *,
    max_variants: int = 8,
    max_results_per_variant: int = 200,
    merge_stop_threshold: int = 120,
    fallback_trigger_size: int = 60,
    fallback_limit: int = 120,
) -> dict[str, Any]:
    """Evaluate one repository with one configuration."""
    backend.set_bm25(idx, k1=config.k1, b=config.b)

    results: list[dict[str, Any]] = []
    latencies: list[float] = []

    for task in tasks:
        query_terms = task["query_dsl"]["must"]
        gold_file = task["gold"]["file"]
        difficulty = task["difficulty"]
        task_type = task.get("type", "unknown")

        normalized = _normalize_query_terms(query_terms, config.max_terms)
        expanded_terms = _expand_query_terms(normalized, limit=4)
        variants = _build_query_variants(normalized, config.min_match_ratio)
        rerank_terms = normalized + [t for t in expanded_terms if t not in normalized]

        merged_by_path: dict[str, PathCandidate] = {}
        selected_variant = "none"
        start = time.perf_counter()
        for variant_idx, (must_terms, should_terms, min_match) in enumerate(variants):
            if variant_idx >= max_variants:
                break
            merged_should = should_terms + [
                t for t in expanded_terms if t not in must_terms and t not in should_terms
            ]
            ar_results = backend.search(
                idx,
                must=must_terms,
                should=merged_should,
                not_terms=[],
                max_results=max_results_per_variant,
                max_hits=3,
                min_match=min_match,
            )
            if ar_results and selected_variant == "none":
                selected_variant = f"variant_{variant_idx}"
            # Relaxed variants are fallback paths; keep them, but down-weight to avoid
            # overwhelming strict matches with broad lexical hits.
            variant_penalty = float(variant_idx) * 60.0
            for item in ar_results:
                candidate_score = float(getattr(item, "score", 0.0)) - variant_penalty
                existing = merged_by_path.get(item.path)
                if existing is None or candidate_score > float(getattr(existing, "score", 0.0)):
                    merged_by_path[item.path] = PathCandidate(
                        path=item.path,
                        score=int(round(candidate_score)),
                    )
            if variant_idx >= 1 and len(merged_by_path) >= merge_stop_threshold:
                break

        if source_rows and len(merged_by_path) <= fallback_trigger_size:
            for candidate in _path_fallback_candidates(
                repo_id,
                rerank_terms,
                source_rows,
                limit=fallback_limit,
            ):
                if candidate.path not in merged_by_path:
                    merged_by_path[candidate.path] = candidate
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)

        merged_results = list(merged_by_path.values())
        ar_results = _rerank_results(repo_id, rerank_terms, merged_results)[:10]
        rank = next((i + 1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
        results.append(
            {
                "task_id": task["id"],
                "difficulty": difficulty,
                "task_type": task_type,
                "found": rank is not None,
                "rank": rank,
                "latency_ms": elapsed,
                "result_count": len(ar_results),
                "query_terms": normalized,
                "search_variant": selected_variant,
                "gold_file": gold_file,
                "top_paths": [str(item.path) for item in ar_results],
            }
        )

    total = len(results)
    found = sum(1 for r in results if r["found"])
    ranks = [r["rank"] for r in results if r["rank"]]
    mrr = sum(1.0 / r for r in ranks) / total if total else 0.0

    diff_metrics: dict[str, dict[str, Any]] = {}
    for diff in ["easy", "medium", "hard"]:
        diff_tasks = [r for r in results if r["difficulty"] == diff]
        if diff_tasks:
            d_found = sum(1 for r in diff_tasks if r["found"])
            d_mrr = sum(1.0 / r["rank"] for r in diff_tasks if r["rank"]) / len(diff_tasks)
            diff_metrics[diff] = {
                "count": len(diff_tasks),
                "found": d_found,
                "recall": d_found / len(diff_tasks),
                "mrr": d_mrr,
            }

    type_metrics: dict[str, dict[str, Any]] = {}
    type_names = sorted({r["task_type"] for r in results})
    for task_type in type_names:
        task_rows = [r for r in results if r["task_type"] == task_type]
        found_rows = sum(1 for r in task_rows if r["found"])
        type_metrics[task_type] = {
            "count": len(task_rows),
            "found": found_rows,
            "recall": found_rows / len(task_rows),
        }

    return {
        "repo": repo_id,
        "config": asdict(config),
        "total": total,
        "found": found,
        "recall": (found / total) if total else 0.0,
        "mrr": mrr,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
        "by_difficulty": diff_metrics,
        "by_task_type": type_metrics,
        "task_results": results,
    }


def _resolve_repo_index_path(repo_config: dict[str, Any], engine_backend: str) -> Path:
    if engine_backend == "rust":
        raw_rust = repo_config.get("index_rust")
        if isinstance(raw_rust, str) and raw_rust:
            rust_path = Path(raw_rust)
            if rust_path.exists():
                return rust_path
    raw = repo_config.get("index")
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"Repository index path is missing: {repo_config.get('id', 'unknown')}")
    return Path(raw)


def _resolve_repo_source_path(repo_config: dict[str, Any], project_root: Path) -> Path | None:
    raw = repo_config.get("source")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def _result_score(result: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(result.get("recall", 0.0)),
        float(result.get("mrr", 0.0)),
        -float(result.get("avg_latency_ms", 0.0)),
    )


def _select_candidate(
    candidate_results: list[tuple[str, SearchConfig | dict[str, Any], dict[str, Any]]],
    *,
    policy: str,
    target_recall: float,
    target_mrr: float,
) -> tuple[str, SearchConfig | dict[str, Any], dict[str, Any]]:
    if not candidate_results:
        raise ValueError("candidate_results must not be empty")

    if len(candidate_results) == 1:
        return candidate_results[0]

    if policy == "latency-first-sota":
        sota_ready = [
            item
            for item in candidate_results
            if float(item[2].get("recall", 0.0)) + 1e-12 >= target_recall
            and float(item[2].get("mrr", 0.0)) + 1e-12 >= target_mrr
        ]
        if sota_ready:
            return min(
                sota_ready,
                key=lambda item: (
                    float(item[2].get("avg_latency_ms", float("inf"))),
                    -float(item[2].get("mrr", 0.0)),
                    -float(item[2].get("recall", 0.0)),
                    str(item[0]),
                ),
            )

    return max(candidate_results, key=lambda item: _result_score(item[2]))


def _parse_repos(raw: str) -> set[str] | None:
    repos = {part.strip() for part in raw.split(",") if part.strip()}
    return repos or None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_summary_payload(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _summary_recall(summary: dict[str, Any], section: str, key: str) -> float:
    section_payload = summary.get(section, {})
    if not isinstance(section_payload, dict):
        return 0.0
    metric_payload = section_payload.get(key, {})
    if not isinstance(metric_payload, dict):
        return 0.0
    return _safe_float(metric_payload.get("recall"), 0.0)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    default_engine = resolve_backend_name(os.environ.get("AR_ENGINE"))
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="configs/experiment_pipeline.yaml")
    parser.add_argument("-o", "--output", default="artifacts/experiments/pipeline")
    parser.add_argument(
        "--engine",
        choices=list(SUPPORTED_ENGINES),
        default=default_engine,
        help="Retrieval backend engine",
    )
    parser.add_argument("--repos", default="", help="Optional comma-separated repo IDs")
    parser.add_argument(
        "--config-strategy",
        choices=["fixed", "aggregate", "best-of-both"],
        default="fixed",
        help="Config selection strategy for each repository",
    )
    parser.add_argument(
        "--selection-policy",
        choices=["quality-first", "latency-first-sota"],
        default="quality-first",
        help=(
            "Candidate selection policy. quality-first keeps highest recall/mrr; "
            "latency-first-sota prefers fastest candidate that satisfies target recall/mrr."
        ),
    )
    parser.add_argument(
        "--aggregate-results",
        default="",
        help="Path to aggregate_results.json (default: <output>/aggregate_results.json)",
    )
    parser.add_argument("--default-k1", type=float, default=1.2)
    parser.add_argument("--default-b", type=float, default=0.75)
    parser.add_argument("--default-min-match-ratio", type=float, default=0.5)
    parser.add_argument("--default-max-terms", type=int, default=3)
    parser.add_argument(
        "--max-results-per-variant",
        type=int,
        default=200,
        help="Max candidate results retrieved per query variant",
    )
    parser.add_argument(
        "--max-variants",
        type=int,
        default=8,
        help="Max relaxed query variants evaluated per task",
    )
    parser.add_argument(
        "--merge-stop-threshold",
        type=int,
        default=120,
        help="Stop relaxed variant expansion once merged candidates reach this size",
    )
    parser.add_argument(
        "--fallback-trigger-size",
        type=int,
        default=60,
        help="Inject path fallback candidates when merged pool size is at or below this threshold",
    )
    parser.add_argument(
        "--fallback-limit",
        type=int,
        default=120,
        help="Max path fallback candidates injected per task",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=1.0,
        help="SOTA target threshold for recall",
    )
    parser.add_argument(
        "--target-mrr",
        type=float,
        default=0.5,
        help="SOTA target threshold for MRR",
    )
    parser.add_argument(
        "--guard-reference-summary",
        default="",
        help="Optional reference final_summary.json for anti-false-opt guard",
    )
    parser.add_argument(
        "--guard-max-mrr-drop",
        type=float,
        default=0.08,
        help="Maximum allowed overall MRR drop vs reference summary",
    )
    parser.add_argument(
        "--guard-require-hard-recall",
        type=float,
        default=1.0,
        help="Minimum hard difficulty recall required by anti-false-opt guard",
    )
    parser.add_argument(
        "--guard-require-usage-recall",
        type=float,
        default=1.0,
        help="Minimum usage_search recall required by anti-false-opt guard",
    )
    parser.add_argument(
        "--guard-strict",
        action="store_true",
        help="Fail with non-zero exit when anti-false-opt guard is violated",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    taskset_path = config["tasksets"]["v2_full"]
    with open(taskset_path, encoding="utf-8") as f:
        all_tasks = [json.loads(l) for l in f if l.strip()]

    default_config = SearchConfig(
        k1=args.default_k1,
        b=args.default_b,
        min_match_ratio=args.default_min_match_ratio,
        max_terms=max(1, args.default_max_terms),
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregate_path = (
        Path(args.aggregate_results)
        if args.aggregate_results
        else (output_dir / "aggregate_results.json")
    )
    aggregate_configs = (
        _load_optimal_configs(aggregate_path) if args.config_strategy != "fixed" else {}
    )
    repos_filter = _parse_repos(args.repos)

    print("=" * 80)
    print("FINAL EVALUATION - ALL REPOSITORIES")
    print("=" * 80)
    print(f"Engine: {args.engine}")
    print(f"Config strategy: {args.config_strategy}")
    print(f"Selection policy: {args.selection_policy}")
    print(
        "Default config: "
        f"k1={default_config.k1}, b={default_config.b}, "
        f"min_match={default_config.min_match_ratio}, max_terms={default_config.max_terms}"
    )
    print(
        "Search budget: "
        f"max_variants={args.max_variants}, "
        f"max_results={args.max_results_per_variant}, "
        f"merge_stop={args.merge_stop_threshold}, "
        f"fallback_trigger={args.fallback_trigger_size}, "
        f"fallback_limit={args.fallback_limit}"
    )
    if args.guard_reference_summary:
        print(
            "Anti-false-opt guard: "
            f"reference={args.guard_reference_summary}, "
            f"max_mrr_drop={args.guard_max_mrr_drop:.3f}, "
            f"hard_recall>={args.guard_require_hard_recall:.3f}, "
            f"usage_recall>={args.guard_require_usage_recall:.3f}, "
            f"strict={args.guard_strict}"
        )
    if args.config_strategy != "fixed":
        print(
            f"Aggregate source: {aggregate_path} "
            f"(loaded={len(aggregate_configs)} repos)"
        )
    print(f"SOTA target: recall>={args.target_recall:.3f}, mrr>={args.target_mrr:.3f}")

    backend = create_backend(args.engine)
    all_results: dict[str, dict[str, Any]] = {}
    per_repo_status: dict[str, dict[str, Any]] = {}

    for repo_config in config["repositories"]:
        repo_id = repo_config["id"]
        if repos_filter is not None and repo_id not in repos_filter:
            continue
        index_path = _resolve_repo_index_path(repo_config, args.engine)

        if not index_path.exists():
            print(f"\n{repo_id}: Index not found, skipping")
            continue

        repo_tasks = [t for t in all_tasks if t["repo"] == repo_id]
        if not repo_tasks:
            continue

        print(f"\n{repo_id:12s}: ", end="", flush=True)
        idx = backend.load_index(index_path)
        source_path = _resolve_repo_source_path(repo_config, project_root)
        source_rows = _collect_code_paths(source_path) if source_path is not None else []

        candidates: list[tuple[str, SearchConfig]] = []
        if args.config_strategy == "fixed":
            candidates = [("fixed", default_config)]
        elif args.config_strategy == "aggregate":
            aggregate_config = aggregate_configs.get(repo_id)
            if aggregate_config is not None:
                candidates = [("aggregate", aggregate_config)]
            else:
                candidates = [("fixed_fallback", default_config)]
        else:
            candidates = [("fixed", default_config)]
            aggregate_config = aggregate_configs.get(repo_id)
            if aggregate_config is not None:
                candidates.append(("aggregate", aggregate_config))

        unique_candidates: list[tuple[str, SearchConfig]] = []
        seen_keys: set[tuple[float, float, float, int]] = set()
        for label, cfg in candidates:
            cfg_key = _config_key(cfg)
            if cfg_key in seen_keys:
                continue
            seen_keys.add(cfg_key)
            unique_candidates.append((label, cfg))

        candidate_results: list[tuple[str, SearchConfig | dict[str, Any], dict[str, Any]]] = []
        for label, cfg in unique_candidates:
            evaluated = evaluate_repository(
                repo_id=repo_id,
                idx=idx,
                tasks=repo_tasks,
                config=cfg,
                backend=backend,
                source_rows=source_rows,
                max_variants=max(1, args.max_variants),
                max_results_per_variant=max(10, args.max_results_per_variant),
                merge_stop_threshold=max(20, args.merge_stop_threshold),
                fallback_trigger_size=max(0, args.fallback_trigger_size),
                fallback_limit=max(0, args.fallback_limit),
            )
            candidate_results.append((label, cfg, evaluated))

        if (
            args.config_strategy == "best-of-both"
            and len(candidate_results) >= 2
        ):
            first = candidate_results[0][2]
            second = candidate_results[1][2]
            fused = _fuse_candidate_results(first, second, rrf_k=60)
            candidate_results.append(
                ("fusion", {"mode": "fusion_rrf", "rrf_k": 60}, fused)
            )

        selected = _select_candidate(
            candidate_results,
            policy=args.selection_policy,
            target_recall=args.target_recall,
            target_mrr=args.target_mrr,
        )

        selected_label, selected_config, result = selected
        result["selection"] = {
            "strategy": args.config_strategy,
            "policy": args.selection_policy,
            "selected": selected_label,
            "candidates": [
                {
                    "label": label,
                    "config": _config_payload(cfg),
                    "recall": candidate["recall"],
                    "mrr": candidate["mrr"],
                    "latency_ms": candidate["avg_latency_ms"],
                }
                for label, cfg, candidate in candidate_results
            ],
        }
        all_results[repo_id] = result

        recall_gap = max(0.0, args.target_recall - result["recall"])
        mrr_gap = max(0.0, args.target_mrr - result["mrr"])
        per_repo_status[repo_id] = {
            "status": "sota_ready"
            if recall_gap <= 1e-12 and mrr_gap <= 1e-12
            else "needs_improvement",
            "recall_gap": recall_gap,
            "mrr_gap": mrr_gap,
            "selected": selected_label,
            "selected_config": _config_payload(selected_config),
        }

        print(
            f"Recall={result['recall']:.1%} MRR={result['mrr']:.3f} "
            f"Latency={result['avg_latency_ms']:.1f}ms "
            f"[{selected_label}]"
        )

        with open(output_dir / f"{repo_id}_final.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    valid = [r for r in all_results.values()]
    total_tasks = sum(r["total"] for r in valid)
    total_found = sum(r["found"] for r in valid)
    overall_recall = (total_found / total_tasks) if total_tasks else 0.0
    avg_mrr = (sum(r["mrr"] for r in valid) / len(valid)) if valid else 0.0
    avg_latency = (sum(r["avg_latency_ms"] for r in valid) / len(valid)) if valid else 0.0

    diff_totals: dict[str, list[int]] = {"easy": [0, 0], "medium": [0, 0], "hard": [0, 0]}
    for result in valid:
        for diff, metrics in result["by_difficulty"].items():
            diff_totals[diff][0] += metrics["found"]
            diff_totals[diff][1] += metrics["count"]

    type_totals: dict[str, list[int]] = {}
    for result in valid:
        for task_type, metrics in result["by_task_type"].items():
            if task_type not in type_totals:
                type_totals[task_type] = [0, 0]
            type_totals[task_type][0] += metrics["found"]
            type_totals[task_type][1] += metrics["count"]

    per_repo_summary: dict[str, dict[str, Any]] = {}
    for repo_id, result in all_results.items():
        status = per_repo_status.get(repo_id, {})
        per_repo_summary[repo_id] = {
            "recall": result["recall"],
            "mrr": result["mrr"],
            "latency_ms": result["avg_latency_ms"],
            "status": status.get("status", "unknown"),
            "recall_gap": status.get("recall_gap", 0.0),
            "mrr_gap": status.get("mrr_gap", 0.0),
            "selected": status.get("selected", "fixed"),
            "selected_config": status.get("selected_config", result.get("config", {})),
        }

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "engine": args.engine,
        "config": {
            "k1": default_config.k1,
            "b": default_config.b,
            "min_match_ratio": default_config.min_match_ratio,
            "max_terms": default_config.max_terms,
            "strategy": args.config_strategy,
            "selection_policy": args.selection_policy,
            "search_budget": {
                "max_variants": int(max(1, args.max_variants)),
                "max_results_per_variant": int(max(10, args.max_results_per_variant)),
                "merge_stop_threshold": int(max(20, args.merge_stop_threshold)),
                "fallback_trigger_size": int(max(0, args.fallback_trigger_size)),
                "fallback_limit": int(max(0, args.fallback_limit)),
            },
            "aggregate_results": str(aggregate_path) if aggregate_configs else "",
        },
        "targets": {
            "recall": args.target_recall,
            "mrr": args.target_mrr,
        },
        "overall": {
            "repositories": len(all_results),
            "total_tasks": total_tasks,
            "found": total_found,
            "recall": overall_recall,
            "avg_mrr": avg_mrr,
            "avg_latency_ms": avg_latency,
        },
        "by_difficulty": {
            diff: {"found": found, "total": total, "recall": found / total}
            for diff, (found, total) in diff_totals.items()
            if total > 0
        },
        "by_task_type": {
            task_type: {"found": found, "total": total, "recall": found / total}
            for task_type, (found, total) in type_totals.items()
            if total > 0
        },
        "per_repository": per_repo_summary,
    }

    guard_violations: list[str] = []
    guard_reference_path = Path(args.guard_reference_summary) if args.guard_reference_summary else None
    reference_summary: dict[str, Any] | None = None
    reference_metrics: dict[str, float] = {}
    current_metrics = {
        "overall_recall": _safe_float(summary["overall"].get("recall"), 0.0),
        "avg_mrr": _safe_float(summary["overall"].get("avg_mrr"), 0.0),
        "hard_recall": _summary_recall(summary, "by_difficulty", "hard"),
        "usage_recall": _summary_recall(summary, "by_task_type", "usage_search"),
    }
    required_hard_recall = float(args.guard_require_hard_recall)
    required_usage_recall = float(args.guard_require_usage_recall)
    mrr_drop_vs_reference: float | None = None
    recall_drop_vs_reference: float | None = None

    if guard_reference_path is not None:
        if not guard_reference_path.exists():
            guard_violations.append(
                f"reference summary not found: {guard_reference_path}"
            )
        else:
            reference_summary = _load_summary_payload(guard_reference_path)
            if reference_summary is None:
                guard_violations.append(
                    f"reference summary is invalid JSON object: {guard_reference_path}"
                )

    if reference_summary is not None:
        reference_metrics = {
            "overall_recall": _safe_float(
                reference_summary.get("overall", {}).get("recall"), 0.0
            ),
            "avg_mrr": _safe_float(
                reference_summary.get("overall", {}).get("avg_mrr"), 0.0
            ),
            "hard_recall": _summary_recall(reference_summary, "by_difficulty", "hard"),
            "usage_recall": _summary_recall(
                reference_summary, "by_task_type", "usage_search"
            ),
        }

        mrr_drop_vs_reference = (
            reference_metrics["avg_mrr"] - current_metrics["avg_mrr"]
        )
        recall_drop_vs_reference = (
            reference_metrics["overall_recall"] - current_metrics["overall_recall"]
        )
        if mrr_drop_vs_reference > float(args.guard_max_mrr_drop) + 1e-12:
            guard_violations.append(
                "avg_mrr drop exceeded guard limit: "
                f"ref={reference_metrics['avg_mrr']:.3f}, "
                f"cur={current_metrics['avg_mrr']:.3f}, "
                f"drop={mrr_drop_vs_reference:.3f}, "
                f"limit={float(args.guard_max_mrr_drop):.3f}"
            )
        if recall_drop_vs_reference > 1e-12:
            guard_violations.append(
                "overall recall dropped vs reference: "
                f"ref={reference_metrics['overall_recall']:.3f}, "
                f"cur={current_metrics['overall_recall']:.3f}, "
                f"drop={recall_drop_vs_reference:.3f}"
            )

        # Prevent a "false optimum" that only improves aggregate score while
        # regressing difficult/real usage slices.
        required_hard_recall = max(required_hard_recall, reference_metrics["hard_recall"])
        required_usage_recall = max(required_usage_recall, reference_metrics["usage_recall"])

    if current_metrics["hard_recall"] + 1e-12 < required_hard_recall:
        guard_violations.append(
            "hard difficulty recall below guard threshold: "
            f"cur={current_metrics['hard_recall']:.3f}, required={required_hard_recall:.3f}"
        )
    if current_metrics["usage_recall"] + 1e-12 < required_usage_recall:
        guard_violations.append(
            "usage_search recall below guard threshold: "
            f"cur={current_metrics['usage_recall']:.3f}, required={required_usage_recall:.3f}"
        )

    guard_report = {
        "enabled": bool(
            guard_reference_path is not None
            or args.guard_require_hard_recall > 0.0
            or args.guard_require_usage_recall > 0.0
            or args.guard_max_mrr_drop >= 0.0
        ),
        "strict": bool(args.guard_strict),
        "reference_summary": str(guard_reference_path) if guard_reference_path else "",
        "max_mrr_drop": float(args.guard_max_mrr_drop),
        "required": {
            "hard_recall": required_hard_recall,
            "usage_recall": required_usage_recall,
        },
        "current": current_metrics,
        "reference": reference_metrics,
        "deltas": {
            "mrr_drop_vs_reference": mrr_drop_vs_reference,
            "recall_drop_vs_reference": recall_drop_vs_reference,
        },
        "violations": guard_violations,
        "passed": len(guard_violations) == 0,
    }
    summary["anti_false_opt_guard"] = guard_report

    backlog_rows = [
        {
            "repo": repo_id,
            "status": row["status"],
            "recall": row["recall"],
            "mrr": row["mrr"],
            "latency_ms": row["latency_ms"],
            "recall_gap": row["recall_gap"],
            "mrr_gap": row["mrr_gap"],
            "selected": row["selected"],
            "selected_config": row["selected_config"],
        }
        for repo_id, row in per_repo_summary.items()
    ]
    backlog_rows.sort(
        key=lambda item: (
            item["status"] != "needs_improvement",
            -item["recall_gap"],
            -item["mrr_gap"],
            item["latency_ms"],
        )
    )

    backlog = {
        "timestamp": summary["timestamp"],
        "engine": args.engine,
        "strategy": args.config_strategy,
        "selection_policy": args.selection_policy,
        "search_budget": summary["config"].get("search_budget", {}),
        "targets": summary["targets"],
        "aggregate_results": str(aggregate_path) if aggregate_configs else "",
        "pending": [row for row in backlog_rows if row["status"] == "needs_improvement"],
        "sota_ready": [row for row in backlog_rows if row["status"] == "sota_ready"],
        "anti_false_opt_guard": {
            "passed": bool(guard_report["passed"]),
            "violations": list(guard_violations),
        },
    }
    with open(output_dir / "final_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(output_dir / "sota_backlog.json", "w", encoding="utf-8") as f:
        json.dump(backlog, f, indent=2)
    with open(output_dir / "anti_false_opt_guard.json", "w", encoding="utf-8") as f:
        json.dump(guard_report, f, indent=2)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nOverall Recall: {total_found}/{total_tasks} ({overall_recall:.1%})")
    print(f"Average MRR: {avg_mrr:.3f}")
    print(f"Average Latency: {avg_latency:.1f}ms")

    print("\nBy Difficulty:")
    for diff, metrics in summary["by_difficulty"].items():
        print(f"  {diff:8s}: {metrics['recall']:.1%} ({metrics['found']}/{metrics['total']})")

    print("\nBy Task Type:")
    for task_type, metrics in summary["by_task_type"].items():
        print(f"  {task_type:20s}: {metrics['recall']:.1%} ({metrics['found']}/{metrics['total']})")

    pending_count = len(backlog["pending"])
    print(f"\nSOTA backlog pending: {pending_count}")
    for row in backlog["pending"][:5]:
        print(
            f"  - {row['repo']}: recall_gap={row['recall_gap']:.3f}, "
            f"mrr_gap={row['mrr_gap']:.3f}, selected={row['selected']}"
        )

    print(f"\nResults saved to: {output_dir}/final_summary.json")
    print(f"SOTA backlog: {output_dir}/sota_backlog.json")
    print(
        "Anti-false-opt guard: "
        f"{'PASS' if guard_report['passed'] else 'FAIL'} "
        f"(violations={len(guard_violations)})"
    )
    print(f"Guard report: {output_dir}/anti_false_opt_guard.json")

    if args.guard_strict and not guard_report["passed"]:
        print("\n[strict] anti-false-opt guard violation detected; exiting with code 2")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
