# AgentRetrieve Lessons Learned

## 実験・評価に関する教訓

### 2026-02-26: フルパイプライン実行

**観測事実**:
- 7リポジトリ35タスクで71.4% recall達成
- curl（1,849ファイル）のレイテンシが15.9秒と実用不可
- min_match=0.5のクエリ緩和が最重要パラメータ（+20-30% recall）

**教訓**:
1. グリッドサーチは並列化必須（300設定×直列実行は非現実的）
2. 大規模コーパス（>1000ファイル）は別途最適化が必要
3. MRR 0.346はランキング品質に大きな改善余地あり

**対応**:
- 並列パイプラインを実装（ProcessPoolExecutor）
- 最適パラメータをデフォルト設定に反映

---

### 2026-02-26: パラメータ探索の知見

**観測事実**:
- リポジトリごとに最適パラメータが異なる（fd: k1=0.8/b=1.0, fmt: k1=1.5/b=1.0）
- b（文書長正規化）は影響が小さい
- max_terms>3はノイズ増加のみで効果なし

**教訓**:
- ユニバーサル最適値は存在せず、コーパス特性による
- グローバル設定より、コーパスサイズに応じたプリセットが実用的

**対応**:
- スモール/ミディアム/ラージの3段階プリセットをドキュメント化

---

### 2026-02-26: 難易度別性能の傾向

**観測事実**:
- Easy: 85.7% → Medium: 64.3% → Hard: 57.1% と漸減
- Hardタスクは文脈依存・複雑な推論を要求
- symbol_definitionは85.7%と安定

**教訓**:
- 単純なBM25+トークナイゼーションでは意味的理解に限界
- Hardタスクにはセマンティック情報（型、スコープ）が必要

**対応**:
- 将来的な改善方向としてセマンティック検索を検討
- 現時点では「小規模・シンボル検索向け」と位置づけを明確化

---

### 2026-02-26: 外部ツール比較の困難さ

**観測事実**:
- ripgrepがPCRE2未サポートでタイムアウト
- 公平な比較には環境・設定の厳密な制御が必要
- git grepは機能的に不足（構造的理解なし）

**教訓**:
- ベンチマーク比較は「同じ条件」での再現性が重要
- 外部ツールの機能差（-Fフラグ、ファイルフィルタ等）を考慮必須

**対応**:
- 比較実験時は-F（固定文字列）フラグを使用
- 個別ファイルvsリポジトリ全体の区別を明確に

---

## 実装上の教訓

### インデックス構造

**教訓**:
- posting listを逐次走査する実装では大規模コーパスに対応不可
- メモリ使用量（curl: 25MB）も問題になる可能性

**改善案**:
- posting listのブロック化と圧縮
- 頻出語のキャッシュ
- スレッド並列化

---

### クエリエンジン

**教訓**:
- min_matchパラメータは「 AND vs OR のトレードオフ」を制御
- strict ANDでは見逃しが多すぎ、緩和しすぎるとノイズ増加

**改善案**:
- クエリ語の重要度重み付け（TF-IDF的アプローチ）
- 動的閾値（コーパスサイズに応じた自動調整）

---

### 2026-02-26: 優先順改修（性能・DSL・テスト導線）

**観測事実**:
- BM25の文書長計算で全索引走査が発生していた（`bm25_score` 呼び出しごと）
- Query DSLの `near/lang/ext/path_prefix/symbol` が実装未反映だった
- `pytest -q` 単体実行では `agentretrieve` import が失敗した

**教訓**:
1. ランキング計算のホットパスは、索引構築時に必要統計を前計算して持つべき
2. スキーマで予約したDSLキーは、未実装のまま放置すると契約負債になる
3. テストは環境変数依存にせず、デフォルト実行で通る導線を先に整える

**対応**:
- `Document.doc_length` と posting行情報を索引に保持し、BM25の再計算を除去
- QueryEngineへ `near/lang/ext/path_prefix/symbol` を追加し、ユニットテストで拘束
- `tests/conftest.py` を追加し、`pytest -q` で `src/` を自動解決

---

### 2026-02-26: near厳密化とcursor継続

