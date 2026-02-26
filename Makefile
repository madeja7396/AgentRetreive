# AgentRetrieve Experiment Pipeline Makefile

.PHONY: help pipeline test clean experiment-ready experiment experiment-all

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
	@echo "  make experiment-all - Preflight + auto-adapt + final evaluation (all support languages)"
	@echo "  make validate    - Run contract harness validation"
	@echo "  make clean       - Clean experiment outputs"
	@echo "  make report      - Generate final report"

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

experiment-all:
	@echo "Running full experiment route (all support languages)..."
	@AR_CLONE_TIMEOUT_SEC=$${AR_CLONE_TIMEOUT_SEC:-2400} python3 scripts/pipeline/run_experiment_route.py --index-all

test:
	@echo "Running quick test..."
	@python3 scripts/pipeline/run_full_pipeline.py

validate:
	@echo "Running contract harness..."
	@python3 scripts/ci/run_contract_harness.sh

clean:
	@echo "Cleaning experiment outputs..."
	@rm -rf artifacts/experiments/pipeline/*.json
	@rm -rf artifacts/experiments/pipeline/*.csv
	@echo "Done!"

report:
	@echo "Generating final report..."
	@python3 scripts/benchmark/generate_report.py \
		--input artifacts/experiments/pipeline/aggregate_results.json \
		--output artifacts/experiments/FINAL_PIPELINE_REPORT.md

# Development targets
format:
	@echo "Formatting code..."
	@black src/ scripts/ --line-length 100

lint:
	@echo "Linting code..."
	@flake8 src/ scripts/ --max-line-length 100
