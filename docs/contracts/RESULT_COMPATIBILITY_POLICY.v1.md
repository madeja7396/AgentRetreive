# Result Compatibility Policy v1 (v1/v2/v3)

## Scope
This policy defines coexistence and migration rules for AgentRetrieve result payload versions:
- `result.v1`
- `result.v2`
- `result.v3`

## Version Status
- `v1`: Stable legacy format for existing Python integrations.
- `v2`: Stable capability-preserving extension of v1.
- `v3`: Current Rust-first format with compact handles and proof envelope.

## Compatibility Matrix
- `v1 -> v2`: Forward-compatible by adding capability metadata fields.
- `v2 -> v1`: Backward-compatible by dropping v2-only capability freshness fields.
- `v3 -> v2`: Adapter-required (field shape changed: `id`/`proof.bounds[]`/`rng[]`).
- `v3 -> v1`: Adapter-required via v2 downgrade then v1 projection.

## Contract Rules
1. Do not remove fields from an existing version schema.
2. Additive changes only inside a version line (new optional fields).
3. Breaking shape changes must introduce a new version id.
4. All versions must preserve deterministic ordering semantics.
5. `proof.digest` and `proof.bounds` are mandatory in v3.

## Downgrade Guidance (v3 -> v2)
- `id` -> derive `doc_id` / `span_id` in adapter layer.
- `proof.digest` -> `digest`
- `proof.bounds[0|1]` -> `bounds.start` / `bounds.end`
- `rng[0|1]` -> `rng.from` / `rng.to`
- Preserve `s`, `h`, `next`, and `path` as-is where possible.

## Operational Notes
- CI validates schema definitions for all active versions.
- New tool integrations should prefer `v3`.
- Existing v1/v2 consumers remain supported until explicit deprecation notice.
