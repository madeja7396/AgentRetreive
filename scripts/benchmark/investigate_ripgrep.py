#!/usr/bin/env python3
"""Investigate ripgrep timeout issues."""

import subprocess
import time
import sys
from pathlib import Path

def test_rg(repo_path, pattern, timeout=5, options=None):
    """Test rg with various options."""
    cmd = ['rg', '-i', pattern]
    if options:
        cmd.extend(options)
    
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=timeout)
        elapsed = time.perf_counter() - start
        return {
            'success': True,
            'returncode': result.returncode,
            'stdout_lines': len(result.stdout.strip().split('\n')) if result.stdout else 0,
            'stderr': result.stderr[:200] if result.stderr else '',
            'elapsed_ms': elapsed * 1000,
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'TIMEOUT',
            'elapsed_ms': timeout * 1000,
        }

def main():
    repos = ['fd', 'ripgrep', 'fzf', 'fmt']
    
    print('=== RIPGREP TIMEOUT INVESTIGATION ===\n')
    
    for repo in repos:
        repo_path = Path(f'artifacts/datasets/raw/{repo}')
        if not repo_path.exists():
            continue
        
        print(f'--- Repository: {repo} ---')
        
        # Test different patterns
        patterns = ['smart', 'default', 'function', 'test']
        
        for pattern in patterns:
            print(f'\nPattern: "{pattern}"')
            
            # Test 1: Basic (current implementation)
            r1 = test_rg(repo_path, pattern, timeout=3, options=['--max-count', '20'])
            status1 = 'OK' if r1['success'] else 'TIMEOUT'
            print(f'  Basic: {status1} ({r1["elapsed_ms"]:.1f}ms)')
            
            # Test 2: With --no-ignore
            r2 = test_rg(repo_path, pattern, timeout=3, options=['--no-ignore', '--max-count', '20'])
            status2 = 'OK' if r2['success'] else 'TIMEOUT'
            print(f'  No-ignore: {status2} ({r2["elapsed_ms"]:.1f}ms)')
            
            # Test 3: Fixed string (-F)
            r3 = test_rg(repo_path, pattern, timeout=3, options=['-F', '--max-count', '20'])
            status3 = 'OK' if r3['success'] else 'TIMEOUT'
            print(f'  Fixed string: {status3} ({r3["elapsed_ms"]:.1f}ms)')
            
            # Test 4: File type filter
            if repo in ['fd', 'ripgrep']:
                r4 = test_rg(repo_path, pattern, timeout=3, options=['-t', 'rust', '--max-count', '20'])
            elif repo == 'fzf':
                r4 = test_rg(repo_path, pattern, timeout=3, options=['-t', 'go', '--max-count', '20'])
            else:
                r4 = test_rg(repo_path, pattern, timeout=3, options=['-g', '*.md', '--max-count', '20'])
            status4 = 'OK' if r4['success'] else 'TIMEOUT'
            print(f'  Type filter: {status4} ({r4["elapsed_ms"]:.1f}ms)')
        
        print()

if __name__ == '__main__':
    main()
