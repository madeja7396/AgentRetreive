# Taskset Design v2.0

## 1. 設計原則

### 1.1 層化サンプリング（Stratified Sampling）

| 難易度 | 比率 | 定義 |
|--------|------|------|
| Easy | 30% | 一意のキーワードで即座に発見可能 |
| Medium | 50% | 複数キーワードの組み合わせが必要 |
| Hard | 20% | 文脈理解や近接検索が必要 |

### 1.2 タスクタイプ多様性

| タイプ | 比率 | 例 |
|--------|------|-----|
| シンボル定義 | 25% | 関数名、型名の定義場所 |
| 使用箇所検索 | 20% | 関数の呼び出し元 |
| 設定/定数 | 20% | 設定値、マクロ、定数 |
| エラーメッセージ | 15% | エラー文字列の発生箇所 |
| ドキュメント | 20% | README、コメント |

### 1.3 ファイルタイプ分散

| カテゴリ | 比率 | パターン |
|----------|------|----------|
| Source Code | 40% | `src/`, `lib/`, `*.rs`, `*.go`, `*.c` |
| Tests | 20% | `tests/`, `*_test.rs` |
| Documentation | 25% | `README*`, `docs/`, `*.md` |
| Configuration | 15% | `Cargo.toml`, `*.yml`, `Makefile` |

## 2. タスク設計テンプレート

### Easy (Query: 1-2語)
```json
{
  "id": "{repo}-easy-{n:02d}",
  "difficulty": "easy",
  "type": "symbol_definition",
  "query_dsl": {"must": ["unique_function_name"], "k": 1},
  "gold": {"file": "src/module.rs", "span": "fn unique_function_name"}
}
```

### Medium (Query: 2-3語)
```json
{
  "id": "{repo}-med-{n:02d}",
  "difficulty": "medium", 
  "type": "usage_search",
  "query_dsl": {"must": ["function_name", "call", "argument"], "k": 3},
  "gold": {"file": "src/caller.rs", "span": "function_name(arg)"}
}
```

### Hard (Query: 3-5語 + 近接条件)
```json
{
  "id": "{repo}-hard-{n:02d}",
  "difficulty": "hard",
  "type": "error_context",
  "query_dsl": {
    "must": ["error", "message"],
    "near": [{"terms": ["if", "condition"], "window": 5}],
    "k": 5
  },
  "gold": {"file": "src/error.rs", "span": "if condition { error!("message"); }"}
}
```

## 3. 評価指標の拡張

### 3.1 基本指標
- Recall@K
- MRR@K
- Latency (p50, p95, p99)

### 3.2 難易度別指標
- Recall@K per difficulty
- MRR@K per difficulty
- Failure analysis per type

### 3.3 ロバスト性指標
- Query perturbation (クエリ語の削除/置換)
- Synonym handling (同義語での検索)
- Case sensitivity (大小文字の違い)
