#!/usr/bin/env python3
"""Fit language-aware symbol weights from corpus benchmark experiments."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.index.tokenizer import normalize_term, tokenize_identifier
from agentretrieve.query.engine import QueryEngine
from agentretrieve.query.symbol_weights import SymbolLanguageWeights


@dataclass(frozen=True)
class Sample:
    repo: str
    lang: str
    base_score_norm: float
    symbol_evidence: float
    label: int


def load_taskset(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def _normalize_symbol_term_sets(raw_symbols: list[str]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for raw in raw_symbols:
        chunks = re.findall(r"[A-Za-z0-9_]+", raw)
        terms: list[str] = []
        for chunk in chunks:
            parts = tokenize_identifier(chunk)
            terms.extend(parts if parts else [normalize_term(chunk)])
        deduped = [t for t in dict.fromkeys(terms) if t]
        if deduped:
            normalized.append(deduped)
    return normalized


def _normalize_must_terms(raw_terms: list[str]) -> list[str]:
    terms: list[str] = []
    for t in raw_terms:
        terms.extend(re.findall(r"[a-z]+|[0-9]+", t.lower()))
    return [normalize_term(t) for t in terms if t]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _build_feature_rows(samples: list[Sample], langs: list[str]) -> tuple[list[list[float]], list[int]]:
    lang_to_idx = {lang: i for i, lang in enumerate(langs)}
    rows: list[list[float]] = []
    labels: list[int] = []
    for sample in samples:
        row = [1.0, sample.base_score_norm, sample.symbol_evidence]
        interactions = [0.0] * len(langs)
        lang_idx = lang_to_idx.get(sample.lang)
        if lang_idx is not None:
            interactions[lang_idx] = sample.symbol_evidence
        row.extend(interactions)
        rows.append(row)
        labels.append(sample.label)
    return rows, labels


def _fit_logistic(
    samples: list[Sample],
    langs: list[str],
    l2: float,
    max_iter: int = 2000,
    base_lr: float = 0.4,
) -> list[float]:
    rows, labels = _build_feature_rows(samples, langs)
    dim = len(rows[0])
    n = len(rows)
    weights = [0.0] * dim

    for step in range(max_iter):
        grad = [0.0] * dim
        for row, y in zip(rows, labels):
            p = _sigmoid(_dot(weights, row))
            err = p - y
            for j, val in enumerate(row):
                grad[j] += err * val

        # L2 regularization (except intercept).
        for j in range(1, dim):
            grad[j] += l2 * weights[j]

        lr = base_lr / (1.0 + step * 0.01)
        max_update = 0.0
        for j in range(dim):
            update = lr * grad[j] / n
            weights[j] -= update
            if abs(update) > max_update:
                max_update = abs(update)

        if max_update < 1e-7:
            break

    return weights


def _logloss(samples: list[Sample], langs: list[str], weights: list[float]) -> float:
    rows, labels = _build_feature_rows(samples, langs)
    eps = 1e-12
    loss = 0.0
    for row, y in zip(rows, labels):
        p = _sigmoid(_dot(weights, row))
        p = min(1.0 - eps, max(eps, p))
        loss += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return loss / len(samples)


def _select_l2_by_repo_cv(samples: list[Sample], langs: list[str]) -> tuple[float, dict[str, float]]:
    repo_ids = sorted({s.repo for s in samples})
    if len(repo_ids) < 2:
        return 1.0, {"1.0": float("nan")}

    candidates = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]
    cv_scores: dict[str, float] = {}
    for l2 in candidates:
        fold_losses: list[float] = []
        for holdout in repo_ids:
            train = [s for s in samples if s.repo != holdout]
            valid = [s for s in samples if s.repo == holdout]
            if not train or not valid:
                continue
            if not any(s.label == 1 for s in train):
                continue
            w = _fit_logistic(train, langs, l2=l2)
            fold_losses.append(_logloss(valid, langs, w))
        if fold_losses:
            cv_scores[str(l2)] = sum(fold_losses) / len(fold_losses)

    if not cv_scores:
        return 1.0, {"1.0": float("nan")}

    best_l2 = min(cv_scores.items(), key=lambda kv: kv[1])[0]
    return float(best_l2), cv_scores


def _repo_index_map(config_path: Path) -> dict[str, Path]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    mapping: dict[str, Path] = {}
    for item in config.get("repositories", []):
        repo_id = item.get("id")
        index_path = item.get("index")
        if isinstance(repo_id, str) and isinstance(index_path, str):
            mapping[repo_id] = Path(index_path)
    return mapping


def _task_symbols(task: dict[str, Any]) -> list[str]:
    query_dsl = task.get("query_dsl", {})
    raw_symbol = query_dsl.get("symbol")
    if isinstance(raw_symbol, list) and raw_symbol:
        return [s for s in raw_symbol if isinstance(s, str) and s.strip()]
    if task.get("type") == "symbol_definition":
        must = query_dsl.get("must", [])
        return [s for s in must if isinstance(s, str) and s.strip()]
    return []


def collect_samples(
    repo_to_index: dict[str, Path],
    tasks: list[dict[str, Any]],
    max_results: int,
) -> tuple[list[Sample], dict[str, int], dict[str, int], dict[str, int]]:
    samples: list[Sample] = []
    task_count_by_lang: dict[str, int] = Counter()
    task_total_by_repo: dict[str, int] = Counter()
    task_used_by_repo: dict[str, int] = Counter()

    for repo_id, index_path in repo_to_index.items():
        if not index_path.exists():
            continue

        repo_tasks = [t for t in tasks if t.get("repo") == repo_id]
        task_total_by_repo[repo_id] = len(repo_tasks)
        if not repo_tasks:
            continue

        idx = InvertedIndex.load(index_path)
        engine = QueryEngine(idx, symbol_weights=SymbolLanguageWeights.disabled())

        for task in repo_tasks:
            raw_symbols = _task_symbols(task)
            if not raw_symbols:
                continue

            query_dsl = task.get("query_dsl", {})
            symbol_term_sets = _normalize_symbol_term_sets(raw_symbols)
            if not symbol_term_sets:
                continue

            must_terms = _normalize_must_terms(
                [v for v in query_dsl.get("must", []) if isinstance(v, str)]
            )
            should_terms = _normalize_must_terms(
                [v for v in query_dsl.get("should", []) if isinstance(v, str)]
            )
            not_terms = _normalize_must_terms(
                [v for v in query_dsl.get("not", []) if isinstance(v, str)]
            )

            results = engine.search(
                must=must_terms,
                should=should_terms,
                not_terms=not_terms,
                max_results=min(max_results, idx.total_docs),
                max_hits=3,
                min_match=int(query_dsl.get("min_match", 0)),
                near=query_dsl.get("near", []),
                lang=query_dsl.get("lang", []),
                ext=query_dsl.get("ext", []),
                path_prefix=query_dsl.get("path_prefix", []),
                symbol=[],
            )
            if not results:
                continue

            gold_file = str(task.get("gold", {}).get("file", ""))
            if not gold_file:
                continue

            if not any(gold_file in r.path for r in results):
                continue

            task_used_by_repo[repo_id] += 1
            for result in results:
                doc = idx.get_document(result.doc_id)
                if doc is None:
                    continue
                lang = (doc.lang or "unknown").lower()
                evidence = max(
                    engine._symbol_termset_evidence(result.doc_id, term_set)
                    for term_set in symbol_term_sets
                )
                label = 1 if gold_file in result.path else 0
                samples.append(
                    Sample(
                        repo=repo_id,
                        lang=lang,
                        base_score_norm=result.score / 1000.0,
                        symbol_evidence=evidence,
                        label=label,
                    )
                )
                if label == 1:
                    task_count_by_lang[lang] += 1

    return samples, dict(task_count_by_lang), dict(task_total_by_repo), dict(task_used_by_repo)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fit symbol language weights from benchmark corpus experiments."
    )
    parser.add_argument(
        "--config",
        default="configs/experiment_pipeline.yaml",
        help="Pipeline config path with repo/index mapping",
    )
    parser.add_argument(
        "--taskset",
        default="docs/benchmarks/taskset.v2.full.jsonl",
        help="Taskset JSONL path",
    )
    parser.add_argument(
        "--output",
        default="configs/symbol_language_weights.v1.json",
        help="Output weight JSON path",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Top-N results sampled per task for training",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    config_path = root / args.config
    taskset_path = root / args.taskset
    output_path = root / args.output

    repo_to_index = _repo_index_map(config_path)
    tasks = load_taskset(taskset_path)
    samples, positive_count_by_lang, task_total_by_repo, task_used_by_repo = collect_samples(
        repo_to_index=repo_to_index,
        tasks=tasks,
        max_results=max(1, args.max_results),
    )

    if not samples:
        raise RuntimeError("No training samples generated from corpus experiments")
    if not any(s.label == 1 for s in samples):
        raise RuntimeError("No positive samples available for fitting")

    langs = sorted({s.lang for s in samples})
    l2, cv_scores = _select_l2_by_repo_cv(samples, langs)
    weights = _fit_logistic(samples, langs, l2=l2)

    beta_base = weights[1]
    beta_global = weights[2]
    raw_global_weight = beta_global
    raw_by_lang: dict[str, float] = {}
    for idx, lang in enumerate(langs):
        raw_by_lang[lang] = beta_global + weights[3 + idx]

    # Empirical-Bayes shrinkage toward global weight for low-sample languages.
    observed_counts = [count for count in positive_count_by_lang.values() if count > 0]
    kappa = float(median(observed_counts)) if observed_counts else 1.0
    by_lang: dict[str, float] = {}
    for lang, raw_weight in raw_by_lang.items():
        n = float(positive_count_by_lang.get(lang, 0))
        alpha = n / (n + kappa) if (n + kappa) > 0 else 0.0
        by_lang[lang] = alpha * raw_weight + (1.0 - alpha) * raw_global_weight

    model = SymbolLanguageWeights(
        global_weight=raw_global_weight,
        by_lang=by_lang,
        metadata={
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "method": "logistic_regression_with_language_interaction",
            "taskset": str(taskset_path),
            "config": str(config_path),
            "max_results_per_task": int(args.max_results),
            "sample_count": len(samples),
            "positive_sample_count": sum(s.label for s in samples),
            "languages": langs,
            "positive_count_by_lang": positive_count_by_lang,
            "task_total_by_repo": task_total_by_repo,
            "task_used_by_repo": task_used_by_repo,
            "l2_selected": l2,
            "cv_logloss": cv_scores,
            "coefficients": {
                "beta_intercept": weights[0],
                "beta_base": beta_base,
                "beta_symbol_global": beta_global,
                "beta_symbol_lang_delta": {
                    lang: weights[3 + idx] for idx, lang in enumerate(langs)
                },
            },
            "score_mapping": "weight = beta_symbol (logit coefficient, no manual scaling)",
            "shrinkage": {
                "type": "empirical_bayes",
                "kappa_median_positive_count": kappa,
            },
        },
    )
    model.save(output_path)

    print(json.dumps(model.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
