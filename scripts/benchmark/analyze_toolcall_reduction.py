#!/usr/bin/env python3
"""Estimate tool-call reduction versus generic grep-based workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPOS = ["ripgrep", "fd", "fzf", "curl", "fmt", "pytest", "cli"]


def _estimated_calls_for_generic_tool(rank: int | None, inspect_limit: int) -> int:
    # 1 call for grep/search + N calls for opening candidates until gold evidence.
    if rank is None:
        return 1 + inspect_limit
    return 1 + min(rank, inspect_limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze tool-call reduction from comparison artifacts.")
    parser.add_argument("--run-dir", required=True, help="Run directory with comparison_*.json")
    parser.add_argument("--inspect-limit", type=int, default=5, help="Max candidate files opened by baseline")
    parser.add_argument("-o", "--output", required=True, help="Output JSON")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    inspect_limit = max(1, args.inspect_limit)

    repo_rows: list[dict] = []
    all_agentretrieve_calls: list[int] = []
    all_ripgrep_calls: list[int] = []
    all_gitgrep_calls: list[int] = []

    for repo in REPOS:
        comp_path = run_dir / f"comparison_{repo}.json"
        if not comp_path.exists():
            continue
        data = json.loads(comp_path.read_text(encoding="utf-8"))
        comparisons = data.get("comparisons", [])
        ar_calls: list[int] = []
        rg_calls: list[int] = []
        gg_calls: list[int] = []

        for item in comparisons:
            ar_rank = None
            rg_rank = None
            gg_rank = None
            for r in item.get("results", []):
                tool = r.get("tool")
                if tool == "agentretrieve":
                    ar_rank = r.get("rank")
                elif tool == "ripgrep":
                    rg_rank = r.get("rank")
                elif tool == "git_grep":
                    gg_rank = r.get("rank")

            # AgentRetrieve returns structured evidence in one call.
            ar_calls.append(1)
            rg_calls.append(_estimated_calls_for_generic_tool(rg_rank, inspect_limit))
            gg_calls.append(_estimated_calls_for_generic_tool(gg_rank, inspect_limit))

        if not ar_calls:
            continue

        avg_ar = sum(ar_calls) / len(ar_calls)
        avg_rg = sum(rg_calls) / len(rg_calls)
        avg_gg = sum(gg_calls) / len(gg_calls)
        repo_rows.append(
            {
                "repo": repo,
                "tasks": len(ar_calls),
                "avg_calls_agentretrieve": avg_ar,
                "avg_calls_ripgrep_workflow": avg_rg,
                "avg_calls_gitgrep_workflow": avg_gg,
                "reduction_vs_ripgrep": 1.0 - (avg_ar / avg_rg if avg_rg else 1.0),
                "reduction_vs_gitgrep": 1.0 - (avg_ar / avg_gg if avg_gg else 1.0),
            }
        )
        all_agentretrieve_calls.extend(ar_calls)
        all_ripgrep_calls.extend(rg_calls)
        all_gitgrep_calls.extend(gg_calls)

    def avg(xs: list[int]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    avg_ar = avg(all_agentretrieve_calls)
    avg_rg = avg(all_ripgrep_calls)
    avg_gg = avg(all_gitgrep_calls)

    out = {
        "version": "toolcall_reduction.v1",
        "assumption": {
            "generic_tool_workflow": "1 search call + candidate file opens until gold or inspect limit",
            "inspect_limit": inspect_limit,
        },
        "by_repo": repo_rows,
        "overall": {
            "tasks": len(all_agentretrieve_calls),
            "avg_calls_agentretrieve": avg_ar,
            "avg_calls_ripgrep_workflow": avg_rg,
            "avg_calls_gitgrep_workflow": avg_gg,
            "reduction_vs_ripgrep": 1.0 - (avg_ar / avg_rg if avg_rg else 1.0),
            "reduction_vs_gitgrep": 1.0 - (avg_ar / avg_gg if avg_gg else 1.0),
        },
    }
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
