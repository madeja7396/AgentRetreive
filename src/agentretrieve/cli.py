#!/usr/bin/env python3
"""AgentRetrieve CLI: ar command-line interface."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .index.inverted import InvertedIndex
from .query.engine import QueryEngine
from .models.output import format_results

_RE_DOC_ID = re.compile(r"^doc_([0-9a-f]+)$")
_RE_SPAN_ID = re.compile(r"^span_([0-9a-f]+)_([0-9]+)(?:_([a-f0-9]{6,40}))?$")

_DEFAULT_PATTERN = (
    "*.py,*.pyi,*.js,*.jsx,*.mjs,*.cjs,*.ts,*.tsx,*.mts,*.cts,*.rs,*.go,*.cs,*.php,"
    "*.rb,*.kt,*.kts,*.swift,*.dart,*.hs,*.lhs,*.ex,*.exs,*.c,*.h,*.cpp,*.cc,*.cxx,"
    "*.hpp,*.java,*.md"
)


def _collect_files(root: Path, pattern_csv: str) -> list[Path]:
    files: set[Path] = set()
    patterns = [part.strip() for part in pattern_csv.split(",") if part.strip()]
    for pattern in patterns:
        for path in root.rglob(pattern):
            if path.is_file():
                files.add(path)
    return sorted(files, key=lambda p: str(p.relative_to(root)))


def _build_index(root: Path, pattern_csv: str) -> InvertedIndex:
    idx = InvertedIndex()
    idx.source_root = str(root.resolve())
    files = _collect_files(root, pattern_csv)
    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(path.relative_to(root))
            lang = _detect_lang(path.suffix)
            idx.add_document(rel_path, content, lang)
        except Exception as exc:
            print(f"Warning: Failed to index {path}: {exc}", file=sys.stderr)
    return idx


def _summarize_update(old_idx: InvertedIndex, new_idx: InvertedIndex) -> dict[str, Any]:
    old_docs = {doc.path: doc.content_hash for doc in old_idx.documents.values()}
    new_docs = {doc.path: doc.content_hash for doc in new_idx.documents.values()}
    old_paths = set(old_docs.keys())
    new_paths = set(new_docs.keys())

    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    changed = sorted(p for p in (old_paths & new_paths) if old_docs[p] != new_docs[p])
    unchanged = len((old_paths & new_paths) - set(changed))
    return {
        "version": "index_update_report.v1",
        "old": {
            "documents": old_idx.total_docs,
            "terms": len(old_idx.index),
            "corpus_fingerprint": old_idx.corpus_fingerprint(),
        },
        "new": {
            "documents": new_idx.total_docs,
            "terms": len(new_idx.index),
            "corpus_fingerprint": new_idx.corpus_fingerprint(),
        },
        "delta": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "unchanged_count": unchanged,
            "added_paths": added,
            "removed_paths": removed,
            "changed_paths": changed,
        },
    }


def cmd_index_build(args: argparse.Namespace) -> int:
    """Build index from directory."""
    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
        return 1

    idx = _build_index(root, args.pattern)

    # Save index
    output_path = Path(args.output)
    idx.save(output_path)
    print(f"Index saved: {output_path}")
    print(f"Documents: {idx.total_docs}, Terms: {len(idx.index)}, Total tokens: {idx.total_terms}")
    
    return 0


def cmd_index_update(args: argparse.Namespace) -> int:
    """Update existing index safely via deterministic rebuild + atomic replace."""
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index not found: {args.index}", file=sys.stderr)
        return 1

    old_idx = InvertedIndex.load(index_path)
    source_root = args.dir or old_idx.source_root
    if not source_root:
        print(
            "Error: source root is unknown. Pass --dir explicitly for ix update.",
            file=sys.stderr,
        )
        return 2
    root = Path(source_root)
    if not root.exists() or not root.is_dir():
        print(f"Error: Directory not found: {root}", file=sys.stderr)
        return 2

    output_path = Path(args.output) if args.output else index_path
    rebuilt = _build_index(root, args.pattern)
    report = _summarize_update(old_idx, rebuilt)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    rebuilt.save(tmp_path)
    tmp_path.replace(output_path)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Update report saved: {report_path}")

    print(f"Index updated: {output_path}")
    print(
        "Delta: +{added} / -{removed} / ~{changed} / ={unchanged}".format(
            added=report["delta"]["added_count"],
            removed=report["delta"]["removed_count"],
            changed=report["delta"]["changed_count"],
            unchanged=report["delta"]["unchanged_count"],
        )
    )
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Execute query."""
    # Load index
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index not found: {args.index}", file=sys.stderr)
        return 1
    
    idx = InvertedIndex.load(index_path)
    engine = QueryEngine(idx)
    
    # Parse query
    if args.json:
        query = json.loads(Path(args.json).read_text(encoding='utf-8'))
        must = query.get('must', [])
        should = query.get('should', [])
        not_terms = query.get('not', [])
        near = query.get('near', [])
        lang = query.get('lang', [])
        ext = query.get('ext', [])
        path_prefix = query.get('path_prefix', [])
        symbol = query.get('symbol', [])
        options = query.get('options', {})
        if not isinstance(options, dict):
            print("Error: options must be an object", file=sys.stderr)
            return 2
        cursor = options.get('cursor')
        result_version = options.get("result_version", args.result_version)
        budget = query.get('budget', {})
        max_results = budget.get('max_results', 20)
        max_hits = budget.get('max_hits', 10)
        max_bytes = budget.get('max_bytes', 8192)
        max_excerpt = budget.get('max_excerpt', 256)
    else:
        must = args.must.split(',') if args.must else []
        should = args.should.split(',') if args.should else []
        not_terms = args.not_.split(',') if args.not_ else []
        near = []
        lang = args.lang.split(',') if args.lang else []
        ext = args.ext.split(',') if args.ext else []
        path_prefix = args.path_prefix.split(',') if args.path_prefix else []
        symbol = args.symbol.split(',') if args.symbol else []
        cursor = args.cursor
        result_version = args.result_version
        max_results = args.max_results
        max_hits = args.max_hits
        max_bytes = 8192
        max_excerpt = 256

    if result_version not in {"v1", "v2"}:
        print("Error: result_version must be v1 or v2", file=sys.stderr)
        return 2
    
    # Execute search
    try:
        page = engine.search_page(
            must=must,
            should=should,
            not_terms=not_terms,
            max_results=max_results,
            max_hits=max_hits,
            near=near,
            lang=lang,
            ext=ext,
            path_prefix=path_prefix,
            symbol=symbol,
            cursor=cursor,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    
    # Format once to determine how many results can actually be emitted
    # under byte/result/hit budgets.
    preliminary = format_results(
        results=page.results,
        budget_max_bytes=max_bytes,
        budget_max_results=max_results,
        budget_max_hits=max_hits,
        budget_max_excerpt=max_excerpt,
        cursor=None,
        pagination_truncated=False,
        result_version=result_version,
        capability_epoch=idx.corpus_fingerprint() if result_version == "v2" else None,
    )

    emitted_count = len(preliminary.r)
    if emitted_count == 0 and page.total_results > page.start_offset:
        print(
            "Error: response budget too small to emit any result; increase budget.max_bytes "
            "or lower max_hits/max_excerpt",
            file=sys.stderr,
        )
        return 2

    next_cursor = page.next_cursor_for_emitted(emitted_count)

    # Re-format with pagination metadata attached.
    output = format_results(
        results=page.results,
        budget_max_bytes=max_bytes,
        budget_max_results=max_results,
        budget_max_hits=max_hits,
        budget_max_excerpt=max_excerpt,
        cursor=next_cursor,
        pagination_truncated=next_cursor is not None,
        result_version=result_version,
        capability_epoch=idx.corpus_fingerprint() if result_version == "v2" else None,
    )
    
    print(output.to_json())
    
    return 0


def _parse_doc_id(handle: str) -> int | None:
    m = _RE_DOC_ID.match(handle)
    if m is None:
        return None
    return int(m.group(1), 16)


def _parse_span_id(handle: str) -> tuple[int, int, str | None] | None:
    m = _RE_SPAN_ID.match(handle)
    if m is None:
        return None
    return int(m.group(1), 16), int(m.group(2)), m.group(3)


def cmd_cap_verify(args: argparse.Namespace) -> int:
    """Verify capability handle validity against current index."""
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index not found: {args.index}", file=sys.stderr)
        return 1

    idx = InvertedIndex.load(index_path)
    doc_num = _parse_doc_id(args.doc_id)
    span = _parse_span_id(args.span_id)
    current_fingerprint = idx.corpus_fingerprint()

    out: dict[str, Any] = {
        "v": "cap.verify.v1",
        "ok": False,
        "state": "mismatch",
        "index_fingerprint": current_fingerprint,
        "doc_id": args.doc_id,
        "span_id": args.span_id,
    }

    if doc_num is None or span is None:
        out["reason"] = "invalid_handle_format"
        print(json.dumps(out, ensure_ascii=False))
        return 3

    span_doc, span_ord, span_epoch = span
    if span_doc != doc_num:
        out["reason"] = "doc_span_mismatch"
        print(json.dumps(out, ensure_ascii=False))
        return 3
    if span_ord < 1:
        out["reason"] = "invalid_span_ordinal"
        print(json.dumps(out, ensure_ascii=False))
        return 3

    doc = idx.get_document(doc_num)
    if doc is None:
        out["state"] = "not_found"
        out["reason"] = "document_not_found"
        print(json.dumps(out, ensure_ascii=False))
        return 3

    digest = args.digest.lower() if args.digest else None
    doc_digest = doc.content_hash.lower()

    if digest is not None and digest != doc_digest:
        out["state"] = "stale"
        out["reason"] = "digest_mismatch"
        out["current_digest"] = doc_digest
        out["path"] = doc.path
        print(json.dumps(out, ensure_ascii=False))
        return 3

    if span_epoch is not None and not current_fingerprint.startswith(span_epoch):
        out["state"] = "stale"
        out["reason"] = "epoch_mismatch"
        out["path"] = doc.path
        out["current_digest"] = doc_digest
        print(json.dumps(out, ensure_ascii=False))
        return 3

    out["ok"] = True
    out["state"] = "valid"
    out["path"] = doc.path
    out["current_digest"] = doc_digest
    print(json.dumps(out, ensure_ascii=False))
    return 0


def _detect_lang(ext: str) -> str | None:
    """Detect language from file extension."""
    lang_map = {
        '.py': 'python',
        '.pyi': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.mjs': 'javascript',
        '.cjs': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.mts': 'typescript',
        '.cts': 'typescript',
        '.rs': 'rust',
        '.go': 'go',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.kt': 'kotlin',
        '.kts': 'kotlin',
        '.swift': 'swift',
        '.dart': 'dart',
        '.hs': 'haskell',
        '.lhs': 'haskell',
        '.ex': 'elixir',
        '.exs': 'elixir',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.java': 'java',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
    }
    return lang_map.get(ext.lower())


def main() -> int:
    parser = argparse.ArgumentParser(
        prog='ar',
        description='AgentRetrieve - Agent-native code search',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # ar ix build
    ix_parser = subparsers.add_parser('ix', help='Index operations')
    ix_sub = ix_parser.add_subparsers(dest='ix_command', required=True)
    
    build_parser = ix_sub.add_parser('build', help='Build index')
    build_parser.add_argument('dir', help='Directory to index')
    build_parser.add_argument('-o', '--output', required=True, help='Output index file')
    build_parser.add_argument(
        '-p',
        '--pattern',
        default=_DEFAULT_PATTERN,
        help='File patterns to index (comma-separated)',
    )
    
    update_parser = ix_sub.add_parser('update', help='Update index')
    update_parser.add_argument('index', help='Index file to update')
    update_parser.add_argument('--dir', help='Source directory (defaults to index source_root)')
    update_parser.add_argument('-o', '--output', help='Output index file (defaults to in-place)')
    update_parser.add_argument('--report', help='Optional JSON report path')
    update_parser.add_argument(
        '-p',
        '--pattern',
        default=_DEFAULT_PATTERN,
        help='File patterns to index (comma-separated)',
    )
    
    # ar q
    q_parser = subparsers.add_parser('q', help='Query index')
    q_parser.add_argument('-i', '--index', required=True, help='Index file')
    q_parser.add_argument('--json', help='Query JSON file')
    q_parser.add_argument('--must', help='Required terms (comma-separated)')
    q_parser.add_argument('--should', help='Optional terms (comma-separated)')
    q_parser.add_argument('--not', dest='not_', help='Excluded terms (comma-separated)')
    q_parser.add_argument('--lang', help='Language filters (comma-separated, e.g. python,go)')
    q_parser.add_argument('--ext', help='Extension filters (comma-separated, e.g. .py,.rs)')
    q_parser.add_argument('--path-prefix', help='Path prefix filters (comma-separated)')
    q_parser.add_argument('--symbol', help='Symbol constraints (comma-separated)')
    q_parser.add_argument('--cursor', help='Cursor token for paginated continuation')
    q_parser.add_argument('--result-version', choices=['v1', 'v2'], default='v1')
    q_parser.add_argument('--max-results', type=int, default=20)
    q_parser.add_argument('--max-hits', type=int, default=10)

    # ar cap verify
    cap_parser = subparsers.add_parser('cap', help='Capability operations')
    cap_sub = cap_parser.add_subparsers(dest='cap_command', required=True)
    cap_verify = cap_sub.add_parser('verify', help='Verify capability handle')
    cap_verify.add_argument('-i', '--index', required=True, help='Index file')
    cap_verify.add_argument('--doc-id', required=True, help='Capability doc_id handle')
    cap_verify.add_argument('--span-id', required=True, help='Capability span_id handle')
    cap_verify.add_argument('--digest', help='Optional digest from retrieval output')
    
    args = parser.parse_args()
    
    if args.command == 'ix':
        if args.ix_command == 'build':
            return cmd_index_build(args)
        elif args.ix_command == 'update':
            return cmd_index_update(args)
    elif args.command == 'q':
        return cmd_query(args)
    elif args.command == 'cap':
        if args.cap_command == 'verify':
            return cmd_cap_verify(args)
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
