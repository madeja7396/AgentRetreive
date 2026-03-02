# R1-PERF 性能測定報告

**ID**: R1-PERF  
**目的**: large-repo 含む性能改善を実測で証明  
**完了日**: 2026-03-02  
**ステータス**: ⚠️ 条件付き完了（Python測定のみ）

---

## 測定概要

### 環境
- **Date**: 2026-03-02
- **Platform**: Linux-6.6.87.2-microsoft-standard-WSL2-x86_64
- **CPU**: x86_64
- **RAM**: 30.66 GB
- **Python**: 3.12.3
- **Rust**: cargo 1.85.0

### 対象リポジトリ
- **fd**: 24 documents, 1,862 terms
- **Index size**: 1.1 MB (JSON format)

### 測定方法
```python
# Warmup: 3 iterations
# Benchmark: 10 iterations × 4 queries = 40 searches
# Queries: ["main", "search", "file", "path"]
```

---

## 結果

### Python Backend

| Metric | Value |
|--------|-------|
| Average | **21.577 ms** |
| Minimum | 18.468 ms |
| Maximum | 26.255 ms |
| Queries | 40 |

### Rust Backend (CLI Bridge)

**ステータス**: 基盤実装完了、性能測定は制約あり

**制約**:
- Rust backendはバイナリindex形式（`.bin`）を必要とする
- 現状のJSON index（`.json`）とは互換性なし
- R1-WALでバイナリ形式への変換/永続化を実装予定

**確認済み機能**:
- ✅ `ar-cli`検出: `/mnt/d/dev/AgentRetrieve/target/release/ar-cli`
- ✅ Index load: バイナリ形式であれば可能
- ✅ Search execution: `ar q`コマンド経由で実行可能
- ✅ JSON parsing: 結果をPythonオブジェクトに変換

---

## 制約と次のステップ

### 現状の制約

1. **Index形式の不一致**
   - Python: JSON形式（互換性・可読性重視）
   - Rust: バイナリ形式（性能・サイズ重視）
   - 変換レイヤーが必要

2. **完全な性能比較不可**
   - 同条件（同じindex形式）での比較ができない
   - Python側のレイテンシにJSONパースが含まれる
   - Rust側はmmapベースのゼロコピーを実現可能

### 次のステップ（R1-WAL）

```
R1-WAL: 差分更新（WAL/compaction）実装
├── バイナリindex形式の定義
├── JSON→バイナリ変換
├── WALログ実装
└── Compaction処理
```

R1-WAL完了後、以下が可能になる:
- Python vs Rust 同条件性能比較
- Large-repo（10k+ docs）での測定
- mmapによるゼロコピー効果の検証

---

## まとめ

### 達成したこと

- ✅ Python backend性能基準確立: **21.577ms avg** (fd repo)
- ✅ Rust backend CLI bridge実装完了（R1-CORE）
- ✅ 性能測定インフラ整備

### 達成できなかったこと

- ⚠️ Rust backend性能測定（index形式不一致）
- ⚠️ Large-repo性能検証（10k+ docs）
- ⚠️ Python vs Rust 直接比較

### 結論

R1-PERFは**条件付き完了**とする。

完全な性能比較はR1-WAL（バイナリindex実装）後に実施。
現状では:
1. Python backend性能基準を確立
2. Rust backend実行基盤を整備
3. 性能測定方法を確立

---

## Run Record

```json
{
  "version": "run_record.v2",
  "run_id": "r1_perf_baseline_20260302",
  "created_at_utc": "2026-03-02T00:00:00Z",
  "baseline": {
    "python_backend_ms": 21.577,
    "repository": "fd",
    "docs": 24,
    "queries": 40
  },
  "rust_backend": {
    "status": "bridge_ready",
    "note": "binary_index_required"
  }
}
```
