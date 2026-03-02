#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install AgentRetrieve "ar" launcher into PATH without losing GNU ar compatibility.

Usage:
  bash scripts/dev/install_ar_launcher.sh [options]

Options:
  --binary <path>       Use this AgentRetrieve binary explicitly.
  --install-dir <path>  Install destination directory (default: $HOME/.local/bin).
  --no-build            Do not build when binary is missing.
  --force               Overwrite non-AgentRetrieve launcher.
  -h, --help            Show this help.
EOF
}

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
BIN_PATH=""
AUTO_BUILD=1
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary)
      BIN_PATH="${2:-}"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --no-build)
      AUTO_BUILD=0
      shift 1
      ;;
    --force)
      FORCE=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BIN_PATH" ]]; then
  if [[ -x "${ROOT_DIR}/target/release-dist/ar" ]]; then
    BIN_PATH="${ROOT_DIR}/target/release-dist/ar"
  elif [[ -x "${ROOT_DIR}/target/release/ar" ]]; then
    BIN_PATH="${ROOT_DIR}/target/release/ar"
  fi
fi

if [[ -z "$BIN_PATH" || ! -x "$BIN_PATH" ]]; then
  if [[ "$AUTO_BUILD" -eq 1 ]]; then
    echo "[INFO] AgentRetrieve binary not found. Building release-dist profile..."
    (cd "$ROOT_DIR" && cargo build --profile release-dist -p ar-cli)
    BIN_PATH="${ROOT_DIR}/target/release-dist/ar"
  fi
fi

if [[ -z "$BIN_PATH" || ! -x "$BIN_PATH" ]]; then
  echo "[ERROR] AgentRetrieve binary not found/executable: ${BIN_PATH:-<empty>}" >&2
  echo "        Provide --binary <path> or build with: cargo build --profile release-dist -p ar-cli" >&2
  exit 2
fi

BIN_PATH_ABS="$(realpath "$BIN_PATH")"
LAUNCHER_PATH="${INSTALL_DIR}/ar"

mkdir -p "$INSTALL_DIR"

if [[ -f "$LAUNCHER_PATH" ]] && [[ "$FORCE" -ne 1 ]]; then
  if ! grep -q "AgentRetrieve ar launcher" "$LAUNCHER_PATH"; then
    echo "[ERROR] ${LAUNCHER_PATH} already exists and is not an AgentRetrieve launcher." >&2
    echo "        Re-run with --force if you want to replace it." >&2
    exit 2
  fi
fi

if [[ -f "$LAUNCHER_PATH" ]] && [[ "$FORCE" -eq 1 ]]; then
  BACKUP_PATH="${LAUNCHER_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  cp "$LAUNCHER_PATH" "$BACKUP_PATH"
  echo "[INFO] existing launcher backed up: ${BACKUP_PATH}"
fi

cat >"$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
# AgentRetrieve ar launcher
# - AgentRetrieve command path can be overridden with AR_AGENTRETRIEVE_BIN
# - Set AR_LAUNCHER_FORCE_GNU=1 to force GNU ar passthrough
AGENT_AR="\${AR_AGENTRETRIEVE_BIN:-$BIN_PATH_ABS}"
SYSTEM_AR="\${AR_SYSTEM_AR_PATH:-/usr/bin/ar}"

if [[ "\${AR_LAUNCHER_FORCE_GNU:-0}" == "1" ]]; then
  if [[ -x "\$SYSTEM_AR" ]]; then
    exec "\$SYSTEM_AR" "\$@"
  fi
  echo "[ar-launcher] GNU ar not found at: \$SYSTEM_AR" >&2
  exit 127
fi

cmd="\${1:-}"
case "\$cmd" in
  ""|ix|q|help|--help|-h)
    if [[ ! -x "\$AGENT_AR" ]]; then
      echo "[ar-launcher] AgentRetrieve binary not found/executable: \$AGENT_AR" >&2
      echo "[ar-launcher] Reinstall launcher or set AR_AGENTRETRIEVE_BIN." >&2
      exit 127
    fi
    exec "\$AGENT_AR" "\$@"
    ;;
  *)
    if [[ -x "\$SYSTEM_AR" ]]; then
      exec "\$SYSTEM_AR" "\$@"
    fi
    echo "[ar-launcher] GNU ar not found at: \$SYSTEM_AR" >&2
    exit 127
    ;;
esac
EOF

chmod 0755 "$LAUNCHER_PATH"

echo "[OK] installed launcher: ${LAUNCHER_PATH}"
echo "[OK] agentretrieve binary: ${BIN_PATH_ABS}"
echo "[INFO] verify with:"
echo "  ar ix --help"
echo "  ar q --help"
echo "  AR_LAUNCHER_FORCE_GNU=1 ar --version"
