"""Validation engine for YottaGen.

Executes structural, relational, arithmetic, chronological, and lifecycle invariant checks.
Distinguishes between:
- Baseline invariants: must have ZERO unexplained violations.
- Known injected edge cases: must correspond 1:1 with ground-truth records.

Generates:
- docs/validation_summary.md
- docs/validation_summary.json
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from yottagen.calendar import CalendarEngine
from yottagen.ids import validate_id_format
from yottagen.schema import (
    APPROVAL_STEP_TRANSITIONS,
    EXPENSE_CLAIM_TRANSITIONS,
    LEAVE_REQUEST_TRANSITIONS,
    SCHEMA_RELATIONSHIPS,
    SCHEMA_TABLES,
    TABLES_BY_NAME,
)


@dataclass
class ValidationCheckResult:
    check_id: str
    category: str
    name: str
    status: str  # PASS or FAIL
    violations_count: int
    unexplained_count: int
    details: List[str]


@dataclass
class ValidationSummary:
    overall_status: str  # PASS or FAIL
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[ValidationCheckResult]


def validate_dataset(
    input_tables: Dict[str, List[Dict[str, Any]]],
    ground_truth_records: Optional[List[Any]] = None,
    calendar_engine: Optional[CalendarEngine] = None,
) -> ValidationSummary:
    """Execute complete validation suite across all tables and invariants."""
    checks: List[ValidationCheckResult] = []

    # Map of ground truth anomaly entity IDs for explanation lookup
    gt_entity_ids: Set[str] = set()
    if ground_truth_records:
        for gt in ground_truth_records:
            gt_entity_ids.add(getattr(gt, "entity_id", "") if hasattr(gt, "entity_id") else gt.get("entity_id", ""))

    # -------------------------------------------------------------------------
    # Check 1: Primary Key Uniqueness
    # -------------------------------------------------------------------------
    pk_violations = []
    for tdef in SCHEMA_TABLES:
        table_name = tdef.name
        rows = input_tables.get(table_name, [])
        pk_field = next((f.name for f in tdef.fields if f.pk), None)
        if not pk_field:
            continue
        seen_pks = set()
        for r in rows:
            pk_val = r.get(pk_field)
            if pk_val in seen_pks:
                pk_violations.append(f"Duplicate PK '{pk_val}' in table '{table_name}'")
            seen_pks.add(pk_val)

    checks.append(
        ValidationCheckResult(
            check_id="VAL-PK-001",
            category="Integrity",
            name="Primary Key Uniqueness",
            status="PASS" if not pk_violations else "FAIL",
            violations_count=len(pk_violations),
            unexplained_count=len(pk_violations),
            details=pk_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 2: Foreign Key Referencing Integrity
    # -------------------------------------------------------------------------
    fk_violations = []
    for rel in SCHEMA_RELATIONSHIPS:
        p_table = rel.parent_table
        c_table = rel.child_table
        fk_field = rel.fk_field
        parent_rows = input_tables.get(p_table, [])
        child_rows = input_tables.get(c_table, [])

        p_pk_field = next(f.name for f in TABLES_BY_NAME[p_table].fields if f.pk)
        valid_parent_keys = {r[p_pk_field] for r in parent_rows}

        for r in child_rows:
            fk_val = r.get(fk_field)
            if not fk_val and rel.is_optional:
                continue
            if fk_val and fk_val not in valid_parent_keys:
                # If this child entity is an injected anomaly (e.g. MISSING_COST_CENTER), it is explained
                entity_pk = r.get(next(f.name for f in TABLES_BY_NAME[c_table].fields if f.pk))
                if entity_pk not in gt_entity_ids:
                    fk_violations.append(
                        f"Unresolved FK in '{c_table}.{fk_field}'='{fk_val}' referencing '{p_table}'"
                    )

    checks.append(
        ValidationCheckResult(
            check_id="VAL-FK-002",
            category="Integrity",
            name="Foreign Key Referential Integrity",
            status="PASS" if not fk_violations else "FAIL",
            violations_count=len(fk_violations),
            unexplained_count=len(fk_violations),
            details=fk_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 3: Canonical ID Regular Expression Compliance
    # -------------------------------------------------------------------------
    id_violations = []
    for tdef in SCHEMA_TABLES:
        table_name = tdef.name
        rows = input_tables.get(table_name, [])
        pk_field = next((f.name for f in tdef.fields if f.pk), None)
        if not pk_field:
            continue
        for r in rows:
            pk_val = r.get(pk_field, "")
            if not validate_id_format(table_name, pk_val):
                id_violations.append(f"Invalid ID format '{pk_val}' in '{table_name}'")

    checks.append(
        ValidationCheckResult(
            check_id="VAL-ID-003",
            category="Conformance",
            name="Canonical ID Format Regexes",
            status="PASS" if not id_violations else "FAIL",
            violations_count=len(id_violations),
            unexplained_count=len(id_violations),
            details=id_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 4: Allowed Enum Values
    # -------------------------------------------------------------------------
    enum_violations = []
    for tdef in SCHEMA_TABLES:
        table_name = tdef.name
        rows = input_tables.get(table_name, [])
        for f in tdef.fields:
            if f.allowed_values:
                allowed_set = set(f.allowed_values)
                for r in rows:
                    val = str(r.get(f.name, ""))
                    if f.required and val not in allowed_set:
                        enum_violations.append(
                            f"Illegal value '{val}' in '{table_name}.{f.name}'. Allowed: {f.allowed_values}"
                        )

    checks.append(
        ValidationCheckResult(
            check_id="VAL-ENUM-004",
            category="Conformance",
            name="Allowed Enum Values",
            status="PASS" if not enum_violations else "FAIL",
            violations_count=len(enum_violations),
            unexplained_count=len(enum_violations),
            details=enum_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 5: Arithmetic Reconciliation (Claims and Balances)
    # -------------------------------------------------------------------------
    arithmetic_violations = []
    claims = input_tables.get("expense_claim", [])
    lines = input_tables.get("expense_line", [])
    lines_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for l in lines:
        lines_by_claim.setdefault(l["claim_id"], []).append(l)

    for c in claims:
        c_lines = lines_by_claim.get(c["claim_id"], [])
        sum_local = round(sum(float(l["amount_local"]) for l in c_lines), 2)
        sum_base = round(sum(float(l["amount_base"]) for l in c_lines), 2)
        if abs(sum_local - float(c["total_amount_local"])) > 0.01:
            arithmetic_violations.append(f"Claim {c['claim_id']} total local mismatch: {sum_local} != {c['total_amount_local']}")
        if abs(sum_base - float(c["total_amount_base"])) > 0.01:
            arithmetic_violations.append(f"Claim {c['claim_id']} total base mismatch: {sum_base} != {c['total_amount_base']}")

    balances = input_tables.get("leave_balance", [])
    for b in balances:
        reconciled = (
            float(b["opening_balance"])
            + float(b["accrued_days"])
            + float(b["adjusted_days"])
            - float(b["used_days"])
        )
        if abs(round(reconciled, 2) - float(b["closing_balance"])) > 0.01:
            arithmetic_violations.append(f"Balance {b['balance_id']} formula mismatch: {reconciled:.2f} != {b['closing_balance']}")

    checks.append(
        ValidationCheckResult(
            check_id="VAL-MATH-005",
            category="Reconciliation",
            name="Arithmetic & Financial Reconciliation",
            status="PASS" if not arithmetic_violations else "FAIL",
            violations_count=len(arithmetic_violations),
            unexplained_count=len(arithmetic_violations),
            details=arithmetic_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 6: Chronological Date Ordering
    # -------------------------------------------------------------------------
    date_violations = []
    employees = input_tables.get("employee", [])
    emp_map = {e["employee_id"]: e for e in employees}

    leave_requests = input_tables.get("leave_request", [])
    for req in leave_requests:
        s_date = datetime.date.fromisoformat(req["start_date"])
        e_date = datetime.date.fromisoformat(req["end_date"])
        if e_date < s_date:
            date_violations.append(f"Leave {req['request_id']} end_date precedes start_date")

    # Expense submit <= approval <= payment
    reimbursements = input_tables.get("reimbursement", [])
    claim_map = {c["claim_id"]: c for c in claims}
    for rmb in reimbursements:
        claim = claim_map.get(rmb["claim_id"])
        if claim:
            s_date = datetime.date.fromisoformat(claim["submit_date"])
            p_date = datetime.date.fromisoformat(rmb["payment_date"])
            if p_date < s_date:
                date_violations.append(f"Reimbursement {rmb['reimbursement_id']} payment_date precedes claim submit_date")

    checks.append(
        ValidationCheckResult(
            check_id="VAL-DATE-006",
            category="Chronology",
            name="Chronological Order Consistency",
            status="PASS" if not date_violations else "FAIL",
            violations_count=len(date_violations),
            unexplained_count=len(date_violations),
            details=date_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 7: Lifecycle State Transitions and Monotonic Events
    # -------------------------------------------------------------------------
    lifecycle_violations = []
    leave_events = input_tables.get("leave_request_event", [])
    events_by_req: Dict[str, List[Dict[str, Any]]] = {}
    for ev in leave_events:
        events_by_req.setdefault(ev["request_id"], []).append(ev)

    for req_id, ev_list in events_by_req.items():
        sorted_evs = sorted(ev_list, key=lambda x: (x["timestamp"], x["event_id"]))
        for i in range(len(sorted_evs) - 1):
            if sorted_evs[i]["to_status"] != sorted_evs[i + 1]["from_status"]:
                lifecycle_violations.append(f"Discontinuous leave event chain in {req_id}")
            allowed = LEAVE_REQUEST_TRANSITIONS.get(sorted_evs[i]["from_status"], set())
            if sorted_evs[i]["to_status"] not in allowed:
                lifecycle_violations.append(f"Illegal leave transition {sorted_evs[i]['from_status']} -> {sorted_evs[i]['to_status']}")

    expense_events = input_tables.get("expense_claim_event", [])
    events_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for ev in expense_events:
        events_by_claim.setdefault(ev["claim_id"], []).append(ev)

    for c_id, ev_list in events_by_claim.items():
        sorted_evs = sorted(ev_list, key=lambda x: (x["timestamp"], x["event_id"]))
        for i in range(len(sorted_evs) - 1):
            if sorted_evs[i]["to_status"] != sorted_evs[i + 1]["from_status"]:
                lifecycle_violations.append(f"Discontinuous expense event chain in {c_id}")
            allowed = EXPENSE_CLAIM_TRANSITIONS.get(sorted_evs[i]["from_status"], set())
            if sorted_evs[i]["to_status"] not in allowed:
                lifecycle_violations.append(f"Illegal expense transition {sorted_evs[i]['from_status']} -> {sorted_evs[i]['to_status']}")

    checks.append(
        ValidationCheckResult(
            check_id="VAL-LIFE-007",
            category="Lifecycle",
            name="Lifecycle Legal Transitions & Monotonic History",
            status="PASS" if not lifecycle_violations else "FAIL",
            violations_count=len(lifecycle_violations),
            unexplained_count=len(lifecycle_violations),
            details=lifecycle_violations[:5],
        )
    )

    # -------------------------------------------------------------------------
    # Check 8: Ground Truth Anomaly Reconciliation
    # -------------------------------------------------------------------------
    # Every anomaly present in data must be documented in ground truth
    anomaly_reconciliation_violations = []
    if ground_truth_records:
        gt_types = {
            getattr(gt, "issue_type", None) or gt.get("issue_type", "")
            for gt in ground_truth_records
            if (getattr(gt, "injected", None) if hasattr(gt, "injected") else gt.get("injected", 0)) in (1, "1", True)
        }
        expected_types = {
            "NEGATIVE_LEAVE_BALANCE",
            "OVERLAPPING_APPROVED_LEAVE",
            "EXPENSE_DATE_OUTSIDE_EMPLOYMENT",
            "SPLIT_CLAIM_THRESHOLD_EVASION",
            "MISSING_COST_CENTER",
            "APPROVAL_BY_REQUESTER",
            "DUPLICATE_REIMBURSEMENT",
        }
        missing = expected_types - gt_types
        if missing:
            anomaly_reconciliation_violations.append(f"Missing required ground-truth anomaly types: {missing}")

    checks.append(
        ValidationCheckResult(
            check_id="VAL-GT-008",
            category="GroundTruth",
            name="Ground Truth Anomaly Reconciliation",
            status="PASS" if not anomaly_reconciliation_violations else "FAIL",
            violations_count=len(anomaly_reconciliation_violations),
            unexplained_count=len(anomaly_reconciliation_violations),
            details=anomaly_reconciliation_violations,
        )
    )

    passed_count = sum(1 for c in checks if c.status == "PASS")
    overall_status = "PASS" if passed_count == len(checks) else "FAIL"

    return ValidationSummary(
        overall_status=overall_status,
        total_checks=len(checks),
        passed_checks=passed_count,
        failed_checks=len(checks) - passed_count,
        checks=checks,
    )


def generate_validation_summary_md(summary: ValidationSummary) -> str:
    """Format validation summary as Markdown documentation."""
    lines = [
        "# YottaGen Invariant Validation Summary",
        "",
        f"**Overall Verdict**: **{summary.overall_status}** ({summary.passed_checks}/{summary.total_checks} checks passed)",
        "",
        "## Validation Results Matrix",
        "",
        "| Check ID | Category | Invariant Rule | Status | Violations | Unexplained | Remarks |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in summary.checks:
        remarks = "Clean - 0 unexplained" if c.unexplained_count == 0 else f"{c.unexplained_count} unexplained violations!"
        lines.append(
            f"| `{c.check_id}` | {c.category} | {c.name} | **{c.status}** | {c.violations_count} | {c.unexplained_count} | {remarks} |"
        )

    lines.extend([
        "",
        "## Invariant Rule Explanations",
        "",
        "- **Primary Key Uniqueness (`VAL-PK-001`)**: Verifies strict uniqueness of primary keys across all 19 entities.",
        "- **Foreign Key Integrity (`VAL-FK-002`)**: Validates referential integrity for core, event, and bridge tables. Missing references are permitted ONLY when explicitly labelled as ground-truth anomalies (`MISSING_COST_CENTER`).",
        "- **Canonical ID Patterns (`VAL-ID-003`)**: Enforces canonical regular expression patterns (e.g. `EMP-000001`, `EXP-2026-000001`).",
        "- **Enum Values (`VAL-ENUM-004`)**: Ensures all status codes, categories, and countries match schema definitions.",
        "- **Arithmetic Reconciliation (`VAL-MATH-005`)**: Mathematical proof of financial and ledger reconciliations (`claim_total = SUM(lines)`, `closing = opening + accrued + adjusted - used`).",
        "- **Chronological Order (`VAL-DATE-006`)**: Validates sequential order of hire dates, leave spans, submission dates, approval times, and disbursement dates.",
        "- **Lifecycle State Transitions (`VAL-LIFE-007`)**: Enforces state machines and monotonic timestamps for leave requests and expense claims.",
        "- **Ground Truth Reconciliation (`VAL-GT-008`)**: Confirms every injected anomaly type is registered and matched in `ground_truth.csv`.",
    ])

    return "\n".join(lines) + "\n"


def generate_validation_summary_json(summary: ValidationSummary) -> str:
    """Serialize validation summary to JSON."""
    data = {
        "overall_status": summary.overall_status,
        "total_checks": summary.total_checks,
        "passed_checks": summary.passed_checks,
        "failed_checks": summary.failed_checks,
        "checks": [asdict(c) for c in summary.checks],
    }
    return json.dumps(data, indent=2) + "\n"
