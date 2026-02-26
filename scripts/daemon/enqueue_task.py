#!/usr/bin/env python3
"""Enqueue project-scoped daemon tasks into artifacts/agentd/spool/pending."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PENDING = ROOT / "artifacts" / "agentd" / "spool" / "pending"
ALLOWED_TYPES = {
    "contract_harness",
    "contract_harness_refresh",
    "prepare_worktree",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enqueue a daemon task")
    p.add_argument(
        "--type",
        required=True,
        choices=sorted(ALLOWED_TYPES),
        help="Task type to execute",
    )
    p.add_argument(
        "--id",
        default=None,
        help="Optional task id (default: auto timestamp id)",
    )
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument(
        "--payload",
        default="{}",
        help="JSON object payload string",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    PENDING.mkdir(parents=True, exist_ok=True)

    if args.max_attempts < 1:
        raise SystemExit("--max-attempts must be >= 1")

    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--payload must be JSON object: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("--payload must be a JSON object")

    task_id = args.id or f"{args.type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    task = {
        "version": "daemon_task.v1",
        "id": task_id,
        "type": args.type,
        "attempts": 0,
        "max_attempts": args.max_attempts,
        "created_at_utc": now_utc(),
        "last_started_at_utc": None,
        "last_error": None,
        "payload": payload,
    }

    dst = PENDING / f"{task_id}.json"
    if dst.exists():
        raise SystemExit(f"task already exists: {dst}")
    tmp = dst.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(dst)
    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
