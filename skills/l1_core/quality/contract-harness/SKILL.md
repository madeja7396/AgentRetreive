---
name: l1-core-contract-harness
description: Run and enforce contract/CI quality gates before and after any implementation change.
---

# L1 Core: Contract Harness

## When to use

- 仕様/スキーマ/契約に関わる変更前後
- CI で契約検証が失敗したとき
- 実装完了時の最終品質ゲート

## Steps

1. Run:
```bash
bash scripts/ci/run_contract_harness.sh
```
2. If needed refresh env:
```bash
bash scripts/ci/run_contract_harness.sh --refresh
```
3. Record result in `tasks/todo.md` review section.

## Guardrails

- 失敗を無視して先へ進まない
- 破壊的変更は v1 上書き禁止
- 検証結果のない主張を残さない

## Canonical references

- `skills/agentretrieve-contract-harness/SKILL.md`
- `skills/agentretrieve-contract-harness/references/failure-playbook.md`

