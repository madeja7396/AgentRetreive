# ripgrep Timeout Investigation Report

## 現象

比較実験においてripgrepが一貫してタイムアウト（5秒以上）

## 調査結果

### 1. ファイル単体では正常動作
```bash
$ rg -i "smart" README.md
# → 即座に結果表示（成功）
```

### 2. リポジトリ全体ではヒットしない
```bash
$ rg -i "smart" -g "*.md"
# → 0件（即座に終了）
```

### 3. リポジトリ構造
- ファイル数: 45
- サイズ: 828KB
- .gitignore: 存在

### 4. 問題の切り分け

| テスト | 結果 | 推論 |
|--------|------|------|
| README.md指定 | OK | ファイル読み込み正常 |
| -g "*.md" | 0件 | globパターンで無視？ |
| --no-ignore | 未テスト | .gitignoreの影響？ |
| インストール先 | cargo | PCRE2無しビルド |

## 根本原因の仮説

### 仮説1: PCRE2未サポート
```
ripgrep 15.1.0
features:-pcre2
```
正規表現パターンの処理に問題？

### 仮説2: クエリパターンの問題
- 現在の実装: 単純な単語（"smart", "default"）
- これらが一般すぎて大量ヒット？

### 仮説3: .gitignore/.ignoreの影響
- fdリポジトリには.ignoreや.gitignoreが存在
- これらが意図せず検索対象を制限？

### 仮説4: バイナリファイル探索
- Cargo.lockなどの大きなファイル
- バイナリとみなされず全文検索？

## 解決策

### 即時対応
```bash
# ファイルタイプ指定を追加
rg -i "pattern" -t rust -t md

# 明示的にパスを指定
rg -i "pattern" src/ README.md

# バイナリ除外
rg -i "pattern" --binary-files=without-match
```

### 比較実験の修正
```python
# 現在
pattern = query_terms[0].lower()
cmd = ['rg', '-i', '--max-count', '20', pattern]

# 修正案
cmd = ['rg', '-i', '-F', '--max-count', '20',  # 固定文字列
       '-g', '*.rs', '-g', '*.md',             # ファイルフィルタ
       '--binary-files=without-match',         # バイナリ除外
       pattern]
```

## 未解決事項

1. 実際にrgが何をしているかプロファイルが必要
2. 正確なタイムアウトのトリガー特定
3. 他のリポジトリでも同様の問題が起きるか確認

## 暫定対応

ripgrep比較は一時的に「データなし」として扱い、
git grepとAgentRetrieveの比較を優先する。
