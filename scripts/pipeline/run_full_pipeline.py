#!/usr/bin/env python3
"""Full experiment pipeline with parallel parameter search."""

import json
import yaml
import sys
import time
import re
import itertools
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


@dataclass(frozen=True)
class ExperimentConfig:
    k1: float
    b: float
    min_match_ratio: float
    max_terms: int
    
    def name(self) -> str:
        return f"k1{self.k1}_b{self.b}_mm{self.min_match_ratio}_mt{self.max_terms}"


def evaluate_single_config(args: tuple) -> dict:
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
            query_terms = task['query_dsl']['must']
            gold_file = task['gold']['file']
            difficulty = task['difficulty']
            
            # Preprocessing
            normalized = [w for t in query_terms for w in re.findall(r'[a-z]+|[0-9]+', t.lower())]
            normalized = normalized[:config.max_terms]
            
            # Query splitting
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
                min_match=min_match
            )
            elapsed = time.perf_counter() - start
            
            rank = next((i+1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
            
            results.append({
                'task_id': task['id'],
                'difficulty': difficulty,
                'found': rank is not None,
                'rank': rank,
                'latency_ms': elapsed,
            })
        
        # Calculate metrics
        total = len(results)
        found = sum(1 for r in results if r['found'])
        ranks = [r['rank'] for r in results if r['rank']]
        mrr = sum(1.0/r for r in ranks) / total if total else 0
        
        # By difficulty
        diff_metrics = {}
        for diff in ['easy', 'medium', 'hard']:
            diff_tasks = [r for r in results if r['difficulty'] == diff]
            if diff_tasks:
                d_found = sum(1 for r in diff_tasks if r['found'])
                d_mrr = sum(1.0/r['rank'] for r in diff_tasks if r['rank']) / len(diff_tasks)
                diff_metrics[diff] = {'recall': d_found / len(diff_tasks), 'mrr': d_mrr}
        
        return {
            'config': config_dict,
            'config_name': config.name(),
            'repo': repo_id,
            'total': total,
            'found': found,
            'recall': found / total,
            'mrr': mrr,
            'by_difficulty': diff_metrics,
        }
    except Exception as e:
        return {
            'config': config_dict,
            'config_name': config.name(),
            'repo': repo_id,
            'error': str(e),
        }


def _run_search_sequential(args_list: list[tuple]) -> list[dict]:
    """Run search without multiprocessing primitives (sandbox-safe fallback)."""
    results: list[dict] = []
    total = len(args_list)
    for completed, args in enumerate(args_list, start=1):
        if completed % 50 == 0 or completed == total:
            print(f"    Progress: {completed}/{total}")
        results.append(evaluate_single_config(args))
    return results


def _run_search_parallel(args_list: list[tuple], num_workers: int, executor_cls) -> list[dict]:
    """Run search with the specified executor class."""
    results: list[dict] = []
    with executor_cls(max_workers=num_workers) as executor:
        futures = {executor.submit(evaluate_single_config, args): args for args in args_list}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0 or completed == len(args_list):
                print(f"    Progress: {completed}/{len(args_list)}")
            result = future.result()
            results.append(result)
    return results


def run_parameter_search(repo_id: str, index_path: Path, tasks: list, configs: list, 
                         weights: dict, num_workers: int = 4) -> tuple:
    """Run parameter search for a single repository."""
    # Prepare arguments for parallel execution
    args_list = [
        (asdict(cfg), repo_id, str(index_path), tasks) 
        for cfg in configs
    ]
    
    if num_workers <= 1:
        results = _run_search_sequential(args_list)
    else:
        try:
            results = _run_search_parallel(args_list, num_workers, ProcessPoolExecutor)
        except (PermissionError, OSError) as err:
            print(f"    ProcessPool unavailable ({err}); fallback to ThreadPoolExecutor")
            results = _run_search_parallel(args_list, num_workers, ThreadPoolExecutor)
    
    # Find optimal config
    best_score = -1
    best_result = None
    best_config = None
    
    for result in results:
        if 'error' in result:
            continue
        
        score = 0
        for diff, weight in weights.items():
            if diff in result['by_difficulty']:
                score += weight * result['by_difficulty'][diff]['mrr']
        
        if score > best_score:
            best_score = score
            best_config = result['config']
            best_result = result
    
    return best_config, best_score, best_result, results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run full experiment pipeline')
    parser.add_argument('-c', '--config', default='configs/experiment_pipeline.yaml')
    parser.add_argument('-o', '--output', default='artifacts/experiments/pipeline')
    parser.add_argument('-w', '--workers', type=int, default=4)
    parser.add_argument('--repos', type=str, default='', help='Comma-separated repo list')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config) as f:
        config = yaml.safe_load(f)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load taskset
    taskset_path = config['tasksets']['v2_full']
    with open(taskset_path) as f:
        all_tasks = [json.loads(l) for l in f if l.strip()]
    
    print('='*80)
    print('FULL EXPERIMENT PIPELINE (PARALLEL)')
    print('='*80)
    print(f"Output: {output_dir}")
    print(f"Workers: {args.workers}")
    
    # Filter repositories if specified
    repos = config['repositories']
    if args.repos:
        target_repos = args.repos.split(',')
        repos = [r for r in repos if r['id'] in target_repos]
    
    # Generate parameter grid
    param_config = config['parameter_search']
    configs = []
    for k1, b, mm, mt in itertools.product(
        param_config['grid']['k1'],
        param_config['grid']['b'],
        param_config['grid']['min_match_ratio'],
        param_config['grid']['max_terms']
    ):
        configs.append(ExperimentConfig(k1=k1, b=b, min_match_ratio=mm, max_terms=mt))
    
    print(f"Tasks: {len(all_tasks)}")
    print(f"Repositories: {len(repos)}")
    print(f"Parameter configs: {len(configs)}")
    print(f"Total evaluations: {len(repos) * len(configs)}")
    
    # Process each repository
    all_results = {}
    optimal_configs = {}
    
    for repo_config in repos:
        repo_id = repo_config['id']
        print(f"\n{'='*80}")
        print(f"Repository: {repo_id}")
        print('='*80)
        
        if not Path(repo_config['index']).exists():
            print(f"  ⚠ Index not found: {repo_config['index']}")
            continue
        
        repo_tasks = [t for t in all_tasks if t['repo'] == repo_id]
        if not repo_tasks:
            print(f"  ⚠ No tasks for {repo_id}")
            continue
        
        print(f"  Tasks: {len(repo_tasks)}")
        print(f"  Index: {repo_config['index']}")
        print(f"\n  Phase 1: Parameter Search ({len(configs)} configs, {args.workers} workers)")
        
        start_time = time.perf_counter()
        optimal_config, score, opt_result, search_results = run_parameter_search(
            repo_id, Path(repo_config['index']), repo_tasks, configs,
            param_config['optimization']['weights'], args.workers
        )
        elapsed = time.perf_counter() - start_time
        
        if optimal_config:
            print(f"\n  Optimal: k1={optimal_config['k1']}, b={optimal_config['b']}, "
                  f"mm={optimal_config['min_match_ratio']}, mt={optimal_config['max_terms']}")
            print(f"  Score: {score:.3f}")
            print(f"  Recall: {opt_result['recall']:.1%}")
            print(f"  MRR: {opt_result['mrr']:.3f}")
            print(f"  Time: {elapsed:.1f}s")
            
            optimal_configs[repo_id] = optimal_config
            all_results[repo_id] = opt_result
            
            # Save search results
            search_file = output_dir / f'{repo_id}_search_results.json'
            with open(search_file, 'w') as f:
                json.dump({
                    'repo': repo_id,
                    'total_configs': len(configs),
                    'optimal': {'config': optimal_config, 'score': score, 'result': opt_result},
                    'all_results': search_results,
                }, f, indent=2)
    
    # Save aggregate
    aggregate = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'configuration': param_config,
        'optimal_configs': optimal_configs,
        'results': all_results,
    }
    with open(output_dir / 'aggregate_results.json', 'w') as f:
        json.dump(aggregate, f, indent=2)
    
    # Print summary
    print('\n' + '='*80)
    print('FINAL SUMMARY')
    print('='*80)
    
    valid_results = [r for r in all_results.values() if 'total' in r]
    if valid_results:
        total_tasks = sum(r['total'] for r in valid_results)
        total_found = sum(r['found'] for r in valid_results)
        print(f"\nTotal Repositories: {len(all_results)}")
        print(f"Total Tasks: {total_tasks}")
        print(f"Overall Recall: {total_found}/{total_tasks} ({total_found/total_tasks*100:.1f}%)")
        
        print("\nPer-Repository Results:")
        for repo_id, result in all_results.items():
            if 'error' not in result:
                opt = optimal_configs[repo_id]
                print(f"  {repo_id:12s}: Recall={result['recall']:>5.1%} MRR={result['mrr']:.3f} "
                      f"(k1={opt['k1']}, b={opt['b']}, mm={opt['min_match_ratio']})")
    
    print(f"\nResults saved to: {output_dir}")


if __name__ == '__main__':
    main()
