#!/usr/bin/env python3
"""AgentRetrieve CLI: ar command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .index.inverted import InvertedIndex
from .query.engine import QueryEngine
from .models.output import format_results


def cmd_index_build(args: argparse.Namespace) -> int:
    """Build index from directory."""
    idx = InvertedIndex()
    
    root = Path(args.dir)
    if not root.exists():
        print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
        return 1
    
    # Collect files
    files: list[Path] = []
    for pattern in args.pattern.split(','):
        files.extend(root.rglob(pattern))
    
    # Index files
    for path in files:
        if path.is_file():
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(path.relative_to(root))
                lang = _detect_lang(path.suffix)
                idx.add_document(rel_path, content, lang)
            except Exception as e:
                print(f"Warning: Failed to index {path}: {e}", file=sys.stderr)
    
    # Save index
    output_path = Path(args.output)
    idx.save(output_path)
    print(f"Index saved: {output_path}")
    print(f"Documents: {idx.total_docs}, Terms: {len(idx.index)}, Total tokens: {idx.total_terms}")
    
    return 0


def cmd_index_update(args: argparse.Namespace) -> int:
    """Update existing index (incremental)."""
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index not found: {args.index}", file=sys.stderr)
        return 1
    
    idx = InvertedIndex.load(index_path)
    print(f"Loaded index: {idx.total_docs} documents")
    
    # TODO: Implement incremental update
    print("Incremental update not yet implemented, use build for full reindex")
    
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
        max_results = args.max_results
        max_hits = args.max_hits
        max_bytes = 8192
        max_excerpt = 256
    
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
    )
    
    print(output.to_json())
    
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
        default='*.py,*.pyi,*.js,*.jsx,*.mjs,*.cjs,*.ts,*.tsx,*.mts,*.cts,*.rs,*.go,*.cs,*.php,*.rb,*.kt,*.kts,*.swift,*.dart,*.hs,*.lhs,*.ex,*.exs,*.c,*.h,*.cpp,*.cc,*.cxx,*.hpp,*.java,*.md',
                             help='File patterns to index (comma-separated)')
    
    update_parser = ix_sub.add_parser('update', help='Update index')
    update_parser.add_argument('index', help='Index file to update')
    
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
    q_parser.add_argument('--max-results', type=int, default=20)
    q_parser.add_argument('--max-hits', type=int, default=10)
    
    args = parser.parse_args()
    
    if args.command == 'ix':
        if args.ix_command == 'build':
            return cmd_index_build(args)
        elif args.ix_command == 'update':
            return cmd_index_update(args)
    elif args.command == 'q':
        return cmd_query(args)
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
