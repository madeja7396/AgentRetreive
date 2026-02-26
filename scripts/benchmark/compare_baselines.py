#!/usr/bin/env python3
"""Compare AgentRetrieve vs baselines (ripgrep, git grep)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


def load_taskset(path: Path) -> list[dict[str, Any]]:
    tasks = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def benchmark_agentretrieve(engine: QueryEngine, query_terms: list[str], repo_path: Path) -> dict:
    """Benchmark AgentRetrieve."""
    start = time.perf_counter()
    results = engine.search(
        must=query_terms,
        should=[],
        not_terms=[],
        max_results=10,
        max_hits=5,
    )
    elapsed = time.perf_counter() - start
    
    return {
        'tool': 'agentretrieve',
        'latency_ms': elapsed * 1000,
        'num_results': len(results),
        'top_result': results[0].path if results else None,
    }


def benchmark_ripgrep(query: str, repo_path: Path) -> dict:
    """Benchmark ripgrep."""
    cmd = ['rg', '--no-heading', '--line-number', '--color', 'never', '-i', query]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l]
        
        return {
            'tool': 'ripgrep',
            'latency_ms': elapsed * 1000,
            'num_results': len(lines),
            'top_result': lines[0].split(':')[0] if lines else None,
            'stdout_bytes': len(result.stdout.encode('utf-8')),
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': 'ripgrep',
            'latency_ms': 30000,
            'num_results': 0,
            'top_result': None,
            'stdout_bytes': 0,
            'timeout': True,
        }


def benchmark_gitgrep(query: str, repo_path: Path) -> dict:
    """Benchmark git grep."""
    cmd = ['git', 'grep', '-n', '-i', query]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l]
        
        return {
            'tool': 'git_grep',
            'latency_ms': elapsed * 1000,
            'num_results': len(lines),
            'top_result': lines[0].split(':')[0] if lines else None,
            'stdout_bytes': len(result.stdout.encode('utf-8')),
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': 'git_grep',
            'latency_ms': 30000,
            'num_results': 0,
            'top_result': None,
            'stdout_bytes': 0,
            'timeout': True,
        }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', required=True)
    parser.add_argument('--repo', required=True, help='Path to repo')
    parser.add_argument('--taskset', required=True)
    parser.add_argument('--repo-name', required=True)
    args = parser.parse_args()
    
    idx = InvertedIndex.load(Path(args.index))
    engine = QueryEngine(idx)
    tasks = load_taskset(Path(args.taskset))
    tasks = [t for t in tasks if t.get('repo') == args.repo_name]
    
    print(f'Comparing baselines for {args.repo_name}: {len(tasks)} tasks')
    print('=' * 100)
    print(f'{"Task":<12} {"Query":<40} {"Tool":<15} {"Latency":<12} {"Results":<10} {"Top Result":<30}')
    print('=' * 100)
    
    results = []
    for task in tasks:
        task_id = task['id']
        query_terms = task['query_dsl']['must']
        query_str = ' '.join(query_terms)
        
        # Normalize query for baseline
        normalized = ' '.join(t.lower().replace('.', '').replace('-', '') for t in query_terms)
        
        # AgentRetrieve
        ar_result = benchmark_agentretrieve(engine, [normalized.split()[-1]], Path(args.repo))
        ar_result['task_id'] = task_id
        ar_result['query'] = query_str[:40]
        results.append(ar_result)
        print(f"{task_id:<12} {query_str[:40]:<40} {ar_result['tool']:<15} {ar_result['latency_ms']:>8.2f}ms {ar_result['num_results']:<10} {str(ar_result['top_result'])[:30]:<30}")
        
        # ripgrep
        rg_result = benchmark_ripgrep(normalized, Path(args.repo))
        rg_result['task_id'] = task_id
        rg_result['query'] = query_str[:40]
        results.append(rg_result)
        print(f"{'':<12} {'':<40} {rg_result['tool']:<15} {rg_result['latency_ms']:>8.2f}ms {rg_result['num_results']:<10} {str(rg_result['top_result'])[:30]:<30}")
        
        # git grep
        gg_result = benchmark_gitgrep(normalized, Path(args.repo))
        gg_result['task_id'] = task_id
        gg_result['query'] = query_str[:40]
        results.append(gg_result)
        print(f"{'':<12} {'':<40} {gg_result['tool']:<15} {gg_result['latency_ms']:>8.2f}ms {gg_result['num_results']:<10} {str(gg_result['top_result'])[:30]:<30}")
        print()
    
    # Summary
    print('=' * 100)
    print('SUMMARY')
    print('=' * 100)
    
    for tool in ['agentretrieve', 'ripgrep', 'git_grep']:
        tool_results = [r for r in results if r['tool'] == tool]
        if tool_results:
            avg_latency = sum(r['latency_ms'] for r in tool_results) / len(tool_results)
            total_results = sum(r['num_results'] for r in tool_results)
            print(f"{tool:15s}: avg_latency={avg_latency:8.2f}ms, total_results={total_results}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
