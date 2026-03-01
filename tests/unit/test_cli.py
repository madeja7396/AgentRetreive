#!/usr/bin/env python3
"""Unit tests for CLI operational commands."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from agentretrieve.cli import cmd_cap_verify, cmd_index_build, cmd_index_update
from agentretrieve.index.inverted import InvertedIndex


class TestCliOperations(unittest.TestCase):
    def test_ix_update_rebuilds_and_reports_delta(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            repo = temp_root / "repo"
            repo.mkdir()
            (repo / "a.py").write_text("alpha\n", encoding="utf-8")

            index_path = temp_root / "repo.index.json"
            build_args = argparse.Namespace(
                dir=str(repo),
                output=str(index_path),
                pattern="*.py",
            )
            rc = cmd_index_build(build_args)
            self.assertEqual(rc, 0)

            (repo / "a.py").write_text("alpha\nbeta\n", encoding="utf-8")
            (repo / "b.py").write_text("gamma\n", encoding="utf-8")

            report_path = temp_root / "update_report.json"
            update_args = argparse.Namespace(
                index=str(index_path),
                dir=str(repo),
                output=None,
                report=str(report_path),
                pattern="*.py",
            )
            rc = cmd_index_update(update_args)
            self.assertEqual(rc, 0)

            idx = InvertedIndex.load(index_path)
            self.assertEqual(idx.total_docs, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["delta"]["added_count"], 1)
            self.assertEqual(report["delta"]["changed_count"], 1)

    def test_cap_verify_detects_valid_and_stale_handles(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            repo = temp_root / "repo"
            repo.mkdir()
            (repo / "a.py").write_text("alpha\n", encoding="utf-8")

            index_path = temp_root / "repo.index.json"
            build_args = argparse.Namespace(
                dir=str(repo),
                output=str(index_path),
                pattern="*.py",
            )
            self.assertEqual(cmd_index_build(build_args), 0)

            idx = InvertedIndex.load(index_path)
            doc = idx.get_document(0)
            self.assertIsNotNone(doc)
            assert doc is not None
            epoch_short = idx.corpus_fingerprint()[:8]

            valid_args = argparse.Namespace(
                index=str(index_path),
                doc_id="doc_00000000",
                span_id=f"span_00000000_001_{epoch_short}",
                digest=doc.content_hash,
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cmd_cap_verify(valid_args), 0)

            stale_args = argparse.Namespace(
                index=str(index_path),
                doc_id="doc_00000000",
                span_id=f"span_00000000_001_{epoch_short}",
                digest="deadbeefdeadbeef",
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cmd_cap_verify(stale_args), 3)


if __name__ == "__main__":
    unittest.main()
