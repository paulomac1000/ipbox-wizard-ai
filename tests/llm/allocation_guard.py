"""Build precision-aware allocation audit facts for the year-aware oracle."""

from __future__ import annotations

from typing import Any

from python_helper.allocation_audit import AllocationFinding, reconcile_return_to_ledger
from python_helper.allocation_precision import audit_revenue_allocation
from python_helper.input_validation import strict_bool

from . import oracle as legacy
from .oracle_adapter import invoice_amount, month_evidence, month_invoices, number

ScenarioError = legacy.ScenarioError


def _clients(input_data: dict[str, Any]) -> dict[str, bool | None]:
    result: dict[str, bool | None] = {}
    for client in input_data.get("kontrahenci", []) or []:
        if not isinstance(client, dict) or not client.get("nazwa"):
            continue
        try:
            value = (
                strict_bool(client["klauzula_IP"], f"client[{client.get('nazwa')}].klauzula_IP")
                if "klauzula_IP" in client
                else None
            )
        except ValueError as exc:
            raise ScenarioError(str(exc)) from exc
        result[str(client.get("nazwa"))] = value
    return result


def _invoice_is_ip(invoice: dict[str, Any], clients: dict[str, bool | None]) -> bool:
    client = str(invoice.get("kontrahent", "default"))
    if "kwalifikuje_IP" not in invoice:
        return clients.get(client) is True
    try:
        return strict_bool(invoice["kwalifikuje_IP"], "invoice.kwalifikuje_IP")
    except ValueError as exc:
        raise ScenarioError(str(exc)) from exc


def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _stream_row(
    *,
    month_id: str,
    stream: dict[str, Any],
    default_evidence: dict[str, Any],
    method: str,
    total: float,
    default_stream_id: str,
    expected_w_percent: float | None = None,
    rounding_steps: int = 1,
) -> dict[str, Any]:
    evidence = dict(default_evidence)
    override = stream.get("ewidencja")
    if isinstance(override, dict):
        evidence.update(override)
    reported_ip = number(
        _first(stream, "przychod_IP", "reported_ip_revenue", "ip_revenue", default=0),
        "kontrola.przychod_IP",
    )
    reported_non = number(
        _first(
            stream,
            "przychod_NIE",
            "reported_non_ip_revenue",
            "non_ip_revenue",
            default=total - reported_ip,
        ),
        "kontrola.przychod_NIE",
    )
    row = {
        "month": month_id,
        "stream_id": str(
            _first(
                stream,
                "stream_id",
                "allocation_id",
                "projekt",
                "nazwa",
                default=default_stream_id,
            )
        ),
        "total_revenue": total,
        "reported_ip_revenue": reported_ip,
        "reported_non_ip_revenue": reported_non,
        "work_hours": _first(
            stream,
            "work_hours",
            "godziny_pracy",
            default=evidence.get("godziny_pracy", 0),
        ),
        "non_ip_hours": _first(
            stream,
            "non_ip_hours",
            "godziny_nie_IP",
            default=evidence.get("godziny_nie_IP", 0),
        ),
        "invoice_percentage": _first(
            stream,
            "invoice_percentage",
            "procent_faktury_IP",
            default=evidence.get("procent_faktury_IP", 100),
        ),
        "w_method": str(stream.get("w_method", method)),
        "w_precision_pp": _first(
            stream,
            "w_precision_pp",
            "W_precision_pp",
            default=_first(evidence, "w_precision_pp", "W_precision_pp", default=0.01),
        ),
        "invoice_percentage_precision_pp": _first(
            stream,
            "invoice_percentage_precision_pp",
            default=evidence.get("invoice_percentage_precision_pp", 0.01),
        ),
        "rounding_steps": rounding_steps,
    }
    reported_w = _first(
        stream,
        "reported_w_percent",
        "reported_W",
        "W",
        "wartosc_W",
        "wartość_W",
        default=_first(
            evidence,
            "reported_w_percent",
            "reported_W",
            "W",
            "wartosc_W",
            "wartość_W",
        ),
    )
    if reported_w is not None:
        row["reported_w_percent"] = reported_w
    if expected_w_percent is not None:
        row["expected_w_percent"] = expected_w_percent
    return row


