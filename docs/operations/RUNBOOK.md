# Operations Runbook

更新日: 2026-02-28

## Day-1 セットアップ

1. 前提確認:
```bash
python3 --version
pytest --version
```
2. 品質ゲート:
```bash
make validate
make experiment-ready
```
3. 失敗時:
- `docs/operations/MAINTENANCE_GOVERNANCE.md` のフローで復旧
- 復旧後に `tasks/lessons.md` を更新

## Day-2 定常運用

### 日次

```bash
pytest -q
python3 scripts/ci/validate_contracts.py
```

### 週次

```bash
make validate
make experiment-ready
make report
```

確認項目:
- `artifacts/experiments/pipeline/final_summary.json` の更新有無
- `artifacts/experiments/pipeline/gold_coverage_summary.json` が `coverage_ok=true` か
- `tasks/todo.md` の残タスクに優先度が付いているか

## KPI更新手順（公式）

1. raw固定で評価:
```bash
python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4
```
2. SSOT確認:
- `artifacts/experiments/pipeline/final_summary.json`
3. レポート更新:
```bash
make report
```
4. `tasks/todo.md` に実行記録を追記

## 障害対応（一次）

1. 症状分類:
- 契約違反
- テスト失敗
- gold coverage fail
- 実験導線 fail
2. 最小復旧:
- 変更を最小単位に分割
- 検証コマンド再実行
3. 記録:
- `tasks/lessons.md` に再発防止ルールを追加

## エスカレーション条件

- `make validate` が連続2回以上失敗
- `gold_coverage_summary.json` が fail のまま復旧不能
- 公式KPIのSSOTが特定できない状態

## エスカレーション連絡先（skills owner）

- 品質ゲート障害: `core_quality` (`core-quality-oncall`)
- 実行導線障害: `ops_runtime` (`ops-runtime-oncall`)
- KPI運用障害: `ops_governance` (`ops-governance-oncall`)
- 組織運用課題: `program_office` (`program-office`)
