from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.llm.evaluator import Evaluator
from tests.llm.oracle import (
    ScenarioError,
    compute_reference,
    derive_decision_codes,
    validate_scenario,
)
from tests.llm.output_schema import DECISION_JSON_SCHEMA, OUTPUT_JSON_SCHEMA
from tests.llm.runner import (
    LLMTestRunner,
    build_decision_protocol,
    build_tool_context,
)

SCENARIOS = sorted((Path(__file__).parents[1] / "llm/scenarios").glob("*.yaml"))


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scenario(name: str) -> dict:
    return load(next(path for path in SCENARIOS if path.stem == name))


def decision_for(reference: dict) -> dict:
    return {
        "status": reference["status"],
        "stops": reference["stops_reviews"]["stops"],
        "reviews": reference["stops_reviews"]["reviews"],
    }


def test_exact_scenario_set_and_contracts() -> None:
    assert len(SCENARIOS) == 46
    ids = []
    for path in SCENARIOS:
        loaded = load(path)
        validate_scenario(loaded)
        ids.append(loaded["meta"]["id"])
        assert not loaded["meta"].get("skip")
        assert loaded["assertions"]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("scenario_path", SCENARIOS, ids=lambda path: path.stem)
def test_oracle_output_matches_schema_and_self_evaluates(scenario_path: Path) -> None:
    loaded = load(scenario_path)
    reference = compute_reference(loaded)
    schema_validated = {key: value for key, value in reference.items() if key != "decision_facts"}
    errors = list(Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"]).iter_errors(schema_validated))
    assert errors == []
    assert reference["decision_facts"]
    assert all(isinstance(value, bool) for value in reference["decision_facts"].values())
    failures, _ = Evaluator(loaded).evaluate(reference)
    assert failures == []


def test_oracle_regressions() -> None:
    by_id = {path.stem: compute_reference(load(path)) for path in SCENARIOS}
    assert by_id["23_loss_carry_forward"]["result"]["przychody_roczne"]["IP"] == 18000
    assert by_id["23_loss_carry_forward"]["result"]["podatek"]["podatek_IP"] == 896
    assert by_id["29_edge_related_parties_nexus_0"]["result"]["podatek"]["podatek_IP"] == 0
    assert by_id["30_edge_related_parties_nexus_mixed"]["result"]["nexus"] == 0.337037
    assert by_id["39_multi_project_weighted_W"]["monthly_W"][0]["wartość"] == 74.0
    assert by_id["44_mix_revenue_key_kis"]["result"]["klucz_MIX"]["metoda"] == (
        "przychodowa_roczna"
    )
    assert by_id["45_multi_ip_two_stage"]["result"]["alokacja_multi_ip"]["allocations"] == [
        {"ip": "IP_A", "amount": 3000.0},
        {"ip": "IP_B", "amount": 5000.0},
    ]


@pytest.mark.parametrize(
    ("name", "expected_stops", "expected_reviews"),
    [
        ("14_lump_sum_ineligible_check", {"STOP_01"}, set()),
        ("18_logic_zero_work_hours", {"STOP_04"}, {"REVIEW_09"}),
        ("38_verify_missing_kpir_data", {"STOP_08"}, {"REVIEW_09"}),
        ("42_stop_08_no_documentation", {"STOP_08"}, {"REVIEW_09"}),
        (
            "45_multi_ip_two_stage",
            set(),
            {"REVIEW_04", "REVIEW_16", "REVIEW_17"},
        ),
    ],
)
def test_atomic_decision_facts_prevent_stop_cascades(
    name: str,
    expected_stops: set[str],
    expected_reviews: set[str],
) -> None:
    reference = compute_reference(scenario(name))
    stops, reviews = derive_decision_codes(reference["decision_facts"])
    assert stops == expected_stops
    assert reviews == expected_reviews
    assert set(reference["stops_reviews"]["stops"]) == expected_stops
    assert set(reference["stops_reviews"]["reviews"]) == expected_reviews


def test_multi_ip_is_a_visible_review_fact() -> None:
    reference = compute_reference(scenario("45_multi_ip_two_stage"))
    assert reference["decision_facts"]["multiple_projects_or_ips"] is True
    assert reference["decision_facts"]["uses_kis_interpretation"] is True
    assert reference["decision_facts"]["kis_implementation_requires_confirmation"] is True


def test_meta_expected_reviews_cannot_change_oracle_truth() -> None:
    loaded = scenario("01_basic_linear")
    baseline = compute_reference(loaded)
    mutated = deepcopy(loaded)
    mutated["meta"]["expected_reviews"] = ["REVIEW_99"]
    observed = compute_reference(mutated)
    assert observed["decision_facts"] == baseline["decision_facts"]
    assert observed["stops_reviews"] == baseline["stops_reviews"]


def test_evaluator_is_fail_closed_for_missing_fields() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    broken = deepcopy(reference)
    del broken["tests"]["TEST_7"]
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "test_oracle_mismatch" for failure in failures)

    broken = deepcopy(reference)
    broken["result"]["nexus"] = None
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "nexus_mismatch" for failure in failures)

    broken = deepcopy(reference)
    broken["classifications"] = []
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "classification_keys" for failure in failures)


