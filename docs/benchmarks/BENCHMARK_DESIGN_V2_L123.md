# Benchmark Design v2 (L1/L2/L3)

## Goal
Define a stable benchmark taxonomy for Program R1 that separates lexical retrieval from symbol-aware and compositional retrieval.

## Tier Definitions
- `L1 Keyword`: lexical-only intent (`must/should/not`) without explicit symbol dependency.
- `L2 Symbol`: query requires symbol resolution (`symbol` field is non-empty).
- `L3 Compositional`: query includes structural coupling (`near`) or combined constraints (`must+should+symbol`).

## Assignment Rules
1. If `near` is present and non-empty -> `L3`.
2. Else if `symbol` is present and non-empty -> `L2`.
3. Else -> `L1`.

## Metrics by Tier
- Retrieval: Recall@10, MRR@10, latency(ms).
- Stability: variance across repeated runs.
- Coverage: number of repositories and languages represented in each tier.

## Operational Artifact
- Tier manifest output: `artifacts/experiments/benchmark_tiers.v2.json`
- Generator script: `scripts/benchmark/build_l123_task_views.py`

## Notes
- Tiering is deterministic from task DSL.
- Existing taskset is reused; no task id rewriting is required.