**観測事実**:
- `near.scope` を window だけで近似すると、別ブロック/別シンボル跨ぎの誤一致が残る
- ページングでカーソルにquery情報を持たせないと、別クエリに再利用できてしまう
- 同点ソートが未固定だと、ページング境界で結果順が揺れる

**教訓**:
1. 近接検索は「距離条件」と「構造境界条件」を分離して実装する
2. cursor はオフセット単体では不十分で、query-state署名による整合検証が必要
3. ページング導入時は tie-break 規則を明示的に固定する

**対応**:
- `block_regions/symbol_regions` を索引に保持し、`near.scope` 判定を同一領域に限定
- `cur_<offset>_<signature>` を採用し、署名不一致はエラーにした
- ランキング順を `score desc + doc_id asc` に固定し、決定性を確保

---

### 2026-02-26: API差分追従とフォールバック設計の注意点

**観測事実**:
- `SearchPage` のAPI変更（`next_cursor` 廃止）後に `CLI`/テスト側の追従漏れが残り、回帰した
- `near.scope=block` で Python AST 境界が空の場合、全体1ブロック扱いに落ちると偽陽性が発生した
- bytes budget で 0 件出力時に offset 非進行カーソルを返すと再取得ループになる

**教訓**:
1. コアAPIの変更時は、`rg` で参照箇所を全列挙して同時改修する
2. 構造抽出のフォールバックは「精度悪化方向」を明示し、判定用途ごとに安全側を選ぶ
3. カーソル進行は「返却候補件数」でなく「実際に提示できた件数」に合わせる

**対応**:
- `CLI` を `next_cursor_for_emitted(len(output.r))` 基準へ変更
- 0件出力 + 残件あり時はエラー化して無限再開を防止
- Python block抽出のフォールバックを空行分割へ修正し、`near.scope=block` の誤一致を抑制

---

### 2026-02-26: ヒューリスティック排除と統計推定の実装上の注意

**観測事実**:
- 旧 index（`posting.lines` 欠落）を使うと `symbol_evidence` が全ゼロになり、学習重みも全ゼロ化した
- 学習候補を `symbol` 事前フィルタで絞ると特徴量分散が潰れ、係数推定が不安定化する
- サンプル数が少ない言語は係数が振れやすく、言語別重みの過学習が起きやすい

**教訓**:
1. 統計推定を導入する前に、学習に使う索引フォーマットの世代整合を必ず確認する
2. 目的変数の識別に必要な特徴分散を確保するため、学習時の候補生成条件は慎重に設計する
3. 言語別係数は shrinkage を入れないと、少数言語で過適合する

**対応**:
- 7repo index を現行コードで再構築し、`posting.lines` と scope メタを再生成
- 学習スクリプトで lexical 候補から特徴抽出し、`symbol` フィルタ依存を除去
- Empirical-Bayes shrinkage を導入して低サンプル言語を global 重みへ縮約

---

### 2026-02-26: コーパス追加運用を manifest 駆動へ統一

**観測事実**:
- 既存運用では `corpus` と `experiment_pipeline` の二重更新が必要で、追加漏れリスクが高かった
- taskset 非登録 repo を強制で学習対象にすると、重み学習が失敗しうる
- major language coverage をチェックしないと、拡張後に言語偏りを見落としやすい

**教訓**:
1. コーパス追加フローは manifest を唯一の入力源にして自動生成へ寄せる
2. 学習ステップは「選択 repo ∩ taskset repo」を前提にガードを入れる
3. 自動化スクリプトには dry-run と coverage 検証を必須で持たせる

**対応**:
- `run_corpus_auto_adapt.py` で clone/index/fit/parameter-search を 1 コマンド化
- taskset 非登録 repo 選択時は重み学習を自動スキップ
- manifest の major-language 不足はデフォルトでエラー化（オプトアウト可能）

---

### 2026-02-26: 構文多様性を入れる際のコーパス選定基準

**観測事実**:
- C系/Python系中心のコーパスでは、記号密度や宣言様式が似通い、汎化検証が甘くなる
- Haskell/Elixir のような構文系統を追加すると、トークン分布・近接特性が大きく変わる
- 主要言語サポートは「manifest 追加」だけでなく、拡張子マッピング同期が必要