def test_evaluator_rejects_extra_decision_codes() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)

    broken = deepcopy(reference)
    broken["stops_reviews"]["reviews"].append("REVIEW_99")
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "reviews" for failure in failures)

    broken = deepcopy(reference)
    broken["stops_reviews"]["warnings"].append("WARNING_99")
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "warnings" for failure in failures)


def test_test_key_space_alias_is_understood() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    reference["tests"] = {key.replace("_", " "): value for key, value in reference["tests"].items()}
    failures, _ = Evaluator(loaded).evaluate(reference)
    assert failures == []


def test_invalid_scenario_contracts() -> None:
    loaded = load(SCENARIOS[0])
    for mutation in (
        lambda value: value.pop("meta"),
        lambda value: value["input"].pop("rok"),
        lambda value: value["input"].pop("forma_opodatkowania"),
        lambda value: value.update(assertions={}),
        lambda value: value["input"].pop("polityka_alokacji"),
        lambda value: value["input"].update(ulgi={"ikze": -1}),
        lambda value: value["input"].update(ulgi={"straty_poprzednie": 1}),
        lambda value: value["input"].update(zus="not-a-mapping"),
        lambda value: value["input"].update(zaliczki={"suma": -1}),
        lambda value: value["input"]["miesiace"][0].update(faktury=["not-a-mapping"]),
        lambda value: value["input"]["miesiace"][0].update(
            faktury=[{"kwota_PLN": -1, "kwalifikuje_IP": True}]
        ),
        lambda value: value["input"]["miesiace"][0].update(koszty=["not-a-mapping"]),
    ):
        broken = deepcopy(loaded)
        mutation(broken)
        with pytest.raises(ScenarioError):
            validate_scenario(broken)


@pytest.mark.parametrize("month_id", ["2026-01", "2025-13", "2025-1"])
def test_month_identifier_must_be_strict_and_match_input_year(month_id: str) -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["miesiace"][0]["miesiac"] = month_id
    with pytest.raises(ScenarioError, match="miesiac"):
        validate_scenario(loaded)


def test_thermomodernization_limit_is_fail_closed() -> None:
    loaded = deepcopy(scenario("27_termomodernizacja_full"))
    loaded["input"]["ulgi"]["termomodernizacja_pula"] = 53_000.01
    with pytest.raises(ScenarioError, match="cannot exceed 53000"):
        compute_reference(loaded)


