#!/usr/bin/env python3
"""Unit tests for backend factory helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from unittest import TestCase
from unittest.mock import patch

from agentretrieve.backends import create_backend, resolve_backend_name
from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.backends.python_backend import PythonBackend
from agentretrieve.backends.rust_backend import RustBackend


class TestBackendFactory(TestCase):
    def test_resolve_backend_name_defaults_to_py(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_backend_name(None), "py")

    def test_resolve_backend_name_accepts_supported_engine(self) -> None:
        self.assertEqual(resolve_backend_name("rust"), "rust")

    def test_resolve_backend_name_falls_back_on_unknown(self) -> None:
        self.assertEqual(resolve_backend_name("unknown"), "py")

    def test_resolve_backend_name_reads_env(self) -> None:
        with patch.dict(os.environ, {"AR_ENGINE": "rust"}, clear=True):
            self.assertEqual(resolve_backend_name(None), "rust")

    def test_create_backend_python(self) -> None:
        backend = create_backend("py")
        self.assertIsInstance(backend, PythonBackend)

    def test_create_backend_rust(self) -> None:
        backend = create_backend("rust")
        self.assertIsInstance(backend, RustBackend)

    def test_rust_backend_cli_available(self) -> None:
        """Verify Rust CLI binary is detected."""
        backend = create_backend("rust")
        self.assertTrue(hasattr(backend, '_cli'))
        self.assertIsInstance(backend._cli, str)
        self.assertIn(Path(backend._cli).name, {"ar", "ar-cli"})

    def test_rust_backend_ar_bin_path_takes_precedence(self) -> None:
        with patch.dict(
            os.environ,
            {"AR_BIN_PATH": "/tmp/custom-ar", "AR_CLI_PATH": "/tmp/legacy-ar-cli"},
            clear=True,
        ):
            backend = create_backend("rust")
            self.assertEqual(backend._cli, "/tmp/custom-ar")

    def test_rust_backend_search_page_parses_result_v3(self) -> None:
        backend = RustBackend.__new__(RustBackend)
        backend._cli = "/tmp/ar-cli"

        idx = InvertedIndex(documents={}, index={})
        idx._rust_index_path = Path("/tmp/sample.index.bin")  # type: ignore[attr-defined]
        idx.k1 = 1.7
        idx.b = 0.55

        payload = {
            "v": "result.v3",
            "ok": True,
            "r": [
                {
                    "id": "d5_s1",
                    "s": 777,
                    "h": [{"ln": 10, "txt": "fn main()", "sc": 777}],
                    "rng": [9, 20],
                    "proof": {"digest": "abc123", "bounds": [1, 42]},
                    "next": ["d5_s2"],
                    "path": "src/main.rs",
                }
            ],
        }

        with patch.object(
            backend,
            "_run_checked",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr=""),
        ) as mocked:
            page = backend.search_page(
                idx,
                must=["main"],
                should=[],
                not_terms=[],
                max_results=5,
                max_hits=3,
                min_match=0,
                near=None,
                lang=None,
                ext=None,
                path_prefix=None,
                symbol=None,
                cursor=None,
            )

        self.assertEqual(len(page.results), 1)
        result = page.results[0]
        self.assertEqual(result.doc_id, 5)
        self.assertEqual(result.path, "src/main.rs")
        self.assertEqual(result.score, 777)
        self.assertEqual(result.rng.from_line, 9)
        self.assertEqual(result.rng.to_line, 20)
        self.assertEqual(result.bounds.start, 1)
        self.assertEqual(result.bounds.end, 42)
        self.assertEqual(result.doc_id_str, "doc_5")
        self.assertEqual(result.span_id, "span_5_1")
        mocked.assert_called_once()
        called_args = mocked.call_args.args[0]
        self.assertIn("--k1", called_args)
        self.assertIn("--b", called_args)
        self.assertIn("1.7", called_args)
        self.assertIn("0.55", called_args)

    def test_rust_backend_search_page_cursor_not_supported(self) -> None:
        backend = RustBackend.__new__(RustBackend)
        backend._cli = "/tmp/ar-cli"
        idx = InvertedIndex(documents={}, index={})
        idx._rust_index_path = Path("/tmp/sample.index.bin")  # type: ignore[attr-defined]

        with self.assertRaises(ValueError):
            backend.search_page(
                idx,
                must=[],
                should=[],
                not_terms=[],
                max_results=5,
                max_hits=3,
                min_match=0,
                near=None,
                lang=None,
                ext=None,
                path_prefix=None,
                symbol=None,
                cursor="cur_1_deadbeef",
            )
