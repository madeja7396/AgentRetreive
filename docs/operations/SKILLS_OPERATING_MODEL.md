# Skills Operating Model

更新日: 2026-02-28

## 目的

- skill の設計・配置・運用を標準化する
- スキルの乱立と責務重複を防ぐ
- 新規メンバーでも skill を選択できる状態を作る

## 階層モデル

- `l1_core`: 品質ゲート（必須）
- `l2_ops`: 運用実行・変更管理
- `l3_program`: 組織標準化・継続改善

詳細:
- `skills/README.md`
- `skills/CATALOG.yaml`

## スキル採用ルール

1. 新規 skill は階層配下に作成する
2. 1 skill 1責務を守る
3. `SKILL.md` に以下を必須記載:
   - いつ使うか
   - 実行手順
   - ガードレール
   - 参照先
4. 追加/変更時は `tasks/todo.md` にレビュー記録を残す
5. `skills/CATALOG.yaml` の `owners` に owner ID を登録し、各 skill の `owner` はその ID を参照する

## 品質チェック

- skill 参照先コマンドが実行可能
- 参照ドキュメントが存在
- 既存 skill と責務が重複しない
- owner ID が `owners` 定義と一致し、連絡先が有効

## 廃止ルール

- 非推奨 skill は `skills/CATALOG.yaml` の `status` を `deprecated` に変更
- 後継 skill を明示し、移行期間を設定
- 互換が必要な場合のみ flat path を残す
