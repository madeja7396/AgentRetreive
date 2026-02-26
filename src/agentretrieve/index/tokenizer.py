#!/usr/bin/env python3
"""AgentRetrieve tokenizer: identifier-aware tokenization for code search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Token:
    """A normalized token with position info."""
    text: str
    pos: int  # byte position in original text


# Pattern definitions
# Match: lowercase words, TitleCase words, UPPERCASE abbreviations followed by TitleCase
_RE_CAMEL = re.compile(r'[a-z]+|[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)')
_RE_SNAKE = re.compile(r'[a-zA-Z0-9]+')
_RE_ALNUM = re.compile(r'[a-zA-Z0-9]+')


def split_camel(ident: str) -> list[str]:
    """Split CamelCase identifier into parts.
    
    Examples:
        "CamelCase" -> ["camel", "case"]
        "HTTPRequest" -> ["http", "request"]
        "parseJSON" -> ["parse", "json"]
    """
    parts = _RE_CAMEL.findall(ident)
    return [p.lower() for p in parts if p]


def split_snake(ident: str) -> list[str]:
    """Split snake_case identifier into parts.
    
    Examples:
        "snake_case" -> ["snake", "case"]
        "foo__bar" -> ["foo", "bar"]
    """
    parts = _RE_SNAKE.findall(ident)
    return [p.lower() for p in parts if p]


def tokenize_identifier(ident: str) -> list[str]:
    """Tokenize an identifier into normalized terms.
    
    Handles both camelCase and snake_case, including mixed cases.
    """
    if not ident:
        return []
    
    # First split by underscore (snake_case)
    snake_parts = ident.split('_')
    
    result: list[str] = []
    for part in snake_parts:
        if not part:
            continue
        # Then split each part by camel case
        camel_parts = split_camel(part)
        if camel_parts:
            result.extend(camel_parts)
        else:
            # Fallback: just lowercase
            result.append(part.lower())
    
    return result


def tokenize_line(line: str, base_pos: int = 0) -> Iterator[Token]:
    """Tokenize a line of text into normalized tokens.
    
    Strategy:
    1. Extract alphanumeric sequences
    2. For sequences with uppercase or digits, try identifier tokenization
    3. Otherwise emit as-is (lowercased)
    
    Args:
        line: The text line to tokenize
        base_pos: Starting byte position in original document
    
    Yields:
        Token objects with normalized text and position
    """
    for match in _RE_ALNUM.finditer(line):
        text = match.group(0)
        pos = base_pos + match.start()
        
        # Check if it looks like an identifier (has uppercase or is all lowercase)
        if text[0].isalpha():
            # Looks like an identifier - tokenize it
            terms = tokenize_identifier(text)
            for term in terms:
                yield Token(text=term, pos=pos)
        else:
            # Probably just a number or starts with digit - emit as-is
            yield Token(text=text.lower(), pos=pos)


def tokenize_document(text: str) -> list[Token]:
    """Tokenize a full document into normalized tokens.
    
    Args:
        text: Full document text
    
    Returns:
        List of tokens with positions
    """
    tokens: list[Token] = []
    pos = 0
    for line in text.split('\n'):
        for token in tokenize_line(line, pos):
            tokens.append(token)
        pos += len(line) + 1  # +1 for newline
    return tokens


def normalize_term(term: str) -> str:
    """Normalize a search term for matching.
    
    Applies the same normalization as tokenization.
    """
    return term.lower()