def _explicit_stream_rows(
    month: dict[str, Any],
    declared: dict[str, Any],
    invoices: list[dict[str, Any]],
    evidence: dict[str, Any],
    method: str,
) -> list[dict[str, Any]]:
    streams = _first(declared, "alokacje", "strumienie", "streams")
    if not isinstance(streams, list):
        return []
    projects = evidence.get("projekty", []) if isinstance(evidence.get("projekty"), list) else []
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(streams):
        if not isinstance(raw, dict):
            raise ScenarioError(f"kontrola_alokacji.alokacje[{index}] must be a mapping")
        stream = dict(raw)
        default_evidence = dict(evidence)
        total_raw = _first(stream, "total_revenue", "przychod", "kwota")
        invoice_index = stream.get("invoice_index", stream.get("faktura_index"))
        project_index = stream.get("project_index", stream.get("projekt_index"))
        if invoice_index is not None:
            try:
                invoice = invoices[int(invoice_index)]
            except (ValueError, IndexError) as exc:
                raise ScenarioError(f"invalid invoice_index in allocation stream {index}") from exc
            if total_raw is None:
                total_raw = invoice_amount(invoice)
            invoice_evidence = invoice.get("ewidencja")
            if isinstance(invoice_evidence, dict):
                default_evidence.update(invoice_evidence)
        if project_index is not None:
            try:
                project = projects[int(project_index)]
            except (ValueError, IndexError) as exc:
                raise ScenarioError(f"invalid project_index in allocation stream {index}") from exc
            if not isinstance(project, dict):
                raise ScenarioError(f"project_index {project_index} does not reference a mapping")
            if total_raw is None:
                total_raw = _first(project, "przychod", "total_revenue", "kwota")
            default_evidence.update(
                {
                    "godziny_pracy": _first(project, "godziny_pracy", "godziny", default=0),
                    "godziny_nie_IP": project.get("godziny_nie_IP", 0),
                    "procent_faktury_IP": project.get(
                        "procent_faktury_IP", evidence.get("procent_faktury_IP", 100)
                    ),
                }
            )
            stream.setdefault("stream_id", str(project.get("nazwa", f"project-{project_index}")))
        if total_raw is None:
            raise ScenarioError(
                f"allocation stream {index} requires total_revenue, invoice_index or project_index"
            )
        rows.append(
            _stream_row(
                month_id=str(month.get("miesiac", "")),
                stream=stream,
                default_evidence=default_evidence,
                method=method,
                total=number(total_raw, f"allocation[{index}].total_revenue"),
                default_stream_id=f"stream-{index}",
            )
        )
    return rows


