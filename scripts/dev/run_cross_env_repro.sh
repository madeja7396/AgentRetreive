#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:-run_20260228_154238_exp001_raw}"
python3.11 scripts/pipeline/run_cross_env_repro.py \
  --run-id "${RUN_ID}" \
  --python-exec python3.11 \
  --rel-latency-tol 0.30