**教訓**:
1. コーパス追加の優先軸は「人気」単独ではなく、構文多様性と実務普及の両立で決める
2. 言語追加時は `manifest`, `pipeline config`, `indexer extension map` を同時更新する
3. dry-run で coverage を先に確認してから重い clone/index を回す

**対応**:
- Haskell/Elixir を採用し、C#/PHP/Ruby/Kotlin/Swift/Dart を合わせて major coverage を拡張
- auto-adapt と CLI の両方で言語拡張子マップを更新
- taskset 未整備 repo でも将来拡張できるよう config を先行登録

---

### 2026-02-27: 実行環境制約を前提にした並列探索フォールバック

**観測事実**:
- `run_corpus_auto_adapt.py` の最終段で `ProcessPoolExecutor` が `PermissionError: [Errno 13]` で停止した
- エラー原因は `multiprocessing.SemLock` 生成時の権限制約（実行環境依存）で、探索ロジック自体の不整合ではなかった
- process pool を使えなくても、thread/逐次実行なら同一入力で最適パラメータを決定できた

**教訓**:
1. 並列実行は「方式」ではなく「結果完遂性」を優先し、環境制約を吸収するフォールバックを持つべき
2. 研究パイプラインは失敗即終了より、性能劣化を許容してでも完走する設計が再現性に有利
3. 実運用ログには「失敗理由」と「代替経路」を残し、次回のデバッグ工数を削減する

**対応**:
- `run_full_pipeline.py` に `workers<=1` の逐次実行経路を追加
- `ProcessPoolExecutor` 失敗時は `ThreadPoolExecutor` へ自動フォールバック
- `clone_or_update_corpus` に timeout/retry（`AR_CLONE_TIMEOUT_SEC`）を追加し、clone停滞時の待ち続けを防止
- 修正後に7repo・2100評価を完走し、`aggregate_results.json` と最適値を再生成

---

### 2026-02-27: コーパス公平性の統計設計と実行時間の両立

**観測事実**:
- repo間で `code_file_count` と `code_bytes` の分散が非常に大きく、そのまま比較すると評価バイアスが強い
- 「件数だけ揃える」実装では bytes 側の偏りが残り、公平性説明が弱かった
- 大規模repoで逐次 `stat()` を多用すると、バランシング前処理がボトルネック化した

**教訓**:
1. 公平性は単一指標でなく、少なくとも `件数` と `サイズ` を同時に監査可能な形で揃えるべき
2. 目標値は固定閾値ではなく、コーパス分布の統計量（中央値など）から決定する方が再現性と説明性が高い
3. 大規模コーパス走査では filesystem stat より git object metadata を優先し、I/O待ちを避ける

**対応**:
- `target_files=min(code_file_count)` + `target_bytes=median(target_files * repo_mean_file_bytes)` を導入
- `auto_adapt_summary.json` へ `balanced_code_files_cv`, `balanced_code_bytes_cv`, `balanced_size_deviation_ratio` を追加
- `git ls-tree -rl --long HEAD` ベースでサイズ取得し、走査時間を短縮
- 複雑repoを多指標 z-score 合算で選定し、根拠メトリクスを summary に保存

---

### 2026-02-27: 実験導線は「前処理込みの単一入口」に集約する

**観測事実**:
- 実験実行前に contract/test を手動で回す運用は、ステップ抜けが起きやすい
- clone/index/探索/最終評価が別コマンドだと、失敗時の再開ポイント判断が属人化する

**教訓**:
1. 実験導線は「準備込みの1コマンド」で提供し、失敗点を段階ログで追える形にする
2. 新しい導線は既存スクリプトをラップする構成にし、評価本体ロジックを変更しない

**対応**:
- `run_experiment_route.py` を追加し、`preflight -> auto-adapt -> final-eval` を直列実行
- `Makefile` に `experiment-ready / experiment / experiment-all` を追加
- docs に標準導線を明記

---

### 2026-02-28: KPI不整合は「index整合ゲート」と「SSOT分離」で防ぐ