def test_year_dependent_limits_fail_closed() -> None:
    loaded = scenario("41_ikze_cascade")
    excessive = deepcopy(loaded)
    excessive["input"]["ulgi"]["ikze"] = 15611.41
    excessive_reference = compute_reference(excessive)
    assert excessive_reference["status"] == "STOPPED"
    assert "STOP_14" in excessive_reference["stops_reviews"]["stops"]

    unknown_year = deepcopy(loaded)
    unknown_year["input"]["rok"] = 2027
    for month in unknown_year["input"]["miesiace"]:
        month["miesiac"] = month["miesiac"].replace("2025-", "2027-")
    unknown_reference = compute_reference(unknown_year)
    assert unknown_reference["status"] == "STOPPED"
    assert "STOP_16" in unknown_reference["stops_reviews"]["stops"]

    health = scenario("12_zus_in_pit_path")
    health = deepcopy(health)
    health["input"]["zus"]["odliczenie_zdrowotne_PIT"] = 1
    health["input"]["rok"] = 2027
    for month in health["input"]["miesiace"]:
        month["miesiac"] = month["miesiac"].replace("2025-", "2027-")
    health_reference = compute_reference(health)
    assert health_reference["status"] == "STOPPED"
    assert "STOP_16" in health_reference["stops_reviews"]["stops"]


def test_runner_exposes_only_authoritative_decision_envelope() -> None:
    import json

    loaded = scenario("51_return_ledger_classification_shift_stop")
    reference = compute_reference(loaded)
    context = build_tool_context(reference)
    assert context == {
        "expected_decision": {
            "status": "STOPPED",
            "stops": ["STOP_12"],
            "reviews": ["REVIEW_09"],
        }
    }

    serialized = json.dumps(context, ensure_ascii=False)
    assert "return_ledger_reconciliation_failed" not in serialized
    assert "single_positive_revenue_client" not in serialized
    assert "decision_facts" not in serialized

    prompt = LLMTestRunner(None).build_prompt("ignored human documentation", loaded)
    assert "AUTHORITATIVE DECISION ENVELOPE" in prompt
    assert "expected_decision" in prompt
    assert "active_rules" not in prompt
    assert "deterministic_report" not in prompt
    assert '"result"' not in prompt
    assert "return_ledger_reconciliation_failed" not in prompt
    assert "single_positive_revenue_client" not in prompt


def test_decision_protocol_keeps_stop_and_review_channels_independent() -> None:
    protocol = build_decision_protocol()
    assert "Copy expected_decision.stops exactly" in protocol
    assert "Copy expected_decision.reviews exactly" in protocol
    assert "A STOP never moves, suppresses, or converts a REVIEW code" in protocol
    assert "Do not invent, omit, duplicate, or reclassify" in protocol
    assert "Markdown fences" in protocol
    assert "STOP_01" not in protocol
    assert "REVIEW_09" not in protocol


def test_decision_schema_rejects_cross_channel_codes() -> None:
    validator = Draft202012Validator(DECISION_JSON_SCHEMA["schema"])
    review_in_stops = {
        "status": "STOPPED",
        "stops": ["STOP_12", "REVIEW_09"],
        "reviews": [],
    }
    stop_in_reviews = {
        "status": "STOPPED",
        "stops": ["STOP_12"],
        "reviews": ["STOP_12"],
    }
    assert list(validator.iter_errors(review_in_stops))
    assert list(validator.iter_errors(stop_in_reviews))


def test_authoritative_envelope_preserves_empty_and_nonempty_stop_channels() -> None:
    final_context = build_tool_context(compute_reference(scenario("01_basic_linear")))
    stopped_context = build_tool_context(
        compute_reference(scenario("14_lump_sum_ineligible_check"))
    )
    assert final_context["expected_decision"]["stops"] == []
    assert final_context["expected_decision"]["status"] == "FINAL"
    assert stopped_context["expected_decision"]["stops"] == ["STOP_01"]
    assert stopped_context["expected_decision"]["status"] == "STOPPED"


def test_runner_assembles_deterministic_report_after_small_model_decision() -> None:
    loaded = scenario("45_multi_ip_two_stage")
    reference = compute_reference(loaded)
    runner = LLMTestRunner(None)
    raw_decision = yaml.safe_dump(decision_for(reference), sort_keys=False)
    # JSON is mandatory; YAML that is not JSON must be rejected.
    with pytest.raises(ValueError, match="pure JSON"):
        runner.validate_semantics(raw_decision, loaded)

    import json

    assembled = runner.validate_semantics(json.dumps(decision_for(reference)), loaded)
    assert assembled["result"] == reference["result"]
    assert assembled["tests"] == reference["tests"]
    assert assembled["stops_reviews"] == reference["stops_reviews"]


