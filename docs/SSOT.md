# SSOT (Single Source of Truth)

更新日: 2026-03-01

## 最新実験結果（Baseline v1.1 確定値）

| Metric | Fast Profile | Full Profile | Target | Status |
|--------|--------------|--------------|--------|--------|
| Recall@1 | 74.3% (26/35) | 74.3% (26/35) | ≥70% | ✅ 達成 |
| MRR | 0.381 | 0.381 | ≥0.35 | ✅ 達成 |
| Avg Latency | 0.62ms | 0.75ms | <2.0ms | ✅ 達成 |
| Repositories | 7 | 7 | 7 | ✅ 達成 |
| Tasks | 35 | 35 | ≥25 | ✅ 達成 |
| Gold Coverage | OK | OK | OK | ✅ 達成 |

### 確定日
- 2026-03-01

### 参照実験
- run_id: `run_20260301_144348_route`
- profile: `full`
- run_record: `artifacts/experiments/runs/run_20260301_144348_route/`

### 備考
- Fast/Full両プロファイルで同一KPIを達成し、再現性を確認
- 全目標値を達成し、Baseline v1.1として確定
- 詳細: `docs/benchmarks/results.latest.json`

## 多言語分析（Sprint 13）

| 言語 | リポジトリ数 | 合計Docs | 平均Docs | 例 |
|------|-------------|---------|---------|-----|
| C# | 1 | 10,417 | 10,417 | aspnetcore |
| Haskell | 1 | 1,927 | 1,927 | cabal |
| Python | 2 | 1,047 | 523 | pytest, cli |
| C | 1 | 990 | 990 | curl |
| Elixir | 1 | 544 | 544 | elixir |
| JavaScript | 1 | 164 | 164 | axios |
| Rust | 2 | 125 | 62 | fd, ripgrep |
| Go | 1 | 85 | 85 | fzf |
| C++ | 1 | 75 | 75 | fmt |

### カバレッジ
- Baseline v1.1: 5言語（Rust, Go, C, C++, Python）
- 追加可能: 4言語（JavaScript, Haskell, Elixir, C#）
- 詳細: `docs/benchmarks/multilang_analysis.v1.json`

## スケーラビリティ分析（Sprint 11）

| 規模 | リポジトリ | Docs | Index Size |
|------|-----------|------|------------|
| Small | fd, fmt | 24-75 | 1-9 MB |
| Medium | curl, cli, pytest | 257-990 | 11-44 MB |
| Large | aspnetcore | 10,417 | 254 MB |
| **Total** | 9 repos | 12,903 | 360 MB |

### 分析結果
- Baseline 7 reposはsmall-to-mediumスケール（合計2,322 docs）
- aspnetcoreは42倍の大規模リポジトリだが、index sizeは14.4倍（圧縮効果）
- 詳細: `docs/benchmarks/scale_analysis.v1.json`

更新日: 2026-02-25

## 目的

- 仕様の一次情報を固定し、実装・実験・論文の不整合を防ぐ

## 優先順位

1. `docs/` の仕様（本書・名前空間・スキーマ）
2. `tasks/` の運用記録（進捗、レビュー、リスク）
3. `plan.md` / `outline.md` の構想

矛盾がある場合は、上位を正として下位を更新する。

## SSOT レジストリ

| Domain | SSOT File | Notes |
|---|---|---|
| 仕様ガバナンス | `docs/SSOT.md` | 仕様の優先順位と変更規則 |
| 名前空間 | `docs/NAMESPACE_RESERVATIONS.md` | 予約キー・ID・prefix |
| Query DSL v1 | `docs/schemas/query.dsl.v1.schema.json` | 入力契約 |
| Result v1 | `docs/schemas/result.minijson.v1.schema.json` | 出力契約 |
| Result v2 | `docs/schemas/result.minijson.v2.schema.json` | capability freshness を含む出力契約 |
| Dataset Manifest v1 | `docs/schemas/dataset_manifest.v1.schema.json` | データ来歴契約 |
| Experiment Run Record v1 | `docs/schemas/experiment_run_record.v1.schema.json` | 実験再現契約 |
| Experiment Run Record v2 | `docs/schemas/experiment_run_record.v2.schema.json` | e2e/micro を含む実験再現契約 |
| Run Constraints v2 | `docs/benchmarks/run_constraints.v2.json` | 再現許容誤差を含む実行制約 |
| Benchmark Inputs v1 | `docs/benchmarks/*` | 評価コーパス、タスク、ベースライン、実行制約 |
| Experiment Findings v2 | `docs/research/experiment_findings_v2.md` | 最新実験結果（7リポジトリ35タスク） |
| Research Roadmap | `docs/research/roadmap.md` | 改善計画と優先順位 |
| Implementation Contract v1 | `docs/contracts/*` | 契約ポリシーと実装ガードレール |
| Agent Daemon Contract v1 | `docs/schemas/daemon_task.v1.schema.json` | 常駐タスク契約 |
| Project Execution Tasks v1 | `tasks/project_execution_plan.v1.jsonl` | 登録専用の全体実行計画 |
| 計画進行 | `tasks/todo.md` | 実行フェーズ、ゲート、レビュー |
| リスク管理 | `tasks/risk_register.md` | リスクと緩和策 |
| 検証定義 | `tasks/validation_matrix.md` | 検証方法と exit criteria |

## Version Coexistence Policy (v1/v2)

| Version | Status | Default | Deprecation Condition |
|---------|--------|---------|----------------------|
| v1 | Stable | CLI default | Maintained indefinitely for backward compatibility |
| v2 | Stable | Available via `--result-version v2` | Will become default after 3+ months production validation |

### Migration Path
1. **Current**: v1 is default, v2 is opt-in (`--result-version v2`)
2. **Transition** (TBD): v2 becomes default, v1 available via `--result-version v1`
3. **Deprecation** (TBD): v1 marked deprecated, removal announced 6 months in advance

### Compatibility Rules
- v1 and v2 schemas are additive (v2 adds `cap.index_fingerprint` and `r[].cap_epoch`)
- All v1 outputs remain valid v2 inputs (forward compatibility for queries)
- v2 outputs can be downgraded to v1 by ignoring extra fields (backward compatibility for consumers)
- Capability handles (`doc_id`, `span_id`) format is identical between v1 and v2

### When to Use v2
- **Required**: When `cap verify` freshness checking is needed
- **Recommended**: For new integrations and production deployments
- **Optional**: For existing v1 consumers without capability verification needs

## 変更ルール

- 仕様変更時は、関連する schema と namespace を同一コミットで更新する
- 破壊的変更は新 version を追加し、旧 version の廃止時期を明記する
- 論文に使う数値は schema 準拠の実験記録からのみ取得する
- v1/v2 の併存期間中は、両方の schema を同一コミットで更新する
