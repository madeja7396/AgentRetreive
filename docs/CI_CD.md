# CI/CD Guide

更新日: 2026-03-01

## CI

Workflow: `.github/workflows/ci.yml`

- Trigger:
  - `pull_request`
  - `push` to `main`
  - manual (`workflow_dispatch`)
- Jobs:
  - Contract Validation (Python 3.11, 3.12)
  - Unit Tests (Python 3.11, 3.12)
  - Figure Integrity (Python 3.12)
  - Release Ready (main branch only)
- Checks:
  - JSON 構文検証（`docs/schemas/*.json`, `tasks/templates/*.json`, `docs/contracts/*.json`）
  - schema 検証（テンプレートが schema に準拠）
  - schema 検証（`docs/benchmarks/*` が対応 schema に準拠）
  - schema 検証（`tasks/project_execution_plan.v1.jsonl` が task schema に準拠）
  - クロスファイル不変条件（重複ID、参照整合、件数下限、レイテンシ順序）
  - `pytest -q`（`PYTHONPATH=src`）

実行スクリプト:

```bash
bash scripts/ci/run_contract_harness.sh --refresh
```

## CD

Workflow: `.github/workflows/cd-release.yml`

- Trigger:
  - `push` tag `v*`（例: `v0.1.0`）
  - manual (`workflow_dispatch`)
- Job:
  - release artifact を `dist/` に作成
  - GitHub Actions Artifact としてアップロード
  - tag push 時は GitHub Release に添付

生成物:

- `agentretrieve-<label>.tar.gz`
- `SHA256SUMS.txt`

## Release Ready ゲート

ローカル実行:

```bash
make release-ready
# または明示的に RUN_ID を指定
make release-ready RUN_ID=run_20260228_154238_exp001_raw
```

これは以下を順次実行します:
1. `validate` - 契約検証
2. `pytest` - ユニットテスト
3. `figures` - 論文図表生成（既定 RUN_ID: `run_20260228_154238_exp001_raw`）
4. `validate_figure_integrity --strict` - 図表整合検証
5. `template-sync-check` - TEMPLATE 同期検証
6. `report` - レポート生成

## 運用ルール

- schema 変更は CI 通過を必須にする
- release は tag ベースで行う
- 論文で参照する成果物は release artifact を正とする
- 図表は **手編集禁止** - 必ず `make figures` で機械生成する
