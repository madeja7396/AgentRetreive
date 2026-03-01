# Validation Matrix

更新日: 2026-03-01

| Area | Artifact | Validation Method | Exit Criteria | Status |
|---|---|---|---|---|
| Input Contract | DSL v1 schema | JSON Schema contract tests | 必須キー/型/制約違反が検出される | Done |
| Output Contract | Mini-JSON v1 | Golden tests + byte-limit tests | 上限超過時も schema 準拠で cursor 継続可能 | Done |
| Output Contract v2 | Mini-JSON v2 (`cap_epoch`/`cap.index_fingerprint`) | JSON Schema + unit test (`test_output.py`) | v1互換を維持したまま freshness メタが検証可能 | Done |
| Capability Lifecycle | `ar cap verify` + `result.v2` | CLI unit test (`test_cli.py`) + handle検証スモーク | `valid/stale/not_found/mismatch` を機械判定できる | Done |
| Ranking | BM25 + boosts | Offline replay + deterministic tests | 同一入力で同一順位、score は 0-1000 整数 | Done |
| Evidence | `hit/rng/next[]` | Retrieval task replay | 次手が 1 回以内で確定する割合を測定可能 | Done |
| Index | build/update pipeline | Micro benchmark | build/update の時間・RSS・index size を記録 | Done |
| E2E Cost | Agent tasks | Tool-call trace analysis | Tool calls / stdout bytes / TTFC を比較可能 | Done |
| Baseline | rg/git grep/(参考)埋め込み系 | 同条件ベンチ比較 | 指標差分を再現可能な形で記録 | Done |
| Data Provenance | dataset manifest / run registry | Metadata completeness checks | 必須メタデータ欠損が 0 件 | Done |
| Reproducibility | cross-env rerun results | 2 環境での再実行比較 | 主要指標が許容誤差内に収まる | Done |
| Template Governance | `scripts/dev/sync_template_bundle.py` | `make template-sync-check` | TEMPLATE バンドルのドリフトを検出できる | Done |
| Paper Traceability | claim-to-evidence mapping | 論文主張と実験 ID の照合 | 全主張が実験証跡にリンク済み | Done |
| Symbol Extraction Coverage | `scripts/benchmark/export_symbol_support_metrics.py` | Index analysis per language | 言語別抽出カバレッジが可視化されている | Done |
| Figure Integrity | `scripts/ci/validate_figure_integrity.py` | CI mandatory check | 図表の手編集が検出され、再生成が強制される | Done |

## 実行前チェック

- 固定コミット一覧が確定している
- ベンチ実行環境（CPU/RAM/OS）を記録している
- 計測スクリプトのバージョンを固定している
- dataset license と公開条件を確認している
- 再現許容誤差の定義を文書化している
