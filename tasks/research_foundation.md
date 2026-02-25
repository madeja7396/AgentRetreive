# Research Foundation

更新日: 2026-02-25

## 1. 研究運用ポリシー

- すべての主張は実験 ID で追跡可能にする
- 生データを不変（immutable）で保存し、派生データは別ディレクトリに出力する
- 実験は設定・コード・環境を同時に記録し、再実行を可能にする
- 論文図表はスクリプト生成のみを許可し、手編集を禁止する

## 2. 推奨ディレクトリ規約

```text
artifacts/
  datasets/
    manifests/
    raw/
    processed/
  experiments/
    runs/
    summaries/
  papers/
    figures/
    tables/
```

## 3. データ蓄積の最小要件

- dataset manifest を作成する
- ひな形は `tasks/templates/dataset_manifest.json` を利用する
- 構造は `docs/schemas/dataset_manifest.v1.schema.json` に準拠する
- 各 dataset に以下を保持する:
  - source（URL/リポジトリ）
  - snapshot（commit / release tag / date）
  - license
  - collection script version
  - checksum
- raw データは追記のみ、上書き禁止
- processed データは生成スクリプトと入力 manifest ID を紐付ける

## 4. 実験記録の最小要件

- run ごとに `run_id` を採番する
- ひな形は `tasks/templates/experiment_run_record.json` を利用する
- 構造は `docs/schemas/experiment_run_record.v1.schema.json` に準拠する
- 以下メタデータを必須化する:
  - git commit
  - config hash
  - random seed
  - runtime environment（OS, CPU, RAM, toolchain）
  - start/end time
  - metrics summary
  - artifact paths
- 失敗 run も削除しない（failure analysis の対象）

## 5. 環境非依存性の要件

- lockfile ベースで依存バージョンを固定する
- 実験は「クリーン環境で 1 コマンド再実行」できる状態を維持する
- 環境差異を埋めるため、最低 2 環境で再現試験を行う
- 再現許容誤差（例: 指標差 < 1%）を事前に定義する

## 6. 論文成果物の要件

- 主張一覧と対応実験 ID の対応表を作る
- 図表ごとに生成スクリプトと入力 run ID を記録する
- 結果章の全数値は再集計スクリプトで再生成可能にする
- Appendix に再現手順と計算資源要件を記載する

## 7. 完了判定（Research Ready）

- dataset manifest と run registry が揃っている
- 主要結果が別環境で再現できている
- 論文ドラフトで全主張が実験証跡に接続されている
