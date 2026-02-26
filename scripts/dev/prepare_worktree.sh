#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p artifacts/datasets/manifests
mkdir -p artifacts/datasets/raw
mkdir -p artifacts/datasets/processed
mkdir -p artifacts/experiments/runs
mkdir -p artifacts/experiments/summaries
mkdir -p artifacts/papers/figures
mkdir -p artifacts/papers/tables
mkdir -p artifacts/agentd/spool/pending
mkdir -p artifacts/agentd/spool/in_progress
mkdir -p artifacts/agentd/spool/done
mkdir -p artifacts/agentd/spool/dead
mkdir -p artifacts/agentd/logs
mkdir -p dist

echo "[OK] worktree local directories prepared under:"
echo "  - artifacts/"
echo "  - dist/"
