# Agentd Operations

更新日: 2026-02-26

## 目的

- AgentRetrieve を「タスク完了まで回し続ける」常駐運用を最小構成で実現する
- 実装安全性のため、実行可能タスクを固定列挙に制限する

## スプール構造

- `artifacts/agentd/spool/pending/`
- `artifacts/agentd/spool/in_progress/`
- `artifacts/agentd/spool/done/`
- `artifacts/agentd/spool/dead/`
- `artifacts/agentd/logs/`

## タスク型（固定）

- `contract_harness`
- `contract_harness_refresh`
- `prepare_worktree`

任意シェル実行は許可しない。

## 使い方

1. ディレクトリ初期化:

```bash
bash scripts/dev/prepare_worktree.sh
```

2. タスク投入:

```bash
python3 scripts/daemon/enqueue_task.py --type contract_harness
```

3. 単発実行（キューを捌いて終了）:

```bash
bash scripts/daemon/run_agentd.sh --once
```

4. 常駐実行:

```bash
bash scripts/daemon/run_agentd.sh
```

## 停滞回収

- `in_progress` のタスクが `lease_sec` を超えると `pending` に戻す
- デフォルト lease は 180 秒
- `--lease-sec` で上書き可能

## 失敗運用

- `attempts < max_attempts`: `pending` へ戻して再試行
- `attempts >= max_attempts`: `dead` へ移動
- ログは `artifacts/agentd/logs/<task_id>.log`
