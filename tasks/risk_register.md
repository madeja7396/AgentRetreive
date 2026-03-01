# Risk Register

更新日: 2026-03-01

| ID | Risk | Impact | Probability | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R-001 | DSL が広がりすぎ、MVP で実装負荷が肥大化する | High | Medium | v1 は必須キーに限定し、追加要件は拡張キーへ分離 | core_quality | Mitigated |
| R-002 | 出力 bytes 上限を守ると必要根拠が欠落する | High | Medium | `max_bytes` 内で `next[]` を優先残存し、再取得導線を保証 | core_quality | Mitigated |
| R-003 | symbol 抽出の言語差で検索品質が偏る | Medium | High | `configs/symbol_extraction_support.v1.json` で言語別モードを明示し、`export_symbol_support_metrics.py` で定例監視 | core_quality | Mitigated |
| R-004 | benchmark データセットの正解ラベル作成コストが高い | Medium | Medium | 難易度別に段階化し、まず小規模固定セットで開始 | program_office | Mitigated |
| R-005 | 決定性要件（同一入力同一出力）が崩れる | High | Medium | 並び順規則・同点規則・乱数禁止を contract test 化 | core_quality | Mitigated |
| R-006 | `span_id` が index 更新で不整合になる | High | Medium | Invalidate First を採用し、`cap verify`（doc/span/digest/epoch）で機械判定する | core_quality | Mitigated |
| R-007 | 実験ログ欠損で論文主張を遡れない | High | Medium | run registry への記録を CI チェックで必須化 | ops_governance | Mitigated |
| R-008 | 環境差異で主要結果が再現しない | High | Medium | `run_constraints.v2` で許容誤差を固定し、`make repro-cross-env` を週次導線へ組込む | ops_runtime | Mitigated |
| R-009 | データライセンス不備で公開不可になる | High | Low | dataset manifest に license 欄を必須化しレビューする | ops_governance | Mitigated |
| R-010 | 図表の手編集で数値整合が崩れる | Medium | Medium | `FIGURE_SOURCES.v1.json` で生成元を固定し、`validate_figure_integrity.py` を CI で強制 | program_office | Mitigated |

## 監視トリガー

- p95 latency が目標値を超過し続ける
- truncation 率（`t=true`）が想定を超える
- 同一クエリの結果順が実行ごとに変わる
- run registry の欠損率が 0% でなくなる
- 別環境再現時の主要指標差が許容閾値を超える
