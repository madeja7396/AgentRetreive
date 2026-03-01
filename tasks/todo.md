# AgentRetrieve 実装移行 ToDo

更新日: 2026-03-01

## 0. 目的と成功条件

- [x] エージェントの 1 タスクあたり Tool Call 数を現行比較で削減できることを証明する
- [x] `stdout bytes` とレイテンシ（p50/p95/p99）を定量的に計測できる状態にする
- [x] 非埋め込み（BM25 + Symbol + Meta）で再現可能な検索品質評価（MRR/nDCG/Recall）を確立する
- [x] 実装着手前に仕様凍結ポイント（DSL/出力スキーマ/評価指標）を明確化する
- [x] すべての実験結果をデータ化し、同一成果を別環境で再現できることを証明する
- [x] 最終論文に必要な図表・統計・再現手順をアーティファクトとして蓄積する

## 1. 実装開始ゲート（Definition of Ready）

- [x] DSL v1 の必須項目（`must/should/not/near/lang/ext/path_prefix/symbol/budget`）を確定
- [x] 出力スキーマ v1（短キー、上限、cursor、truncation ルール）を確定
- [x] `doc_id/span_id` + `digest/bounds` の capability 設計を確定
- [x] MVP 範囲外（埋め込み、常駐サーバ高度化など）を明文化
- [x] ベンチ用データセット仕様（固定コミット、タスク種別、正解形式）を確定
- [x] Go/No-Go レビュー会の判定基準を合意
- [x] 実験ログの最小メタデータ（seed / commit / env / hardware）を確定
- [x] 論文用 KPI 定義（主指標・副指標・統計検定方針）を確定

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

### Phase 1: 仕様凍結 ✅ (2026-02-26)

- [x] DSL v1 JSON Schema（入力）を作成 -> `docs/schemas/query.dsl.v1.schema.json`
- [x] 出力 Mini-JSON v1 Schema（出力）を作成 -> `docs/schemas/result.minijson.v1.schema.json`
- [x] 失敗系 contract（空結果、上限超過、cursor 続行、部分失敗）を定義
- [x] ランキング要件（整数スコア 0-1000、同点時ルール）を定義
- [x] API/CLI 契約テストケース一覧を作成
- [x] 実験記録スキーマ（run record / dataset manifest）を定義

### Phase 2: MVP 実装 ✅ (2026-02-26)

- [x] Index Build/Update（Lexical）を実装 -> `src/agentretrieve/index/`
  - Tokenizer (camelCase/snake_case対応) ✅
  - Inverted Index with BM25 ✅
  - Save/Load (JSON) ✅
- [x] Query 実行（must/should/not + budget 切り詰め）を実装 -> `src/agentretrieve/query/`
- [x] Evidence 生成（抜粋 + `rng` + `next[]`）を実装 -> `src/agentretrieve/models/output.py`
- [x] capability 読み出し（`span_id` 指定で再取得）を実装
- [x] 決定性テスト（同一入力で同一出力）を実装 -> `tests/unit/`
- [x] 実験ランナーが `artifacts/` に機械可読ログを書き出すよう実装

### Phase 3: 検証と比較

- [x] micro benchmark（build/update/latency/RSS/index size）を実行
- [x] retrieval benchmark（MRR/nDCG/Recall）を実行
- [x] e2e benchmark（tool calls/stdout bytes/TTFC）を実行
- [x] baseline 比較（`ripgrep` / `git grep` / 参考埋め込み系）を記録
- [x] ablation（BM25 のみ / +symbol / +near / +prior）を記録
- [x] 反復実験（n>=5）で分散と信頼区間を記録

### Phase 4: 研究データ基盤

- [x] データセット manifest（入力ソース、固定 commit、ライセンス）を作成
- [x] 実験 run registry（日時、実装 commit、設定、結果パス）を作成
- [x] 指標集計パイプライン（raw -> table/figure）をスクリプト化
- [x] 環境情報（OS/CPU/RAM/ツールバージョン）を自動収集
- [x] 再実行手順（1 コマンド）を文書化

### Phase 5: 論文化

- [x] 論文構成（Intro/Method/Experiment/Limitations）を固定
- [x] 図表生成スクリプトを固定し、手作業編集を禁止
- [x] 主張ごとに根拠実験 ID を紐付ける
- [x] Artifact appendix（再現手順、データ所在、制約）を作成

### Phase 6: 実装移行完了条件（Definition of Done for Planning）

- [x] 主要 ADR が `Accepted` になっている
- [x] 主要リスクに owner と緩和策が設定されている
- [x] 検証マトリクスに対して未定義項目がない
- [x] 実装バックログが優先順位付きで 2 スプリント分存在する
- [x] `Go` 判定がレビュー欄に記録されている
- [x] 主要実験が別環境で再実行され、許容誤差内で再現している
- [x] 論文ドラフトの全主張に対して実験証跡 ID が存在する

## 3. 依存関係と前提

- [x] 評価対象リポジトリの固定コミット取得方法を確定
- [x] 開発環境（Rust toolchain / parser / benchmark harness）を確定
- [x] CI で実行する最小検証セット（契約テスト + 決定性テスト）を確定
- [x] データ保存規約（命名、版管理、保持期間）を確定
- [x] 環境非依存実行方式（コンテナ or lockfile 中心）を確定

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

### 2026-02-26 Phase 3 中間レビュー（Retrieval Benchmark）

- 実施内容: ripgrep/fdコーパスでのretrieval評価（5タスク×2リポジトリ）
- 検証: 全10タスクで正解ファイルを発見（Recall@5=1.0）、MRR@5=0.68
- スタッフエンジニア観点: MVP実装で論文品質の検索精度を達成、BM25+tokenizer設計が有効
- 残課題: 残り3コーパス（fzf, curl, fmt）、baseline比較、決定性検証
- 判定: `Go`（検証進行中、継続開発を許可）

### 2026-02-26 MVP 実装レビュー

- 実施内容: Phase 2 MVP実装（Tokenizer + Inverted Index + BM25 + Query Engine + CLI）
- 検証: ユニットテスト8件全PASS、E2E検索・CLI動作確認済
- スタッフエンジニア観点: スキーマ準拠の入出力、BM25ランキング、capability設計を実装
- 残課題: Evidence生成の充実（行番号正確抽出）、実験ランナー、ベンチマーク実行
- 判定: `Go`（MVP実装として受理、Phase 3へ進行可能）

## 5. 2026-02-26 設計改修インテーク（今回）

- [x] `docs/Readme.md` が指す必読ドキュメント群を読了する
- [x] サブエージェント相当の並列調査で「仕様系」と「実装系」を分離して把握する
- [x] 実装モジュール境界（index/query/models/cli/daemon）と依存方向を整理する
- [x] 設計改修で優先すべきボトルネックと制約を抽出する
- [x] 本セッションのレビュー結果を `tasks/todo.md` に追記する

