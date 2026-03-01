# AgentRetrieve Release Notes

**Version**: Baseline v1.1  
**Release Date**: 2026-03-01  
**Status**: ✅ Complete

---

## Executive Summary

AgentRetrieveは、コード検索のための高性能検索エンジンです。Baseline v1.1では、7リポジトリ35タスクで**74.3%のRecall@1**と**0.381のMRR**を達成しました。

## Key Achievements

### 🎯 Performance
- **Recall@1**: 74.3% (26/35 tasks found)
- **MRR**: 0.381
- **Avg Latency**: 0.75ms (target: <2.0ms ✅)
- **Repositories**: 7 (Rust, Go, C, C++, Python)
- **Tasks**: 35 (easy: 14, medium: 14, hard: 7)

### 🌍 Multi-Language Support
Baseline v1.1 covers 5 languages with additional 4 languages indexed:

| Language | Repositories | Status |
|----------|--------------|--------|
| Rust | fd, ripgrep | ✅ Evaluated |
| Go | fzf | ✅ Evaluated |
| C | curl | ✅ Evaluated |
| C++ | fmt | ✅ Evaluated |
| Python | pytest, cli | ✅ Evaluated |
| JavaScript | axios | ⏳ Indexed |
| Haskell | cabal | ⏳ Indexed |
| Elixir | elixir | ⏳ Indexed |
| C# | aspnetcore | ⏳ Indexed |

**Total**: 11 repositories, 15,374 documents

### 📊 Scalability
Verified across repository scales:
- Small: 24-75 docs (fd, fmt)
- Medium: 257-990 docs (curl, cli, pytest)
- Large: 10,417 docs (aspnetcore)

**Key Finding**: Index size scales sub-linearly with document count.

## Experiment Pipeline

### Automated Workflow
```bash
make experiment-fast        # ~3 minutes
make experiment-daily-full  # ~10 minutes
make release-ready          # Full validation
```

### Quality Gates (5 Steps)
1. ✅ Contracts (68 checks)
2. ✅ Pytest (27 tests)
3. ✅ Figures (8 types)
4. ✅ Figure Integrity (0 errors)
5. ✅ Template Sync

### Run Records
- `run_20260301_144348_route` (Baseline v1.1)
- Registry: `artifacts/experiments/run_registry.v2.jsonl`

## Paper Artifacts

8 figure types generated:
1. retrieval_recall_by_repo
2. retrieval_latency_by_repo
3. tool_call_comparison
4. micro_benchmark_summary
5. ablation_study
6. stability_analysis
7. cross_env_reproducibility
8. symbol_extraction_coverage

All available at: `artifacts/papers/figures/`

## Technical Highlights

### Innovation: Short-Circuit Execution
- Fingerprint-based change detection
- Skips redundant index rebuilds
- Maintains reproducibility

### Symbol Extraction
- Language-aware block extraction
- AST-based for Python
- Brace-based for C-family
- Fallback to blank-line heuristic

### Query Engine
- BM25 scoring (k1=1.2, b=0.75 default)
- DSL with near constraints
- Cursor pagination
- Deterministic ordering

## Limitations & Future Work

### Current Limitations
- Parameter tuning alone cannot exceed 75% recall
- 4 languages await evaluation (JavaScript, Haskell, Elixir, C#)
- Large repo (10k+ docs) performance not fully optimized

### Future Directions
1. **Short-term**: Maintain Baseline v1.1 (74.3%)
2. **Medium-term**: Symbol extraction improvements (+5-10%)
3. **Long-term**: ML-based ranking integration

## Documentation

Key documents:
- `docs/SSOT.md` - Single source of truth
- `docs/research/sprint_summary_8_14.md` - Experiment summary
- `docs/benchmarks/results.latest.json` - Latest metrics
- `docs/benchmarks/multilang_analysis.v1.json` - Language coverage
- `docs/benchmarks/scale_analysis.v1.json` - Scalability data

## Validation

All quality gates passing:
```
contracts:      PASS (68 checks)
pytest:         PASS (27 tests)
figures:        PASS (8 generated)
integrity:      PASS (0 errors)
template-sync:  PASS
```

## Contributors

- Core Development: AgentRetrieve Team
- Experiment Design: Sprint 8-16
- Baseline v1.1: run_20260301_144348_route

---

**Status**: Ready for publication 🎉
