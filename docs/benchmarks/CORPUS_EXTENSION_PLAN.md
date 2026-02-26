# Corpus Extension Plan v1.1

## 概要

v1コーパスの拡張版として、pytest（Python）とcli/cli（Go）を追加。

## コーパス構成

| # | ID | Language | Type | Purpose |
|---|----|----------|------|---------|
| 1 | ripgrep | Rust | Search tool | Original |
| 2 | fd | Rust | File finder | Original |
| 3 | fzf | Go | Filter tool | Original |
| 4 | curl | C | Network tool | Original |
| 5 | fmt | C++ | Format library | Original |
| **6** | **pytest** | **Python** | **Testing framework** | **New** |
| **7** | **cli** | **Go** | **CLI tool** | **New** |

## 追加リポジトリ詳細

### pytest (必須追加)
- **URL**: https://github.com/pytest-dev/pytest
- **Version**: v7.4.3
- **Language**: Python
- **License**: MIT
- **Size**: 253 files, 7056 terms, 328K tokens
- **特徴**: 
  - プラグインシステム
  - Fixture機構
  - Assertion書き換え
  - テスト自動検出

### cli/cli (推奨追加)
- **URL**: https://github.com/cli/cli
- **Version**: v2.87.3
- **Language**: Go
- **License**: MIT
- **Size**: 824 files, 7646 terms, 860K tokens
- **特徴**:
  - GitHub API統合
  - コマンドライン操作
  - 認証フロー
  - 拡張可能なアーキテクチャ

## 多言語カバレッジ

| 言語 | リポジトリ数 | 用途 |
|------|------------|------|
| Rust | 2 | システムツール |
| Go | 2 | CLI/フィルタリング |
| C | 1 | ネットワーク |
| C++ | 1 | ライブラリ |
| **Python** | **1** | **テスティング** |

## タスク設計案

### pytest向けタスク案

```json
{
  "id": "pytest-easy-01",
  "repo": "pytest",
  "difficulty": "easy",
  "type": "symbol_definition",
  "query_nl": "Where is the fixture decorator defined?",
  "query_dsl": {"must": ["fixture", "decorator"]},
  "gold": {"file": "src/_pytest/fixtures.py", "anchor": "def fixture"}
}
```

### cli向けタスク案

```json
{
  "id": "cli-easy-01",
  "repo": "cli",
  "difficulty": "easy",
  "type": "symbol_definition",
  "query_nl": "Where is the pr create command implemented?",
  "query_dsl": {"must": ["pr", "create", "command"]},
  "gold": {"file": "pkg/cmd/pr/create/create.go", "anchor": "NewCmdCreate"}
}
```

## 利点

1. **Pythonカバレッジ**: 動的言語の検索特性を評価
2. **テスティングドメイン**: 開発者にとって重要な領域
3. **API統合**: GitHub APIの使用パターンを含む
4. **規模の多様性**: 253-824ファイルの範囲

## インデックス構築状況

| リポジトリ | 状態 | ドキュメント | 用語数 |
|-----------|------|------------|--------|
| pytest | ✅ 完了 | 253 | 7,056 |
| cli | ✅ 完了 | 824 | 7,646 |

## 次のステップ

1. v2タスクセットにpytest/cliタスクを追加
2. 既存タスクと同様の難易度層化を適用
3. 最適パラメータで評価実行
4. 結果を集計・比較
