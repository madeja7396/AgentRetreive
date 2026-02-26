#!/usr/bin/env python3
"""Parameter grid search for optimal AgentRetrieve configuration."""

import json
import sys
import time
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


@dataclass
class SearchConfig:
    name: str
    k1: float
    b: float
    should_boost: float
    min_match_ratio: float  # 0.0 = all must, 1.0 = any must
    max_terms: int


def evaluate_config(config: SearchConfig, index_path: Path, tasks: list[dict]) -> dict:
    """Evaluate a single configuration."""
    idx = InvertedIndex.load(index_path)
    idx.k1 = config.k1
    idx.b = config.b
    engine = QueryEngine(idx)
    
    results = []
    for task in tasks:
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        difficulty = task['difficulty']
        
        # Normalize
        normalized = [w for t in query_terms for w in re.findall(r'[a-z]+|[0-9]+', t.lower())]
        normalized = normalized[:config.max_terms]
        
        # Apply min_match logic
        if config.min_match_ratio == 0.0:
            must_terms = normalized
            should_terms = []
        else:
            split_point = max(1, int(len(normalized) * (1 - config.min_match_ratio)))
            must_terms = normalized[:split_point]
            should_terms = normalized[split_point:]
        
        start = time.perf_counter()
        ar_results = engine.search(
            must=must_terms,
            should=should_terms,
            not_terms=[],
            max_results=10,
            max_hits=3
        )
        elapsed = (time.perf_counter() - start) * 1000
        
        rank = next((i+1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
        
        results.append({
            'task_id': task['id'],
            'difficulty': difficulty,
            'found': rank is not None,
            'rank': rank,
            'latency_ms': elapsed,
        })
    
    # Aggregate by difficulty
    metrics = {}
    for diff in ['easy', 'medium', 'hard']:
        diff_results = [r for r in results if r['difficulty'] == diff]
        if diff_results:
            found = sum(1 for r in diff_results if r['found'])
            ranks = [r['rank'] for r in diff_results if r['rank']]
            metrics[diff] = {
                'recall': found / len(diff_results),
                'mrr': sum(1.0/r for r in ranks) / len(diff_results) if diff_results else 0,
                'avg_latency': sum(r['latency_ms'] for r in diff_results) / len(diff_results),
            }
    
    # Overall
    found_total = sum(1 for r in results if r['found'])
    ranks_total = [r['rank'] for r in results if r['rank']]
    metrics['overall'] = {
        'recall': found_total / len(results),
        'mrr': sum(1.0/r for r in ranks_total) / len(results) if results else 0,
        'avg_latency': sum(r['latency_ms'] for r in results) / len(results),
    }
    
    return {
        'config': {
            'name': config.name,
            'k1': config.k1,
            'b': config.b,
            'should_boost': config.should_boost,
            'min_match_ratio': config.min_match_ratio,
            'max_terms': config.max_terms,
        },
        'metrics': metrics,
        'results': results,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--index', required=True)
    parser.add_argument('--taskset', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    
    # Load tasks
    with open(args.taskset) as f:
        tasks = [json.loads(l) for l in f if l.strip()]
    tasks = [t for t in tasks if t['repo'] == args.repo]
    
    print(f'Parameter search for {args.repo}: {len(tasks)} tasks')
    
    # Define configurations to test
    configs = []
    
    # Baseline
    configs.append(SearchConfig('baseline', 1.2, 0.75, 0.5, 0.0, 3))
    
    # BM25 parameter variations
    for k1 in [0.8, 1.0, 1.5, 2.0]:
        for b in [0.3, 0.5, 0.75, 1.0]:
            configs.append(SearchConfig(
                f'k1_{k1}_b_{b}',
                k1, b, 0.5, 0.0, 3
            ))
    
    # Min-match variations (query relaxation)
    for ratio in [0.0, 0.25, 0.5, 0.75]:
        configs.append(SearchConfig(
            f'minmatch_{ratio}',
            1.2, 0.75, 0.5, ratio, 3
        ))
    
    # Max terms variations
    for max_terms in [2, 3, 4, 5]:
        configs.append(SearchConfig(
            f'maxterms_{max_terms}',
            1.2, 0.75, 0.5, 0.0, max_terms
        ))
    
    # Combined best candidates
    configs.append(SearchConfig('relaxed_k1_1.5', 1.5, 0.5, 0.7, 0.5, 4))
    configs.append(SearchConfig('strict_k1_0.8', 0.8, 0.75, 0.3, 0.0, 3))
    
    print(f'Testing {len(configs)} configurations...\n')
    
    # Evaluate all
    all_results = []
    for i, config in enumerate(configs, 1):
        print(f'[{i}/{len(configs)}] Testing {config.name}...', end=' ')
        result = evaluate_config(config, Path(args.index), tasks)
        all_results.append(result)
        
        m = result['metrics']['overall']
        print(f"Recall={m['recall']:.2f}, MRR={m['mrr']:.3f}")
    
    # Find best by difficulty
    print('\n' + '='*80)
    print('BEST CONFIGURATIONS BY DIFFICULTY')
    print('='*80)
    
    for diff in ['easy', 'medium', 'hard', 'overall']:
        best_recall = max(all_results, key=lambda x: x['metrics'][diff]['recall'])
        best_mrr = max(all_results, key=lambda x: x['metrics'][diff]['mrr'])
        
        print(f'\n{diff.upper()}:')
        print(f"  Best Recall: {best_recall['config']['name']} "
              f"({best_recall['metrics'][diff]['recall']:.2f})")
        print(f"  Best MRR:    {best_mrr['config']['name']} "
              f"({best_mrr['metrics'][diff]['mrr']:.3f})")
    
    # Top 5 overall
    print('\n' + '='*80)
    print('TOP 5 CONFIGURATIONS (Overall MRR)')
    print('='*80)
    
    sorted_results = sorted(all_results, key=lambda x: x['metrics']['overall']['mrr'], reverse=True)
    for i, r in enumerate(sorted_results[:5], 1):
        c = r['config']
        m = r['metrics']['overall']
        print(f"{i}. {c['name']}")
        print(f"   k1={c['k1']}, b={c['b']}, min_match={c['min_match_ratio']}, max_terms={c['max_terms']}")
        print(f"   Recall={m['recall']:.2f}, MRR={m['mrr']:.3f}, Latency={m['avg_latency']:.1f}ms")
    
    # Save all results
    Path(args.output).write_text(json.dumps({
        'repo': args.repo,
        'num_tasks': len(tasks),
        'num_configs': len(configs),
        'all_results': all_results,
        'top_5': [r['config'] for r in sorted_results[:5]],
    }, indent=2))
    
    print(f'\nSaved to: {args.output}')


if __name__ == '__main__':
    main()
