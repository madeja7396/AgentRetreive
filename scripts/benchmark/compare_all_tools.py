#!/usr/bin/env python3
"""Direct comparison: AgentRetrieve vs ripgrep vs git grep vs GNU grep."""

import json
import subprocess
import sys
import time
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine


def run_agentretrieve(engine, query_terms, gold_file):
    """Run AgentRetrieve."""
    normalized = []
    for t in query_terms:
        words = re.findall(r'[a-z]+|[0-9]+', t.lower())
        normalized.extend(words)
    
    start = time.perf_counter()
    results = engine.search(must=normalized[:3], should=[], not_terms=[], max_results=10, max_hits=3)
    elapsed = time.perf_counter() - start
    
    rank = None
    for i, r in enumerate(results):
        if gold_file in r.path:
            rank = i + 1
            break
    
    output = json.dumps([{'p': r.path, 's': r.score} for r in results[:5]])
    
    return {
        'tool': 'agentretrieve',
        'latency_ms': elapsed * 1000,
        'num_results': len(results),
        'output_bytes': len(output.encode('utf-8')),
        'found': rank is not None,
        'rank': rank,
        'top_result': results[0].path if results else None,
    }


def run_ripgrep(repo_path, query_terms, gold_file):
    """Run ripgrep with pattern matching."""
    # Use first term as pattern
    pattern = query_terms[0].lower().replace('.', '').replace('-', '')
    cmd = ['rg', '-i', '--no-heading', '--line-number', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=10)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l][:50]  # Limit to 50 results
        
        # Find gold file rank
        rank = None
        for i, line in enumerate(lines):
            parts = line.split(':')
            if parts and gold_file in parts[0]:
                rank = i + 1
                break
        
        return {
            'tool': 'ripgrep',
            'latency_ms': elapsed * 1000,
            'num_results': len(lines),
            'output_bytes': len(result.stdout.encode('utf-8')),
            'found': rank is not None,
            'rank': rank,
            'top_result': lines[0].split(':')[0] if lines else None,
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': 'ripgrep',
            'latency_ms': 10000,
            'num_results': 0,
            'output_bytes': 0,
            'found': False,
            'rank': None,
            'top_result': None,
            'timeout': True,
        }


def run_gitgrep(repo_path, query_terms, gold_file):
    """Run git grep."""
    pattern = query_terms[0].lower().replace('.', '').replace('-', '')
    cmd = ['git', 'grep', '-n', '-i', pattern]
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=10)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l][:50]
        
        rank = None
        for i, line in enumerate(lines):
            parts = line.split(':')
            if parts and gold_file in parts[0]:
                rank = i + 1
                break
        
        return {
            'tool': 'git_grep',
            'latency_ms': elapsed * 1000,
            'num_results': len(lines),
            'output_bytes': len(result.stdout.encode('utf-8')),
            'found': rank is not None,
            'rank': rank,
            'top_result': lines[0].split(':')[0] if lines else None,
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': 'git_grep',
            'latency_ms': 10000,
            'num_results': 0,
            'output_bytes': 0,
            'found': False,
            'rank': None,
            'top_result': None,
            'timeout': True,
        }


def run_grep(repo_path, query_terms, gold_file):
    """Run GNU grep."""
    pattern = query_terms[0].lower().replace('.', '').replace('-', '')
    cmd = ['grep', '-r', '-n', '-i', pattern, '.']
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=10)
        elapsed = time.perf_counter() - start
        
        lines = result.stdout.strip().split('\n') if result.stdout else []
        lines = [l for l in lines if l][:50]
        
        rank = None
        for i, line in enumerate(lines):
            parts = line.split(':')
            if parts and gold_file in parts[0]:
                rank = i + 1
                break
        
        return {
            'tool': 'gnu_grep',
            'latency_ms': elapsed * 1000,
            'num_results': len(lines),
            'output_bytes': len(result.stdout.encode('utf-8')),
            'found': rank is not None,
            'rank': rank,
            'top_result': lines[0].split(':')[0] if lines else None,
        }
    except subprocess.TimeoutExpired:
        return {
            'tool': 'gnu_grep',
            'latency_ms': 10000,
            'num_results': 0,
            'output_bytes': 0,
            'found': False,
            'rank': None,
            'top_result': None,
            'timeout': True,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-name', required=True)
    parser.add_argument('--repo-path', required=True)
    parser.add_argument('--index', required=True)
    parser.add_argument('--taskset', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    
    idx = InvertedIndex.load(Path(args.index))
    engine = QueryEngine(idx)
    
    with open(args.taskset) as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    tasks = [t for t in tasks if t['repo'] == args.repo_name]
    
    repo_path = Path(args.repo_path)
    
    print(f'Comparing 4 tools on {args.repo_name}: {len(tasks)} tasks')
    print('=' * 100)
    print(f'{"Task":<12} {"Tool":<15} {"Latency":<12} {"Found":<8} {"Rank":<8} {"Results":<10} {"Bytes":<10}')
    print('=' * 100)
    
    all_results = []
    
    for task in tasks:
        task_id = task['id']
        query_terms = task['query_dsl']['must']
        gold_file = task['gold']['file']
        
        task_results = {
            'task_id': task_id,
            'query': ' '.join(query_terms),
            'gold_file': gold_file,
            'tools': []
        }
        
        # Run all 4 tools
        for run_func in [run_agentretrieve, run_ripgrep, run_gitgrep, run_grep]:
            if run_func == run_agentretrieve:
                result = run_func(engine, query_terms, gold_file)
            else:
                result = run_func(repo_path, query_terms, gold_file)
            
            task_results['tools'].append(result)
            print(f"{task_id:<12} {result['tool']:<15} {result['latency_ms']:>8.2f}ms   {str(result['found']):<8} {str(result['rank']):<8} {result['num_results']:<10} {result['output_bytes']:<10}")
        
        all_results.append(task_results)
        print()
    
    # Aggregate
    print('=' * 100)
    print('SUMMARY')
    print('=' * 100)
    
    summary = {}
    for tool in ['agentretrieve', 'ripgrep', 'git_grep', 'gnu_grep']:
        tool_results = []
        for task in all_results:
            for r in task['tools']:
                if r['tool'] == tool:
                    tool_results.append(r)
        
        if tool_results:
            found = sum(1 for r in tool_results if r['found'])
            ranks = [r['rank'] for r in tool_results if r['rank']]
            mrr = sum(1.0/r for r in ranks) / len(tool_results) if tool_results else 0
            avg_latency = sum(r['latency_ms'] for r in tool_results) / len(tool_results)
            total_bytes = sum(r['output_bytes'] for r in tool_results)
            
            summary[tool] = {
                'recall': found / len(tool_results),
                'mrr': mrr,
                'avg_latency_ms': avg_latency,
                'total_output_bytes': total_bytes,
                'total_results': sum(r['num_results'] for r in tool_results),
            }
            
            print(f"\n{tool}:")
            print(f"  Recall: {found}/{len(tool_results)} ({found/len(tool_results)*100:.1f}%)")
            print(f"  MRR: {mrr:.3f}")
            print(f"  Avg Latency: {avg_latency:.2f}ms")
            print(f"  Total Output: {total_bytes} bytes")
    
    # Save
    output = {
        'repo': args.repo_name,
        'num_tasks': len(tasks),
        'summary': summary,
        'detailed_results': all_results,
    }
    Path(args.output).write_text(json.dumps(output, indent=2))
    print(f"\nSaved to: {args.output}")


if __name__ == '__main__':
    main()
