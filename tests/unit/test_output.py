#!/usr/bin/env python3
"""Unit tests for mini-JSON formatter budget handling."""

from __future__ import annotations

import unittest

from agentretrieve.models.output import format_results
from agentretrieve.query.engine import Bounds, Hit, Range, SearchResult


class TestOutputFormatter(unittest.TestCase):
    def _mk_result(self, doc_id: int, path: str, text: str) -> SearchResult:
        return SearchResult(
            doc_id=doc_id,
            path=path,
            score=500,
            hits=[Hit(line=1, text=text, score=500)],
            rng=Range(from_line=1, to_line=5),
            doc_id_str=f"doc_{doc_id:08x}",
            span_id=f"span_{doc_id:08x}_001",
            digest="a1b2c3d4",
            bounds=Bounds(start=1, end=20),
            next_spans=[],
        )

    def test_max_bytes_is_enforced(self):
        results = [
            self._mk_result(0, "src/a.py", "x" * 120),
            self._mk_result(1, "src/b.py", "y" * 120),
        ]
        out = format_results(
            results=results,
            budget_max_bytes=360,
            budget_max_results=20,
            budget_max_hits=10,
            budget_max_excerpt=200,
        )
        payload = out.to_dict()

        self.assertTrue(payload["t"])
        self.assertLessEqual(payload["lim"]["emitted_bytes"], 360)
        self.assertLessEqual(len(payload["r"]), 2)

    def test_path_index_is_compact(self):
        results = [
            self._mk_result(0, "src/a.py", "line1"),
            self._mk_result(1, "src/a.py", "line2"),
            self._mk_result(2, "src/b.py", "line3"),
        ]
        payload = format_results(results=results).to_dict()

        self.assertEqual(payload["p"], ["src/a.py", "src/b.py"])
        self.assertEqual([r["pi"] for r in payload["r"]], [0, 0, 1])

    def test_cursor_and_pagination_truncation_flag(self):
        results = [self._mk_result(0, "src/a.py", "line1")]
        payload = format_results(
            results=results,
            cursor="cur_2_deadbeef",
            pagination_truncated=True,
        ).to_dict()

        self.assertEqual(payload["cur"], "cur_2_deadbeef")
        self.assertTrue(payload["t"])

    def test_v2_includes_capability_metadata(self):
        results = [self._mk_result(0, "src/a.py", "line1")]
        payload = format_results(
            results=results,
            result_version="v2",
            capability_epoch="a" * 20,
        ).to_dict()

        self.assertEqual(payload["v"], "result.v2")
        self.assertIn("cap", payload)
        self.assertEqual(payload["cap"]["index_fingerprint"], "a" * 20)
        self.assertEqual(payload["r"][0]["cap_epoch"], "a" * 20)
        self.assertTrue(payload["r"][0]["span_id"].endswith("_aaaaaaaa"))


if __name__ == "__main__":
    unittest.main()
