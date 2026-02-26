# Taskset v2.0 Evaluation Report

**Date**: 2026-02-26  
**Tasks**: 25 (5 repos × 5 tasks)  
**Design**: Stratified by difficulty (Easy/Medium/Hard) and type

## Results Summary

| Metric | Value |
|--------|-------|
| **Overall Recall** | 64.0% (16/25) |
| **Overall MRR** | 0.368 |
| **Easy Recall** | 90.0% (9/10) |
| **Medium Recall** | 50.0% (5/10) |
| **Hard Recall** | 40.0% (2/5) |

## By Difficulty

| Difficulty | Tasks | Recall | MRR | Analysis |
|------------|-------|--------|-----|----------|
| **Easy** | 10 | 90.0% | 0.52 | Good single-term performance |
| **Medium** | 10 | 50.0% | 0.32 | Multi-term queries challenging |
| **Hard** | 5 | 40.0% | 0.17 | Complex queries need improvement |

## By Task Type

| Type | Tasks | Recall | Notes |
|------|-------|--------|-------|
| **symbol_definition** | 10 | 90% | Best performance - unique names |
| **configuration** | 5 | 60% | Moderate - settings are identifiable |
| **error_handling** | 5 | 40% | Hard - error messages are generic |
| **usage_search** | 5 | 40% | Hard - requires context understanding |

## Key Findings

### 1. Single-term queries work well (Easy: 90% recall)
- Unique symbol names are easily found
- Indexing with identifier tokenization effective

### 2. Multi-term queries need improvement (Medium: 50% recall)
- Current AND logic too strict
- Should implement OR with boosting for partial matches

### 3. Proximity search required (Hard: 40% recall)
- Terms appearing together in context
- Current implementation lacks near/within constraint

### 4. File type matters
- Source code files (.rs, .go) easier than docs
- Tests and configs have varying difficulty

## Comparison with v1.0

| Aspect | v1.0 | v2.0 | Change |
|--------|------|------|--------|
| Total Tasks | 25 | 25 | - |
| Overall Recall | 96% | 64% | ↓ (harder tasks) |
| Source Files | 0% | 80% | ↑ (diversified) |
| Documentation | 76% | 20% | ↓ (balanced) |
| Difficulty Levels | None | 3 levels | ↑ (stratified) |

## Recommendations for v3.0

### 1. Query Relaxation (Medium difficulty)
```python
# Current: strict AND
must: ["term1", "term2"]  # Both required

# Proposed: soft AND with boosting
must: ["term1"],         # Primary term required
should: ["term2"],        # Secondary boosts score
min_match: 1              # At least 1 should match
```

### 2. Proximity Search (Hard difficulty)
```json
{
  "near": [
    {"terms": ["error", "message"], "window": 10},
    {"terms": ["if", "condition"], "window": 5}
  ]
}
```

### 3. Query Expansion
- Synonym handling (e.g., "config" ≈ "configuration")
- Stemming (e.g., "searching" → "search")

### 4. Task Balance
- Reduce symbol_definition to 30%
- Add more usage_search with explicit call patterns
- Include cross-file references

## Validated Design Principles

✓ **Stratified difficulty** reveals tool limitations  
✓ **Diverse file types** prevents overfitting  
✓ **Task type diversity** covers real use cases  
✗ **Query complexity** needs algorithm improvements  

## Next Steps

1. Implement query relaxation (OR + boost)
2. Add proximity search (near constraint)
3. Re-evaluate with improved engine
4. Target: Easy 95%, Medium 70%, Hard 50%
