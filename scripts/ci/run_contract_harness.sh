#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

REFRESH=0
if [[ "${1:-}" == "--refresh" ]]; then
  REFRESH=1
fi

if [[ ! -x ".venv-ci/bin/python" ]]; then
  python3 -m venv .venv-ci
  REFRESH=1
fi

if [[ "$REFRESH" -eq 1 ]]; then
  .venv-ci/bin/python -m pip install --upgrade pip
  .venv-ci/bin/python -m pip install -r requirements-ci.txt
fi

.venv-ci/bin/python scripts/ci/validate_contracts.py
