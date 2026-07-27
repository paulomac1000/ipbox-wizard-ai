.PHONY: quality test record verify

quality:
	ruff format --check .
	ruff check .
	python -m compileall -q python_helper tests scripts
	for script in scripts/*.sh; do bash -n "$$script"; done

test: quality
	pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
	pytest -q
	python scripts/check_cassette_policy.py

record: test
	./scripts/record_all_models.sh

verify:
	./scripts/verify_all_models.sh
	python scripts/benchmark_report.py
