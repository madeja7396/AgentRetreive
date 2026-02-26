---
name: agentretrieve-contract-harness
description: Strengthen and enforce AgentRetrieve implementation contracts, benchmark schemas, and CI harness guardrails. Use when adding or modifying docs/schemas, docs/benchmarks, docs/contracts, contract validation scripts, or when fixing CI failures from contract checks.
---

# AgentRetrieve Contract Harness

## Overview

Enforce contract-first development for AgentRetrieve. Run strict validation, apply minimal corrective patches, and keep schema/input/policy files in sync with CI.

## Workflow

1. Read the current contract sources:
- `docs/contracts/contract_policy.v1.json`
- `docs/schemas/*.schema.json`
- `docs/benchmarks/*`
- `scripts/ci/validate_contracts.py`

2. Run strict harness:
- `bash scripts/ci/run_contract_harness.sh --refresh`

3. Diagnose failures by class using `references/failure-playbook.md`:
- schema parse/definition errors
- sample/schema mismatch
- JSONL entry errors
- cross-file invariant violations

4. Patch minimal files:
- Prefer schema or policy updates when behavior intentionally changed
- Prefer sample/input fixes when behavior is unchanged
- Keep versioning rules (`v1` overwrite禁止 for breaking changes)

5. Re-run strict harness until pass:
- `bash scripts/ci/run_contract_harness.sh`

6. Record governance updates:
- Add review entry to `tasks/todo.md`
- Update `tasks/lessons.md` if user correction exposed a new failure pattern

## Hard Rules

- Do not change implementation behavior without updating schema/policy contracts first.
- Do not bypass cross-file invariant failures by weakening checks silently.
- Do not merge contract changes without local harness pass.
- Do not introduce undocumented keys outside namespace policy.

## Resources

### scripts/run_skill_harness.sh
Run the project strict harness from skill context.

### references/failure-playbook.md
Map failure signatures to likely root causes and fix targets.

### agents/openai.yaml
UI metadata generated from this skill content.
