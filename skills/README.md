# Skills Architecture (Hierarchical)

更新日: 2026-02-28

## 目的

- skill を階層管理し、探索性と再利用性を上げる
- 属人化を避け、どの skill をどこで使うかを固定する

## レイヤー定義

- `l1_core`: 全作業で必須の品質・契約スキル
- `l2_ops`: 日次運用・障害対応・変更管理スキル
- `l3_program`: プロジェクト横断の運営・統治スキル

## ディレクトリ規約

```text
skills/
  l1_core/<domain>/<skill_name>/SKILL.md
  l2_ops/<domain>/<skill_name>/SKILL.md
  l3_program/<domain>/<skill_name>/SKILL.md
```

## 命名規約

- ディレクトリ名: `kebab-case`
- skill名: `scope-purpose`（例: `contract-harness`, `change-control`）
- 1 skill = 1 責務

## 互換方針

- 既存の flat skill（`skills/agentretrieve-*`）は互換維持のため残す
- 新規作成は階層配下を正とし、flat 追加は原則禁止

## 運用ルール

1. skill 追加時は `skills/CATALOG.yaml` を更新
2. skill 変更時は `tasks/todo.md` レビュー欄に記録
3. skill で参照するコマンドは再実行可能であること
4. skill の `owner` は `skills/CATALOG.yaml` の `owners` 定義IDを参照する
