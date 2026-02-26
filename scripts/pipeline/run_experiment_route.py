#!/usr/bin/env python3
"""Experiment execution route: preflight -> auto-adapt -> final evaluation."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path, dry_run: bool) -> None:
    rendered = " ".join(shlex.quote(part) for part in cmd)
    print(f"+ {rendered}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-command route to reach experiment outputs.",
    )
    parser.add_argument("--repos", default="", help="Comma-separated repository IDs")
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Worker count for parameter adaptation",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/experiments/pipeline",
        help="Output directory for experiment artifacts",
    )
    parser.add_argument(
        "--generated-config",
        default="artifacts/experiments/pipeline/generated_experiment_pipeline.auto.yaml",
        help="Generated config path used by auto-adapt",
    )
    parser.add_argument(
        "--final-config",
        default="",
        help="Optional config path for final evaluation. If empty, generated-config is preferred.",
    )
    parser.add_argument(
        "--index-all",
        action="store_true",
        help="Run auto-adapt over all corpora in manifest",
    )
    parser.add_argument(
        "--allow-missing-major-languages",
        action="store_true",
        help="Pass through to auto-adapt",
    )
    parser.add_argument(
        "--no-balance",
        action="store_true",
        help="Disable fairness balancing in auto-adapt",
    )
    parser.add_argument("--skip-clone", action="store_true", help="Pass through to auto-adapt")
    parser.add_argument("--skip-index", action="store_true", help="Pass through to auto-adapt")
    parser.add_argument(
        "--skip-symbol-fit",
        action="store_true",
        help="Pass through to auto-adapt",
    )
    parser.add_argument(
        "--skip-parameter-search",
        action="store_true",
        help="Pass through to auto-adapt",
    )
    parser.add_argument(
        "--skip-contracts",
        action="store_true",
        help="Skip contract validation preflight",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest preflight")
    parser.add_argument(
        "--skip-auto-adapt",
        action="store_true",
        help="Skip auto-adapt stage",
    )
    parser.add_argument(
        "--skip-final-eval",
        action="store_true",
        help="Skip final evaluation stage",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print route commands without execution",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = str((root / args.output_dir).resolve())
    generated_config = str((root / args.generated_config).resolve())

    print("=" * 80)
    print("EXPERIMENT ROUTE")
    print("=" * 80)
    print(f"output_dir: {output_dir}")
    print(f"generated_config: {generated_config}")
    print(f"repos: {args.repos or '(taskset default)'}")
    print(f"index_all: {args.index_all}")
    print(f"dry_run: {args.dry_run}")

    if not args.skip_contracts:
        _run(["python3", "scripts/ci/validate_contracts.py"], cwd=root, dry_run=args.dry_run)
    else:
        print("[skip] contracts")

    if not args.skip_tests:
        _run(["pytest", "-q"], cwd=root, dry_run=args.dry_run)
    else:
        print("[skip] tests")

    if not args.skip_auto_adapt:
        auto_cmd = [
            "python3",
            "scripts/pipeline/run_corpus_auto_adapt.py",
            "--workers",
            str(args.workers),
            "--output-dir",
            args.output_dir,
            "--generated-config",
            args.generated_config,
        ]
        if args.repos:
            auto_cmd.extend(["--repos", args.repos])
        if args.index_all:
            auto_cmd.append("--index-all")
        if args.allow_missing_major_languages:
            auto_cmd.append("--allow-missing-major-languages")
        if args.no_balance:
            auto_cmd.append("--no-balance")
        if args.skip_clone:
            auto_cmd.append("--skip-clone")
        if args.skip_index:
            auto_cmd.append("--skip-index")
        if args.skip_symbol_fit:
            auto_cmd.append("--skip-symbol-fit")
        if args.skip_parameter_search:
            auto_cmd.append("--skip-parameter-search")
        _run(auto_cmd, cwd=root, dry_run=args.dry_run)
    else:
        print("[skip] auto-adapt")

    if not args.skip_final_eval:
        preferred_config = args.final_config or args.generated_config
        preferred_config_path = root / preferred_config
        if args.final_config:
            final_config = args.final_config
        elif preferred_config_path.exists():
            final_config = args.generated_config
        else:
            final_config = "configs/experiment_pipeline.yaml"

        _run(
            [
                "python3",
                "scripts/pipeline/run_final_evaluation.py",
                "-c",
                final_config,
                "-o",
                args.output_dir,
            ],
            cwd=root,
            dry_run=args.dry_run,
        )
    else:
        print("[skip] final-eval")

    print("=" * 80)
    print("ROUTE COMPLETE")
    print("=" * 80)
    print(f"summary: {output_dir}/final_summary.json")
    print(f"adapt-summary: {output_dir}/auto_adapt_summary.json")
    print(f"search-aggregate: {output_dir}/aggregate_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