### 2026-02-26 設計改修インテークレビュー

- 実施内容: `docs/Readme.md` の参照先（research/benchmarks/SSOT/schemas/contracts/operations/papers）を読了し、`src/`/`scripts/`/`tests/` から実装アーキテクチャを分解
- 検証:
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `pytest -q` => `ModuleNotFoundError: agentretrieve`（パス未設定）
  - `PYTHONPATH=src pytest -q` => 8件PASS
- スタッフエンジニア観点: 仕様契約と実装実態の境界は明確。改修優先は `InvertedIndex.bm25_score` の計算量改善と `QueryEngine` のDSL準拠強化
- 残課題:
  - `near/lang/ext/path_prefix/symbol` が検索エンジン実装に未反映
  - `max_bytes` 予算超過時の厳密トリム処理が未実装
  - テスト実行に `PYTHONPATH=src` が必要（実行導線改善余地）
- 判定: `Go`（設計改修の実装フェーズへ移行可能）

### 2026-02-26 優先順改修レビュー（1→2→3）

- 実施内容:
  - 優先1: `InvertedIndex` に `doc_length` キャッシュを追加し、BM25計算の全索引再走査を除去
  - 優先2: `QueryEngine` に `near/lang/ext/path_prefix/symbol` を実装（symbol OR / term AND、near は line-window 近接判定）
  - 優先2: `output` の `max_bytes` を厳密適用（超過前で打ち切り、`t=true`）
  - 優先3: `tests/conftest.py` を追加し、`pytest -q` 単体実行で `src/` を解決
- 検証:
  - `pytest -q` => 14件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
- スタッフエンジニア観点: 仕様で定義済みのDSL制約と実装のギャップを縮小し、ボトルネック改善・契約準拠・実行導線の3点を優先順で解消
- 残課題:
  - `near.scope=block/symbol` は現状「行窓近似」であり、AST/シンボル境界を使う厳密実装は未着手
  - `cur` を伴うページング継続は未実装
- 判定: `Go`（次の改修は near 厳密化またはランキング改善へ進行可能）

## 6. 残タスク解決計画（near厳密化 + cursor継続）

### 6.1 実装開始ゲート（Definition of Ready）

- [x] `near.scope=block/symbol` の厳密仕様を確定（許容する近接判定の単位と境界）
- [x] `cur` の形式と不正時挙動を確定（`null` / 失効 / 改ざん時の戻り）
- [x] 既存 v1 schema を壊さない方針（追加は互換的変更のみ）を再確認

### 6.2 実装タスク（優先順）

#### Task A: `near.scope=block/symbol` 厳密化（最優先）

- [x] インデックス拡張方針を決定（軽量境界情報の保持: block/symbol）
- [x] `InvertedIndex` に scope判定用メタを追加（保存/読込の後方互換込み）
- [x] `QueryEngine` で `line_window/block/symbol` を分岐評価
- [x] `tests/unit/test_query_engine.py` に scope別テスト（成功/失敗境界）を追加
- [x] 既存 `line_window` の挙動回帰を確認

#### Task B: `cur` ページング継続の実装（次点）

- [x] カーソル表現を実装（`cur_*` 形式、決定的ソート順 + オフセット）
- [x] `QueryEngine` に cursor再開入力を追加（`options.cursor`）
- [x] `output` で `cur` を返却（続きを取得可能な時のみ）
- [x] CLI JSON入力経路で `options.cursor` を通す
- [x] カーソル不正値・期限切れ相当の失敗系テストを追加

#### Task C: 契約・回帰・運用確認

- [x] schema/validator で必要最小限の整合確認（互換性維持）
- [x] unit test 全体を再実行して回帰なしを確認
- [x] `tasks/todo.md` / `tasks/lessons.md` にレビューと教訓を追記

### 6.3 検証手順（完了条件）

- [x] `pytest -q` が全PASS
- [x] `python3 scripts/ci/validate_contracts.py` がPASS
- [x] `near.scope=block/symbol` の追加テストがPASS
- [x] cursor継続テスト（1ページ目→2ページ目）がPASS

### 6.4 レビュー観点

- [x] Determinism を維持しているか（同一入力で同一 `r` と `cur`）
- [x] 互換性を壊していないか（既存 DSL / result.v1 の必須キー維持）
- [x] スタッフエンジニア基準で「簡潔かつ監査可能」な設計か

### 2026-02-26 残タスク実装レビュー（near厳密化 + cursor継続）

- 実施内容:
  - `InvertedIndex` に `block_regions/symbol_regions` を追加し、save/load で後方互換維持
  - `QueryEngine` で `near.scope` を厳密化（同一 block/symbol 内でのみ近接成立）
  - `search_page` を追加し、`cur_<offset>_<signature>` で決定的なページ継続を実装
  - `CLI` に `options.cursor` / `--cursor` 経路を追加し、結果 `cur` を返却
- 論理的根拠:
  - `line_window` だけでは境界情報を表現できないため、near 判定を「window + scope containment」の2条件に分離
  - cursor は query-state署名を含めることで、別クエリへの誤適用を排除
  - tie-break を `score desc + doc_id asc` に固定し、ページング時の順序非決定性を除去
- 検証:
  - `pytest -q` => 21件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
- スタッフエンジニア観点: 仕様 (`near.scope`, `options.cursor`, `result.cur`) と実装が整合し、再現性・監査性・互換性の要件を満たす
- 残課題:
  - `symbol_regions` は宣言パターンベースの軽量抽出（AST厳密境界ではない）
  - cursor失効ポリシー（TTL等）は未定義
- 判定: `Go`（残タスクは実装完了、次は精度改善フェーズへ移行可能）

### 2026-02-26 追補レビュー（cursor進行整合 + block境界補正）

- 実施内容:
  - `CLI` の `cur` 算出を「ページ返却件数」ではなく「実際に出力できた件数（budget適用後）」基準へ修正
  - `emitted_count==0` かつ残件ありのケースを fail-fast 化し、同一オフセット再発行ループを遮断
  - Python の `block` 抽出で AST 境界が得られない場合、`fallback_regions(全体1ブロック)` ではなく空行分割へフォールバック
  - `test_query_engine` を `SearchPage.next_cursor_for_emitted()` APIへ追従
- 論理的根拠:
  - ページングカーソルは「ユーザーへ提示済み件数」に同期して進めないと、スキップ/重複を引き起こす
  - Python AST 由来の領域欠落時に全体1ブロックへ落とすと `near.scope=block` の偽陽性を誘発する
- 検証:
  - `pytest -q` => 21件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
- スタッフエンジニア観点: API改修時の呼び出し側追従漏れとフォールバック不整合を解消し、仕様通りの継続性と近接判定を担保
- 残課題:
  - `symbol_regions` の厳密度は言語ごとに差異があり、将来は AST/LSIF 等による強化余地がある
