"""Fail-closed semantic evaluator for model responses."""

from __future__ import annotations

import math
from typing import Any

from .oracle import compute_reference

KNOWN_ASSERTIONS = {
    "W_miesieczne",
    "alokacja_multi_ip",
    "klucz_MIX_metoda",
    "klucz_MIX_źródło",
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
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _path(mapping: Any, dotted: str) -> Any:
    current = mapping
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _codes(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().upper() for item in value}


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


def _monthly_map(value: Any) -> dict[str, float]:
    if not isinstance(value, list):
        return {}
    result: dict[str, float] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        month = str(entry.get("miesiąc", ""))
        number = _number(entry.get("wartość"))
        if month and number is not None:
            result[month] = number
    return result


def _classification_map(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("opis", "")).strip().casefold()
        if description:
            result[description] = entry
    return result


def _multi_ip_map(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
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
                    result[name] = amount
    return result


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
                "result.podatek.podstawa_IP",
                "result.podatek.podstawa_NIE",
                "result.podatek.podatek_IP",
                "result.podatek.podatek_NIE_finalny",
                "result.podatek.podatek_całościowy",
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
        expected = _monthly_map(self.reference.get("monthly_W"))
        observed = _monthly_map(actual.get("monthly_W"))
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
        expected_stops = _codes(expected_section.get("stops"))
        actual_stops = _codes(actual_section.get("stops"))
        if actual_stops != expected_stops:
            failures.append(
                _failure("stops", "stop codes differ", sorted(expected_stops), sorted(actual_stops))
            )
        expected_reviews = _codes(expected_section.get("reviews"))
        actual_reviews = _codes(actual_section.get("reviews"))
        if actual_reviews != expected_reviews:
            failures.append(
                _failure(
                    "reviews",
                    "review codes differ",
                    sorted(expected_reviews),
                    sorted(actual_reviews),
                )
            )
        expected_warnings = _codes(expected_section.get("warnings"))
        actual_warnings = _codes(actual_section.get("warnings"))
        if actual_warnings != expected_warnings:
            failures.append(
                _failure(
                    "warnings",
                    "warning codes differ",
                    sorted(expected_warnings),
                    sorted(actual_warnings),
                )
            )

    def _compare_classifications(
        self,
        actual: dict[str, Any],
        failures: list[dict[str, Any]],
    ) -> None:
        expected = _classification_map(self.reference.get("classifications"))
        observed = _classification_map(actual.get("classifications"))
        if set(observed) != set(expected):
            failures.append(
                _failure(
                    "classification_keys",
                    "cost descriptions differ",
                    sorted(expected),
                    sorted(observed),
                )
            )
        for description, expected_entry in expected.items():
            actual_entry = observed.get(description)
            if actual_entry is None:
                continue
            for key in ("basket", "nexus_source", "nexus_basket"):
                if actual_entry.get(key) != expected_entry.get(key):
                    failures.append(
                        _failure(
                            "classification_mismatch",
                            f"{description}.{key}",
                            expected_entry.get(key),
                            actual_entry.get(key),
                        )
                    )
            for key in ("amount", "ip_amount", "non_ip_amount", "nexus_amount"):
                expected_value = _number(expected_entry.get(key))
                actual_value = _number(actual_entry.get(key))
                if (
                    actual_value is None
                    or expected_value is None
                    or abs(actual_value - expected_value) > 0.011
                ):
                    failures.append(
                        _failure(
                            "classification_amount",
                            f"{description}.{key}",
                            expected_value,
                            actual_value,
                        )
                    )

    def _compare_multi_ip(self, actual: dict[str, Any], failures: list[dict[str, Any]]) -> None:
        expected = _multi_ip_map(_path(self.reference, "result.alokacja_multi_ip"))
        observed = _multi_ip_map(_path(actual, "result.alokacja_multi_ip"))
        if expected is None:
            if observed is not None:
                failures.append(
                    _failure("multi_ip_unexpected", "alokacja_multi_ip", None, observed)
                )
            return
        if observed is None:
            failures.append(_failure("multi_ip_missing", "alokacja_multi_ip"))
            return
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

        monthly = _monthly_map(actual.get("monthly_W"))
        for month, expected in assertions.get("W_miesieczne", {}).items():
            observed = monthly.get(str(month))
            if observed is None or abs(observed - float(expected)) > 0.011:
                failures.append(_failure("assertion_w", str(month), expected, observed))

        classifications = _classification_map(actual.get("classifications"))
        for description, basket in assertions.get("koszty_koszyk", {}).items():
            entry = classifications.get(str(description).casefold())
            observed = entry.get("basket") if entry else None
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
        if assertions.get("nie_używaj_W_do_MIX") and mix.get("metoda") == "czasowa_W":
            failures.append(_failure("assertion_w_for_mix", "W was used for MIX"))

        if assertions.get("mix_w_nexus_A") is False:
            for entry in classifications.values():
                if entry.get("basket") == "MIX" and entry.get("nexus_basket") == "A":
                    failures.append(_failure("assertion_mix_in_a", str(entry.get("opis"))))

        if assertions.get("roznice_kursowe_w_IP") is False:
            for entry in classifications.values():
                if "kurs" in str(entry.get("opis", "")).lower() and entry.get("basket") == "IP":
                    failures.append(_failure("assertion_fx_in_ip", str(entry.get("opis"))))

        if assertions.get("zus_dubel") is False and observed_tests.get("TEST_3") != "PASS":
            failures.append(_failure("assertion_zus_double", "TEST_3 must pass"))

        if "alokacja_multi_ip" in assertions:
            observed_multi = _multi_ip_map(_path(actual, "result.alokacja_multi_ip")) or {}
            for key, expected in assertions["alokacja_multi_ip"].items():
                observed = observed_multi.get(key)
                if observed is None or abs(observed - float(expected)) > 0.011:
                    failures.append(_failure("assertion_multi_ip", key, expected, observed))
