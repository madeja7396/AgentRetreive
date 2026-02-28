# Maintenance Governance Manual

更新日: 2026-02-28

## 目的

- 属人化を排除し、誰が担当しても同品質で運用できる状態を作る
- 「してよいこと / してはいけないこと」を明文化して判断ブレを防ぐ
- 変更管理、障害対応、実験運用を同じ統治ルールで扱う

## 適用範囲

- `docs/`, `tasks/`, `scripts/`, `skills/`, `configs/` の変更
- 実験パイプライン実行 (`make experiment*`, `run_experiment_route.py`)
- 生成物管理 (`artifacts/`) と公式KPI更新

## 役割定義（RACI）

| Role | 責務 | 必須アウトプット |
|---|---|---|
| Maintainer (R) | 実装・修正・運用作業を実行 | 変更差分、検証ログ、`tasks/todo.md` 更新 |
| Reviewer (A) | 変更承認、品質ゲート判定 | `tasks/todo.md` レビュー判定 |
| Operator (C) | 定期実行、障害一次切り分け | 実行ログ、障害チケット |
| Archivist (I) | 証跡保全、台帳更新 | run metadata、`tasks/lessons.md` |

## Skill Owner 割当（実運用）

- `core_quality`: AgentRetrieve Core Quality Team（`core-quality-oncall`）
- `ops_runtime`: AgentRetrieve Runtime Operations Team（`ops-runtime-oncall`）
- `ops_governance`: AgentRetrieve Governance Operations Team（`ops-governance-oncall`）
- `program_office`: AgentRetrieve Program Office（`program-office`）
- 定義元は `skills/CATALOG.yaml` の `owners` セクションとし、skill の `owner` は上記IDのみ許可する

## 作業フロー（標準）

1. 受領: 要求を `tasks/todo.md` にチェック項目化
2. 影響分析: 仕様・データ・運用への影響範囲を明確化
3. 実装: 最小差分で変更
4. 検証: `pytest -q` と `python3 scripts/ci/validate_contracts.py` を必須実行
5. 記録: `tasks/todo.md` レビュー欄と `tasks/lessons.md` を更新
6. 引き継ぎ: 次担当が再実行できる状態で終了

## してよいこと（Allow）

- 契約を守る変更（schema/SSOT と整合）
- 検証付きの運用導線改善
- 再現性向上のための自動化追加
- 失敗を隠さない記録更新（lessons / review）

## してはいけないこと（Deny）

- 検証未実施での運用値更新
- `final_summary.json` と `aggregate_results.json` の用途混同
- `artifacts/datasets/raw/` 生データ上書き
- 仕様更新なしでの実装先行変更
- 任意シェル実行の運用常態化（固定導線を破る行為）

## KPI管理ルール

- 公式KPIのSSOTは `artifacts/experiments/pipeline/final_summary.json`
- `aggregate_results.json` は探索用（最適パラメータ検討）
- 評価前に `gold_coverage_summary.json` を生成し、coverage fail は即停止

## 変更管理ルール

- 破壊的変更は v1 上書き禁止（version を上げる）
- すべての重要変更は `tasks/todo.md` にレビュー行を残す
- ユーザー修正が入った場合は `tasks/lessons.md` を同日更新する

## 監査チェック（毎週）

- `make validate` が通るか
- `make experiment-ready` が通るか
- `make report` が通るか
- `tasks/todo.md` の未完了項目に owner/期限があるか
- `tasks/lessons.md` が最新インシデントを反映しているか
- `skills/CATALOG.yaml` の `owner` が `owners` 定義IDに一致しているか
