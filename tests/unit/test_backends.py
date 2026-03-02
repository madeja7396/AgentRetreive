#!/usr/bin/env python3
"""Unit tests for backend factory helpers."""

from __future__ import annotations

import os
from unittest import TestCase
from unittest.mock import patch

from agentretrieve.backends import create_backend, resolve_backend_name
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
        """Verify ar-cli binary is detected."""
        backend = create_backend("rust")
        self.assertTrue(hasattr(backend, '_cli'))
        self.assertIsInstance(backend._cli, str)
        # Verify the path looks like ar-cli
        self.assertIn("ar-cli", backend._cli)
