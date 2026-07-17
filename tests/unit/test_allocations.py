from __future__ import annotations

import math

import pytest

from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    aggregate_nexus_costs,
    allocate_costs_monthly,
    allocate_multi_ip,
    allocate_revenue_monthly,
    annual_mix_allocation_revenue,
    calculate_nexus,
    compare_allocation_methods,
    nexus_classify,
    resolve_mix_key,
)


def policy(**kwargs) -> AllocationPolicy:
    defaults = dict(policy_id="p", source="użytkownik", justification="documented")
    defaults.update(kwargs)
    return AllocationPolicy(**defaults)


def test_policy_alias_and_validations() -> None:
    assert policy(mix_method="przychodowy_roczny").mix_method == "przychodowa_roczna"
    with pytest.raises(ValueError):
        policy(policy_id="")
    with pytest.raises(ValueError):
        policy(revenue_method="bad")
    with pytest.raises(ValueError):
        policy(mix_method="bad")
    with pytest.raises(ValueError):
        AllocationPolicy(policy_id="p", source="bad")
    with pytest.raises(ValueError):
        policy(mix_method="przychodowa_roczna", mix_key=0.5)
    with pytest.raises(ValueError):
        AllocationPolicy(policy_id="p", source="użytkownik", mix_method="czasowa_W")


def test_revenue_allocation_document_and_key() -> None:
    documented = allocate_revenue_monthly(100, "dokumentowa", document_split_ip=40)
    assert documented["ip_revenue"] == 40
    assert documented["non_ip_revenue"] == 60
    keyed = allocate_revenue_monthly(100, "czasowa_W", revenue_key=0.4)
    assert keyed["ip_revenue"] == 40
    assert keyed["non_ip_revenue"] == 60


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1])
def test_revenue_allocation_rejects_bad_money(bad: float) -> None:
    with pytest.raises(ValueError):
        allocate_revenue_monthly(bad, "czasowa_W", revenue_key=0.5)


def test_revenue_allocation_rejects_contract_errors() -> None:
    with pytest.raises(ValueError):
        allocate_revenue_monthly(100, "bad", revenue_key=0.5)
    with pytest.raises(ValueError):
        allocate_revenue_monthly(100, "dokumentowa")
    with pytest.raises(ValueError):
        allocate_revenue_monthly(100, "dokumentowa", document_split_ip=101)
    with pytest.raises(ValueError):
        allocate_revenue_monthly(100, "czasowa_W")
    with pytest.raises(ValueError):
        allocate_revenue_monthly(100, "czasowa_W", revenue_key=2)


def test_resolve_mix_accepts_zero() -> None:
    item = CostItem("MIX", 100, basket="MIX", allocation_key=0.0)
    assert resolve_mix_key(item, policy())[0] == 0.0


def test_monthly_cost_allocation_trace_and_deferred() -> None:
    items = [
        CostItem("direct", 100, basket="IP", nexus_source="own_br", nexus_basket="A"),
        CostItem("private", 20, basket="NON"),
        CostItem("asset", 30, basket="WYKLUCZONE"),
        CostItem("shared", 50, basket="MIX"),
    ]
    result = allocate_costs_monthly(items, allocation_policy=policy(), w_coefficient=80)
    assert result["costs_ip"] == 100
    assert result["costs_non"] == 20
    assert result["mix_deferred"] == 50
    assert result["excluded"] == 30
    assert result["result_status"] == "PROVISIONAL"
    assert len(result["allocation_trace"]) == 4


def test_monthly_cost_allocation_explicit_key() -> None:
    result = allocate_costs_monthly(
        [CostItem("shared", 100, basket="MIX")],
        allocation_policy=policy(mix_method="czasowa_W", mix_key=0.25),
    )
    assert result["costs_ip"] == 25
    assert result["costs_non"] == 75
    assert result["mix_effective_key"] == 0.25
    assert result["result_status"] == "FINAL"


