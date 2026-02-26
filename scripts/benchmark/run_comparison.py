#!/usr/bin/env python3
"""Structured comparison: AgentRetrieve vs ripgrep vs git grep."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


@dataclass
class ToolResult:
    tool: str
    query: str
    latency_ms: float
    num_results: int
    stdout_bytes: int
    top_result: str | None
    found_gold: bool
    rank: int | None
    gold_file: str


@dataclass
class ComparisonResult:
    task_id: str
    repo: str
    query_nl: str
    gold_file: str
    results: list[ToolResult] = field(default_factory=list)


def load_taskset(path: Path) -> list[dict[str, Any]]:
    tasks = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def run_agentretrieve(engine: QueryEngine, query_terms: list[str], gold_file: str) -> ToolResult:
    """Run AgentRetrieve and measure."""
    # Normalize query
    import re
    normalized = []
    for t in query_terms:
        words = re.findall(r'[a-z]+|[0-9]+', t.lower())
        normalized.extend(words)
    
    start = time.perf_counter()
    results = engine.search(
        must=normalized[:3],  # Use first 3 terms
        should=[],
        not_terms=[],
        max_results=10,
        max_hits=5,
    )
    elapsed = time.perf_counter() - start
    
    # Check gold
    rank = None
    for i, r in enumerate(results):
        if gold_file in r.path:
            rank = i + 1
            break
    
    # Simulate output size
    output_json = json.dumps([{
        'path': r.path,
        'score': r.score,
        'doc_id': r.doc_id_str
    } for r in results[:5]])
    
    return ToolResult(
        tool='agentretrieve',
        query=' '.join(query_terms),
        latency_ms=elapsed * 1000,
        num_results=len(results),
        stdout_bytes=len(output_json.encode('utf-8')),
        top_result=results[0].path if results else None,
        found_gold=rank is not None,
        rank=rank,
        gold_file=gold_file,
    )


def run_ripgrep(repo_path: Path, query_terms: list[str], gold_file: str) -> ToolResult:
    """Run ripgrep and measure."""
    # Build regex pattern from terms
    pattern = '|'.join(t.lower() for t in query_terms[:3])
    cmd = ['rg', '-i', '--no-heading', '--line-number', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l]
        
        # Check gold
        rank = None
        for i, line in enumerate(lines):
            parts = line.split(':')
            if len(parts) >= 2:
                filename = parts[0]
                if gold_file in filename:
                    rank = i + 1
                    break
        
        return ToolResult(
            tool='ripgrep',
            query=' '.join(query_terms),
            latency_ms=elapsed * 1000,
            num_results=len(lines),
            stdout_bytes=len(result.stdout.encode('utf-8')),
            top_result=lines[0].split(':')[0] if lines else None,
            found_gold=rank is not None,
            rank=rank,
            gold_file=gold_file,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            tool='ripgrep',
            query=' '.join(query_terms),
            latency_ms=30000,
            num_results=0,
            stdout_bytes=0,
            top_result=None,
            found_gold=False,
            rank=None,
            gold_file=gold_file,
        )


def run_gitgrep(repo_path: Path, query_terms: list[str], gold_file: str) -> ToolResult:
    """Run git grep and measure."""
    pattern = '|'.join(t.lower() for t in query_terms[:3])
    cmd = ['git', 'grep', '-n', '-i', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=30)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l]
        
        # Check gold
        rank = None
        for i, line in enumerate(lines):
            parts = line.split(':')
            if len(parts) >= 2:
                filename = parts[0]
                if gold_file in filename:
                    rank = i + 1
                    break
        
        return ToolResult(
            tool='git_grep',
            query=' '.join(query_terms),
            latency_ms=elapsed * 1000,
            num_results=len(lines),
            stdout_bytes=len(result.stdout.encode('utf-8')),
            top_result=lines[0].split(':')[0] if lines else None,
            found_gold=rank is not None,
            rank=rank,
            gold_file=gold_file,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            tool='git_grep',
            query=' '.join(query_terms),
            latency_ms=30000,
            num_results=0,
            stdout_bytes=0,
            top_result=None,
            found_gold=False,
            rank=None,
            gold_file=gold_file,
        )


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-name', required=True)
    parser.add_argument('--repo-path', required=True)
    parser.add_argument('--index', required=True)
    parser.add_argument('--taskset', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    
    # Load
    idx = InvertedIndex.load(Path(args.index))
    engine = QueryEngine(idx)
    tasks = load_taskset(Path(args.taskset))
    tasks = [t for t in tasks if t.get('repo') == args.repo_name]
    
    repo_path = Path(args.repo_path)
    
    print(f'Running comparison for {args.repo_name}: {len(tasks)} tasks')
    print('=' * 100)
    
    comparisons: list[ComparisonResult] = []
    
    for task in tasks:
        task_id = task['id']
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        query_nl = task['query_nl']
        
        print(f'\n[{task_id}] {query_nl[:50]}...')
        print(f'Gold: {gold_file}')
        
        comp = ComparisonResult(
            task_id=task_id,
            repo=args.repo_name,
            query_nl=query_nl,
            gold_file=gold_file,
        )
        
        # Run each tool
        ar_result = run_agentretrieve(engine, query_terms, gold_file)
        comp.results.append(ar_result)
        print(f"  AgentRetrieve: {ar_result.latency_ms:>8.2f}ms | found={ar_result.found_gold} | rank={ar_result.rank} | bytes={ar_result.stdout_bytes}")
        
        rg_result = run_ripgrep(repo_path, query_terms, gold_file)
        comp.results.append(rg_result)
        print(f"  ripgrep:     {rg_result.latency_ms:>8.2f}ms | found={rg_result.found_gold} | rank={rg_result.rank} | bytes={rg_result.stdout_bytes}")
        
        gg_result = run_gitgrep(repo_path, query_terms, gold_file)
        comp.results.append(gg_result)
        print(f"  git grep:    {gg_result.latency_ms:>8.2f}ms | found={gg_result.found_gold} | rank={gg_result.rank} | bytes={gg_result.stdout_bytes}")
        
        comparisons.append(comp)
    
    # Aggregate
    print('\n' + '=' * 100)
    print('SUMMARY')
    print('=' * 100)
    
    summary = {}
    for tool in ['agentretrieve', 'ripgrep', 'git_grep']:
        tool_results = []
        for comp in comparisons:
            for r in comp.results:
                if r.tool == tool:
                    tool_results.append(r)
        
        if tool_results:
            found = sum(1 for r in tool_results if r.found_gold)
            mrr = sum(1.0/r.rank if r.rank else 0 for r in tool_results) / len(tool_results)
            avg_latency = sum(r.latency_ms for r in tool_results) / len(tool_results)
            total_bytes = sum(r.stdout_bytes for r in tool_results)
            
            summary[tool] = {
                'tasks': len(tool_results),
                'found': found,
                'recall': found / len(tool_results),
                'mrr': mrr,
                'avg_latency_ms': avg_latency,
                'total_bytes': total_bytes,
            }
            
            print(f"\n{tool}:")
            print(f"  Recall: {found}/{len(tool_results)} ({found/len(tool_results)*100:.1f}%)")
            print(f"  MRR: {mrr:.3f}")
            print(f"  Avg Latency: {avg_latency:.2f}ms")
            print(f"  Total Output: {total_bytes} bytes")
    
    # Save results
    output = {
        'repo': args.repo_name,
        'num_tasks': len(comparisons),
        'summary': summary,
        'comparisons': [
            {
                'task_id': c.task_id,
                'repo': c.repo,
                'query_nl': c.query_nl,
                'gold_file': c.gold_file,
                'results': [
                    {
                        'tool': r.tool,
                        'latency_ms': r.latency_ms,
                        'num_results': r.num_results,
                        'stdout_bytes': r.stdout_bytes,
                        'top_result': r.top_result,
                        'found_gold': r.found_gold,
                        'rank': r.rank,
                    }
                    for r in c.results
                ],
            }
            for c in comparisons
        ],
    }
    
    Path(args.output).write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(f'\nResults saved to: {args.output}')
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