def test_runner_rejects_a_full_report_instead_of_decision_envelope() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    runner = LLMTestRunner(None)

    import json

    with pytest.raises(ValueError, match="decision does not match strict schema"):
        runner.parse_decision(json.dumps(reference, ensure_ascii=False))


def test_oracle_stops_when_no_qualifying_ip_revenue() -> None:
    loaded = scenario("40_mixed_ip_clause")
    loaded = deepcopy(loaded)
    for client in loaded["input"]["kontrahenci"]:
        client["klauzula_IP"] = False
    for month in loaded["input"]["miesiace"]:
        for invoice in month["faktury"]:
            invoice["kwalifikuje_IP"] = False
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    assert reference["stops_reviews"]["stops"] == ["STOP_03"]
    assert reference["result"]["podatek"]["podatek_IP"] == 0


def test_missing_qualification_evidence_defaults_to_non_ip() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["kontrahenci"][0].pop("klauzula_IP")
    loaded["input"]["miesiace"][0]["faktury"][0].pop("kwalifikuje_IP")
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    assert reference["stops_reviews"]["stops"] == ["STOP_03"]


def test_oracle_rejects_invalid_w_instead_of_using_zero() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    evidence = loaded["input"]["miesiace"][0]["ewidencja"]
    evidence["godziny_pracy"] = 10
    evidence["godziny_nie_IP"] = 11
    with pytest.raises(ScenarioError, match="non_ip_hours cannot exceed work_hours"):
        compute_reference(loaded)


def test_valid_zero_w_triggers_low_w_review() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    evidence = loaded["input"]["miesiace"][0]["ewidencja"]
    evidence["godziny_nie_IP"] = evidence["godziny_pracy"]
    reference = compute_reference(loaded)
    assert reference["monthly_W"] == [{"miesiąc": "2025-01", "wartość": 0.0}]
    assert "REVIEW_02" in reference["stops_reviews"]["reviews"]


def test_revenue_key_outside_fraction_fails_closed() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["polityka_alokacji"]["przychody"] = {
        "metoda": "custom",
        "klucz": 1.01,
    }
    with pytest.raises(ScenarioError, match="revenue_key"):
        compute_reference(loaded)


def test_health_deduction_applies_once_and_double_dip_stops() -> None:
    loaded = deepcopy(scenario("12_zus_in_pit_path"))
    loaded["input"]["zus"]["odliczenie_zdrowotne_PIT"] = 1000
    reference = compute_reference(loaded)
    assert reference["result"]["podatek"]["podstawa_NIE"] == 2200
    assert reference["result"]["podatek"]["podatek_NIE_finalny"] == 418

    loaded["input"]["zus"]["zdrowotna_w_KPiR"] = True
    stopped = compute_reference(loaded)
    assert "HEALTH_DOUBLE_DIP" in stopped["stops_reviews"]["stops"]
    assert stopped["status"] == "STOPPED"
    assert stopped["result"]["podatek"]["podatek_całościowy"] == 0


def test_health_deduction_year_limit_is_enforced() -> None:
    loaded = deepcopy(scenario("12_zus_in_pit_path"))
    loaded["input"]["zus"]["odliczenie_zdrowotne_PIT"] = 12900.01
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    assert "STOP_14" in reference["stops_reviews"]["stops"]


