"""Fail-closed wrapper for the precision allocation audit.

The primary oracle owns STOP facts for missing or unusable documentation. The
secondary precision audit is meaningful only when at least one independent
allocation stream has positive work-hour evidence. This wrapper prevents a raw
validation error from replacing the primary STOP report.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .allocation_guard import audit_facts as _audit_facts
from .oracle_adapter import month_evidence, number


def _positive_work_hours(evidence: Any) -> bool:
    if not isinstance(evidence, dict):
        return False
    try:
        return (
            number(evidence.get("godziny_pracy", evidence.get("work_hours", 0)), "work_hours") > 0
        )
    except Exception:
        return False


def _stream_has_evidence(stream: Any) -> bool:
    if not isinstance(stream, dict):
        return False
    if _positive_work_hours(stream.get("ewidencja")):
        return True
    return _positive_work_hours(stream)


def _month_has_auditable_evidence(month: dict[str, Any]) -> bool:
    if _positive_work_hours(month_evidence(month)):
        return True

    declared = month.get("kontrola_alokacji")
    if isinstance(declared, dict):
        for key in ("alokacje", "strumienie", "streams"):
            streams = declared.get(key)
            if isinstance(streams, list) and any(_stream_has_evidence(item) for item in streams):
                return True

    for invoice in month.get("faktury", []) or []:
        if not isinstance(invoice, dict):
            continue
        control = invoice.get("kontrola_alokacji")
        if isinstance(control, dict) and (
            _stream_has_evidence(control) or _positive_work_hours(invoice.get("ewidencja"))
        ):
            return True

    evidence = month_evidence(month)
    projects = evidence.get("projekty") if isinstance(evidence, dict) else None
    return bool(
        isinstance(projects, list) and any(_stream_has_evidence(project) for project in projects)
    )


def audit_facts(
    scenario: dict[str, Any], result: dict[str, Any], method: str
) -> tuple[dict[str, bool], list[str]]:
    """Run the precision audit only for controls backed by usable evidence."""
    filtered = deepcopy(scenario)
    input_data = filtered.get("input")
    if isinstance(input_data, dict):
        for month in input_data.get("miesiace", []) or []:
            if (
                isinstance(month, dict)
                and isinstance(month.get("kontrola_alokacji"), dict)
                and not _month_has_auditable_evidence(month)
            ):
                month.pop("kontrola_alokacji", None)
    return _audit_facts(filtered, result, method)