**観測事実**:
- balanced corpus 用に再構築した index（24 docs/repo）が raw index を上書きし、taskset gold file の大半が index から消えていた
- その状態で評価すると `aggregate_results.json` の指標が低下し、過去の `final_summary.json` と整合しなくなる
- `Makefile` の `validate`/`report` 導線にも実行不能箇所があり、運用上の検証信頼性が下がっていた

**教訓**:
1. 評価前に「taskset gold file が index に存在するか」を機械的に検証し、欠落時は即失敗させるべき
2. KPIのSSOTは1つに固定し、探索集計（`aggregate_results.json`）と最終評価（`final_summary.json`）を混同しない
3. 運用導線（Make target）は定期的に smoke 実行し、参照切れを早期に検知する

**対応**:
- `scripts/pipeline/check_gold_coverage.py` を追加し、gold coverage を検証
- `run_experiment_route.py` に gold coverage ゲートを追加（最終評価前）
- `Makefile validate` を `bash scripts/ci/run_contract_harness.sh` に修正
- `scripts/benchmark/generate_report.py` を追加し、`make report` を復旧
- `docs/PIPELINE_GUIDE.md` で `final_summary.json` を公式KPIのSSOTとして明文化

---

### 2026-02-28: 大規模化フェーズでは「運用文書 + skill階層」を同時に整備する

**観測事実**:
- 改修点がコードだけでなく、運用・評価・報告に跨るため、実装だけ直しても再発を防げない
- skill が flat 構造だと「どの文脈で使う skill か」が曖昧になり、適用判断が属人化する

**教訓**:
1. 重要改修は「コード修正」と「運用マニュアル更新」をセットで完了条件にするべき
2. skill は階層（core/ops/program）で責務分離しないと、保守コストが増える
3. catalog（owner/status/path）を持たない skill 運用は、陳腐化と重複を招く

**対応**:
- `docs/operations/MAINTENANCE_GOVERNANCE.md`, `SIER_SOUL.md`, `RUNBOOK.md`, `SKILLS_OPERATING_MODEL.md` を追加
- `skills/README.md` と `skills/CATALOG.yaml` を追加し、L1/L2/L3 階層を導入
- 既存 flat skill は互換維持しつつ、新規追加は階層配下を正規ルートに固定

---

### 2026-02-28: 復元フェーズ後は owner 情報を「実体ID + 連絡先」で固定する

**観測事実**:
- 復元後はコード自体が復旧しても、運用責任の所在が role 名だけだと引き継ぎ時に判断が止まる
- `skills/CATALOG.yaml` に owner 実体（team/contact/escalation）がないと、障害時の連絡経路が文書間で分散する
- 復元直後の再検証を省くと、運用導線の破損を見落としやすい

**教訓**:
1. owner は抽象 role 名でなく、catalog 上の一意IDと連絡先を持たせるべき
2. skill 運用文書と runbook は owner directory を共通参照し、重複定義を避けるべき
3. 復元後は必ず品質ゲート（test/contract/make導線）を再実行してから完了判定するべき

**対応**:
- `skills/CATALOG.yaml` に `owners` を追加し、`team/contact/escalation` を定義
- 各 skill の `owner` を `owners` 参照IDへ移行（`core_quality`, `ops_runtime`, `ops_governance`, `program_office`）
- `docs/operations/MAINTENANCE_GOVERNANCE.md`, `RUNBOOK.md`, `SKILLS_OPERATING_MODEL.md`, `skills/README.md` を同期更新
- `pytest -q`, `python3 scripts/ci/validate_contracts.py`, `make validate`, `make report`, `make experiment-ready` を再実行

---

### 2026-03-01: 大規模化した資産は「削除前に分類台帳へ接続」する

**観測事実**:
- docs/scripts に有用資産が残っていても、index から参照されないと実質的に存在しないのと同じ状態になる
- 一部 benchmark スクリプトは本番導線では未使用だが、調査・比較で再利用価値がある
- taskset の旧版/補修版/バックアップが混在していると、運用時に誤参照のリスクが上がる

**教訓**:
1. 未接続資産は即削除ではなく `active/incubation/archive` の分類で可視化するべき
2. scripts は「標準導線」と「補助導線」を分離して明示しないと属人的運用になる
3. データセット系ファイルは status を明記した registry を用意しないと SSOT が崩れる

