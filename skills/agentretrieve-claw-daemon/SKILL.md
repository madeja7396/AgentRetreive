---
name: agentretrieve-claw-daemon
description: Operate AgentRetrieve claw-style persistent execution with a spool daemon. Use when running project tasks continuously, recovering stuck work, enqueueing harness jobs, or debugging queue lifecycle issues in artifacts/agentd.
---

# AgentRetrieve Claw Daemon

## Overview

Execute project tasks via the spool daemon without introducing ad-hoc shell execution. Keep queue state observable and recoverable while enforcing fixed task types.

## Workflow

1. Prepare directories:
- `bash scripts/dev/prepare_worktree.sh`

2. Enqueue task:
- `python3 scripts/daemon/enqueue_task.py --type contract_harness`

3. Run daemon:
- One shot: `bash scripts/daemon/run_agentd.sh --once`
- Continuous: `bash scripts/daemon/run_agentd.sh`

4. Inspect results:
- Success: `artifacts/agentd/spool/done/`
- Failures: `artifacts/agentd/spool/dead/`
- Logs: `artifacts/agentd/logs/*.log`

5. Recover failures with playbook:
- `references/queue-failure-playbook.md`

## Allowed Task Types

- `contract_harness`
- `contract_harness_refresh`
- `prepare_worktree`

Never add arbitrary shell execution to daemon task types.

## Resources

### scripts/daemon_once.sh
Run queued tasks once and exit.

### scripts/enqueue_contract_harness.sh
Enqueue strict contract harness task quickly.

### references/queue-failure-playbook.md
Map queue symptoms to corrective actions.

### agents/openai.yaml
UI metadata generated from this skill definition.
