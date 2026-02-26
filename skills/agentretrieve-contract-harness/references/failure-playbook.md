# Failure Playbook

## 1. `schema definition` failures

- Symptom: `[NG] schema definition`
- Likely cause: malformed JSON Schema or invalid Draft 2020-12 construct
- Fix targets:
  - `docs/schemas/*.schema.json`

## 2. `schema validate` failures for JSON files

- Symptom: `[NG] schema validate: <file>.json against <schema>`
- Likely cause: sample file drifted from schema
- Fix targets:
  - `tasks/templates/*.json`
  - `docs/benchmarks/*.json`
  - corresponding `docs/schemas/*.schema.json`

## 3. `jsonl parse` or JSONL entry schema failures

- Symptom: `[NG] jsonl parse` or line-level schema errors
- Likely cause: malformed task entry or invalid field in one task row
- Fix targets:
  - `docs/benchmarks/taskset.v1.jsonl`
  - `docs/schemas/taskset.v1.entry.schema.json`

## 4. `invariant` failures

- Symptom: `[NG] invariant: ...`
- Likely cause:
  - duplicate IDs
  - repo/task cross-reference mismatch
  - count below policy minimum
  - baseline placeholder missing
  - latency order violation
- Fix targets:
  - `docs/benchmarks/*.json*`
  - `docs/contracts/contract_policy.v1.json`

## 5. Governance mismatch after fixes

- Symptom: checks pass but docs/policy not updated
- Likely cause: implementation-only change without contract update
- Fix targets:
  - `docs/SSOT.md`
  - `docs/NAMESPACE_RESERVATIONS.md`
  - `tasks/todo.md`
