# Docs Index

更新日: 2026-03-01

このディレクトリは、実装と研究の共通契約を管理する。

## 読む順序

### 実験者向けクイックスタート
1. `docs/research/experiment_findings_v2.md` - **最新実験結果の全知見**
2. `docs/research/roadmap.md` - 今後の改善計画
3. `docs/benchmarks/README.md` - 評価データセット
4. `docs/benchmarks/TASKSET_V2_EVALUATION.md` - v2.0評価詳細
5. `docs/operations/MAINTENANCE_GOVERNANCE.md` - 保守運用の標準統治

### 実装者向け
1. `docs/SSOT.md` - 真実情報源定義
2. `docs/NAMESPACE_RESERVATIONS.md` - 名前空間管理
3. `docs/schemas/*.schema.json` - データスキーマ
4. `docs/CI_CD.md` - CI/CD設定
5. `docs/WORKTREE.md` - ワークツリー管理
6. `docs/contracts/IMPLEMENTATION_CONTRACT.md` - 実装契約の運用ルール
7. `docs/schemas/README.md` - schema索引

### 研究者向け
1. `docs/papers/PROPOSED_METHOD.md` - 提案手法
2. `docs/papers/RELATED_WORK.md` - 関連研究
3. `docs/papers/PAPER_OUTLINE.md` - 論文構成ドラフト
4. `docs/benchmarks/TASKSET_DESIGN_V2.md` - タスク設計
5. `docs/benchmarks/DIFFICULTY_FRAMEWORK.md` - 難易度枠組み
6. `docs/contracts/*` - 実装契約
7. `docs/operations/*` - 運用ドキュメント

## 新規実験者向けガイド

```
[初見] → experiment_findings_v2.md (実験結果の全体像)
      → roadmap.md (現在の課題と改善計画)
      → TASKSET_V2_EVALUATION.md (詳細評価データ)
      → 必要に応じて benchmarks/*, papers/* を参照
```

## 実験実行導線

最短導線（taskset対象repo）:

```bash
make experiment
```

全サポート言語で実行:

```bash
make experiment-all
```

前処理チェックのみ:

```bash
make experiment-ready
```

詳細は `docs/PIPELINE_GUIDE.md` を参照。

## 運用マニュアル

- `docs/operations/README.md` - 運用ドキュメントの参照順序
- `docs/operations/MAINTENANCE_GOVERNANCE.md` - してよいこと/悪いこと、RACI、統治フロー
- `docs/operations/RUNBOOK.md` - 日次/週次運用、KPI更新手順、障害一次対応
- `docs/operations/SIER_SOUL.md` - 行動原則（属人化排除の基準）
- `docs/operations/SKILLS_OPERATING_MODEL.md` - skill階層運用モデル
- `docs/operations/ASSET_CLASSIFICATION.md` - 資産分類台帳（active/incubation/archive）

## Skills 管理

- `skills/README.md` - skill階層構造（L1/L2/L3）
- `skills/CATALOG.yaml` - skill台帳（owner/status/path）

## Scripts 管理

- `scripts/README.md` - scripts分類台帳（標準導線/補助導線）

## Template 配布

- `TEMPLATE/README.md` - テンプレートバンドル利用ガイド
- `TEMPLATE/PROJECT_STRUCTURE.md` - 新規プロジェクト用の推奨構成
- `TEMPLATE/contracts/*` - schema/policy/task template の集約

## ルート資料（履歴）

- `PROPOSED_METHOD_COMPLETE.md` - 提案内容の要約スナップショット
- `RIPGREP_INVESTIGATION_REPORT.md` - 過去インシデント調査ログ
- `outline.md`, `plan.md`, `give.md` - 初期検討・入力履歴

## 原則

- 実装コードより先に仕様を更新する
- スキーマ破壊変更は version を上げる
- `tasks/` は進行管理、`docs/` は仕様管理
- **実験結果は `docs/research/` に集約する**
