from __future__ import annotations

import math

import pytest

from python_helper.ipbox_calculator import (
    CostItem,
    aggregate_w_multiproject,
    calculate_w_coefficient,
    canonical_basket,
    classify_cost,
    money,
    tax_round,
)


def test_money_and_tax_round_half_up() -> None:
    assert float(money(1.005)) == 1.01
    assert tax_round(1.5) == 2
    assert tax_round(1.49) == 1


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_money_rejects_nonfinite(value: float) -> None:
    with pytest.raises(ValueError):
        money(value)


def test_w_happy_path_and_reviews() -> None:
    assert calculate_w_coefficient(160, 16)["W"] == 90.0
    assert calculate_w_coefficient(160, 2)["status"] == "REVIEW_01"
    assert calculate_w_coefficient(160, 90)["status"] == "REVIEW_02"
    assert calculate_w_coefficient(160, 160)["status"] == "SKIP_MONTH"


def test_w_zero_and_invalid_data() -> None:
    assert calculate_w_coefficient(0, 0)["status"] == "ERROR"
    assert calculate_w_coefficient(10, 11)["status"] == "ERROR"
    for args in ((-1, 0, 100), (1, -1, 100), (1, 0, 101), (1, 0, math.nan)):
        with pytest.raises(ValueError):
            calculate_w_coefficient(*args)


def test_weighted_w() -> None:
    assert (
        aggregate_w_multiproject([{"revenue": 15000, "W": 90}, {"revenue": 10000, "W": 50}]) == 74.0
    )
    with pytest.raises(ValueError, match="project revenue"):
        aggregate_w_multiproject([{"revenue": 0, "W": 50}])
    with pytest.raises(ValueError):
        aggregate_w_multiproject([])
    with pytest.raises(ValueError):
        aggregate_w_multiproject([{"revenue": 1}])
    with pytest.raises(ValueError):
        aggregate_w_multiproject([{"revenue": -1, "W": 50}])
    with pytest.raises(ValueError):
        aggregate_w_multiproject([{"revenue": 1, "W": 101}])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("IP", "IP"), ("MIX", "MIX"), ("NIE", "NON"), ("EXCLUDED", "WYKLUCZONE")],
)
def test_canonical_basket_aliases(raw: str, expected: str) -> None:
    assert canonical_basket(raw) == expected


def test_canonical_basket_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        canonical_basket("UNKNOWN")


def test_cost_item_validations() -> None:
    assert CostItem("x", 1, basket="EXCLUDED").basket == "WYKLUCZONE"
    with pytest.raises(ValueError):
        CostItem("", 1)
    with pytest.raises(ValueError):
        CostItem("x", -1)
    with pytest.raises(ValueError):
        CostItem("x", 1, allocation_key=1.1)
    with pytest.raises(ValueError):
        CostItem("x", 1, nexus_amount=2)
    with pytest.raises(ValueError):
        CostItem("x", 1, nexus_source="own_br")
    with pytest.raises(ValueError):
        CostItem("x", 1, nexus_source="bad")


@pytest.mark.parametrize(
    ("description", "amount", "social", "health", "expected"),
    [
        ("ZUS społeczne", 100, True, False, "MIX"),
        ("ZUS społeczne", 100, False, False, "WYKLUCZONE"),
        ("Składka zdrowotna", 100, False, True, "MIX"),
        ("Składka zdrowotna", 100, False, False, "WYKLUCZONE"),
        ("Mandat", 100, False, False, "MIX"),
        ("Laptop", 12000, False, False, "WYKLUCZONE"),
        ("Kawa do domu", 100, False, False, "MIX"),
        ("Licencja JetBrains", 100, False, False, "MIX"),
        ("Księgowość", 100, False, False, "MIX"),
    ],
)
def test_classify_cost(
    description: str,
    amount: float,
    social: bool,
    health: bool,
    expected: str,
) -> None:
    result = classify_cost(CostItem(description, amount), social, health)
    assert result.basket == expected


@pytest.mark.parametrize(
    "description",
    ["Usługa firmy KawaSoft", "Akcesoria Kawasaki", "Faktura Mandat Consulting"],
)
def test_description_substrings_do_not_decide_kup(description: str) -> None:
    result = classify_cost(CostItem(description, 100), False, False)
    assert result.basket == "MIX"


def test_classify_cost_threshold_validation() -> None:
    with pytest.raises(ValueError):
        classify_cost(CostItem("x", 1), False, False, asset_threshold=-1)


def test_direct_ip_cost_requires_explicit_evidence_source() -> None:
    with pytest.raises(ValueError, match="allocation_source evidence"):
        CostItem("Licencja wyłącznie do projektu IP", 100, basket="IP")


def test_classify_cost_preserves_explicit_evidence() -> None:
    explicit = CostItem(
        "Licencja wyłącznie do projektu IP", 100, basket="IP", allocation_source="license-ledger"
    )
    assert classify_cost(explicit, False, False) is explicit


def test_ambiguous_asset_and_tool_require_explicit_policy() -> None:
    asset = classify_cost(CostItem("Laptop", 12000), False, False)
    tool = classify_cost(CostItem("Licencja JetBrains", 100), False, False)
    assert asset.basket == "WYKLUCZONE"
    assert tool.basket == "MIX"
    assert "depreciation" in asset.note.lower()
    assert "documented" in tool.note.lower()


def test_description_signal_does_not_override_explicit_cost_classification() -> None:
    explicit = CostItem(
        "Kawa do domu — koszt zweryfikowany dokumentem",
        100,
        basket="IP",
        allocation_source="verified-cost-ledger",
    )

    assert classify_cost(explicit, False, False) is explicit
