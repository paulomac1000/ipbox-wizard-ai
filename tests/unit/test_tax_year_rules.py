from __future__ import annotations

import math

import pytest

from python_helper.tax_year_rules import (
    calculate_scale_tax,
    calculate_tax_for_year,
    get_tax_year_rules,
    supported_years,
    validate_year_amounts,
)


def test_all_ipbox_years_are_supported() -> None:
    assert supported_years() == tuple(range(2019, 2027))


@pytest.mark.parametrize(
    ("year", "ikze", "health"),
    [
        (2019, 5718.00, None),
        (2020, 6272.40, None),
        (2021, 9466.20, None),
        (2022, 10659.60, 8700.00),
        (2023, 12483.00, 10200.00),
        (2024, 14083.20, 11600.00),
        (2025, 15611.40, 12900.00),
        (2026, 16956.00, 14100.00),
    ],
)
def test_historical_limits(year: int, ikze: float, health: float | None) -> None:
    rules = get_tax_year_rules(year)
    assert float(rules.ikze_business_limit) == ikze
    assert (float(rules.health_linear_limit) if rules.health_linear_limit else None) == health


@pytest.mark.parametrize("year", [2019, 2020, 2021])
def test_pre_2022_rejects_income_health_and_simultaneous_br(year: int) -> None:
    assert validate_year_amounts(year, health_income_deduction=1) == ["HEALTH_MODE_INVALID"]
    assert validate_year_amounts(year, rd_relief_ip=1) == ["BR_IPBOX_NOT_SIMULTANEOUS"]


@pytest.mark.parametrize("year", [2022, 2023, 2024, 2025, 2026])
def test_post_2021_rejects_old_health_credit(year: int) -> None:
    assert validate_year_amounts(year, health_tax_credit=1) == ["HEALTH_MODE_INVALID"]


def test_limits_are_not_silently_clipped() -> None:
    violations = validate_year_amounts(
        2024,
        ikze=14083.21,
        health_income_deduction=11600.01,
    )
    assert violations == ["IKZE_LIMIT_EXCEEDED", "HEALTH_LIMIT_EXCEEDED"]


@pytest.mark.parametrize("bad", [2018, 2027, "x", None])
def test_unsupported_years_fail_closed(bad) -> None:
    with pytest.raises(ValueError):
        get_tax_year_rules(bad)


def test_historical_scale_known_points() -> None:
    assert calculate_scale_tax(2019, 8000) == 0
    assert calculate_scale_tax(2019, 13000) == 1759
    assert calculate_scale_tax(2020, 8000) == 0
    assert calculate_scale_tax(2020, 13000) == 1685
    assert calculate_scale_tax(2021, 85528) == 14015
    assert calculate_scale_tax(2022, 30000) == 0
    assert calculate_scale_tax(2026, 200000) == 36400


def test_2024_linear_cascade_matches_pit_like_pattern_without_real_data() -> None:
    result = calculate_tax_for_year(
        2024,
        non_ip_income=30000,
        ip_income=180000,
        nexus=1,
        tax_form="liniowy_19%",
        social_security_deduction=15000,
        ikze=14000,
        thermomodernization_pool=10000,
    )
    assert result["non_ip_base_rounded"] == 0
    assert result["thermomodernization_used"] == 1000
    assert result["thermomodernization_carry_over"] == 9000
    assert result["ip_tax"] == 9000
    assert result["total_tax"] == 9000


def test_2019_health_credit_reduces_combined_tax_after_ipbox() -> None:
    result = calculate_tax_for_year(
        2019,
        non_ip_income=20000,
        ip_income=100000,
        nexus=1,
        tax_form="liniowy_19%",
        ikze=5000,
        health_tax_credit=1200,
    )
    assert result["non_ip_base_rounded"] == 15000
    assert result["non_ip_tax_final"] == 2850
    assert result["ip_tax"] == 5000
    assert result["total_tax_before_health_credit"] == 7850
    assert result["health_tax_credit_used"] == 1200
    assert result["total_tax"] == 6650


def test_2021_simultaneous_br_ipbox_is_rejected() -> None:
    with pytest.raises(ValueError, match="BR_IPBOX_NOT_SIMULTANEOUS"):
        calculate_tax_for_year(
            2021,
            non_ip_income=10000,
            ip_income=100000,
            nexus=1,
            tax_form="liniowy_19%",
            rd_relief_ip=1000,
            rd_relief_limit=1000,
        )


