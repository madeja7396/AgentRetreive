# Risk Register

更新日: 2026-02-25

| ID | Risk | Impact | Probability | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R-001 | DSL が広がりすぎ、MVP で実装負荷が肥大化する | High | Medium | v1 は必須キーに限定し、追加要件は拡張キーへ分離 | TBD | Open |
| R-002 | 出力 bytes 上限を守ると必要根拠が欠落する | High | Medium | `max_bytes` 内で `next[]` を優先残存し、再取得導線を保証 | TBD | Open |
| R-003 | symbol 抽出の言語差で検索品質が偏る | Medium | High | MVP は対応言語を明示し、非対応時は lexical fallback を強制 | TBD | Open |
| R-004 | benchmark データセットの正解ラベル作成コストが高い | Medium | Medium | 難易度別に段階化し、まず小規模固定セットで開始 | TBD | Open |
| R-005 | 決定性要件（同一入力同一出力）が崩れる | High | Medium | 並び順規則・同点規則・乱数禁止を contract test 化 | TBD | Open |
| R-006 | `span_id` が index 更新で不整合になる | High | Medium | 互換ポリシー（invalidate or migrate）を ADR で先に固定 | TBD | Open |
| R-007 | 実験ログ欠損で論文主張を遡れない | High | Medium | run registry への記録を CI チェックで必須化 | TBD | Open |
| R-008 | 環境差異で主要結果が再現しない | High | Medium | lockfile 固定と 2 環境再現テストを定例化 | TBD | Open |
| R-009 | データライセンス不備で公開不可になる | High | Low | dataset manifest に license 欄を必須化しレビューする | TBD | Open |
| R-010 | 図表の手編集で数値整合が崩れる | Medium | Medium | 図表生成をスクリプト経由に限定し、元データを記録 | TBD | Open |

## 監視トリガー

- p95 latency が目標値を超過し続ける
- truncation 率（`t=true`）が想定を超える
- 同一クエリの結果順が実行ごとに変わる
- run registry の欠損率が 0% でなくなる
- 別環境再現時の主要指標差が許容閾値を超える
