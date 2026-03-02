#!/usr/bin/env python3
"""Final evaluation with optimal parameters across all repositories."""

import json
import sys
import time
import re
import os
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.backends import SUPPORTED_ENGINES, create_backend, resolve_backend_name


@dataclass
class OptimalConfig:
    k1: float = 1.2
    b: float = 0.75
    min_match_ratio: float = 0.5
    max_terms: int = 3


def evaluate_repository(
    repo_id: str,
    index_path: Path,
    tasks: list,
    config: OptimalConfig,
    engine_backend: str,
) -> dict:
    """Evaluate a repository with given configuration."""
    backend = create_backend(engine_backend)
    idx = backend.load_index(index_path)
    backend.set_bm25(idx, k1=config.k1, b=config.b)
    
    results = []
    latencies = []
    
    for task in tasks:
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        difficulty = task['difficulty']
        task_type = task.get('type', 'unknown')
        
        # Preprocessing
        normalized = [w for t in query_terms for w in re.findall(r'[a-z]+|[0-9]+', t.lower())]
        normalized = normalized[:config.max_terms]
        
        # Query splitting based on min_match_ratio
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
        ar_results = backend.search(
            idx,
            must=must_terms,
            should=should_terms,
            not_terms=[],
            max_results=10,
            max_hits=3,
            min_match=min_match
        )
        elapsed = (time.perf_counter() - start) * 1000  # ms
        latencies.append(elapsed)
        
        rank = next((i+1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
        
        results.append({
            'task_id': task['id'],
            'difficulty': difficulty,
            'task_type': task_type,
            'found': rank is not None,
            'rank': rank,
            'latency_ms': elapsed,
            'result_count': len(ar_results),
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
            diff_metrics[diff] = {
                'count': len(diff_tasks),
                'found': d_found,
                'recall': d_found / len(diff_tasks),
                'mrr': d_mrr
            }
    
    # By task type (dynamic, based on taskset content)
    type_metrics = {}
    type_names = sorted({r['task_type'] for r in results})
    for tt in type_names:
        tt_tasks = [r for r in results if r['task_type'] == tt]
        t_found = sum(1 for r in tt_tasks if r['found'])
        type_metrics[tt] = {
            'count': len(tt_tasks),
            'found': t_found,
            'recall': t_found / len(tt_tasks),
        }
    
    return {
        'repo': repo_id,
        'config': {
            'k1': config.k1,
            'b': config.b,
            'min_match_ratio': config.min_match_ratio,
            'max_terms': config.max_terms,
        },
        'total': total,
        'found': found,
        'recall': found / total,
        'mrr': mrr,
        'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
        'by_difficulty': diff_metrics,
        'by_task_type': type_metrics,
        'task_results': results,
    }


def _resolve_repo_index_path(repo_config: dict, engine_backend: str) -> Path:
    if engine_backend == "rust":
        raw_rust = repo_config.get("index_rust")
        if isinstance(raw_rust, str) and raw_rust:
            rust_path = Path(raw_rust)
            if rust_path.exists():
                return rust_path
        raw = repo_config.get("index")
    else:
        raw = repo_config.get("index")
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"Repository index path is missing: {repo_config.get('id', 'unknown')}")
    return Path(raw)


def main():
    import argparse
    default_engine = resolve_backend_name(os.environ.get("AR_ENGINE"))
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='configs/experiment_pipeline.yaml')
    parser.add_argument('-o', '--output', default='artifacts/experiments/pipeline')
    parser.add_argument(
        '--engine',
        choices=list(SUPPORTED_ENGINES),
        default=default_engine,
        help='Retrieval backend engine',
    )
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config) as f:
        config = yaml.safe_load(f)
    
    # Load taskset
    taskset_path = config['tasksets']['v2_full']
    with open(taskset_path) as f:
        all_tasks = [json.loads(l) for l in f if l.strip()]
    
    # Optimal configuration from research
    optimal = OptimalConfig(k1=1.2, b=0.75, min_match_ratio=0.5, max_terms=3)
    
    print('='*80)
    print('FINAL EVALUATION - ALL REPOSITORIES')
    print('='*80)
    print(f"Engine: {args.engine}")
    print(f"Configuration: k1={optimal.k1}, b={optimal.b}, "
          f"min_match={optimal.min_match_ratio}, max_terms={optimal.max_terms}")
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    for repo_config in config['repositories']:
        repo_id = repo_config['id']
        index_path = _resolve_repo_index_path(repo_config, args.engine)
        
        if not index_path.exists():
            print(f"\n{repo_id}: Index not found, skipping")
            continue
        
        repo_tasks = [t for t in all_tasks if t['repo'] == repo_id]
        if not repo_tasks:
            continue
        
        print(f"\n{repo_id:12s}: ", end='', flush=True)
        
        result = evaluate_repository(
            repo_id=repo_id,
            index_path=index_path,
            tasks=repo_tasks,
            config=optimal,
            engine_backend=args.engine,
        )
        all_results[repo_id] = result
        
        print(f"Recall={result['recall']:.1%} MRR={result['mrr']:.3f} "
              f"Latency={result['avg_latency_ms']:.1f}ms")
        
        # Save individual result
        with open(output_dir / f'{repo_id}_final.json', 'w') as f:
            json.dump(result, f, indent=2)
    
    # Aggregate results
    valid = [r for r in all_results.values()]
    total_tasks = sum(r['total'] for r in valid)
    total_found = sum(r['found'] for r in valid)
    
    # Difficulty breakdown
    diff_totals = {'easy': [0, 0], 'medium': [0, 0], 'hard': [0, 0]}
    for r in valid:
        for diff, metrics in r['by_difficulty'].items():
            diff_totals[diff][0] += metrics['found']
            diff_totals[diff][1] += metrics['count']
    
    # Type breakdown
    type_totals = {}
    for r in valid:
        for tt, metrics in r['by_task_type'].items():
            if tt not in type_totals:
                type_totals[tt] = [0, 0]
            type_totals[tt][0] += metrics['found']
            type_totals[tt][1] += metrics['count']
    
    summary = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'engine': args.engine,
        'config': {
            'k1': optimal.k1,
            'b': optimal.b,
            'min_match_ratio': optimal.min_match_ratio,
            'max_terms': optimal.max_terms,
        },
        'overall': {
            'repositories': len(all_results),
            'total_tasks': total_tasks,
            'found': total_found,
            'recall': total_found / total_tasks,
            'avg_mrr': sum(r['mrr'] for r in valid) / len(valid),
            'avg_latency_ms': sum(r['avg_latency_ms'] for r in valid) / len(valid),
        },
        'by_difficulty': {
            diff: {'found': f, 'total': t, 'recall': f/t} 
            for diff, (f, t) in diff_totals.items() if t > 0
        },
        'by_task_type': {
            tt: {'found': f, 'total': t, 'recall': f/t}
            for tt, (f, t) in type_totals.items()
        },
        'per_repository': {k: {
            'recall': v['recall'],
            'mrr': v['mrr'],
            'latency_ms': v['avg_latency_ms'],
        } for k, v in all_results.items()},
    }
    
    with open(output_dir / 'final_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print('\n' + '='*80)
    print('SUMMARY')
    print('='*80)
    print(f"\nOverall Recall: {total_found}/{total_tasks} ({summary['overall']['recall']:.1%})")
    print(f"Average MRR: {summary['overall']['avg_mrr']:.3f}")
    print(f"Average Latency: {summary['overall']['avg_latency_ms']:.1f}ms")
    
    print("\nBy Difficulty:")
    for diff, metrics in summary['by_difficulty'].items():
        print(f"  {diff:8s}: {metrics['recall']:.1%} ({metrics['found']}/{metrics['total']})")
    
    print("\nBy Task Type:")
    for tt, metrics in summary['by_task_type'].items():
        print(f"  {tt:20s}: {metrics['recall']:.1%} ({metrics['found']}/{metrics['total']})")
    
    print(f"\nResults saved to: {output_dir}/final_summary.json")


if __name__ == '__main__':
    import yaml
    main()
