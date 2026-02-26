#!/usr/bin/env python3
"""AgentRetrieve query engine: DSL execution with BM25 ranking."""

from __future__ import annotations

import hashlib
import heapq
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..index.inverted import InvertedIndex
from ..index.tokenizer import normalize_term, tokenize_identifier
from .symbol_weights import SymbolLanguageWeights


def _encode_cursor_token(offset: int, signature: str) -> str:
    return f"cur_{offset}_{signature}"


@dataclass(order=True)
class ScoredResult:
    """A scored search result, comparable by score (descending)."""

    # Use negative score for min-heap behavior (higher score = better)
    neg_score: float
    doc_id: int = field(compare=False)
    hits: list[Hit] = field(default_factory=list, compare=False)

    @property
    def score(self) -> float:
        return -self.neg_score


@dataclass
class Hit:
    """A single hit (occurrence) in a document."""

    line: int
    text: str
    score: int  # 0-1000, hit-level score


@dataclass
class SearchResult:
    """Final search result for a document."""

    doc_id: int
    path: str
    score: int  # 0-1000, integer score
    hits: list[Hit]
    rng: Range  # recommended read range
    doc_id_str: str  # capability handle
    span_id: str  # capability handle
    digest: str  # content hash
    bounds: Bounds  # line bounds
    next_spans: list[str]  # suggested next spans


@dataclass
class SearchPage:
    """Cursor-aware page of search results."""

    results: list[SearchResult]
    start_offset: int
    total_results: int
    cursor_signature: str

    def next_cursor_for_emitted(self, emitted_count: int) -> str | None:
        if emitted_count < 0:
            raise ValueError("emitted_count must be >= 0")
        if emitted_count > len(self.results):
            raise ValueError("emitted_count cannot exceed returned result count")
        next_offset = self.start_offset + emitted_count
        if next_offset < self.total_results:
            return _encode_cursor_token(next_offset, self.cursor_signature)
        return None


@dataclass
class Range:
    """Recommended read range."""

    from_line: int
    to_line: int


@dataclass
class Bounds:
    """Document bounds for proof-carrying."""

    start: int
    end: int