def test_2022_simultaneous_br_ipbox_is_allowed() -> None:
    result = calculate_tax_for_year(
        2022,
        non_ip_income=10000,
        ip_income=100000,
        nexus=0.5,
        tax_form="liniowy_19%",
        rd_relief_ip=1000,
        rd_relief_limit=1000,
    )
    assert result["rd_relief_ip_used"] == 1000
    assert result["ip_base_rounded"] == 49500
    assert result["ip_tax"] == 2475


def test_scale_combines_extra_income_but_business_loss_does_not_consume_it() -> None:
    result = calculate_tax_for_year(
        2020,
        non_ip_income=10000,
        ip_income=0,
        nexus=0,
        tax_form="skala",
        previous_non_ip_business_losses=20000,
        extra_income_scale=50000,
    )
    assert result["non_ip_base_rounded"] == 50000
    assert result["total_tax"] == calculate_scale_tax(2020, 50000)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ikze": -1},
        {"non_ip_income": math.inf},
        {"nexus": 2},
        {"internet_tax_relief": 761},
        {"thermomodernization_pool": 53000.01},
    ],
)
def test_invalid_inputs_fail(kwargs: dict[str, float]) -> None:
    base = dict(
        year=2025,
        non_ip_income=10000,
        ip_income=10000,
        nexus=1,
        tax_form="skala",
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        calculate_tax_for_year(**base)


def test_linear_rejects_scale_only_reliefs_and_extra_income() -> None:
    with pytest.raises(ValueError):
        calculate_tax_for_year(
            2025,
            non_ip_income=10000,
            ip_income=0,
            nexus=0,
            tax_form="liniowy_19%",
            donations=1,
        )
    with pytest.raises(ValueError):
        calculate_tax_for_year(
            2025,
            non_ip_income=10000,
            ip_income=0,
            nexus=0,
            tax_form="liniowy_19%",
            extra_income_scale=1,
        )


def test_thermomodernization_lots_use_oldest_and_expire_after_six_years() -> None:
    from python_helper.tax_year_rules import apply_thermomodernization_lots

    result = apply_thermomodernization_lots(
        2026,
        [
            {"origin_year": 2019, "remaining_amount": 1000, "evidence_ref": "old"},
            {"origin_year": 2020, "remaining_amount": 2000, "evidence_ref": "new"},
        ],
        1500,
    )
    assert result["expired"] == 1000
    assert result["used"] == 1500
    assert result["carry_over"] == 500
    assert result["lots"][0]["expired"] == 1000


def test_tax_cascade_accepts_thermomodernization_lots() -> None:
    result = calculate_tax_for_year(
        2025,
        non_ip_income=3000,
        ip_income=10000,
        nexus=1,
        tax_form="liniowy_19%",
        thermomodernization_lots=[
            {"origin_year": 2022, "remaining_amount": 2000},
            {"origin_year": 2024, "remaining_amount": 2000},
        ],
    )
    assert result["thermomodernization_used"] == 3000
    assert result["thermomodernization_carry_over"] == 1000
    assert result["thermomodernization_expired"] == 0


def test_correction_settlement_distinguishes_return_from_cash_delta() -> None:
    from python_helper.tax_year_rules import reconcile_correction_settlement

    result = reconcile_correction_settlement(
        advances_paid=40000,
        original_tax_due=0,
        corrected_tax_due=10000,
        refund_already_disbursed=40000,
    )
    assert result == {
        "original_overpayment": 40000.0,
        "corrected_overpayment": 30000.0,
        "refund_already_disbursed": 40000.0,
        "cash_adjustment": 10000.0,
        "action": "refund_to_repay_or_offset",
    }


def test_thermomodernization_lots_enforce_total_taxpayer_limit() -> None:
    from python_helper.tax_year_rules import apply_thermomodernization_lots

    with pytest.raises(ValueError, match="53000"):
        apply_thermomodernization_lots(
            2025,
            [
                {"origin_year": 2023, "remaining_amount": 30000},
                {"origin_year": 2024, "remaining_amount": 23000.01},
            ],
            10000,
        )
