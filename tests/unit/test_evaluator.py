"""Unit tests for the LLM scenario evaluator (tests/llm/evaluator.py)."""

import pytest

from tests.llm.evaluator import (
    Evaluator,
    _check_description_consistency,
    _find_nexus,
    _find_non_ip_tax,
    _find_value,
    _oracle_test_1,
    _oracle_test_2,
    _oracle_test_3,
    _oracle_test_4,
    _oracle_test_7,
    _oracle_test_9,
    _test_failed,
    _test_passed,
    normalize_test_key,
    validate_assertion_keys,
)


@pytest.mark.unit
@pytest.mark.P2
class TestNormalizeTestKey:
    """Tests for the normalize_test_key function."""

    def test_normalize_test_1(self):
        assert normalize_test_key("TEST_1") == "TEST_1"

    def test_normalize_test_with_space(self):
        assert normalize_test_key("TEST 1") == "TEST_1"

    def test_normalize_test_lowercase(self):
        assert normalize_test_key("test_1_bilans") == "TEST_1"

    def test_normalize_test_case_insensitive(self):
        assert normalize_test_key("Test 1") == "TEST_1"

    def test_normalize_test_17_different_from_1(self):
        assert normalize_test_key("TEST_17") == "TEST_17"
        assert normalize_test_key("TEST_17") != "TEST_1"


@pytest.mark.unit
@pytest.mark.P0
class TestFindNexus:
    """Tests for _find_nexus — must handle 0.0 correctly (not as falsy)."""

    def test_find_nexus_returns_zero(self):
        """Nexus=0.0 via wartość dict key should return 0.0, not None."""
        result = {"nexus": {"wartość": 0.0}}
        assert _find_nexus(result) == 0.0

    def test_find_nexus_returns_nonzero(self):
        """Nexus=0.5 via wartość dict key should return 0.5."""
        result = {"nexus": {"wartość": 0.5}}
        assert _find_nexus(result) == 0.5

    def test_find_nexus_flat_number(self):
        """Nexus=0.0 as a flat number should return 0.0, not None."""
        result = {"nexus": 0.0}
        assert _find_nexus(result) == 0.0


@pytest.mark.unit
@pytest.mark.P2
class TestValidateAssertionKeys:
    """Tests for the validate_assertion_keys function."""

    def test_known_key_passes(self):
        errors = validate_assertion_keys({"nexus": 0.8}, "test_scenario")
        assert len(errors) == 0

    def test_unknown_key_fails(self):
        errors = validate_assertion_keys({"totally_bogus_key": 123}, "test_scenario")
        assert len(errors) == 1
        assert "unknown" in errors[0].lower()
        assert "totally_bogus_key" in errors[0]

    def test_known_and_unknown_mixed(self):
        errors = validate_assertion_keys({"nexus": 0.8, "bogus": 1}, "test_scenario")
        assert any("bogus" in e for e in errors)
        assert not any("nexus" in e for e in errors)

    def test_all_discovered_keys_are_known(self):
        discovered = {
            "W_miesieczne", "alokacja_multi_ip", "klucz_MIX_metoda",
            "klucz_MIX_źródło", "koszty_koszyk", "nexus", "nexus_range",
            "nie_używaj_W_do_MIX", "podatek_IP_range", "podatek_NIE_range",
            "przychod_IP_roczny_range", "przychod_NIE_roczny_range",
            "review_obecne", "roznice_kursowe_w_IP", "stops",
            "testy_fail", "testy_pass", "warnings", "zus_dubel",
        }
        errors = validate_assertion_keys({k: None for k in discovered}, "test")
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_meta_prefix_is_allowed(self):
        errors = validate_assertion_keys({"meta.custom_field": "value"}, "test")
        assert len(errors) == 0

    def test_empty_assertions_no_errors(self):
        errors = validate_assertion_keys({}, "test")
        assert len(errors) == 0


