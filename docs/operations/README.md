# Operations Docs Index

更新日: 2026-03-03

## 目的

- 運用文書の参照順序を固定し、担当者ごとの解釈差を減らす

## 読む順序

1. `MAINTENANCE_GOVERNANCE.md`  
   統治方針、RACI、してよいこと/悪いこと
2. `SIER_SOUL.md`  
   行動原則と受け入れ基準
3. `RUNBOOK.md`  
   日次/週次運用、KPI更新、障害一次対応
4. `CLI_DISTRIBUTION.md`  
   CLI配布ゲート、配布物生成、チェックサム検証
5. `SKILLS_OPERATING_MODEL.md`  
   skill階層化の運用モデル
6. `ASSET_CLASSIFICATION.md`  
   未統合ナレッジ/スクリプトの分類台帳（active/incubation/archive）
7. `AGENTD.md`  
   デーモン実行の運用詳細
8. `../../skills/CATALOG.yaml`  
   skill owner（team/contact/escalation）台帳

## 実行前チェック

```bash
make validate
make experiment-ready
make report
```
