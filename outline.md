[[AgentRetrieve]]

「人間の可読性を捨てる」は既に強いけど、もう一段ひっくり返すなら、**“LLMがファイル名すら見ない”**まで行くのが効く。ここがコペルニクス味。

---

## コペルニクス的転回：LLMに“世界”を見せない（Capability-based Retrieval）

通念：  
検索ツールは「パス/行/スニペ」をそのまま出して、LLMがそれを読んで次を決める。

転回：  
LLMには **不透明ハンドル（capability）** しか渡さない。LLMは **IDで読む**だけ。

- `doc_id` / `span_id`（短い整数 or base32）をツールが発行
    
- LLMは `ar rd --span <id>` みたいにID指定で続きを取る
    
- パス文字列の反復が消えて **トークンが落ちる**
    
- さらに副作用として、LLMが勝手に「関係ないファイルを想像で開く」余地が減る（安全面の縮退）
    

この発想、OSで言う **capability-based security** と同型。  
LLMは“世界の表現”を持たず、ツールが発行した参照権だけを持つ。

---

## もう一つの反転：検索結果を返すな。**観測プラン**を返せ

通念：  
“ヒット一覧”が検索の出力。

転回：  
エージェントはヒット一覧が欲しいんじゃなくて、**次の一手が確定するだけの最小情報**が欲しい。  
なので AgentRetrieve は「一致箇所」より「次に読むべき塊」を返す。

出力をこうする：

- `next[]`: 次に読むべき `span_id` 候補（上位K）
    
- `rng`: 推奨読み範囲（±N行とか関数ブロックとか）
    
- `proof`: `digest`（ハッシュ）+ `bounds`（行範囲）で再現可能性を担保
    

つまり「検索」ではなく **能動観測（active sensing）**。  
“情報利得が最大になりそうな断片を提示する装置”になる。

---

## SLM台頭/コスト最適に刺さる理由

SLMが得意なのは「狭いスキーマに従ってツールを呼ぶ」やつ。小さめモデルをツール呼び出しに最適化する流れも出てる。 ([arXiv](https://arxiv.org/abs/2512.15943?utm_source=chatgpt.com "Small Language Models for Efficient Agentic Tool Calling"))  
各社が **JSON Schemaでの厳密な構造化出力**に寄せてるのも同じ方向（＝契約で動かす）。 ([Android Central](https://www.androidcentral.com/apps-software/ai/google-is-making-it-easier-to-use-the-gemini-api-in-multi-agent-workflows?utm_source=chatgpt.com "Google is making it easier to use the Gemini API in multi-agent workflows"))

だからツール側は「LLMが賢く読む前提」を捨てて、**賢いのはツール、LLMは配線**でいい。

---

## ベンチを“rich”にするなら：勝負軸をズラす

埋め込み系に対して、検索精度だけで殴り合うと不利になる瞬間がある。  
代わりに論文で刺さるのは **総コスト最小化**：

- Tool calls / task（最重要）
    
- stdout bytes（≒LLMに渡る情報量、トークンのproxy）
    
- latency（p50/p95/p99）
    
- 決定性（同一入力→同一出力）
    
- そして retrieval 指標（MRR/nDCG/Recall）は “守備範囲の確認” として出す
    

比較ベースラインは

- `ripgrep/git grep`（厳密一致）
    
- 埋め込み系（例：GrepAI, mgrep）を参考比較（思想が違うので勝負軸はコスト/再現性/往復） ([GitHub](https://github.com/yoanbernabeu/grepai?utm_source=chatgpt.com "yoanbernabeu/grepai: Semantic Search & Call Graphs ..."))
    

---

## 実装上の具体変更（AgentRetrieve設計に追加すべき最小セット）

- 出力は **pathを原則出さない**（`doc_id`辞書とcapabilityのみ）
    
- `span_id`に `digest` と `bounds` を必須化（proof-carrying）
    
- `next[]`（次の観測候補）を返す
    
- `cursor`でページング（上限超えでも再取得可能）
    

この方向の追記は、キャンバスの AgentRetrieve 計画に反映しておいた（capability転回＆観測プラン）。

---

この転回を採用すると、ツールの思想が「検索」から「**最小の観測で意思決定を確定させる装置**」に変わる。エージェントとSLMの時代に、わりと露骨に“正しい向き”なんだよね。
