---
name: l2-ops-kpi-release
description: Recompute official KPI safely, enforce coverage gate, and publish report artifacts.
---

# L2 Ops: KPI Release

## When to use

- 公式KPIを更新するとき
- 実験結果の公開・報告を行うとき
- KPI不整合を修復するとき

## Steps

1. Preflight:
```bash
pytest -q
python3 scripts/ci/validate_contracts.py
```
2. Recompute (official raw):
```bash
python3 scripts/pipeline/run_experiment_route.py --no-balance --skip-clone --workers 4
```
3. Coverage gate:
- `artifacts/experiments/pipeline/gold_coverage_summary.json` が成功
4. Publish report:
```bash
make report
```
5. Record:
- `tasks/todo.md` に実行日時・commit・KPIを追記

## Guardrails

- `final_summary.json` を公式SSOTとして扱う
- `aggregate_results.json` を公式KPIとして扱わない
- coverage fail 時は公開停止

## References

- `docs/PIPELINE_GUIDE.md`
- `docs/operations/RUNBOOK.md`

