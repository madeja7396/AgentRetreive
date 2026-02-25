# AgentRetrieve 開発計画（非埋め込み・エージェントネイティブ）

## 0. 目的（成功条件）

- **ツール呼び出し回数を減らす**：探索→検索→検査を「検索API 1回」でほぼ完結させる。
    
- **トークン効率最大化**：出力は **ミニJSON固定スキーマ**（短キー + 辞書 + enum + 上限 + cursor）。
    
- **非埋め込み**：embeddingプロバイダ不要。決定性/再現性/軽量性を優先。
    
- **AIネイティブ**：人間の自然言語入力ではなく、**エージェントが生成する構造化クエリ(DSL)** を一次入力にする。
    

---

## 1. 立ち位置（既存の埋め込み系 grep と違う点）

### 1.1 コペルニクス的転回：LLMにファイル名を見せない（Capability-based Retrieval）

**通念の反転**：多くのツールは「人間が読むために _パス/行/差分_ をそのまま出す」。  
本提案は逆で、LLMには **短い不透明ハンドル（capability）** だけを渡す。

- `doc_id` / `span_id` はツールが発行する **参照権（capability）**
    
- LLMは以後「IDで読む/拡張する」だけ：`ar rd --span <id>`
    
- パス文字列の反復を消し、**トークンを削る + 情報漏えい面も縮む**
    
- 出力は _proof-carrying_ にする：各spanに `digest`（ハッシュ）と `bounds`（行範囲）を付け、再現性と検証可能性を確保
    

この転回により、ツール設計の中心が「人間可読」から「**最小十分統計量（MSS）**をIDで運ぶ」へ移る。

### 1.2 追加の反転：検索結果ではなく“次の観測プラン”を返す

- `rng`（推奨読み範囲）だけでなく、`next[]`（次に読むべきspan候補）を返す
    
- 目的は「一致箇所の羅列」ではなく、**エージェントの次の1手を最小回数で確定させる**こと
    

---

## 1. 立ち位置（既存の埋め込み系 grep と違う点）

- 埋め込み系は「自然言語→意味検索」をツール側で吸収（例：GrepAI / mgrep の方向）。
    
- 本プロジェクトは逆：
    
    - **意味の分解（意図→キーワード/制約）はエージェント側**
        
    - ツールは **高速・決定的・上限付きのランキング検索**に特化
        

---

## 2. API / CLI（MVP）

### 2.1 コマンド

- `ar q --json <query.json>` … Query（候補提示 + 根拠抜粋 + 範囲）
    
- `ar ix build` / `ar ix update` … Index（初回構築 / 差分更新）
    
- （任意）`ar serve` … 常駐（後回し）
    

### 2.2 入力DSL（JSON）

**思想**：grepの「文字列一致」を越え、エージェントが欲しい制約を持てるようにする。

- 例（概念）：
    
    - `must[]`：必須語
        
    - `should[]`：加点語
        
    - `not[]`：除外語
        
    - `near[]`：近接条件（同一関数/同一ブロック/±N行）
        
    - `lang[]` / `ext[]`
        
    - `path_prefix[]`
        
    - `symbol[]`：識別子（関数名/型名/モジュール名）
        
    - `budget{max_bytes,max_results,max_hits,max_excerpt}`
        

### 2.3 出力（ミニJSON固定スキーマ）

- `v` schema version
    
- `ok`
    
- `p[]` パス辞書（重複排除）
    
- `r[]` 結果：`pi`(path index), `s`(0-1000), `h[]`(hit), `rng`(推奨読み範囲)
    
- `t` truncated
    
- `cur` 続き取得用cursor
    
- `lim` 上限
    

---

## 3. インデックス（非埋め込み）

### 3.1 3本立て（MVP）

1. **Lexical（倒立インデックス + BM25）**
    

- トークナイズ：識別子分割（snake/camel）、英数正規化、記号除去の最小セット。
    
- doc粒度：
    
    - file粒度（まずはここ）
        
    - （余裕が出たら）symbol粒度/ブロック粒度
        

2. **Symbol（軽量構文抽出）**
    

