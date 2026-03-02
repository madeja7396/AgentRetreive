#!/usr/bin/env python3
"""Rust backend CLI bridge.

This adapter invokes the Rust `ar` CLI binary (with `ar-cli` compatibility)
for index operations and search.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..index.inverted import InvertedIndex
from ..query.engine import Bounds, Hit, Range, SearchPage, SearchResult

_DEFAULT_PATTERN = (
    "*.py,*.pyi,*.js,*.jsx,*.mjs,*.cjs,*.ts,*.tsx,*.mts,*.cts,*.rs,*.go,*.cs,*.php,"
    "*.rb,*.kt,*.kts,*.swift,*.dart,*.hs,*.lhs,*.ex,*.exs,*.c,*.h,*.cpp,*.cc,*.cxx,"
    "*.hpp,*.java,*.md"
)


def _ar_cli_path() -> str:
    """Locate Rust CLI binary with backward-compatible fallbacks."""
    if path := os.environ.get("AR_BIN_PATH"):
        return path
    if path := os.environ.get("AR_CLI_PATH"):
        return path

    project_root = Path(__file__).resolve().parents[3]
    local_candidates = [
        project_root / "target" / "release" / "ar",
        project_root / "target" / "release" / "ar-cli",
        project_root / "target" / "debug" / "ar",
        project_root / "target" / "debug" / "ar-cli",
    ]
    for candidate in local_candidates:
        if candidate.exists():
            return str(candidate)

    for name in ("ar", "ar-cli"):
        resolved = shutil.which(name)
        if resolved:
            return resolved

    raise RuntimeError(
        "Rust CLI binary not found. Set AR_BIN_PATH (or legacy AR_CLI_PATH), or build with: "
        "cargo build --release -p ar-cli"
    )


def _sha1_short(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()[:20]


def _parse_doc_id(raw_id: str) -> int:
    # Rust result.v3 id format: d{doc_id}_s{span}
    if raw_id.startswith("d") and "_s" in raw_id:
        head = raw_id[1:].split("_s", 1)[0]
        if head.isdigit():
            return int(head)
    return 0


def _parse_stats_line(stdout: str) -> dict[str, int]:
    stats: dict[str, int] = {}
    for part in stdout.strip().split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key in {"docs", "terms", "total_tokens"} and value.isdigit():
            stats[key] = int(value)
    return stats


class RustBackend:
    """Rust engine backend via CLI bridge."""

    name = "rust"

    def __init__(self) -> None:
        self._cli = _ar_cli_path()
        self._supports_bm25_flags: bool | None = None

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [self._cli] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def _run_checked(self, args: list[str], *, op: str) -> subprocess.CompletedProcess[str]:
        result = self._run(args)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            detail = stderr or stdout or f"exit={result.returncode}"
            raise RuntimeError(f"{op} failed: {detail}")
        return result

    def _new_holder(self, index_path: Path) -> InvertedIndex:
        idx = InvertedIndex(documents={}, index={})
        idx._rust_index_path = index_path  # type: ignore[attr-defined]
        idx._corpus_fingerprint_cache = _sha1_short(index_path)  # type: ignore[attr-defined]
        return idx

    def _resolve_reference_json(self, index_path: Path, data: dict[str, Any]) -> Path | None:
        rust_ref = data.get("rust_index")
        if isinstance(rust_ref, str) and rust_ref.strip():
            ref_path = Path(rust_ref)
            if not ref_path.is_absolute():
                ref_path = (index_path.parent / ref_path).resolve()
            if ref_path.exists():
                return ref_path
        return None

    def _build_binary_from_source(self, source_root: Path, output_bin: Path) -> None:
        output_bin.parent.mkdir(parents=True, exist_ok=True)
        self._run_checked(
            [
                "ix",
                "build",
                "--dir",
                str(source_root),
                "--output",
                str(output_bin),
                "--pattern",
                _DEFAULT_PATTERN,
            ],
            op="rust index build",
        )

    def _ensure_binary_index(self, index_path: Path) -> Path:
        if not index_path.exists():
            raise RuntimeError(f"Index not found: {index_path}")

        if index_path.suffix == ".bin":
            return index_path

        if index_path.suffix != ".json":
            return index_path

        sibling_bin = index_path.with_suffix(".bin")
        if sibling_bin.exists():
            return sibling_bin

        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            # Backward compatibility: some runs saved binary payload with .json suffix.
            return index_path

        if isinstance(payload, dict):
            ref_bin = self._resolve_reference_json(index_path, payload)
            if ref_bin is not None:
                return ref_bin

            source_root = payload.get("source_root")
            if isinstance(source_root, str) and source_root.strip():
                root = Path(source_root)
                if root.exists() and root.is_dir():
                    self._build_binary_from_source(root, sibling_bin)
                    return sibling_bin

        raise RuntimeError(
            f"Rust backend requires binary index (.bin). Could not resolve from: {index_path}"
        )

    def build_index(self, root: Path, pattern_csv: str) -> InvertedIndex:
        fd, tmp_name = tempfile.mkstemp(prefix="ar_rust_", suffix=".bin")
        os.close(fd)
        tmp_output = Path(tmp_name)
        try:
            result = self._run_checked(
                [
                    "ix",
                    "build",
                    "--dir",
                    str(root),
                    "--output",
                    str(tmp_output),
                    "--pattern",
                    pattern_csv or _DEFAULT_PATTERN,
                ],
                op="rust build_index",
            )
            holder = self._new_holder(tmp_output)
            holder.source_root = str(root.resolve())
            holder._rust_stats = _parse_stats_line(result.stdout)  # type: ignore[attr-defined]
            return holder
        except Exception:
            if tmp_output.exists():
                tmp_output.unlink(missing_ok=True)
            raise

    def load_index(self, index_path: Path) -> InvertedIndex:
        resolved = self._ensure_binary_index(index_path)
        holder = self._new_holder(resolved)
        if index_path.suffix == ".json":
            try:
                payload = json.loads(index_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    source_root = payload.get("source_root")
                    if isinstance(source_root, str):
                        holder.source_root = source_root
            except Exception:
                pass
        return holder

    def save_index(self, index: InvertedIndex, output_path: Path) -> None:
        src = getattr(index, "_rust_index_path", None)
        if src is None:
            raise RuntimeError("Rust index holder is missing internal index path.")
        src = Path(src)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == ".json":
            bin_path = output_path.with_suffix(".bin")
            shutil.copy(src, bin_path)
            manifest = {
                "version": "rust_index_ref.v1",
                "source_root": index.source_root,
                "rust_index": bin_path.name,
            }
            output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            return

        shutil.copy(src, output_path)

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
        if cursor:
            raise ValueError("Rust backend cursor continuation is not supported yet.")

        index_path = getattr(index, "_rust_index_path", None)
        if not index_path:
            raise RuntimeError("No index loaded. Call build_index or load_index first.")

        args = [
            "q",
            "--index",
            str(index_path),
            "--max-results",
            str(max_results),
            "--min-match",
            str(min_match),
            "--max-hits",
            str(max_hits),
        ]

        bm25_args = [
            "--k1",
            str(float(getattr(index, "k1", 0.8))),
            "--b",
            str(float(getattr(index, "b", 0.3))),
        ]

        if must:
            args.extend(["--must", ",".join(must)])
        if should:
            args.extend(["--should", ",".join(should)])
        if not_terms:
            args.extend(["--not", ",".join(not_terms)])
        if symbol:
            args.extend(["--symbol", ",".join(symbol)])

        supports_bm25_flags = getattr(self, "_supports_bm25_flags", None)
        cmd_args = list(args)
        if supports_bm25_flags is not False:
            cmd_args.extend(bm25_args)

        try:
            result = self._run_checked(cmd_args, op="rust search")
            if supports_bm25_flags is None and cmd_args != args:
                self._supports_bm25_flags = True
        except RuntimeError as exc:
            msg = str(exc)
            if (
                supports_bm25_flags is not False
                and "--k1" in msg
                and "unexpected argument" in msg
            ):
                self._supports_bm25_flags = False
                result = self._run_checked(args, op="rust search")
            else:
                raise

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON output from ar-cli: {exc}") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Invalid rust search output payload")

        entries = data.get("r")
        if not isinstance(entries, list):
            entries = data.get("results", [])
        if not isinstance(entries, list):
            entries = []

        path_dict = data.get("p", [])
        results: list[SearchResult] = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            raw_id = str(entry.get("id", "d0_s1"))
            doc_id = _parse_doc_id(raw_id)
            path = entry.get("path")
            if not isinstance(path, str):
                pi = entry.get("pi")
                if isinstance(pi, int) and 0 <= pi < len(path_dict):
                    p = path_dict[pi]
                    if isinstance(p, str):
                        path = p
            if not isinstance(path, str):
                path = f"doc_{doc_id}"

            raw_hits = entry.get("h", [])
            hits: list[Hit] = []
            if isinstance(raw_hits, list):
                for h in raw_hits:
                    if not isinstance(h, dict):
                        continue
                    hits.append(
                        Hit(
                            line=int(h.get("ln", 1)),
                            text=str(h.get("txt", "")),
                            score=int(h.get("sc", entry.get("s", 0))),
                        )
                    )

            raw_rng = entry.get("rng", [1, 1])
            if isinstance(raw_rng, dict):
                from_line = int(raw_rng.get("from", 1))
                to_line = int(raw_rng.get("to", from_line))
            elif isinstance(raw_rng, list) and len(raw_rng) >= 2:
                from_line = int(raw_rng[0])
                to_line = int(raw_rng[1])
            else:
                from_line = 1
                to_line = 1

            proof = entry.get("proof", {})
            digest = ""
            b_start = from_line
            b_end = to_line
            if isinstance(proof, dict):
                if isinstance(proof.get("digest"), str):
                    digest = str(proof["digest"])
                raw_bounds = proof.get("bounds")
                if isinstance(raw_bounds, list) and len(raw_bounds) >= 2:
                    b_start = int(raw_bounds[0])
                    b_end = int(raw_bounds[1])
            if not digest and isinstance(entry.get("digest"), str):
                digest = str(entry["digest"])

            if isinstance(entry.get("bounds"), dict):
                b_start = int(entry["bounds"].get("start", b_start))
                b_end = int(entry["bounds"].get("end", b_end))

            next_spans = entry.get("next", [])
            if not isinstance(next_spans, list):
                next_spans = []

            results.append(
                SearchResult(
                    doc_id=doc_id,
                    path=path,
                    score=int(entry.get("s", entry.get("score", 0))),
                    hits=hits,
                    rng=Range(from_line=max(1, from_line), to_line=max(from_line, to_line)),
                    doc_id_str=f"doc_{doc_id:x}",
                    span_id=f"span_{doc_id:x}_1",
                    digest=digest,
                    bounds=Bounds(start=max(1, b_start), end=max(b_start, b_end)),
                    next_spans=[str(v) for v in next_spans],
                )
            )

        return SearchPage(
            results=results,
            start_offset=0,
            total_results=len(results),
            cursor_signature="rust_cli_v3",
        )
