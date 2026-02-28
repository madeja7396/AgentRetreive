---
name: l2-ops-claw-daemon
description: Operate queued daemon tasks safely with fixed task types and recoverable spool state.
---

# L2 Ops: Claw Daemon Runtime

## When to use

- 定常の非対話実行（contract_harness など）
- キュー停滞や再試行運用
- daemon ログ監査

## Steps

1. Prepare:
```bash
bash scripts/dev/prepare_worktree.sh
```
2. Enqueue:
```bash
python3 scripts/daemon/enqueue_task.py --type contract_harness
```
3. Run daemon:
```bash
bash scripts/daemon/run_agentd.sh --once
```
4. Inspect:
- `artifacts/agentd/spool/done/`
- `artifacts/agentd/spool/dead/`
- `artifacts/agentd/logs/`

## Guardrails

- task type は固定リスト以外を許可しない
- `in_progress` を手動編集しない
- `dead` の再投入前に失敗原因を記録する

## Canonical references

- `skills/agentretrieve-claw-daemon/SKILL.md`
- `docs/operations/AGENTD.md`

