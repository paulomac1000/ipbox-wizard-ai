"""Strict JSON Schema shared by all benchmark models."""

from __future__ import annotations

from typing import Any

MONEY = {"type": "number"}
NONNEGATIVE_MONEY = {"type": "number", "minimum": 0}
FRACTION = {"type": "number", "minimum": 0, "maximum": 1}
PERCENTAGE = {"type": "number", "minimum": 0, "maximum": 100}
CODE = {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"}
LEGACY_STOP_CODES = [
    "STOP_01",
    "STOP_02",
    "STOP_03",
    "STOP_04",
    "STOP_08",
    "ZUS_DOUBLE_DIP",
    "HEALTH_DOUBLE_DIP",
]
REVIEW_CODES = [
    "REVIEW_01",
    "REVIEW_02",
    "REVIEW_04",
    "REVIEW_08",
    "REVIEW_09",
    "REVIEW_16",
    "REVIEW_17",
]
STOP_CODE = {"type": "string", "enum": LEGACY_STOP_CODES}
REVIEW_CODE = {"type": "string", "enum": REVIEW_CODES}


DECISION_JSON_SCHEMA: dict[str, Any] = {
    "name": "ipbox_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "stops", "reviews"],
        "properties": {
            "status": {"enum": ["FINAL", "PROVISIONAL", "STOPPED"]},
            "stops": {"type": "array", "items": STOP_CODE, "uniqueItems": True},
            "reviews": {"type": "array", "items": REVIEW_CODE, "uniqueItems": True},
        },
    },
}

OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "name": "ipbox_wizard_result",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "status",
            "result",
            "classifications",
            "monthly_W",
            "tests",
            "stops_reviews",
        ],
        "properties": {
            "status": {"enum": ["FINAL", "PROVISIONAL", "STOPPED"]},
            "result": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "rok",
                    "przychody_roczne",
                    "koszty_roczne",
                    "nexus_koszty",
                    "nexus",
                    "dochód_IP",
                    "dochód_NIE",
                    "klucz_MIX",
                    "alokacja_multi_ip",
                    "podatek",
                ],
                "properties": {
                    "rok": {"type": "integer"},
                    "przychody_roczne": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["IP", "NIE"],
                        "properties": {"IP": NONNEGATIVE_MONEY, "NIE": NONNEGATIVE_MONEY},
                    },
                    "koszty_roczne": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["IP", "NIE", "MIX", "WYKLUCZONE"],
                        "properties": {
                            "IP": NONNEGATIVE_MONEY,
                            "NIE": NONNEGATIVE_MONEY,
                            "MIX": NONNEGATIVE_MONEY,
                            "WYKLUCZONE": NONNEGATIVE_MONEY,
                        },
                    },
                    "nexus_koszty": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["A", "B", "C", "D", "poza_nexus"],
                        "properties": {
                            "A": NONNEGATIVE_MONEY,
                            "B": NONNEGATIVE_MONEY,
                            "C": NONNEGATIVE_MONEY,
                            "D": NONNEGATIVE_MONEY,
                            "poza_nexus": NONNEGATIVE_MONEY,
                        },
                    },
                    "nexus": FRACTION,
                    "dochód_IP": MONEY,
                    "dochód_NIE": MONEY,
                    "klucz_MIX": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["metoda", "źródło", "wartość", "status"],
                        "properties": {
                            "metoda": {
                                "enum": [
                                    "przychodowa_roczna",
                                    "czasowa_W",
                                    "metraż",
                                    "licencje",
                                    "projekt",
                                    "custom",
                                ]
                            },
                            "źródło": {
                                "enum": [
                                    "interpretacja_KIS",
                                    "księgowa",
                                    "poprzednie_rozliczenie",
                                    "domyślna_wizard",
                                    "użytkownik",
                                ]
                            },
                            "wartość": {
                                "anyOf": [{"type": "null"}, FRACTION],
                            },
                            "status": {"enum": ["FINAL", "DEFERRED", "NOT_APPLICABLE"]},
                        },
                    },
                    "alokacja_multi_ip": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "stage1_software_share",
                                    "stage1_non_software_share",
                                    "allocations",
                                ],
                                "properties": {
                                    "stage1_software_share": NONNEGATIVE_MONEY,
                                    "stage1_non_software_share": NONNEGATIVE_MONEY,
                                    "allocations": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["ip", "amount"],
                                            "properties": {
                                                "ip": {"type": "string", "minLength": 1},
                                                "amount": NONNEGATIVE_MONEY,
                                            },
                                        },
                                    },
                                },
                            },
                        ]
                    },
                    "podatek": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "podstawa_IP",
                            "podstawa_NIE",
                            "podatek_IP",
                            "podatek_NIE_finalny",
                            "podatek_całościowy",
                            "nadpłata_lub_dopłata",
                            "termomodernization_carry_over",
                            "ulga_BR_IP_wykorzystana",
                            "ulga_BR_NIE_wykorzystana",
                            "ulga_BR_carry_over",
                            "dochód_dodatkowy_skala",
                        ],
                        "properties": {
                            "podstawa_IP": NONNEGATIVE_MONEY,
                            "podstawa_NIE": NONNEGATIVE_MONEY,
                            "podatek_IP": NONNEGATIVE_MONEY,
                            "podatek_NIE_finalny": NONNEGATIVE_MONEY,
                            "podatek_całościowy": NONNEGATIVE_MONEY,
                            "nadpłata_lub_dopłata": MONEY,
                            "termomodernization_carry_over": NONNEGATIVE_MONEY,
                            "ulga_BR_IP_wykorzystana": NONNEGATIVE_MONEY,
                            "ulga_BR_NIE_wykorzystana": NONNEGATIVE_MONEY,
                            "ulga_BR_carry_over": NONNEGATIVE_MONEY,
                            "dochód_dodatkowy_skala": NONNEGATIVE_MONEY,
                        },
                    },
                },
            },
            "classifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "opis",
                        "amount",
                        "basket",
                        "allocation_method",
                        "allocation_source",
                        "allocation_key",
                        "ip_amount",
                        "non_ip_amount",
                        "nexus_source",
                        "nexus_basket",
                        "nexus_amount",
                    ],
                    "properties": {
                        "opis": {"type": "string", "minLength": 1},
                        "amount": NONNEGATIVE_MONEY,
                        "basket": {"enum": ["IP", "MIX", "NON", "WYKLUCZONE"]},
                        "allocation_method": {"type": "string"},
                        "allocation_source": {"type": "string"},
                        "allocation_key": {
                            "anyOf": [{"type": "null"}, FRACTION],
                        },
                        "ip_amount": NONNEGATIVE_MONEY,
                        "non_ip_amount": NONNEGATIVE_MONEY,
                        "nexus_source": {
                            "enum": [
                                "own_br",
                                "unrelated_br_contractor",
                                "related_br_contractor",
                                "acquired_ip",
                                "outside_nexus",
                                "indirect_or_general",
                                "unknown",
                            ]
                        },
                        "nexus_basket": {"enum": ["A", "B", "C", "D", "poza_nexus"]},
                        "nexus_amount": NONNEGATIVE_MONEY,
                    },
                },
            },
            "monthly_W": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["miesiąc", "wartość"],
                    "properties": {
                        "miesiąc": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}$"},
                        "wartość": PERCENTAGE,
                    },
                },
            },
            "tests": {
                "type": "object",
                "additionalProperties": False,
                "required": [f"TEST_{number}" for number in range(1, 10)],
                "properties": {
                    f"TEST_{number}": {"enum": ["PASS", "FAIL"]} for number in range(1, 10)
                },
            },
            "stops_reviews": {
                "type": "object",
                "additionalProperties": False,
                "required": ["stops", "reviews", "warnings"],
                "properties": {
                    "stops": {"type": "array", "items": CODE, "uniqueItems": True},
                    "reviews": {"type": "array", "items": CODE, "uniqueItems": True},
                    "warnings": {"type": "array", "items": CODE, "uniqueItems": True},
                },
            },
        },
    },
}
