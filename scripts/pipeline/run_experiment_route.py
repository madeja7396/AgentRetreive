#!/usr/bin/env python3
"""Experiment execution route: preflight -> auto-adapt -> final evaluation."""

from __future__ import annotations

import argparse
import shutil
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def _generate_run_id(profile: str) -> str:
    """Generate a unique run_id based on timestamp."""
    from datetime import timezone

    now = datetime.now(timezone.utc)
    suffix = "route_fast" if profile == "fast" else "route"
    return f"run_{now.strftime('%Y%m%d_%H%M%S')}_{suffix}"


def _run(cmd: list[str], cwd: Path, dry_run: bool) -> None:
    rendered = " ".join(shlex.quote(part) for part in cmd)
    print(f"+ {rendered}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _resolve_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _build_raw_eval_config(
    root: Path,
    source_config_path: Path,
    output_path: Path,
    dry_run: bool,
) -> Path:
    if dry_run:
        return output_path

    config = yaml.safe_load(source_config_path.read_text(encoding="utf-8"))
    repos = config.get("repositories", [])
    rewritten: list[dict] = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        repo_id = repo.get("id")
        if not isinstance(repo_id, str) or not repo_id:
            continue
        updated = dict(repo)
        updated["index"] = f"artifacts/datasets/{repo_id}.index.json"
        updated["source"] = f"artifacts/datasets/raw/{repo_id}"
        rewritten.append(updated)
    config["repositories"] = rewritten

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return output_path


