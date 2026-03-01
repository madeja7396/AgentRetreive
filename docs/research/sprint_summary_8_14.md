# Sprint 8-14 実験まとめ

更新日: 2026-03-01

## 概要

Sprint 8から14までの実験活動を通じて、AgentRetrieveの検索性能を評価・改善し、多言語対応とスケーラビリティを検証した。

## 主要成果

### 1. Baseline v1.1達成（Sprint 8-10）

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Recall@1 | ≥70% | 74.3% | ✅ 達成 |
| MRR | ≥0.35 | 0.381 | ✅ 達成 |
| Avg Latency | <2.0ms | 0.75ms | ✅ 達成 |
| Repositories | 7 | 7 | ✅ 達成 |
| Tasks | ≥25 | 35 | ✅ 達成 |

**主要run**: `run_20260301_144348_route`

### 2. 多言語対応（Sprint 13）

Baseline v1.1で5言語（Rust, Go, C, C++, Python）をカバー。
追加で4言語（JavaScript, Haskell, Elixir, C#）のindexを構築。

| 言語 | リポジトリ | Docs | 評価状態 |
|------|-----------|------|---------|
| Rust | fd, ripgrep | 125 | ✅ 評価済 |
| Go | fzf | 85 | ✅ 評価済 |
| C | curl | 990 | ✅ 評価済 |
| C++ | fmt | 75 | ✅ 評価済 |
| Python | pytest, cli | 1,047 | ✅ 評価済 |
| JavaScript | axios | 164 | ⏳ 未評価 |
| Haskell | cabal | 1,927 | ⏳ 未評価 |
| Elixir | elixir | 544 | ⏳ 未評価 |
| C# | aspnetcore | 10,417 | ⏳ 未評価 |

### 3. スケーラビリティ検証（Sprint 11）

| 規模 | リポジトリ | Docs | Index Size |
|------|-----------|------|------------|
| Small | fd, fmt | 24-75 | 1-9 MB |
| Medium | curl, cli, pytest | 257-990 | 11-44 MB |
| Large | aspnetcore | 10,417 | 254 MB |
| **Total** | 11 repos | 15,374 | 360 MB |

**主要発見**: Index sizeはdoc数に対してsub-linearに増加（圧縮効果）。

## 実験導線の整備

### 自動化されたワークフロー

```
make experiment-fast      → Fast実験（7 repos, ~3分）
make experiment-daily-full → Full実験（7 repos, ~10分）
make release-ready        → 全検証ゲート（5ステップ）
```

### Run Record生成

- `run_experiment_route.py`経由で自動生成
- v2形式で記録（run_record.v2.json）
- Registry: `artifacts/experiments/run_registry.v2.jsonl`

### 品質ゲート

1. contracts: 68チェック
2. pytest: 27 tests
3. figures: 8種類生成
4. figure-integrity: 0 errors, 0 warnings
5. template-sync: PASS

## 論文用図表

| 図表 | 内容 | 状態 |
|------|------|------|
| retrieval_recall_by_repo | リポジトリ別recall | ✅ |
| retrieval_latency_by_repo | リポジトリ別レイテンシ | ✅ |
| tool_call_comparison | ツール比較 | ✅ |
| micro_benchmark_summary | マイクロベンチマーク | ✅ |
| ablation_study | アブレーション | ✅ |
| stability_analysis | 安定性分析 | ✅ |
| cross_env_reproducibility | 環境再現性 | ✅ |
| symbol_extraction_coverage | シンボル抽出カバレッジ | ✅ |

全8種類の図表が`artifacts/papers/figures/`に生成済。

## 今後の課題

### 短期的（1-2ヶ月）

1. **未評価言語の検証**
   - Haskell (cabal): 関数型言語でのシンボル抽出
   - Elixir: 動的型付け関数型言語
   - JavaScript: 動的型付け言語での検索

2. **大規模リポジトリ評価**
   - aspnetcore (10k+ docs): 検索レイテンシとrecall
   - Index構築時間の最適化

### 中期的（3-6ヶ月）

1. **シンボル抽出精度の改善**
   - 言語別の抽出モード改善
   - fallback_rateの低減

2. **Taskset拡張**
   - 追加言語用のgoldデータ作成
   - 難易度別タスクの充実

### 長期的（6-12ヶ月）

1. **リアルタイム検索**
   - 大規模リポジトリでの性能最適化
   - 増分index更新

2. **多言語統合評価**
   - 9言語統一KPIの測定
   - 言語間転移学習の検討

## まとめ

Sprint 8-14で以下を達成:

- ✅ Baseline v1.1: Recall 74.3%, MRR 0.381
- ✅ 多言語基盤: 9言語対応（5評価済 + 4未評価）
- ✅ スケーラビリティ: 15k+ docs検証
- ✅ 実験導線: 自動化・品質ゲート整備
- ✅ 論文用図表: 8種類生成

次ステップ: 未評価言語（Haskell, Elixir, JavaScript, C#）での検索品質評価。
