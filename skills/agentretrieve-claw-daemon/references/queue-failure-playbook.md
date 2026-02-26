# Queue Failure Playbook

## pending に積まれるが処理されない

- `agentd` が起動しているか確認
- `artifacts/agentd/agentd.lock` の stale lock を確認
- `bash scripts/daemon/run_agentd.sh --once` で単発実行して切り分け

## in_progress に残り続ける

- lease 超過で自動回収されるか確認（既定 180 秒）
- 長時間処理が必要なら `--lease-sec` を調整

## dead に落ちる

- `artifacts/agentd/logs/<task_id>.log` を確認
- `max_attempts` と `last_error` を確認
- 原因修正後に新規 task id で再投入

## してはいけない操作

- `in_progress` ファイルの手編集
- schema 未定義 task type の投入
- 任意シェル実行を task type に追加
