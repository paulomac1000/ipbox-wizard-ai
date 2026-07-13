# Changelog

## [v1.2.0] — Evaluator fail-closed, VCR hardening, Ruff CI

### Added
- Per-section validation in evaluator: each scenario assertion type now checks that its required `<result>`, `<monthly_W>`, `<tests>`, `<stops_reviews>`, or `<classifications>` section is present in the LLM response
- `testy_fail` assertion: requires specific tests to be FAIL (symmetrical to `testy_pass`)
- `nexus_range` assertion: range check with ±0.001 tolerance (alternative to exact `nexus`)
- `przychod_NIE_roczny_range` assertion: range check for non-IP annual revenue
- `assertions.stops`: per-assertion stop codes (in addition to `meta.expected_stops`)
- `klucz_MIX_metoda`, `klucz_MIX_źródło` assertions: exact match on MIX key method and source
- `nie_używaj_W_do_MIX` assertion: validates W coefficient is NOT used for MIX allocation
- `review_obecne` assertion: alternative name for expected reviews check
- `alokacja_multi_ip` assertion: validates two-stage multi-IP allocation values
- `soft_warnings` assertion: non-blocking warnings (separate from `warnings` which is now HARD)
- `request_hash` field in `CassetteTurn` for response-to-cassette traceability
- `PROMPT_TEMPLATE_VERSION` constant (`"2"`) in `fingerprint.py` for prompt format tracking
- `SYSTEM_PROMPT` constant in `runner.py` — single source of truth for the LLM system prompt
- Ruff linting job in `full-suite.yml` CI pipeline (`ruff check .`)
- Ruff configuration in `pyproject.toml` (E, F, W, I, N, UP, B, SIM, RUF rule sets)
- New helper functions in evaluator: `_normalize_test_id`, `_parse_tests_map`, `_test_passed`, `_find_klucz_mix_field`, `_w_used_for_mix`, `_find_number_for_key`, `_flatten_dict`

### Changed
- **Evaluator fail-closed** for all assertion types:
  - `testy_pass` now requires explicit PASS in the tests block (absence is not PASS)
  - `testy_fail` requires explicit FAIL (PASS is an error, missing is an error)
  - `nexus`/`nexus_range`: `None` result fields now produce failures instead of being silently skipped
  - `podatek_IP_range`, `podatek_NIE_range`, `przychod_IP_roczny_range`, `przychod_NIE_roczny_range`: `None` values now produce failures instead of being silently skipped
  - `W_miesieczne`: missing monthly values now produce failures
- **Warnings are HARD failures by default**: `assertions.warnings` is now a HARD check (blocking). Non-blocking warnings moved to `assertions.soft_warnings`
- **TEST ID normalization**: regex-based extraction (`TEST[\s_-]*(\d+)` → `TEST_N`). Tests like `TEST 1`, `TEST_1_bilans` all normalize to `TEST_1`
- **Live API fallback after VCR error removed**: VCR failures in non-`none` mode now raise (`print` + `raise`) instead of silently falling back to the live API
- `LLMClient(require_api_key=False)` in playback mode — no API key required when using cassettes
- `test_scenarios.py` fixture passes `require_api_key=False` automatically in playback mode
- VCR playback validates prompt hash (`sha256` fingerprint mismatch → `ValueError`)
- System prompt deduplicated to `SYSTEM_PROMPT` constant in `runner.py`
- `GEMINI_MODEL` default: `gemini-2.0-flash` → `gemini-3.1-flash-lite-preview`
- CI workflows use `vars.GEMINI_MODEL` (GitHub Variables) instead of per-job hardcode
- CI LLM tests: `VCR_MODE=playback` for PRs (zero API cost), `VCR_MODE=auto` for push/dispatch
- `conftest.py`: modernized imports (`from os import environ, getenv`), `--vcr-mode` propagation

### Fixed
- `testy_pass` zero-false-positive: was silently passing when tests block was empty or test was missing — now fails if test is absent
- `_test_failed` ambiguity: now uses `_normalize_test_id` + `_parse_tests_map` for reliable matching
- `conftest.py` `pytest_configure` handles `--vcr-mode` option correctly

## [v1.1.1] — Fixup: None vs 0.0 sentinel correction