**対応**:
- `docs/operations/ASSET_CLASSIFICATION.md` を新規追加し、knowledge/script/data/root-note を分類
- `scripts/README.md` を追加し、active と incubation スクリプトを明示
- `docs/README.md`, `docs/operations/README.md`, `docs/benchmarks/README.md` に参照導線を追加
- `MAINTENANCE_GOVERNANCE.md` の週次監査に分類台帳の鮮度チェックを追加

---

### 2026-02-28: 再利用を前提にするなら「正本」と「配布テンプレート」を分離する

**観測事実**:
- 正本ディレクトリだけを整備しても、新規プロジェクトへ転用する時に必要資産の抽出で手戻りが発生する
- 契約資産（schema/policy/templates）と運用資産（runbook/governance）は同時に持ち出せないと再現性が崩れる

**教訓**:
1. テンプレート運用では、正本（本体）と配布用バンドル（`TEMPLATE/`）を明示的に分離するべき
2. 構成ガイド（project tree）を同梱しないテンプレートは、導入先で構造ドリフトを起こす
3. テンプレート化後は docs index から導線を張らないと、存在しても使われない

**対応**:
- `TEMPLATE/` を新設し、`contracts/operations/workflows/configs` を集約
- `TEMPLATE/README.md` と `TEMPLATE/PROJECT_STRUCTURE.md` を追加
- `docs/README.md` と `ASSET_CLASSIFICATION.md` に TEMPLATE 導線を追加

---

### 2026-03-01: 実行記録は「出力JSONの実キー」を基準にマッピングする

**観測事実**:
- `final_summary.json` の `overall` キーは `avg_mrr/recall/found` 形式で、`average_mrr/recall_percentage/successful_tasks` ではない
- run record 生成時に期待キーで読んだ結果、初回の `run_record.json` と `RUN_SUMMARY.md` が 0/None を記録した

**教訓**:
1. 記録スクリプトは「ドキュメント上の想定名」ではなく、実ファイルのキーを直接検証してから実装するべき
2. run 成果物を作った直後に sanity check（主要指標が非ゼロか）を入れるべき

**対応**:
- run 記録生成を修正し、`avg_mrr/recall/found/total_tasks/avg_latency_ms` を正しく採取
- `run_record.json` を schema 再検証し、`RUN_SUMMARY.md` を実測値へ更新

---

### 2026-03-01: 大規模コーパスの micro 計測はタイムアウト前提で設計する

**観測事実**:
- `ix build` の micro 計測で一部 repo が I/O wait (`D`) に入り、無制限待機だと実験全体が停止した
- タイムアウト導入後は「失敗を記録して継続」でき、Phase3 全体を完了できた

**教訓**:
1. ベンチハーネスは「完走性」を優先し、重いステップには必ず timeout を付けるべき
2. timeout 時は欠測として落とさず、明示フラグ付きで結果を残すべき

**対応**:
- `scripts/benchmark/complete_phase3.py` に build/update/比較実験の timeout を追加
- micro 出力へ `timed_out` フラグを追加し、後段集計を継続可能にした

---

### 2026-03-01: cross-env 再現は「品質」と「速度」で許容誤差を分ける

**観測事実**:
- Python 3.12 と 3.11 で recall/mrr は一致した一方、平均レイテンシは約25%差が出た
- 単一の固定閾値（例: ±10%）だと、品質は再現していても速度だけで不合格になった

**教訓**:
1. 再現判定は品質指標（recall/mrr）と速度指標（latency）で別閾値を持つべき
2. runtime差を含む cross-env 比較では latency の相対閾値を明示しないと判定が不安定になる

**対応**:
- cross-env レポートに quality ±0.01（absolute）/ latency ±30%（relative）を採用
- `run_cross_env_repro.py` と `run_cross_env_repro.sh` を追加して判定を自動化

---

### 2026-03-01: v2 契約導入は「v1互換 + dual-write + 機械検証」を同時に入れる

**観測事実**:
- v2 schema だけを追加しても、生成導線（run_record）と検証導線（CI/validator）が追従しないと実運用で使えない
- capability の鮮度判定は、`span_id` 単体より `digest`/`epoch` を併用した機械検証の方が事故率が低い
- TEMPLATE バンドルは手動同期だと高確率でドリフトする

