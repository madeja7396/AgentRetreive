# Validation Matrix

更新日: 2026-03-01

| Area | Artifact | Validation Method | Exit Criteria | Status |
|---|---|---|---|---|
| Input Contract | DSL v1 schema | JSON Schema contract tests | 必須キー/型/制約違反が検出される | Done |
| Output Contract | Mini-JSON v1 | Golden tests + byte-limit tests | 上限超過時も schema 準拠で cursor 継続可能 | Done |
| Ranking | BM25 + boosts | Offline replay + deterministic tests | 同一入力で同一順位、score は 0-1000 整数 | Done |
| Evidence | `hit/rng/next[]` | Retrieval task replay | 次手が 1 回以内で確定する割合を測定可能 | Done |
| Index | build/update pipeline | Micro benchmark | build/update の時間・RSS・index size を記録 | Done |
| E2E Cost | Agent tasks | Tool-call trace analysis | Tool calls / stdout bytes / TTFC を比較可能 | Done |
| Baseline | rg/git grep/(参考)埋め込み系 | 同条件ベンチ比較 | 指標差分を再現可能な形で記録 | Done |
| Data Provenance | dataset manifest / run registry | Metadata completeness checks | 必須メタデータ欠損が 0 件 | Done |
| Reproducibility | cross-env rerun results | 2 環境での再実行比較 | 主要指標が許容誤差内に収まる | Done |
| Paper Traceability | claim-to-evidence mapping | 論文主張と実験 ID の照合 | 全主張が実験証跡にリンク済み | Done |

## 実行前チェック

- 固定コミット一覧が確定している
- ベンチ実行環境（CPU/RAM/OS）を記録している
- 計測スクリプトのバージョンを固定している
- dataset license と公開条件を確認している
- 再現許容誤差の定義を文書化している