def _load_profile_settings(root: Path, profile_config: str, profile: str) -> dict[str, Any]:
    config_path = _resolve_path(root, profile_config)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid profile config: {config_path}")
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        raise RuntimeError(f"Invalid profile set in: {config_path}")
    settings = profiles.get(profile)
    if not isinstance(settings, dict):
        raise RuntimeError(f"Profile not found: {profile} ({config_path})")
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-command route to reach experiment outputs.",
    )
    parser.add_argument(
        "--profile",
        choices=["full", "fast"],
        default="full",
        help="Execution profile. fast uses reduced scope for quick iterations.",
    )
    parser.add_argument(
        "--profile-config",
        default="configs/experiment_profiles.v1.yaml",
        help="Profile definition YAML path.",
    )
    parser.add_argument("--repos", default="", help="Comma-separated repository IDs")
    parser.add_argument(
        "--engine",
        choices=["py", "rust"],
        default=None,
        help="Retrieval backend engine",
    )
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
        default=None,
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
        "--grid-profile",
        choices=["full", "fast"],
        default="",
        help="Grid profile passed to run_corpus_auto_adapt and run_full_pipeline.",
    )
    parser.add_argument(
        "--search-cache-dir",
        default="",
        help="Search cache directory passed to run_corpus_auto_adapt.",
    )
    parser.add_argument(
        "--state-file",
        default="",
        help="State file path passed to run_corpus_auto_adapt.",
    )
    parser.add_argument("--force-clone", action="store_true", help="Pass through to auto-adapt")
    parser.add_argument("--force-index", action="store_true", help="Pass through to auto-adapt")
    parser.add_argument("--force-symbol-fit", action="store_true", help="Pass through to auto-adapt")
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
        "--skip-gold-coverage",
        action="store_true",
        help="Skip gold coverage validation before final evaluation",
    )
    parser.add_argument(
        "--final-eval-as-is",
        action="store_true",
        help="Use final config as-is without forcing raw index/source paths",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print route commands without execution",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional run_id. If not set, auto-generated from timestamp.",
    )
    parser.add_argument(
        "--skip-run-record",
        action="store_true",
        help="Skip run_record generation (default: auto-generate after final evaluation).",
    )
    parser.add_argument(
        "--run-record-v2",
        action="store_true",
        default=True,
        help="Generate run_record v2 (default: True).",
    )
    args = parser.parse_args()

    default_output_dir = "artifacts/experiments/pipeline"
    default_generated_config = "artifacts/experiments/pipeline/generated_experiment_pipeline.auto.yaml"

    root = Path(__file__).resolve().parents[2]
    profile_settings = _load_profile_settings(
        root=root,
        profile_config=args.profile_config,
        profile=args.profile,
    )

    if args.output_dir == default_output_dir:
        args.output_dir = str(profile_settings.get("output_dir", args.output_dir))
    if args.generated_config == default_generated_config:
        args.generated_config = str(profile_settings.get("generated_config", args.generated_config))
    if not args.repos:
        args.repos = str(profile_settings.get("repos", args.repos))
    if args.no_balance is None:
        args.no_balance = bool(profile_settings.get("no_balance", False))
    if not args.grid_profile:
        args.grid_profile = str(profile_settings.get("grid_profile", "full"))
    if not args.state_file:
        args.state_file = str(profile_settings.get("state_file", ""))
    if not args.search_cache_dir:
        args.search_cache_dir = str(profile_settings.get("search_cache_dir", ""))
    if not args.engine:
        args.engine = str(profile_settings.get("engine_backend", "py"))

    runs_root = str(profile_settings.get("runs_root", "artifacts/experiments/runs"))
    registry_root = str(profile_settings.get("registry_root", "artifacts/experiments"))

    output_dir = str((root / args.output_dir).resolve())
    generated_config = str((root / args.generated_config).resolve())

    print("=" * 80)
    print("EXPERIMENT ROUTE")
    print("=" * 80)
    print(f"profile: {args.profile}")
    print(f"output_dir: {output_dir}")
    print(f"generated_config: {generated_config}")
    print(f"repos: {args.repos or '(taskset default)'}")
    print(f"index_all: {args.index_all}")
    print(f"engine: {args.engine}")
    print(f"no_balance: {args.no_balance}")
    print(f"grid_profile: {args.grid_profile}")
    if args.state_file:
        print(f"state_file: {str((root / args.state_file).resolve())}")
    if args.search_cache_dir:
        print(f"search_cache_dir: {str((root / args.search_cache_dir).resolve())}")
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
            "--grid-profile",
            args.grid_profile,
            "--engine",
            args.engine,
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
        if args.search_cache_dir:
            auto_cmd.extend(["--search-cache-dir", args.search_cache_dir])
        if args.state_file:
            auto_cmd.extend(["--state-file", args.state_file])
        if args.force_clone:
            auto_cmd.append("--force-clone")
        if args.force_index:
            auto_cmd.append("--force-index")
        if args.force_symbol_fit:
            auto_cmd.append("--force-symbol-fit")
        _run(auto_cmd, cwd=root, dry_run=args.dry_run)
    else:
        print("[skip] auto-adapt")

    preferred_config = args.final_config or args.generated_config
    preferred_config_path = _resolve_path(root, preferred_config)
    if args.final_config:
        final_config = args.final_config
    elif preferred_config_path.exists():
        final_config = args.generated_config
    else:
        final_config = "configs/experiment_pipeline.yaml"
    final_config_path = _resolve_path(root, final_config)

    if not args.final_eval_as_is:
        raw_eval_config_path = _resolve_path(
            root, f"{args.output_dir}/generated_experiment_pipeline.final_raw.yaml"
        )
        final_eval_config_path = _build_raw_eval_config(
            root=root,
            source_config_path=final_config_path,
            output_path=raw_eval_config_path,
            dry_run=args.dry_run,
        )
        final_eval_config = str(final_eval_config_path.relative_to(root)).replace("\\", "/")
    else:
        final_eval_config = final_config

    if not args.skip_final_eval:
        if not args.skip_gold_coverage:
            _run(
                [
                    "python3",
                    "scripts/pipeline/check_gold_coverage.py",
                    "--config",
                    final_eval_config,
                    "--output",
                    f"{args.output_dir}/gold_coverage_summary.json",
                ],
                cwd=root,
                dry_run=args.dry_run,
            )
        else:
            print("[skip] gold-coverage")

    if not args.skip_final_eval:
        _run(
            [
                "python3",
                "scripts/pipeline/run_final_evaluation.py",
                "-c",
                final_eval_config,
                "-o",
                args.output_dir,
                "--engine",
                args.engine,
            ],
            cwd=root,
            dry_run=args.dry_run,
        )
    else:
        print("[skip] final-eval")

    # Determine run_id (auto-generate if not provided)
    run_id = args.run_id
    if not run_id and not args.skip_run_record:
        run_id = _generate_run_id(args.profile)
        print(f"[auto-generated run_id: {run_id}]")

    if run_id and not args.skip_run_record:
        # Create run directory and copy artifacts
        run_dir = root / runs_root.lstrip("./") / run_id
        output_path = Path(output_dir)
        if not args.dry_run:
            run_dir.mkdir(parents=True, exist_ok=True)
            print(f"[run_dir created: {run_dir}]")
            # Copy essential artifacts to run_dir
            artifacts_to_copy = [
                (output_path / "final_summary.json", "final_summary.json"),
                (output_path / "aggregate_results.json", "aggregate_results.json"),
                (output_path / "auto_adapt_summary.json", "auto_adapt_summary.json"),
                (output_path / "gold_coverage_summary.json", "gold_coverage_summary.json"),
                (output_path / "symbol_support_summary.json", "symbol_support_summary.json"),
            ]
            for src, dst_name in artifacts_to_copy:
                if src.exists():
                    shutil.copy2(src, run_dir / dst_name)
                    print(f"  copied: {src.name} -> {dst_name}")

        record_cmd = [
            "python3",
            "scripts/pipeline/generate_run_record.py",
            "--run-id",
            run_id,
            "--config-path",
            final_eval_config,
            "--runs-root",
            runs_root,
            "--registry-root",
            registry_root,
            "--create-run-dir",
        ]
        if args.run_record_v2:
            record_cmd.append("--write-v2")
        _run(record_cmd, cwd=root, dry_run=args.dry_run)
    else:
        print("[skip] run-record")

    # Generate symbol extraction support metrics if index exists
    if not args.dry_run and not args.skip_final_eval:
        # Find first index file to analyze
        index_dir = root / "artifacts" / "datasets"
        if index_dir.exists():
            index_files = list(index_dir.glob("*.index.json"))
            if index_files:
                print("[symbol extraction metrics]")
                _run(
                    [
                        "python3",
                        "scripts/benchmark/export_symbol_support_metrics.py",
                        "--index",
                        str(index_files[0]),
                        "--output",
                        f"{output_dir}/symbol_support_summary.json",
                    ],
                    cwd=root,
                    dry_run=args.dry_run,
                )

    print("=" * 80)
    print("ROUTE COMPLETE")
    print("=" * 80)
    if run_id:
        print(f"run_id: {run_id}")
    print(f"summary: {output_dir}/final_summary.json")
    print(f"gold-coverage: {output_dir}/gold_coverage_summary.json")
    print(f"adapt-summary: {output_dir}/auto_adapt_summary.json")
    print(f"search-aggregate: {output_dir}/aggregate_results.json")
    print(f"symbol-support: {output_dir}/symbol_support_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