- tree-sitter 等で関数/クラス/トップレベル定義を抽出し、
    
    - `symbol name → file + span` の辞書を作る
        
- 目的：エージェントが「関数名っぽい語」を持っている時に強い。
    

3. **Meta（ファイル属性）**
    

- ext/lang/path/サイズ/最終更新など（ランキングのpriorに使う）
    

### 3.2 ランキング（整数スコア）

- `BM25(should)` を主軸
    
- `must` 未満は除外
    
- 追加ブースト：
    
    - phrase一致
        
    - `near` 満たす
        
    - symbol一致
        
    - file prior（README/docs/src/testsなど）
        
- scoreは **0–1000整数**（決定性優先、浮動小数禁止）
    

---

## 4. 省トークン設計（超重要）

- 辞書化：パス/言語/enum
    
- 抜粋は `max_excerpt` で強制カット
    
- 結果は上位Kのみ、hitも上位Mのみ
    
- `rng`（推奨読み範囲）を返して「次のread」を減らす
    
- 出力総量は `max_bytes` を絶対遵守（超えたら低スコアから落とす）
    

---

## 5. ベンチ（richにする：論文用）

### 5.1 マイクロベンチ（性能）

- Index build time（初回）
    
- Incremental update time（1ファイル/100ファイル）
    
- Query latency（p50/p95/p99）
    
- Peak RSS / index size（disk）
    
- cold start（起動+1クエリ）
    

### 5.2 リトリーバル品質（正解がある評価）

#### Dataset A：キーワード検索ベンチ

- OSSリポを固定コミットで収集（多言語・サイズ段階）
    
- クエリ：
    
    - 既知のシンボル名/エラーメッセージ/設定キー
        
    - 近接条件（例：`auth` と `refresh` が同一関数内）
        
- 正解：対象ファイル or 対象span
    
- 指標：MRR@K / nDCG@K / Recall@K
    

#### Dataset B：エージェント由来クエリ（AIネイティブ）

- タスク文章 → DSLクエリは「生成して固定」し、評価は再現可能にする。
    
- 指標は Dataset A と同じ + DSL妥当率（must/shouldの適合）
    

### 5.3 エンドツーエンド（エージェントコスト）

- 目的：**呼び出し回数とトークンの削減**を定量化
    
- 例タスク：
    
    - “この関数の責務は？”（該当定義と呼び出し元を拾えるか）
        
    - “設定値Xはどこで使われる？”
        
    - “エラー文Yの発生条件は？”
        
- 指標：
    
    - Tool calls / task
        
    - stdout bytes（=LLMに渡る情報量のproxy）
        
    - Time-to-first-candidate
        

### 5.4 比較ベースライン

- ripgrep / git grep（厳密一致）
    
- 埋め込み系：GrepAI, mgrep（参考比較）
    
- ablation：BM25のみ / +symbol / +near / +prior
    

---

## 6. 論文（ペーパー）構成案

1. Introduction：エージェントはgrepを多用し、反復でターン/遅延/トークンが膨らむ問題
    
2. Problem：
    
    - 目的関数：回答品質を保ちつつ tool calls と tokens を最小化
        
3. Method：
    
    - 構造化DSL
        
    - 非埋め込みインデックス（BM25 + symbol + meta）
        
    - ミニJSON contract（上限・決定性）
        
4. Experiments：
    
    - micro（性能）
        
    - retrieval（MRR/nDCG）
        
    - e2e（tool calls/bytes/time）
        
5. Related Work：
    
    - 埋め込み系 semantic grep と agentic search
        
6. Limitations：
    
    - NL意図理解はエージェント側依存
        
    - rename/同義語は弱い（必要なら query expansion）
        

---

## 7. 直近ToDo（実装順）

1. DSL v1 & 出力スキーマv1確定（short keys, enums, limits, cursor）
    
2. Index：tokenizer + inverted index（file粒度）
    
3. Query：BM25 + must/should/not + budget切り詰め
    
4. Evidence：抜粋生成（最小）+ `rng` 推奨範囲
    
5. Bench harness：固定リポ収集（commit固定）+ 指標計算
    
6. README：ベンチ結果 + 「呼び出し回数削減」のデモ