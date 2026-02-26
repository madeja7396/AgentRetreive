#!/usr/bin/env python3
"""Validate JSON contracts used by AgentRetrieve planning/research docs."""

from __future__ import annotations

from collections import Counter
import json
import pathlib
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = pathlib.Path(__file__).resolve().parents[2]

SCHEMAS = {
    "query": ROOT / "docs/schemas/query.dsl.v1.schema.json",
    "result": ROOT / "docs/schemas/result.minijson.v1.schema.json",
    "dataset_manifest": ROOT / "docs/schemas/dataset_manifest.v1.schema.json",
    "experiment_run_record": ROOT / "docs/schemas/experiment_run_record.v1.schema.json",
    "corpus": ROOT / "docs/schemas/corpus.v1.schema.json",
    "baselines": ROOT / "docs/schemas/baselines.v1.schema.json",
    "run_constraints": ROOT / "docs/schemas/run_constraints.v1.schema.json",
    "taskset_entry": ROOT / "docs/schemas/taskset.v1.entry.schema.json",
    "contract_policy": ROOT / "docs/schemas/contract_policy.v1.schema.json",
    "daemon_task": ROOT / "docs/schemas/daemon_task.v1.schema.json",
}

SAMPLES = {
    "dataset_manifest": ROOT / "tasks/templates/dataset_manifest.json",
    "experiment_run_record": ROOT / "tasks/templates/experiment_run_record.json",
    "corpus": ROOT / "docs/benchmarks/corpus.v1.json",
    "baselines": ROOT / "docs/benchmarks/baselines.v1.json",
    "run_constraints": ROOT / "docs/benchmarks/run_constraints.v1.json",
    "contract_policy": ROOT / "docs/contracts/contract_policy.v1.json",
    "daemon_task": ROOT / "tasks/templates/daemon_task.v1.json",
}

JSON_CHECK_PATHS = [
    ROOT / "docs/schemas",
    ROOT / "tasks/templates",
    ROOT / "docs/benchmarks",
    ROOT / "docs/contracts",
]

JSONL_SAMPLES = {
    "taskset_entry": ROOT / "docs/benchmarks/taskset.v1.jsonl",
}


def load_json(path: pathlib.Path) -> Any:
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
    for path in list(SCHEMAS.values()) + list(SAMPLES.values()) + list(JSONL_SAMPLES.values()):
        if not path.exists():
            errors += 1
            print(f"[NG] missing required file: {path.relative_to(ROOT)}")
    return errors


def check_schema_definitions() -> int:
    errors = 0
    for key, path in SCHEMAS.items():
        try:
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            print(f"[OK] schema definition: {key} ({path.relative_to(ROOT)})")
        except SchemaError as exc:
            errors += 1
            print(f"[NG] schema definition: {path.relative_to(ROOT)} -> {exc.message}")
        except Exception as exc:  # pragma: no cover - CI visibility over precision
            errors += 1
            print(f"[NG] schema definition: {path.relative_to(ROOT)} -> {exc}")
    return errors


def validate_samples() -> int:
    errors = 0
    for sample_key, sample_path in SAMPLES.items():
        schema_path = SCHEMAS[sample_key]
        schema = load_json(schema_path)
        sample = load_json(sample_path)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
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


def validate_jsonl_samples() -> tuple[int, dict[str, list[dict[str, Any]]]]:
    errors = 0
    parsed: dict[str, list[dict[str, Any]]] = {}
    for schema_key, sample_path in JSONL_SAMPLES.items():
        schema_path = SCHEMAS[schema_key]
        schema = load_json(schema_path)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        line_errors = 0
        entries: list[dict[str, Any]] = []
        with sample_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception as exc:  # pragma: no cover - CI visibility over precision
                    line_errors += 1
                    print(
                        f"[NG] jsonl parse: {sample_path.relative_to(ROOT)}:{line_no} -> {exc}"
                    )
                    continue

                validation_errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
                if validation_errors:
                    line_errors += len(validation_errors)
                    for err in validation_errors:
                        path = "/".join(str(x) for x in err.path) or "<root>"
                        print(
                            f"[NG] schema validate: {sample_path.relative_to(ROOT)}:{line_no} "
                            f"{path}: {err.message}"
                        )
                else:
                    entries.append(obj)

        if line_errors:
            errors += line_errors
        else:
            parsed[schema_key] = entries
            print(
                f"[OK] schema validate: {sample_path.relative_to(ROOT)} "
                f"against {schema_path.relative_to(ROOT)}"
            )

    return errors, parsed


def _dup_values(items: list[str]) -> list[str]:
    counts = Counter(items)
    return sorted([v for v, c in counts.items() if c > 1])


