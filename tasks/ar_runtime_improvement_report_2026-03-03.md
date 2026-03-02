# AR Runtime 改善レポート（実運用観点）

作成日: 2026-03-03  
対象: `ar` launcher + AgentRetrieve CLI（`ar ix`, `ar q`）

## 1. 結論（所感）

`ar` は現時点で「分割インデックス前提のコード探索ツール」として実用的。  
一方で、リポジトリ全体を一括 `ix build` する運用は不安定で、改善余地が大きい。

## 2. 実測サマリ

### 2.1 インデックス作成（成功）

- `src`:
  - コマンド: `ar ix build --dir /mnt/d/dev/AgentRetrieve/src --output /tmp/ar_report_src.index.json`
  - 結果: `docs=16 terms=850 total_tokens=11418 status=ok`
  - 実測: `elapsed=0:00.40`, `maxrss_kb=7060`
- `docs`:
  - コマンド: `ar ix build --dir /mnt/d/dev/AgentRetrieve/docs --output /tmp/ar_report_docs.index.json`
  - 結果: `docs=38 terms=3348 total_tokens=10661 status=ok`
  - 実測: `elapsed=0:00.39`, `maxrss_kb=6940`
- `scripts`:
  - コマンド: `ar ix build --dir /mnt/d/dev/AgentRetrieve/scripts --output /tmp/ar_report_scripts.index.json`
  - 結果: `docs=31 terms=1503 total_tokens=40123 status=ok`
  - 実測: `elapsed=0:00.69`, `maxrss_kb=8804`

### 2.2 全体インデックス（課題）

- `ar ix build --dir /mnt/d/dev/AgentRetrieve --output ...` はこの環境で長時間化し、完了確認に至らず。
- 運用上は `src/docs/scripts` の分割インデックスに切り替えると安定。

### 2.3 検索精度（探索用途）

- `src` に対して `--must index --should build`、`--must query --should result`、`--must backend --should rust` は有効な上位候補を返した。
- 一方で語彙が不一致なクエリ（例: `launcher` を `src` に投げる）は空振り。

## 3. 実運用での改善提案（優先順）

## P0（最優先）

- `ix build` に除外オプションを追加する
  - 例: `--exclude target,.git,.venv,dist,artifacts,__pycache__`
  - 期待効果: 全体ビルド時のハング/長時間化を大幅に減らす
- `ix build` の進捗表示を追加する
  - 例: 処理済みファイル数、現在ディレクトリ、経過時間
  - 期待効果: 「遅い」のか「止まった」のか判別可能になる
- `ix build` のタイムアウト/フェイルファストを追加する
  - 例: `--max-seconds`, `--max-files`
  - 期待効果: CI/運用で無限待ちを防止

## P1（次点）

- クエリ補助（語彙揺れ対策）を追加する
  - 例: 同義語辞書（`cli` ↔ `launcher`、`wal` ↔ `update log`）
  - 期待効果: 空振り削減、初回ヒット率向上
- `ar q` の結果表示を改善する
  - 例: `--show-lines 5`, `--show-path-only`, `--pretty`
  - 期待効果: 人手探索の往復回数を減らす
- マルチインデックス検索を追加する
  - 例: `--index src.json --index docs.json --index scripts.json`
  - 期待効果: 分割運用と検索UXの両立

## P2（運用強化）

- 定番構成のプリセット化
  - 例: `ar ix build --preset repo-dev`（内部で include/exclude を適用）
- `docs/operations/CLI_DISTRIBUTION.md` に実運用テンプレートを明記
  - 例: 「大規模repoは分割インデックス推奨」
- 検索回帰ベンチを CI に追加
  - 空振り率、上位N hit率、build時間を継続監視

## 4. 推奨運用（現時点）

- 全体1本ではなく、領域ごとの分割インデックスを使う
  - `/tmp/agentretrieve_src.index.json`
  - `/tmp/agentretrieve_docs.index.json`
  - `/tmp/agentretrieve_scripts.index.json`
- 探索クエリは `must` を広めの語にし、`should` で意図を寄せる
  - 例: `--must backend --should rust`
- 0件時は語彙を切り替える
  - 例: `launcher` -> `cli`, `runtime`, `distribution`

## 5. 判定

- 判定: `Conditional Go`
- 条件:
  - 全体ビルド改善（P0）が入るまでは「分割インデックス前提」で運用すること
