#!/usr/bin/env python3
"""Rust backend CLI bridge.

This adapter invokes the Rust ar-cli binary for index operations and search.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from ..index.inverted import InvertedIndex
from ..query.engine import SearchPage, SearchResult


def _ar_cli_path() -> str:
    """Locate ar-cli binary."""
    # Check environment override first
    if path := os.environ.get("AR_CLI_PATH"):
        return path
    
    # Try target/release/ar-cli relative to project root
    project_root = Path(__file__).parent.parent.parent.parent
    cli_path = project_root / "target" / "release" / "ar-cli"
    if cli_path.exists():
        return str(cli_path)
    
    # Try target/debug/ar-cli
    cli_path = project_root / "target" / "debug" / "ar-cli"
    if cli_path.exists():
        return str(cli_path)
    
    raise RuntimeError(
        "ar-cli binary not found. Set AR_CLI_PATH or build with: cargo build --release -p ar-cli"
    )


class RustBackend:
    """Rust engine backend via CLI bridge."""

    name = "rust"

    def __init__(self) -> None:
        self._cli = _ar_cli_path()

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute ar-cli with given args."""
        cmd = [self._cli] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def build_index(self, root: Path, pattern_csv: str) -> InvertedIndex:
        """Build an index from source tree via Rust CLI."""
        # Build binary index first
        output_path = Path("/tmp") / f"ar_index_{os.getpid()}.bin"
        
        # Parse patterns
        patterns = pattern_csv.split(",") if pattern_csv else ["*.py", "*.rs", "*.go", "*.c", "*.cpp", "*.h"]
        
        # Run ar-cli ix build
        result = self._run([
            "ix", "build",
            "--source", str(root),
            "--output", str(output_path),
            "--patterns", ",".join(patterns)
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Index build failed: {result.stderr}")
        
        # Load the resulting binary index and convert to Python InvertedIndex
        # For now, return a placeholder that will be loaded via load_index
        return self.load_index(output_path)

    def load_index(self, index_path: Path) -> InvertedIndex:
        """Load index artifact."""
        # Binary index loaded by Rust; we keep the path for subsequent operations
        idx = InvertedIndex(documents={}, index={})
        idx._rust_index_path = index_path  # type: ignore
        return idx

    def save_index(self, index: InvertedIndex, output_path: Path) -> None:
        """Persist index artifact (handled by Rust during build)."""
        if hasattr(index, '_rust_index_path'):
            import shutil
            shutil.copy(index._rust_index_path, output_path)

    def set_bm25(self, index: InvertedIndex, *, k1: float, b: float) -> None:
        """Set scoring parameters (stored for search calls)."""
        index.k1 = k1  # type: ignore
        index.b = b    # type: ignore

    def search(
        self,
        index: InvertedIndex,
        *,
        must: list[str],
        should: list[str],
        not_terms: list[str],
        max_results: int,
        max_hits: int,
        min_match: int,
        near: list[dict[str, Any]] | None = None,
        lang: list[str] | None = None,
        ext: list[str] | None = None,
        path_prefix: list[str] | None = None,
        symbol: list[str] | None = None,
    ) -> list[SearchResult]:
        """Execute search via Rust CLI."""
        page = self.search_page(
            index,
            must=must,
            should=should,
            not_terms=not_terms,
            max_results=max_results,
            max_hits=max_hits,
            min_match=min_match,
            near=near,
            lang=lang,
            ext=ext,
            path_prefix=path_prefix,
            symbol=symbol,
            cursor=None,
        )
        return page.results

    def search_page(
        self,
        index: InvertedIndex,
        *,
        must: list[str],
        should: list[str],
        not_terms: list[str],
        max_results: int,
        max_hits: int,
        min_match: int,
        near: list[dict[str, Any]] | None = None,
        lang: list[str] | None = None,
        ext: list[str] | None = None,
        path_prefix: list[str] | None = None,
        symbol: list[str] | None = None,
        cursor: str | None = None,
    ) -> SearchPage:
        """Execute cursor-aware search via Rust CLI."""
        index_path = getattr(index, '_rust_index_path', None)
        if not index_path:
            raise RuntimeError("No index loaded. Call build_index or load_index first.")

        # Build query args
        args = [
            "q",
            "--index", str(index_path),
            "--max-results", str(max_results),
            "--min-match", str(min_match),
            "--max-hits", str(max_hits),
        ]

        if must:
            args.extend(["--must", " ".join(must)])
        if should:
            args.extend(["--should", " ".join(should)])
        if not_terms:
            args.extend(["--not", " ".join(not_terms)])
        if symbol:
            args.extend(["--symbol", " ".join(symbol)])

        # Execute search
        result = self._run(args)
        
        if result.returncode != 0:
            raise RuntimeError(f"Search failed: {result.stderr}")

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON output from ar-cli: {e}")

        # Convert to SearchResult objects
        results = []
        for r in data.get("results", []):
            results.append(SearchResult(
                doc_id=r["doc_id"],
                score=r["score"],
                hits=r["hits"],
                rng=tuple(r["range"]),
                span_id=r.get("span_id"),
                capability=r.get("capability"),
            ))

        return SearchPage(
            results=results,
            total=data.get("total", len(results)),
            next_cursor=data.get("next_cursor"),
        )
