# Experiment Pipeline Guide

## 概要

フル実験パイプラインは、複数リポジトリでの自動評価とパラメータ探索を実現します。

## 構成

```
configs/experiment_pipeline.yaml    # パイプライン設定
scripts/pipeline/                   # パイプラインスクリプト
├── run_full_pipeline.py           # メイン実行スクリプト
artifacts/experiments/pipeline/     # 出力ディレクトリ
```

## クイックスタート

### 0. 実験までの標準導線（推奨）

実験実行までの前処理を含む標準導線は以下。

```bash
make experiment
```

上記 1 コマンドで以下を直列実行:

1. contract 検証（`validate_contracts.py`）
2. テスト（`pytest -q`）
3. corpus auto-adapt（clone/index/学習/探索）
4. final evaluation（`final_summary.json` 生成）

全サポート言語（18repo）で同じ導線を実行する場合:

```bash
make experiment-all
```

前処理チェックのみ行う場合:

```bash
make experiment-ready
```

### 1. コーパス追加後のワンコマンド自動適応（推奨）

```bash
python3 scripts/pipeline/run_corpus_auto_adapt.py
```

上記 1 コマンドで以下を自動実行:

1. `docs/benchmarks/corpus.v1.1.json` を読み込み（主要言語カバレッジを検証）
2. タスクセットに存在する repo を clone/update
3. 統計的バランシングで `balanced_raw/` を生成（公平比較用に code files を厳密一致、code bytes を統計目標へ収束）
4. index を再構築
5. `symbol_language_weights.v1` を学習
6. パラメータ探索 (`run_full_pipeline.py`) を実行

主要言語カバレッジ判定対象:
- Rust / Go / C / C++ / C# / Python / JavaScript / TypeScript / Java
- Haskell / Elixir / PHP / Ruby / Kotlin / Swift / Dart

追加したコーパスのみ対象にする例:

```bash
python3 scripts/pipeline/run_corpus_auto_adapt.py --repos axios,typescript,gson
```

全サポート言語コーパスを毎回強制同期するワンコマンド:

```bash
make auto-adapt-all
```

補足:
- `--repos` で指定した repo にタスクが未登録の場合、index は作成されるが重み学習は自動スキップされる
- 全コーパスを強制処理する場合は `--index-all` を付与する
- バランシングを無効化して生リポジトリを使う場合は `--no-balance` を付与する
- 実行環境で `ProcessPoolExecutor` が使えない場合、探索は `ThreadPoolExecutor` へ自動フォールバックする
- clone timeout は `AR_CLONE_TIMEOUT_SEC`（デフォルト 1800秒）で調整できる
- バランシングは `target_files=min(repo code files)` と `target_bytes=median(target_files * repo_mean_file_bytes)` を統計的に決定する
- 各 repo は `target_files` を満たしつつ `target_bytes` への偏差が最小になるよう deterministic にサンプリングされる
- 複雑性検証用 repo は `code_file_count / code_bytes / language_diversity / extension_diversity / language_entropy / path_depth_p90 / file_size_cv` の z-score 合算で自動選定し、`auto_adapt_summary.json` に記録する

### 2. テスト実行（fdリポジトリのみ）

```bash
make test
# または
python3 scripts/pipeline/run_full_pipeline.py
```

### 3. フルパイプライン実行

```bash
make pipeline
# または
python3 scripts/pipeline/run_full_pipeline.py -c configs/experiment_pipeline.yaml
```

### 4. 検証

```bash
make validate
```

## 設定ファイル

`configs/experiment_pipeline.yaml`:

```yaml
repositories:      # 評価対象リポジトリ
  - id: fd
    language: rust
    index: artifacts/datasets/fd.index.json
    ...

parameter_search:  # パラメータ探索設定
  enabled: true
  grid:
    k1: [0.8, 1.0, 1.2, 1.5, 2.0]
    b: [0.3, 0.5, 0.75, 0.9, 1.0]
    min_match_ratio: [0.0, 0.25, 0.5, 0.75]
    max_terms: [2, 3, 4]
  
  optimization:    # 最適化目標
    primary_metric: mrr
    secondary_metric: recall
    weights:
      easy: 1.0
      medium: 1.5
      hard: 2.0
```

