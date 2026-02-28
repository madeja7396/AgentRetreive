---
name: l2-ops-change-control
description: Standardize change intake, impact analysis, approval records, and rollback readiness.
---

# L2 Ops: Change Control

## When to use

- 重要変更（3ステップ以上、契約や運用に影響）
- KPI更新フローの変更
- 運用導線（Makefile/scripts/docs）の改修

## Steps

1. Intake:
- `tasks/todo.md` にチェック可能な項目を先に書く
2. Impact:
- 契約/データ/運用の影響範囲を明示
3. Execute:
- 最小差分で実装
4. Verify:
- `pytest -q`
- `python3 scripts/ci/validate_contracts.py`
5. Review record:
- `tasks/todo.md` のレビュー欄に記録
- 必要時 `tasks/lessons.md` 追記

## Guardrails

- レビュー記録のない重要変更を完了扱いにしない
- rollback 不可な変更を無審査で入れない
- 実装先行で契約更新を後回しにしない

## References

- `docs/operations/MAINTENANCE_GOVERNANCE.md`
- `tasks/implementation_donts.md`