def test_stopped_report_zeros_every_financial_output() -> None:
    loaded = scenario("14_lump_sum_ineligible_check")
    loaded["input"]["ulgi"] = {
        "ulga_internet": 760,
        "ulga_prorodzinna": 1112.04,
        "weryfikacja": {
            "ulga_internet": {
                "zweryfikowana": True,
                "kategoria": "pierwsze_dwa_lata",
                "dowod": "faktury_2025",
            },
            "ulga_prorodzinna": {
                "zweryfikowana": True,
                "kategoria": "jedno_dziecko",
                "dowod": "dane_rodzinne_2025",
            },
        },
    }
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    result = reference["result"]
    assert all(value == 0 for value in result["przychody_roczne"].values())
    assert all(value == 0 for value in result["koszty_roczne"].values())
    assert all(value == 0 for value in result["nexus_koszty"].values())
    assert result["nexus"] == 0
    assert result["dochód_IP"] == result["dochód_NIE"] == 0
    assert all(value == 0 for value in result["podatek"].values())
    assert result["alokacja_multi_ip"] is None
    assert result["klucz_MIX"]["wartość"] is None
    assert reference["classifications"] == []


def test_evaluator_rejects_duplicate_semantic_keys() -> None:
    loaded = scenario("45_multi_ip_two_stage")
    reference = compute_reference(loaded)

    duplicate_month = deepcopy(reference)
    duplicate_month["monthly_W"].append(deepcopy(duplicate_month["monthly_W"][0]))
    failures, _ = Evaluator(loaded).evaluate(duplicate_month)
    assert any(item["type"] == "duplicate_month" for item in failures)

    duplicate_ip = deepcopy(reference)
    duplicate_ip["result"]["alokacja_multi_ip"]["allocations"].append(
        deepcopy(duplicate_ip["result"]["alokacja_multi_ip"]["allocations"][0])
    )
    failures, _ = Evaluator(loaded).evaluate(duplicate_ip)
    assert any(item["type"] == "duplicate_multi_ip" for item in failures)

    duplicate_code = deepcopy(reference)
    duplicate_code["stops_reviews"]["reviews"].append(duplicate_code["stops_reviews"]["reviews"][0])
    failures, _ = Evaluator(loaded).evaluate(duplicate_code)
    assert any(item["type"] == "duplicate_reviews" for item in failures)


def test_schema_rejects_negative_and_out_of_range_values() -> None:
    reference = compute_reference(scenario("01_basic_linear"))
    base = {key: value for key, value in reference.items() if key != "decision_facts"}

    mutations = [
        lambda value: value["result"]["podatek"].__setitem__("podatek_IP", -1),
        lambda value: value["result"].__setitem__("nexus", 1.01),
        lambda value: value["monthly_W"][0].__setitem__("wartość", 100.01),
        lambda value: value["classifications"][0].__setitem__("allocation_key", 1.01),
    ]
    validator = Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"])
    for mutation in mutations:
        invalid = deepcopy(base)
        mutation(invalid)
        assert list(validator.iter_errors(invalid))


def test_personal_relief_requires_verified_record() -> None:
    loaded = deepcopy(scenario("25_rehab_relief"))
    del loaded["input"]["ulgi"]["weryfikacja"]
    with pytest.raises(ScenarioError, match="weryfikacja.*must be a mapping"):
        compute_reference(loaded)


def test_b_r_relief_cannot_exceed_documented_qualified_costs() -> None:
    loaded = deepcopy(scenario("26_rd_relief_nexus"))
    loaded["input"]["ulgi"]["ulga_BR_IP"] = 501
    loaded["input"]["ulgi"]["ulga_BR_limit_odliczenia"] = 501
    with pytest.raises(ScenarioError, match="exceeds documented IP-qualified"):
        compute_reference(loaded)


def test_invalid_shapes_fail_with_scenario_error() -> None:
    loaded = deepcopy(scenario("45_multi_ip_two_stage"))
    loaded["input"]["kontrahenci"] = None
    with pytest.raises(ScenarioError, match="not null"):
        validate_scenario(loaded)

    loaded = deepcopy(scenario("45_multi_ip_two_stage"))
    del loaded["input"]["alokacja_multi_ip"]["przychody_IP"]
    with pytest.raises(ScenarioError, match="przychody_IP is required"):
        validate_scenario(loaded)


def test_direct_ip_cost_requires_real_allocation_source() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["miesiace"][0]["koszty"][0].pop("allocation_source")
    with pytest.raises(ScenarioError, match="requires allocation_source"):
        validate_scenario(loaded)


