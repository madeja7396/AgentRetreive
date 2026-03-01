# Claim to Evidence Map

更新日: 2026-03-01
対象 run_id: `run_20260228_154238_exp001_raw`

## 対応表

| Claim ID | Claim | Evidence Artifact | Notes |
|---|---|---|---|
| C-001 | raw固定の公式評価で全体 Recall 74.3%、Average MRR 0.381 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/final_summary.json` | `overall.recall`, `overall.avg_mrr` |
| C-002 | gold coverage は taskset対象7repoで欠落なし | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/gold_coverage_summary.json` | 各repo `present=5/5` |
| C-003 | retrieval benchmark を repo別に再現可能 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/retrieval_*.json` | 7repo分を保存 |
| C-004 | baseline 比較（AgentRetrieve/ripgrep/git grep）を repo別に再現可能 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/comparison_*.json` | 7repo分を保存 |
| C-005 | micro benchmark の p50/p95/p99 を計測済み | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/micro_benchmark.json` | build/update/query/RSS/index size |
| C-006 | e2e 指標（tool calls/stdout bytes/TTFC）を計測済み | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/e2e_metrics.json` | TTFC は p50/p95/p99 を保存 |
| C-007 | ablation（BM25 only / +symbol / +near / +prior）の差分を計測済み | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/ablation.json` | `delta_vs_bm25_only` |
| C-008 | 反復実験 n=5 の mean/std/CI を算出済み | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/stability.json` | EXP-001/003/004 指標 |
| C-009 | 実験 provenance（環境/commit/config/hash）を追跡可能 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/run_record.json` | schema: `run_record.v1` |
| C-010 | run registry で実験履歴を時系列保存 | `artifacts/experiments/run_registry.v1.jsonl` | run_id 単位で追記 |
| C-011 | AgentRetrieve は現行grep系ワークフロー想定より tool-call を約83%削減 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/tool_call_reduction.json` | inspect_limit=5 の仮定で算出 |
| C-012 | 主要実験は cross-env（Python 3.11）でも許容誤差内で再現 | `artifacts/experiments/runs/run_20260228_154238_exp001_raw/cross_env_py311/cross_env_repro_report.tol30.json` | quality ±0.01, latency ±30% |