class QueryEngine:
    """Query engine for executing DSL queries."""

    _RE_CURSOR = re.compile(r"^cur_([0-9]+)_([a-z0-9]+)$")

    def __init__(
        self,
        index: InvertedIndex,
        symbol_weights: SymbolLanguageWeights | None = None,
    ):
        self.index = index
        self.symbol_weights = (
            symbol_weights if symbol_weights is not None else self._load_default_symbol_weights()
        )

    @classmethod
    def _default_symbol_weights_path(cls) -> Path:
        return Path(__file__).resolve().parents[3] / "configs" / "symbol_language_weights.v1.json"

    @classmethod
    def _load_default_symbol_weights(cls) -> SymbolLanguageWeights:
        path = cls._default_symbol_weights_path()
        if not path.exists():
            return SymbolLanguageWeights.disabled()
        try:
            return SymbolLanguageWeights.load(path)
        except Exception:
            # Fail-safe: keep search functional even if config is broken.
            return SymbolLanguageWeights.disabled()

    def search(
        self,
        must: list[str],
        should: list[str],
        not_terms: list[str],
        max_results: int = 20,
        max_hits: int = 10,
        min_match: int = 0,  # Minimum number of should terms to match
        near: list[dict[str, Any]] | None = None,
        lang: list[str] | None = None,
        ext: list[str] | None = None,
        path_prefix: list[str] | None = None,
        symbol: list[str] | None = None,
    ) -> list[SearchResult]:
        """Execute a search query and return first page of results."""
        page = self.search_page(
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
        must: list[str],
        should: list[str],
        not_terms: list[str],
        max_results: int = 20,
        max_hits: int = 10,
        min_match: int = 0,  # Minimum number of should terms to match
        near: list[dict[str, Any]] | None = None,
        lang: list[str] | None = None,
        ext: list[str] | None = None,
        path_prefix: list[str] | None = None,
        symbol: list[str] | None = None,
        cursor: str | None = None,
    ) -> SearchPage:
        """Execute a search query and return a cursor-aware result page."""
        query_state = self._normalize_query_state(
            must=must,
            should=should,
            not_terms=not_terms,
            near=near or [],
            lang=lang or [],
            ext=ext or [],
            path_prefix=path_prefix or [],
            symbol=symbol or [],
            min_match=min_match,
        )

        query_signature = self._make_query_signature(
            query_state=query_state,
            max_hits=max_hits,
        )
        start = self._decode_cursor(cursor, query_signature) if cursor else 0
        needed_count = start + max_results

        ranked_prefix, total_count = self._search_ranked(
            must=query_state["must"],
            should=query_state["should"],
            not_terms=query_state["not_terms"],
            min_match=query_state["min_match"],
            near_clauses=query_state["near_clauses"],
            lang_set=query_state["lang_set"],
            ext_set=query_state["ext_set"],
            path_prefixes=query_state["path_prefixes"],
            symbol_term_sets=query_state["symbol_term_sets"],
            max_hits=max_hits,
            needed_count=needed_count,
        )

        if total_count > 0 and start >= total_count:
            raise ValueError("Cursor offset out of range")

        page_results = ranked_prefix[start:] if start < len(ranked_prefix) else []
        return SearchPage(
            results=page_results,
            start_offset=start,
            total_results=total_count,
            cursor_signature=query_signature,
        )

    def _normalize_query_state(
        self,
        must: list[str],
        should: list[str],
        not_terms: list[str],
        near: list[dict[str, Any]],
        lang: list[str],
        ext: list[str],
        path_prefix: list[str],
        symbol: list[str],
        min_match: int,
    ) -> dict[str, Any]:
        return {
            "must": [normalize_term(t) for t in must],
            "should": [normalize_term(t) for t in should],
            "not_terms": [normalize_term(t) for t in not_terms],
            "near_clauses": self._normalize_near(near),
            "lang_set": {v.lower() for v in lang if isinstance(v, str) and v.strip()},
            "ext_set": {
                v.lower() if v.startswith(".") else f".{v.lower()}"
                for v in ext
                if isinstance(v, str) and v.strip()
            },
            "path_prefixes": [
                self._normalize_path_prefix(v)
                for v in path_prefix
                if isinstance(v, str) and v.strip()
            ],
            "symbol_term_sets": self._normalize_symbol_terms(symbol),
            "min_match": max(0, int(min_match)),
        }

    def _search_ranked(
        self,
        must: list[str],
        should: list[str],
        not_terms: list[str],
        min_match: int,
        near_clauses: list[dict[str, Any]],
        lang_set: set[str],
        ext_set: set[str],
        path_prefixes: list[str],
        symbol_term_sets: list[list[str]],
        max_hits: int,
        needed_count: int,
    ) -> tuple[list[SearchResult], int]:
        # Collect candidate documents.
        candidates: dict[int, float] = {}

        # Must terms: all must be present.
        if must:
            first_term = must[0]
            for doc_id, score in self.index.query_term(first_term):
                candidates[doc_id] = score

            for term in must[1:]:
                term_docs: dict[int, float] = {}
                for doc_id, score in self.index.query_term(term):
                    if doc_id in candidates:
                        term_docs[doc_id] = candidates[doc_id] + score
                candidates = term_docs

        # Should terms: boost score and track matches.
        should_matches: dict[int, int] = {}
        for term in should:
            for doc_id, score in self.index.query_term(term):
                should_matches[doc_id] = should_matches.get(doc_id, 0) + 1
                if doc_id in candidates:
                    candidates[doc_id] += score * 0.5
                elif not must:
                    candidates[doc_id] = candidates.get(doc_id, 0.0) + score * 0.5

        # Symbol constraints:
        # each symbol string => AND across tokenized terms
        # multiple symbols => OR.
        # Symbol strength is scored via language-aware statistical weights.
        symbol_evidence_by_doc: dict[int, float] = {}
        if symbol_term_sets:
            symbol_docs_union: set[int] = set()
            for term_set in symbol_term_sets:
                docs = self._docs_matching_all_terms(term_set)
                symbol_docs_union.update(docs)
                for doc_id in docs:
                    evidence = self._symbol_termset_evidence(doc_id, term_set)
                    if evidence > symbol_evidence_by_doc.get(doc_id, 0.0):
                        symbol_evidence_by_doc[doc_id] = evidence

            if candidates:
                candidates = {
                    doc_id: score
                    for doc_id, score in candidates.items()
                    if doc_id in symbol_docs_union
                }
            else:
                candidates = {doc_id: 0.0 for doc_id in symbol_docs_union}

            for doc_id in list(candidates.keys()):
                doc = self.index.get_document(doc_id)
                lang = doc.lang if doc is not None else None
                weight = self.symbol_weights.weight_for(lang)
                evidence = symbol_evidence_by_doc.get(doc_id, 0.0)
                candidates[doc_id] += weight * evidence

        # Metadata-only / near-only query support.
        has_non_lexical_without_symbol = bool(lang_set or ext_set or path_prefixes or near_clauses)
        if not candidates and not must and not should and has_non_lexical_without_symbol and not symbol_term_sets:
            candidates = {doc_id: 0.0 for doc_id in self.index.documents.keys()}

        # Apply min_match for should terms.
        if should and min_match > 0:
            candidates = {
                doc_id: score
                for doc_id, score in candidates.items()
                if should_matches.get(doc_id, 0) >= min_match
            }

        # Not terms: exclude documents.
        for term in not_terms:
            for doc_id, _ in self.index.query_term(term):
                candidates.pop(doc_id, None)

        # Metadata filters.
        if lang_set or ext_set or path_prefixes:
            filtered: dict[int, float] = {}
            for doc_id, score in candidates.items():
                doc = self.index.get_document(doc_id)
                if doc is None:
                    continue
                if lang_set and (doc.lang or "").lower() not in lang_set:
                    continue
                if ext_set and Path(doc.path).suffix.lower() not in ext_set:
                    continue
                if path_prefixes:
                    path_norm = doc.path.replace("\\", "/")
                    if not any(path_norm.startswith(prefix) for prefix in path_prefixes):
                        continue
                filtered[doc_id] = score
            candidates = filtered

        # Near constraints.
        if near_clauses:
            candidates = {
                doc_id: score
                for doc_id, score in candidates.items()
                if self._satisfies_near_constraints(doc_id, near_clauses)
            }

        # Build scored results.
        scored: list[ScoredResult] = []
        for doc_id, score in candidates.items():
            int_score = max(0, min(1000, int(score * 100)))
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue
            hit = Hit(line=1, text=f"{doc.path}", score=int_score)
            scored.append(ScoredResult(neg_score=-int_score, doc_id=doc_id, hits=[hit]))

        total_count = len(scored)
        if needed_count <= 0 or total_count == 0:
            return [], total_count

        # Partial ranking to avoid full sort when cursor is shallow.
        key_fn = lambda r: (r.neg_score, r.doc_id)
        if needed_count < total_count:
            top_scored = heapq.nsmallest(needed_count, scored, key=key_fn)
        else:
            top_scored = sorted(scored, key=key_fn)

        final_results: list[SearchResult] = []
        for r in top_scored:
            doc = self.index.get_document(r.doc_id)
            if doc is None:
                continue

            rng = Range(from_line=1, to_line=min(50, doc.line_count))
            doc_id_str = f"doc_{r.doc_id:08x}"
            span_id = f"span_{r.doc_id:08x}_001"
            bounds = Bounds(start=1, end=doc.line_count)

            final_results.append(
                SearchResult(
                    doc_id=r.doc_id,
                    path=doc.path,
                    score=int(-r.neg_score),
                    hits=r.hits[:max_hits],
                    rng=rng,
                    doc_id_str=doc_id_str,
                    span_id=span_id,
                    digest=doc.content_hash,
                    bounds=bounds,
                    next_spans=[],
                )
            )

        return final_results, total_count

    def _normalize_path_prefix(self, value: str) -> str:
        prefix = value.strip().replace("\\", "/")
        while prefix.startswith("./"):
            prefix = prefix[2:]
        return prefix

    def _normalize_symbol_terms(self, symbols: list[str]) -> list[list[str]]:
        normalized: list[list[str]] = []
        for raw in symbols:
            chunks = re.findall(r"[A-Za-z0-9_]+", raw)
            terms: list[str] = []
            for chunk in chunks:
                parts = tokenize_identifier(chunk)
                terms.extend(parts if parts else [normalize_term(chunk)])
            deduped = [term for term in dict.fromkeys(terms) if term]
            if deduped:
                normalized.append(deduped)
        return normalized

    def _docs_matching_all_terms(self, terms: list[str]) -> set[int]:
        docs: set[int] | None = None
        for term in terms:
            ids = self.index.document_ids_for_term(term)
            docs = ids if docs is None else docs & ids
            if not docs:
                return set()
        return docs or set()

    def _symbol_termset_evidence(self, doc_id: int, terms: list[str]) -> float:
        """Return symbol-region evidence in [0, 1] for one symbol term-set."""
        regions = self.index.get_scope_regions(doc_id, "symbol")
        if not regions or not terms:
            return 0.0

        term_ratios: list[float] = []
        for term in terms:
            lines = self.index.get_term_lines(term, doc_id)
            if not lines:
                return 0.0
            inside = 0
            for line_no in lines:
                if any(start <= line_no <= end for start, end in regions):
                    inside += 1
            term_ratios.append(inside / len(lines))
        return sum(term_ratios) / len(term_ratios) if term_ratios else 0.0

    def _normalize_near(self, clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for clause in clauses:
            terms_raw = clause.get("terms")
            scope = clause.get("scope")
            window = clause.get("window")
            if (
                not isinstance(terms_raw, list)
                or len(terms_raw) < 2
                or not isinstance(scope, str)
                or not isinstance(window, int)
            ):
                continue
            terms = [normalize_term(t) for t in terms_raw if isinstance(t, str) and t.strip()]
            if len(terms) < 2:
                continue
            normalized.append({"terms": terms, "scope": scope, "window": max(0, window)})
        return normalized

    def _satisfies_near_constraints(self, doc_id: int, clauses: list[dict[str, Any]]) -> bool:
        for clause in clauses:
            if not self._satisfies_single_near_clause(doc_id, clause):
                return False
        return True

    def _satisfies_single_near_clause(self, doc_id: int, clause: dict[str, Any]) -> bool:
        terms = clause["terms"]
        scope = clause["scope"]
        window = clause["window"]

        line_lists: list[list[int]] = []
        for term in terms:
            lines = self.index.get_term_lines(term, doc_id)
            if not lines:
                return False
            line_lists.append(lines)

        if scope == "line_window":
            return self._has_lines_within_window(line_lists, window)

        if scope not in {"block", "symbol"}:
            return False

        # Strict scope matching: every term must appear inside the same
        # block/symbol region before window check is applied.
        regions = self.index.get_scope_regions(doc_id, scope)
        for start, end in regions:
            scoped_lists = [
                [ln for ln in lines if start <= ln <= end]
                for lines in line_lists
            ]
            if any(not scoped for scoped in scoped_lists):
                continue
            if self._has_lines_within_window(scoped_lists, window):
                return True
        return False

    def _has_lines_within_window(self, line_lists: list[list[int]], window: int) -> bool:
        events: list[tuple[int, int]] = []
        for term_idx, lines in enumerate(line_lists):
            events.extend((line_no, term_idx) for line_no in lines)
        events.sort(key=lambda x: x[0])

        term_count = len(line_lists)
        covered = 0
        counts = [0] * term_count
        left = 0

        for right, (line_right, term_idx_right) in enumerate(events):
            if counts[term_idx_right] == 0:
                covered += 1
            counts[term_idx_right] += 1

            while covered == term_count and left <= right:
                line_left = events[left][0]
                if line_right - line_left <= window:
                    return True
                term_idx_left = events[left][1]
                counts[term_idx_left] -= 1
                if counts[term_idx_left] == 0:
                    covered -= 1
                left += 1

        return False

    def _make_query_signature(self, query_state: dict[str, Any], max_hits: int) -> str:
        payload = {
            "must": query_state["must"],
            "should": query_state["should"],
            "not_terms": query_state["not_terms"],
            "near_clauses": query_state["near_clauses"],
            "lang_set": sorted(query_state["lang_set"]),
            "ext_set": sorted(query_state["ext_set"]),
            "path_prefixes": query_state["path_prefixes"],
            "symbol_term_sets": query_state["symbol_term_sets"],
            "min_match": query_state["min_match"],
            "max_hits": max_hits,
            "bm25": {"k1": self.index.k1, "b": self.index.b},
            "corpus_fingerprint": self.index.corpus_fingerprint(),
            "symbol_weights_signature": self.symbol_weights.signature(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def _decode_cursor(self, cursor: str, query_signature: str) -> int:
        m = self._RE_CURSOR.match(cursor)
        if m is None:
            raise ValueError("Invalid cursor format")
        offset = int(m.group(1))
        sig = m.group(2)
        if sig != query_signature:
            raise ValueError("Cursor does not match query")
        if offset < 0:
            raise ValueError("Cursor offset must be >= 0")
        return offset