def test_equal_but_distinct_items_do_not_use_identity_incorrectly() -> None:
    classified = CostItem("same", 1, basket="NON")
    extra = CostItem("same", 1, basket="NON")
    with pytest.raises(ValueError, match="ip_direct_costs"):
        allocate_costs_monthly([classified], allocation_policy=policy(), ip_direct_costs=[extra])


def test_monthly_cost_rejects_duplicates_and_bad_w() -> None:
    item = CostItem("x", 1, basket="IP")
    with pytest.raises(ValueError):
        allocate_costs_monthly([item], allocation_policy=policy(), ip_direct_costs=[item])
    with pytest.raises(ValueError):
        allocate_costs_monthly([], allocation_policy=policy(), w_coefficient=101)
    with pytest.raises(ValueError):
        allocate_costs_monthly([], allocation_policy=policy(), w_coefficient=math.nan)


def test_annual_mix_allocation() -> None:
    result = annual_mix_allocation_revenue(100, 80, 100)
    assert result["mix_ip"] == 80
    assert result["mix_non_ip"] == 20
    for args in ((100, 1, 0), (100, 101, 100), (-1, 1, 1), (1, math.nan, 1)):
        with pytest.raises(ValueError):
            annual_mix_allocation_revenue(*args)


def test_multi_ip_preserves_cents_and_zero_software() -> None:
    result = allocate_multi_ip(10.01, 3, 10, {"A": 1, "B": 1, "C": 1})
    assert sum(result["projects"].values()) == result["stage1_software_share"]
    zero = allocate_multi_ip(10, 0, 10, {"A": 0, "B": 0})
    assert zero["projects"] == {"A": 0.0, "B": 0.0}


@pytest.mark.parametrize(
    "args",
    [
        (-1, 1, 1, {"A": 1}),
        (1, -1, 1, {"A": 1}),
        (1, 2, 1, {"A": 2}),
        (1, 1, 0, {"A": 1}),
        (1, 1, 1, {}),
        (1, 1, 1, {"A": 0.5}),
        (math.inf, 1, 1, {"A": 1}),
    ],
)
def test_multi_ip_rejects_bad_input(args) -> None:
    with pytest.raises(ValueError):
        allocate_multi_ip(*args)


def test_nexus_classification_and_aggregation() -> None:
    direct = nexus_classify(CostItem("IDE", 100, basket="IP"), "own_br")
    shared = nexus_classify(CostItem("Cloud", 100, basket="MIX", nexus_amount=25), "own_br")
    totals = aggregate_nexus_costs([direct, shared])
    assert totals == {"A": 125.0, "B": 0.0, "C": 0.0, "D": 0.0, "poza_nexus": 75.0}
    with pytest.raises(ValueError):
        nexus_classify(direct, "bad")
    with pytest.raises(ValueError):
        aggregate_nexus_costs([nexus_classify(CostItem("Cloud", 100, basket="MIX"), "own_br")])


def test_calculate_nexus_zero_and_mixed() -> None:
    assert calculate_nexus(0, 0, 0, 0)["nexus"] == 0
    assert calculate_nexus(100)["nexus"] == 1
    assert calculate_nexus(3500, 0, 10000, 0)["nexus"] == 0.337037
    with pytest.raises(ValueError):
        calculate_nexus(-1)


def test_compare_allocation_methods() -> None:
    result = compare_allocation_methods(
        mix_total=1000,
        annual_ip_revenue=80,
        annual_total_revenue=100,
        annual_w_percent=50,
        ip_income_before_mix=10000,
        nexus=1,
    )
    assert len(result["methods"]) == 2
    assert result["decision_rule"].startswith("follow documented")
    with pytest.raises(ValueError):
        compare_allocation_methods(
            mix_total=1,
            annual_ip_revenue=1,
            annual_total_revenue=1,
            annual_w_percent=101,
            ip_income_before_mix=1,
            nexus=1,
        )


def test_multi_ip_equality_uses_pln_cents_not_relative_tolerance() -> None:
    with pytest.raises(ValueError, match="PLN-cent precision"):
        allocate_multi_ip(
            100,
            1_000_000_000,
            1_000_000_000,
            {"A": 999_999_999.99},
        )