@pytest.mark.unit
@pytest.mark.P2
class TestDescriptionConsistency:
    """Scenario descriptions must match what assertions actually check."""

    def test_review_mentioned_in_description_when_only_stops_expected(self):
        """Description says 'stop or emit REVIEW' but assertions only check
        for STOP_08 — inconsistency should be detected."""
        scenario = {
            "meta": {
                "id": "test",
                "description": "Should stop or emit REVIEW",
            },
            "assertions": {"stops": ["STOP_08"]},
        }
        errors = _check_description_consistency(scenario)
        assert any("REVIEW" in err for err in errors)

    def test_no_error_when_description_matches_assertions(self):
        """Description only mentions STOP_08, assertions only check STOP_08."""
        scenario = {
            "meta": {
                "id": "test",
                "description": "Should stop with STOP_08",
            },
            "assertions": {"stops": ["STOP_08"]},
        }
        errors = _check_description_consistency(scenario)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_no_error_when_description_and_assertions_mention_review(self):
        """Both description and assertions reference REVIEW."""
        scenario = {
            "meta": {
                "id": "test",
                "description": "Should emit REVIEW_01",
                "expected_reviews": ["REVIEW_01"],
            },
            "assertions": {"review_obecne": ["REVIEW_01"]},
        }
        errors = _check_description_consistency(scenario)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_no_error_when_no_stops_or_reviews(self):
        scenario = {
            "meta": {"id": "test", "description": "Just a normal calculation"},
            "assertions": {"nexus": 0.8},
        }
        errors = _check_description_consistency(scenario)
        assert len(errors) == 0


@pytest.mark.unit
@pytest.mark.P0
class TestTestPassedHelper:
    """Tests for the _test_passed helper function."""

    def test_passes_on_explicit_pass(self):
        assert _test_passed("TEST_1: PASS", "TEST_1")

    def test_passes_without_colon(self):
        assert _test_passed("TEST_1 PASS", "TEST_1")

    def test_passes_with_underscore(self):
        assert _test_passed("TEST_1: PASS", "TEST_1")

    def test_fails_on_explicit_fail(self):
        assert not _test_passed("TEST_1: FAIL", "TEST_1")

    def test_fails_on_empty_string(self):
        assert not _test_passed("", "TEST_1")

    def test_fails_on_none(self):
        assert not _test_passed("TEST_1: NONE", "TEST_1")

    def test_partial_match_does_not_confuse(self):
        """TEST_17 should not match pattern for TEST_1."""
        assert not _test_passed("TEST_17: PASS", "TEST_1")

    def test_detects_pass_among_multiple_tests(self):
        text = "TEST_1: PASS\nTEST_2: PASS\nTEST_3: FAIL"
        assert _test_passed(text, "TEST_1")
        assert _test_passed(text, "TEST_2")
        assert not _test_passed(text, "TEST_3")


@pytest.mark.unit
@pytest.mark.P0
class TestTestFailedHelper:
    """Tests for the _test_failed helper function."""

    def test_detects_explicit_fail(self):
        assert _test_failed("TEST_1: FAIL", "TEST_1")

    def test_not_fail_on_pass(self):
        assert not _test_failed("TEST_1: PASS", "TEST_1")

    def test_not_fail_on_empty(self):
        assert not _test_failed("", "TEST_1")


@pytest.mark.unit
@pytest.mark.P0
class TestEvaluatorTestyPass:
    """Evaluator: testy_pass assertions."""

    def _make_parsed(self, tests_text="", result=None, stops_reviews=None):
        return {
            "tests": tests_text,
            "result": result or {},
            "stops_reviews": stops_reviews or {},
        }

    def test_fails_when_tests_block_empty(self):
        scenario = {"assertions": {"testy_pass": ["TEST_1"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(tests_text=""))
        assert any(f["type"] == "test_missing_TEST_1" for f in failures)

    def test_fails_when_test_not_pass(self):
        scenario = {"assertions": {"testy_pass": ["TEST_1"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(tests_text="TEST_1: FAIL"))
        assert any("test_fail_TEST_1" in f["type"] for f in failures)

    def test_passes_when_test_is_pass(self):
        scenario = {"assertions": {"testy_pass": ["TEST_1"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(tests_text="TEST_1: PASS"))
        assert not any("test_fail_TEST_1" in f["type"] for f in failures)


@pytest.mark.unit
@pytest.mark.P0
class TestEvaluatorReviews:
    """Evaluator: expected_reviews and review_obecne assertions."""

    def test_fails_when_expected_review_missing(self):
        scenario = {
            "assertions": {"review_obecne": ["REVIEW_17"]},
            "meta": {"expected_reviews": ["REVIEW_17"]},
        }
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {},
            "tests": "",
            "stops_reviews": {"reviews": ["REVIEW_20"]},
        })
        review_failures = [f for f in failures if f["type"] == "missing_review"]
        assert len(review_failures) >= 2  # One from meta, one from assertions

    def test_passes_when_review_present(self):
        scenario = {
            "assertions": {"review_obecne": ["REVIEW_16"]},
            "meta": {"expected_reviews": ["REVIEW_16"]},
        }
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {},
            "tests": "",
            "stops_reviews": {"reviews": ["REVIEW_16", "REVIEW_20"]},
        })
        assert not any(f["type"] == "missing_review" for f in failures)


@pytest.mark.unit
@pytest.mark.P1
class TestEvaluatorNexus:
    """Evaluator: nexus assertions."""

    def test_fails_when_nexus_missing(self):
        scenario = {"assertions": {"nexus": 1.0}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"przychody_roczne": {"IP": 10000}},
            "tests": "",
            "stops_reviews": {},
        })
        assert any(f["type"] == "nexus_missing" for f in failures)

    def test_passes_when_nexus_correct(self):
        scenario = {"assertions": {"nexus": 1.0}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"nexus": 1.0},
            "tests": "",
            "stops_reviews": {},
        })
        assert not any("nexus" in f["type"] for f in failures)


