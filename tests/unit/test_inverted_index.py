#!/usr/bin/env python3
"""Unit tests for inverted index."""

import unittest
import tempfile
from pathlib import Path
from agentretrieve.index.inverted import InvertedIndex


class TestInvertedIndex(unittest.TestCase):
    
    def test_add_document(self):
        idx = InvertedIndex()
        doc_id = idx.add_document("test.py", "def hello_world():\n    pass")
        
        self.assertEqual(doc_id, 0)
        self.assertEqual(idx.total_docs, 1)
        self.assertIn("hello", idx.index)
        self.assertIn("world", idx.index)
    
    def test_query_term(self):
        idx = InvertedIndex()
        idx.add_document("test.py", "def hello_world():\n    return hello")
        idx.add_document("other.py", "def goodbye():\n    pass")
        
        results = list(idx.query_term("hello"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 0)  # doc_id
    
    def test_save_load(self):
        idx = InvertedIndex()
        idx.add_document("test.py", "def hello_world():\n    pass", lang="python")
        
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            idx.save(path)
            
            loaded = InvertedIndex.load(path)
            self.assertEqual(loaded.total_docs, 1)
            self.assertEqual(len(loaded.index), len(idx.index))
            
            doc = loaded.get_document(0)
            self.assertEqual(doc.path, "test.py")
            self.assertEqual(doc.lang, "python")
            self.assertGreater(doc.doc_length, 0)

    def test_doc_length_cached(self):
        idx = InvertedIndex()
        idx.add_document("a.py", "def hello_world():\n    return hello_world")
        doc = idx.get_document(0)
        self.assertIsNotNone(doc)
        self.assertGreater(doc.doc_length, 0)

    def test_posting_lines_persist(self):
        idx = InvertedIndex()
        idx.add_document("a.py", "alpha\nbeta alpha\nbeta")

        posting = idx.get_posting("alpha", 0)
        self.assertIsNotNone(posting)
        self.assertEqual(posting.lines, [1, 2])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            idx.save(path)
            loaded = InvertedIndex.load(path)
            loaded_posting = loaded.get_posting("alpha", 0)
            self.assertIsNotNone(loaded_posting)
            self.assertEqual(loaded_posting.lines, [1, 2])

    def test_scope_regions_extracted(self):
        idx = InvertedIndex()
        idx.add_document(
            "a.py",
            "def first():\n    alpha\n\n\ndef second():\n    beta\n",
            lang="python",
        )

        block_regions = idx.get_scope_regions(0, "block")
        symbol_regions = idx.get_scope_regions(0, "symbol")

        self.assertTrue(any(start <= 2 <= end for start, end in block_regions))
        self.assertTrue(any(start <= 6 <= end for start, end in block_regions))
        self.assertTrue(any(start <= 2 <= end for start, end in symbol_regions))
        self.assertTrue(any(start <= 6 <= end for start, end in symbol_regions))

    def test_scope_regions_persist(self):
        idx = InvertedIndex()
        idx.add_document(
            "a.py",
            "def first():\n    alpha\n\ndef second():\n    beta\n",
            lang="python",
        )
        original_block = idx.get_scope_regions(0, "block")
        original_symbol = idx.get_scope_regions(0, "symbol")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            idx.save(path)
            loaded = InvertedIndex.load(path)
            self.assertEqual(loaded.get_scope_regions(0, "block"), original_block)
            self.assertEqual(loaded.get_scope_regions(0, "symbol"), original_symbol)


if __name__ == '__main__':
    unittest.main()
