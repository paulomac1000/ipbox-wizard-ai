from tests.llm.allocation_guard import audit_facts


def base_result(w):
    return {
        "monthly_W": [{"miesiąc": "2024-01", "wartość": w}],
        "result": {
            "przychody_roczne": {"IP": 0, "NIE": 0},
            "koszty_roczne": {"IP": 0, "NIE": 0},
        },
    }


def test_month_aggregate_separates_known_non_ip_invoice():
    scenario = {
        "input": {
            "kontrahenci": [{"nazwa": "A", "klauzula_IP": True}],
            "miesiace": [
                {
                    "miesiac": "2024-01",
                    "faktury": [
                        {"kwota_PLN": 10000, "kontrahent": "A", "kwalifikuje_IP": True},
                        {"kwota_PLN": 2500, "kontrahent": "B", "kwalifikuje_IP": False},
                    ],
                    "ewidencja": {
                        "godziny_pracy": 160,
                        "godziny_nie_IP": 16,
                        "procent_faktury_IP": 80,
                    },
                    "kontrola_alokacji": {"przychod_IP": 7000, "przychod_NIE": 5500},
                }
            ],
        }
    }
    facts, codes = audit_facts(scenario, base_result(70), "disjoint_components")
    assert facts["revenue_allocation_inconsistent"] is False
    assert codes == []


def test_project_streams_are_audited_independently():
    scenario = {
        "input": {
            "kontrahenci": [
                {"nazwa": "A", "klauzula_IP": True},
                {"nazwa": "B", "klauzula_IP": True},
            ],
            "miesiace": [
                {
                    "miesiac": "2024-01",
                    "faktury": [
                        {"kwota_PLN": 15000, "kontrahent": "A", "kwalifikuje_IP": True},
                        {"kwota_PLN": 10000, "kontrahent": "B", "kwalifikuje_IP": True},
                    ],
                    "ewidencja": {
                        "godziny_pracy": 160,
                        "godziny_nie_IP": 40,
                        "procent_faktury_IP": 100,
                        "projekty": [
                            {
                                "nazwa": "A",
                                "godziny": 100,
                                "godziny_nie_IP": 10,
                                "przychod": 15000,
                            },
                            {
                                "nazwa": "B",
                                "godziny": 60,
                                "godziny_nie_IP": 30,
                                "przychod": 10000,
                            },
                        ],
                    },
                    "kontrola_alokacji": {
                        "alokacje": [
                            {
                                "projekt_index": 0,
                                "przychod_IP": 13500,
                                "przychod_NIE": 1500,
                                "W": 90,
                            },
                            {
                                "projekt_index": 1,
                                "przychod_IP": 5000,
                                "przychod_NIE": 5000,
                                "W": 50,
                            },
                        ]
                    },
                }
            ],
        }
    }
    facts, codes = audit_facts(scenario, base_result(74), "time_only")
    assert facts["revenue_allocation_inconsistent"] is False
    assert codes == []


def test_rounded_double_percentage_and_switch_create_all_stops():
    scenario = {
        "input": {
            "kontrahenci": [{"nazwa": "A", "klauzula_IP": True}],
            "miesiace": [
                {
                    "miesiac": "2025-01",
                    "faktury": [{"kwota_PLN": 23100, "kontrahent": "A", "kwalifikuje_IP": True}],
                    "ewidencja": {
                        "godziny_pracy": 168,
                        "godziny_nie_IP": 22,
                        "procent_faktury_IP": 81.82,
                    },
                    "kontrola_alokacji": {
                        "przychod_IP": 15463.64,
                        "przychod_NIE": 7636.36,
                    },
                },
                {
                    "miesiac": "2025-02",
                    "faktury": [{"kwota_PLN": 23100, "kontrahent": "A", "kwalifikuje_IP": True}],
                    "ewidencja": {
                        "godziny_pracy": 168,
                        "godziny_nie_IP": 22,
                        "procent_faktury_IP": 100,
                    },
                    "kontrola_alokacji": {"przychod_IP": 23100, "przychod_NIE": 0},
                },
            ],
        }
    }
    result = base_result(68.72)
    result["monthly_W"].append({"miesiąc": "2025-01", "wartość": 68.72})
    result["monthly_W"].append({"miesiąc": "2025-02", "wartość": 86.90})
    facts, codes = audit_facts(scenario, result, "disjoint_components")
    assert facts["revenue_allocation_inconsistent"] is True
    assert facts["invoice_percentage_double_applied"] is True
    assert facts["allocation_method_changed_without_evidence"] is True
    assert "INVOICE_PERCENTAGE_DOUBLE_APPLIED" in codes
    assert "ALLOCATION_METHOD_SWITCH" in codes
