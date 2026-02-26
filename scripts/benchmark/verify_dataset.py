#!/usr/bin/env python3
"""Verify dataset integrity: check gold files and anchors exist."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_taskset(path: Path) -> list[dict]:
    tasks = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def verify_task(task: dict, repo_root: Path) -> dict:
    """Verify a single task's gold data exists."""
    repo = task['repo']
    gold = task['gold']
    gold_file = gold['file']
    anchor = gold.get('anchor', '')
    
    result = {
        'task_id': task['id'],
        'repo': repo,
        'gold_file': gold_file,
        'anchor': anchor[:50] + '...' if len(anchor) > 50 else anchor,
        'file_exists': False,
        'anchor_found': False,
        'issues': [],
    }
    
    # Check file exists
    file_path = repo_root / repo / gold_file
    if not file_path.exists():
        # Try case-insensitive search
        parent = file_path.parent
        if parent.exists():
            for f in parent.iterdir():
                if f.name.lower() == gold_file.lower():
                    result['issues'].append(f'Case mismatch: expected {gold_file}, found {f.name}')
                    file_path = f
                    break
        else:
            result['issues'].append(f'Parent directory not found: {parent}')
            return result
    
    if not file_path.exists():
        result['issues'].append(f'File not found: {gold_file}')
        return result
    
    result['file_exists'] = True
    
    # Check anchor exists
    if anchor:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if anchor in content:
                result['anchor_found'] = True
            else:
                # Try partial match
                anchor_words = anchor.split()[:5]  # First 5 words
                partial = ' '.join(anchor_words)
                if partial in content:
                    result['issues'].append(f'Partial anchor match only (first 5 words)')
                    result['anchor_found'] = True  # Partial success
                else:
                    result['issues'].append(f'Anchor not found in file')
        except Exception as e:
            result['issues'].append(f'Error reading file: {e}')
    
    return result


def main() -> int:
    taskset_path = Path('docs/benchmarks/taskset.v2.jsonl')
    repo_root = Path('artifacts/datasets/raw')
    
    tasks = load_taskset(taskset_path)
    
    print('=' * 80)
    print('DATASET VERIFICATION REPORT')
    print('=' * 80)
    
    all_issues = []
    file_dist = {}  # Distribution of gold files
    
    for task in tasks:
        result = verify_task(task, repo_root)
        
        # Track file distribution
        gold_file = result['gold_file']
        file_dist[gold_file] = file_dist.get(gold_file, 0) + 1
        
        # Report issues
        if result['issues']:
            all_issues.append(result)
            print(f"\n[{result['task_id']}] {result['repo']}")
            print(f"  File: {result['gold_file']} {'✓' if result['file_exists'] else '✗'}")
            print(f"  Anchor: {'✓' if result['anchor_found'] else '✗'}")
            for issue in result['issues']:
                print(f"  ⚠ {issue}")
    
    # Summary
    print('\n' + '=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f"Total tasks: {len(tasks)}")
    print(f"Tasks with issues: {len(all_issues)}")
    
    print('\nGold file distribution (bias check):')
    for f, count in sorted(file_dist.items(), key=lambda x: -x[1]):
        pct = count / len(tasks) * 100
        bar = '█' * int(pct / 5)
        print(f"  {f:20s}: {count:2d} ({pct:5.1f}%) {bar}")
    
    # Bias warnings
    print('\nBias analysis:')
    readme_pct = file_dist.get('README.md', 0) / len(tasks) * 100
    if readme_pct > 60:
        print(f"  ⚠ WARNING: {readme_pct:.1f}% tasks target README.md (potential bias)")
        print(f"    Consider diversifying target files (docs/, src/, etc.)")
    
    if len(all_issues) > 0:
        print(f"\n⚠ {len(all_issues)} tasks have verification failures")
        return 1
    else:
        print(f"\n✓ All {len(tasks)} tasks verified successfully")
        return 0


if __name__ == '__main__':
    sys.exit(main())
