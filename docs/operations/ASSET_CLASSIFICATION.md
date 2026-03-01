# Asset Classification and Connectivity

更新日: 2026-03-01

## 目的

- 未統合ナレッジと未整理スクリプトを `active / incubation / archive` で分類する
- 参照導線（どこから辿るか）を固定し、探索コストを下げる
- 運用自動化が参照すべき資産と、保留/履歴資産を分離する

## ステータス定義

- `active`: 現行運用・検証・実験導線で利用する公式資産
- `incubation`: 有用だが標準導線には未組み込みの検討資産
- `archive`: 履歴保全目的。標準導線からは参照しない

## Knowledge Assets

| Asset | Status | 理由 | 接続先 |
|---|---|---|---|
| `docs/contracts/IMPLEMENTATION_CONTRACT.md` | active | 契約境界の運用規則 | `docs/README.md` |
| `docs/schemas/README.md` | active | schema 群の索引 | `docs/README.md` |
| `docs/benchmarks/CORPUS_EXTENSION_PLAN.md` | incubation | 拡張設計メモ（実運用前） | `docs/benchmarks/README.md` |
| `docs/benchmarks/DATASET_BIAS_ANALYSIS.md` | incubation | データ偏り分析 | `docs/benchmarks/README.md` |
| `docs/benchmarks/OPTIMAL_PARAMETER_RATIONALE.md` | incubation | パラメータ根拠整理 | `docs/benchmarks/README.md` |
| `docs/benchmarks/VALIDITY_SUMMARY.md` | incubation | 難易度設計妥当性メモ | `docs/benchmarks/README.md` |
| `docs/papers/PAPER_OUTLINE.md` | incubation | 論文ドラフト構成 | `docs/README.md` |

## Script Assets

| Asset | Status | 理由 | 接続先 |
|---|---|---|---|
| `scripts/pipeline/*` | active | 実験標準導線（preflight/adapt/eval） | `docs/PIPELINE_GUIDE.md`, `Makefile` |
| `scripts/ci/*` | active | 契約検証・品質ゲート | `docs/operations/RUNBOOK.md`, `Makefile` |
| `scripts/daemon/*` | active | 常駐運用（agentd） | `docs/operations/AGENTD.md` |
| `scripts/dev/prepare_worktree.sh` | active | 運用初期化 | `docs/operations/AGENTD.md` |
| `scripts/benchmark/fit_symbol_language_weights.py` | active | 重み学習の公式導線 | `scripts/pipeline/run_corpus_auto_adapt.py` |
| `scripts/benchmark/generate_report.py` | active | レポート生成の公式導線 | `Makefile report` |
| `scripts/benchmark/complete_phase3.py` | active | Phase3残タスク（micro/e2e/ablation/stability）の実測生成 | `Makefile phase3-complete` |
| `scripts/benchmark/analyze_toolcall_reduction.py` | active | tool-call削減率の定量証明 | `tasks/todo.md` |
| `scripts/pipeline/run_cross_env_repro.py` | active | cross-env再現検証（Python 3.11） | `scripts/dev/run_cross_env_repro.sh` |
| `scripts/dev/run_cross_env_repro.sh` | active | cross-env再現の1コマンド実行入口 | `docs/papers/ARTIFACT_APPENDIX.md` |
| `scripts/benchmark/compare_all_tools.py` | incubation | 比較実験の補助スクリプト | `scripts/README.md` |
| `scripts/benchmark/compare_baselines.py` | incubation | 比較実験の補助スクリプト | `scripts/README.md` |
| `scripts/benchmark/compare_with_optimal.py` | incubation | 比較実験の補助スクリプト | `scripts/README.md` |
| `scripts/benchmark/evaluate_taskset.py` | incubation | 単体評価補助 | `scripts/README.md` |
| `scripts/benchmark/investigate_ripgrep.py` | incubation | 事象調査補助 | `scripts/README.md` |
| `scripts/benchmark/parameter_search.py` | incubation | 旧探索導線（pipeline版へ統合済み） | `scripts/README.md` |
| `scripts/benchmark/run_all_experiments.py` | incubation | 旧実行導線（route版へ統合済み） | `scripts/README.md` |
| `scripts/benchmark/run_comparison.py` | incubation | 比較実験補助 | `scripts/README.md` |
| `scripts/benchmark/verify_dataset.py` | incubation | データ検証補助 | `scripts/README.md` |

## Dataset and Root Notes

| Asset | Status | 理由 | 接続先 |
|---|---|---|---|
| `docs/benchmarks/taskset.v2.full.jsonl` | active | 現行 taskset SSOT | `configs/experiment_pipeline.yaml` |
| `docs/benchmarks/taskset.v2.jsonl` | incubation | 旧v2 subset | `docs/benchmarks/README.md` |
| `docs/benchmarks/taskset.v2.1.jsonl` | incubation | 追加版候補 | `docs/benchmarks/README.md` |
| `docs/benchmarks/taskset.v1.jsonl` | archive | 旧世代 taskset | `docs/benchmarks/README.md` |
| `docs/benchmarks/taskset.v1.fixed.jsonl` | archive | v1補修版の履歴 | `docs/benchmarks/README.md` |
| `docs/benchmarks/taskset.v1.jsonl.bak` | archive | バックアップ履歴 | `docs/benchmarks/README.md` |
| `PROPOSED_METHOD_COMPLETE.md` | incubation | 研究要約スナップショット | `docs/README.md` |
| `RIPGREP_INVESTIGATION_REPORT.md` | incubation | 調査ログ | `docs/README.md` |
| `outline.md` | archive | 企画メモ履歴 | `docs/README.md` |
| `plan.md` | archive | 初期計画メモ履歴 | `docs/README.md` |
| `give.md` | archive | インプット原文履歴 | `docs/README.md` |
| `TEMPLATE/README.md` | active | 再利用向けテンプレートバンドルの入口 | `docs/README.md` |
| `TEMPLATE/PROJECT_STRUCTURE.md` | active | 新規プロジェクト構成の標準 | `docs/README.md` |

## 運用ルール

1. 新規資産は本台帳へ登録してから運用導線へ追加する
2. `active` は必ず `docs/README.md` または `scripts/README.md` から辿れる状態にする
3. `archive` は自動実行導線（Make/route/CI）から参照しない
