# Benchmark Inputs

更新日: 2026-02-25

`give.md` で提示された評価設計を、実行可能な入力資産へ固定した。

## Files

- `docs/benchmarks/corpus.v1.json`
- `docs/benchmarks/taskset.v1.jsonl`
- `docs/benchmarks/baselines.v1.json`
- `docs/benchmarks/run_constraints.v1.json`

## Validation

- schema: `docs/schemas/*.schema.json`
- CI validator: `scripts/ci/validate_contracts.py`

## Notes

- `taskset.v1.jsonl` は 1 行 1 タスク
- `gold` は壊れにくさ優先で `file + anchor` を採用
