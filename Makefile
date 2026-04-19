.PHONY: install test test-unit test-llm test-llm-smoke test-llm-playback test-llm-record coverage clean vcr-check vcr-smoke

install:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

test: test-unit

test-unit:
	pytest tests/unit/ -v --tb=short --cov=python_helper --cov-report=term-missing

# LLM tests with VCR (auto mode - use cassettes if valid, record if stale)
test-llm:
	pytest tests/llm/ --run-llm -v --tb=long

# LLM tests in playback mode (no API calls - use cassettes only)
test-llm-playback:
	pytest tests/llm/ --run-llm -v --vcr-mode=playback --tb=short

# LLM tests in record mode (force re-record all cassettes)
test-llm-record:
	pytest tests/llm/ --run-llm -v --vcr-mode=record

test-llm-smoke:
	pytest tests/llm/ --run-llm -v -m smoke --tb=long

# Smoke test with VCR (playback only - no API calls)
vcr-smoke:
	./scripts/vcr_smoke.sh

# Check VCR cassette freshness
vcr-check:
	python scripts/vcr_precommit.py

coverage:
	mkdir -p reports
	pytest tests/unit/ \
		--cov=python_helper \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/htmlcov \
		--cov-report=term-missing

clean:
	rm -rf reports/
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
