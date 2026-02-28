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

*最終更新: 2026-03-01*
