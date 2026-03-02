# Scripts Catalog

更新日: 2026-03-03

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
- `scripts/dev/install_ar_launcher.sh`
- `scripts/benchmark/fit_symbol_language_weights.py`
- `scripts/benchmark/generate_report.py`
- `scripts/benchmark/complete_phase3.py`
- `scripts/benchmark/analyze_toolcall_reduction.py`
- `scripts/pipeline/run_cross_env_repro.py`
- `scripts/pipeline/generate_run_record.py`
- `scripts/dev/run_cross_env_repro.sh`
- `scripts/dev/sync_template_bundle.py`
- `scripts/release/check_binary_size.sh`
- `scripts/release/bench_cli_regression.py`
- `scripts/release/package_cli_distribution.sh`

### Active（Pipeline サブコンポーネント）

これらは `make` / pipeline から間接的に呼び出される：

- `scripts/benchmark/evaluate_taskset.py` - taskset 評価（EXP-003）
- `scripts/benchmark/run_comparison.py` - baseline 比較（EXP-004）
- `scripts/benchmark/verify_dataset.py` - dataset 検証
- `scripts/pipeline/run_full_pipeline.py` - 従来パイプライン（段階的に route へ移行中）

### Incubation（実験・分析・補助）

利用実績あり、標準導線への統合検討中：

- `scripts/benchmark/compare_all_tools.py` - 多ツール比較（段階的に run_comparison へ統合）
- `scripts/benchmark/compare_baselines.py` - ベースライン比較分析
- `scripts/benchmark/compare_with_optimal.py` - 最適値との差分分析
- `scripts/benchmark/parameter_search.py` - パラメータグリッドサーチ
- `scripts/benchmark/run_all_experiments.py` - 全実験一括実行

利用実績なし／重複／代替あり：

- `scripts/benchmark/investigate_ripgrep.py` - RIPGREP_INVESTIGATION_REPORT.md 作成時の調査スクリプト

### Archive（非推奨・履歴保存）

なし（現時点では incubation から直接削除せず、利用実績を見守る）

## 昇格/廃止判断基準

| 判断 | 基準 | 最終判断時期 |
|------|------|-------------|
| Active 昇格 | 標準導線（Makefile/pipeline）から呼び出しが定常化 | 2026-03-15 |
| Archive 移行 | 2週間以上利用実績なし、かつ代替導線でカバー | 2026-03-15 |
| 残留 Incubation | 実験・分析時に都度利用継続 | 継続 |

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
