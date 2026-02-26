# Implementation Contract

更新日: 2026-02-26

## 目的

- 実装・評価・論文化の契約境界を固定する
- CI で機械検証できる不変条件を明示する

## 契約対象

- 入出力 schema: `docs/schemas/*.schema.json`
- ベンチマーク入力: `docs/benchmarks/*`
- 研究テンプレート: `tasks/templates/*.json`
- 常駐タスク入力: `tasks/templates/daemon_task.v1.json`
- 実行計画タスク入力: `tasks/project_execution_plan.v1.jsonl`
- 厳格ポリシー: `docs/contracts/contract_policy.v1.json`

## 強制ルール

- schema は Draft 2020-12 として妥当であること
- サンプル JSON / JSONL は schema 準拠であること
- クロスファイル整合:
  - `taskset.repo` は `corpus.id` に必ず存在
  - `taskset.id` は一意
  - `baseline.tool` は一意
  - `run_constraints.latency_targets` は `p50 <= p95 <= p99`
- ポリシー下限:
  - `corpora >= 5`
  - `baselines >= 4`
  - `tasks_total >= 25`
  - `tasks_per_repo >= 5`

## 変更ルール

- 契約を強化/緩和する場合は `contract_policy` を更新する
- 破壊的変更は新バージョン追加（v1上書き禁止）
- 契約更新時は validator を同一コミットで更新する
