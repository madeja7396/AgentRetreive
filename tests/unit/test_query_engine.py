#!/usr/bin/env python3
"""Unit tests for query engine DSL constraints."""

from __future__ import annotations

import unittest

from agentretrieve.index.inverted import InvertedIndex
from agentretrieve.query.engine import QueryEngine
from agentretrieve.query.symbol_weights import SymbolLanguageWeights


class TestQueryEngine(unittest.TestCase):
    def test_metadata_and_symbol_filters(self):
        idx = InvertedIndex()
        idx.add_document("src/main.py", "def parse_args():\n    pass", lang="python")
        idx.add_document("docs/readme.md", "parse args reference", lang="markdown")
        engine = QueryEngine(idx)

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            symbol=["parse_args"],
            lang=["python"],
            ext=[".py"],
            path_prefix=["src/"],
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, "src/main.py")

    def test_near_line_window_filter(self):
        idx = InvertedIndex()
        idx.add_document("a.py", "alpha\nx\nbeta", lang="python")  # distance=2
        idx.add_document("b.py", "alpha\nx\nx\nx\nbeta", lang="python")  # distance=4
        engine = QueryEngine(idx)

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            near=[{"terms": ["alpha", "beta"], "scope": "line_window", "window": 2}],
        )
        paths = [r.path for r in results]

        self.assertIn("a.py", paths)
        self.assertNotIn("b.py", paths)

    def test_near_block_scope_strict(self):
        idx = InvertedIndex()
        idx.add_document("same_block.py", "alpha\nbeta\n", lang="python")
        idx.add_document("split_block.py", "alpha\n\nbeta\n", lang="python")
        engine = QueryEngine(idx)

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            near=[{"terms": ["alpha", "beta"], "scope": "block", "window": 10}],
        )
        paths = [r.path for r in results]

        self.assertIn("same_block.py", paths)
        self.assertNotIn("split_block.py", paths)

    def test_near_symbol_scope_strict(self):
        idx = InvertedIndex()
        idx.add_document(
            "same_symbol.py",
            "def first():\n    alpha\n    beta\n",
            lang="python",
        )
        idx.add_document(
            "split_symbol.py",
            "def first():\n    alpha\n\n\ndef second():\n    beta\n",
            lang="python",
        )
        engine = QueryEngine(idx)

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            near=[{"terms": ["alpha", "beta"], "scope": "symbol", "window": 10}],
        )
        paths = [r.path for r in results]

        self.assertIn("same_symbol.py", paths)
        self.assertNotIn("split_symbol.py", paths)

    def test_cursor_pagination(self):
        idx = InvertedIndex()
        for i in range(5):
            idx.add_document(f"doc{i}.py", "alpha\n", lang="python")
        engine = QueryEngine(idx)

        page1 = engine.search_page(
            must=["alpha"],
            should=[],
            not_terms=[],
            max_results=2,
            max_hits=2,
        )
        self.assertEqual(len(page1.results), 2)
        cursor1 = page1.next_cursor_for_emitted(len(page1.results))
        self.assertIsNotNone(cursor1)

        page2 = engine.search_page(
            must=["alpha"],
            should=[],
            not_terms=[],
            max_results=2,
            max_hits=2,
            cursor=cursor1,
        )
        self.assertEqual(len(page2.results), 2)
        cursor2 = page2.next_cursor_for_emitted(len(page2.results))
        self.assertIsNotNone(cursor2)

        page3 = engine.search_page(
            must=["alpha"],
            should=[],
            not_terms=[],
            max_results=2,
            max_hits=2,
            cursor=cursor2,
        )
        self.assertEqual(len(page3.results), 1)
        cursor3 = page3.next_cursor_for_emitted(len(page3.results))
        self.assertIsNone(cursor3)

    def test_cursor_validation(self):
        idx = InvertedIndex()
        idx.add_document("doc.py", "alpha\n", lang="python")
        engine = QueryEngine(idx)

        with self.assertRaises(ValueError):
            engine.search_page(
                must=["alpha"],
                should=[],
                not_terms=[],
                max_results=2,
                max_hits=2,
                cursor="cur_invalid",
            )

    def test_symbol_language_weights_affect_order(self):
        idx = InvertedIndex()
        idx.add_document("src/main.py", "def parse_args():\n    return 1\n", lang="python")
        idx.add_document("docs/readme.md", "parse_args\n", lang="markdown")
        engine = QueryEngine(
            idx,
            symbol_weights=SymbolLanguageWeights(
                global_weight=0.0,
                by_lang={"python": 100.0, "markdown": 1.0},
            ),
        )

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            symbol=["parse_args"],
            max_results=10,
            max_hits=2,
        )
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0].path, "src/main.py")

    def test_cursor_rejects_symbol_weight_model_mismatch(self):
        idx = InvertedIndex()
        for i in range(3):
            idx.add_document(f"doc{i}.py", "alpha\n", lang="python")

        engine_a = QueryEngine(
            idx,
            symbol_weights=SymbolLanguageWeights(global_weight=10.0, by_lang={"python": 10.0}),
        )
        engine_b = QueryEngine(
            idx,
            symbol_weights=SymbolLanguageWeights(global_weight=1.0, by_lang={"python": 1.0}),
        )

        page = engine_a.search_page(
            must=["alpha"],
            should=[],
            not_terms=[],
            max_results=1,
            max_hits=2,
        )
        cursor = page.next_cursor_for_emitted(len(page.results))
        self.assertIsNotNone(cursor)

        with self.assertRaises(ValueError):
            engine_b.search_page(
                must=["alpha"],
                should=[],
                not_terms=[],
                max_results=1,
                max_hits=2,
                cursor=cursor,
            )

    def test_symbol_scores_are_clamped_to_zero(self):
        idx = InvertedIndex()
        idx.add_document("a.py", "def parse_args():\n    return 1\n", lang="python")
        idx.add_document("b.py", "def parse_args():\n    return 2\n", lang="python")
        engine = QueryEngine(
            idx,
            symbol_weights=SymbolLanguageWeights(global_weight=-10.0, by_lang={"python": -10.0}),
        )

        results = engine.search(
            must=[],
            should=[],
            not_terms=[],
            symbol=["parse_args"],
            max_results=10,
            max_hits=2,
        )
        self.assertTrue(results)
        self.assertTrue(all(r.score >= 0 for r in results))


if __name__ == "__main__":
    unittest.main()
