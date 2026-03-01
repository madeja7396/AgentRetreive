#!/usr/bin/env python3
"""Backend factory and engine selection helpers."""

from __future__ import annotations

import os

from .protocol import RetrievalBackend
from .python_backend import PythonBackend
from .rust_backend import RustBackend

SUPPORTED_ENGINES = ("py", "rust")


def resolve_backend_name(explicit: str | None = None) -> str:
    """Resolve backend name from CLI arg/env with safe fallback."""
    raw = (explicit or os.environ.get("AR_ENGINE") or "py").strip().lower()
    if raw in SUPPORTED_ENGINES:
        return raw
    return "py"


def create_backend(name: str | None = None) -> RetrievalBackend:
    """Create backend instance by name."""
    resolved = resolve_backend_name(name)
    if resolved == "py":
        return PythonBackend()
    if resolved == "rust":
        return RustBackend()
    raise ValueError(f"Unsupported engine backend: {resolved}")
