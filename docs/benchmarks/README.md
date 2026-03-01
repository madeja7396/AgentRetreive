# Benchmark Inputs

更新日: 2026-03-01

`give.md` で提示された評価設計を、実行可能な入力資産へ固定した。

## 実験結果（最新）

**最新評価（2026-02-27）**: 7リポジトリ35タスク

| 指標 | 結果 |
|------|------|
| Overall Recall | **74.3%** (26/35) |
| Average MRR | **0.346** |
| Easy | 85.7% |
| Medium | 64.3% |
| Hard | 57.1% |

**詳細レポート**:
- `docs/research/experiment_findings_v2.md` - **全知見の詳細**
- `docs/benchmarks/TASKSET_V2_EVALUATION.md` - 評価詳細
- `docs/research/roadmap.md` - 改善ロードマップ

## Files

- `docs/benchmarks/corpus.v1.json`
- `docs/benchmarks/corpus.v1.1.json` ← **主要言語カバレッジ拡張版**
- `docs/benchmarks/taskset.v1.jsonl`
- `docs/benchmarks/taskset.v2.full.jsonl` ← **最新タスクセット（35タスク）**
- `docs/benchmarks/baselines.v1.json`
- `docs/benchmarks/run_constraints.v1.json`
- `docs/benchmarks/run_constraints.v2.json` ← **cross-env 許容誤差を明文化**

## Taskset Registry（分類）

- `active`: `taskset.v2.full.jsonl`（現行評価SSOT）
- `incubation`: `taskset.v2.jsonl`, `taskset.v2.1.jsonl`
- `archive`: `taskset.v1.jsonl`, `taskset.v1.fixed.jsonl`, `taskset.v1.jsonl.bak`

## Language Coverage

`corpus.v1.1` は主要言語をカバー:

- Rust
- Go
- C
- C++
- C#
- Python
- JavaScript
- TypeScript
- Java
- Haskell
- Elixir
- PHP
- Ruby
- Kotlin
- Swift
- Dart

## One-Command Adaptation

taskset 対象（7repo）の学習・適応は以下 1 コマンドで実行:

```bash
python3 scripts/pipeline/run_corpus_auto_adapt.py
```

実験前処理から最終評価まで一括実行する場合:

```bash
make experiment
```

全サポート言語コーパス（`corpus.v1.1` 全18repo）を clone/index 対象に含める場合:

```bash
make auto-adapt-all
```

補足:
- デフォルトは公平比較のため `balanced_raw/` を自動生成し、`code_file_count` を厳密一致させたうえで `code_bytes` を統計目標（中央値）へ寄せる
- 複雑性検証用の repo は多指標 z-score（規模・多様性・深さ・サイズ分散）で自動選定され、`artifacts/experiments/pipeline/auto_adapt_summary.json` に記録される

## Validation

- schema: `docs/schemas/*.schema.json`
- CI validator: `scripts/ci/validate_contracts.py`

## Notes

- `taskset.v1.jsonl` は 1 行 1 タスク
- `gold` は壊れにくさ優先で `file + anchor` を採用
- v2.0では難易度別（Easy/Medium/Hard）とタスクタイプ別の評価を導入

## 補助分析ドキュメント（Incubation）

- `docs/benchmarks/CORPUS_EXTENSION_PLAN.md`
- `docs/benchmarks/DATASET_BIAS_ANALYSIS.md`
- `docs/benchmarks/OPTIMAL_PARAMETER_RATIONALE.md`
- `docs/benchmarks/VALIDITY_SUMMARY.md`
