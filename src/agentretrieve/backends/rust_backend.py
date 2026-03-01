#!/usr/bin/env python3
"""Rust backend placeholder.

This adapter intentionally fails fast until the Rust engine is implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..index.inverted import InvertedIndex
from ..query.engine import SearchPage, SearchResult


class RustBackend:
    """Reserved backend id for upcoming Rust engine."""

    name = "rust"

    def _unsupported(self) -> None:
        raise RuntimeError(
            "Rust backend is not implemented yet. Use '--engine py' or AR_ENGINE=py."
        )

    def build_index(self, root: Path, pattern_csv: str) -> InvertedIndex:
        self._unsupported()
        raise AssertionError("unreachable")

    def load_index(self, index_path: Path) -> InvertedIndex:
        self._unsupported()
        raise AssertionError("unreachable")

    def save_index(self, index: InvertedIndex, output_path: Path) -> None:
        self._unsupported()

    def set_bm25(self, index: InvertedIndex, *, k1: float, b: float) -> None:
        self._unsupported()

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
        self._unsupported()
        raise AssertionError("unreachable")

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
        self._unsupported()
        raise AssertionError("unreachable")
