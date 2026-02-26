# AgentRetrieve 実装移行 ToDo

更新日: 2026-02-25

## 0. 目的と成功条件

- [ ] エージェントの 1 タスクあたり Tool Call 数を現行比較で削減できることを証明する
- [ ] `stdout bytes` とレイテンシ（p50/p95/p99）を定量的に計測できる状態にする
- [ ] 非埋め込み（BM25 + Symbol + Meta）で再現可能な検索品質評価（MRR/nDCG/Recall）を確立する
- [ ] 実装着手前に仕様凍結ポイント（DSL/出力スキーマ/評価指標）を明確化する
- [ ] すべての実験結果をデータ化し、同一成果を別環境で再現できることを証明する
- [ ] 最終論文に必要な図表・統計・再現手順をアーティファクトとして蓄積する

## 1. 実装開始ゲート（Definition of Ready）

- [ ] DSL v1 の必須項目（`must/should/not/near/lang/ext/path_prefix/symbol/budget`）を確定
- [ ] 出力スキーマ v1（短キー、上限、cursor、truncation ルール）を確定
- [ ] `doc_id/span_id` + `digest/bounds` の capability 設計を確定
- [ ] MVP 範囲外（埋め込み、常駐サーバ高度化など）を明文化
- [ ] ベンチ用データセット仕様（固定コミット、タスク種別、正解形式）を確定
- [ ] Go/No-Go レビュー会の判定基準を合意
- [ ] 実験ログの最小メタデータ（seed / commit / env / hardware）を確定
- [ ] 論文用 KPI 定義（主指標・副指標・統計検定方針）を確定

## 2. 実行計画（チェックリスト）

### Phase 0: 計画基盤整備（このセッション）

- [x] `tasks/todo.md` を作成し、検証可能な計画へ分解
- [x] `tasks/lessons.md` を作成し、自己改善ループの記録先を準備
- [x] 意思決定ログ（`tasks/decisions.md`）を初期化
- [x] リスク登録簿（`tasks/risk_register.md`）を初期化
- [x] 検証マトリクス（`tasks/validation_matrix.md`）を初期化
- [x] 研究運用基盤（`tasks/research_foundation.md`）を初期化
- [x] CI/CD 基盤（`ci.yml` / `cd-release.yml` / contract validator）を初期化
- [x] 実装禁止事項ガイド（`tasks/implementation_donts.md`）を追加
- [x] 常駐エージェント運用基盤（`agentd` + task schema）を初期化
- [x] 全体実行計画を登録専用タスク（`tasks/project_execution_plan.v1.jsonl`）として追加

### Phase 1: 仕様凍結

- [ ] DSL v1 JSON Schema（入力）を作成
- [ ] 出力 Mini-JSON v1 Schema（出力）を作成
- [ ] 失敗系 contract（空結果、上限超過、cursor 続行、部分失敗）を定義
- [ ] ランキング要件（整数スコア 0-1000、同点時ルール）を定義
- [ ] API/CLI 契約テストケース一覧を作成
- [ ] 実験記録スキーマ（run record / dataset manifest）を定義

### Phase 2: MVP 実装

- [ ] Index Build/Update（Lexical）を実装
- [ ] Query 実行（must/should/not + budget 切り詰め）を実装
- [ ] Evidence 生成（抜粋 + `rng` + `next[]`）を実装
- [ ] capability 読み出し（`span_id` 指定で再取得）を実装
- [ ] 決定性テスト（同一入力で同一出力）を実装
- [ ] 実験ランナーが `artifacts/` に機械可読ログを書き出すよう実装

### Phase 3: 検証と比較

- [ ] micro benchmark（build/update/latency/RSS/index size）を実行
- [ ] retrieval benchmark（MRR/nDCG/Recall）を実行
- [ ] e2e benchmark（tool calls/stdout bytes/TTFC）を実行
- [ ] baseline 比較（`ripgrep` / `git grep` / 参考埋め込み系）を記録
- [ ] ablation（BM25 のみ / +symbol / +near / +prior）を記録
- [ ] 反復実験（n>=5）で分散と信頼区間を記録

### Phase 4: 研究データ基盤

- [ ] データセット manifest（入力ソース、固定 commit、ライセンス）を作成
- [ ] 実験 run registry（日時、実装 commit、設定、結果パス）を作成
- [ ] 指標集計パイプライン（raw -> table/figure）をスクリプト化
- [ ] 環境情報（OS/CPU/RAM/ツールバージョン）を自動収集
- [ ] 再実行手順（1 コマンド）を文書化

### Phase 5: 論文化

- [ ] 論文構成（Intro/Method/Experiment/Limitations）を固定
- [ ] 図表生成スクリプトを固定し、手作業編集を禁止
- [ ] 主張ごとに根拠実験 ID を紐付ける
- [ ] Artifact appendix（再現手順、データ所在、制約）を作成

### Phase 6: 実装移行完了条件（Definition of Done for Planning）

- [ ] 主要 ADR が `Accepted` になっている
- [ ] 主要リスクに owner と緩和策が設定されている
- [ ] 検証マトリクスに対して未定義項目がない
- [ ] 実装バックログが優先順位付きで 2 スプリント分存在する
- [ ] `Go` 判定がレビュー欄に記録されている
- [ ] 主要実験が別環境で再実行され、許容誤差内で再現している
- [ ] 論文ドラフトの全主張に対して実験証跡 ID が存在する

