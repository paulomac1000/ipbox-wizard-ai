"""Strict JSON Schema shared by all benchmark models."""

from __future__ import annotations

from typing import Any

MONEY = {"type": "number"}
NONNEGATIVE_MONEY = {"type": "number"}
CODE = {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"}


DECISION_JSON_SCHEMA: dict[str, Any] = {
    "name": "ipbox_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "stops", "reviews"],
        "properties": {
            "status": {"enum": ["FINAL", "STOPPED"]},
            "stops": {"type": "array", "items": CODE},
            "reviews": {"type": "array", "items": CODE},
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
                    "nexus": {"type": "number"},
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
                                "type": ["number", "null"],
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
                        ],
                        "properties": {
                            "podstawa_IP": NONNEGATIVE_MONEY,
                            "podstawa_NIE": NONNEGATIVE_MONEY,
                            "podatek_IP": NONNEGATIVE_MONEY,
                            "podatek_NIE_finalny": NONNEGATIVE_MONEY,
                            "podatek_całościowy": NONNEGATIVE_MONEY,
                            "nadpłata_lub_dopłata": MONEY,
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
                            "type": ["number", "null"],
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
                        "wartość": {"type": "number"},
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
