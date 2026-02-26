#!/usr/bin/env python3
"""Run all experiments across all repositories."""

import json
import subprocess
import sys
import time
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine

REPOS = ['fd', 'ripgrep', 'fzf', 'fmt', 'curl', 'pytest', 'cli']

def evaluate_repository(repo, taskset_path, use_optimal=True):
    """Evaluate a single repository."""
    index_path = Path(f'artifacts/datasets/{repo}.index.json')
    repo_path = Path(f'artifacts/datasets/raw/{repo}')
    
    if not index_path.exists():
        return None, f"Index not found: {index_path}"
    
    # Load tasks for this repo
    with open(taskset_path) as f:
        tasks = [json.loads(l) for l in f if l.strip() and json.loads(l)['repo'] == repo]
    
    if not tasks:
        return None, f"No tasks for {repo}"
    
    # Load index with optimal params
    idx = InvertedIndex.load(index_path)
    if use_optimal:
        idx.k1 = 1.2
        idx.b = 0.9
    engine = QueryEngine(idx)
    
    results = []
    for task in tasks:
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        difficulty = task['difficulty']
        task_type = task['type']
        
        # Optimal preprocessing
        normalized = [w for t in query_terms for w in re.findall(r'[a-z]+|[0-9]+', t.lower())]
        normalized = normalized[:3]  # max_terms=3
        
        # Optimal query splitting (min_match=0.5)
        if len(normalized) >= 2:
            split_point = max(1, int(len(normalized) * 0.5))
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
        elapsed = (time.perf_counter() - start) * 1000
        
        rank = next((i+1 for i, r in enumerate(ar_results) if gold_file in r.path), None)
        
        results.append({
            'task_id': task['id'],
            'difficulty': difficulty,
            'type': task_type,
            'found': rank is not None,
            'rank': rank,
            'latency_ms': elapsed,
        })
    
    return results, None

def main():
    taskset_path = 'docs/benchmarks/taskset.v2.full.jsonl'
    
    print('='*100)
    print('FULL EXPERIMENT SUITE - All Repositories')
    print('='*100)
    print(f'Configuration: k1=1.2, b=0.9, min_match=0.5, max_terms=3')
    print('='*100)
    
    all_results = {}
    
    for repo in REPOS:
        print(f'\n--- Evaluating {repo} ---')
        results, error = evaluate_repository(repo, taskset_path)
        
        if error:
            print(f'  ⚠ {error}')
            continue
        
        # Calculate metrics
        total = len(results)
        found = sum(1 for r in results if r['found'])
        ranks = [r['rank'] for r in results if r['rank']]
        mrr = sum(1.0/r for r in ranks) / total if total else 0
        avg_latency = sum(r['latency_ms'] for r in results) / total
        
        # By difficulty
        diff_stats = {}
        for diff in ['easy', 'medium', 'hard']:
            diff_tasks = [r for r in results if r['difficulty'] == diff]
            if diff_tasks:
                d_found = sum(1 for r in diff_tasks if r['found'])
                d_mrr = sum(1.0/r['rank'] for r in diff_tasks if r['rank']) / len(diff_tasks)
                diff_stats[diff] = {
                    'recall': d_found / len(diff_tasks),
                    'mrr': d_mrr,
                }
        
        all_results[repo] = {
            'total': total,
            'found': found,
            'recall': found / total,
            'mrr': mrr,
            'avg_latency': avg_latency,
            'by_difficulty': diff_stats,
            'tasks': results,
        }
        
        print(f'  Tasks: {total}, Recall: {found}/{total} ({found/total*100:.1f}%), MRR: {mrr:.3f}, Latency: {avg_latency:.1f}ms')
        for diff, stats in diff_stats.items():
            print(f'    {diff}: Recall={stats["recall"]*100:.0f}%, MRR={stats["mrr"]:.2f}')
    
    # Aggregate summary
    print('\n' + '='*100)
    print('AGGREGATE SUMMARY')
    print('='*100)
    
    total_tasks = sum(r['total'] for r in all_results.values())
    total_found = sum(r['found'] for r in all_results.values())
    
    print(f'\nTotal Repositories: {len(all_results)}')
    print(f'Total Tasks: {total_tasks}')
    print(f'Overall Recall: {total_found}/{total_tasks} ({total_found/total_tasks*100:.1f}%)')
    
    # By difficulty aggregate
    print('\nBy Difficulty (aggregate):')
    for diff in ['easy', 'medium', 'hard']:
        diff_tasks = []
        for repo_results in all_results.values():
            diff_tasks.extend([t for t in repo_results['tasks'] if t['difficulty'] == diff])
        if diff_tasks:
            found = sum(1 for t in diff_tasks if t['found'])
            mrr = sum(1.0/t['rank'] for t in diff_tasks if t['rank']) / len(diff_tasks)
            print(f'  {diff}: {found}/{len(diff_tasks)} ({found/len(diff_tasks)*100:.1f}%), MRR={mrr:.2f}')
    
    # By type aggregate
    print('\nBy Type (aggregate):')
    type_stats = defaultdict(lambda: {'total': 0, 'found': 0})
    for repo_results in all_results.values():
        for task in repo_results['tasks']:
            t = task['type']
            type_stats[t]['total'] += 1
            if task['found']:
                type_stats[t]['found'] += 1
    for t, s in sorted(type_stats.items()):
        print(f'  {t}: {s["found"]}/{s["total"]} ({s["found"]/s["total"]*100:.1f}%)')
    
    # Save results
    output_path = Path('artifacts/experiments/FULL_EXPERIMENT_RESULTS.json')
    output_path.write_text(json.dumps({
        'configuration': {
            'k1': 1.2,
            'b': 0.9,
            'min_match_ratio': 0.5,
            'max_terms': 3,
        },
        'repositories': all_results,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }, indent=2))
    
    print(f'\nResults saved to: {output_path}')
    print('='*100)

if __name__ == '__main__':
    main()