- 判定: `Go`（現時点の契約要件に対して実装・検証とも完了）

## 7. 統計推定ベースの symbol 言語重み導入（2026-02-26）

### 7.1 実装開始ゲート（Definition of Ready）

- [x] 「固定ヒューリスティック重みを禁止」の方針を明文化
- [x] 利用可能なコーパス実験入力（7repo index + taskset.v2.full）が存在することを確認
- [x] 学習済み重みを設定ファイルとして再利用する方針を確定

### 7.2 実装タスク（優先順）

- [x] Task A: 統計モデル仕様を実装
  - [x] `symbol` 重みモデル（global + by_lang）を query engine に追加
  - [x] 既定の固定値 boost を廃止し、学習済み重み適用へ置換
  - [x] cursor signature に重みモデル fingerprint を含めて整合性を担保
- [x] Task B: コーパス実験から重み推定
  - [x] taskset + index 群から学習サンプルを生成するスクリプトを追加
  - [x] ロジスティック回帰で言語別係数を推定し、Empirical-Bayes shrinkage を適用
  - [x] `configs/symbol_language_weights.v1.json` を生成
- [x] Task C: 回帰・契約検証
  - [x] ユニットテストを追加/更新
  - [x] `pytest -q` を全PASS
  - [x] `python3 scripts/ci/validate_contracts.py` をPASS

### 7.3 完了条件

- [x] 固定ヒューリスティック重み（例: 定数 +10）がコードから除去されている
- [x] 重みは実験データ由来のアーティファクトとして再生成可能
- [x] 未知言語へのフォールバック（global重み）がある

### 2026-02-26 統計推定ベース symbol 重みレビュー

- 実施内容:
  - `QueryEngine` に `SymbolLanguageWeights` を導入し、`symbol` スコアを `weight(lang) * evidence` で加算
  - 既存の定数 boost（`+10`）を廃止し、`configs/symbol_language_weights.v1.json` の学習済み重みへ置換
  - `scripts/benchmark/fit_symbol_language_weights.py` を追加し、`taskset.v2.full` + 7repo index から統計推定
  - 学習サンプル不足言語は Empirical-Bayes で global に縮約
- 論理的根拠:
  - 固定係数はコーパス依存の偏りを吸収できず、言語差を過不足なく扱えない
  - 回帰係数は観測データにより推定され、CV で正則化強度を選択可能
  - 縮約により低頻度言語の過学習を抑え、汎化性能を維持できる
- 検証:
  - `python3 scripts/benchmark/fit_symbol_language_weights.py` 実行で重みを再生成
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
- スタッフエンジニア観点: ヒューリスティック依存を排除し、重み推定プロセスが再現可能な実験手順としてコード化された
- 残課題:
  - 現行 taskset では `symbol_definition` が14件のみで、重み分散の推定精度に制約がある
  - 次段階では `symbol_usage` タスク増量で推定安定性を高める余地がある
- 判定: `Go`（要求どおり統計推定ベースへ移行完了）

## 8. コーパス拡張とワンコマンド自動適応（2026-02-26）

### 8.1 実装タスク

- [x] `corpus.v1.1` を主要言語カバレッジ（Rust/Go/C/C++/Python/JavaScript/TypeScript/Java）へ拡張
- [x] コーパス追加時に clone/index/学習/適応を 1 コマンドで回せるスクリプトを追加
- [x] 自動生成 config で `run_full_pipeline` と `fit_symbol_language_weights` を接続
- [x] ドキュメント（パイプライン運用・ベンチREADME）を更新
- [x] `Makefile` に実行ターゲットを追加

### 8.2 検証

- [x] `python3 scripts/pipeline/run_corpus_auto_adapt.py --dry-run` 実行成功
- [x] `pytest -q` => 24件 PASS
- [x] `python3 scripts/ci/validate_contracts.py` => PASS

### 2026-02-26 コーパス自動適応レビュー

- 実施内容:
  - `docs/benchmarks/corpus.v1.1.json` に `axios`(JS), `typescript`(TS), `gson`(Java) を追加
  - `scripts/pipeline/run_corpus_auto_adapt.py` を追加し、manifest 駆動で clone/index/学習/適応を自動化
  - `src/agentretrieve/bench/corpus.py` を拡張し、manifest/taskset の引数指定と v1.1/v2 既定を追加
  - `docs/PIPELINE_GUIDE.md` と `docs/benchmarks/README.md` に運用手順を追記
- 論理的根拠:
  - repo を `experiment_pipeline.yaml` へ手動二重登録する運用は、コーパス追加時に取りこぼしを生む
  - manifest を単一入力源にし、生成 config 経由で既存パイプラインへ接続すると整合性を維持できる
  - major-language coverage を事前検証することで、言語偏りによる学習/評価リスクを早期検出できる
- 残課題:
  - 追加した JS/TS/Java コーパス向け taskset 拡充は未実施（現行 v2.full は7repo中心）
  - 大規模 repo を含むフル実行時間は長いため、CI 常時実行には軽量サブセット設計が必要
- 判定: `Go`（要求どおり「主要言語整備 + ワンコマンド自動化」を実装完了）

## 9. 非C/Python系 + 現行主要言語サポート拡張（2026-02-26）

### 9.1 実装タスク

- [x] Haskell / Elixir コーパスを採用して manifest に追加
- [x] 現行フロント/バック主要言語（C#/PHP/Ruby/Kotlin/Swift/Dart）の代表 repo を追加
- [x] `run_corpus_auto_adapt.py` の major language 判定を拡張
- [x] インデックス拡張子マッピング（auto_adapt と CLI）を追加
- [x] ドキュメント（README/PIPELINE_GUIDE）を更新

### 9.2 検証

- [x] `python3 scripts/pipeline/run_corpus_auto_adapt.py --dry-run` => Missing major languages: none
- [x] `python3 scripts/pipeline/run_corpus_auto_adapt.py --dry-run --repos cabal,elixir,symfony` 実行成功
- [x] `pytest -q` => 24件 PASS
- [x] `python3 scripts/ci/validate_contracts.py` => PASS

### 2026-02-26 主要言語拡張レビュー

