# Changelog

## Unreleased

### Added
- Strict JSON Schema for LLM output validation (tests/llm/output_schema.py)
- Deterministic oracle for TEST 1-9 (independent recomputation, not model self-report)
- Evaluator fixes: exact code matching, recursive nested_get, warnings lookup fix
- Calculator fixes: NaN/inf guards, aggregate_w_multiproject validation, FX method whitelist
- Scenario assertions restored for 02, 16, 29, 31, 33, 41, 42, 44, 45

### Changed
- Removed GEMINI_API_KEY/GEMINI_MODEL legacy env vars (use OPENROUTER_API_KEY/LLM_MODEL)
- pyproject.toml version set to 0.1.0 (pre-release)
- response_format upgraded from json_object to json_schema for structured outputs
