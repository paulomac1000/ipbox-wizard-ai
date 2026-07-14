# Changelog

## Unreleased

### Added

- Deterministic-first LLM pipeline with Python tool context.
- Independent full-output oracle and fail-closed evaluator.
- 36 normalized scenarios with explicit allocation policies and NEXUS evidence.
- Strict provider-neutral JSON Schema.
- Multi-model benchmark for Gemini 3.5 Flash, GPT-5 Mini and Claude Haiku 4.5.
- Resumable per-model cassette recording and actual-cost reports.

### Changed

- Revenue, MIX and NEXUS are independent decisions.
- Annual revenue MIX is deferred and reconciled at year end.
- Canonical excluded-cost basket is `WYKLUCZONE`; legacy `EXCLUDED` is accepted only at the calculator boundary.
- Multi-IP uses largest-remainder cent allocation.
- All financial inputs reject NaN, infinity and invalid negative values.
- Standard GitHub CI is deterministic and free of API calls.

### Removed

- All stale and semantically failing historical cassettes.
- Provider-prefixed cassette directories.
- Gemini-specific environment aliases.
- VCR auto mode and live fallback from playback.
