# Operations Docs Index

更新日: 2026-02-28

## 目的

- 運用文書の参照順序を固定し、担当者ごとの解釈差を減らす

## 読む順序

1. `MAINTENANCE_GOVERNANCE.md`  
   統治方針、RACI、してよいこと/悪いこと
2. `SIER_SOUL.md`  
   行動原則と受け入れ基準
3. `RUNBOOK.md`  
   日次/週次運用、KPI更新、障害一次対応
4. `SKILLS_OPERATING_MODEL.md`  
   skill階層化の運用モデル
5. `AGENTD.md`  
   デーモン実行の運用詳細
6. `../../skills/CATALOG.yaml`  
   skill owner（team/contact/escalation）台帳

## 実行前チェック

```bash
make validate
make experiment-ready
make report
```
