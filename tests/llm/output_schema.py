"""
Strict JSON Schema for LLM output validation.

This schema defines the EXACT output shape the LLM must return.
OpenRouter supports response_format=json_schema with strict=True.
"""

from __future__ import annotations

from typing import Any

OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "name": "ipbox_output",
    "strict": True,
    "schema": {
        "type": "object",
        "required": ["result", "classifications", "monthly_W", "tests", "stops_reviews"],
        "additionalProperties": False,
        "properties": {
            "result": {
                "type": "object",
                "required": ["rok", "przychody_roczne", "nexus", "podatek"],
                "additionalProperties": False,
                "properties": {
                    "rok": {"type": "integer"},
                    "przychody_roczne": {
                        "type": "object",
                        "required": ["IP", "NIE"],
                        "properties": {"IP": {"type": "number"}, "NIE": {"type": "number"}},
                        "additionalProperties": False,
                    },
                    "nexus": {"type": "number"},
                    "podatek": {
                        "type": "object",
                        "required": ["podatek_IP", "podatek_NIE_finalny", "podatek_całościowy"],
                        "properties": {
                            "podatek_IP": {"type": "number"},
                            "podatek_NIE_finalny": {"type": "number"},
                            "podatek_całościowy": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                    "dochód_IP": {"type": "number"},
                    "dochód_NIE": {"type": "number"},
                    "klucz_MIX": {
                        "type": "object",
                        "properties": {"metoda": {"type": "string"}, "źródło": {"type": "string"}},
                        "additionalProperties": False,
                    },
                    "alokacja_multi_ip": {
                        "type": "object",
                        "properties": {
                            "stage1_software_share": {"type": "number"},
                            "IP_A": {"type": "number"},
                            "IP_B": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "classifications": {"type": "array", "items": {"type": "string"}},
            "monthly_W": {"type": "object", "additionalProperties": {"type": "number"}},
            "tests": {"type": "object", "additionalProperties": {"type": "string"}},
            "stops_reviews": {
                "type": "object",
                "properties": {
                    "stops": {"type": "array", "items": {"type": "string"}},
                    "reviews": {"type": "array", "items": {"type": "string"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
    },
}