def check_contract_invariants(taskset_entries: list[dict[str, Any]]) -> int:
    errors = 0

    policy = load_json(SAMPLES["contract_policy"])
    corpus = load_json(SAMPLES["corpus"])
    baselines = load_json(SAMPLES["baselines"])
    run_constraints = load_json(SAMPLES["run_constraints"])

    corpus_items = corpus["corpora"]
    baseline_items = baselines["baselines"]

    minimums = policy["minimums"]
    required_placeholders = policy["baseline_required_placeholders"]
    enforce_latency_order = policy["run_constraints"]["enforce_latency_order"]

    corpus_ids = [item["id"] for item in corpus_items]
    dup_corpus_ids = _dup_values(corpus_ids)
    if dup_corpus_ids:
        errors += 1
        print(f"[NG] invariant: duplicate corpus ids -> {dup_corpus_ids}")
    else:
        print("[OK] invariant: corpus ids are unique")

    if len(corpus_items) < minimums["corpora"]:
        errors += 1
        print(
            f"[NG] invariant: corpora count {len(corpus_items)} < minimum {minimums['corpora']}"
        )
    else:
        print(
            f"[OK] invariant: corpora count {len(corpus_items)} >= minimum {minimums['corpora']}"
        )

    tools = [item["tool"] for item in baseline_items]
    dup_tools = _dup_values(tools)
    if dup_tools:
        errors += 1
        print(f"[NG] invariant: duplicate baseline tools -> {dup_tools}")
    else:
        print("[OK] invariant: baseline tools are unique")

    if len(baseline_items) < minimums["baselines"]:
        errors += 1
        print(
            f"[NG] invariant: baseline count {len(baseline_items)} < minimum {minimums['baselines']}"
        )
    else:
        print(
            f"[OK] invariant: baseline count {len(baseline_items)} >= minimum "
            f"{minimums['baselines']}"
        )

    missing_placeholder_found = False
    for baseline in baseline_items:
        cmd_template = baseline["cmd_template"]
        missing_placeholders = [p for p in required_placeholders if p not in cmd_template]
        if missing_placeholders:
            errors += 1
            missing_placeholder_found = True
            print(
                f"[NG] invariant: baseline '{baseline['tool']}' missing placeholders "
                f"{missing_placeholders}"
            )

    if not missing_placeholder_found:
        print("[OK] invariant: all baseline templates include required placeholders")

    latency = run_constraints["latency_targets"]
    p50 = latency["p50_ms"]
    p95 = latency["p95_ms"]
    p99 = latency["p99_ms"]
    if enforce_latency_order and not (p50 <= p95 <= p99):
        errors += 1
        print(
            f"[NG] invariant: latency order broken (p50={p50}, p95={p95}, p99={p99})"
        )
    else:
        print("[OK] invariant: latency target ordering is valid")

    task_ids = [task["id"] for task in taskset_entries]
    dup_task_ids = _dup_values(task_ids)
    if dup_task_ids:
        errors += 1
        print(f"[NG] invariant: duplicate task ids -> {dup_task_ids}")
    else:
        print("[OK] invariant: task ids are unique")

    if len(taskset_entries) < minimums["tasks_total"]:
        errors += 1
        print(
            f"[NG] invariant: task count {len(taskset_entries)} < minimum "
            f"{minimums['tasks_total']}"
        )
    else:
        print(
            f"[OK] invariant: task count {len(taskset_entries)} >= minimum "
            f"{minimums['tasks_total']}"
        )

    task_counts = Counter(task["repo"] for task in taskset_entries)
    unknown_repos = sorted(set(task_counts.keys()) - set(corpus_ids))
    if unknown_repos:
        errors += 1
        print(f"[NG] invariant: taskset has repos not in corpus -> {unknown_repos}")
    else:
        print("[OK] invariant: all task repos are declared in corpus")

    for repo_id in corpus_ids:
        count = task_counts.get(repo_id, 0)
        if count < minimums["tasks_per_repo"]:
            errors += 1
            print(
                f"[NG] invariant: repo '{repo_id}' has {count} tasks < minimum "
                f"{minimums['tasks_per_repo']}"
            )

    for task in taskset_entries:
        must_len = len(task["query_dsl"]["must"])
        if must_len < minimums["must_terms_per_task"]:
            errors += 1
            print(
                f"[NG] invariant: task '{task['id']}' must terms {must_len} < minimum "
                f"{minimums['must_terms_per_task']}"
            )
        anchor_len = len(task["gold"]["anchor"])
        if anchor_len < minimums["anchor_min_length"]:
            errors += 1
            print(
                f"[NG] invariant: task '{task['id']}' anchor length {anchor_len} < minimum "
                f"{minimums['anchor_min_length']}"
            )

    if errors == 0:
        print("[OK] invariant: cross-file contract checks passed")

    return errors


def main() -> int:
    total_errors = 0
    total_errors += check_required_files()
    total_errors += check_schema_definitions()
    total_errors += check_json_syntax()
    total_errors += validate_samples()
    jsonl_errors, parsed_jsonl = validate_jsonl_samples()
    total_errors += jsonl_errors

    if jsonl_errors == 0 and "taskset_entry" in parsed_jsonl:
        total_errors += check_contract_invariants(parsed_jsonl["taskset_entry"])
    else:
        total_errors += 1
        print("[NG] invariant: skipped cross-file checks because JSONL validation failed")

    if total_errors:
        print(f"[FAIL] contract validation failed with {total_errors} error(s).")
        return 1

    print("[PASS] all contract checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
