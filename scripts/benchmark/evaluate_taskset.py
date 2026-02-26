#!/usr/bin/env python3
"""Evaluate AgentRetrieve against benchmark taskset."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


def load_taskset(path: Path) -> list[dict[str, Any]]:
    """Load taskset from JSONL."""
    tasks = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def evaluate_task(engine: QueryEngine, task: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single task."""
    query_dsl = task.get('query_dsl', {})
    must = query_dsl.get('must', [])
    k = query_dsl.get('k', 1)
    
    gold = task.get('gold', {})
    gold_file = gold.get('file', '')
    
    # Normalize query terms - split phrases and handle numbers
    normalized_must = []
    for t in must:
        # Keep alphanumeric sequences, split on punctuation and space
        import re
        words = re.findall(r'[a-z]+|[0-9]+', t.lower())
        normalized_must.extend(words)
    
    # Execute search
    start_time = time.perf_counter()
    results = engine.search(
        must=normalized_must,
        should=[],
        not_terms=[],
        max_results=max(k, 10),
        max_hits=5,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    # Check if gold file is in results
    rank = None
    for i, r in enumerate(results):
        if gold_file in r.path:
            rank = i + 1
            break
    
    # Calculate MRR
    mrr = 1.0 / rank if rank else 0.0
    
    return {
        'task_id': task['id'],
        'repo': task['repo'],
        'query_nl': task.get('query_nl', ''),
        'gold_file': gold_file,
        'rank': rank,
        'mrr': mrr,
        'found': rank is not None,
        'latency_ms': elapsed_ms,
        'num_results': len(results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Evaluate AgentRetrieve benchmark')
    parser.add_argument('--index', required=True, help='Index file path')
    parser.add_argument('--taskset', required=True, help='Taskset JSONL path')
    parser.add_argument('--repo', help='Filter by repo (e.g., ripgrep)')
    parser.add_argument('-o', '--output', help='Output JSON path')
    args = parser.parse_args()
    
    # Load index
    print(f'Loading index: {args.index}', file=sys.stderr)
    idx = InvertedIndex.load(Path(args.index))
    print(f'  Docs: {idx.total_docs}, Terms: {len(idx.index)}', file=sys.stderr)
    
    engine = QueryEngine(idx)
    
    # Load tasks
    tasks = load_taskset(Path(args.taskset))
    if args.repo:
        tasks = [t for t in tasks if t.get('repo') == args.repo]
    print(f'Tasks: {len(tasks)}', file=sys.stderr)
    
    # Evaluate each task
    results = []
    for task in tasks:
        result = evaluate_task(engine, task)
        results.append(result)
        status = '✓' if result['found'] else '✗'
        print(f"{status} {result['task_id']}: rank={result['rank']}, {result['latency_ms']:.1f}ms", file=sys.stderr)
    
    # Aggregate metrics
    found_count = sum(1 for r in results if r['found'])
    total_latency = sum(r['latency_ms'] for r in results)
    mean_mrr = sum(r['mrr'] for r in results) / len(results) if results else 0.0
    
    metrics = {
        'num_tasks': len(results),
        'found_count': found_count,
        'recall@k': found_count / len(results) if results else 0.0,
        'mrr': mean_mrr,
        'mean_latency_ms': total_latency / len(results) if results else 0.0,
        'total_latency_ms': total_latency,
    }
    
    # Output
    output = {
        'metrics': metrics,
        'results': results,
    }
    
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(f'\nResults saved to: {args.output}', file=sys.stderr)
    
    print(json.dumps(metrics, indent=2))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