def test_fx_scenarios_use_source_currency_and_derived_differences() -> None:
    fx = compute_reference(scenario("03_fx_usd_single_client"))
    assert fx["result"]["przychody_roczne"] == {"IP": 20000.0, "NIE": 150.0}

    mixed = compute_reference(scenario("11_multi_client_mixed_currencies"))
    assert mixed["result"]["przychody_roczne"] == {"IP": 22900.0, "NIE": 50.0}
    assert mixed["result"]["koszty_roczne"]["NIE"] == 100.0


@pytest.mark.parametrize("value", ["false", "nie", "0", "true", "unexpected", 0, 1])
def test_qualification_flags_require_actual_booleans(value) -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["miesiace"][0]["faktury"][0]["kwalifikuje_IP"] = value
    with pytest.raises(ScenarioError, match="must be a boolean"):
        validate_scenario(loaded)

    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["kontrahenci"][0]["klauzula_IP"] = value
    with pytest.raises(ScenarioError, match="must be a boolean"):
        validate_scenario(loaded)


def test_missing_global_qualified_right_is_not_assumed_true() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"].pop("kwalifikowane_IP")

    result = compute_reference(loaded)

    assert result["status"] == "STOPPED"
    assert "STOP_02" in result["stops_reviews"]["stops"]


def test_documented_revenue_requires_explicit_split_or_explicit_full_ip() -> None:
    loaded = deepcopy(scenario("40_mixed_ip_clause"))
    invoice = loaded["input"]["miesiace"][0]["faktury"][0]
    invoice.pop("całość_IP")
    with pytest.raises(ScenarioError, match="kwota_IP or całość_IP"):
        validate_scenario(loaded)

    invoice["całość_IP"] = False
    with pytest.raises(ScenarioError, match="całość_IP=false"):
        validate_scenario(loaded)


def test_cost_date_mix_denominator_includes_positive_fx_difference() -> None:
    loaded = deepcopy(scenario("52_cost_date_revenue_mix_policy"))
    invoice = loaded["input"]["miesiace"][0]["faktury"][0]
    invoice.clear()
    invoice.update(
        {
            "kwota_waluta": 1000,
            "waluta": "USD",
            "data_wystawienia": "2025-06-02",
            "data_zaplaty": "2025-06-10",
            "data_kursu_przychodu": "2025-05-30",
            "kurs_przychodu": 10,
            "data_kursu_zaplaty": "2025-06-09",
            "kurs_zaplaty": 11,
            "źródło_kursu": "NBP_table_A_fixture",
            "kwota_IP": 3333,
            "kontrahent": "ClientA",
            "kwalifikuje_IP": True,
        }
    )

    result = compute_reference(loaded)

    mix_rows = [row for row in result["classifications"] if row["basket"] == "MIX"]
    assert mix_rows
    assert all(row["allocation_key"] == pytest.approx(3333 / 11000) for row in mix_rows)
    assert result["result"]["przychody_roczne"]["NIE"] == pytest.approx(7667)


@pytest.mark.parametrize("bad_year", [2025.5, "2025", True])
def test_scenario_year_type_is_strict(bad_year) -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["rok"] = bad_year
    with pytest.raises(ScenarioError, match="must be an integer"):
        validate_scenario(loaded)


def test_donation_scenario_rejects_missing_or_exceeded_verified_limit() -> None:
    loaded = deepcopy(scenario("24_donations_relief"))
    verification = loaded["input"]["ulgi"]["weryfikacja"]["darowizny"]
    verification.pop("limit_kwotowy")
    with pytest.raises(ScenarioError, match="limit_kwotowy"):
        validate_scenario(loaded)

    loaded = deepcopy(scenario("24_donations_relief"))
    loaded["input"]["ulgi"]["weryfikacja"]["darowizny"]["limit_kwotowy"] = 999
    with pytest.raises(ScenarioError, match="exceeds verified"):
        validate_scenario(loaded)