@pytest.mark.unit
@pytest.mark.P1
class TestEvaluatorKluczMix:
    """Evaluator: klucz_MIX_metoda and klucz_MIX_źródło assertions."""

    def test_fails_when_method_mismatch(self):
        scenario = {"assertions": {"klucz_MIX_metoda": "przychodowa_roczna"}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"alokacja": {"koszty_MIX": {"metoda": "czasowa_W"}}},
            "tests": "",
            "stops_reviews": {},
        })
        assert any(f["type"] == "klucz_mix_metoda_mismatch" for f in failures)

    def test_passes_when_method_correct(self):
        scenario = {"assertions": {"klucz_MIX_metoda": "przychodowa_roczna"}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"alokacja": {"koszty_MIX": {"metoda": "przychodowa_roczna"}}},
            "tests": "",
            "stops_reviews": {},
        })
        assert not any("klucz_mix_metoda" in f["type"] for f in failures)

    def test_fails_when_source_mismatch(self):
        scenario = {"assertions": {"klucz_MIX_źródło": "interpretacja_KIS"}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"alokacja": {"koszty_MIX": {"źródło": "domyślna"}}},
            "tests": "",
            "stops_reviews": {},
        })
        assert any(f["type"] == "klucz_mix_zrodlo_mismatch" for f in failures)


@pytest.mark.unit
@pytest.mark.P1
class TestEvaluatorWUsedForMix:
    """Evaluator: nie_używaj_W_do_MIX assertion."""

    def test_fails_when_w_used_for_mix(self):
        scenario = {"assertions": {"nie_używaj_W_do_MIX": True}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"alokacja": {"koszty_MIX": {"metoda": "przychodowa_roczna"}}},
            "tests": "",
            "classifications": "Koszty MIX: w = 87.5 (czasowy)\n",
            "stops_reviews": {},
        })
        assert any(f["type"] == "w_used_for_mix" for f in failures)

    def test_passes_when_w_not_used_for_mix(self):
        scenario = {"assertions": {"nie_używaj_W_do_MIX": True}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"alokacja": {"koszty_MIX": {"metoda": "przychodowa_roczna"}}},
            "tests": "",
            "classifications": "Koszty MIX: przychodowa_roczna\n",
            "stops_reviews": {},
        })
        assert not any(f["type"] == "w_used_for_mix" for f in failures)


@pytest.mark.unit
@pytest.mark.P1
class TestEvaluatorAlokacjaMultiIp:
    """Evaluator: alokacja_multi_ip assertions."""

    def test_fails_when_value_missing(self):
        scenario = {"assertions": {"alokacja_multi_ip": {"stage1_software_share": 8000}}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {},
            "tests": "",
            "classifications": "",
            "stops_reviews": {},
        })
        assert any(f["type"] == "alokacja_multi_ip_missing" for f in failures)

    def test_passes_when_value_correct(self):
        scenario = {"assertions": {"alokacja_multi_ip": {"stage1_software_share": 8000}}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {"stage1_software_share": 8000},
            "tests": "",
            "classifications": "",
            "stops_reviews": {},
        })
        assert not any("alokacja_multi_ip" in f["type"] for f in failures)


