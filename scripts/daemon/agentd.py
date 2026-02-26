#!/usr/bin/env python3
"""AgentRetrieve daemon: file-spool based worker for recurring project tasks."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "artifacts" / "agentd"
SPOOL = BASE / "spool"
PENDING = SPOOL / "pending"
IN_PROGRESS = SPOOL / "in_progress"
DONE = SPOOL / "done"
DEAD = SPOOL / "dead"
LOGS = BASE / "logs"
LOCK_FILE = BASE / "agentd.lock"

TASK_TYPE_COMMANDS = {
    "contract_harness": ["bash", "scripts/ci/run_contract_harness.sh"],
    "contract_harness_refresh": ["bash", "scripts/ci/run_contract_harness.sh", "--refresh"],
    "prepare_worktree": ["bash", "scripts/dev/prepare_worktree.sh"],
}

DEFAULT_POLL_SEC = 1.0
DEFAULT_MAX_BACKOFF_SEC = 5.0
DEFAULT_LEASE_SEC = 180.0

_STOP = False


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for d in (PENDING, IN_PROGRESS, DONE, DEAD, LOGS):
        d.mkdir(parents=True, exist_ok=True)


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock() -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            pid = -1
        if is_pid_alive(pid):
            raise SystemExit(f"agentd already running (pid={pid})")
        LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def release_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


def on_signal(*_: Any) -> None:
    global _STOP
    _STOP = True


def list_tasks(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime)


def load_task(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_task(path: Path, task: dict[str, Any]) -> None:
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")


def move_atomic(src: Path, dst_dir: Path) -> Path:
    dst = dst_dir / src.name
    src.replace(dst)
    return dst


def write_task_log(task_id: str, body: str) -> None:
    log_path = LOGS / f"{task_id}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(body)
        f.write("\n")


def sanitize_task(task: dict[str, Any]) -> dict[str, Any]:
    task.setdefault("version", "daemon_task.v1")
    task.setdefault("payload", {})
    task.setdefault("attempts", 0)
    task.setdefault("max_attempts", 3)
    task.setdefault("last_started_at_utc", None)
    task.setdefault("last_error", None)
    return task


def validate_task(task: dict[str, Any]) -> str | None:
    if task.get("version") != "daemon_task.v1":
        return "unsupported task version"
    if task.get("type") not in TASK_TYPE_COMMANDS:
        return f"unsupported task type: {task.get('type')}"
    try:
        attempts = int(task.get("attempts", 0))
        max_attempts = int(task.get("max_attempts", 3))
    except Exception:
        return "attempts/max_attempts must be integers"
    if attempts < 0:
        return "attempts must be >= 0"
    if max_attempts < 1:
        return "max_attempts must be >= 1"
    task_id = str(task.get("id", "")).strip()
    if not task_id:
        return "task id is required"
    return None


def reconcile_stuck(lease_sec: float) -> int:
    now = time.time()
    recovered = 0
    for path in list_tasks(IN_PROGRESS):
        age = now - path.stat().st_mtime
        if age <= lease_sec:
            continue
        recovered += 1
        move_atomic(path, PENDING)
    return recovered


def run_task(task: dict[str, Any]) -> tuple[int, str, str]:
    cmd = TASK_TYPE_COMMANDS[task["type"]]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    stdout = (result.stdout or "")[-12000:]
    stderr = (result.stderr or "")[-12000:]
    return result.returncode, stdout, stderr


def process_one_task() -> bool:
    pending = list_tasks(PENDING)
    if not pending:
        return False

    task_file = pending[0]
    inprog = move_atomic(task_file, IN_PROGRESS)
    try:
        task = sanitize_task(load_task(inprog))
    except Exception as exc:
        write_task_log(
            task_file.stem,
            f"[{now_utc()}] invalid JSON, moving to dead: {exc}",
        )
        move_atomic(inprog, DEAD)
        return True

    err = validate_task(task)
    if err:
        task["last_error"] = err
        save_task(inprog, task)
        write_task_log(task["id"], f"[{now_utc()}] validation error: {err}")
        move_atomic(inprog, DEAD)
        return True

    task["attempts"] = int(task["attempts"]) + 1
    task["last_started_at_utc"] = now_utc()
    save_task(inprog, task)

    rc, out, err_text = run_task(task)
    log_body = (
        f"[{now_utc()}] rc={rc} type={task['type']} attempts={task['attempts']}\n"
        f"--- stdout ---\n{out}\n"
        f"--- stderr ---\n{err_text}\n"
    )
    write_task_log(task["id"], log_body)

    if rc == 0:
        move_atomic(inprog, DONE)
        return True

    task["last_error"] = f"command failed with rc={rc}"
    save_task(inprog, task)
    if int(task["attempts"]) >= int(task["max_attempts"]):
        move_atomic(inprog, DEAD)
    else:
        move_atomic(inprog, PENDING)
    return True


def run_loop(poll_sec: float, max_backoff_sec: float, lease_sec: float, once: bool) -> int:
    backoff = poll_sec
    while not _STOP:
        recovered = reconcile_stuck(lease_sec)
        if recovered:
            print(f"[agentd] recovered_stuck={recovered}")

        worked = False
        while not _STOP:
            did = process_one_task()
            if not did:
                break
            worked = True
            backoff = poll_sec

        if once:
            break

        if worked:
            continue

        time.sleep(backoff)
        backoff = min(max_backoff_sec, backoff * 1.5)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AgentRetrieve spool daemon")
    p.add_argument("--poll-sec", type=float, default=DEFAULT_POLL_SEC)
    p.add_argument("--max-backoff-sec", type=float, default=DEFAULT_MAX_BACKOFF_SEC)
    p.add_argument("--lease-sec", type=float, default=DEFAULT_LEASE_SEC)
    p.add_argument(
        "--once",
        action="store_true",
        help="Process current queue then exit.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    acquire_lock()
    try:
        print("[agentd] started")
        return run_loop(args.poll_sec, args.max_backoff_sec, args.lease_sec, args.once)
    finally:
        release_lock()
        print("[agentd] stopped")


if __name__ == "__main__":
    sys.exit(main())
