from __future__ import annotations

from typing import Any


class Evaluator:
    """Evaluates LLM output against scenario assertions (HARD / RANGE / SOFT)."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario

    def evaluate(self, parsed: dict[str, Any]) -> tuple[list[dict], list[str]]:
        """Return (failures, warnings). failures = HARD/RANGE errors, warnings = SOFT."""
        failures: list[dict] = []
        warnings: list[str] = []

        assertions = self.scenario.get("assertions", {})
        if not assertions:
            return failures, warnings

        result = parsed.get("result") or {}
        if isinstance(result, str):
            failures.append({"type": "parse_error", "message": "Nie udało się sparsować <result> jako YAML"})
            return failures, warnings

        stops_reviews = parsed.get("stops_reviews") or {}

        # --- HARD checks ---

        # zus_dubel: TEST_3 musi być PASS gdy zus_dubel=False
        if assertions.get("zus_dubel") is False:
            tests_text = parsed.get("tests") or ""
            if _test_failed(tests_text, "TEST_3") or _test_failed(tests_text, "TEST 3"):
                failures.append({
                    "type": "zus_double_dip",
                    "message": "Wykryto podwójne odliczenie ZUS (TEST_3 FAIL)",
                })

        # testy_pass: każdy wymieniony test musi być PASS
        for test_id in assertions.get("testy_pass", []):
            tests_text = parsed.get("tests") or ""
            if _test_failed(tests_text, test_id):
                failures.append({
                    "type": f"test_fail_{test_id}",
                    "message": f"{test_id} powinien być PASS, ale jest FAIL",
                })

        # roznice_kursowe_w_IP: różnice kursowe nie mogą trafić do koszyka IP
        if assertions.get("roznice_kursowe_w_IP") is False:
            classifications = parsed.get("classifications") or ""
            if _fx_diff_in_ip(classifications):
                failures.append({
                    "type": "fx_diff_in_ip",
                    "message": "Różnice kursowe trafiły do koszyka IP — powinny być w NIE",
                })

        # expected_stops: wszystkie oczekiwane STOP muszą się pojawić
        for expected_stop in self.scenario.get("meta", {}).get("expected_stops", []):
            stops_list = stops_reviews.get("stops", []) if isinstance(stops_reviews, dict) else []
            if not any(expected_stop.lower() in str(s).lower() for s in stops_list):
                failures.append({
                    "type": "missing_stop",
                    "message": f"Oczekiwany STOP '{expected_stop}' nie wystąpił",
                })

        # expected_reviews: wszystkie oczekiwane REVIEW muszą się pojawić
        for expected_review in self.scenario.get("meta", {}).get("expected_reviews", []):
            if isinstance(stops_reviews, dict):
                reviews_list = stops_reviews.get("reviews", [])
            else:
                reviews_list = [str(stops_reviews)] if stops_reviews else []
            if not any(expected_review.lower() in str(r).lower() for r in reviews_list):
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
            classifications = parsed.get("classifications") or ""
            if _w_used_for_mix(classifications):
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
            if not any(expected_review.lower() in str(r).lower() for r in reviews_list):
                failures.append({
                    "type": "missing_review",
                    "message": f"Oczekiwany REVIEW '{expected_review}' nie wystąpił",
                })

        # alokacja_multi_ip: sprawdzenie wartości alokacji dwustopniowej
        alokacja_multi = assertions.get("alokacja_multi_ip", {})
        if alokacja_multi:
            classifications_text = parsed.get("classifications") or ""
            for field_key, expected_value in alokacja_multi.items():
                actual = _find_value(result, [field_key, f"alokacja_{field_key}", f"multi_ip_{field_key}"])
                if actual is None:
                    actual = _nested_get(result, field_key)
                if actual is None:
                    raw = parsed.get("raw_response") or ""
                    actual = _find_number_for_key(raw + "\n" + classifications_text, field_key)
                if actual is not None:
                    try:
                        if abs(float(actual) - float(expected_value)) > 0.5:
                            failures.append({
                                "type": "alokacja_multi_ip_mismatch",
                                "message": f"alokacja_multi_ip.{field_key}: oczekiwano {expected_value}, otrzymano {actual}",
                            })
                    except (ValueError, TypeError):
                        pass

        # koszty_koszyk: sprawdzenie przypisania wybranych pozycji do koszyków
        for cost_desc, expected_basket in assertions.get("koszty_koszyk", {}).items():
            classifications = parsed.get("classifications") or ""
            if not _cost_in_basket(classifications, cost_desc, expected_basket):
                failures.append({
                    "type": "cost_classification",
                    "message": f"Koszt '{cost_desc}' powinien być w koszyku {expected_basket}",
                })

        # nexus: dokładność ±0.001
        if "nexus" in assertions:
            actual = _find_nexus(result)
            if actual is not None:
                if abs(actual - float(assertions["nexus"])) > 0.001:
                    failures.append({
                        "type": "nexus_mismatch",
                        "message": f"NEXUS: oczekiwano {assertions['nexus']}, otrzymano {actual}",
                    })

        # --- RANGE checks ---

        if "podatek_IP_range" in assertions:
            low, high = assertions["podatek_IP_range"]
            actual = _find_ip_tax(result)
            if actual is not None and not (low <= actual <= high):
                failures.append({
                    "type": "tax_ip_out_of_range",
                    "message": f"Podatek IP {actual:.2f} poza zakresem [{low}, {high}]",
                })

        if "podatek_NIE_range" in assertions:
            low, high = assertions["podatek_NIE_range"]
            actual = _find_non_ip_tax(result)
            if actual is not None and not (low <= actual <= high):
                failures.append({
                    "type": "tax_non_ip_out_of_range",
                    "message": f"Podatek NIE {actual:.2f} poza zakresem [{low}, {high}]",
                })

        if "przychod_IP_roczny_range" in assertions:
            low, high = assertions["przychod_IP_roczny_range"]
            actual = _find_value(result, ["przychod_IP", "revenue_ip", "przychody_IP"])
            if actual is not None and not (low <= actual <= high):
                failures.append({
                    "type": "revenue_ip_out_of_range",
                    "message": f"Przychód IP {actual:.2f} poza zakresem [{low}, {high}]",
                })

        # W_miesieczne: tolerancja ±2pp
        for month, expected_w in assertions.get("W_miesieczne", {}).items():
            monthly_w_text = parsed.get("monthly_W") or ""
            actual_w = _find_monthly_w(monthly_w_text, month)
            if actual_w is not None:
                diff = abs(actual_w - float(expected_w))
                if diff > 2.0:
                    failures.append({
                        "type": "monthly_w_mismatch",
                        "message": f"W dla {month}: oczekiwano {expected_w}%, otrzymano {actual_w:.2f}% (różnica {diff:.2f}pp > 2pp)",
                    })

        # --- SOFT checks (warnings) ---

        if assertions.get("warnings"):
            for warning_code in assertions["warnings"]:
                if isinstance(stops_reviews, dict):
                    reviews_list = stops_reviews.get("reviews", [])
                else:
                    reviews_list = [str(stops_reviews)] if stops_reviews else []
                classifications = parsed.get("classifications") or ""
                if not (
                    any(warning_code.lower() in str(r).lower() for r in reviews_list)
                    or warning_code.lower() in classifications.lower()
                ):
                    warnings.append(f"Oczekiwane ostrzeżenie '{warning_code}' nie zostało wygenerowane")

        return failures, warnings


# ---------------------------------------------------------------------------
# Helper parsers
# ---------------------------------------------------------------------------

def _test_failed(tests_text: str, test_id: str) -> bool:
    """Return True if test_id appears with FAIL in the tests block."""
    import re
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
        if cost_desc.lower() in line.lower():
            if expected_basket.upper() in line.upper():
                return True
    return False


def _find_nexus(result: dict) -> float | None:
    for key in ("nexus", "nexus_value", "wskaznik_nexus", "wskaźnik_nexus"):
        val = result.get(key)
        if val is not None:
            if isinstance(val, dict):
                val = val.get("wartość") or val.get("wartosc") or val.get("value")
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
    for key in ("podatek_NIE", "non_ip_tax", "tax_non_ip", "podatek_nie"):
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
    import re

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


def _nested_get(d: dict, key: str) -> Any:
    """Get value from flat or one-level-nested dict."""
    if key in d:
        return d[key]
    for v in d.values():
        if isinstance(v, dict) and key in v:
            return v[key]
    return None


