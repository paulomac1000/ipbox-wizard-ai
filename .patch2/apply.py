from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    ROOT / "python_helper/ipbox_calculator.py",
    '''    for item in [*items, *extra]:
        amount = _money(item.amount)
        basket = item.basket or ("IP" if item in extra else "")
''',
    '''    tagged_items = [
        *((item, False) for item in items),
        *((item, True) for item in extra),
    ]
    for item, is_explicit_ip_direct in tagged_items:
        amount = _money(item.amount)
        basket = item.basket or ("IP" if is_explicit_ip_direct else "")
''',
)

replace_once(
    ROOT / "python_helper/ipbox_calculator.py",
    '''    stage1 = _money(
        Decimal(str(deferred_mix_total))
        * Decimal(str(software_ip_revenue))
        / Decimal(str(total_revenue))
    )
    projects = _split_money_by_weights(float(stage1), ip_revenues)
''',
    '''    stage1 = _money(
        Decimal(str(deferred_mix_total))
        * Decimal(str(software_ip_revenue))
        / Decimal(str(total_revenue))
    )
    if software_ip_revenue == 0:
        projects = {name: 0.0 for name in ip_revenues}
    else:
        projects = _split_money_by_weights(float(stage1), ip_revenues)
''',
)

replace_once(
    ROOT / "tests/llm/output_schema.py",
    'STATUS_CODE = {"type": "string", "pattern": "^(STOP|REVIEW|WARNING)_[0-9]{2}$"}',
    '''STATUS_CODE = {
    "type": "string",
    "pattern": r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$",
}''',
)

replace_once(
    ROOT / "tests/llm/evaluator.py",
    '''def _classification_records(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    value = parsed.get("classifications")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


''',
    '''def _classification_records(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    value = parsed.get("classifications")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _monthly_w_map(parsed: dict[str, Any]) -> dict[str, Any]:
    """Normalize the canonical monthly_W array to a month -> value mapping."""
    value = parsed.get("monthly_W")
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return {}

    result: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        month = item.get("miesiąc")
        if isinstance(month, str) and month not in result:
            result[month] = item.get("wartość")
    return result


''',
)

replace_once(
    ROOT / "tests/llm/evaluator.py",
    '''        monthly = parsed.get("monthly_W") if isinstance(parsed.get("monthly_W"), dict) else {}
        for month, expected in assertions.get("W_miesieczne", {}).items():
''',
    '''        monthly = _monthly_w_map(parsed)
        for month, expected in assertions.get("W_miesieczne", {}).items():
''',
)

(ROOT / "tests/unit/test_output_contract_regressions.py").write_text(
    '''from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    allocate_costs_monthly,
    allocate_multi_ip,
)
from tests.llm.evaluator import Evaluator
from tests.llm.output_schema import OUTPUT_JSON_SCHEMA


def _minimal_output() -> dict:
    return {
        "status": "STOPPED",
        "result": {
            "rok": 2025,
            "przychody_roczne": {"IP": 0, "NIE": 0},
            "koszty_roczne": {"IP": 0, "NIE": 0, "MIX": 0, "EXCLUDED": 0},
            "nexus_koszty": {"A": 0, "B": 0, "C": 0, "D": 0, "poza_nexus": 0},
            "nexus": 0,
            "dochód_IP": 0,
            "dochód_NIE": 0,
            "klucz_MIX": {
                "metoda": "przychodowa_roczna",
                "źródło": "domyślna_wizard",
                "wartość": None,
                "status": "DEFERRED",
            },
            "alokacja_multi_ip": None,
            "podatek": {
                "podstawa_IP": 0,
                "podstawa_NIE": 0,
                "podatek_IP": 0,
                "podatek_NIE_finalny": 0,
                "podatek_całościowy": 0,
            },
        },
        "classifications": [],
        "monthly_W": [{"miesiąc": "2025-01", "wartość": 90}],
        "tests": {f"TEST_{number}": "PASS" for number in range(1, 10)},
        "stops_reviews": {
            "stops": ["ZUS_DOUBLE_DIP"],
            "reviews": [],
            "warnings": [],
        },
    }


@pytest.mark.unit
@pytest.mark.P0
def test_output_schema_accepts_domain_stop_and_monthly_array():
    validator = Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"])
    assert list(validator.iter_errors(_minimal_output())) == []


@pytest.mark.unit
@pytest.mark.P0
def test_evaluator_reads_monthly_w_from_canonical_array():
    scenario = {
        "meta": {"id": "monthly-array"},
        "input": {
            "rok": 2025,
            "forma_opodatkowania": "liniowy_19%",
            "miesiace": [
                {
                    "miesiac": "2025-01",
                    "opis_projektu": "Rozwój systemu",
                    "przychody": 1000,
                    "koszty": [],
                }
            ],
        },
        "assertions": {"W_miesieczne": {"2025-01": 90}},
    }
    output = _minimal_output()
    output["status"] = "PROVISIONAL"
    output["stops_reviews"]["stops"] = []
    failures, _ = Evaluator(scenario).evaluate(output)
    assert failures == []


@pytest.mark.unit
@pytest.mark.P0
def test_equal_distinct_cost_items_do_not_gain_ip_direct_status_by_equality():
    regular = CostItem(description="Same", amount=100)
    explicit_ip = CostItem(description="Same", amount=100)
    policy = AllocationPolicy(
        policy_id="policy",
        source="domyślna_wizard",
        mix_method="przychodowa_roczna",
    )
    with pytest.raises(ValueError, match="unsupported basket"):
        allocate_costs_monthly(
            [regular],
            allocation_policy=policy,
            ip_direct_costs=[explicit_ip],
        )


@pytest.mark.unit
@pytest.mark.P1
def test_multi_ip_zero_software_revenue_returns_zero_project_allocations():
    result = allocate_multi_ip(
        deferred_mix_total=1000,
        total_revenue=10000,
        software_ip_revenue=0,
        ip_revenues={"IP_A": 0, "IP_B": 0},
    )
    assert result["stage1_software_share"] == 0
    assert result["stage1_non_software_share"] == 1000
    assert result["projects"] == {"IP_A": 0.0, "IP_B": 0.0}
''',
    encoding="utf-8",
)
