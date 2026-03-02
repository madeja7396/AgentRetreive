# Program R1 Migration Guide (Python -> Rust)

## Scope
This guide defines the controlled migration from Python retrieval runtime to Rust core runtime.

## Runtime Modes
- `AR_ENGINE=py`: legacy Python execution path.
- `AR_ENGINE=rust`: Rust execution path (currently via Rust CLI/MCP surface).
- `AR_BIN_PATH=/path/to/ar`: preferred Rust CLI override.
- `AR_CLI_PATH=/path/to/ar-cli`: legacy override (backward-compatible).

## Rollout Steps
1. Keep contracts green (`validate_contracts`, `pytest`, `template-sync`).
2. Build Rust index with `ar ix build` (or `ar-cli ix build`) and validate `ar q` output (`result.v3`).
3. Validate MCP tool path (`ar.search` JSON-RPC roundtrip).
4. Compare KPI/latency against Python baseline for target corpora.
5. Promote Rust as default only after KPI non-regression gate passes.

## Rollback
- Set `AR_ENGINE=py`.
- Re-run route pipeline and generate run_record.
- Record rollback reason in run notes and risk register.

## Required Artifacts
- `docs/schemas/query.dsl.v2.schema.json`
- `docs/schemas/result.minijson.v3.schema.json`
- `docs/contracts/RESULT_COMPATIBILITY_POLICY.v1.md`
- `artifacts/experiments/benchmark_tiers.v2.json`

## Known Gaps (to close before default flip)
- PyO3 native bindings for direct Python runtime integration.
- WAL/compaction for high-frequency index updates.
- Large-repo p95 latency validation versus Python baseline.
