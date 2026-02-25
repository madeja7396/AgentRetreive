# Decision Log (ADR Lite)

更新日: 2026-02-25

| ID | Topic | Decision | Rationale | Consequence | Status |
|---|---|---|---|---|---|
| D-001 | Retrieval Interface | LLM へは `doc_id/span_id` を基本出力し、path は辞書化して最小化 | トークン削減と参照一貫性を優先 | デバッグ時に逆引き機能が必要 | Accepted |
| D-002 | Search Core | 非埋め込み（BM25 + Symbol + Meta）を MVP の中核に採用 | 決定性・軽量性・再現性を重視 | 同義語/言い換え耐性は別施策が必要 | Accepted |
| D-003 | Output Contract | Mini-JSON 固定スキーマ（上限付き、cursor 対応）を採用 | エージェント向けに応答サイズ制御を厳密化 | スキーマ破壊変更時に version 管理が必須 | Accepted |
| D-004 | Evidence Model | 結果は hit 羅列より `rng` + `next[]` を重視 | 次アクションの確定を最短化 | ランキング品質の説明責任が増える | Accepted |
| D-005 | Evaluation Priority | e2e 指標（Tool Calls / Bytes / Time）を主、検索精度を副に置く | 実運用コスト最適化を目的関数に合わせる | ベースライン定義を厳密化する必要あり | Accepted |
| D-006 | Data Provenance | dataset manifest + run registry を必須化する | 研究成果の追跡可能性と監査性を担保する | 記録負荷が増えるため自動化が必要 | Accepted |
| D-007 | Environment Independence | lockfile 固定 + 1 コマンド再現手順を採用する | 環境依存を減らし再現性を高める | ツールチェーン更新時に互換検証が必要 | Accepted |
| D-008 | Paper Artifacts | 図表はスクリプト生成のみを許可し手編集を禁止する | 論文値の再生成性を担保する | 可視化修正はコード変更で対応する必要あり | Accepted |

## 未決事項

- `span_id` の有効期限（index 更新後の互換ポリシー）
- `digest` 算出方式（速度優先か衝突耐性優先か）
- symbol 抽出対象言語の優先順位（MVP 初期対応範囲）
- 再現許容誤差（指標差分しきい値）の定量定義