**教訓**:
1. 破壊的移行を避けるには v1/v2 の dual-write を先に整備するべき
2. v2 導入時は schema 追加だけでなく、生成スクリプト・CI・runbook まで同一ターンで接続するべき
3. テンプレート配布運用は `--check` を持つ同期スクリプトを必須化するべき

**対応**:
- `result.minijson.v2` / `experiment_run_record.v2` / `run_constraints.v2` を追加
- `generate_run_record.py` で run_record v1/v2 と registry v1/v2 を自動更新
- `ar cap verify` と `result.v2` の `cap_epoch/index_fingerprint` で Invalid/Valid 判定を機械化
- `sync_template_bundle.py` と `make template-sync-check` を追加

---

## 全般的な原則

1. **「シンプルさ」はパフォーマンスの敵ではない**:
   - BM25 + 基本的なトークナイゼーションで71% recallは実用的
   - 過度な複雑化（深層学習等）の前にパラメータチューニングを徹底

2. **「スケール」は別問題**:
   - 小規模で効果的な手法が大規模でも効果的とは限らない
   - curlの15秒問題はアーキテクチャレベルの見直しが必要

3. **「評価」の重要性**:
   - 主観的な「良さ」ではなく、タスクセットによる客観評価が必須
   - 難易度別・タイプ別の分解が真の課題を浮き彫りにする

---

### 2026-03-01: 資産分類判断基準（active/incubation/archive）

**観測事実**:
- スクリプトが増えると「どれを使うべきか」が新人に伝わらず、古い導線を使って事故る
- 一度作った調査スクリプトが「念のため」で残り続け、台帳と実態が乖離する
- archive へ移す判断を先延ばしにすると、incubation が肥大化して分類の意味が薄れる

**教訓**:
1. 分類は「使う頻度」でなく「標準導線に組み込まれているか」で決めるべき
2. 昇格判断には期限を設け、それまでに定常化しなければ廃止候補にすべき
3. archive 移行は「削除」ではなく「履歴保存」として、再利用価値のないものだけ段階的に移すべき

**対応**:
- `scripts/README.md` に「昇格/廃止判断基準」と「最終判断時期」を明記
- `investigate_ripgrep.py` は調査完了のため archive へ移行
- `compare_baselines/compare_with_optimal` は利用実績ありのため incubation 残留、昇格判断を 2026-03-15 に設定

---

### 2026-03-01: 完了判定は「strict gate 実測PASS」前に宣言しない

**観測事実**:
- 23章で「完了レビュー」が記載されていた一方、`validate_figure_integrity.py --strict` は `1 error, 3 warnings` で失敗していた
- `make release-ready` も `RUN_ID` 必須と `cross_env_reproducibility` generator 未実装により完走しなかった
- チェックボックス未完了状態と完了レビューが併存し、完了判定の信頼性が下がった

**教訓**:
1. 完了レビューは必須 gate（strict integrity / release-ready）を実行し、PASSログ確認後にのみ記載するべき
2. 「通常モードPASS（warningsあり）」と「strictモードPASS（warningsなし）」を混同してはいけない
3. チェックボックス状態とレビュー文は同一ターンで整合確認し、矛盾を残さない

**対応**:
- `tasks/todo.md` に 23.8 検証追補を追加し、23章を `Reopen` 判定へ修正
- 次スプリント（24章）を strict 緑化と release-ready 完走に限定して再計画
- 今後は完了宣言前に `python3 scripts/ci/validate_figure_integrity.py --strict` と `make release-ready` を必須実行する

---

### 2026-03-01: 完了判定前に strict gate を実行する

**観測事実**:
- Sprint 完了申告後に `validate_figure_integrity.py --strict` を実行すると、未生成ファイルで warning が残っていた
- `{run_id}` placeholder を持つ input_artifacts が解決されないまま、完了と誤認していた
- 手編集をしていた箇所が残っていると、再生成時に上書き衝突が起きうる

