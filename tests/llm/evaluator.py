"""Fail-closed semantic evaluator for model responses."""

from __future__ import annotations

import json
from typing import Any

from python_helper.input_validation import strict_number

from .oracle import compute_reference

KNOWN_ASSERTIONS = {
    "W_miesieczne",
    "alokacja_multi_ip",
    "klucz_MIX_metoda",
    "klucz_MIX_źródło",
    "klucz_MIX_wartość",
    "koszty_koszyk",
    "mix_w_nexus_A",
    "nexus",
    "nexus_range",
    "nie_używaj_W_do_MIX",
    "podatek_IP_range",
    "podatek_NIE_range",
    "przychod_IP_roczny_range",
    "przychod_NIE_roczny_range",
    "review_obecne",
    "roznice_kursowe_w_IP",
    "stops",
    "testy_fail",
    "testy_pass",
    "termomodernization_carry_over",
    "zus_dubel",
}


def _failure(kind: str, message: str, expected: Any = None, actual: Any = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": kind, "message": message}
    if expected is not None:
        value["expected"] = expected
    if actual is not None:
        value["actual"] = actual
    return value


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return strict_number(value, "reported number")
    except ValueError:
        return None


def _path(mapping: Any, dotted: str) -> Any:
    current = mapping
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _code_set(value: Any) -> tuple[set[str], set[str]]:
    if not isinstance(value, list):
        return set(), set()
    normalized = [str(item).strip().upper() for item in value]
    duplicates = {code for code in normalized if normalized.count(code) > 1}
    return set(normalized), duplicates


def _codes(value: Any) -> set[str]:
    return _code_set(value)[0]


def _tests(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, status in value.items():
        normalized = str(key).upper().replace(" ", "_").replace("-", "_")
        if normalized.startswith("TEST") and not normalized.startswith("TEST_"):
            normalized = normalized.replace("TEST", "TEST_", 1)
        result[normalized] = str(status).upper()
    return result


def _monthly_map(value: Any) -> tuple[dict[str, float], set[str]]:
    if not isinstance(value, list):
        return {}, set()
    result: dict[str, float] = {}
    duplicates: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            continue
        month = str(entry.get("miesiąc", ""))
        number = _number(entry.get("wartość"))
        if month and number is not None:
            if month in result:
                duplicates.add(month)
            result[month] = number
    return result, duplicates


def _classification_groups(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, list):
        return {}
    result: dict[str, list[dict[str, Any]]] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("opis", "")).strip().casefold()
        if description:
            result.setdefault(description, []).append(entry)
    return result


def _entry_sort_key(entry: dict[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _multi_ip_map(value: Any) -> tuple[dict[str, float], set[str]] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        return {}, set()
    result: dict[str, float] = {}
    duplicates: set[str] = set()
    stage1 = _number(value.get("stage1_software_share"))
    non_software = _number(value.get("stage1_non_software_share"))
    if stage1 is not None:
        result["stage1_software_share"] = stage1
    if non_software is not None:
        result["stage1_non_software_share"] = non_software
    allocations = value.get("allocations")
    if isinstance(allocations, list):
        for entry in allocations:
            if isinstance(entry, dict):
                name = str(entry.get("ip", ""))
                amount = _number(entry.get("amount"))
                if name and amount is not None:
                    if name in result:
                        duplicates.add(name)
                    result[name] = amount
    return result, duplicates


class Evaluator:
    """Compare a model output with an independent deterministic reference."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario
        self.reference = compute_reference(scenario)

    def evaluate(self, parsed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        failures: list[dict[str, Any]] = []
        warnings: list[str] = []
        if not isinstance(parsed, dict):
            return ([_failure("response_type", "response root must be an object")], warnings)

        assertions = self.scenario.get("assertions")
        if not isinstance(assertions, dict) or not assertions:
            return ([_failure("scenario_config", "assertions must be non-empty")], warnings)
        for key in sorted(set(assertions) - KNOWN_ASSERTIONS):
            failures.append(_failure("unknown_assertion", key))

        self._compare_status(parsed, failures)
        self._compare_numbers(parsed, failures)
        self._compare_monthly_w(parsed, failures)
        self._compare_tests(parsed, failures)
        self._compare_codes(parsed, failures)
        self._compare_classifications(parsed, failures)
        self._compare_multi_ip(parsed, failures)
        self._evaluate_assertions(parsed, assertions, failures)
        return failures, warnings

    def _compare_status(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected_status = self.reference["status"]
        if actual.get("status") != expected_status:
            failures.append(
                _failure("status", "incorrect status", expected_status, actual.get("status"))
            )
        if expected_status == "STOPPED":
            for key in (
                "result.przychody_roczne.IP",
                "result.przychody_roczne.NIE",
                "result.koszty_roczne.IP",
                "result.koszty_roczne.NIE",
                "result.koszty_roczne.MIX",
                "result.koszty_roczne.WYKLUCZONE",
                "result.nexus_koszty.A",
                "result.nexus_koszty.B",
                "result.nexus_koszty.C",
                "result.nexus_koszty.D",
                "result.nexus_koszty.poza_nexus",
                "result.nexus",
                "result.dochód_IP",
                "result.dochód_NIE",
                "result.podatek.podstawa_IP",
                "result.podatek.podstawa_NIE",
                "result.podatek.podatek_IP",
                "result.podatek.podatek_NIE_finalny",
                "result.podatek.podatek_całościowy",
                "result.podatek.nadpłata_lub_dopłata",
                "result.podatek.termomodernization_carry_over",
            ):
                value = _number(_path(actual, key))
                if value is None or value != 0:
                    failures.append(_failure("stop_nonzero", key, 0, value))

    def _compare_numbers(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        money_paths = (
            "result.przychody_roczne.IP",
            "result.przychody_roczne.NIE",
            "result.koszty_roczne.IP",
            "result.koszty_roczne.NIE",
            "result.koszty_roczne.MIX",
            "result.koszty_roczne.WYKLUCZONE",
            "result.nexus_koszty.A",
            "result.nexus_koszty.B",
            "result.nexus_koszty.C",
            "result.nexus_koszty.D",
            "result.nexus_koszty.poza_nexus",
            "result.dochód_IP",
            "result.dochód_NIE",
            "result.podatek.podstawa_IP",
            "result.podatek.podstawa_NIE",
            "result.podatek.podatek_IP",
            "result.podatek.podatek_NIE_finalny",
            "result.podatek.podatek_całościowy",
            "result.podatek.nadpłata_lub_dopłata",
            "result.podatek.termomodernization_carry_over",
        )
        for path in money_paths:
            expected = _number(_path(self.reference, path))
            observed = _number(_path(actual, path))
            if expected is None:
                continue
            if observed is None or abs(observed - expected) > 0.011:
                failures.append(_failure("numeric_mismatch", path, expected, observed))

        expected_nexus = _number(_path(self.reference, "result.nexus"))
        actual_nexus = _number(_path(actual, "result.nexus"))
        if (
            actual_nexus is None
            or expected_nexus is None
            or abs(actual_nexus - expected_nexus) > 1e-6
        ):
            failures.append(
                _failure("nexus_mismatch", "result.nexus", expected_nexus, actual_nexus)
            )

        expected_mix = _path(self.reference, "result.klucz_MIX")
        actual_mix = _path(actual, "result.klucz_MIX")
        if not isinstance(actual_mix, dict):
            failures.append(_failure("mix_missing", "result.klucz_MIX"))
            return
        for key in ("metoda", "źródło", "status"):
            if actual_mix.get(key) != expected_mix.get(key):
                failures.append(
                    _failure(
                        "mix_mismatch",
                        f"klucz_MIX.{key}",
                        expected_mix.get(key),
                        actual_mix.get(key),
                    )
                )
        expected_value = _number(expected_mix.get("wartość"))
        actual_value = _number(actual_mix.get("wartość"))
        if expected_mix.get("wartość") is None:
            if actual_mix.get("wartość") is not None:
                failures.append(
                    _failure("mix_value", "expected null", None, actual_mix.get("wartość"))
                )
        elif (
            actual_value is None
            or expected_value is None
            or abs(actual_value - expected_value) > 1e-6
        ):
            failures.append(_failure("mix_value", "incorrect key", expected_value, actual_value))

    def _compare_monthly_w(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected, expected_duplicates = _monthly_map(self.reference.get("monthly_W"))
        observed, observed_duplicates = _monthly_map(actual.get("monthly_W"))
        if expected_duplicates:
            failures.append(
                _failure(
                    "reference_duplicate_month",
                    "oracle monthly_W has duplicate months",
                    actual=sorted(expected_duplicates),
                )
            )
        if observed_duplicates:
            failures.append(
                _failure(
                    "duplicate_month",
                    "monthly_W contains duplicate months",
                    actual=sorted(observed_duplicates),
                )
            )
        if set(observed) != set(expected):
            failures.append(
                _failure("monthly_w_keys", "month set differs", sorted(expected), sorted(observed))
            )
        for month, expected_value in expected.items():
            actual_value = observed.get(month)
            if actual_value is None or abs(actual_value - expected_value) > 0.011:
                failures.append(_failure("monthly_w", month, expected_value, actual_value))

    def _compare_tests(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected = _tests(self.reference.get("tests"))
        observed = _tests(actual.get("tests"))
        for test_id in (f"TEST_{index}" for index in range(1, 10)):
            if observed.get(test_id) != expected.get(test_id):
                failures.append(
                    _failure(
                        "test_oracle_mismatch",
                        test_id,
                        expected.get(test_id),
                        observed.get(test_id),
                    )
                )

    def _compare_codes(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected_section = self.reference["stops_reviews"]
        actual_section = actual.get("stops_reviews")
        if not isinstance(actual_section, dict):
            failures.append(_failure("codes_missing", "stops_reviews"))
            return
        for key in ("stops", "reviews", "warnings"):
            expected_codes, expected_duplicates = _code_set(expected_section.get(key))
            actual_codes, actual_duplicates = _code_set(actual_section.get(key))
            if expected_duplicates:
                failures.append(
                    _failure(f"reference_duplicate_{key}", key, actual=sorted(expected_duplicates))
                )
            if actual_duplicates:
                failures.append(_failure(f"duplicate_{key}", key, actual=sorted(actual_duplicates)))
            if actual_codes != expected_codes:
                failures.append(
                    _failure(
                        key,
                        f"{key} codes differ",
                        sorted(expected_codes),
                        sorted(actual_codes),
                    )
                )

    def _compare_classifications(
        self,
        actual: dict[str, Any],
        failures: list[dict[str, Any]],
    ) -> None:
        expected = _classification_groups(self.reference.get("classifications"))
        observed = _classification_groups(actual.get("classifications"))
        if set(observed) != set(expected):
            failures.append(
                _failure(
                    "classification_keys",
                    "cost descriptions differ",
                    sorted(expected),
                    sorted(observed),
                )
            )
        for description, expected_entries in expected.items():
            actual_entries = observed.get(description, [])
            if len(actual_entries) != len(expected_entries):
                failures.append(
                    _failure(
                        "classification_count",
                        description,
                        len(expected_entries),
                        len(actual_entries),
                    )
                )
                continue
            for index, (expected_entry, actual_entry) in enumerate(
                zip(
                    sorted(expected_entries, key=_entry_sort_key),
                    sorted(actual_entries, key=_entry_sort_key),
                    strict=True,
                )
            ):
                for key in (
                    "basket",
                    "allocation_method",
                    "allocation_source",
                    "nexus_source",
                    "nexus_basket",
                ):
                    if actual_entry.get(key) != expected_entry.get(key):
                        failures.append(
                            _failure(
                                "classification_mismatch",
                                f"{description}[{index}].{key}",
                                expected_entry.get(key),
                                actual_entry.get(key),
                            )
                        )
                for key in (
                    "amount",
                    "allocation_key",
                    "ip_amount",
                    "non_ip_amount",
                    "nexus_amount",
                ):
                    if expected_entry.get(key) is None:
                        if actual_entry.get(key) is not None:
                            failures.append(
                                _failure(
                                    "classification_amount",
                                    f"{description}[{index}].{key}",
                                    None,
                                    actual_entry.get(key),
                                )
                            )
                        continue
                    expected_value = _number(expected_entry.get(key))
                    actual_value = _number(actual_entry.get(key))
                    tolerance = 1e-6 if key == "allocation_key" else 0.011
                    if (
                        actual_value is None
                        or expected_value is None
                        or abs(actual_value - expected_value) > tolerance
                    ):
                        failures.append(
                            _failure(
                                "classification_amount",
                                f"{description}[{index}].{key}",
                                expected_value,
                                actual_value,
                            )
                        )

    def _compare_multi_ip(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected_result = _multi_ip_map(_path(self.reference, "result.alokacja_multi_ip"))
        observed_result = _multi_ip_map(_path(actual, "result.alokacja_multi_ip"))
        if expected_result is None:
            if observed_result is not None:
                failures.append(
                    _failure("multi_ip_unexpected", "alokacja_multi_ip", None, observed_result[0])
                )
            return
        if observed_result is None:
            failures.append(_failure("multi_ip_missing", "alokacja_multi_ip"))
            return
        expected, expected_duplicates = expected_result
        observed, observed_duplicates = observed_result
        if expected_duplicates:
            failures.append(
                _failure(
                    "reference_duplicate_multi_ip",
                    "oracle duplicate IP names",
                    actual=sorted(expected_duplicates),
                )
            )
        if observed_duplicates:
            failures.append(
                _failure(
                    "duplicate_multi_ip", "duplicate IP names", actual=sorted(observed_duplicates)
                )
            )
        if set(observed) != set(expected):
            failures.append(
                _failure(
                    "multi_ip_keys", "allocation keys differ", sorted(expected), sorted(observed)
                )
            )
        for key, expected_value in expected.items():
            actual_value = observed.get(key)
            if actual_value is None or abs(actual_value - expected_value) > 0.011:
                failures.append(_failure("multi_ip", key, expected_value, actual_value))

    def _evaluate_assertions(
        self,
        actual: dict[str, Any],
        assertions: dict[str, Any],
        failures: list[dict[str, Any]],
    ) -> None:
        def check_range(key: str, path: str) -> None:
            if key not in assertions:
                return
            expected_range = assertions[key]
            observed = _number(_path(actual, path))
            if (
                not isinstance(expected_range, list)
                or len(expected_range) != 2
                or observed is None
                or not float(expected_range[0]) <= observed <= float(expected_range[1])
            ):
                failures.append(_failure("assertion_range", key, expected_range, observed))

        check_range("nexus_range", "result.nexus")
        check_range("podatek_IP_range", "result.podatek.podatek_IP")
        check_range("podatek_NIE_range", "result.podatek.podatek_NIE_finalny")
        check_range("przychod_IP_roczny_range", "result.przychody_roczne.IP")
        check_range("przychod_NIE_roczny_range", "result.przychody_roczne.NIE")

        if "termomodernization_carry_over" in assertions:
            observed = _number(_path(actual, "result.podatek.termomodernization_carry_over"))
            expected = float(assertions["termomodernization_carry_over"])
            if observed is None or abs(observed - expected) > 0.011:
                failures.append(
                    _failure(
                        "assertion_carry_over",
                        "termomodernization_carry_over",
                        expected,
                        observed,
                    )
                )

        if "nexus" in assertions:
            observed = _number(_path(actual, "result.nexus"))
            expected = float(assertions["nexus"])
            if observed is None or abs(observed - expected) > 1e-6:
                failures.append(_failure("assertion_nexus", "nexus", expected, observed))

        observed_tests = _tests(actual.get("tests"))
        for test_id in assertions.get("testy_pass", []):
            normalized = str(test_id).upper().replace(" ", "_").replace("-", "_")
            if normalized.startswith("TEST") and not normalized.startswith("TEST_"):
                normalized = normalized.replace("TEST", "TEST_", 1)
            if observed_tests.get(normalized) != "PASS":
                failures.append(
                    _failure(
                        "assertion_test_pass", normalized, "PASS", observed_tests.get(normalized)
                    )
                )
        for test_id in assertions.get("testy_fail", []):
            normalized = str(test_id).upper().replace(" ", "_").replace("-", "_")
            if normalized.startswith("TEST") and not normalized.startswith("TEST_"):
                normalized = normalized.replace("TEST", "TEST_", 1)
            if observed_tests.get(normalized) != "FAIL":
                failures.append(
                    _failure(
                        "assertion_test_fail", normalized, "FAIL", observed_tests.get(normalized)
                    )
                )

        actual_codes = (
            actual.get("stops_reviews") if isinstance(actual.get("stops_reviews"), dict) else {}
        )
        for code in assertions.get("stops", []):
            if str(code).upper() not in _codes(actual_codes.get("stops")):
                failures.append(_failure("assertion_stop", str(code)))
        for code in assertions.get("review_obecne", []):
            if str(code).upper() not in _codes(actual_codes.get("reviews")):
                failures.append(_failure("assertion_review", str(code)))

        monthly, monthly_duplicates = _monthly_map(actual.get("monthly_W"))
        if monthly_duplicates:
            failures.append(
                _failure(
                    "assertion_duplicate_month", "monthly_W", actual=sorted(monthly_duplicates)
                )
            )
        for month, expected in assertions.get("W_miesieczne", {}).items():
            observed = monthly.get(str(month))
            if observed is None or abs(observed - float(expected)) > 0.011:
                failures.append(_failure("assertion_w", str(month), expected, observed))

        classifications = _classification_groups(actual.get("classifications"))
        for description, basket in assertions.get("koszty_koszyk", {}).items():
            entries = classifications.get(str(description).casefold(), [])
            observed = entries[0].get("basket") if len(entries) == 1 else None
            if observed != basket:
                failures.append(_failure("assertion_basket", description, basket, observed))

        mix = _path(actual, "result.klucz_MIX")
        if not isinstance(mix, dict):
            mix = {}
        if "klucz_MIX_metoda" in assertions and mix.get("metoda") != assertions["klucz_MIX_metoda"]:
            failures.append(
                _failure(
                    "assertion_mix_method",
                    "metoda",
                    assertions["klucz_MIX_metoda"],
                    mix.get("metoda"),
                )
            )
        if "klucz_MIX_źródło" in assertions and mix.get("źródło") != assertions["klucz_MIX_źródło"]:
            failures.append(
                _failure(
                    "assertion_mix_source",
                    "źródło",
                    assertions["klucz_MIX_źródło"],
                    mix.get("źródło"),
                )
            )
        if "klucz_MIX_wartość" in assertions:
            expected_key = float(assertions["klucz_MIX_wartość"])
            observed_key = _number(mix.get("wartość"))
            if observed_key is None or abs(observed_key - expected_key) > 1e-6:
                failures.append(
                    _failure("assertion_mix_value", "wartość", expected_key, observed_key)
                )
        if assertions.get("nie_używaj_W_do_MIX") and mix.get("metoda") == "czasowa_W":
            failures.append(_failure("assertion_w_for_mix", "W was used for MIX"))

        if assertions.get("mix_w_nexus_A") is False:
            for entries in classifications.values():
                for entry in entries:
                    if entry.get("basket") == "MIX" and entry.get("nexus_basket") == "A":
                        failures.append(_failure("assertion_mix_in_a", str(entry.get("opis"))))

        if assertions.get("roznice_kursowe_w_IP") is False:
            for entries in classifications.values():
                for entry in entries:
                    if "kurs" in str(entry.get("opis", "")).lower() and entry.get("basket") == "IP":
                        failures.append(_failure("assertion_fx_in_ip", str(entry.get("opis"))))

        if assertions.get("zus_dubel") is False and observed_tests.get("TEST_3") != "PASS":
            failures.append(_failure("assertion_zus_double", "TEST_3 must pass"))

        if "alokacja_multi_ip" in assertions:
            observed_result = _multi_ip_map(_path(actual, "result.alokacja_multi_ip"))
            observed_multi = observed_result[0] if observed_result is not None else {}
            for key, expected in assertions["alokacja_multi_ip"].items():
                observed = observed_multi.get(key)
                if observed is None or abs(observed - float(expected)) > 0.011:
                    failures.append(_failure("assertion_multi_ip", key, expected, observed))
