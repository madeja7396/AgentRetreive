---
name: l2-ops-ar-cli-runtime
description: Install and operate AgentRetrieve ar launcher in environments where GNU ar already exists.
---

# L2 Ops: AR CLI Runtime

## When to use

- この環境で `ar` を AgentRetrieve CLI として使いたいとき
- `/usr/bin/ar`（GNU binutils）との衝突を避けて運用したいとき
- CLI 配布導線（`release-cli-*`）の検証前に実行環境を整えるとき

## Steps

1. Build binary (if not built yet):
```bash
cargo build --profile release-dist -p ar-cli
```
2. Install launcher:
```bash
bash scripts/dev/install_ar_launcher.sh
```
3. Verify AgentRetrieve route:
```bash
ar ix --help
ar q --help
ar --help
```
4. Verify GNU fallback:
```bash
AR_LAUNCHER_FORCE_GNU=1 ar --version
ar rcs /tmp/ar_skill_smoke.a /tmp/ar_skill_smoke.o
```

## Guardrails

- `/usr/bin/ar` を置き換えない（launcher は `~/.local/bin/ar` のみ）
- AgentRetrieve 経路は `ix/q/help` のみ、その他は GNU `ar` へフォールバックする
- `target/*/ar` の場所を変えた場合は launcher を再インストールする

## Canonical references

- `scripts/dev/install_ar_launcher.sh`
- `docs/operations/CLI_DISTRIBUTION.md`
- `skills/l1_core/quality/contract-harness/SKILL.md`
