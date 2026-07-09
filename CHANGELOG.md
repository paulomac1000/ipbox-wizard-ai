# Changelog

## [v1.1.1] — Fixup: None vs 0.0 sentinel correction

### Fixed
- `AllocationPolicy.mix_key` changed from `float = 0.0` to `float | None = None`
- `CostItem.allocation_key` changed from `float = 0.0` to `float | None = None`
- `resolve_mix_key()` now uses `is not None` instead of `0 < key` — accepts 0.0 as valid key
- `__post_init__` rejects `przychodowa_roczna` with non-None mix_key
- Annual branch no longer catches ValueError as defer signal
- `nexus_classify()` now validates source against NEXUS_SOURCE_MAP, sets nexus_source
- `aggregate_nexus_costs()` rejects MIX costs entering A/B/C/D without explicit nexus_amount
- `allocate_multi_ip()` validates software_ip_revenue bounds and individual ip_revenue >= 0
- `.omo/` added to `.gitignore`, removed from tracking
- Scenario 44: `review_obecne` now includes REVIEW_17
- Scenario 45: real per-IP revenue data with stage1/stage2 assertions
- KIS precedence: algorithm now enforces KIS method as highest priority
- Phase 7.2.A: restricted to `przychodowa_roczna` only; other annual methods → ERROR_ALLOC_07