### Added
- 6 P0 guard tests for None sentinel, 0.0 explicit key, and rejection of annual-policy-with-key
- Scenario 44 (`44_mix_revenue_key_kis.yaml`): KIS revenue key with REVIEW_17 assertion
- Scenario 45 (`45_multi_ip_two_stage.yaml`): real per-IP revenue data with stage1/stage2 assertions and `alokacja_multi_ip` validation
- Method aliases: `przychodowy_roczny` → `przychodowa_roczna`, `czasowy_W` → `czasowa_W` (backward-compat in `AllocationPolicy.__post_init__`)
- Bounds validation for `nexus_amount` (0..item.amount), `w_coefficient` (0..100), `allocation_key` (0..1)
- Evaluator assertions: `klucz_MIX_metoda`, `klucz_MIX_źródło`, `nie_używaj_W_do_MIX`, `review_obecne`, `alokacja_multi_ip`
- Secure dump script (`dump-to-md.sh`): excludes `.git`, `.omo`, `input/`, `reports/`, `tmp/`, `cache/`, `.env` files

### Changed
- `AllocationPolicy.mix_key` from `float = 0.0` to `float | None = None` — `None` = deferred for annual policy
- `CostItem.allocation_key` from `float = 0.0` to `float | None = None` — `0.0` now accepted as valid key (0% to IP)
- `resolve_mix_key()` uses `is not None` instead of `0 < key` — accepts `0.0` as a valid explicit key
- `__post_init__` rejects `przychodowa_roczna` with non-None `mix_key` (deferred method cannot have monthly key)
- Annual branch no longer catches `ValueError` as defer signal — explicit `allocation_key=None` is the defer mechanism
- `aggregate_nexus_costs()` rejects MIX costs entering A/B/C/D without explicit `nexus_amount`
- `allocate_multi_ip()` validates `software_ip_revenue <= total_revenue` and each individual `ip_revenue >= 0`
- `.omo/` added to `.gitignore`, removed from tracking
- KIS precedence: algorithm now enforces KIS method as highest priority in Phase 2A.3/2A.4
- Phase 7.2.A: restricted to `przychodowa_roczna` only; other annual methods → `ERROR_ALLOC_07`
- KIS periodicity: Phase 0.1 clarifies that `przychodowy klucz` != automatic annual deferral
- Unify key name to `Klucz_Przychodu_IP` everywhere in algorithm output schema
- YAML output schema adds `MIX_deferred`, `MIX_status`, `status` (PROVISIONAL/FINAL)
- TEST 7-9 added to output schema
- `spójna_z_interpretacją_KIS` defaults to `null` instead of empty string

### Fixed
- Scenario 44 `review_obecne`: added `REVIEW_17` to match algorithm change
- Scenario 45: restructured input from flat costs to structured `przychody_IP` dict + `koszty_wspólne_MIX`
- Coverage ≥ 90% enforced (actual: 99.46%)
- `dump-to-md.sh`: create output dir before writing, don't hide find errors
- AGENTS.md: typo corrections, `GEMINI_MODEL` env var clarification
- README.md: multiple typo fixes, link updates, model recommendation updates
- `docs/testing.md`: VCR mode documentation alignment

## [v1.1.0] — Allocation Policy & NEXUS Classification

### Added
- `AllocationPolicy` dataclass (`frozen=True`, `kw_only=True`) with fields:
  - `policy_id`, `revenue_method`, `mix_method`, `mix_key`, `source`, `justification`
  - Validation in `__post_init__`: source required, enum checks, mix_key range (0..1), method-specific rules
  - `czasowa_W` requires both `justification` and `mix_key`
  - `przychodowa_roczna` rejects `mix_key` in monthly policy (deferred to annual)
- `CostItem` extended fields: `allocation_key`, `allocation_source`, `nexus_source`, `nexus_basket`, `nexus_amount`
- `allocate_revenue_monthly()` — separates revenue allocation from MIX cost allocation
  - Methods: `dokumentowa` (uses `document_split_ip`), `czasowa_W`, `produktowa`, `z_interpretacji`, `custom`
  - Validation for each method, range checks on keys
- `annual_mix_allocation_revenue()` — annual settlement of deferred MIX costs
  - `mix_key = annual_ip_revenue / annual_total_revenue`
  - Input validation: revenue > 0, deferred >= 0, IP <= total
