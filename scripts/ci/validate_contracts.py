#!/usr/bin/env python3
"""Validate JSON contracts used by AgentRetrieve planning/research docs."""

from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator


ROOT = pathlib.Path(__file__).resolve().parents[2]

SCHEMAS = {
    "query": ROOT / "docs/schemas/query.dsl.v1.schema.json",
    "result": ROOT / "docs/schemas/result.minijson.v1.schema.json",
    "dataset_manifest": ROOT / "docs/schemas/dataset_manifest.v1.schema.json",
    "experiment_run_record": ROOT / "docs/schemas/experiment_run_record.v1.schema.json",
}

SAMPLES = {
    "dataset_manifest": ROOT / "tasks/templates/dataset_manifest.json",
    "experiment_run_record": ROOT / "tasks/templates/experiment_run_record.json",
}

JSON_CHECK_PATHS = [
    ROOT / "docs/schemas",
    ROOT / "tasks/templates",
]


def load_json(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_json_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for base in JSON_CHECK_PATHS:
        files.extend(sorted(base.glob("*.json")))
    return files


def check_json_syntax() -> int:
    errors = 0
    for path in iter_json_files():
        try:
            load_json(path)
            print(f"[OK] json parse: {path.relative_to(ROOT)}")
        except Exception as exc:  # pragma: no cover - CI visibility over precision
            errors += 1
            print(f"[NG] json parse: {path.relative_to(ROOT)} -> {exc}")
    return errors


def check_required_files() -> int:
    errors = 0
    for path in list(SCHEMAS.values()) + list(SAMPLES.values()):
        if not path.exists():
            errors += 1
            print(f"[NG] missing required file: {path.relative_to(ROOT)}")
    return errors


def validate_samples() -> int:
    errors = 0
    for sample_key, sample_path in SAMPLES.items():
        schema_path = SCHEMAS[sample_key]
        schema = load_json(schema_path)
        sample = load_json(sample_path)
        validator = Draft202012Validator(schema)
        validation_errors = sorted(validator.iter_errors(sample), key=lambda e: e.path)
        if validation_errors:
            errors += len(validation_errors)
            print(
                f"[NG] schema validate: {sample_path.relative_to(ROOT)} "
                f"against {schema_path.relative_to(ROOT)}"
            )
            for err in validation_errors:
                path = "/".join(str(x) for x in err.path) or "<root>"
                print(f"  - {path}: {err.message}")
        else:
            print(
                f"[OK] schema validate: {sample_path.relative_to(ROOT)} "
                f"against {schema_path.relative_to(ROOT)}"
            )
    return errors


def main() -> int:
    total_errors = 0
    total_errors += check_required_files()
    total_errors += check_json_syntax()
    total_errors += validate_samples()

    if total_errors:
        print(f"[FAIL] contract validation failed with {total_errors} error(s).")
        return 1

    print("[PASS] all contract checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
