# Schema Index

更新日: 2026-02-25

- `query.dsl.v1.schema.json`: 検索クエリ入力契約
- `result.minijson.v1.schema.json`: 検索結果出力契約
- `dataset_manifest.v1.schema.json`: データセット来歴契約
- `experiment_run_record.v1.schema.json`: 実験記録契約

## 運用

- 破壊的変更は新 version schema を追加する
- 旧 version は即削除せず、移行期間を設ける
