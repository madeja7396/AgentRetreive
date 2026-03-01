#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export AR_CLONE_TIMEOUT_SEC="${AR_CLONE_TIMEOUT_SEC:-2400}"

python3 scripts/pipeline/run_experiment_route.py \
  --profile full \
  --index-all \
  --force-clone \
  --force-index \
  --force-symbol-fit \
  "$@"