@pytest.mark.unit
@pytest.mark.P0
class TestEvaluatorSuccessCase:
    """Evaluator: success case with all assertions matching."""

    def test_no_failures_when_everything_matches(self):
        scenario = {
            "assertions": {
                "testy_pass": ["TEST_1", "TEST_7"],
                "klucz_MIX_metoda": "przychodowa_roczna",
                "klucz_MIX_źródło": "interpretacja_KIS",
                "nie_używaj_W_do_MIX": True,
            },
            "meta": {},
        }
        e = Evaluator(scenario)
        failures, _ = e.evaluate({
            "result": {
                "nexus": 0.75,
                "alokacja": {"koszty_MIX": {"metoda": "przychodowa_roczna", "źródło": "interpretacja_KIS"}},
            },
            "tests": "TEST_1: PASS\nTEST_7: PASS",
            "classifications": "Koszty MIX: przychodowa_roczna\nKoszty IP: IP",
            "stops_reviews": {"stops": [], "reviews": []},
        })
        assert len(failures) == 0, f"Expected 0 failures, got {failures}"


@pytest.mark.unit
@pytest.mark.P0
class TestFailClosed:
    """Fail-closed behavior: unexpected FAILs cause errors."""

    def _make_parsed(self, tests_text="", result=None, stops_reviews=None):
        return {
            "tests": tests_text,
            "result": result or {},
            "stops_reviews": stops_reviews or {},
        }

    def test_unexpected_fail_causes_error(self):
        """TEST_7 FAIL but not in testy_fail → error."""
        scenario = {"assertions": {"testy_fail": ["TEST_3"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(
            tests_text="TEST_3: FAIL\nTEST_7: FAIL",
        ))
        assert any("unexpected_fail_TEST_7" in f["type"] for f in failures)

    def test_expected_fail_no_error(self):
        """TEST_3 FAIL and in testy_fail → no unexpected FAIL error."""
        scenario = {"assertions": {"testy_fail": ["TEST_3"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(
            tests_text="TEST_3: FAIL",
        ))
        unexpected = [f for f in failures if "unexpected_fail" in f["type"]]
        assert len(unexpected) == 0, f"Got unexpected failures: {unexpected}"

    def test_unexpected_fail_only_for_not_in_testy_fail(self):
        """Mix: TEST_3 in testy_fail, TEST_7 not → only TEST_7 errors."""
        scenario = {"assertions": {"testy_fail": ["TEST_3"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(
            tests_text="TEST_3: FAIL\nTEST_7: FAIL",
        ))
        unexpected = [f for f in failures if "unexpected_fail" in f["type"]]
        assert any("unexpected_fail_TEST_7" in f["type"] for f in unexpected)
        assert not any("unexpected_fail_TEST_3" in f["type"] for f in unexpected)

    def test_no_error_when_all_pass(self):
        """All tests PASS, no unexpected failures."""
        scenario = {"assertions": {"testy_pass": ["TEST_1", "TEST_2"]}}
        e = Evaluator(scenario)
        failures, _ = e.evaluate(self._make_parsed(
            tests_text="TEST_1: PASS\nTEST_2: PASS",
        ))
        unexpected = [f for f in failures if "unexpected_fail" in f["type"]]
        assert len(unexpected) == 0


@pytest.mark.unit
@pytest.mark.P1
class TestFindNonIpTax:
    """Tests for _find_non_ip_tax — must handle podatek_NIE_finalny."""

    def test_find_non_ip_tax_podatek_NIE_finalny(self):
        """podatek_NIE_finalny in nested podatek dict should be found."""
        result = {"podatek": {"podatek_NIE_finalny": 2121}}
        assert _find_non_ip_tax(result) == 2121.0


@pytest.mark.unit
@pytest.mark.P2
class TestFindValue:
    """Tests for _find_value — must probe przychody_roczne.{IP,NIE}."""

    def test_find_value_nested_przychody_roczne(self):
        """_find_value should probe przychody_roczne.{IP,NIE} when flat keys miss."""
        result = {"przychody_roczne": {"IP": 15000.0, "NIE": 5000.0}}
        assert _find_value(result, ["przychod_IP", "przychody_IP"]) == 15000.0
        assert _find_value(result, ["przychod_NIE", "przychody_NIE"]) == 5000.0
