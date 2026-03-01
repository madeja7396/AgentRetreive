#!/usr/bin/env python3
"""Backend abstractions for retrieval engine selection."""

from .factory import SUPPORTED_ENGINES, create_backend, resolve_backend_name

__all__ = ["SUPPORTED_ENGINES", "create_backend", "resolve_backend_name"]