- `allocate_multi_ip()` — two-stage allocation for multiple IPs
  - Stage 1: software IP share of total indirect costs
  - Stage 2: split among individual IPs by revenue proportion
  - Validation: non-negative inputs, non-empty ip_revenues, total_ip_revenue > 0
- `nexus_classify()` — classifies cost item into NEXUS basket
  - Validates source against `NEXUS_SOURCE_MAP` (6 categories)
  - Sets `nexus_source`, `nexus_basket` on the item
  - Unknown sources → `poza_nexus` + `REVIEW_NEXUS_UNKNOWN` note
- `aggregate_nexus_costs()` — aggregates amounts by basket
  - MIX costs entering A/B/C/D require explicit `nexus_amount` (prevents over-allocation)
- Phase 2A: Allocation Policy with 7 subsections (`ebcccf8`)
- Phase 0.1: KIS extraction extended for allocation policy (`4cd3770`)
- Phase 3.1-3.2: uses `Klucz_MIX` instead of W for MIX cost allocation
- Phase 4 formulas: per-item MIX allocation loop with `resolve_mix_key()`
- Phase 6: new REVIEW/STOP/ERROR codes (`ERROR_ALLOC_01` through `ERROR_ALLOC_07`)
- Phase 7.2, 8, 10: NEXUS classification tests, expanded output schema
- Test suite: 12 MIX allocation unit tests (6 positive + 6 negative) in `test_mix_allocation.py`
- Test suite: 7 NEXUS classification unit tests in `test_nexus_classification.py`
- LLM scenarios: 44 (`44_mix_revenue_key_kis.yaml`), 45 (`45_multi_ip_two_stage.yaml`)
- VCR cassettes re-recorded for terminology standardization (`119fe66`)

### Changed
- `allocate_costs_monthly()` rewritten to use `AllocationPolicy` instead of bare parameters
  - Per-item MIX loop with `resolve_mix_key()`
  - `przychodowa_roczna` defers costs with `allocation_key=None` → `mix_deferred`
  - Returns `result_status`: `PROVISIONAL` (deferred > 0) or `FINAL`
  - Returns `mix_deferred`, `mix_effective_key`, `w_coefficient`
- `CostItem` validation: `nexus_amount` must be 0..item.amount
- Terminology standardized across algorithm and code: `Klucz_MIX`, `koszyk MIX`, etc.
- LLM test cassettes regenerated for provider/model metadata consistency

### Breaking Changes
- `AllocationPolicy` is a **required** parameter for `allocate_costs_monthly()` — old positional arg order removed
- `CostItem` now validates `nexus_amount` range — existing code with out-of-range values will raise `ValueError`
- `allocate_costs_monthly()` return dict now includes `mix_deferred`, `result_status`, `mix_effective_key` — consumers must handle new keys
- `CostItem.allocation_key` type changed — code using `0.0` as sentinel will see different behavior (use `is not None` check)
- Cost classification no longer defaults to W-based MIX allocation — requires explicit `AllocationPolicy`

### Fixed
- Algorithm terminology: `Współczynnik_W` → `Klucz_MIX` for MIX cost allocation
- Phase 4 formula corrections for per-item allocation
- Phase 6 STOP/REVIEW code consistency
- NEXUS classification tests now cover all 6 source categories

## [v1.0.2] — Algorithm terminology & cassette refresh

### Changed
- Terminology standardization for code execution environments: `Współczynnik_W` → `Klucz_MIX`
- LLM test cassettes regenerated with new metadata format
- README updates

## [v1.0.1] — Fixes

### Fixed
- Various minor fixes

## [v1.0.0] — Initial release

### Added
- Complete 10-phase IP Box algorithm (`ipbox_algorytm.md`)
- Python calculator module (`ipbox_calculator.py`)
- 34 LLM test scenarios with VCR cassette system
- Unit test suite (W coefficient, NEXUS, FX, tax cascade, verification tests)
- CI/CD: GitHub Actions for unit tests, LLM scenario tests, VCR smoke checks
- Automated testing framework with VCR (recording/playback for LLM responses)
- KIS interpretation extraction
- Multi-currency support (NBP API)
- Tax cascade with proper deduction order
- Verification tests (TEST 1-6)
- Documentation: `docs/testing.md`, AGENTS.md
