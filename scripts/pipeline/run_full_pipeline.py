#!/usr/bin/env python3
"""Full experiment pipeline with optional fast-grid and search cache."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


FAST_GRID = {
    "k1": [0.8, 1.2, 1.5],
    "b": [0.3, 0.75, 1.0],
    "min_match_ratio": [0.0, 0.5, 0.75],
    "max_terms": [2, 3],
}

# Extended grid for parameter optimization (Sprint 15)
EXTENDED_GRID = {
    "k1": [0.5, 0.8, 1.0, 1.2, 1.5, 2.0],
    "b": [0.1, 0.3, 0.5, 0.75, 1.0],
    "min_match_ratio": [0.0, 0.25, 0.5, 0.75],
    "max_terms": [2, 3, 4],
}
SEARCH_CACHE_VERSION = "search_cache.v1"


@dataclass(frozen=True)
class ExperimentConfig:
    k1: float
    b: float
    min_match_ratio: float
    max_terms: int

    def name(self) -> str:
        return f"k1{self.k1}_b{self.b}_mm{self.min_match_ratio}_mt{self.max_terms}"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _build_grid(param_config: dict[str, Any], grid_profile: str) -> dict[str, list[Any]]:
    if grid_profile == "fast":
        return FAST_GRID
    if grid_profile == "extended":
        return EXTENDED_GRID
    return param_config["grid"]


def _build_configs(grid: dict[str, list[Any]]) -> list[ExperimentConfig]:
    configs: list[ExperimentConfig] = []
    for k1, b, mm, mt in itertools.product(
        grid["k1"],
        grid["b"],
        grid["min_match_ratio"],
        grid["max_terms"],
    ):
        configs.append(
            ExperimentConfig(k1=float(k1), b=float(b), min_match_ratio=float(mm), max_terms=int(mt))
        )
    return configs


def evaluate_single_config(args: tuple) -> dict[str, Any]:
    """Evaluate a single configuration (standalone for multiprocessing)."""
    config_dict, repo_id, index_path_str, tasks = args
    config = ExperimentConfig(**config_dict)
    index_path = Path(index_path_str)

    try:
        idx = InvertedIndex.load(index_path)
        idx.k1 = config.k1
        idx.b = config.b
        engine = QueryEngine(idx)

        results = []
        for task in tasks:
            query_terms = task["query_dsl"]["must"]
            gold_file = task["gold"]["file"]
            difficulty = task["difficulty"]

            normalized = [w for t in query_terms for w in re.findall(r"[a-z]+|[0-9]+", t.lower())]
            normalized = normalized[: config.max_terms]

            if len(normalized) >= 2:
                split_point = max(1, int(len(normalized) * (1 - config.min_match_ratio)))
                must_terms = normalized[:split_point]
                should_terms = normalized[split_point:]
                min_match = 1 if should_terms else 0
            else:
                must_terms = normalized
                should_terms = []
                min_match = 0

            start = time.perf_counter()
            ar_results = engine.search(
                must=must_terms,
                should=should_terms,
                not_terms=[],
                max_results=10,
                max_hits=3,
                min_match=min_match,
            )
            elapsed = time.perf_counter() - start

            rank = next((i + 1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
            results.append(
                {
                    "task_id": task["id"],
                    "difficulty": difficulty,
                    "found": rank is not None,
                    "rank": rank,
                    "latency_ms": elapsed,
                }
            )

        total = len(results)
        found = sum(1 for r in results if r["found"])
        ranks = [r["rank"] for r in results if r["rank"]]
        mrr = sum(1.0 / r for r in ranks) / total if total else 0.0

        diff_metrics = {}
        for diff in ["easy", "medium", "hard"]:
            diff_tasks = [r for r in results if r["difficulty"] == diff]
            if diff_tasks:
                d_found = sum(1 for r in diff_tasks if r["found"])
                d_mrr = sum(1.0 / r["rank"] for r in diff_tasks if r["rank"]) / len(diff_tasks)
                diff_metrics[diff] = {"recall": d_found / len(diff_tasks), "mrr": d_mrr}

        return {
            "config": config_dict,
            "config_name": config.name(),
            "repo": repo_id,
            "total": total,
            "found": found,
            "recall": found / total if total else 0.0,
            "mrr": mrr,
            "by_difficulty": diff_metrics,
        }
    except Exception as exc:
        return {
            "config": config_dict,
            "config_name": config.name(),
            "repo": repo_id,
            "error": str(exc),
        }


def _run_search_sequential(args_list: list[tuple]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    total = len(args_list)
    for completed, args in enumerate(args_list, start=1):
        if completed % 50 == 0 or completed == total:
            print(f"    Progress: {completed}/{total}")
        results.append(evaluate_single_config(args))
    return results


def _run_search_parallel(
    args_list: list[tuple], num_workers: int, executor_cls
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with executor_cls(max_workers=num_workers) as executor:
        futures = {executor.submit(evaluate_single_config, args): args for args in args_list}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0 or completed == len(args_list):
                print(f"    Progress: {completed}/{len(args_list)}")
            results.append(future.result())
    return results


def run_parameter_search(
    repo_id: str,
    index_path: Path,
    tasks: list[dict[str, Any]],
    configs: list[ExperimentConfig],
    weights: dict[str, float],
    num_workers: int = 4,
) -> tuple[dict[str, Any] | None, float, dict[str, Any] | None, list[dict[str, Any]]]:
    """Run parameter search for a single repository."""
    args_list = [(asdict(cfg), repo_id, str(index_path), tasks) for cfg in configs]

    if num_workers <= 1:
        results = _run_search_sequential(args_list)
    else:
        try:
            results = _run_search_parallel(args_list, num_workers, ProcessPoolExecutor)
        except (PermissionError, OSError) as err:
            print(f"    ProcessPool unavailable ({err}); fallback to ThreadPoolExecutor")
            results = _run_search_parallel(args_list, num_workers, ThreadPoolExecutor)

    best_score = -1.0
    best_result = None
    best_config = None

    for result in results:
        if "error" in result:
            continue
        score = 0.0
        for diff, weight in weights.items():
            if diff in result["by_difficulty"]:
                score += float(weight) * float(result["by_difficulty"][diff]["mrr"])
        if score > best_score:
            best_score = score
            best_config = result["config"]
            best_result = result

    return best_config, best_score, best_result, results


def _cache_key(
    *,
    repo_id: str,
    index_path: Path,
    taskset_path: Path,
    grid_profile: str,
    grid: dict[str, list[Any]],
    weights: dict[str, Any],
    task_ids: list[str],
) -> str:
    payload = {
        "version": SEARCH_CACHE_VERSION,
        "repo": repo_id,
        "index_sha256": _sha256_file(index_path),
        "taskset_sha256": _sha256_file(taskset_path),
        "grid_profile": grid_profile,
        "grid": grid,
        "weights": weights,
        "task_ids": sorted(task_ids),
    }
    return hashlib.sha256(_stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full experiment pipeline")
    parser.add_argument("-c", "--config", default="configs/experiment_pipeline.yaml")
    parser.add_argument("-o", "--output", default="artifacts/experiments/pipeline")
    parser.add_argument("-w", "--workers", type=int, default=4)
    parser.add_argument("--repos", type=str, default="", help="Comma-separated repo list")
    parser.add_argument(
        "--grid-profile",
        choices=["full", "fast", "extended"],
        default="full",
        help="Parameter grid profile",
    )
    parser.add_argument(
        "--search-cache-dir",
        default="",
        help="Optional repository search cache directory",
    )
    parser.add_argument(
        "--no-search-cache",
        action="store_true",
        help="Disable repository search cache",
    )
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    taskset_path = Path(config["tasksets"]["v2_full"]).resolve()
    with taskset_path.open(encoding="utf-8") as f:
        all_tasks = [json.loads(l) for l in f if l.strip()]

    repos = config["repositories"]
    if args.repos:
        target_repos = {r.strip() for r in args.repos.split(",") if r.strip()}
        repos = [r for r in repos if r["id"] in target_repos]

    param_config = config["parameter_search"]
    grid = _build_grid(param_config=param_config, grid_profile=args.grid_profile)
    configs = _build_configs(grid)

    use_cache = not args.no_search_cache
    search_cache_dir = Path(args.search_cache_dir) if args.search_cache_dir else None
    if use_cache and search_cache_dir is not None:
        search_cache_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("FULL EXPERIMENT PIPELINE (PARALLEL)")
    print("=" * 80)
    print(f"Output: {output_dir}")
    print(f"Workers: {args.workers}")
    print(f"Grid profile: {args.grid_profile}")
    if search_cache_dir:
        print(f"Search cache dir: {search_cache_dir} (enabled={use_cache})")
    else:
        print(f"Search cache dir: (disabled)")
    print(f"Tasks: {len(all_tasks)}")
    print(f"Repositories: {len(repos)}")
    print(f"Parameter configs: {len(configs)}")
    print(f"Total evaluations: {len(repos) * len(configs)}")

    all_results: dict[str, dict[str, Any]] = {}
    optimal_configs: dict[str, dict[str, Any]] = {}

    for repo_config in repos:
        repo_id = repo_config["id"]
        index_path = Path(repo_config["index"])
        print(f"\n{'=' * 80}")
        print(f"Repository: {repo_id}")
        print("=" * 80)

        if not index_path.exists():
            print(f"  ⚠ Index not found: {index_path}")
            continue

        repo_tasks = [t for t in all_tasks if t["repo"] == repo_id]
        if not repo_tasks:
            print(f"  ⚠ No tasks for {repo_id}")
            continue

        print(f"  Tasks: {len(repo_tasks)}")
        print(f"  Index: {index_path}")
        print(f"\n  Phase 1: Parameter Search ({len(configs)} configs, {args.workers} workers)")

        optimal_config = None
        score = -1.0
        opt_result = None
        search_results: list[dict[str, Any]] = []
        cache_hit = False

        repo_cache_path = search_cache_dir / f"{repo_id}.search_cache.json" if search_cache_dir else None
        key = _cache_key(
            repo_id=repo_id,
            index_path=index_path,
            taskset_path=taskset_path,
            grid_profile=args.grid_profile,
            grid=grid,
            weights=param_config["optimization"]["weights"],
            task_ids=[t["id"] for t in repo_tasks],
        )
        if use_cache and repo_cache_path:
            cached = _load_cache(repo_cache_path)
            if cached and cached.get("cache_key") == key:
                optimal_config = cached.get("optimal_config")
                score = float(cached.get("score", -1.0))
                opt_result = cached.get("optimal_result")
                search_results = cached.get("search_results", [])
                cache_hit = optimal_config is not None and opt_result is not None
                if cache_hit:
                    print("  [cache] hit")

        if not cache_hit:
            start_time = time.perf_counter()
            optimal_config, score, opt_result, search_results = run_parameter_search(
                repo_id,
                index_path,
                repo_tasks,
                configs,
                param_config["optimization"]["weights"],
                args.workers,
            )
            elapsed = time.perf_counter() - start_time
            print(f"  Time: {elapsed:.1f}s")
            if use_cache and repo_cache_path and optimal_config and opt_result:
                _save_cache(
                    repo_cache_path,
                    {
                        "version": SEARCH_CACHE_VERSION,
                        "cache_key": key,
                        "repo": repo_id,
                        "grid_profile": args.grid_profile,
                        "optimal_config": optimal_config,
                        "score": score,
                        "optimal_result": opt_result,
                        "search_results": search_results,
                    },
                )

        if optimal_config and opt_result:
            print(
                f"\n  Optimal: k1={optimal_config['k1']}, b={optimal_config['b']}, "
                f"mm={optimal_config['min_match_ratio']}, mt={optimal_config['max_terms']}"
            )
            print(f"  Score: {score:.3f}")
            print(f"  Recall: {opt_result['recall']:.1%}")
            print(f"  MRR: {opt_result['mrr']:.3f}")
            optimal_configs[repo_id] = optimal_config
            all_results[repo_id] = opt_result

            search_file = output_dir / f"{repo_id}_search_results.json"
            with search_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "repo": repo_id,
                        "total_configs": len(configs),
                        "grid_profile": args.grid_profile,
                        "cache_hit": cache_hit,
                        "optimal": {"config": optimal_config, "score": score, "result": opt_result},
                        "all_results": search_results,
                    },
                    f,
                    indent=2,
                )

    aggregate = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "configuration": {
            "parameter_search": config["parameter_search"],
            "grid_profile": args.grid_profile,
            "effective_grid": grid,
        },
        "optimal_configs": optimal_configs,
        "results": all_results,
    }
    with (output_dir / "aggregate_results.json").open("w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2)

    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    valid_results = [r for r in all_results.values() if "total" in r]
    if valid_results:
        total_tasks = sum(r["total"] for r in valid_results)
        total_found = sum(r["found"] for r in valid_results)
        print(f"\nTotal Repositories: {len(all_results)}")
        print(f"Total Tasks: {total_tasks}")
        print(f"Overall Recall: {total_found}/{total_tasks} ({total_found/total_tasks*100:.1f}%)")

        print("\nPer-Repository Results:")
        for repo_id, result in all_results.items():
            if "error" in result:
                continue
            opt = optimal_configs[repo_id]
            print(
                f"  {repo_id:12s}: Recall={result['recall']:>5.1%} MRR={result['mrr']:.3f} "
                f"(k1={opt['k1']}, b={opt['b']}, mm={opt['min_match_ratio']})"
            )

    print(f"\nResults saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
