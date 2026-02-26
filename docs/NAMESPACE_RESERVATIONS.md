# Namespace Reservations

更新日: 2026-02-25

## 目的

- キー衝突、命名揺れ、将来拡張時の互換破壊を防ぐ

## 1. ID Prefix 予約

| Prefix | Meaning | Example |
|---|---|---|
| `doc_` | 文書 ID | `doc_a12f9` |
| `span_` | 断片 ID | `span_00k2m` |
| `cur_` | cursor | `cur_1qaz` |
| `ds_` | dataset ID | `ds_20260225_core_v1` |
| `run_` | 実験 run ID | `run_20260225_101500_mvp` |
| `sch_` | schema ID（将来拡張） | `sch_result_v2` |

## 2. Query DSL Key 予約

以下は v1 の固定予約キー。意味の変更は禁止。

- `version`
- `must`
- `should`
- `not`
- `near`
- `lang`
- `ext`
- `path_prefix`
- `symbol`
- `budget`
- `options`

拡張キーは `x_` で始めること。例: `x_domain_boost`

## 3. Result Key 予約

以下は出力 v1 の固定予約キー。短キーの意味の変更は禁止。

- top-level: `v`, `ok`, `p`, `r`, `t`, `cur`, `lim`
- result item: `pi`, `s`, `h`, `rng`, `next`, `doc_id`, `span_id`, `digest`, `bounds`

## 4. Metric Name 予約

評価で利用する正規名称:

- `mrr_at_10`
- `ndcg_at_10`
- `recall_at_10`
- `tool_calls_per_task`
- `stdout_bytes_per_task`
- `ttfc_ms_p50`
- `ttfc_ms_p95`

新規追加時は snake_case で統一し、既存名の意味変更は禁止。

## 5. Path Namespace 予約

`artifacts/` 以下の予約:

- `artifacts/datasets/manifests/`
- `artifacts/datasets/raw/`
- `artifacts/datasets/processed/`
- `artifacts/experiments/runs/`
- `artifacts/experiments/summaries/`
- `artifacts/papers/figures/`
- `artifacts/papers/tables/`
- `artifacts/agentd/spool/pending/`
- `artifacts/agentd/spool/in_progress/`
- `artifacts/agentd/spool/done/`
- `artifacts/agentd/spool/dead/`
- `artifacts/agentd/logs/`

`docs/benchmarks/` 以下の予約:

- `docs/benchmarks/corpus.v1.json`
- `docs/benchmarks/taskset.v1.jsonl`
- `docs/benchmarks/baselines.v1.json`
- `docs/benchmarks/run_constraints.v1.json`

`docs/contracts/` 以下の予約:

- `docs/contracts/contract_policy.v1.json`

## 6. 禁止事項

- 予約済み prefix/key の再定義
- 同一 ID の再利用
- `x_` なしの未定義キー追加
