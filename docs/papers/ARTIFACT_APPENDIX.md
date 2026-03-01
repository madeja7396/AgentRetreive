# Artifact Appendix

更新日: 2026-03-01
対象 run_id: `run_20260228_154238_exp001_raw`

## 1. 再現手順（1コマンド）

```bash
make phase3-complete RUN_ID=run_20260228_154238_exp001_raw
```

前提として、公式評価と比較結果を再生成する場合は以下を先に実行する。

```bash
python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4
```

cross-env 再現（Python 3.11）は以下:

```bash
scripts/dev/run_cross_env_repro.sh run_20260228_154238_exp001_raw
```

## 2. 入力データ

- `docs/benchmarks/corpus.v1.1.json`
- `docs/benchmarks/taskset.v2.full.jsonl`
- `configs/experiment_pipeline.yaml`
- dataset manifest:
  - `artifacts/datasets/manifests/ds_20260301_taskset_v2_full_raw.manifest.json`

## 3. 成果物配置

- run root:
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/`
- 主要成果物:
  - `final_summary.json`
  - `gold_coverage_summary.json`
  - `retrieval_*.json`
  - `comparison_*.json`
  - `micro_benchmark.json`
  - `e2e_metrics.json`
  - `ablation.json`
  - `stability.json`
  - `run_record.json`

## 4. 実行環境（記録値）

- OS: `Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 GNU/Linux`
- CPU: `AMD Ryzen 7 8845HS w/ Radeon 780M Graphics`
- RAM: `30.66 GB`
- Python: `3.12.3`
- Pytest: `7.4.4`

## 5. 許容誤差

- Recall/MRR: ±0.01（absolute）
- Latency 系指標: ±30%（relative, cross-runtime差を許容）

## 6. 既知の制約

- `tool_calls_per_task` は現行比較導線では 1 呼び出しモデル（定数）で評価している
- cross-environment 再現は Python 3.11 で実施済み（`cross_env_repro_report.tol30.json`）
- embedding 系ベースライン比較はスコープ外（本実験は non-embedding 系）
