# Scripts Catalog

更新日: 2026-03-01

## 目的

- `scripts/` 配下を運用状態で分類し、どれを使うべきかを明確化する
- 標準導線（Make / route / runbook）と補助導線（調査・比較）を分離する

## 分類

### Active（標準導線）

- `scripts/pipeline/run_experiment_route.py`
- `scripts/pipeline/run_corpus_auto_adapt.py`
- `scripts/pipeline/run_full_pipeline.py`
- `scripts/pipeline/run_final_evaluation.py`
- `scripts/pipeline/check_gold_coverage.py`
- `scripts/ci/run_contract_harness.sh`
- `scripts/ci/validate_contracts.py`
- `scripts/daemon/agentd.py`
- `scripts/daemon/enqueue_task.py`
- `scripts/daemon/run_agentd.sh`
- `scripts/dev/prepare_worktree.sh`
- `scripts/benchmark/fit_symbol_language_weights.py`
- `scripts/benchmark/generate_report.py`
- `scripts/benchmark/complete_phase3.py`
- `scripts/benchmark/analyze_toolcall_reduction.py`
- `scripts/pipeline/run_cross_env_repro.py`
- `scripts/dev/run_cross_env_repro.sh`

### Incubation（補助・分析）

- `scripts/benchmark/compare_all_tools.py`
- `scripts/benchmark/compare_baselines.py`
- `scripts/benchmark/compare_with_optimal.py`
- `scripts/benchmark/evaluate_taskset.py`
- `scripts/benchmark/investigate_ripgrep.py`
- `scripts/benchmark/parameter_search.py`
- `scripts/benchmark/run_all_experiments.py`
- `scripts/benchmark/run_comparison.py`
- `scripts/benchmark/verify_dataset.py`

## 標準実行入口

```bash
make validate
make experiment-ready
make experiment
make phase3-complete RUN_ID=<run_id>
make report
```

## 接続先

- 運用標準: `docs/operations/RUNBOOK.md`
- パイプライン詳細: `docs/PIPELINE_GUIDE.md`
- 資産分類台帳: `docs/operations/ASSET_CLASSIFICATION.md`
