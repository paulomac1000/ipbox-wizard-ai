.PHONY: quality test record verify full

quality:
	ruff format --check .
	ruff check .
	python -m compileall -q python_helper tests scripts
	python scripts/check_workflow_policy.py
	python -m bandit -q -lll -iii -r python_helper scripts
	for script in scripts/*.sh; do bash -n "$$script"; done

test: quality
	pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
	pytest -q
	python scripts/check_cassette_policy.py

record: test
	./scripts/record_all_models.sh

verify:
	@set -eu; \
	unset OPENROUTER_API_KEY; \
	python scripts/vcr_precommit.py --all-models; \
	python scripts/benchmark_report.py; \
	VCR_MODE=playback ./scripts/verify_all_models.sh

full: test verify
