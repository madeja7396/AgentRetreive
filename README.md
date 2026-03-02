# AgentRetrieve

Deterministic code retrieval for agent workflows.

## Primary Distribution Surface

`ar` (Rust CLI) is the canonical command.

- Preferred command: `ar`
- Backward-compatible alias: `ar-cli`

## Quick Start (Local Build)

```bash
cargo build --release -p ar-cli
./target/release/ar --help
```

Build a compact distribution binary:

```bash
cargo build --profile release-dist -p ar-cli
./target/release-dist/ar --help
```

## Basic Usage

Build index:

```bash
ar ix build --dir /path/to/repo --output /tmp/repo.index.bin
```

Query index:

```bash
ar q --index /tmp/repo.index.bin --must parser,config --max-results 10
```

## Python Bridge Mode

Python tooling can call Rust CLI through the backend bridge:

- `AR_ENGINE=rust` enables Rust path
- `AR_BIN_PATH=/path/to/ar` (preferred)
- `AR_CLI_PATH=/path/to/ar-cli` (legacy)

## Release Artifacts

GitHub Releases publish CLI archives for:

- `linux-x86_64`
- `macos-arm64`

Each release includes checksums (`SHA256SUMS.txt`).

## Validation

```bash
PYTHONPATH=src pytest -q
python3 scripts/ci/validate_contracts.py
```
