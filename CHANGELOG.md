# Changelog

## Unreleased

### Added

- Atomic `decision_facts` contract and code-generated STOP/REVIEW protocol.
- Decision-only model schema; the application assembles the final report deterministically.
- Regression coverage for STOP cascades, multi-IP REVIEW visibility and hidden metadata leakage.

- Deterministic-first LLM pipeline with Python tool context.
- Independent full-output oracle and fail-closed evaluator.
- 36 normalized scenarios with explicit allocation policies and NEXUS evidence.
- Strict provider-neutral JSON Schema.
- Multi-model benchmark for Gemini 3.5 Flash, GPT-5 Mini and Claude Haiku 4.5.
- Resumable per-model cassette recording and actual-cost reports.

### Fixed

- Review findings in STOP zeroing, health-contribution deduction, FX evidence, conservative cost classification and revenue/W validation.
- Fail-closed duplicate detection, cassette/manifest integrity, complete finish-reason checks and safe retry behavior.
- Scenario fixtures now exercise ordinary PIT, thermomodernization carry-over, W-vs-MIX separation and reconciled multi-IP revenues.
- GitHub Actions checkout/input hardening and recording scripts that cannot overwrite stale cassettes.

### Changed

- LLM responses contain only `status`, `stops` and `reviews`; max output is reduced to 1024 tokens.
- STOP/REVIEW comparison is exact and rejects extra codes.
- Cassette format is version 4 and all previous partial cassettes are invalidated.

- Revenue, MIX and NEXUS are independent decisions.
- Annual revenue MIX is deferred and reconciled at year end.
- Canonical excluded-cost basket is `WYKLUCZONE`; legacy `EXCLUDED` is accepted only at the calculator boundary.
- Multi-IP uses largest-remainder cent allocation.
- All financial inputs reject NaN, infinity and invalid negative values.
- Standard GitHub CI is deterministic and free of API calls.

### Removed

- Hidden `meta.expected_reviews` influence on oracle truth.
- Full financial report copying from the LLM request/response path.
- Partial 84/108 cassette matrix generated for the obsolete contract.

- All stale and semantically failing historical cassettes.
- Provider-prefixed cassette directories.
- Gemini-specific environment aliases.
- VCR auto mode and live fallback from playback.
