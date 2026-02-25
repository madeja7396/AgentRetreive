# Lessons Log

更新日: 2026-02-25

## 運用ルール

- ユーザーから修正・指摘が入ったときは、同日中に本ファイルへ追記する
- 追記時は「再発防止ルール」を 1 行で明文化する
- 次セッション開始時に、今回タスクに関連する項目のみ先に読み返す

## 記録テンプレート

### YYYY-MM-DD: タイトル

- Trigger: 何が起きたか（事実）
- Root Cause: 根本原因
- Rule: 再発防止ルール（命令形）
- Check: 実施した予防チェック
- Status: `Open` / `Closed`

## エントリ

### 2026-02-25: 初期セットアップ

- Trigger: Lessons 管理ファイルが未作成だった
- Root Cause: 計画段階の運用基盤未整備
- Rule: 新規プロジェクト開始時は `tasks/todo.md` と同時に `tasks/lessons.md` を初期化する
- Check: `tasks/` 配下にログ運用ファイルを作成済み
- Status: Closed

### 2026-02-25: 研究要件の明示不足

- Trigger: ユーザーから「開発兼研究、データと実験ベース、環境非依存」を追加指示された
- Root Cause: 初回計画が実装中心で、研究運用（データ蓄積・論文化）を十分に明記していなかった
- Rule: 計画初版で「開発成果」と「研究成果」の両方の完了条件を明示する
- Check: `tasks/research_foundation.md` を追加し、`todo/risk/validation/decisions` に研究項目を反映
- Status: Closed
