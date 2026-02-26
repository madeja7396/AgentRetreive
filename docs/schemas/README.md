# Schema Index

更新日: 2026-02-25

- `query.dsl.v1.schema.json`: 検索クエリ入力契約
- `result.minijson.v1.schema.json`: 検索結果出力契約
- `dataset_manifest.v1.schema.json`: データセット来歴契約
- `experiment_run_record.v1.schema.json`: 実験記録契約
- `corpus.v1.schema.json`: 評価コーパス定義
- `taskset.v1.entry.schema.json`: 評価タスク 1 件の定義（JSONL 行単位）
- `baselines.v1.schema.json`: 比較ベースライン定義
- `run_constraints.v1.schema.json`: 実行制約定義
- `contract_policy.v1.schema.json`: 契約厳格ポリシー定義
- `daemon_task.v1.schema.json`: 常駐デーモンタスク定義
- `project_execution_task.v1.entry.schema.json`: 実行計画タスク定義（JSONL行単位）

## 運用

- 破壊的変更は新 version schema を追加する
- 旧 version は即削除せず、移行期間を設ける
