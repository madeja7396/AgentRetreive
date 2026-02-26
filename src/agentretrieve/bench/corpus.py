#!/usr/bin/env python3
"""AgentRetrieve benchmark corpus: dataset management for evaluation."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class Corpus:
    """A corpus entry for benchmarking."""
    id: str
    url: str
    commit: str
    tag: str
    license: str
    primary_language: str
    notes: str


@dataclass
class Task:
    """A benchmark task with gold standard."""
    id: str
    repo: str
    query_nl: str
    query_dsl: dict
    gold: dict


class CorpusManager:
    """Manages benchmark corpora and tasks."""
    
    def __init__(self, root: Path):
        self.root = root
        self.datasets_dir = root / "artifacts" / "datasets"
        self.raw_dir = self.datasets_dir / "raw"
        self.processed_dir = self.datasets_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def load_corpus_manifest(self, manifest_path: Path | None = None) -> list[Corpus]:
        """Load corpus manifest from docs/benchmarks."""
        if manifest_path is None:
            v11 = self.root / "docs" / "benchmarks" / "corpus.v1.1.json"
            manifest_path = v11 if v11.exists() else self.root / "docs" / "benchmarks" / "corpus.v1.json"
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        return [
            Corpus(
                id=c['id'],
                url=c['url'],
                commit=c['commit'],
                tag=c['tag'],
                license=c['license'],
                primary_language=c['primary_language'],
                notes=c['notes'],
            )
            for c in data['corpora']
        ]
    
    def load_tasks(self, taskset_path: Path | None = None) -> list[Task]:
        """Load benchmark tasks from docs/benchmarks."""
        if taskset_path is None:
            v2 = self.root / "docs" / "benchmarks" / "taskset.v2.full.jsonl"
            taskset_path = v2 if v2.exists() else self.root / "docs" / "benchmarks" / "taskset.v1.jsonl"
        tasks = []
        with open(taskset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                tasks.append(Task(
                    id=data['id'],
                    repo=data['repo'],
                    query_nl=data['query_nl'],
                    query_dsl=data['query_dsl'],
                    gold=data['gold'],
                ))
        return tasks
    
    def clone_or_update_corpus(self, corpus: Corpus) -> Path:
        """Clone or update a corpus repository.
        
        Returns:
            Path to the cloned repository
        """
        repo_dir = self.raw_dir / corpus.id
        clone_timeout_sec = int(os.getenv("AR_CLONE_TIMEOUT_SEC", "1800"))
        
        if repo_dir.exists():
            # Verify commit matches
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
            )
            current_commit = result.stdout.strip() if result.returncode == 0 else None
            if current_commit == corpus.commit:
                return repo_dir
            # Commit mismatch, reclone
            subprocess.run(['rm', '-rf', str(repo_dir)], check=True)
        
        # Clone specific commit
        print(f"Cloning {corpus.id} at {corpus.commit} (timeout={clone_timeout_sec}s)...")
        clone_cmd = [
            'git', 'clone', '--depth', '1',
            '--branch', corpus.tag,
            corpus.url, str(repo_dir)
        ]
        for attempt in range(2):
            try:
                # Stream git output to avoid opaque long waits on large repositories.
                subprocess.run(clone_cmd, check=True, timeout=clone_timeout_sec)
                break
            except subprocess.TimeoutExpired as exc:
                if repo_dir.exists():
                    subprocess.run(['rm', '-rf', str(repo_dir)], check=True)
                if attempt == 0:
                    print(
                        f"[clone-timeout] {corpus.id} exceeded {clone_timeout_sec}s; retrying once..."
                    )
                    continue
                raise RuntimeError(
                    f"Clone timed out for {corpus.id} after {clone_timeout_sec}s (retried once)"
                ) from exc
            except subprocess.CalledProcessError as exc:
                if repo_dir.exists():
                    subprocess.run(['rm', '-rf', str(repo_dir)], check=True)
                if attempt == 0:
                    print(
                        f"[clone-error] {corpus.id} clone failed (rc={exc.returncode}); retrying once..."
                    )
                    continue
                raise RuntimeError(
                    f"Clone failed for {corpus.id} after retry (rc={exc.returncode})"
                ) from exc
        
        return repo_dir
    
    def get_corpus_files(self, corpus_id: str, pattern: str = "*") -> Iterator[Path]:
        """Get files from a corpus."""
        repo_dir = self.raw_dir / corpus_id
        if not repo_dir.exists():
            return
        for path in repo_dir.rglob(pattern):
            if path.is_file():
                yield path
