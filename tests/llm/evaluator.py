from __future__ import annotations

from typing import Any


class Evaluator:
    """Evaluates LLM output against scenario assertions (HARD / RANGE / SOFT)."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario

    @staticmethod
    def _normalize_tests(tests: Any) -> str:
        if isinstance(tests, str):
            return tests
        if isinstance(tests, dict):
            return "\n".join(f"{k}: {v}" for k, v in tests.items())
        return str(tests) if tests else ""

    @staticmethod
    def _normalize_classifications(classifications: Any) -> str:
        if isinstance(classifications, str):
            return classifications
        if isinstance(classifications, list):
            lines = []
            for item in classifications:
                if isinstance(item, dict):
                    parts = [f"{k}: {v}" for k, v in item.items()]
                    lines.append(" | ".join(parts))
                else:
                    lines.append(str(item))
            return "\n".join(lines)
        return str(classifications) if classifications else ""

    @staticmethod
    def _normalize_monthly_w(monthly_w: Any) -> str:
        if isinstance(monthly_w, str):
            return monthly_w
        if isinstance(monthly_w, dict):
            return "\n".join(f"{k}: {v}" for k, v in monthly_w.items())
        return str(monthly_w) if monthly_w else ""

    def evaluate(self, parsed: dict[str, Any]) -> tuple[list[dict], list[str]]:
        """Return (failures, warnings). failures = HARD/RANGE errors, warnings = SOFT."""
        failures: list[dict] = []
        warnings: list[str] = []

        assertions = self.scenario.get("assertions", {})
        if not assertions:
            scenario_id = self.scenario.get("meta", {}).get("id", "unknown")
            print(f"[EVALUATOR] WARNING: Scenario '{scenario_id}' has no assertions — passing by default")
            return failures, warnings

        # Check description consistency
        try:
            description_errors = _check_description_consistency(self.scenario)
            if description_errors:
                failures.extend(description_errors)
        except Exception:
            pass

        result = parsed.get("result") or {}
        if isinstance(result, str):
            failures.append({"type": "parse_error", "message": "Nie udało się sparsować <result> jako YAML"})
            return failures, warnings

        stops_reviews = parsed.get("stops_reviews") or {}

        raw_tests = parsed.get("tests") or ""
        raw_classifications = parsed.get("classifications") or ""
        raw_monthly_w = parsed.get("monthly_W") or ""
        tests_text = self._normalize_tests(raw_tests)
        classifications_text = self._normalize_classifications(raw_classifications)
        monthly_w_text = self._normalize_monthly_w(raw_monthly_w)

        # --- Per-section validation ---
        needs_result = any(k in assertions for k in (
            "nexus", "nexus_range", "podatek_IP_range", "podatek_NIE_range",
            "przychod_IP_roczny_range", "przychod_NIE_roczny_range",
            "alokacja_multi_ip", "klucz_MIX_metoda", "klucz_MIX_źródło",
        ))
        needs_monthly_w = "W_miesieczne" in assertions
        needs_tests = bool(assertions.get("testy_pass") or assertions.get("testy_fail"))
        needs_stops_reviews = any(k in assertions for k in (
            "stops", "review_obecne", "warnings", "soft_warnings",
        )) or bool(self.scenario.get("meta", {}).get("expected_stops")
                  or self.scenario.get("meta", {}).get("expected_reviews"))
        needs_classifications = any(k in assertions for k in (
            "koszty_koszyk", "nie_używaj_W_do_MIX",
        )) or assertions.get("roznice_kursowe_w_IP") is False

        if needs_result and not result:
            failures.append({
                "type": "section_missing_result",
                "message": "Brak sekcji <result>, a scenariusz wymaga danych wynikowych",
            })
        if needs_monthly_w and not raw_monthly_w:
            failures.append({
                "type": "section_missing_monthly_w",
                "message": "Brak sekcji <monthly_W>, a scenariusz wymaga W_miesieczne",
            })
        if needs_tests and not tests_text:
            failures.append({
                "type": "section_missing_tests",
                "message": "Brak sekcji <tests>, a scenariusz wymaga weryfikacji testów",
            })
        if needs_stops_reviews and not stops_reviews:
            failures.append({
                "type": "section_missing_stops_reviews",
                "message": "Brak sekcji <stops_reviews>, a scenariusz wymaga STOP/REVIEW",
            })
        if needs_classifications and not raw_classifications:
            # Only fail if the assertion actually needs to check something
            if assertions.get("koszty_koszyk") or (assertions.get("roznice_kursowe_w_IP") is False and not result):
                failures.append({
                    "type": "section_missing_classifications",
                    "message": "Brak sekcji <classifications>, a scenariusz wymaga klasyfikacji kosztów",
                })

        # --- Validate assertion keys ---
        scenario_id = self.scenario.get("meta", {}).get("id", "unknown")
        key_errors = validate_assertion_keys(assertions, scenario_id)
        for err in key_errors:
            failures.append({
                "type": "unknown_assertion_key",
                "message": err,
            })

        # --- HARD checks ---

        # zus_dubel: TEST_3 musi być PASS gdy zus_dubel=False
        if assertions.get("zus_dubel") is False:
            if _test_failed(tests_text, "TEST_3") or _test_failed(tests_text, "TEST 3"):
                failures.append({
                    "type": "zus_double_dip",
                    "message": "Wykryto podwójne odliczenie ZUS (TEST_3 FAIL)",
                })

        # testy_pass: każdy wymieniony test musi być PASS
        for test_id in assertions.get("testy_pass", []):
            if not tests_text:
                failures.append({
                    "type": f"test_missing_{test_id}",
                    "message": f"Blok <tests> jest pusty lub brak wyników testów, a oczekiwano {test_id}",
                })
            elif not _test_passed(tests_text, test_id):
                failures.append({
                    "type": f"test_fail_{test_id}",
                    "message": f"{test_id} powinien być PASS, ale jest FAIL lub brak jawnego PASS",
                })

        # testy_fail: każdy wymieniony test musi być FAIL
        for test_id in assertions.get("testy_fail", []):
            if not tests_text:
                failures.append({
                    "type": f"test_fail_missing_tests_{test_id}",
                    "message": f"Brak bloku <tests>, a oczekiwano FAIL dla {test_id}",
                })
            elif _test_failed(tests_text, test_id):
                pass  # success — test is FAIL as expected
            elif _test_passed(tests_text, test_id):
                failures.append({
                    "type": f"test_fail_unexpected_pass_{test_id}",
                    "message": f"{test_id} powinien być FAIL, a jest PASS",
                })
            else:
                failures.append({
                    "type": f"test_fail_missing_{test_id}",
                    "message": f"{test_id} powinien być FAIL, ale nie występuje w <tests>",
                })

        # --- Unexpected FAIL: every TEST_n FAIL not in testy_fail → error ---
        fail_ids = assertions.get("testy_fail", [])
        fail_ids_normalized = {normalize_test_key(fid) for fid in fail_ids}
        tests_map = _parse_tests_map(tests_text)
        for test_id_norm, status in tests_map.items():
            if status == "FAIL" and test_id_norm not in fail_ids_normalized:
                failures.append({
                    "type": f"unexpected_fail_{test_id_norm}",
                    "message": f"{test_id_norm} jest FAIL, ale nie ma go w testy_fail — możliwy błąd algorytmu",
                })

        # roznice_kursowe_w_IP: różnice kursowe nie mogą trafić do koszyka IP
        if assertions.get("roznice_kursowe_w_IP") is False:
            if _fx_diff_in_ip(classifications_text):
                failures.append({
                    "type": "fx_diff_in_ip",
                    "message": "Różnice kursowe trafiły do koszyka IP — powinny być w NIE",
                })

        # expected_stops: wszystkie oczekiwane STOP muszą się pojawić
        for expected_stop in self.scenario.get("meta", {}).get("expected_stops", []):
            stops_list = stops_reviews.get("stops", []) if isinstance(stops_reviews, dict) else []
            if not _code_matches(expected_stop, stops_list):
                failures.append({
                    "type": "missing_stop",
                    "message": f"Oczekiwany STOP '{expected_stop}' nie wystąpił",
                })

        # assertions.stops: dodatkowe STOP-y z assertions
        for expected_stop in assertions.get("stops", []):
            stops_list = stops_reviews.get("stops", []) if isinstance(stops_reviews, dict) else []
            if not _code_matches(expected_stop, stops_list):
                failures.append({
                    "type": "missing_stop_assertions",
                    "message": f"Oczekiwany STOP '{expected_stop}' (z assertions.stops) nie wystąpił",
                })

        # expected_reviews: wszystkie oczekiwane REVIEW muszą się pojawić
        for expected_review in self.scenario.get("meta", {}).get("expected_reviews", []):
            if isinstance(stops_reviews, dict):
                reviews_list = stops_reviews.get("reviews", [])
            else:
                reviews_list = [str(stops_reviews)] if stops_reviews else []
            if not _code_matches(expected_review, reviews_list):
                failures.append({
                    "type": "missing_review",
                    "message": f"Oczekiwany REVIEW '{expected_review}' nie wystąpił",
                })

        # --- klucz_MIX_metoda ---
        klucz_mix_metoda = assertions.get("klucz_MIX_metoda")
        if klucz_mix_metoda:
            actual = _find_klucz_mix_field(result, "metoda")
            if actual is None:
                failures.append({
                    "type": "klucz_mix_metoda_missing",
                    "message": "Nie znaleziono metody klucza MIX w wyniku",
                })
            elif str(actual).strip().lower() != str(klucz_mix_metoda).strip().lower():
                failures.append({
                    "type": "klucz_mix_metoda_mismatch",
                    "message": f"klucz_MIX_metoda: oczekiwano '{klucz_mix_metoda}', otrzymano '{actual}'",
                })

        # --- klucz_MIX_źródło ---
        klucz_mix_zrodlo = assertions.get("klucz_MIX_źródło")
        if klucz_mix_zrodlo:
            actual = _find_klucz_mix_field(result, "źródło") or _find_klucz_mix_field(result, "zrodlo")
            if actual is None:
                actual = _nested_get(result, "źródło") or _nested_get(result, "zrodlo")
            if actual is None:
                failures.append({
                    "type": "klucz_mix_zrodlo_missing",
                    "message": "Nie znaleziono źródła klucza MIX w wyniku",
                })
            elif str(actual).strip().lower() != str(klucz_mix_zrodlo).strip().lower():
                failures.append({
                    "type": "klucz_mix_zrodlo_mismatch",
                    "message": f"klucz_MIX_źródło: oczekiwano '{klucz_mix_zrodlo}', otrzymano '{actual}'",
                })

        # --- nie_używaj_W_do_MIX ---
        if assertions.get("nie_używaj_W_do_MIX") is True:
            actual_method = _find_klucz_mix_field(result, "metoda")
            w_used = False
            if actual_method:
                m = str(actual_method).strip().lower()
                if "czasow" in m and ("w" in m.replace("_", "").replace("-", "") or "w_" in m):
                    w_used = True
            if _w_used_for_mix(classifications_text):
                w_used = True
            if w_used:
                failures.append({
                    "type": "w_used_for_mix",
                    "message": "Użyto W do alokacji MIX — powinien być inny klucz (np. przychodowy)",
                })

        # review_obecne: każdy oczekiwany REVIEW musi się pojawić
        for expected_review in assertions.get("review_obecne", []):
            if isinstance(stops_reviews, dict):
                reviews_list = stops_reviews.get("reviews", [])
            else:
                reviews_list = [str(stops_reviews)] if stops_reviews else []
            if not _code_matches(expected_review, reviews_list):
                failures.append({
                    "type": "missing_review",
                    "message": f"Oczekiwany REVIEW '{expected_review}' nie wystąpił",
                })

        # alokacja_multi_ip: sprawdzenie wartości alokacji dwustopniowej
        alokacja_multi = assertions.get("alokacja_multi_ip", {})
        if alokacja_multi:
            for field_key, expected_value in alokacja_multi.items():
                actual = _find_value(result, [field_key, f"alokacja_{field_key}", f"multi_ip_{field_key}"])
                if actual is None:
                    actual = _nested_get(result, field_key)
                if actual is None:
                    actual = _find_number_for_key(classifications_text, field_key)
                if actual is None:
                    failures.append({
                        "type": "alokacja_multi_ip_missing",
                        "message": f"alokacja_multi_ip.{field_key}: nie znaleziono wartości w wyniku",
                    })
                else:
                    try:
                        if abs(float(actual) - float(expected_value)) > 0.5:
                            failures.append({
                                "type": "alokacja_multi_ip_mismatch",
                                "message": f"alokacja_multi_ip.{field_key}: oczekiwano {expected_value}, otrzymano {actual}",
                            })
                    except (ValueError, TypeError):
                        failures.append({
                            "type": "alokacja_multi_ip_invalid",
                            "message": f"alokacja_multi_ip.{field_key}: niepoprawny format wartości '{actual}'",
                        })

        # koszty_koszyk: sprawdzenie przypisania wybranych pozycji do koszyków
        for cost_desc, expected_basket in assertions.get("koszty_koszyk", {}).items():
            if not _cost_in_basket(classifications_text, cost_desc, expected_basket):
                failures.append({
                    "type": "cost_classification",
                    "message": f"Koszt '{cost_desc}' powinien być w koszyku {expected_basket}",
                })

        # nexus: dokładność ±0.001
        if "nexus" in assertions:
            actual = _find_nexus(result)
            if actual is None:
                failures.append({
                    "type": "nexus_missing",
                    "message": "NEXUS: nie znaleziono wartości w wyniku",
                })
            elif abs(actual - float(assertions["nexus"])) > 0.001:
                failures.append({
                    "type": "nexus_mismatch",
                    "message": f"NEXUS: oczekiwano {assertions['nexus']}, otrzymano {actual}",
                })

        # nexus_range: zakres ±0.001
        if "nexus_range" in assertions:
            low, high = assertions["nexus_range"]
            actual = _find_nexus(result)
            if actual is None:
                failures.append({
                    "type": "nexus_range_missing",
                    "message": "NEXUS: nie znaleziono wartości w wyniku",
                })
            elif not (low <= actual <= high):
                failures.append({
                    "type": "nexus_range_mismatch",
                    "message": f"NEXUS {actual:.3f} poza zakresem [{low}, {high}]",
                })

        # --- RANGE checks ---

        if "podatek_IP_range" in assertions:
            low, high = assertions["podatek_IP_range"]
            actual = _find_ip_tax(result)
            if actual is None:
                failures.append({
                    "type": "podatek_IP_missing",
                    "message": "Nie znaleziono podatku IP w wyniku",
                })
            elif not (low <= actual <= high):
                failures.append({
                    "type": "tax_ip_out_of_range",
                    "message": f"Podatek IP {actual:.2f} poza zakresem [{low}, {high}]",
                })

        if "podatek_NIE_range" in assertions:
            low, high = assertions["podatek_NIE_range"]
            actual = _find_non_ip_tax(result)
            if actual is None:
                failures.append({
                    "type": "podatek_NIE_missing",
                    "message": "Nie znaleziono podatku NIE w wyniku",
                })
            elif not (low <= actual <= high):
                failures.append({
                    "type": "tax_non_ip_out_of_range",
                    "message": f"Podatek NIE {actual:.2f} poza zakresem [{low}, {high}]",
                })

        if "przychod_IP_roczny_range" in assertions:
            low, high = assertions["przychod_IP_roczny_range"]
            actual = _find_value(result, ["przychod_IP", "revenue_ip", "przychody_IP"])
            if actual is None:
                failures.append({
                    "type": "przychod_IP_missing",
                    "message": "Nie znaleziono przychodu IP w wyniku",
                })
            elif not (low <= actual <= high):
                failures.append({
                    "type": "revenue_ip_out_of_range",
                    "message": f"Przychód IP {actual:.2f} poza zakresem [{low}, {high}]",
                })

        if "przychod_NIE_roczny_range" in assertions:
            low, high = assertions["przychod_NIE_roczny_range"]
            actual = _find_value(result, ["przychod_NIE", "przychod_nie", "revenue_non_ip", "przychody_NIE"])
            if actual is None:
                failures.append({
                    "type": "przychod_NIE_missing",
                    "message": "Nie znaleziono przychodu NIE w wyniku",
                })
            elif not (low <= actual <= high):
                failures.append({
                    "type": "revenue_nie_out_of_range",
                    "message": f"Przychód NIE {actual:.2f} poza zakresem [{low}, {high}]",
                })

        # W_miesieczne: tolerancja ±2pp
        for month, expected_w in assertions.get("W_miesieczne", {}).items():
            actual_w = _find_monthly_w(monthly_w_text, month)
            if actual_w is None:
                failures.append({
                    "type": "monthly_w_missing",
                    "message": f"W dla {month}: nie znaleziono wartości w wyniku",
                })
            else:
                diff = abs(actual_w - float(expected_w))
                if diff > 2.0:
                    failures.append({
                        "type": "monthly_w_mismatch",
                        "message": f"W dla {month}: oczekiwano {expected_w}%, otrzymano {actual_w:.2f}% (różnica {diff:.2f}pp > 2pp)",
                    })

        # --- HARD warnings ---
        if assertions.get("warnings"):
            for warning_code in assertions["warnings"]:
                if isinstance(stops_reviews, dict):
                    reviews_list = stops_reviews.get("reviews", [])
                    warnings_list = stops_reviews.get("warnings", [])
                else:
                    reviews_list = [str(stops_reviews)] if stops_reviews else []
                    warnings_list = []
                if not (
                    any(warning_code.lower() in str(r).lower() for r in reviews_list)
                    or warning_code.lower() in classifications_text.lower()
                    or any(warning_code.lower() in str(w).lower() for w in warnings_list)
                ):
                    failures.append({
                        "type": "missing_warning",
                        "message": f"Oczekiwane ostrzeżenie '{warning_code}' nie zostało wygenerowane",
                    })

        # --- SOFT warnings (non-blocking) ---
        if assertions.get("soft_warnings"):
            for warning_code in assertions["soft_warnings"]:
                if isinstance(stops_reviews, dict):
                    reviews_list = stops_reviews.get("reviews", [])
                    soft_warnings_list = stops_reviews.get("warnings", [])
                else:
                    reviews_list = [str(stops_reviews)] if stops_reviews else []
                    soft_warnings_list = []
                if not (
                    any(warning_code.lower() in str(r).lower() for r in reviews_list)
                    or warning_code.lower() in classifications_text.lower()
                    or any(warning_code.lower() in str(w).lower() for w in soft_warnings_list)
                ):
                    warnings.append(f"Oczekiwane ostrzeżenie '{warning_code}' nie zostało wygenerowane")

        # --- Oracle verification: independently compute TEST 1-9 ---
        oracle_map = {
            "TEST_1": _oracle_test_1,
            "TEST_2": _oracle_test_2,
            "TEST_3": _oracle_test_3,
            "TEST_4": _oracle_test_4,
            "TEST_5": _oracle_test_5,
            "TEST_6": _oracle_test_6,
            "TEST_7": _oracle_test_7,
            "TEST_8": _oracle_test_8,
            "TEST_9": _oracle_test_9,
        }
        all_expected_tests = set(assertions.get("testy_pass", []) + assertions.get("testy_fail", []))
        for test_id in all_expected_tests:
            normalized = _normalize_test_id(test_id)
            oracle_fn = oracle_map.get(normalized)
            if oracle_fn and tests_text:
                oracle_result = oracle_fn(parsed, self.scenario)
                model_passed = _test_passed(tests_text, test_id)
                if oracle_result != model_passed:
                    failures.append({
                        "type": "oracle_mismatch",
                        "message": f"Oracle {normalized}: oracle={'PASS' if oracle_result else 'FAIL'} "
                                  f"model={'PASS' if model_passed else 'FAIL'}",
                    })

        return failures, warnings


def normalize_test_key(raw: str) -> str:
    """Normalize TEST keys: TEST_1, TEST 1, test_1_bilans → TEST_1."""
    import re
    m = re.search(r"[Tt][Ee][Ss][Tt][_ ]?(\d+)", raw)
    return f"TEST_{m.group(1)}" if m else raw.upper()


def validate_assertion_keys(assertions: dict, scenario_id: str) -> list[str]:
    """Check that every key in assertions is a known, handled key.

    Returns a list of error messages; empty list means all keys are known.
    """
    known_keys = {
        "testy_pass", "testy_fail", "nexus", "nexus_range",
        "W_miesieczne", "koszty_koszyk",
        "alokacja_multi_ip", "klucz_MIX_metoda", "klucz_MIX_źródło",
        "nie_używaj_W_do_MIX", "review_obecne", "warnings", "soft_warnings",
        "stops", "zus_dubel", "roznice_kursowe_w_IP",
        "podatek_IP_range", "podatek_NIE_range",
        "przychod_IP_roczny_range", "przychod_NIE_roczny_range",
    }
    errors = []
    for key in assertions:
        if key not in known_keys and not key.startswith("meta."):
            errors.append(f"Unknown assertion key '{key}' in scenario '{scenario_id}'")
    return errors


# ---------------------------------------------------------------------------
# Helper parsers
# ---------------------------------------------------------------------------

def _normalize_test_id(value: str) -> str:
    """Normalize test IDs like 'TEST 1', 'test_1_bilans' → 'TEST_1'."""
    import re
    match = re.search(r"\bTEST[\s_-]*(\d+)", value, re.IGNORECASE)
    if not match:
        return value
    return f"TEST_{int(match.group(1))}"


def _parse_tests_map(tests_text: str) -> dict[str, str]:
    """Build a dict of normalized test ID → PASS/FAIL from the tests block."""
    import re
    result = {}
    for line in tests_text.splitlines():
        m = re.search(r"(TEST[\s_-]*\d+[^:\n]*)\s*[:_]\s*(PASS|FAIL)", line, re.IGNORECASE)
        if m:
            try:
                nid = _normalize_test_id(m.group(1))
                result[nid] = m.group(2).upper()
            except ValueError:
                pass
    return result


def _test_passed(tests_text: str, test_id: str) -> bool:
    """Return True if test_id appears with PASS in the tests block."""
    import re
    nid = _normalize_test_id(test_id)
    tests_map = _parse_tests_map(tests_text)
    if nid in tests_map:
        return tests_map[nid] == "PASS"
    pattern = rf"{re.escape(test_id)}\s*[:_]?\s*PASS\b"
    return bool(re.search(pattern, tests_text, re.IGNORECASE))


def _test_failed(tests_text: str, test_id: str) -> bool:
    """Return True if test_id appears with FAIL in the tests block."""
    import re
    nid = _normalize_test_id(test_id)
    tests_map = _parse_tests_map(tests_text)
    if nid in tests_map:
        return tests_map[nid] == "FAIL"
    pattern = rf"{re.escape(test_id)}\s*[:_]?\s*FAIL"
    return bool(re.search(pattern, tests_text, re.IGNORECASE))


def _fx_diff_in_ip(classifications: str) -> bool:
    """Return True if any line mentions both FX diff and IP basket."""
    if not classifications:
        return False
    for line in classifications.splitlines():
        lower = line.lower()
        if ("różnica kursowa" in lower or "roznica kursowa" in lower or "kursow" in lower):
            if "-> ip" in lower or "koszyk: ip" in lower or "ip box" in lower:
                return True
    return False


def _cost_in_basket(classifications: str, cost_desc: str, expected_basket: str) -> bool:
    """Check if cost_desc is assigned to expected_basket in the classifications text."""
    if not classifications:
        return False
    for line in classifications.splitlines():
        if cost_desc.lower() in line.lower() and expected_basket.upper() in line.upper():
            return True
    return False


def _code_matches(expected: str, actual_list: list) -> bool:
    """Exact match for stop/review codes (no substring matching)."""
    for actual in actual_list:
        if isinstance(actual, str) and actual.lower().strip() == expected.lower().strip():
            return True
    return False


def _check_description_consistency(scenario: dict) -> list[str]:
    """Check that scenario description matches what assertions actually verify.

    If assertions only specify ``stops`` (no ``review_obecne``), the description
    should not mention REVIEW as an alternative expected outcome. Conversely,
    if assertions specify reviews, their codes should appear in the description.

    Returns a list of error messages (empty = consistent).
    """
    import re

    errors: list[str] = []
    meta = scenario.get("meta", {})
    assertions = scenario.get("assertions", {})
    description = (meta.get("description") or "").strip()
    if not description:
        return errors

    expected_stops = meta.get("expected_stops", []) or []
    assertion_stops = assertions.get("stops", []) or []
    expected_reviews = meta.get("expected_reviews", []) or []
    assertion_reviews = assertions.get("review_obecne", []) or []

    has_stops = bool(expected_stops or assertion_stops)
    has_reviews = bool(expected_reviews or assertion_reviews)

    # If only stops are expected, description should not suggest REVIEW as an
    # alternative outcome (e.g. "stop or emit REVIEW")
    if has_stops and not has_reviews:
        if re.search(r'\breview\b', description, re.IGNORECASE):
            errors.append(
                f"Scenario '{meta.get('id', '?')}' only expects stops "
                f"({expected_stops or assertion_stops}) but description "
                f"mentions REVIEW: '{description}'"
            )

    return errors


def _find_nexus(result: dict) -> float | None:
    for key in ("nexus", "nexus_value", "wskaznik_nexus", "wskaźnik_nexus"):
        val = result.get(key)
        if val is not None:
            if isinstance(val, dict):
                val = val.get("wartość", val.get("wartosc", val.get("value")))
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
    return None


def _find_ip_tax(result: dict) -> float | None:
    for key in ("podatek_IP", "ip_tax", "tax_ip", "podatek_ip"):
        val = _nested_get(result, key)
        if val is not None:
            try:
                return float(str(val).replace("zł", "").replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


def _find_non_ip_tax(result: dict) -> float | None:
    for key in ("podatek_NIE", "non_ip_tax", "tax_non_ip", "podatek_nie", "podatek_NIE_finalny"):
        val = _nested_get(result, key)
        if val is not None:
            try:
                return float(str(val).replace("zł", "").replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


def _find_value(result: dict, keys: list[str]) -> float | None:
    for key in keys:
        val = _nested_get(result, key)
        if val is not None:
            try:
                return float(str(val).replace("zł", "").replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
    # Fallback: probe przychody_roczne.{IP,NIE} when flat keys didn't match
    # Match only whole-word _IP / _NIE to avoid "REVENUE_NON_IP" triggering IP lookup
    przychody = result.get("przychody_roczne", {})
    if isinstance(przychody, dict):
        wants_ip = any(k.upper().replace("_","").endswith("IP") and "NON" not in k.upper() for k in keys)
        wants_nie = any("_NIE" in k.upper() or k.upper().endswith("NIE") for k in keys)
        if wants_ip and "IP" in przychody:
            try:
                return float(str(przychody["IP"]).replace("zł", "").replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
        if wants_nie and "NIE" in przychody:
            try:
                return float(str(przychody["NIE"]).replace("zł", "").replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


def _find_monthly_w(text: str, month: str) -> float | None:
    import re
    pattern = rf"{re.escape(month)}\s*[:->]+\s*([\d.,]+)"
    m = re.search(pattern, text)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def _find_klucz_mix_field(result: dict, field: str) -> str | None:
    """Search for a field in klucz_MIX-related structures in the result dict.

    Looks in: alokacja.koszty_MIX.<field>, klucze_alokacji_roczne.koszty_MIX.<field>,
    and any direct key containing 'klucz' + field.
    """

    # Check alokacja.koszty_MIX.<field>
    alokacja = result.get("alokacja") or {}
    koszty_mix = alokacja.get("koszty_MIX") or alokacja.get("koszty_mix") or {}
    if field in koszty_mix:
        return koszty_mix[field]

    # Check klucze_alokacji_roczne.koszty_MIX.<field>
    klucze = result.get("klucze_alokacji_roczne") or result.get("klucze_alokacji") or {}
    koszty_mix2 = klucze.get("koszty_MIX") or klucze.get("koszty_mix") or {}
    if field in koszty_mix2:
        return koszty_mix2[field]

    # Check any key for 'klucz' + field (case-insensitive)
    field_lower = field.lower()
    for key, val in _flatten_dict(result).items():
        k = key.lower().replace(" ", "_").replace("-", "_")
        if "klucz" in k and field_lower in k:
            return str(val)

    return None


def _w_used_for_mix(classifications: str) -> bool:
    """Return True if classifications show W being used for MIX costs."""
    if not classifications:
        return False
    import re
    for line in classifications.splitlines():
        lower = line.lower()
        # Check if line mentions both MIX and W (time-based allocation)
        if "mix" in lower and ("w" in lower or "współczynnik" in lower or "wspolczynnik" in lower):
            if re.search(r'\bw\s*[=:>]', lower) or "czasow" in lower:
                return True
        # Check for "W_czasowy" or "czasowa_W" patterns
        if "w_czasowy" in lower or "czasowa_w" in lower or "w miesięczn" in lower:
            if "mix" in lower:
                return True
    return False


def _find_number_for_key(text: str, key: str) -> float | None:
    """Search text for a pattern like '<key>: <number>' or '<key>=<number>'."""
    import re
    escaped = re.escape(key)
    patterns = [
        rf"{escaped}\s*[:=]\s*([\d.,]+)",
        rf"{escaped}\s*\|>\s*([\d.,]+)",
        rf"{escaped}[^a-zA-Z]*?(\d[\d.,]*)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


def _flatten_dict(d: dict, parent_key: str = "") -> dict:
    """Flatten a nested dict to a single level with dot-separated keys."""
    items: dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items


# ---------------------------------------------------------------------------
# Oracle functions — deterministic TEST recomputation
# ---------------------------------------------------------------------------

def _oracle_test_1(parsed: dict, scenario: dict) -> bool:
    """TEST 1: NEXUS must be in [0, 1]."""
    nexus = parsed.get("result", {}).get("nexus")
    if nexus is None:
        return False
    try:
        val = float(nexus)
        return 0.0 <= val <= 1.0
    except (ValueError, TypeError):
        return False


def _oracle_test_2(parsed: dict, scenario: dict) -> bool:
    """TEST 2: podatek_IP = dochód_IP x 5%."""
    result = parsed.get("result", {})
    podatek_ip = result.get("podatek", {}).get("podatek_IP")
    dochód_ip = result.get("dochód_IP")
    if podatek_ip is None or dochód_ip is None:
        return False
    try:
        return abs(float(podatek_ip) - float(dochód_ip) * 0.05) < 1.0
    except (ValueError, TypeError):
        return False


def _oracle_test_3(parsed: dict, scenario: dict) -> bool:
    """TEST 3: No ZUS double-dip (ZUS in KPiR AND annual ulga)."""
    ulgi = scenario.get("ulgi", {})
    has_annual_zus = bool(ulgi.get("zus_spoleczne_roczne"))
    miesiace = scenario.get("miesiace", [])
    zus_in_kpir = False
    for m in miesiace:
        for cost in m.get("koszty", []):
            if isinstance(cost, dict) and "zus" in cost.get("opis", "").lower():
                zus_in_kpir = True
                break
    return not (has_annual_zus and zus_in_kpir)


def _oracle_test_4(parsed: dict, scenario: dict) -> bool:
    """TEST 4: Tax cascade valid — non-negative + sum matches."""
    result = parsed.get("result", {})
    podatek = result.get("podatek", {})
    try:
        ip = float(podatek.get("podatek_IP", 0) or 0)
        nie = float(podatek.get("podatek_NIE_finalny", 0) or 0)
        cal = float(podatek.get("podatek_całościowy", 0) or 0)
        return ip >= 0 and nie >= 0 and abs(ip + nie - cal) < 1.0
    except (ValueError, TypeError):
        return False


def _oracle_test_5(parsed: dict, scenario: dict) -> bool:
    """TEST 5: Overpayment check — stub, always True for now."""
    return True


def _oracle_test_6(parsed: dict, scenario: dict) -> bool:
    """TEST 6: KPiR balance — stub, always True for now."""
    return True


def _oracle_test_7(parsed: dict, scenario: dict) -> bool:
    """TEST 7: No private costs in IP/MIX/NIE baskets."""
    classifications = parsed.get("classifications", [])
    if isinstance(classifications, str):
        classifications = [classifications]
    for line in classifications:
        if isinstance(line, str) and "prywatny" in line.lower():
            if "IP" in line or "MIX" in line or "NIE" in line:
                return False
    return True


def _oracle_test_8(parsed: dict, scenario: dict) -> bool:
    """TEST 8: MIX allocation — stub, always True for now."""
    return True


def _oracle_test_9(parsed: dict, scenario: dict) -> bool:
    """TEST 9: All months have project descriptions."""
    for m in scenario.get("miesiace", []):
        if not isinstance(m, dict):
            continue
        if not m.get("opis_projektu", "").strip():
            return False
    return True


def _nested_get(d: dict, key: str) -> Any:
    """Recursively get value from nested dict by key."""
    if key in d:
        return d[key]
    for v in d.values():
        if isinstance(v, dict):
            result = _nested_get(v, key)
            if result is not None:
                return result
    return None