**教訓**:
1. 完了判定は「非 strict 通過」ではなく「strict 通過（警告0）」を基準にすべき
2. placeholder を持つ設定ファイルは、実際のファイル生成で解決可能性を確認してから完了とすべき
3. 図表生成は「ソース定義 → 生成スクリプト → strict 検証」を同一ターンで完走すべき

**対応**:
- Sprint 4 を設け、strict 緑化を完了条件に追加
- `FIGURE_SOURCES.v1.json` の input_artifacts を実パスへ更新（`{run_id}` は生成時に解決）
- `make release-ready` に既定 RUN_ID を組み込み、1コマンドで strict 完走を可能にした
- 完了レビューに「strict gate 通過」の実測ログを必須化

---

### 2026-03-01: TEMPLATE 初期化は「機械的コピー」ではなく「検証可能な導線」にする

**観測事実**:
- 手動で `TEMPLATE/` をコピーすると、必要ファイルの取りこぼしや配置ミスが発生する
- コピー後に契約検証が失敗すると、どのファイルが不足しているか診断が困難
- 初期化直後の品質ゲートが通らないと、テンプレート自体の信頼性が損なわれる

**教訓**:
1. TEMPLATE 初期化は「1コマンド + 検証」で完走させる導線を提供すべき
2. 初期化時にプロジェクト名・owner 等の置換を自動化し、手動編集を減らすべき
3. 生成直後に smoke test（contract/構文チェック）を実行し、品質を保証すべき
4. TEMPLATE 更新後は必ず初期化テストを回し、配布品質を維持すべき

**対応**:
- `scripts/dev/init_project_from_template.py` を追加し、1コマンド初期化を実現
- `make template-init` と `make template-smoke` を追加
- CI に template-init smoke job を追加し、TEMPLATE 更新時の品質を自動検証
- `TEMPLATE/README.md` に初期化手順と運用ルールを追記

---

### 2026-03-01: TEMPLATE smoke は fail-open を許可しない

**観測事実**:
- `make template-smoke` は PASS したが、生成先 `pytest -q` は `no tests ran`（exit 5）だった
- 生成先 `python3 scripts/dev/sync_template_bundle.py --check` は script 不在で失敗した
- smoke では sync-check 失敗を許容しており、品質ゲートとしては偽陽性になっていた

**教訓**:
1. smoke は「失敗を許容して先へ進む」設計にしてはいけない
2. 「PASS」の条件には、テスト実行件数と検証対象件数（0件禁止）を含めるべき
3. テンプレート構造（`contracts/schemas`）と検証スクリプト参照先は常に一致させるべき

**対応**:
- 25章を `Reopen` し、Sprint 6 で template 検証実効性（fail-closed）を改善する計画を追加
- 今後は template 完了判定前に「生成先 `pytest -q` が1件以上実行」「生成先 sync-check 実行可能」を必須確認する

---

### 2026-03-01: 高速実験導線は「profile契約 + force override + state短絡」をセットで設計する

**観測事実**:
- fast 実験を都度手動引数で回すと、repos/output/cache/state の指定漏れで成果物が混線しやすい
- index/symbol-fit の再実行は差分がないケースが多く、毎回フル実行すると反復速度が落ちる
- 一方で短絡のみだと復旧時に再計算できず、品質確認が詰まる

**教訓**:
1. 高速化は「暗黙運用」ではなく profile ファイルに契約として固定するべき
2. 短絡実行は fingerprint ベースにし、再現不能なヒューリスティックを避けるべき
3. 省略可能ステップには必ず `--force-*` を用意し、復旧経路を同一導線に残すべき

**対応**:
- `configs/experiment_profiles.v1.yaml` を導入し fast/full の既定値を明示化
- `run_corpus_auto_adapt.py` に `state-file` と repo/symbol fingerprint 短絡を実装
- `run_experiment_route.py` に `--profile` と force フラグ伝播を実装
- `make experiment-fast` / `make experiment-daily-full` を追加して日常運用へ接続

---

### 2026-03-01: skip系フラグでもサマリ出力経路は常に作成する

**観測事実**:
- `run_corpus_auto_adapt.py --skip-parameter-search` 実行時に、`output_dir` 未作成のまま `auto_adapt_summary.json` を書こうとして失敗した
- ステップ省略は「実行負荷の削減」であり、出力契約（summary 生成）を壊してはいけない

