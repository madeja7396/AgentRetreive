#!/usr/bin/env python3
"""AgentRetrieve inverted index: file-granularity inverted index with BM25 scoring."""

from __future__ import annotations

import ast
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterator

from .tokenizer import normalize_term, tokenize_line


@dataclass
class Posting:
    """A posting entry: document ID with term frequency."""
    doc_id: int
    tf: int  # term frequency in document
    lines: list[int] = field(default_factory=list)  # unique line numbers containing term


@dataclass 
class IndexEntry:
    """Index entry for a term: document frequency and posting list."""
    df: int = 0  # document frequency
    postings: list[Posting] = field(default_factory=list)


@dataclass
class Document:
    """Document metadata."""
    doc_id: int
    path: str
    lang: str | None
    size_bytes: int
    line_count: int
    doc_length: int  # token count
    content_hash: str  # for change detection
    block_regions: list[tuple[int, int]] = field(default_factory=list)
    symbol_regions: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class InvertedIndex:
    """File-granularity inverted index with BM25 parameters."""

    _RE_SYMBOL_DECL = re.compile(
        r"^\s*(def|class|fn|func|function|interface|struct|enum|impl|type)\b",
        re.IGNORECASE,
    )
    _BRACE_LANGS = {
        "c",
        "cpp",
        "cxx",
        "cc",
        "rust",
        "go",
        "java",
        "javascript",
        "typescript",
    }
    
    # Index data
    documents: dict[int, Document] = field(default_factory=dict)
    index: dict[str, IndexEntry] = field(default_factory=dict)
    
    # Statistics
    total_docs: int = 0
    total_terms: int = 0
    avg_doc_length: float = 0.0
    
    # BM25 parameters (tuned for code search)
    k1: float = 1.2
    b: float = 0.75
    
    # Internal
    _next_doc_id: int = 0
    _corpus_fingerprint_cache: str | None = None
    source_root: str | None = None
    
    def add_document(self, path: str, content: str, lang: str | None = None) -> int:
        """Add a document to the index.
        
        Args:
            path: Document path (relative or absolute)
            content: Document content
            lang: Language identifier (optional)
        
        Returns:
            Assigned document ID
        """
        # Generate content hash for change detection
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        
        lines = content.split('\n')
        
        # Assign doc_id
        doc_id = self._next_doc_id
        self._next_doc_id += 1
        
        # Build term frequency map + line map in one pass
        term_counts: dict[str, int] = {}
        term_lines: dict[str, set[int]] = defaultdict(set)
        doc_length = 0
        for line_no, line in enumerate(lines, start=1):
            for token in tokenize_line(line):
                term = token.text
                term_counts[term] = term_counts.get(term, 0) + 1
                term_lines[term].add(line_no)
                doc_length += 1

        block_regions = self._extract_block_regions(
            content=content,
            lines=lines,
            lang=lang,
        )
        symbol_regions = self._extract_symbol_regions(
            content=content,
            lines=lines,
            lang=lang,
            block_regions=block_regions,
        )

        # Create document record
        doc = Document(
            doc_id=doc_id,
            path=path,
            lang=lang,
            size_bytes=len(content.encode('utf-8')),
            line_count=len(lines),
            doc_length=doc_length,
            content_hash=content_hash,
            block_regions=block_regions,
            symbol_regions=symbol_regions,
        )
        self.documents[doc_id] = doc

        # Update index
        for term, tf in term_counts.items():
            entry = self.index.get(term)
            if entry is None:
                entry = IndexEntry()
                self.index[term] = entry
            entry.df += 1
            entry.postings.append(
                Posting(doc_id=doc_id, tf=tf, lines=sorted(term_lines.get(term, set())))
            )
        
        # Update statistics
        self.total_docs += 1
        self.total_terms += doc_length
        self.avg_doc_length = self.total_terms / self.total_docs if self.total_docs > 0 else 0.0
        self._corpus_fingerprint_cache = None
        
        return doc_id
    
    def bm25_score(self, term: str, doc_id: int, doc_tf: int) -> float:
        """Calculate BM25 score for a term in a document.
        
        Args:
            term: The query term
            doc_id: Document ID
            doc_tf: Term frequency in document
        
        Returns:
            BM25 score component for this term
        """
        entry = self.index.get(term)
        if entry is None or entry.df == 0:
            return 0.0
        
        # IDF calculation
        idf = math.log(
            (self.total_docs - entry.df + 0.5) / (entry.df + 0.5) + 1.0
        )
        
        # Document length normalization
        doc = self.documents.get(doc_id)
        if doc is None:
            return 0.0
        
        doc_len = doc.doc_length
        
        # TF normalization
        tf_norm = doc_tf * (self.k1 + 1) / (
            doc_tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
        ) if self.avg_doc_length > 0 else doc_tf
        
        return idf * tf_norm
    
    def query_term(self, term: str) -> Iterator[tuple[int, float]]:
        """Query a single term, yielding (doc_id, score) pairs.
        
        Args:
            term: Normalized query term
        
        Yields:
            Tuples of (doc_id, bm25_score)
        """
        term = normalize_term(term)
        entry = self.index.get(term)
        if entry is None:
            return
        
        for posting in entry.postings:
            score = self.bm25_score(term, posting.doc_id, posting.tf)
            yield (posting.doc_id, score)

    def document_ids_for_term(self, term: str) -> set[int]:
        """Return document ids that contain the term."""
        term = normalize_term(term)
        entry = self.index.get(term)
        if entry is None:
            return set()
        return {posting.doc_id for posting in entry.postings}

    def get_posting(self, term: str, doc_id: int) -> Posting | None:
        """Get posting for a term in a specific document."""
        term = normalize_term(term)
        entry = self.index.get(term)
        if entry is None:
            return None
        for posting in entry.postings:
            if posting.doc_id == doc_id:
                return posting
        return None

    def get_term_lines(self, term: str, doc_id: int) -> list[int]:
        """Get sorted line numbers where term appears in the document."""
        posting = self.get_posting(term, doc_id)
        if posting is None:
            return []
        return posting.lines
    
    def get_document(self, doc_id: int) -> Document | None:
        """Get document metadata by ID."""
        return self.documents.get(doc_id)

    def get_scope_regions(self, doc_id: int, scope: str) -> list[tuple[int, int]]:
        """Return structural regions for a scope in the document.

        - block: non-empty paragraph-like regions
        - symbol: declaration regions (fallback: block regions)
        """
        doc = self.documents.get(doc_id)
        if doc is None:
            return []
        if scope == "block":
            return doc.block_regions or self._fallback_regions(doc.line_count)
        if scope == "symbol":
            return (
                doc.symbol_regions
                or doc.block_regions
                or self._fallback_regions(doc.line_count)
            )
        return self._fallback_regions(doc.line_count)

    def corpus_fingerprint(self) -> str:
        """Stable fingerprint of indexed corpus content and identities."""
        if self._corpus_fingerprint_cache is not None:
            return self._corpus_fingerprint_cache
        parts: list[str] = []
        for doc_id in sorted(self.documents.keys()):
            doc = self.documents[doc_id]
            parts.append(
                f"{doc_id}|{doc.path}|{doc.content_hash}|{doc.size_bytes}|{doc.line_count}|{doc.doc_length}"
            )
        raw = "\n".join(parts)
        self._corpus_fingerprint_cache = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
        return self._corpus_fingerprint_cache

    @classmethod
    def _fallback_regions(cls, line_count: int) -> list[tuple[int, int]]:
        if line_count <= 0:
            return []
        return [(1, line_count)]

    @classmethod
    def _extract_block_regions_by_blank(cls, lines: list[str]) -> list[tuple[int, int]]:
        """Language-agnostic block extraction by blank-line segmentation."""
        regions: list[tuple[int, int]] = []
        start: int | None = None
        for line_no, line in enumerate(lines, start=1):
            if line.strip():
                if start is None:
                    start = line_no
            elif start is not None:
                regions.append((start, line_no - 1))
                start = None
        if start is not None:
            regions.append((start, len(lines)))
        return regions or cls._fallback_regions(len(lines))

    @classmethod
    def _extract_brace_regions(cls, lines: list[str]) -> list[tuple[int, int]]:
        """Extract nested brace-delimited regions for brace-based languages."""
        stack: list[int] = []
        regions: list[tuple[int, int]] = []
        for line_no, line in enumerate(lines, start=1):
            for ch in line:
                if ch == "{":
                    stack.append(line_no)
                elif ch == "}" and stack:
                    start = stack.pop()
                    if line_no >= start:
                        regions.append((start, line_no))
        return sorted(regions)

    @classmethod
    def _extract_python_block_regions(
        cls,
        content: str,
        line_count: int,
    ) -> list[tuple[int, int]]:
        regions: list[tuple[int, int]] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            body = getattr(node, "body", None)
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and isinstance(body, list)
                and end >= start
            ):
                regions.append((start, end))
        return regions

    @classmethod
    def _extract_python_symbol_regions(
        cls,
        content: str,
        line_count: int,
        fallback: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        regions: list[tuple[int, int]] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return fallback
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, "lineno", None)
                end = getattr(node, "end_lineno", None)
                if isinstance(start, int) and isinstance(end, int) and end >= start:
                    regions.append((start, end))
        return cls._normalize_regions(regions, line_count, fallback=fallback)

    @classmethod
    def _extract_symbol_regions_by_regex(
        cls,
        lines: list[str],
        block_regions: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Fallback symbol extraction based on declaration-like line starters."""
        starts = [
            line_no
            for line_no, line in enumerate(lines, start=1)
            if cls._RE_SYMBOL_DECL.match(line)
        ]
        if not starts:
            return block_regions

        regions: list[tuple[int, int]] = []
        for idx, start in enumerate(starts):
            end = starts[idx + 1] - 1 if idx + 1 < len(starts) else len(lines)
            if end >= start:
                regions.append((start, end))
        return regions or block_regions

    @classmethod
    def _extract_block_regions(
        cls,
        content: str,
        lines: list[str],
        lang: str | None,
    ) -> list[tuple[int, int]]:
        line_count = len(lines)
        lang_norm = (lang or "").lower()
        if lang_norm == "python":
            return cls._normalize_regions(
                cls._extract_python_block_regions(content, line_count),
                line_count,
                fallback=cls._extract_block_regions_by_blank(lines),
            )
        if lang_norm in cls._BRACE_LANGS:
            brace_regions = cls._extract_brace_regions(lines)
            return cls._normalize_regions(
                brace_regions,
                line_count,
                fallback=cls._extract_block_regions_by_blank(lines),
            )
        return cls._extract_block_regions_by_blank(lines)

    @classmethod
    def _extract_symbol_regions(
        cls,
        content: str,
        lines: list[str],
        lang: str | None,
        block_regions: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        line_count = len(lines)
        lang_norm = (lang or "").lower()
        if lang_norm == "python":
            return cls._extract_python_symbol_regions(content, line_count, fallback=block_regions)
        if lang_norm in cls._BRACE_LANGS:
            return cls._normalize_regions(
                cls._extract_symbol_regions_by_regex(lines, block_regions),
                line_count,
                fallback=block_regions,
            )
        return cls._extract_symbol_regions_by_regex(lines, block_regions)

    @classmethod
    def _normalize_regions(
        cls,
        raw_regions: object,
        line_count: int,
        fallback: list[tuple[int, int]] | None = None,
    ) -> list[tuple[int, int]]:
        regions: list[tuple[int, int]] = []
        if isinstance(raw_regions, list):
            for raw in raw_regions:
                if isinstance(raw, dict):
                    start = raw.get("start")
                    end = raw.get("end")
                elif isinstance(raw, (list, tuple)) and len(raw) == 2:
                    start, end = raw
                else:
                    continue
                if not isinstance(start, int) or not isinstance(end, int):
                    continue
                if line_count > 0:
                    start = max(1, min(start, line_count))
                    end = max(1, min(end, line_count))
                if end >= start:
                    regions.append((start, end))
        if regions:
            return regions
        if fallback is not None:
            return fallback
        return cls._fallback_regions(line_count)
    
    def save(self, path: Path) -> None:
        """Save index to disk.
        
        Args:
            path: Output file path
        """
        data = {
            'version': 'inverted.v2',
            'source_root': self.source_root,
            'documents': [
                {
                    'doc_id': d.doc_id,
                    'path': d.path,
                    'lang': d.lang,
                    'size_bytes': d.size_bytes,
                    'line_count': d.line_count,
                    'doc_length': d.doc_length,
                    'content_hash': d.content_hash,
                    'block_regions': [
                        {'start': start, 'end': end}
                        for start, end in d.block_regions
                    ],
                    'symbol_regions': [
                        {'start': start, 'end': end}
                        for start, end in d.symbol_regions
                    ],
                }
                for d in self.documents.values()
            ],
            'index': {
                term: {
                    'df': entry.df,
                    'postings': [
                        {'doc_id': p.doc_id, 'tf': p.tf, 'lines': p.lines}
                        for p in entry.postings
                    ],
                }
                for term, entry in self.index.items()
            },
            'stats': {
                'total_docs': self.total_docs,
                'total_terms': self.total_terms,
                'avg_doc_length': self.avg_doc_length,
                'corpus_fingerprint': self.corpus_fingerprint(),
            },
            'bm25': {
                'k1': self.k1,
                'b': self.b,
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    @classmethod
    def load(cls, path: Path) -> 'InvertedIndex':
        """Load index from disk.
        
        Args:
            path: Index file path
        
        Returns:
            Loaded InvertedIndex
        """
        data = json.loads(path.read_text(encoding='utf-8'))
        
        idx = cls()
        idx.k1 = data['bm25']['k1']
        idx.b = data['bm25']['b']
        idx.total_docs = data['stats']['total_docs']
        idx.total_terms = data['stats']['total_terms']
        idx.avg_doc_length = data['stats']['avg_doc_length']
        idx.source_root = data.get('source_root')
        idx._corpus_fingerprint_cache = data.get('stats', {}).get('corpus_fingerprint')
        
        for d in data['documents']:
            doc = Document(
                doc_id=d['doc_id'],
                path=d['path'],
                lang=d['lang'],
                size_bytes=d['size_bytes'],
                line_count=d['line_count'],
                doc_length=d.get('doc_length', 0),
                content_hash=d['content_hash'],
                block_regions=[],
                symbol_regions=[],
            )
            doc.block_regions = cls._normalize_regions(
                d.get('block_regions'),
                doc.line_count,
            )
            doc.symbol_regions = cls._normalize_regions(
                d.get('symbol_regions'),
                doc.line_count,
                fallback=doc.block_regions,
            )
            idx.documents[doc.doc_id] = doc
            idx._next_doc_id = max(idx._next_doc_id, doc.doc_id + 1)

        for term, entry_data in data['index'].items():
            entry = IndexEntry(df=entry_data['df'])
            for p in entry_data['postings']:
                entry.postings.append(
                    Posting(
                        doc_id=p['doc_id'],
                        tf=p['tf'],
                        lines=sorted({int(ln) for ln in p.get('lines', []) if int(ln) >= 1}),
                    )
                )
            idx.index[term] = entry

        # Backward compatibility for older index files without doc_length.
        if any(doc.doc_length <= 0 for doc in idx.documents.values()):
            doc_lengths: dict[int, int] = defaultdict(int)
            for entry in idx.index.values():
                for posting in entry.postings:
                    doc_lengths[posting.doc_id] += posting.tf
            for doc in idx.documents.values():
                if doc.doc_length <= 0:
                    doc.doc_length = doc_lengths.get(doc.doc_id, 0)
            idx._corpus_fingerprint_cache = None

        return idx