def _invoice_level_rows(
    month: dict[str, Any],
    invoices: list[dict[str, Any]],
    evidence: dict[str, Any],
    method: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, invoice in enumerate(invoices):
        control = invoice.get("kontrola_alokacji")
        if not isinstance(control, dict):
            continue
        rows.append(
            _stream_row(
                month_id=str(month.get("miesiac", "")),
                stream=control,
                default_evidence=evidence,
                method=method,
                total=invoice_amount(invoice),
                default_stream_id=f"invoice-{index}",
            )
        )
    return rows


def _project_level_rows(
    month: dict[str, Any], evidence: dict[str, Any], method: str
) -> list[dict[str, Any]]:
    projects = evidence.get("projekty")
    if not isinstance(projects, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            continue
        control = project.get("kontrola_alokacji")
        if not isinstance(control, dict) and "przychod_IP" not in project:
            continue
        stream = dict(control or {})
        if "przychod_IP" in project:
            stream.setdefault("przychod_IP", project["przychod_IP"])
        if "przychod_NIE" in project:
            stream.setdefault("przychod_NIE", project["przychod_NIE"])
        stream.setdefault("stream_id", str(project.get("nazwa", f"project-{index}")))
        project_evidence = {
            "godziny_pracy": _first(project, "godziny_pracy", "godziny", default=0),
            "godziny_nie_IP": project.get("godziny_nie_IP", 0),
            "procent_faktury_IP": project.get(
                "procent_faktury_IP", evidence.get("procent_faktury_IP", 100)
            ),
        }
        total = number(
            _first(project, "przychod", "total_revenue", "kwota"),
            f"project[{index}].przychod",
        )
        rows.append(
            _stream_row(
                month_id=str(month.get("miesiac", "")),
                stream=stream,
                default_evidence=project_evidence,
                method=method,
                total=total,
                default_stream_id=f"project-{index}",
            )
        )
    return rows


def audit_facts(
    scenario: dict[str, Any], result: dict[str, Any], method: str
) -> tuple[dict[str, bool], list[str]]:
    input_data = scenario.get("input", {})
    clients = _clients(input_data)
    expected_w = {
        str(row.get("miesiąc", "")): number(row.get("wartość", 0), "monthly_W")
        for row in result.get("monthly_W", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    findings: list[AllocationFinding] = []
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict) or not isinstance(month.get("kontrola_alokacji"), dict):
            continue
        declared = month["kontrola_alokacji"]
        invoices = month_invoices(month)
        evidence = month_evidence(month) or {}

        month_rows = _explicit_stream_rows(month, declared, invoices, evidence, method)
        if not month_rows:
            month_rows = _invoice_level_rows(month, invoices, evidence, method)
        if not month_rows:
            month_rows = _project_level_rows(month, evidence, method)
        if month_rows:
            eligible_total = sum(
                invoice_amount(invoice) for invoice in invoices if _invoice_is_ip(invoice, clients)
            )
            controlled_total = sum(float(row["total_revenue"]) for row in month_rows)
            if abs(controlled_total - eligible_total) > 0.02:
                findings.append(
                    AllocationFinding(
                        "AUDIT_STREAM_TOTAL_MISMATCH",
                        str(month.get("miesiac", "")),
                        detail=(
                            f"eligible invoice total={eligible_total:.2f}; "
                            f"controlled streams={controlled_total:.2f}"
                        ),
                    )
                )
            rows.extend(month_rows)
            continue

        total = sum((invoice_amount(invoice) for invoice in invoices), 0.0)
        eligible_invoices = [invoice for invoice in invoices if _invoice_is_ip(invoice, clients)]
        eligible_total = sum((invoice_amount(invoice) for invoice in eligible_invoices), 0.0)
        known_non_ip = total - eligible_total
        ip = number(declared.get("przychod_IP"), "kontrola.przychod_IP")
        reported_non_total = number(
            declared.get("przychod_NIE", total - ip), "kontrola.przychod_NIE"
        )
        if reported_non_total + 0.02 < known_non_ip:
            findings.append(
                AllocationFinding(
                    "KNOWN_NON_IP_REVENUE_NOT_PRESERVED",
                    str(month.get("miesiac", "")),
                    detail=(
                        f"known fully non-IP invoices={known_non_ip:.2f}; "
                        f"reported non-IP={reported_non_total:.2f}"
                    ),
                )
            )
            audited_non = 0.0
        else:
            audited_non = max(0.0, reported_non_total - known_non_ip)
        if eligible_total > 0 or ip > 0:
            rows.append(
                _stream_row(
                    month_id=str(month.get("miesiac", "")),
                    stream={
                        **declared,
                        "przychod_IP": ip,
                        "przychod_NIE": audited_non,
                        "stream_id": "eligible-invoices",
                    },
                    default_evidence=evidence,
                    method=method,
                    total=eligible_total,
                    default_stream_id="eligible-invoices",
                    expected_w_percent=expected_w.get(str(month.get("miesiac", ""))),
                    rounding_steps=max(1, len(eligible_invoices)),
                )
            )

    findings.extend(audit_revenue_allocation(rows) if rows else [])
    reconciliation = input_data.get("uzgodnienie_zeznania")
    if isinstance(reconciliation, dict):
        ledger = {
            "ip_revenue": result["result"]["przychody_roczne"]["IP"],
            "non_ip_revenue": result["result"]["przychody_roczne"]["NIE"],
            "ip_cost": result["result"]["koszty_roczne"]["IP"],
            "non_ip_cost": result["result"]["koszty_roczne"]["NIE"],
        }
        tax_return = {
            "ip_revenue": reconciliation.get("przychod_IP", reconciliation.get("ip_revenue", 0)),
            "non_ip_revenue": reconciliation.get(
                "przychod_NIE", reconciliation.get("non_ip_revenue", 0)
            ),
            "ip_cost": reconciliation.get("koszt_IP", reconciliation.get("ip_cost", 0)),
            "non_ip_cost": reconciliation.get("koszt_NIE", reconciliation.get("non_ip_cost", 0)),
        }
        findings.extend(reconcile_return_to_ledger(ledger, tax_return))
    codes = {finding.code for finding in findings}
    facts = {
        "revenue_allocation_inconsistent": bool(
            codes
            & {
                "REVENUE_SPLIT_DOES_NOT_BALANCE",
                "REVENUE_ALLOCATION_MISMATCH",
                "FULL_REVENUE_DESPITE_NON_IP_SHARE",
                "W_VALUE_MISMATCH",
                "KNOWN_NON_IP_REVENUE_NOT_PRESERVED",
                "AUDIT_STREAM_TOTAL_MISMATCH",
            }
        ),
        "invoice_percentage_double_applied": "INVOICE_PERCENTAGE_DOUBLE_APPLIED" in codes,
        "allocation_method_changed_without_evidence": "ALLOCATION_METHOD_SWITCH" in codes,
        "return_ledger_reconciliation_failed": any(code.startswith("RETURN_") for code in codes),
    }
    return facts, sorted(codes)
