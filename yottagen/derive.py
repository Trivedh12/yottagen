"""Pure derivation engine for derived metrics, ledger balances, totals, and business days.

All derived values in YottaGen are strictly computed from primary source records
to prevent data drift and guarantee mathematical reconciliation.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Tuple

from yottagen.calendar import CalendarEngine
from yottagen.config import REFERENCE_DATE, REFERENCE_DATE_STR
from yottagen.ids import format_leave_balance_id


def derive_date_metrics(
    calendar_engine: CalendarEngine,
    start_date: datetime.date,
    end_date: datetime.date,
    country: str,
) -> Tuple[int, int, int, int]:
    """Derive calendar days, business days, weekend days, and holiday days."""
    return calendar_engine.compute_date_span_metrics(start_date, end_date, country)


def derive_leave_balances(
    employees: List[Dict[str, Any]],
    leave_policies: List[Dict[str, Any]],
    ledger_entries: List[Dict[str, Any]],
    leave_requests: List[Dict[str, Any]],
    as_of_date: str = REFERENCE_DATE_STR,
) -> List[Dict[str, Any]]:
    """Derive point-in-time LeaveBalance snapshots strictly from ledger entries and pending requests.

    Formula:
    closing_balance = opening_balance + accrued_days + adjusted_days - used_days
    """
    # Index ledger by (employee_id, policy_id)
    ledger_by_emp_pol: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for entry in ledger_entries:
        if entry["effective_date"] <= as_of_date:
            key = (entry["employee_id"], entry["policy_id"])
            ledger_by_emp_pol.setdefault(key, []).append(entry)

    # Index pending requests by (employee_id, policy_id)
    pending_by_emp_pol: Dict[Tuple[str, str], float] = {}
    for req in leave_requests:
        if req["status"] in ("PENDING_APPROVAL", "SUBMITTED"):
            key = (req["employee_id"], req["policy_id"])
            pending_by_emp_pol[key] = pending_by_emp_pol.get(key, 0.0) + float(req["business_days"])

    balances: List[Dict[str, Any]] = []
    bal_idx = 1

    for emp in employees:
        emp_id = emp["employee_id"]
        for pol in leave_policies:
            pol_id = pol["policy_id"]
            entries = ledger_by_emp_pol.get((emp_id, pol_id), [])

            opening = 0.0
            accrued = 0.0
            used = 0.0
            adjusted = 0.0

            for e in entries:
                etype = e["entry_type"]
                days = float(e["days"])
                if etype == "CARRY_FORWARD":
                    opening += days
                elif etype == "ACCRUAL":
                    accrued += days
                elif etype == "USAGE":
                    used += abs(days)  # USAGE is recorded as negative delta in ledger
                elif etype in ("ADJUSTMENT", "FORFEIT"):
                    adjusted += days

            closing = opening + accrued + adjusted - used
            pending = pending_by_emp_pol.get((emp_id, pol_id), 0.0)

            balances.append({
                "balance_id": format_leave_balance_id(bal_idx),
                "employee_id": emp_id,
                "policy_id": pol_id,
                "as_of_date": as_of_date,
                "opening_balance": round(opening, 2),
                "accrued_days": round(accrued, 2),
                "used_days": round(used, 2),
                "adjusted_days": round(adjusted, 2),
                "pending_days": round(pending, 2),
                "closing_balance": round(closing, 2),
            })
            bal_idx += 1

    balances.sort(key=lambda b: (b["employee_id"], b["policy_id"]))
    return balances


def derive_expense_claim_totals(lines: List[Dict[str, Any]]) -> Tuple[float, float, int]:
    """Derive total_amount_local, total_amount_base, and line_count from expense lines."""
    tot_local = sum(round(float(line["amount_local"]), 2) for line in lines)
    tot_base = sum(round(float(line["amount_base"]), 2) for line in lines)
    return round(tot_local, 2), round(tot_base, 2), len(lines)


def derive_reimbursement_amount(lines: List[Dict[str, Any]]) -> float:
    """Derive reimbursement amount from approved, non-disallowed claim lines."""
    approved_total = sum(
        round(float(line["amount_local"]), 2)
        for line in lines
        if not int(line.get("is_disallowed", 0))
    )
    return round(approved_total, 2)
