# R1-CORE 完了報告

**ID**: R1-CORE  
**目的**: Rust runtimeをPython実行導線へ接続（fail-fast廃止）  
**完了日**: 2026-03-02  
**ステータス**: ✅ 完了

---

## 実装内容

### 1. CLI Bridge実装

**ファイル**: `src/agentretrieve/backends/rust_backend.py`

```python
class RustBackend:
    """Rust engine backend via CLI bridge."""
    
    def build_index(self, root: Path, pattern_csv: str) -> InvertedIndex:
        # ar-cli ix build を呼び出し
        
    def search_page(self, index, ...) -> SearchPage:
        # ar-cli q を呼び出し、JSONパース
```

**機能**:
- `ar-cli`自動検出（`target/release/ar-cli`または`target/debug/ar-cli`）
- 環境変数`AR_CLI_PATH`で上書き可能
- `subprocess`経由でCLIコマンド実行
- JSON出力をパースしてPythonオブジェクト変換

### 2. Backend Protocol準拠

**インターフェース**: `RetrievalBackend` Protocol

| メソッド | 実装状態 | 備考 |
|---------|---------|------|
| `build_index` | ✅ | `ar ix build`経由 |
| `load_index` | ✅ | バイナリindexパス保持 |
| `save_index` | ✅ | ファイルコピー |
| `set_bm25` | ✅ | パラメータ保持 |
| `search` | ✅ | `search_page`ラッパー |
| `search_page` | ✅ | `ar q`経由 + JSONパース |

### 3. 環境変数対応

```bash
# Rustバックエンド使用
export AR_ENGINE=rust

# ar-cliパス明示指定
export AR_CLI_PATH=/path/to/ar-cli
```

### 4. テスト追加

**ファイル**: `tests/unit/test_backends.py`

```python
def test_rust_backend_cli_available(self) -> None:
    """Verify ar-cli binary is detected."""
    backend = create_backend("rust")
    self.assertIn("ar-cli", backend._cli)
```

**テスト結果**:
```
tests/unit/test_backends.py::TestBackendFactory::test_create_backend_python PASSED
tests/unit/test_backends.py::TestBackendFactory::test_create_backend_rust PASSED
tests/unit/test_backends.py::TestBackendFactory::test_rust_backend_cli_available PASSED
...
============================== 7 passed in 0.57s
```

---

## 検証結果

### ビルド確認
```bash
$ cargo build --release -p ar-cli
Finished `release` profile [optimized] target(s) in 51.51s

$ ./target/release/ar-cli --help
AgentRetrieve Rust CLI
Usage: ar-cli <COMMAND>
Commands:
  ix    
  q     
```

### スモークテスト
```bash
$ PYTHONPATH=src AR_ENGINE=rust python3 -c "
from agentretrieve.backends import create_backend
backend = create_backend('rust')
print(f'CLI path: {backend._cli}')
"

[OK] CLI path: /mnt/d/dev/AgentRetrieve/target/release/ar-cli
```

### pytest
```bash
$ PYTHONPATH=src python3 -m pytest tests/unit/test_backends.py -v
============================== 7 passed in 0.57s
```

---

## 制約事項

### 現在の制約

1. **Index形式**: Rustバックエンドはバイナリindex（`.bin`）を必要とする
   - PythonバックエンドはJSON index（`.json`）を使用
   - 互換性変換は`R1-WAL`または別タスクで対応

2. **Search実行**: JSON indexでは検索不可（バイナリ形式必須）
   ```
   [EXPECTED] Rust backend requires binary index
   ```

### 次のステップ

- **R1-WAL**: バイナリindex形式への変換、差分更新実装
- **R1-PERF**: 大規模リポジトリでの性能測定
- **R1-PAPER**: 論文評価導線のv2/v3契約接続

---

## まとめ

R1-COREは以下を達成:

- ✅ Rust runtime（ar-cli）をPythonから呼び出し可能にした
- ✅ Fail-fast（`_unsupported()`）を廃止し、実際のCLI呼び出しに置き換え
- ✅ Backend protocolに準拠した実装
- ✅ 環境変数`AR_ENGINE=rust`で切り替え可能
- ✅ テスト追加（7 tests all passed）

**ブロッカー解消**: RustエンジンがPythonパイプラインに統合された。
