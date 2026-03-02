# Operations Runbook

更新日: 2026-03-03

## Day-1 セットアップ

1. 前提確認:
```bash
python3 --version
pytest --version
python3.11 --version
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
make experiment-fast
```

### 週次

```bash
make validate
make experiment-ready
make report
make template-sync-check
make experiment-daily-full
```

確認項目:
- `artifacts/experiments/pipeline/final_summary.json` の更新有無
- `artifacts/experiments/pipeline/gold_coverage_summary.json` が `coverage_ok=true` か
- `tasks/todo.md` の残タスクに優先度が付いているか
- 図表資産の鮮度（`FIGURE_SOURCES.v1.json` 対応表と整合性）

## 高速実験ループ

```bash
make experiment-fast
```

- profile: `fast`
- repo: `fd,ripgrep,fzf,fmt,curl,pytest,cli`
- grid: `fast`（縮小グリッド）
- cache/state:
  - `artifacts/experiments/fast/cache/search`
  - `artifacts/experiments/fast/state/auto_adapt_state.v1.json`

差分がない場合、index と symbol-fit は短絡スキップされる。強制再実行する場合:

```bash
python3 scripts/pipeline/run_experiment_route.py --profile fast --force-index --force-symbol-fit
```

## KPI更新手順（公式）

1. raw固定で評価:
```bash
python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4
```
2. run record 生成:
```bash
make run-record RUN_ID=run_20260228_154238_exp001_raw
```
3. SSOT確認:
- `artifacts/experiments/pipeline/final_summary.json`
4. レポート更新:
```bash
make report
```
5. `tasks/todo.md` に実行記録を追記

## 図表更新手順（論文用）

図表は **手編集禁止**です。必ず以下の手順で機械生成してください。

### 既定 RUN_ID 方針

- **既定値**: `run_20260228_154238_exp001_raw`
- 明示的に変更しない場合は既定値が自動適用される
- 新しい実験で基準を変更する場合は、`docs/papers/FIGURE_SOURCES.v1.json` と `Makefile` の両方を更新

### 手順

1. 図表生成（既定 RUN_ID が自動適用）:
```bash
make figures
```

または明示的に指定:
```bash
make figures RUN_ID=run_20260228_154238_exp001_raw
```

2. 整合検証（strict - 警告もエラーとして扱う）:
```bash
python3 scripts/ci/validate_figure_integrity.py --strict
```

3. 検証失敗時:
- 手編集していた場合は手動変更を `git checkout` で破棄
- スクリプト修正後、再生成
- それでも解消しない場合は `FIGURE_SOURCES.v1.json` の input_artifacts パスを確認

## Release Ready ゲート

リリース前に以下を一括実行:

```bash
make release-ready RUN_ID=run_20260228_154238_exp001_raw
```

これは以下を順次実行します:
1. `make validate` - 契約検証
2. `pytest -q` - ユニットテスト
3. `make figures RUN_ID=...` - 図表生成（strict）
4. `validate_figure_integrity.py --strict` - 図表整合検証
5. `template-sync-check` - TEMPLATE 同期検証
6. `make report` - レポート生成

## CLI配布ゲート（製品配布向け）

CLI配布前は以下を実行:

```bash
make release-cli-ready LABEL=local TARGET=linux-x86_64
```

チェック内容:

1. `cargo build --release -p ar-cli`
2. `cargo build --profile release-dist -p ar-cli`
3. `check_binary_size.sh`（stripped binary `<= 3.5MB`）
4. `bench_cli_regression.py`（query p50 劣化 `<= 5%`）
5. `package_cli_distribution.sh`（`dist/*.tar.gz` + checksum）

詳細は `docs/operations/CLI_DISTRIBUTION.md` を参照。

## Cross-Env 再現

Python 3.11 で主要実験の再現判定:

```bash
make repro-cross-env RUN_ID=run_20260228_154238_exp001_raw
```

依存固定:

- `requirements-lock.txt`
- `Dockerfile.repro`

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
- TEMPLATE 初期化障害: `ops_runtime` (`ops-runtime-oncall`)

## TEMPLATE 運用

### 新規プロジェクト初期化

```bash
# 基本形
make template-init TARGET=/path/to/new-project

# プロジェクト名と所有者を指定
make template-init TARGET=/path/to/new-project NAME="MyProject" OWNER="my-team"

# 初期化後の検証
cd /path/to/new-project
python3 scripts/ci/validate_contracts.py
```

### TEMPLATE smoke テスト

```bash
make template-smoke
```

### TEMPLATE 更新手順

1. **正本側を先に更新**: `docs/`, `scripts/` などの正本を更新して検証
2. **TEMPLATE へ同期**: `make template-sync` でバンドルを更新
3. **初期化テスト**: `make template-smoke` で生成品質を検証
4. **破壊的変更時**: TEMPLATE version を上げ、移行ガイドを作成

**注意**: TEMPLATE 更新後は必ず `make template-smoke` を実行し、生成品質を確認すること。
