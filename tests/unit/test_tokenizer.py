#!/usr/bin/env python3
"""Unit tests for tokenizer."""

import unittest
from agentretrieve.index.tokenizer import (
    split_camel,
    split_snake,
    tokenize_identifier,
    tokenize_document,
    normalize_term,
)


class TestTokenizer(unittest.TestCase):
    
    def test_split_camel(self):
        self.assertEqual(split_camel("CamelCase"), ["camel", "case"])
        self.assertEqual(split_camel("HTTPRequest"), ["http", "request"])
        self.assertEqual(split_camel("parseJSON"), ["parse", "json"])
        self.assertEqual(split_camel("URL"), ["url"])
    
    def test_split_snake(self):
        self.assertEqual(split_snake("snake_case"), ["snake", "case"])
        self.assertEqual(split_snake("foo__bar"), ["foo", "bar"])
    
    def test_tokenize_identifier(self):
        self.assertEqual(tokenize_identifier("snake_case"), ["snake", "case"])
        self.assertEqual(tokenize_identifier("camelCase"), ["camel", "case"])
        self.assertEqual(tokenize_identifier("CamelCase"), ["camel", "case"])
        self.assertEqual(tokenize_identifier("snake_case_mixed"), ["snake", "case", "mixed"])
        self.assertEqual(tokenize_identifier("HTTPResponseWriter"), ["http", "response", "writer"])
    
    def test_tokenize_document(self):
        text = "def hello_world():\n    return 42"
        tokens = tokenize_document(text)
        texts = [t.text for t in tokens]
        self.assertIn("def", texts)
        self.assertIn("hello", texts)
        self.assertIn("world", texts)
        self.assertIn("return", texts)
    
    def test_normalize_term(self):
        self.assertEqual(normalize_term("Hello"), "hello")
        self.assertEqual(normalize_term("WORLD"), "world")


if __name__ == '__main__':
    unittest.main()
