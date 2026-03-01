#!/usr/bin/env python3
"""Regression tests for run_record generation flow."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase


class TestGenerateRunRecord(TestCase):
    def test_create_run_dir_and_use_config_output_summary(self) -> None:
        root = Path(__file__).resolve().parents[2]
        artifacts_root = root / "artifacts"
        artifacts_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=artifacts_root) as td:
            temp_root = Path(td)
            runs_root = temp_root / "runs"
            registry_root = temp_root / "registry"
            output_dir = temp_root / "pipeline"
            output_dir.mkdir(parents=True, exist_ok=True)

            config_path = output_dir / "generated_experiment_pipeline.auto.yaml"
            config_path.write_text("repositories: []\n", encoding="utf-8")

            summary = {
                "overall": {
                    "avg_mrr": 0.381,
                    "recall": 0.743,
                    "avg_latency_ms": 0.75,
                }
            }
            (output_dir / "final_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False),
                encoding="utf-8",
            )

            run_id = "run_test_create_dir"
            cmd = [
                "python3",
                "scripts/pipeline/generate_run_record.py",
                "--run-id",
                run_id,
                "--config-path",
                str(config_path.relative_to(root)),
                "--runs-root",
                str(runs_root.relative_to(root)),
                "--registry-root",
                str(registry_root.relative_to(root)),
                "--create-run-dir",
            ]
            subprocess.run(
                cmd,
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )

            run_dir = runs_root / run_id
            self.assertTrue(run_dir.exists(), "run_dir should be created automatically")

            record_path = run_dir / "run_record.v2.json"
            self.assertTrue(record_path.exists(), "run_record.v2.json should be generated")

            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["run_id"], run_id)
            self.assertAlmostEqual(record["metrics"]["mrr_at_10"], 0.381)
            self.assertAlmostEqual(record["metrics"]["recall_at_10"], 0.743)
            self.assertEqual(record["status"], "partial")
