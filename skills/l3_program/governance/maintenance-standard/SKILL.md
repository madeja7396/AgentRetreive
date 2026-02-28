---
name: l3-program-maintenance-standard
description: Build non-person-dependent maintenance standards across docs/tasks/skills and enforce SIer_SOUL.
---

# L3 Program: Maintenance Standard

## Goal

- 運用知識を個人依存から組織標準へ変換する
- SIer_SOUL 原則を実務レベルで定着させる

## Steps

1. Audit baseline:
- `docs/operations/*` と `tasks/*` を棚卸し
2. Standardize:
- Do/Don't を更新
- Runbook と RACI を更新
3. Skillize:
- 手順を階層 skill として登録
- `skills/CATALOG.yaml` を更新
4. Verify adoption:
- 定例コマンド（validate/experiment-ready/report）で動作確認
5. Institutionalize:
- `tasks/lessons.md` へ学習を定着

## Guardrails

- 文書だけ作って実行導線を作らない状態を禁止
- skill の責務重複を放置しない
- 更新履歴のない運用ルールを「標準」と呼ばない

## References

- `docs/operations/MAINTENANCE_GOVERNANCE.md`
- `docs/operations/SIER_SOUL.md`
- `skills/README.md`

