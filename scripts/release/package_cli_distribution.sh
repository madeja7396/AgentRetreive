#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  package_cli_distribution.sh \
    --binary <path-to-ar-binary> \
    --label <release-label> \
    --target <platform-target> \
    [--output-dir dist]
EOF
}

binary_path=""
label=""
target=""
output_dir="dist"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary)
      binary_path="${2:-}"
      shift 2
      ;;
    --label)
      label="${2:-}"
      shift 2
      ;;
    --target)
      target="${2:-}"
      shift 2
      ;;
    --output-dir)
      output_dir="${2:-}"
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

if [[ -z "$binary_path" || -z "$label" || -z "$target" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "$binary_path" ]]; then
  echo "Binary not found: $binary_path" >&2
  exit 2
fi
if [[ ! -f "README.md" ]]; then
  echo "README.md not found in project root." >&2
  exit 2
fi
if [[ ! -f "LICENSE" ]]; then
  echo "LICENSE not found in project root." >&2
  exit 2
fi

mkdir -p "$output_dir"
stage="$(mktemp -d /tmp/ar_pkg.XXXXXX)"
pkg_name="agentretrieve-cli-${label}-${target}"
pkg_root="${stage}/${pkg_name}"
mkdir -p "${pkg_root}/bin"

install -m 0755 "$binary_path" "${pkg_root}/bin/ar"
ln -sf ar "${pkg_root}/bin/ar-cli"
cp README.md "${pkg_root}/README.md"
cp LICENSE "${pkg_root}/LICENSE"

archive="${output_dir}/${pkg_name}.tar.gz"
tar -C "$stage" -czf "$archive" "$pkg_name"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$archive" > "${archive}.sha256"
else
  shasum -a 256 "$archive" > "${archive}.sha256"
fi

echo "archive=${archive}"
echo "checksum=${archive}.sha256"

rm -rf "$stage"
