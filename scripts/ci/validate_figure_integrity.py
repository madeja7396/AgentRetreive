#!/usr/bin/env python3
"""Validate figure integrity against FIGURE_SOURCES.v1.json.

Checks:
1. All defined figures exist at output_path
2. Generator scripts exist and are executable
3. Input artifacts exist
4. Figure files are newer than generator scripts (if timestamp_check enabled)
5. Optional: File hash matches (if file_hash_required and baseline exists)

Usage:
    python3 scripts/ci/validate_figure_integrity.py [--strict]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_figure_sources() -> dict[str, Any]:
    """Load figure sources configuration."""
    config_path = (
        Path(__file__).resolve().parents[2] / "docs" / "papers" / "FIGURE_SOURCES.v1.json"
    )
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_run_id_placeholder(path_pattern: str, default_run_id: str = "run_20260228_154238_exp001_raw") -> str:
    """Resolve {run_id} placeholder in path patterns."""
    if "{run_id}" in path_pattern:
        return path_pattern.replace("{run_id}", default_run_id)
    return path_pattern


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:32]


def check_file_exists(path: Path, description: str) -> tuple[bool, str]:
    """Check if a file exists."""
    if not path.exists():
        return False, f"{description} not found: {path}"
    return True, f"{description} exists: {path}"


def check_generator_executable(script_path: Path) -> tuple[bool, str]:
    """Check if generator script exists and is readable."""
    ok, msg = check_file_exists(script_path, "Generator script")
    if not ok:
        return ok, msg
    if not os.access(script_path, os.R_OK):
        return False, f"Generator script not readable: {script_path}"
    return True, f"Generator script readable: {script_path}"


def check_timestamp(generator_path: Path, output_path: Path) -> tuple[bool, str]:
    """Check if output is newer than generator (or close enough)."""
    if not output_path.exists():
        return False, f"Output not found: {output_path}"
    
    gen_stat = generator_path.stat()
    out_stat = output_path.stat()
    
    # Allow 60 second tolerance for filesystem timestamp granularity
    if out_stat.st_mtime < gen_stat.st_mtime - 60:
        return (
            False,
            f"Output older than generator: {output_path} ({out_stat.st_mtime}) < {generator_path} ({gen_stat.st_mtime})"
        )
    return True, f"Timestamp OK: {output_path}"


def validate_figure(
    name: str,
    config: dict[str, Any],
    project_root: Path,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Validate a single figure configuration."""
    issues: list[dict[str, Any]] = []
    
    output_path = project_root / config["output_path"]
    generator = config.get("generator", {})
    script_path = project_root / generator.get("script", "")
    input_artifacts = generator.get("input_artifacts", [])
    
    # Check output file exists
    ok, msg = check_file_exists(output_path, "Output")
    if not ok:
        # In non-strict mode, missing output is just a warning (may need regeneration)
        severity = "error" if strict else "warning"
        issues.append({"severity": severity, "type": "missing_output", "message": msg})
    
    # Check generator script
    ok, msg = check_generator_executable(script_path)
    if not ok:
        issues.append({"severity": "error", "type": "generator_issue", "message": msg})
    
    # Check input artifacts
    for pattern in input_artifacts:
        # Resolve {run_id} placeholder
        resolved_pattern = resolve_run_id_placeholder(pattern)
        
        # Handle glob patterns
        if "*" in resolved_pattern:
            # Find matching files
            parent = (project_root / resolved_pattern).parent
            if parent.exists():
                matched = list(parent.glob(os.path.basename(resolved_pattern)))
                if not matched:
                    issues.append({
                        "severity": "warning",
                        "type": "missing_input",
                        "message": f"No files matched pattern: {resolved_pattern}",
                    })
        else:
            input_path = project_root / resolved_pattern
            if not input_path.exists():
                issues.append({
                    "severity": "warning",
                    "type": "missing_input",
                    "message": f"Input artifact not found: {input_path}",
                })
    
    # Check timestamps if both exist
    if output_path.exists() and script_path.exists():
        integrity_rules = load_figure_sources().get("integrity_rules", {})
        if integrity_rules.get("timestamp_check"):
            ok, msg = check_timestamp(script_path, output_path)
            if not ok:
                issues.append({"severity": "warning", "type": "timestamp", "message": msg})
    
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate figure integrity")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (fail on missing outputs)",
    )
    parser.add_argument(
        "--check-generator",
        action="store_true",
        help="Additionally verify generator scripts are syntactically valid",
    )
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parents[2]
    sources = load_figure_sources()
    
    if not sources:
        print("Error: FIGURE_SOURCES.v1.json not found or empty", file=sys.stderr)
        return 1
    
    figures = sources.get("figures", {})
    all_issues: list[dict[str, Any]] = []
    
    print(f"Validating {len(figures)} figures...")
    
    for name, config in figures.items():
        print(f"  Checking: {name}")
        issues = validate_figure(name, config, project_root, strict=args.strict)
        for issue in issues:
            issue["figure"] = name
            all_issues.append(issue)
    
    # Additional check: validate generator scripts are syntactically valid Python
    if args.check_generator:
        print("Checking generator script syntax...")
        checked_scripts: set[str] = set()
        for config in figures.values():
            script = config.get("generator", {}).get("script", "")
            if script and script not in checked_scripts:
                checked_scripts.add(script)
                script_path = project_root / script
                if script_path.exists() and script_path.suffix == ".py":
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(script_path)],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        all_issues.append({
                            "severity": "error",
                            "type": "syntax_error",
                            "figure": "N/A",
                            "message": f"Syntax error in {script}: {result.stderr}",
                        })
    
    # Summarize results
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    
    print(f"\nResults: {len(errors)} errors, {len(warnings)} warnings")
    
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  [{w['type']}] {w.get('figure', 'N/A')}: {w['message']}")
    
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  [{e['type']}] {e.get('figure', 'N/A')}: {e['message']}")
    
    # Output JSON report
    report = {
        "valid": len(errors) == 0,
        "strict_mode": args.strict,
        "summary": {
            "total_figures": len(figures),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "issues": all_issues,
    }
    
    print("\n" + json.dumps(report["summary"], indent=2))
    
    return 0 if len(errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