**教訓**:
1. `--skip-*` は処理のみ短絡し、成果物パスの契約は維持するべき
2. summary/manifest のような監査資産は、どの実行モードでも生成されるべき

**対応**:
- `run_corpus_auto_adapt.py` で summary 書き込み前に `output_dir.mkdir(parents=True, exist_ok=True)` を追加
- `skip-parameter-search` 条件でも summary 出力 PASS を実測確認した

---

### 2026-03-01: 実験導線の完了条件は「run_record 生成」まで含める

**観測事実**:
- Sprint 8 で Fast/Full の評価自体は完了したが、run_record 生成時に `runs/{run_id}` ディレクトリ不在で失敗した
- KPI成果物（`final_summary.json`）があっても、記録資産（run_record/registry）が欠けると運用監査が不完全になる

**教訓**:
1. 実験導線の Done は「評価完了」ではなく「run_record まで完走」を基準にするべき
2. route 層は run_record 呼び出し前に run_dir の存在を保証するべき
3. 既存成果物を fallback 参照するだけでなく、run単位ディレクトリへの配置を標準化するべき

**対応**:
- `tasks/todo.md` に Sprint 9（run_record導線修復）を追加し、Program R1 へ接続
- `run_experiment_route.py` で run_dir 自動作成・成果物移送・`--create-run-dir` 伝播を実装
- `generate_run_record.py` で run_dir 自動作成と summary fallback 探索順を実装
- `tests/unit/test_generate_run_record.py` を追加し、再発防止テストを常設

---

### 2026-03-01: backend切替を導入するときは cache key と検証を engine-aware にする

**観測事実**:
- `--engine`（`py`/`rust`）を導入すると、同一repo・同一tasksetでも探索結果キャッシュが混線する可能性がある
- CLI・pipeline・route の一部だけ engine 対応すると、実験導線の一貫性が崩れる

**教訓**:
1. backend切替を導入する場合、キャッシュキーに engine を含めるべき
2. engine パラメータは CLI・pipeline・route を同時に更新し、片系統だけの対応を避けるべき
3. 新しい抽象化層は即座に回帰テストを追加し、導線の退行を防ぐべき

**対応**:
- `run_full_pipeline.py` の search cache key に `engine_backend` を追加
- `run_experiment_route.py` / `run_corpus_auto_adapt.py` / `run_final_evaluation.py` へ `--engine` を伝播
- `tests/unit/test_backends.py` を追加し、factory 解決と fallback を検証

---

### 2026-03-01: todo の完了判定はレビュー本文とチェックボックスを同時更新する

**観測事実**:
- Sprint 29/32/34/35/36 はレビュー本文が `Done` でも、DoD のチェックボックスに `- [ ]` が残っていた
- 進捗可視化が崩れ、次アクション選定のノイズになった

**教訓**:
1. レビューを `Done` に更新するターンで、同じ章の DoD チェックを必ず同期すべき
2. 長期計画（Program R1）では `x` / `~` / ` ` の意味を固定し、状態遷移を明示すべき

**対応**:
- `tasks/todo.md` の過去章チェック漏れを是正し、完了済みDoDを `- [x]` に統一
- Program R1 の未完了項目は `- [~]` へ明示的に状態化し、検証済み項目のみ `- [x]` に更新

---

### 2026-03-02: route の診断系ステップは非ブロッキング化する

**観測事実**:
- `run_experiment_route.py` 本体（contracts/tests/final-eval/run_record）は成功していても、診断系の `export_symbol_support_metrics.py` が閾値警告で非0終了し、全体が失敗していた
- 結果として「実験完走」と「診断警告」が混同され、run_record 成果物の扱いが不安定になった

**教訓**:
1. 実験の完走条件と診断の品質警告は分離すべき
2. route は run_record 生成完了を主成功条件にし、診断失敗は warning に落とすべき

**対応**:
- `run_experiment_route.py` の symbol metrics 実行を try/except 化し、失敗時は warning を出して継続
- これにより `--profile full --skip-auto-adapt` でも route 完走と run_record 生成を安定化

---

*最終更新: 2026-03-01*
