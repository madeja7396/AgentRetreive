#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  check_binary_size.sh --binary <path> --max-mb <float>

Options:
  --binary   Target binary path
  --max-mb   Maximum allowed binary size in MB
EOF
}

binary_path=""
max_mb=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary)
      binary_path="${2:-}"
      shift 2
      ;;
    --max-mb)
      max_mb="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$binary_path" || -z "$max_mb" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "$binary_path" ]]; then
  echo "[size-gate] binary not found: $binary_path" >&2
  exit 2
fi

size_bytes="$(wc -c < "$binary_path")"
size_mb="$(python3 - <<'PY' "$size_bytes"
import sys
size_bytes = int(sys.argv[1])
print(size_bytes / (1024 * 1024))
PY
)"

echo "[size-gate] binary=$binary_path size_bytes=$size_bytes size_mb=${size_mb} limit_mb=${max_mb}"

python3 - <<'PY' "$size_mb" "$max_mb"
import sys
size_mb = float(sys.argv[1])
max_mb = float(sys.argv[2])
if size_mb <= max_mb + 1e-12:
    sys.exit(0)
sys.exit(1)
PY

echo "[size-gate] PASS"
