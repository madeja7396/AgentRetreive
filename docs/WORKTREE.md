# Worktree Guide

更新日: 2026-02-25

## 目的

- 開発・実験でワークツリーを常にクリーンに保つ
- ローカル生成物と追跡対象ファイルを分離する

## ルール

- 仕様/計画/スキーマは Git 管理する
- 実験出力は `artifacts/` に集約し Git 管理しない
- 配布用生成物は `dist/` に置き Git 管理しない

## 初期化

```bash
./scripts/dev/prepare_worktree.sh
```

これにより以下を作成する:

- `artifacts/datasets/{manifests,raw,processed}`
- `artifacts/experiments/{runs,summaries}`
- `artifacts/papers/{figures,tables}`
- `dist/`

## 日常運用

- 作業前: `git status --short --branch` で差分確認
- 作業後: CI 相当の検証を実行してからコミット
  - `python scripts/ci/validate_contracts.py`
