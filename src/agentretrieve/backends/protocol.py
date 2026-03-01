#!/usr/bin/env python3
"""Backend protocol for pluggable retrieval engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from ..index.inverted import InvertedIndex
from ..query.engine import SearchPage, SearchResult


class RetrievalBackend(Protocol):
    """Common interface for Python/Rust retrieval backends."""

    name: str

    def build_index(self, root: Path, pattern_csv: str) -> InvertedIndex:
        """Build an index from source tree."""

    def load_index(self, index_path: Path) -> InvertedIndex:
        """Load index artifact."""

    def save_index(self, index: InvertedIndex, output_path: Path) -> None:
        """Persist index artifact."""

    def set_bm25(self, index: InvertedIndex, *, k1: float, b: float) -> None:
        """Set scoring parameters for queries."""

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
        """Execute search and return first page."""

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
        """Execute cursor-aware search."""
