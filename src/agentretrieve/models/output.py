#!/usr/bin/env python3
"""AgentRetrieve output formatter: mini-JSON result contract."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..query.engine import SearchResult


@dataclass
class MiniJsonResult:
    """Mini-JSON result conforming to result.minijson.v1.schema.json."""
    
    v: str = "result.v1"
    ok: bool = True
    p: list[str] = field(default_factory=list)  # path dictionary
    r: list[ResultEntry] = field(default_factory=list)  # results
    t: bool = False  # truncated
    cur: str | None = None  # cursor
    lim: Limits = field(default_factory=lambda: Limits(
        max_bytes=8192, max_results=20, max_hits=10, max_excerpt=256, emitted_bytes=0
    ))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Build path dictionary and rewrite pi to keep compact contiguous indices.
        path_index: dict[str, int] = {}
        results: list[dict[str, Any]] = []
        for entry in self.r:
            if entry.p not in path_index:
                path_index[entry.p] = len(path_index)

            hit_dicts = [
                {
                    "ln": h.ln,
                    "txt": h.txt[:self.lim.max_excerpt],  # truncate text
                    "sc": h.sc,
                }
                for h in entry.h
            ]
            
            results.append({
                "pi": path_index[entry.p],
                "s": entry.s,
                "h": hit_dicts,
                "rng": {
                    "from": entry.rng.from_line,
                    "to": entry.rng.to_line,
                },
                "next": entry.next,
                "doc_id": entry.doc_id,
                "span_id": entry.span_id,
                "digest": entry.digest,
                "bounds": {
                    "start": entry.bounds.start,
                    "end": entry.bounds.end,
                },
            })

        paths = [p for p, _ in sorted(path_index.items(), key=lambda x: x[1])]
        payload = {
            "v": self.v,
            "ok": self.ok,
            "p": paths,
            "r": results,
            "t": self.t,
            "cur": self.cur,
            "lim": {
                "max_bytes": self.lim.max_bytes,
                "max_results": self.lim.max_results,
                "max_hits": self.lim.max_hits,
                "max_excerpt": self.lim.max_excerpt,
                "emitted_bytes": 0,
            },
        }
        emitted_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        payload["lim"]["emitted_bytes"] = emitted_bytes
        return payload
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ResultEntry:
    """Single result entry."""
    pi: int  # path index
    p: str  # path (temporary, for building index)
    s: int  # score 0-1000
    h: list[HitEntry]  # hits
    rng: RangeEntry  # range
    next: list[str]  # next span suggestions
    doc_id: str  # capability handle
    span_id: str  # capability handle
    digest: str  # content hash
    bounds: BoundsEntry  # line bounds


@dataclass
class HitEntry:
    """Hit entry."""
    ln: int  # line number
    txt: str  # text excerpt
    sc: int  # hit score 0-1000


@dataclass
class RangeEntry:
    """Range entry."""
    from_line: int
    to_line: int


@dataclass  
class BoundsEntry:
    """Bounds entry."""
    start: int
    end: int


@dataclass
class Limits:
    """Limits entry."""
    max_bytes: int
    max_results: int
    max_hits: int
    max_excerpt: int
    emitted_bytes: int


def format_results(
    results: list[SearchResult],
    budget_max_bytes: int = 8192,
    budget_max_results: int = 20,
    budget_max_hits: int = 10,
    budget_max_excerpt: int = 256,
    cursor: str | None = None,
    pagination_truncated: bool = False,
) -> MiniJsonResult:
    """Format search results to mini-JSON contract.
    
    Args:
        results: Search results from query engine
        budget_max_bytes: Maximum output bytes
        budget_max_results: Maximum results
        budget_max_hits: Maximum hits per result
        budget_max_excerpt: Maximum excerpt length
    
    Returns:
        MiniJsonResult conforming to schema
    """
    truncated = pagination_truncated or len(results) > budget_max_results

    # Build candidate entries up to max_results/max_hits.
    path_to_idx: dict[str, int] = {}
    entries: list[ResultEntry] = []
    
    for sr in results[:budget_max_results]:
        # Get or assign path index
        if sr.path not in path_to_idx:
            path_to_idx[sr.path] = len(path_to_idx)
        
        pi = path_to_idx[sr.path]
        
        # Build hits
        if len(sr.hits) > budget_max_hits:
            truncated = True
        hits = [
            HitEntry(ln=h.line, txt=h.text, sc=h.score)
            for h in sr.hits[:budget_max_hits]
        ]
        
        entry = ResultEntry(
            pi=pi,
            p=sr.path,  # temporary for building
            s=sr.score,
            h=hits,
            rng=RangeEntry(from_line=sr.rng.from_line, to_line=sr.rng.to_line),
            next=sr.next_spans,
            doc_id=sr.doc_id_str,
            span_id=sr.span_id,
            digest=sr.digest,
            bounds=BoundsEntry(start=sr.bounds.start, end=sr.bounds.end),
        )
        entries.append(entry)

    limits = Limits(
        max_bytes=budget_max_bytes,
        max_results=budget_max_results,
        max_hits=budget_max_hits,
        max_excerpt=budget_max_excerpt,
        emitted_bytes=0,
    )

    # Enforce max_bytes strictly by admitting entries while output stays in budget.
    accepted: list[ResultEntry] = []
    for entry in entries:
        probe = MiniJsonResult(ok=True, r=accepted + [entry], t=False, lim=limits).to_dict()
        if probe["lim"]["emitted_bytes"] <= budget_max_bytes:
            accepted.append(entry)
            continue
        truncated = True
        break

    if len(accepted) < len(entries):
        truncated = True

    return MiniJsonResult(
        ok=True,
        r=accepted,
        t=truncated,
        cur=cursor,
        lim=limits,
    )
