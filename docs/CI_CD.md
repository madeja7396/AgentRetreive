# CI/CD Guide

更新日: 2026-02-25

## CI

Workflow: `.github/workflows/ci.yml`

- Trigger:
  - `pull_request`
  - `push` to `main`
  - manual (`workflow_dispatch`)
- Job:
  - Contract Validation
- Checks:
  - JSON 構文検証（`docs/schemas/*.json`, `tasks/templates/*.json`）
  - schema 検証（テンプレートが schema に準拠）
  - schema 検証（`docs/benchmarks/*` が対応 schema に準拠）

実行スクリプト:

```bash
python scripts/ci/validate_contracts.py
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

## 運用ルール

- schema 変更は CI 通過を必須にする
- release は tag ベースで行う
- 論文で参照する成果物は release artifact を正とする
