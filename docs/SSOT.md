# SSOT (Single Source of Truth)

更新日: 2026-02-25

## 目的

- 仕様の一次情報を固定し、実装・実験・論文の不整合を防ぐ

## 優先順位

1. `docs/` の仕様（本書・名前空間・スキーマ）
2. `tasks/` の運用記録（進捗、レビュー、リスク）
3. `plan.md` / `outline.md` の構想

矛盾がある場合は、上位を正として下位を更新する。

## SSOT レジストリ

| Domain | SSOT File | Notes |
|---|---|---|
| 仕様ガバナンス | `docs/SSOT.md` | 仕様の優先順位と変更規則 |
| 名前空間 | `docs/NAMESPACE_RESERVATIONS.md` | 予約キー・ID・prefix |
| Query DSL v1 | `docs/schemas/query.dsl.v1.schema.json` | 入力契約 |
| Result v1 | `docs/schemas/result.minijson.v1.schema.json` | 出力契約 |
| Dataset Manifest v1 | `docs/schemas/dataset_manifest.v1.schema.json` | データ来歴契約 |
| Experiment Run Record v1 | `docs/schemas/experiment_run_record.v1.schema.json` | 実験再現契約 |
| Benchmark Inputs v1 | `docs/benchmarks/*` | 評価コーパス、タスク、ベースライン、実行制約 |
| Experiment Findings v2 | `docs/research/experiment_findings_v2.md` | 最新実験結果（7リポジトリ35タスク） |
| Research Roadmap | `docs/research/roadmap.md` | 改善計画と優先順位 |
| Implementation Contract v1 | `docs/contracts/*` | 契約ポリシーと実装ガードレール |
| Agent Daemon Contract v1 | `docs/schemas/daemon_task.v1.schema.json` | 常駐タスク契約 |
| Project Execution Tasks v1 | `tasks/project_execution_plan.v1.jsonl` | 登録専用の全体実行計画 |
| 計画進行 | `tasks/todo.md` | 実行フェーズ、ゲート、レビュー |
| リスク管理 | `tasks/risk_register.md` | リスクと緩和策 |
| 検証定義 | `tasks/validation_matrix.md` | 検証方法と exit criteria |

## 変更ルール

- 仕様変更時は、関連する schema と namespace を同一コミットで更新する
- 破壊的変更は新 version を追加し、旧 version の廃止時期を明記する
- 論文に使う数値は schema 準拠の実験記録からのみ取得する
