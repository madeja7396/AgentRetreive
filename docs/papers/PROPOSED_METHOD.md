# AgentRetrieve: Proposed Method

## 1. Problem Formulation

### 1.1 Traditional Code Search (Human-Centric)
- **Input**: Natural language or regex patterns
- **Output**: File paths, line numbers, code snippets
- **Optimization**: Human readability

### 1.2 Agent-Native Code Search (Proposed)
- **Input**: Structured DSL (must/should/not constraints)
- **Output**: Capability handles + minimal context
- **Optimization**: Tool-call efficiency + token economy

**Key Metric**: Minimize `Tool Calls per Task` and `Output Tokens` while maintaining retrieval accuracy.

## 2. Architecture

### 2.1 Design Principles

| Principle | Rationale |
|-----------|-----------|
| Non-embedding | Deterministic, reproducible, no external API dependency |
| Capability-based | LLM receives opaque handles, not full paths |
| Budget-aware | Strict output limits (bytes/results/hits) |
| Proof-carrying | Results include digest + bounds for verification |

### 2.2 System Components

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  DSL Input  │────▶│ Query Engine │────▶│ Mini-JSON   │
│  (JSON)     │     │ (BM25 +      │     │ Output      │
└─────────────┘     │  Constraints)│     └─────────────┘
                    └──────────────┘           │
                           │                   │
                    ┌──────▼──────┐           │
                    │ Inverted    │◀──────────┘
                    │ Index       │  (doc_id lookup)
                    │ (File-gran. │
                    │  BM25)      │
                    └─────────────┘
```

## 3. Index Structure

### 3.1 Tokenization
**Identifier-aware tokenization** for code:
- `camelCase` → `["camel", "case"]`
- `snake_case` → `["snake", "case"]`
- `HTTPResponse` → `["http", "response"]`

### 3.2 Inverted Index
```python
IndexEntry {
  term: str
  df: int                    # Document frequency
  postings: List[Posting]    # (doc_id, tf) pairs
}

Posting {
  doc_id: int
  tf: int                    # Term frequency
}
```

### 3.3 BM25 Scoring
```
score(q, d) = Σ idf(t) · (tf(t,d) · (k1 + 1)) / (tf(t,d) + k1 · (1 - b + b · |d|/avgdl))

where:
  k1 = 1.2, b = 0.75
  score range: 0-1000 (integer)
```

## 4. Query Processing

### 4.1 Input DSL
```json
{
  "version": "dsl.v1",
  "must": ["required", "terms"],
  "should": ["boost", "terms"],
  "not": ["exclude", "terms"],
  "near": [{
    "terms": ["close", "together"],
    "scope": "line_window",
    "window": 5
  }],
  "budget": {
    "max_results": 20,
    "max_hits": 10,
    "max_bytes": 8192,
    "max_excerpt": 256
  }
}
```

### 4.2 Processing Pipeline
1. **Normalize**: lowercase, identifier split, punctuation removal
2. **Must Intersect**: Documents must contain ALL must terms
3. **Should Boost**: Add BM25 score for should terms
4. **Not Filter**: Remove documents containing not terms
5. **Rank**: BM25 score (descending), integer 0-1000
6. **Truncate**: Enforce budget limits strictly

## 5. Output Format

### 5.1 Mini-JSON v1
Short keys for token efficiency:

```json
{
  "v": "result.v1",
  "ok": true,
  "p": ["src/main.rs", "README.md"],
  "r": [{
    "pi": 0,
    "s": 456,
    "h": [{"ln": 42, "txt": "fn main()", "sc": 100}],
    "rng": {"from": 40, "to": 45},
    "next": ["span_00000001_002"],
    "doc_id": "doc_00000000",
    "span_id": "span_00000000_001",
    "digest": "a1b2c3d4",
    "bounds": {"start": 1, "end": 100}
  }],
  "t": false,
  "cur": null,
  "lim": {
    "max_bytes": 8192,
    "max_results": 20,
    "max_hits": 10,
    "max_excerpt": 256,
    "emitted_bytes": 456
  }
}
```

### 5.2 Capability Handles
- `doc_id`: Opaque document reference
- `span_id`: Specific location within document
- `digest`: Content hash for verification
- `bounds`: Line range for proof-carrying

## 6. Evaluation Results

### 6.1 Retrieval Quality (25 tasks, 5 repositories)

| Repository | Tasks | Recall@5 | MRR@5 | Mean Latency |
|-----------|-------|----------|-------|--------------|
| ripgrep | 5 | 100% | 0.58 | 139ms |
| fd | 5 | 100% | 0.77 | 21ms |
| fzf | 5 | 100% | 0.47 | 105ms |
| curl | 5 | 80% | 0.51 | ~15s* |
| fmt | 5 | 100% | 0.70 | 112ms |
| **Average** | **25** | **96%** | **0.61** | **-** |

*curl requires query optimization for large corpora (>1000 files)

### 6.2 Determinism
- **Test**: 5 runs, same query, same index
- **Result**: 100% identical outputs
- **Verification**: PASS

### 6.3 Token Efficiency (vs Traditional)
```
Traditional Output:
  Path: "/long/path/to/src/components/UserAuthentication.ts"
  Lines: "function authenticateUser(token: string) {...}"
  
AgentRetrieve Output:
  {"doc_id": "doc_0000000a", "span_id": "span_0000000a_003"}

Token Reduction: ~80% (estimated)
```

## 7. Limitations

1. **No Semantic Understanding**: Relies on lexical matching (intention → keywords is agent's responsibility)
2. **Rename Sensitivity**: Symbol renames require separate handling
3. **Scale**: Large corpora (>1000 files) need query optimization

## 8. Comparison with Baselines

| Aspect | ripgrep | git grep | AgentRetrieve |
|--------|---------|----------|---------------|
| Input | Regex | Regex | Structured DSL |
| Output | Text lines | Text lines | Mini-JSON |
| Ranking | None | None | BM25 |
| Token Efficiency | Low | Low | High |
| Deterministic | Yes | Yes | Yes |
| Agent-Native | No | No | Yes |
