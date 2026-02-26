#!/usr/bin/env python3
"""Compare baseline vs optimal parameters across all tools."""

import json
import subprocess
import sys
import time
import re
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


def run_agentretrieve_optimized(engine, query_terms, gold_file, difficulty):
    """Run AgentRetrieve with optimal parameters."""
    # Optimal preprocessing
    normalized = [w for t in query_terms for w in re.findall(r'[a-z]+|[0-9]+', t.lower())]
    normalized = normalized[:3]  # max_terms=3
    
    # Optimal query splitting
    if len(normalized) >= 2:
        split_point = max(1, int(len(normalized) * 0.5))  # min_match_ratio=0.5
        must_terms = normalized[:split_point]
        should_terms = normalized[split_point:]
        min_match = 1 if should_terms else 0
    else:
        must_terms = normalized
        should_terms = []
        min_match = 0
    
    start = time.perf_counter()
    results = engine.search(
        must=must_terms,
        should=should_terms,
        not_terms=[],
        max_results=10,
        max_hits=3,
        min_match=min_match
    )
    elapsed = (time.perf_counter() - start) * 1000
    
    rank = next((i+1 for i, r in enumerate(results) if gold_file in r.path), None)
    
    # Output size estimation
    output = json.dumps([{'p': r.path, 's': r.score} for r in results[:3]])
    
    return {
        'tool': 'agentretrieve_optimized',
        'latency_ms': elapsed,
        'found': rank is not None,
        'rank': rank,
        'output_bytes': len(output.encode('utf-8')),
    }


def run_ripgrep(repo_path, query_terms, gold_file):
    """Run ripgrep."""
    pattern = query_terms[0] if query_terms else ''
    cmd = ['rg', '-i', '--max-count', '20', '--no-heading', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=5)
        elapsed = (time.perf_counter() - start) * 1000
        lines = [l for l in result.stdout.strip().split('\n') if l][:20]
        rank = next((i+1 for i, l in enumerate(lines) if gold_file in l.split(':')[0]), None)
        return {
            'tool': 'ripgrep',
            'latency_ms': elapsed,
            'found': rank is not None,
            'rank': rank,
            'output_bytes': len(result.stdout.encode('utf-8')),
        }
    except:
        return {'tool': 'ripgrep', 'latency_ms': 5000, 'found': False, 'rank': None, 'output_bytes': 0}


def run_gitgrep(repo_path, query_terms, gold_file):
    """Run git grep."""
    pattern = query_terms[0] if query_terms else ''
    cmd = ['git', 'grep', '-n', '-i', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=5)
        elapsed = (time.perf_counter() - start) * 1000
        lines = [l for l in result.stdout.strip().split('\n') if l][:20]
        rank = next((i+1 for i, l in enumerate(lines) if gold_file in l.split(':')[0]), None)
        return {
            'tool': 'git_grep',
            'latency_ms': elapsed,
            'found': rank is not None,
            'rank': rank,
            'output_bytes': len(result.stdout.encode('utf-8')),
        }
    except:
        return {'tool': 'git_grep', 'latency_ms': 5000, 'found': False, 'rank': None, 'output_bytes': 0}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-name', required=True)
    parser.add_argument('--repo-path', required=True)
    parser.add_argument('--index', required=True)
    parser.add_argument('--taskset', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    
    # Load with optimal BM25 parameters
    idx = InvertedIndex.load(Path(args.index))
    idx.k1 = 1.2  # Optimal
    idx.b = 0.9   # Optimal
    engine = QueryEngine(idx)
    
    with open(args.taskset) as f:
        tasks = [json.loads(l) for l in f if l.strip() and json.loads(l)['repo'] == args.repo_name]
    
    repo_path = Path(args.repo_path)
    
    print(f'Optimal comparison for {args.repo_name}: {len(tasks)} tasks')
    print('='*100)
    print(f'{"Task":<20} {"Diff":<8} {"AR-Opt":<12} {"RG":<12} {"GG":<12}')
    print('='*100)
    
    results = []
    for task in tasks:
        task_id = task['id']
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        difficulty = task['difficulty']
        
        ar = run_agentretrieve_optimized(engine, query_terms, gold_file, difficulty)
        rg = run_ripgrep(repo_path, query_terms, gold_file)
        gg = run_gitgrep(repo_path, query_terms, gold_file)
        
        print(f"{task_id:<20} {difficulty:<8} "
              f"R:{ar['rank'] if ar['rank'] else '-':<3} {ar['latency_ms']:>6.1f}ms  "
              f"R:{rg['rank'] if rg['rank'] else '-':<3} {rg['latency_ms']:>6.1f}ms  "
              f"R:{gg['rank'] if gg['rank'] else '-':<3} {gg['latency_ms']:>6.1f}ms")
        
        results.append({
            'task_id': task_id,
            'difficulty': difficulty,
            'agentretrieve': ar,
            'ripgrep': rg,
            'git_grep': gg,
        })
    
    # Summary
    print('\n' + '='*100)
    print('SUMMARY')
    print('='*100)
    
    summary = {}
    for tool in ['agentretrieve', 'ripgrep', 'git_grep']:
        tool_key = 'agentretrieve_optimized' if tool == 'agentretrieve' else tool
        found = sum(1 for r in results if r[tool]['found'])
        ranks = [r[tool]['rank'] for r in results if r[tool]['rank']]
        mrr = sum(1.0/r for r in ranks) / len(results) if results else 0
        avg_lat = sum(r[tool]['latency_ms'] for r in results) / len(results)
        total_bytes = sum(r[tool]['output_bytes'] for r in results)
        
        summary[tool] = {
            'recall': found / len(results),
            'mrr': mrr,
            'avg_latency_ms': avg_lat,
            'total_bytes': total_bytes,
        }
        
        print(f"\n{tool}:")
        print(f"  Recall: {found}/{len(results)} ({found/len(results)*100:.1f}%)")
        print(f"  MRR: {mrr:.3f}")
        print(f"  Avg Latency: {avg_lat:.1f}ms")
        print(f"  Total Output: {total_bytes} bytes")
    
    # Save
    Path(args.output).write_text(json.dumps({
        'repo': args.repo_name,
        'config': 'optimal (k1=1.2, b=0.9, min_match=0.5, max_terms=3)',
        'summary': summary,
        'results': results,
    }, indent=2))
    
    print(f'\nSaved: {args.output}')

if __name__ == '__main__':
    main()
