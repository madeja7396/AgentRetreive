#!/usr/bin/env python3
"""Python backend using existing InvertedIndex + QueryEngine implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..index.inverted import InvertedIndex
from ..query.engine import QueryEngine, SearchPage, SearchResult

_DEFAULT_PATTERN = (
    "*.py,*.pyi,*.js,*.jsx,*.mjs,*.cjs,*.ts,*.tsx,*.mts,*.cts,*.rs,*.go,*.cs,*.php,"
    "*.rb,*.kt,*.kts,*.swift,*.dart,*.hs,*.lhs,*.ex,*.exs,*.c,*.h,*.cpp,*.cc,*.cxx,"
    "*.hpp,*.java,*.md"
)


class PythonBackend:
    """Reference backend implemented fully in Python."""

    name = "py"

    @staticmethod
    def _detect_lang(ext: str) -> str | None:
        lang_map = {
            ".py": "python",
            ".pyi": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mts": "typescript",
            ".cts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".swift": "swift",
            ".dart": "dart",
            ".hs": "haskell",
            ".lhs": "haskell",
            ".ex": "elixir",
            ".exs": "elixir",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".java": "java",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }
        return lang_map.get(ext.lower())

    @staticmethod
    def _collect_files(root: Path, pattern_csv: str) -> list[Path]:
        files: set[Path] = set()
        patterns = [part.strip() for part in pattern_csv.split(",") if part.strip()]
        for pattern in patterns:
            for path in root.rglob(pattern):
                if path.is_file():
                    files.add(path)
        return sorted(files, key=lambda p: str(p.relative_to(root)))

    def build_index(self, root: Path, pattern_csv: str = _DEFAULT_PATTERN) -> InvertedIndex:
        idx = InvertedIndex()
        idx.source_root = str(root.resolve())
        for path in self._collect_files(root, pattern_csv):
            content = path.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(path.relative_to(root))
            idx.add_document(rel_path, content, lang=self._detect_lang(path.suffix))
        return idx

    def load_index(self, index_path: Path) -> InvertedIndex:
        return InvertedIndex.load(index_path)

    def save_index(self, index: InvertedIndex, output_path: Path) -> None:
        index.save(output_path)

    def set_bm25(self, index: InvertedIndex, *, k1: float, b: float) -> None:
        index.k1 = float(k1)
        index.b = float(b)

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
        engine = QueryEngine(index)
        return engine.search(
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
        )

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
        engine = QueryEngine(index)
        return engine.search_page(
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
            cursor=cursor,
        )