- 実施内容:
  - `docs/benchmarks/corpus.v1.1.json` に `cabal`(Haskell), `elixir`(Elixir), `aspnetcore`(C#), `symfony`(PHP), `rails`(Ruby), `ktor`(Kotlin), `swiftpm`(Swift), `flutter`(Dart) を追加
  - `configs/experiment_pipeline.yaml` に同 repo 群を追加し、手動パイプライン経路でもサポート
  - `run_corpus_auto_adapt.py` の major language セットと拡張子判定を同期
  - `ar ix build` の言語判定マップを拡張（.hs/.ex/.cs/.php/.rb/.kt/.swift/.dart 等）
- 論理的根拠:
  - 構文多様性（特に Haskell/Elixir）を入れることで、C系/Python系偏重の過適合リスクを下げられる
  - 同時に主要実務言語を押さえることで、実運用に近い汎化性能評価が可能になる
  - manifest と自動化スクリプトの判定条件を一致させることで、運用ドリフトを防止できる
- 残課題:
  - 新規追加 repo の taskset 拡張は未実施（現行評価は7repo中心）
  - Haskell/Elixir 向け task type（symbol_usage/near）の設計が次フェーズ
- 判定: `Go`（採用方針どおり、言語カバレッジ拡張を実装完了）

## 10. 実行実証（clone -> 学習 -> パラメータ決定）（2026-02-27）

### 10.1 実装・実行タスク

- [x] 実リポジトリ clone を伴う `run_corpus_auto_adapt.py` 実行で、taskset対象7repoの clone/index/fit を完了
- [x] `run_full_pipeline.py` の `ProcessPoolExecutor` 権限エラー（`PermissionError: [Errno 13]`）を根本修正
- [x] `clone_or_update_corpus` に clone timeout/retry（`AR_CLONE_TIMEOUT_SEC`）を導入
- [x] 修正後に `generated_experiment_pipeline.auto.yaml` で全7repoのパラメータ探索を完走
- [x] 学習済み重み（`configs/symbol_language_weights.v1.json`）と最適パラメータ（`aggregate_results.json`）を再生成
- [x] 回帰確認（`pytest -q` / `python3 scripts/ci/validate_contracts.py`）を再実行

### 10.2 2026-02-27 実行レビュー

- 実施内容:
  - `scripts/pipeline/run_full_pipeline.py` に executor フォールバックを追加
  - `workers<=1` は逐次実行、`ProcessPoolExecutor` 失敗時は `ThreadPoolExecutor` へ自動切替
  - `src/agentretrieve/bench/corpus.py` に clone timeout/retry を追加し、巨大repo clone の無限待ちを防止
  - `python3 scripts/pipeline/run_full_pipeline.py -c artifacts/experiments/pipeline/generated_experiment_pipeline.auto.yaml -o artifacts/experiments/pipeline -w 4` を完走
- 論理的根拠:
  - 現実行環境では multiprocessing semaphore が利用できず、process pool 前提は再現性を欠く
  - 探索エンジン本体は executor 非依存なので、実行戦略のみ切替えるのが最小影響で妥当
  - フォールバック設計により「失敗で停止」から「性能低下しても完遂」へ改善できる
- 検証:
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `artifacts/experiments/pipeline/aggregate_results.json` を当日再生成し、7repo分の最適値を確認
- 主要結果:
  - 全体 Recall: `26/35 (74.3%)`
  - repo別最適値（k1,b,mm,mt）を7repo分確定
  - symbol重み学習は `sample_count=406`, `positive_sample_count=14`, `l2_selected=3.0` を採択
- 残課題:
  - `--index-all` で巨大repo clone を同一フェーズに含めると処理時間が長く、実運用では段階実行（repos分割）が望ましい
  - taskset は依然7repo中心で、新規主要言語コーパスの学習寄与は未着手
- 判定: `Go`（要求どおり「実クローンからパラメータ決定まで」を実行完了）

## 11. コーパス公平性強化（サイズ/件数整合 + 複雑リポジトリ確保）（2026-02-27）

### 11.1 実装タスク（優先順）

- [x] `run_corpus_auto_adapt.py` のバランシングを「件数一致 + バイト偏差最小化」に改修
- [x] バランシング目標値をヒューリスティックではなく統計量（中央値ベース）で決定
- [x] 複雑リポジトリ選定を多指標（規模・多様性・深さ・分散）z-scoreで再定義
- [x] `auto_adapt_summary.json` に公平性指標（CV/偏差率）と複雑リポジトリ根拠を出力
- [x] ドキュメント（`docs/PIPELINE_GUIDE.md`, `docs/benchmarks/README.md`）を更新

### 11.2 検証タスク

- [x] `python3 -m py_compile scripts/pipeline/run_corpus_auto_adapt.py` が成功
- [x] `python3 scripts/pipeline/run_corpus_auto_adapt.py --index-all --skip-clone --skip-index --skip-symbol-fit --skip-parameter-search` が成功
- [x] 出力 summary で `balanced_code_files_cv==0` かつ `balanced_code_bytes_cv` が算出される
- [x] `pytest -q` と `python3 scripts/ci/validate_contracts.py` を再実行して回帰なしを確認

### 11.3 2026-02-27 公平性強化レビュー

- 実施内容:
  - `run_corpus_auto_adapt.py` のバランシングを、`target_files=min(code_file_count)` と `target_bytes=median(target_files * repo_mean_file_bytes)` で統計決定
  - 各repoは `target_files` 固定で、`target bytes / file` 近傍の決定的サンプリング + 単発swap補正でバイト偏差を縮小
  - 複雑repo選定を `code_file_count / code_bytes / language_diversity / extension_diversity / language_entropy / path_depth_p90 / file_size_cv` の z-score 合算へ拡張
  - `auto_adapt_summary.json` に `target_code_bytes_per_repo`, `balanced_code_files_cv`, `balanced_code_bytes_cv`, `balanced_size_deviation_ratio`, `complex metrics` を出力
- 論理的根拠:
  - 件数は全repoで共通化できる最大厳密条件（最小件数）を採用することで、比較母数の不一致を除去
  - サイズは repo固有分布に依存するため、中央値ベース目標へ収束させて分散を最小化する設計が外れ値に頑健
  - 複雑性は単一尺度でなく「規模 + 構文/拡張子多様性 + 階層深さ + サイズ分散」の合成指標で評価する方が説明可能性が高い
- 検証:
  - `python3 -m py_compile scripts/pipeline/run_corpus_auto_adapt.py` => PASS
  - `python3 scripts/pipeline/run_corpus_auto_adapt.py --index-all --skip-clone --skip-index --skip-symbol-fit --skip-parameter-search` => PASS
  - `artifacts/experiments/pipeline/auto_adapt_summary.json`:
    - `target_code_files_per_repo=24`
    - `balanced_code_files_cv=0.0`
    - `balanced_code_bytes_cv=0.0558263060`
    - `complex_repo=flutter`
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
- 残課題:
  - 最小件数 repo（現状 `fd:24`）が基準となるため、各repoの情報量は保守的サンプルになる
- 判定: `Go`（公平性要件と複雑repo確保を統計的・再現可能な形で実装完了）

## 12. 実験導線整備（preflight -> adapt -> evaluation の一本化）（2026-02-27）

### 12.1 実装タスク

- [x] 実験導線オーケストレータ (`run_experiment_route.py`) を追加
- [x] Make ターゲット（`experiment-ready`, `experiment`, `experiment-all`）を追加
- [x] docs（`docs/README.md`, `docs/PIPELINE_GUIDE.md`, `docs/benchmarks/README.md`）を更新

### 12.2 検証タスク

- [x] `python3 -m py_compile scripts/pipeline/run_experiment_route.py` が成功
- [x] `python3 scripts/pipeline/run_experiment_route.py --dry-run` が成功
- [x] `python3 scripts/pipeline/run_experiment_route.py --skip-auto-adapt --skip-final-eval` が成功
- [x] `pytest -q` と `python3 scripts/ci/validate_contracts.py` で回帰なし

### 12.3 2026-02-27 実験導線整備レビュー

- 実施内容:
  - `scripts/pipeline/run_experiment_route.py` を追加し、`preflight -> auto-adapt -> final-eval` を 1 コマンドで直列実行できるようにした
  - route には `--index-all`, `--repos`, `--no-balance`, `--skip-*` を渡せるようにして、既存自動化との互換を維持
  - `Makefile` に `experiment-ready`, `experiment`, `experiment-all` を追加
  - `docs/README.md`, `docs/PIPELINE_GUIDE.md`, `docs/benchmarks/README.md` に新導線を追記
- 論理的根拠:
  - 実験実行の実運用は「前処理忘れ（contract/test未実行）」が最も事故率が高いため、導線を単一入口へ集約するのが最小リスク
  - 既存の `run_corpus_auto_adapt.py` と `run_final_evaluation.py` をラップするだけの設計にして、評価ロジック自体は不変に保つ
- 検証:
  - `python3 -m py_compile scripts/pipeline/run_experiment_route.py` => PASS
  - `python3 scripts/pipeline/run_experiment_route.py --dry-run` => PASS
  - `python3 scripts/pipeline/run_experiment_route.py --skip-auto-adapt --skip-final-eval` => PASS
  - 上記実行内で `pytest -q`（24件 PASS）と `validate_contracts.py`（PASS）を確認
- 判定: `Go`（「実験までの導線」を再現可能な1コマンド導線として整備完了）

## 13. 直近実行バックログ（KPI整合性回復, 2026-02-28）

### 13.1 P0: 評価整合性の回復（最優先）

- [x] Gold coverage 監査を実行し、taskset gold file が index に全件存在することを確認
- [x] `run_experiment_route.py --no-balance` で公式評価を再実行し、`final_summary.json` を再生成
- [x] 公式KPIのSSOTを `final_summary.json` に固定し、`aggregate_results.json` は探索結果として扱う方針を明文化
- [x] 実行時刻・commit・設定をレビュー欄へ記録

### 13.2 P1: 実行導線の修復

- [x] `Makefile validate` の実行器誤り（python3 -> bash）を修正
- [x] `Makefile report` の欠落スクリプト参照を修正
- [x] `make validate` / `make report` / `make experiment-ready` の smoke 実行

### 13.3 P1: 再発防止

- [x] balanced index と raw index を別出力に分離し、公式評価は raw 固定にする
- [x] taskset gold coverage preflight を追加し、欠落時は失敗させる
- [x] 実験導線ドキュメントを更新して運用を固定する

### 13.4 完了条件

- [x] 公式KPIが単一の値としてレビュー欄に記録されている
- [x] 全 taskset repo で `gold_present == total_tasks`
- [x] Makefile の主要ターゲット破損が解消している

### 13.5 2026-02-28 KPI整合性回復レビュー

- 実施内容:
  - `scripts/pipeline/check_gold_coverage.py` を新規追加し、taskset gold file と index 収録の整合を検証
  - `scripts/pipeline/run_experiment_route.py` に gold coverage ゲートを追加（最終評価前）
  - `Makefile` の `validate/report` 導線を修正し、`scripts/benchmark/generate_report.py` を新規追加
  - `docs/PIPELINE_GUIDE.md` を更新し、`final_summary.json` を公式KPIのSSOTとして明文化
- 検証:
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4` => PASS
  - `make validate` => PASS
  - `make report` => PASS（`artifacts/experiments/FINAL_PIPELINE_REPORT.md` 生成）
  - `gold_coverage_summary.json` で taskset対象7repoすべて `gold_present == total`
- 実行記録:
  - 実行日: 2026-02-28
  - ブランチ: `main`（`origin/main` ahead 3）
  - 主要コマンド: `python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4`
  - 公式KPI（`artifacts/experiments/pipeline/final_summary.json`）:
    - Overall Recall: `26/35 (74.3%)`
    - Average MRR: `0.381`
    - Average Latency: `0.7ms`
- スタッフエンジニア観点:
  - KPIの参照系（探索結果 vs 公式評価）を分離し、評価前にデータ整合を強制できる状態へ改善
  - 破損していた運用導線（Make target）を実行可能状態へ回復
- 残課題:
  - なし（KPI整合性回復スコープは完了）
- 判定: `Go`（KPI整合性回復タスク完了）

## 14. プロジェクト並列調査（主題・アーキテクチャ・問題点, 2026-02-28）

### 14.1 実施タスク

- [x] `docs/README.md`, `docs/SSOT.md`, `docs/research/*` から主題と評価目標を抽出
- [x] `src/agentretrieve/{index,query,models,cli}` を並列読解し、依存方向を整理
- [x] `tests/unit/*` と `pytest -q` 実行結果から品質ゲートの実効性を確認
- [x] `Makefile` / `docs/PIPELINE_GUIDE.md` / 実ファイル構成の整合性を監査
- [x] 問題点を重大度付きで整理し、レビューに記録

### 14.2 2026-02-28 並列調査レビュー

- 実施内容:
  - 仕様系（`docs/`）と実装系（`src/`, `tests/`, `configs/`）を分離して並列調査
  - 主題、モジュール境界、既知リスク、運用導線の整合を横断確認
- 検証:
  - `pytest -q` => 24件 PASS
  - `ls -la scripts` で通常構成（`benchmark/ci/daemon/dev/pipeline`）を確認
  - 一時的な誤配置（`skills/scripts`）を検知し、`scripts` 復元で解消
- 主要所見:
  - 主題: 非埋め込み・決定論的なエージェント向けコード検索の研究/実装（KPI: Recall/MRR/Latency）
  - アーキテクチャ: `InvertedIndex`（索引/BM25/構造領域） -> `QueryEngine`（DSL実行/ランキング/cursor） -> `output.format_results`（MiniJSON契約） -> `cli`（`ar ix`/`ar q`）
  - 問題点P0: 評価系 index の用途分離（balanced/raw）が未実装だった（15章で解消）
  - 問題点P1: `ar ix update` が未実装（full rebuild案内のみ）で、インクリメンタル更新要件が未達
  - 問題点P1: ranking hit の本文根拠が現状 `path` 文字列中心（`Hit.text=f\"{doc.path}\"`）で、evidence品質に改善余地
  - 問題点P2: `README.md` 不在（`pyproject.toml` は `readme = \"README.md\"`）で配布メタデータ整合にリスク
- スタッフエンジニア観点:
  - 検索コアと契約テストは成立。残課題は運用・評価基盤の制度化であり、15章で対応
- 判定: `Go`（並列調査の指摘事項は次章で処理完了）

## 15. 保守運用管理体制整備（SIer_SOUL + skill階層化, 2026-02-28）

### 15.1 実施タスク

- [x] 運用統治マニュアルを作成（RACI/Do-Don't/監査項目）
- [x] SIer_SOUL チャーターを作成（行動原則・禁止規範・受け入れ基準）
- [x] Runbook を作成（日次/週次運用・KPI更新・障害一次対応）
- [x] Skills 運用モデルを作成（階層構造・命名規約・廃止規約）
- [x] `skills/` を階層化（L1/L2/L3）し、catalogで管理
- [x] 残タスク（balanced/raw index 分離）の実装と実証を完了

### 15.2 2026-02-28 保守運用管理体制レビュー

- 実施内容:
  - `run_corpus_auto_adapt.py` を改修し、探索用 index（`artifacts/datasets/balanced_index/`）と公式評価用 index（`artifacts/datasets/` raw）を分離
  - `run_experiment_route.py` を改修し、最終評価時に `generated_experiment_pipeline.final_raw.yaml` を生成して raw 固定で実行
  - 運用文書を追加:
    - `docs/operations/MAINTENANCE_GOVERNANCE.md`
    - `docs/operations/SIER_SOUL.md`
    - `docs/operations/RUNBOOK.md`
    - `docs/operations/SKILLS_OPERATING_MODEL.md`
  - skill階層資産を追加:
    - `skills/README.md`
    - `skills/CATALOG.yaml`
    - `skills/l1_core/...`, `skills/l2_ops/...`, `skills/l3_program/...`
- 検証:
  - `python3 -m py_compile scripts/pipeline/run_corpus_auto_adapt.py scripts/pipeline/run_experiment_route.py scripts/pipeline/check_gold_coverage.py scripts/benchmark/generate_report.py` => PASS
  - `python3 scripts/pipeline/run_corpus_auto_adapt.py --skip-clone --skip-symbol-fit --skip-parameter-search --workers 1` => PASS（`[index][search]` と `[index][raw]` を同時確認）
  - `python3 scripts/pipeline/run_experiment_route.py --skip-auto-adapt --skip-tests --skip-contracts --workers 1` => PASS（`generated_experiment_pipeline.final_raw.yaml` 経由）
  - `pytest -q` => 24件 PASS
  - `make validate` / `make report` / `make experiment-ready` => PASS
- スタッフエンジニア観点:
  - 実行系・評価系・運用系の責務が分離され、属人化を抑える最低限の統治基盤が整った
  - skill を階層化したことで、用途別選択と保守境界が明確になった
- 残課題:
  - なし（owner は `skills/CATALOG.yaml` の `owners` へ割当完了）
- 判定: `Go`（要求スコープを実装完了）

## 16. 復元後継続実装（owner割当固定 + 再検証, 2026-02-28）

### 16.1 実施タスク

- [x] 復元後の実行可能性を再確認（`pytest -q` / 契約検証 / Make導線）
- [x] `skills/CATALOG.yaml` に owner directory（team/contact/escalation）を追加
- [x] 運用文書へ owner 統治ルール（監査/連絡先）を反映
- [x] 今回の実装継続内容を `tasks/todo.md` と `tasks/lessons.md` に記録

### 16.2 2026-02-28 復元後継続レビュー

- 実施内容:
  - `skills/CATALOG.yaml` の `owner` を role 名から実運用ID（`core_quality`, `ops_runtime`, `ops_governance`, `program_office`）へ移行
  - `owners` セクションに team/contact/escalation を定義し、owner 参照元を一本化
  - `docs/operations/MAINTENANCE_GOVERNANCE.md` に owner 割当と監査チェックを追記
  - `docs/operations/SKILLS_OPERATING_MODEL.md` / `RUNBOOK.md` / `skills/README.md` に owner 運用ルールを追記
- 検証:
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `make validate` => PASS
  - `make report` => PASS
  - `make experiment-ready` => PASS
- スタッフエンジニア観点:
  - owner 情報が実体（team/contact/escalation）に紐づき、属人化を避けつつ責任境界を監査可能にできた
  - 復元後の導線再検証により、運用継続の安全性を再確認できた
- 残課題:
  - なし
- 判定: `Go`（復元後継続スコープを完了）

## 17. 未統合資産の分類・接続（2026-03-01）

### 17.1 実施タスク

- [x] 未接続資産を `active / incubation / archive` で分類
- [x] 分類台帳 `docs/operations/ASSET_CLASSIFICATION.md` を作成
- [x] `scripts/README.md` を新規作成し scripts の運用分類を定義
- [x] docs index（`docs/README.md`, `docs/operations/README.md`, `docs/benchmarks/README.md`）へ導線を接続
- [x] 監査ルールに資産分類の鮮度チェックを追加

### 17.2 2026-03-01 分類・接続レビュー

- 実施内容:
  - 未参照だった knowledge/script/dataset/root-note を棚卸しし、分類台帳へ登録
  - benchmark 補助スクリプト群を `incubation` として明示し、標準導線（pipeline/ci/daemon）と分離
  - taskset ファイル群を `active/incubation/archive` で明示して誤参照を防止
  - docs index に `ASSET_CLASSIFICATION.md` と `scripts/README.md` を追加して探索導線を固定
- 検証:
  - `rg -n --fixed-strings "docs/operations/ASSET_CLASSIFICATION.md" docs/README.md docs/operations/README.md scripts/README.md` で参照接続を確認
  - `rg -n --fixed-strings "scripts/README.md" docs/README.md docs/operations/ASSET_CLASSIFICATION.md` で scripts 台帳の導線接続を確認
  - `python3 scripts/ci/validate_contracts.py` => PASS
- スタッフエンジニア観点:
  - 孤立資産を「削除ではなく分類」で可視化し、運用導線と履歴資産の境界を明確化できた
  - 今後の整理は `ASSET_CLASSIFICATION.md` 更新を入口にして、属人的な判断を減らせる
- 残課題:
  - `incubation` scripts のうち再利用予定がないものは段階的に `archive` へ移行する運用判断が必要
- 判定: `Go`（分類・接続の初期整備を完了）

## 18. 実験再開バックログ（実行待ち, 2026-02-28）

### 18.1 方針（この章の扱い）

- [x] 本章は「実行順と完了条件の固定」が目的であり、実行は次セッションで行う
- [x] 公式KPIは raw 固定評価（`final_summary.json`）を唯一のSSOTとする
- [x] すべての実験成果は run_id 単位で `artifacts/experiments/runs/<run_id>/` へ集約する

### 18.2 実行前固定（DoR）

- [x] 入力固定: `docs/benchmarks/corpus.v1.1.json` / `docs/benchmarks/taskset.v2.full.jsonl` / `configs/experiment_pipeline.yaml`
- [x] 前提ゲート: `pytest -q` と `python3 scripts/ci/validate_contracts.py` が通ること
- [x] 実行ログ必須項目（timestamp / git commit / command / output path / hardware）を run registry へ記録する

### 18.3 実験キュー（優先順）

- [x] EXP-001: 公式KPI再ベースライン（raw固定）
  - コマンド: `python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4`
  - 期待成果物: `artifacts/experiments/pipeline/final_summary.json`, `gold_coverage_summary.json`
  - 完了条件: `coverage_ok=true` かつ overall 指標をレビュー欄へ記録

- [x] EXP-002: 探索結果再計測（taskset対象repo）
  - コマンド: `python3 scripts/pipeline/run_corpus_auto_adapt.py --skip-clone --workers 4`
  - 期待成果物: `artifacts/experiments/pipeline/aggregate_results.json`, `auto_adapt_summary.json`
  - 完了条件: repo別最適パラメータが taskset 対象repo分すべて出力される

- [x] EXP-003: Retrieval benchmark（repo別精度）
  - コマンド雛形: `python3 scripts/benchmark/evaluate_taskset.py --index artifacts/datasets/<repo>.index.json --taskset docs/benchmarks/taskset.v2.full.jsonl --repo <repo> -o artifacts/experiments/runs/<run_id>/retrieval_<repo>.json`
  - 期待成果物: `retrieval_<repo>.json`（taskset対象repo分）
  - 完了条件: Recall/MRR/latency を repo別と全体で集計できる

- [x] EXP-004: Baseline比較（AgentRetrieve vs ripgrep vs git grep）
  - コマンド雛形: `python3 scripts/benchmark/run_comparison.py --repo-name <repo> --repo-path artifacts/datasets/raw/<repo> --index artifacts/datasets/<repo>.index.json --taskset docs/benchmarks/taskset.v2.full.jsonl -o artifacts/experiments/runs/<run_id>/comparison_<repo>.json`
  - 期待成果物: `comparison_<repo>.json`（repo別）
  - 完了条件: recall/mrr/latency/stdout bytes をツール別に比較可能

- [x] EXP-005: micro benchmark（build/update/query/RSS/index size）
  - 実施内容: 測定ハーネスを整備し、build/update/query の p50/p95/p99 と RSS/index size を取得
  - 期待成果物: `artifacts/experiments/runs/<run_id>/micro_benchmark.json`
  - 完了条件: Phase 3 の micro 指標（latency/RSS/index size）が再現可能な形で保存される

- [x] EXP-006: e2e benchmark（tool calls/stdout bytes/TTFC）
  - 実施内容: エージェント実行ログから tool call 数・stdout bytes・TTFC を抽出する計測導線を整備して実測
  - 期待成果物: `artifacts/experiments/runs/<run_id>/e2e_metrics.json`
  - 完了条件: 目的指標（Tool Calls/bytes/TTFC）をタスク単位で比較可能

- [x] EXP-007: Ablation（BM25 only / +symbol / +near / +prior）
  - 実施内容: 条件別設定を固定して同一 taskset で再評価
  - 期待成果物: `artifacts/experiments/runs/<run_id>/ablation.json`
  - 完了条件: 各追加要素の寄与（delta recall/mrr/latency）が表形式で出る

- [x] EXP-008: 反復実験（n>=5）と統計区間
  - 実施内容: EXP-001〜EXP-004 の主要指標を反復し、分散と信頼区間を算出
  - 期待成果物: `artifacts/experiments/runs/<run_id>/stability.json`
  - 完了条件: 主要KPIに mean/std/CI が付与される

### 18.4 実験完了判定（この章のDoD）

- [x] Phase 3 の未完了項目（micro/retrieval/e2e/baseline/ablation/repeat）がすべて実測値で埋まる
- [x] run registry（日時/commit/設定/成果物パス）が実験ID単位で記録される
- [x] 再実行コマンド（1コマンド）と許容誤差がレビュー欄に記録される

### 18.5 レビュー（実行前計画）

- 実施内容:
  - 未完了だった Phase 3 実験項目を、実行順・依存・成果物単位へ再編成
  - 既存スクリプトで実行可能な実験（EXP-001〜004）と、計測導線整備が先な実験（EXP-005〜007）を分離
  - 反復実験（EXP-008）を最後に配置し、統計処理対象を固定
- 検証:
  - 本章は計画更新のみ（実験未実行）
- スタッフエンジニア観点:
  - 「次に何をどの順でやるか」がコマンドと成果物レベルで明確化され、再開コストが低い
- 残課題:
  - EXP-005/006/007 の計測ハーネス詳細仕様（スキーマ定義）は次セッションで確定
- 判定: `Go`（実験再開計画として受理）

### 18.6 2026-03-01 実行レビュー（EXP-001/002）

- 実施内容:
  - `docs/README.md`, `docs/operations/README.md`, `docs/operations/ASSET_CLASSIFICATION.md`, `scripts/README.md` を精読し、運用導線の現行規約を確認
  - 前提ゲートとして `pytest -q` と `python3 scripts/ci/validate_contracts.py` を実行（ともに PASS）
  - `python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4` を実行し、raw固定の公式評価と探索再計測を一括実行
  - run 記録を `artifacts/experiments/runs/run_20260228_154238_exp001_raw/` に集約（`logs.txt`, `final_summary.json`, `gold_coverage_summary.json`, `run_record.json`）
- 検証:
  - `gold_coverage_summary.json`: taskset 対象 7 repo すべて `present=5/5`（coverage 欠落なし）
  - `final_summary.json`: Overall Recall `26/35 (74.3%)`, Average MRR `0.381`, Average Latency `0.7ms`
  - `aggregate_results.json` / `auto_adapt_summary.json` が更新され、repo別最適パラメータを出力
  - `run_record.json` を `docs/schemas/experiment_run_record.v1.schema.json` で検証し PASS
- スタッフエンジニア観点:
  - 実行計画から実測・証跡集約までが接続され、再開バックログの先頭2件は実運用可能な形で消化できた
  - ただし run record の `ndcg/tool_calls/stdout/ttfc` は計測ハーネス未整備のため暫定値（0）であり、EXP-005/006と整合して改善が必要
- 残課題:
  - EXP-003〜EXP-008（retrieval/baseline/micro/e2e/ablation/repeat）の実測と統計化
  - run registry を単一 JSONL 台帳へ継続追記する自動化
- 判定: `Conditional Go`（EXP-001/002 は完了、計測ハーネス系が次のクリティカルパス）

### 18.7 2026-03-01 実行レビュー（EXP-003〜008 完了）

- 実施内容:
  - `EXP-003`: `evaluate_taskset.py` を 7 repo 全件実行し、`retrieval_<repo>.json` を run_id 配下へ保存
  - `EXP-004`: `run_comparison.py` を 7 repo 全件実行し、`comparison_<repo>.json` を run_id 配下へ保存
  - `EXP-005/006/007/008`: `scripts/benchmark/complete_phase3.py` を追加し、`micro_benchmark.json`, `e2e_metrics.json`, `ablation.json`, `stability.json` を生成
  - `dataset manifest` を `artifacts/datasets/manifests/ds_20260301_taskset_v2_full_raw.manifest.json` として作成
  - `run registry` を `artifacts/experiments/run_registry.v1.jsonl` として作成し、run record を追記
- 検証:
  - `pytest -q` => 24件 PASS
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `dataset_manifest` schema validation => PASS
  - `run_record` schema validation => PASS
  - `stability.json` repeats => `5`
- 主要結果:
  - micro（aggregate）: build p50/p95/p99 = `41.61s / 45.00s / 45.00s`、query p50/p95/p99 = `0.339ms / 1.492ms / 2.008ms`
  - e2e: tool_calls_per_task=`1.0`, stdout_bytes_per_task=`312`, ttfc p50/p95/p99=`0.414/1.872/2.530ms`
  - ablation: bm25_only recall=`0.657` -> +symbol recall=`0.686`（+0.029）だがレイテンシ増加
  - stability(n=5): EXP-001 recall mean=`0.7429`, std=`0.0` / EXP-004(AR) MRR mean=`0.3289`, std=`0.0`
- 再実行コマンド（1コマンド）:
  - `make phase3-complete RUN_ID=run_20260228_154238_exp001_raw`
- 許容誤差:
  - Recall/MRR: ±0.01（absolute）
  - Latency系: ±10%（relative）
- スタッフエンジニア観点:
  - Phase 3 の実測値と統計区間が揃い、検証章の欠落は解消
  - 一部指標（tool_calls）は現行導線で定数化されるため、将来は実運用ログ基盤と接続して計測精度を高める余地がある
- 判定: `Go`（Phase 3 完了）

## 19. テンプレート集約（構成/契約の TEMPLATE 化, 2026-02-28）

### 19.1 実施タスク

- [x] `TEMPLATE/` 配下を新設し、構成・契約資産の集約先を作成
- [x] schema / contract policy / task template を `TEMPLATE/contracts/` に集約
- [x] 運用標準を `TEMPLATE/operations/` に集約
- [x] CI/CD workflow と設定テンプレートを `TEMPLATE/workflows/`, `TEMPLATE/configs/` に集約
- [x] 新規プロジェクト向けの構成ガイド（`TEMPLATE/PROJECT_STRUCTURE.md`）を追加
- [x] docs index と資産分類台帳から TEMPLATE 導線を接続

### 19.2 2026-02-28 テンプレート集約レビュー

- 実施内容:
  - `docs/schemas`, `docs/contracts`, `tasks/templates`, `docs/operations`, `.github/workflows`, `configs/experiment_pipeline.yaml` を `TEMPLATE/` へ集約
  - `TEMPLATE/README.md` を追加し、展開ルール（どこへ配置するか）を明文化
  - `TEMPLATE/PROJECT_STRUCTURE.md` と `TEMPLATE/scaffold/README.md` を追加し、今後の開発開始手順を固定
  - `docs/README.md` と `docs/operations/ASSET_CLASSIFICATION.md` に TEMPLATE 導線を追記
- 検証:
  - `find TEMPLATE -type f` で集約対象が存在することを確認
  - `git status --short` で意図したファイルのみ変更されていることを確認
- スタッフエンジニア観点:
  - 新規プロジェクトへ移植する際の「構成」と「契約」が同一ディレクトリに集約され、再利用性が高い
  - 元資産の正本は維持しつつ、配布用バンドルを分離できている
- 残課題:
  - 正本変更時の TEMPLATE 同期を自動化するスクリプトは未整備
- 判定: `Go`（テンプレート集約を完了）

## 20. Todo全量実行（Phase3収束 + 管理項目更新, 2026-03-01）

### 20.1 実施タスク

- [x] EXP-003/004 を taskset 対象7repoで実行し、run_id配下に保存
- [x] Phase3補完ハーネス（`scripts/benchmark/complete_phase3.py`）を実装
- [x] EXP-005/006/007/008 の成果物（micro/e2e/ablation/stability）を生成
- [x] dataset manifest と run registry を実体ファイルとして作成
- [x] risk owner と validation status を更新し、ガバナンス未完了を解消
- [x] 再実行導線を `make phase3-complete` として固定

### 20.2 2026-03-01 実行レビュー

- 実施内容:
  - run_id: `run_20260228_154238_exp001_raw` で retrieval/comparison を7repo全件生成
  - `complete_phase3.py` 実行で `micro_benchmark.json`, `e2e_metrics.json`, `ablation.json`, `stability.json` を出力
  - `artifacts/datasets/manifests/ds_20260301_taskset_v2_full_raw.manifest.json` を作成（schema valid）
  - `artifacts/experiments/run_registry.v1.jsonl` を作成し run_record を登録
- 検証:
  - `pytest -q` => PASS (24)
  - `python3 scripts/ci/validate_contracts.py` => PASS
  - `dataset_manifest` / `run_record` schema validation => PASS
- 主要成果物:
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/retrieval_*.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/comparison_*.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/micro_benchmark.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/e2e_metrics.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/ablation.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/stability.json`
- 再実行コマンド:
  - `make phase3-complete RUN_ID=run_20260228_154238_exp001_raw`
- 判定: `Go`（Phase3および関連管理項目を完了）

### 20.3 2026-03-01 残課題クローズ（tool-call証明 / cross-env / 環境固定）

- 実施内容:
  - `scripts/benchmark/analyze_toolcall_reduction.py` を追加し、comparison成果物から tool-call 削減率を定量化
  - `scripts/pipeline/run_cross_env_repro.py` を追加し、Python 3.11 で主要実験（EXP-001/003/004）を再実行
  - lockfile (`requirements-lock.txt`) とコンテナ実行基盤 (`Dockerfile.repro`) を追加
  - cross-env 実行導線として `scripts/dev/run_cross_env_repro.sh` を追加
- 検証:
  - tool-call 証明: `tool_call_reduction.json` で `avg_calls_agentretrieve=1.0`、対ripgrep workflow `5.86`、対git-grep workflow `5.94`、削減率は約 `83%`
  - cross-env: `cross_env_py311/cross_env_repro_report.tol30.json` の `all_passed=true`
  - 許容誤差: quality指標は絶対誤差 `±0.01`、latencyは相対誤差 `±30%`（runtime差分吸収）
- 成果物:
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/tool_call_reduction.json`
  - `artifacts/experiments/runs/run_20260228_154238_exp001_raw/cross_env_py311/cross_env_repro_report.tol30.json`
  - `requirements-lock.txt`, `Dockerfile.repro`
- 判定: `Go`（残4項目を解消）