## パイプラインの流れ

1. **設定読み込み** - YAML設定を解析
2. **リポジトリ巡回** - 各リポジトリを順次処理
3. **パラメータ探索** - グリッドサーチを実行
4. **最適設定選定** - 重み付きスコアで選定
5. **フル評価** - 最適設定で全タスク評価
6. **結果保存** - JSON/CSV/MD形式で出力

## 出力ファイル

```
artifacts/experiments/pipeline/
├── {repo}_search_results.json     # パラメータ探索結果（全設定 + 最適設定）
├── aggregate_results.json         # 集計結果（repo別最適値を含む）
└── generated_experiment_pipeline.auto.yaml  # auto-adapt生成設定
```

## パラメータ探索の仕組み

### 探索空間

| パラメータ | 範囲 | ステップ |
|-----------|------|---------|
| k1 | 0.8 - 2.0 | 5値 |
| b | 0.3 - 1.0 | 5値 |
| min_match_ratio | 0.0 - 0.75 | 4値 |
| max_terms | 2 - 4 | 3値 |

**総組み合わせ**: 5 × 5 × 4 × 3 = **300通り**

### 最適化スコア計算

```
score = Σ (difficulty_weight × mrr_by_difficulty)

Weights:
  easy:   1.0
  medium: 1.5
  hard:   2.0
```

## 拡張方法

### 新規リポジトリ追加

1. `docs/benchmarks/corpus.v1.1.json` にコーパスを追加:

```json
{
  "id": "new_repo",
  "url": "https://github.com/org/new_repo",
  "commit": "abcdef1",
  "tag": "v1.0.0",
  "license": "MIT",
  "primary_language": "TypeScript",
  "notes": "..."
}
```

2. タスクセットにタスク追加:
```bash
# docs/benchmarks/taskset.v2.full.jsonl に追記
```

3. 実行:
```bash
python3 scripts/pipeline/run_corpus_auto_adapt.py
```

### パラメータ範囲変更

`configs/experiment_pipeline.yaml` を編集:
```yaml
parameter_search:
  grid:
    k1: [0.5, 1.0, 1.5]  # 新しい範囲
```

## Makefile Targets

| Target | 説明 |
|--------|------|
| `make pipeline` | フルパイプライン実行 |
| `make test` | クイックテスト |
| `make validate` | 契約検証 |
| `make clean` | 出力削除 |
| `make report` | レポート生成 |

## デバッグ

### 個別リポジトリテスト

```bash
python3 << 'EOF'
from scripts.pipeline.run_full_pipeline import *

config = ExperimentConfig(k1=1.2, b=0.9, min_match_ratio=0.5, max_terms=3)
result = evaluate_single_config(
    config, 'fd',
    Path('artifacts/datasets/fd.index.json'),
    tasks
)
print(result)
EOF
```

## 注意事項

- パラメータ探索は時間がかかります（300通り × リポジトリ数）
- curl/cli など大規模 repo の探索時間が支配的になりやすい
- `--index-all` は巨大 repo clone がボトルネックになりうるため、通常は taskset 対象 repo で実行する

## 実験結果の解釈

パイプライン実行後、以下のドキュメントを参照して結果を理解してください:

| ドキュメント | 内容 |
|-------------|------|
| `docs/research/experiment_findings_v2.md` | **実験結果の全知見** - 必読 |
| `docs/research/roadmap.md` | 発見された課題と改善計画 |
| `docs/benchmarks/TASKSET_V2_EVALUATION.md` | 評価詳細データ |

### 主要な発見（2026-02-27 再実行）

- **Overall Recall**: 74.3% (26/35タスク)
- **最適パラメータ**: repoごとに異なるため `aggregate_results.json` を参照
- **重要知見**: `ProcessPoolExecutor` 非対応環境でもフォールバックにより探索は完走可能
- **課題**: 大規模 repo（特に curl/cli）で探索時間が長く、軽量サブセット運用の設計が必要

## 次のステップ

1. パイプライン実行: `make pipeline`
2. 結果確認: `artifacts/experiments/pipeline/`
3. **結果解釈**: `docs/research/experiment_findings_v2.md` を読む
4. 改善計画確認: `docs/research/roadmap.md`
