# AgentRetrieve Experiment Pipeline Makefile

.PHONY: help pipeline test clean experiment-ready experiment experiment-fast experiment-all experiment-daily-full run-record repro-cross-env template-sync-check template-sync figures release-ready template-init template-smoke release-cli-build release-cli-check release-cli-package release-cli-ready

help:
	@echo "AgentRetrieve Experiment Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  make pipeline    - Run full experiment pipeline with parameter search"
	@echo "  make test        - Run quick test on fd repository"
	@echo "  make auto-adapt  - One-command corpus sync + training + parameter adaptation"
	@echo "  make auto-adapt-all - One-command full corpus sync (all support languages) + training + parameter adaptation"
	@echo "  make experiment-ready - Run preflight checks only (contracts + tests)"
	@echo "  make experiment  - Preflight + auto-adapt + final evaluation (taskset repos)"
	@echo "  make experiment-fast - Fast profile (7 repos, reduced grid/cache, quick iteration)"
	@echo "  make experiment-all - Preflight + auto-adapt + final evaluation (all support languages)"
	@echo "  make experiment-daily-full - Daily full-fidelity experiment with forced refresh"
	@echo "  make phase3-complete RUN_ID=<run_id> - Generate micro/e2e/ablation/stability artifacts"
	@echo "  make run-record RUN_ID=<run_id> - Generate run_record v1/v2 and registries"
	@echo "  make repro-cross-env RUN_ID=<run_id> - Cross-environment reproducibility check"
	@echo "  make template-sync-check - Verify TEMPLATE bundle synchronization"
	@echo "  make template-sync - Synchronize TEMPLATE bundle from source assets"
	@echo "  make validate    - Run contract harness validation"
	@echo "  make clean       - Clean experiment outputs"
	@echo "  make report      - Generate final report"
	@echo "  make figures RUN_ID=<run_id> - Generate paper figure assets"
	@echo "  make release-ready - Full release gate (validate + test + figures + template-sync-check + report)"
	@echo "  make release-cli-build - Build Rust CLI binaries (release + release-dist)"
	@echo "  make release-cli-check - Run CLI distribution gates (size + perf regression)"
	@echo "  make release-cli-package LABEL=<label> TARGET=<target> - Package CLI archive into dist/"
	@echo "  make release-cli-ready LABEL=<label> TARGET=<target> - Build + check + package in one command"

pipeline:
	@echo "Running full experiment pipeline..."
	@mkdir -p artifacts/experiments/pipeline
	@python3 scripts/pipeline/run_full_pipeline.py -c configs/experiment_pipeline.yaml

auto-adapt:
	@echo "Running one-command corpus auto adaptation..."
	@python3 scripts/pipeline/run_corpus_auto_adapt.py

auto-adapt-all:
	@echo "Running one-command full corpus auto adaptation (all support languages)..."
	@AR_CLONE_TIMEOUT_SEC=$${AR_CLONE_TIMEOUT_SEC:-2400} python3 scripts/pipeline/run_corpus_auto_adapt.py --index-all

experiment-ready:
	@echo "Running experiment preflight checks..."
	@python3 scripts/pipeline/run_experiment_route.py --skip-auto-adapt --skip-final-eval

experiment:
	@echo "Running full experiment route (taskset repos)..."
	@python3 scripts/pipeline/run_experiment_route.py

experiment-fast:
	@echo "Running fast experiment profile..."
	@python3 scripts/pipeline/run_experiment_route.py --profile fast

experiment-all:
	@echo "Running full experiment route (all support languages)..."
	@AR_CLONE_TIMEOUT_SEC=$${AR_CLONE_TIMEOUT_SEC:-2400} python3 scripts/pipeline/run_experiment_route.py --index-all

experiment-daily-full:
	@echo "Running daily full-fidelity experiment..."
	@bash scripts/dev/run_daily_full.sh

phase3-complete:
	@echo "Completing Phase 3 metrics for run_id=$(RUN_ID)"
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required: make phase3-complete RUN_ID=run_..." && exit 1)
	@python3 scripts/benchmark/complete_phase3.py --run-id "$(RUN_ID)" --repeats 5

run-record:
	@echo "Generating run record for run_id=$(RUN_ID)"
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required: make run-record RUN_ID=run_..." && exit 1)
	@python3 scripts/pipeline/generate_run_record.py --run-id "$(RUN_ID)"

repro-cross-env:
	@echo "Running cross-env reproducibility for run_id=$(RUN_ID)"
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required: make repro-cross-env RUN_ID=run_..." && exit 1)
	@scripts/dev/run_cross_env_repro.sh "$(RUN_ID)"

template-sync-check:
	@echo "Checking TEMPLATE bundle synchronization..."
	@python3 scripts/dev/sync_template_bundle.py --check

template-sync:
	@echo "Synchronizing TEMPLATE bundle from source assets..."
	@python3 scripts/dev/sync_template_bundle.py

test:
	@echo "Running quick test..."
	@python3 scripts/pipeline/run_full_pipeline.py

