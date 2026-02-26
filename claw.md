# Claw Technique Adaptation for AgentRetrieve

更新日: 2026-02-26

## 結論

「1回実行コマンドを外側デーモンで回し続ける」方式を、AgentRetrieve に安全制約付きで実装した。

## 実装済みコンポーネント

- 常駐ワーカー: `scripts/daemon/agentd.py`
- タスク投入: `scripts/daemon/enqueue_task.py`
- 起動ラッパー: `scripts/daemon/run_agentd.sh`
- 運用手順: `docs/operations/AGENTD.md`
- 契約: `docs/schemas/daemon_task.v1.schema.json`
- サンプル: `tasks/templates/daemon_task.v1.json`

## なぜこの形か

- DB不要で依存が増えない
- スプールの状態が目視できる
- 失敗・再試行・デッドレターが分離できる
- 実行可能タスクを固定列挙にして安全性を確保できる

## スプール

- `artifacts/agentd/spool/pending`
- `artifacts/agentd/spool/in_progress`
- `artifacts/agentd/spool/done`
- `artifacts/agentd/spool/dead`
- `artifacts/agentd/logs`

## 実行可能タスク型（固定）

- `contract_harness`
- `contract_harness_refresh`
- `prepare_worktree`

任意コマンド注入は不可。

## 典型運用

```bash
bash scripts/dev/prepare_worktree.sh
python3 scripts/daemon/enqueue_task.py --type contract_harness
bash scripts/daemon/run_agentd.sh --once
```

## リカバリ

- lease 超過の `in_progress` は `pending` へ回収
- `max_attempts` 超過で `dead` へ退避
- 詳細は `artifacts/agentd/logs/<task_id>.log`