## 3. 依存関係と前提

- [ ] 評価対象リポジトリの固定コミット取得方法を確定
- [ ] 開発環境（Rust toolchain / parser / benchmark harness）を確定
- [ ] CI で実行する最小検証セット（契約テスト + 決定性テスト）を確定
- [ ] データ保存規約（命名、版管理、保持期間）を確定
- [ ] 環境非依存実行方式（コンテナ or lockfile 中心）を確定

## 4. レビュー

### 2026-02-25 計画基盤整備レビュー

- 実施内容: 計画を実装可能単位へ分解し、運用ドキュメント群を追加
- 検証: ファイル構成・リンク整合を確認（`tasks/` 配下新規作成）
- スタッフエンジニア観点: 目的・ゲート・検証・リスクの最小セットは成立
- 残課題: DSL/Schema の具体仕様は未凍結
- 判定: `No-Go`（仕様凍結完了後に再判定）

### 2026-02-25 研究基盤拡張レビュー

- 実施内容: データ蓄積、再現性、論文化フェーズを計画へ統合
- 検証: 研究運用文書の追加と `todo` 項目の整合を確認
- スタッフエンジニア観点: 開発計画と研究計画の接続が明確
- 残課題: 実験記録スキーマと再現許容誤差の数値定義
- 判定: `Conditional Go`（Phase 1 の仕様凍結完了が条件）

### 2026-02-25 docs 契約定義レビュー

- 実施内容: `docs/` に SSOT、名前空間予約、JSON Schema 群を追加
- 検証: docs と `tasks/templates` の version/prefix を整合
- スタッフエンジニア観点: 実装前に契約境界を固定できる状態へ改善
- 残課題: schema の実運用テスト（validator 導入）と CI 連携
- 判定: `Go`（仕様の初版として受理）

### 2026-02-25 CI/CD 基盤レビュー

- 実施内容: contract validation CI と release artifact CD を追加
- 検証: ローカルで validator 実行、JSON/schema 整合を確認
- スタッフエンジニア観点: 仕様変更時の品質ゲートと配布導線を確保
- 残課題: branch protection 設定と release versioning 規約の固定
- 判定: `Go`（基盤として受理）

### 2026-02-25 ワークツリー整備レビュー

- 実施内容: `.gitignore` 強化、`prepare_worktree.sh` 追加、`docs/WORKTREE.md` 追加
- 検証: スクリプト実行で `artifacts/` と `dist/` のローカル構造生成を確認
- スタッフエンジニア観点: 開発ファイルと生成物の境界が明確化
- 残課題: ブランチ運用ポリシー（複数 worktree 運用）の明文化
- 判定: `Go`（運用基盤として受理）

### 2026-02-25 評価入力取り込みレビュー

- 実施内容: `give.md` 由来のコーパス/タスク/ベースライン/制約を `docs/benchmarks/` に機械可読化
- 検証: CI validator を拡張し、JSON/JSONL と schema 準拠を確認
- スタッフエンジニア観点: 実験入力の再利用性と監査性が向上
- 残課題: 実リポジトリ clone 後の anchor 解決スクリプト実装
- 判定: `Go`（実験準備として受理）

### 2026-02-26 実装禁止事項レビュー

- 実施内容: `tasks/implementation_donts.md` を追加し、禁止事項をカテゴリ化
- 検証: 既存方針（SSOT/再現性/評価運用）との整合を確認
- スタッフエンジニア観点: 実装時の事故を事前に抑制できる
- 残課題: PR テンプレートへのチェック項目転記
- 判定: `Go`（運用規約として受理）

### 2026-02-26 実装契約強化・ハーネス厳格化レビュー

- 実施内容: contract policy 導入、validator 強化、CI matrix 化、strict harness ランナー追加
- 検証: `bash scripts/ci/run_contract_harness.sh` で schema/整合/不変条件が全通過
- スタッフエンジニア観点: 実装契約の強制力と検出力が大幅に向上
- 残課題: PR テンプレートと branch protection で運用強制を完成させる
- 判定: `Go`（実装ガードレールとして受理）

### 2026-02-26 skill 化レビュー

- 実施内容: `skills/agentretrieve-contract-harness/` を作成し、実行手順と失敗プレイブックを整備
- 検証: `quick_validate.py` でスキル妥当性を確認（valid）
- スタッフエンジニア観点: 今後の反復改善をスキル経由で標準化できる
- 残課題: 実運用での失敗事例を references に継続反映
- 判定: `Go`（運用可能）

### 2026-02-26 claw 常駐化適用レビュー

- 実施内容: `claw.md` を AgentRetrieve 向けに再設計し、`agentd` スプール実装を追加
- 検証: enqueue -> `agentd --once` の実行経路と strict harness の成功を確認
- スタッフエンジニア観点: 追加依存なしで継続実行・再試行・回収が可能
- 残課題: systemd ユニット化と監視メトリクスの追加
- 判定: `Go`（実運用可能）

### 2026-02-26 実行計画タスク登録レビュー

- 実施内容: プロジェクト最初から最後までを `project_execution_plan.v1.jsonl` へ登録（実行は未実施）
- 検証: JSONL schema 準拠、依存関係、順序連番、phase網羅を契約ハーネスで確認
- スタッフエンジニア観点: 実行前に全工程の可視化・監査が可能
- 残課題: 将来の自動実行連携時に task type マッピングを追加
- 判定: `Go`（登録台帳として受理）
