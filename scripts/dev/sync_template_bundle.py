#!/usr/bin/env python3
"""Sync/check TEMPLATE bundle against source-of-truth assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _collect_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_file()], key=lambda p: p.name)


def _sync_dir(src_dir: Path, dst_dir: Path, *, check_only: bool) -> int:
    errors = 0
    src_files = _collect_files(src_dir)
    dst_files = _collect_files(dst_dir)
    src_names = {p.name for p in src_files}
    dst_names = {p.name for p in dst_files}

    missing = sorted(src_names - dst_names)
    extras = sorted(dst_names - src_names)
    for name in missing:
        if check_only:
            errors += 1
            print(f"[NG] missing template file: {dst_dir / name}")
        else:
            print(f"[SYNC] missing template file: {dst_dir / name}")
    for name in extras:
        if check_only:
            errors += 1
            print(f"[NG] unexpected template file: {dst_dir / name}")
        else:
            print(f"[WARN] unexpected template file: {dst_dir / name}")

    for src in src_files:
        dst = dst_dir / src.name
        if not dst.exists():
            if not check_only:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"[SYNC] {src} -> {dst}")
            continue
        if _sha256(src) != _sha256(dst):
            if check_only:
                errors += 1
                print(f"[NG] drift: {src} != {dst}")
            else:
                print(f"[SYNC] drift: {src} -> {dst}")
            if not check_only:
                shutil.copy2(src, dst)
                print(f"[SYNC] {src} -> {dst}")

    return errors


def _sync_file(src: Path, dst: Path, *, check_only: bool) -> int:
    if not src.exists():
        print(f"[NG] missing source file: {src}")
        return 1
    if not dst.exists():
        print(f"[NG] missing template file: {dst}")
        if not check_only:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"[SYNC] {src} -> {dst}")
            return 0
        return 1
    if _sha256(src) != _sha256(dst):
        print(f"[NG] drift: {src} != {dst}")
        if not check_only:
            shutil.copy2(src, dst)
            print(f"[SYNC] {src} -> {dst}")
            return 0
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync/check TEMPLATE bundle drift")
    parser.add_argument("--check", action="store_true", help="Check only (no writes)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    check_only = args.check
    errors = 0

    mappings = [
        (root / "docs/schemas", root / "TEMPLATE/contracts/schemas"),
        (root / "docs/contracts", root / "TEMPLATE/contracts/policies"),
        (root / "tasks/templates", root / "TEMPLATE/contracts/task_templates"),
        (root / "docs/operations", root / "TEMPLATE/operations"),
        (root / ".github/workflows", root / "TEMPLATE/workflows"),
    ]
    for src_dir, dst_dir in mappings:
        errors += _sync_dir(src_dir, dst_dir, check_only=check_only)

    errors += _sync_file(
        root / "configs/experiment_pipeline.yaml",
        root / "TEMPLATE/configs/experiment_pipeline.yaml",
        check_only=check_only,
    )

    if errors:
        print(f"[FAIL] template sync check failed: {errors} issue(s)")
        return 1
    print("[PASS] template bundle is synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
