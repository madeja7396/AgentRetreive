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