validate:
	@echo "Running contract harness..."
	@bash scripts/ci/run_contract_harness.sh

clean:
	@echo "Cleaning experiment outputs..."
	@rm -rf artifacts/experiments/pipeline/*.json
	@rm -rf artifacts/experiments/pipeline/*.csv
	@echo "Done!"

report:
	@echo "Generating final report..."
	@python3 scripts/benchmark/generate_report.py \
		--summary artifacts/experiments/pipeline/final_summary.json \
		--aggregate artifacts/experiments/pipeline/aggregate_results.json \
		--output artifacts/experiments/FINAL_PIPELINE_REPORT.md

release-cli-build:
	@echo "Building Rust CLI binaries (release + release-dist)..."
	@cargo build --release -p ar-cli
	@cargo build --profile release-dist -p ar-cli

release-cli-check: release-cli-build
	@echo "Running CLI size/performance gates..."
	@bash scripts/release/check_binary_size.sh --binary target/release-dist/ar --max-mb 3.5
	@python3 scripts/release/bench_cli_regression.py \
		--baseline-bin target/release/ar \
		--candidate-bin target/release-dist/ar \
		--allowed-regression-ratio 0.05 \
		--output dist/cli_perf_regression.json

release-cli-package: release-cli-check
	@echo "Packaging CLI distribution archive..."
	$(eval RELEASE_LABEL := $(if $(LABEL),$(LABEL),local))
	$(eval RELEASE_TARGET := $(if $(TARGET),$(TARGET),linux-x86_64))
	@bash scripts/release/package_cli_distribution.sh \
		--binary target/release-dist/ar \
		--label "$(RELEASE_LABEL)" \
		--target "$(RELEASE_TARGET)" \
		--output-dir dist

release-cli-ready: release-cli-package
	@echo "CLI distribution artifact ready in dist/"

figures:
	@echo "Generating paper figure assets..."
	$(eval DEFAULT_RUN_ID := run_20260228_154238_exp001_raw)
	$(eval RUN_ID_VALUE := $(if $(RUN_ID),$(RUN_ID),$(DEFAULT_RUN_ID)))
	@echo "Using RUN_ID: $(RUN_ID_VALUE)"
	@python3 scripts/papers/generate_figure_assets.py --run-id "$(RUN_ID_VALUE)"

release-ready: validate
	@echo "=== Release Gate ==="
	@echo "[1/5] Running tests..."
	@python3 -m pytest tests/ -q
	@echo "[2/5] Generating figures..."
	$(eval DEFAULT_RUN_ID := run_20260228_154238_exp001_raw)
	$(eval RUN_ID_VALUE := $(if $(RUN_ID),$(RUN_ID),$(DEFAULT_RUN_ID)))
	@echo "Using RUN_ID: $(RUN_ID_VALUE)"
	@python3 scripts/papers/generate_figure_assets.py --run-id "$(RUN_ID_VALUE)" --strict
	@echo "[3/5] Checking figure integrity..."
	@python3 scripts/ci/validate_figure_integrity.py --strict
	@echo "[4/5] Checking TEMPLATE sync..."
	@python3 scripts/dev/sync_template_bundle.py --check
	@echo "[5/5] Generating report..."
	@python3 scripts/benchmark/generate_report.py \
		--summary artifacts/experiments/pipeline/final_summary.json \
		--aggregate artifacts/experiments/pipeline/aggregate_results.json \
		--output artifacts/experiments/FINAL_PIPELINE_REPORT.md
	@echo "=== Release Ready ==="

template-init:
	@echo "Initializing new project from TEMPLATE..."
	@test -n "$(TARGET)" || (echo "TARGET is required: make template-init TARGET=/path/to/new-project" && exit 1)
	@python3 scripts/dev/init_project_from_template.py --target "$(TARGET)" --name "$(NAME)" --owner "$(OWNER)"

template-smoke:
	@echo "Running TEMPLATE smoke test (strict)..."
	@rm -rf /tmp/agentretrieve-template-smoke
	@echo "[1/5] Initializing project from TEMPLATE..."
	@python3 scripts/dev/init_project_from_template.py --target /tmp/agentretrieve-template-smoke --name "SmokeTest" --owner "core_quality"
	@echo "[2/5] Validate contracts..."
	@cd /tmp/agentretrieve-template-smoke && python3 scripts/ci/validate_contracts.py
	@echo "[3/5] Run pytest (minimum tests)..."
	@cd /tmp/agentretrieve-template-smoke && python3 -m pytest tests/ -v
	@echo "[4/5] Template sync check..."
	@cd /tmp/agentretrieve-template-smoke && python3 scripts/dev/sync_template_bundle.py --check
	@echo "[5/5] Cleanup..."
	@rm -rf /tmp/agentretrieve-template-smoke
	@echo "=== TEMPLATE Smoke Test Passed ==="

# Development targets
format:
	@echo "Formatting code..."
	@black src/ scripts/ --line-length 100

lint:
	@echo "Linting code..."
	@flake8 src/ scripts/ --max-line-length 100
