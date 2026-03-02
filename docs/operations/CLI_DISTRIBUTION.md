# CLI Distribution Guide

更新日: 2026-03-03

## 配布方針

- 正式コマンド: `ar`
- 互換コマンド: `ar-cli`（`ar` への互換エイリアス）
- 初回対応プラットフォーム:
  - `linux-x86_64`
  - `macos-arm64`
- 配布チャネル: GitHub Releases
- 整合性: `SHA256SUMS.txt` による検証

## ローカルで配布物を作る

```bash
make release-cli-ready LABEL=local TARGET=linux-x86_64
```

出力:

- `dist/agentretrieve-cli-<label>-<target>.tar.gz`
- `dist/agentretrieve-cli-<label>-<target>.tar.gz.sha256`
- `dist/cli_perf_regression.json`

## リリース前ゲート

- サイズ: stripped binary `<= 3.5MB`
- 性能: `release-dist` の query p50 劣化が `<= 5%`（vs `release`）

## 利用者向けインストール

```bash
tar -xzf agentretrieve-cli-vX.Y.Z-linux-x86_64.tar.gz
cd agentretrieve-cli-vX.Y.Z-linux-x86_64
./bin/ar --help
```

`ar-cli` 互換:

```bash
./bin/ar-cli --help
```

## 開発環境への `ar` 導入（GNU `ar` と共存）

この環境には既定で `/usr/bin/ar`（GNU binutils）が存在するため、AgentRetrieve 用の launcher を `~/.local/bin/ar` に導入して切り替える。

```bash
bash scripts/dev/install_ar_launcher.sh
```

導入後の挙動:

- `ar ix ...` / `ar q ...` / `ar --help`: AgentRetrieve CLI へ転送
- 上記以外の引数（例: `ar rcs libfoo.a ...`）: GNU `ar` へフォールバック

強制的に GNU `ar` を使う場合:

```bash
AR_LAUNCHER_FORCE_GNU=1 ar --version
```

AgentRetrieve バイナリを明示したい場合:

```bash
AR_AGENTRETRIEVE_BIN=/path/to/ar ar ix --help
```

## チェックサム検証

Linux:

```bash
sha256sum -c SHA256SUMS.txt
```

macOS:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

## Python bridge 連携

- 推奨: `AR_BIN_PATH=/path/to/ar`
- 互換: `AR_CLI_PATH=/path/to/ar-cli`

```bash
export AR_ENGINE=rust
export AR_BIN_PATH=/path/to/ar
```
