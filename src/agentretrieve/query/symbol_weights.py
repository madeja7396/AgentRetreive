#!/usr/bin/env python3
"""Statistical symbol weighting model (global + language-specific)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SymbolLanguageWeights:
    """Language-aware symbol bonus weights learned from corpus experiments."""

    version: str = "symbol_language_weights.v1"
    global_weight: float = 0.0
    by_lang: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def disabled(cls) -> "SymbolLanguageWeights":
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SymbolLanguageWeights":
        raw_map = data.get("by_lang", {})
        by_lang: dict[str, float] = {}
        if isinstance(raw_map, dict):
            for key, value in raw_map.items():
                if not isinstance(key, str):
                    continue
                try:
                    by_lang[key.lower()] = float(value)
                except (TypeError, ValueError):
                    continue
        metadata = data.get("metadata")
        return cls(
            version=str(data.get("version", "symbol_language_weights.v1")),
            global_weight=float(data.get("global_weight", 0.0)),
            by_lang=by_lang,
            metadata=metadata if isinstance(metadata, dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "global_weight": self.global_weight,
            "by_lang": dict(sorted(self.by_lang.items())),
            "metadata": self.metadata,
        }

    @classmethod
    def load(cls, path: Path) -> "SymbolLanguageWeights":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid symbol weight file: root must be object")
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def weight_for(self, lang: str | None) -> float:
        lang_key = (lang or "").strip().lower()
        if lang_key and lang_key in self.by_lang:
            return self.by_lang[lang_key]
        return self.global_weight

    def signature(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
