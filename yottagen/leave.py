"""Leave management engine for YottaGen.

Handles:
- Deterministic monthly accruals and ledger postings (LeaveBalanceLedger)
- Derived LeaveBalance calculation via derive.py
- LeaveRequest generation with seasonality and realistic duration skew
- Calendar calculations (business days, holidays, weekends)
- Rule-based status resolution (balance check, overlap check, notice period, consecutive days)
- Multi-tier approval routing and step instantiation (ApprovalStep)
- Append-only event history (LeaveRequestEvent)
- DecisionLog audit trail entries
"""

from __future__ import annotations

import datetime
import json
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from yottagen.calendar import CalendarEngine
from yottagen.config import REFERENCE_DATE, REFERENCE_DATE_STR, ScaleConfig
from yottagen.derive import derive_date_metrics, derive_leave_balances
from yottagen.ids import (
    format_approval_step_id,
    format_decision_id,
    format_leave_ledger_id,
    format_leave_request_event_id,
    format_leave_request_id,
)


@dataclass
class LeaveBundle:
    ledger_entries: List[Dict[str, Any]]
    balances: List[Dict[str, Any]]
    requests: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    approval_steps: List[Dict[str, Any]]
    decision_logs: List[Dict[str, Any]]


def generate_initial_accruals(
    employees: List[Dict[str, Any]],
    leave_policies: List[Dict[str, Any]],
    as_of_date: datetime.date = REFERENCE_DATE,
) -> List[Dict[str, Any]]:
    """Simulate month-by-month accruals and carry-forwards from hire date to as_of_date."""
    ledger_entries: List[Dict[str, Any]] = []
    ledger_idx = 1

    for emp in employees:
        emp_id = emp["employee_id"]
        hire_date = datetime.date.fromisoformat(emp["hire_date"])

        for pol in leave_policies:
            pol_id = pol["policy_id"]
            pol_name = pol["policy_name"]
            monthly_rate = float(pol["accrual_days_per_month"])
            annual_cap = float(pol["annual_cap"])
            carry_max = float(pol["carry_forward_max"])

            if pol_name == "Comp-Off":
                # Comp-off grant: give some employees initial 1-3 days grant for verified weekend coverage
                initial_grant = 2.0 if int(emp_id[-1]) % 3 == 0 else 1.0
                ledger_entries.append({
                    "ledger_id": format_leave_ledger_id(ledger_idx),
                    "employee_id": emp_id,
                    "policy_id": pol_id,
                    "entry_type": "ADJUSTMENT",
                    "days": initial_grant,
                    "effective_date": hire_date.isoformat(),
                    "reference_id": "SYSTEM_INITIAL_GRANT",
                    "created_at": f"{hire_date.isoformat()}T09:00:00Z",
                    "notes": "Initial earned compensatory leave grant",
                })
                ledger_idx += 1
                continue

            if pol_name in ("Parental", "Unpaid"):
                # Statutory allocation: available cap as entitlement
                entitlement = 90.0 if pol_name == "Parental" else 30.0
                ledger_entries.append({
                    "ledger_id": format_leave_ledger_id(ledger_idx),
                    "employee_id": emp_id,
                    "policy_id": pol_id,
                    "entry_type": "ADJUSTMENT",
                    "days": entitlement,
                    "effective_date": hire_date.isoformat(),
                    "reference_id": "SYSTEM_STATUTORY_GRANT",
                    "created_at": f"{hire_date.isoformat()}T09:00:00Z",
                    "notes": f"Statutory {pol_name} entitlement allocation",
                })
                ledger_idx += 1
                continue

            if monthly_rate <= 0:
                continue

            # Monthly accrual simulation from hire date up to as_of_date
            curr_year = hire_date.year
            curr_month = hire_date.month
            year_accrued = 0.0
            cumulative_balance = 0.0

            while True:
                first_of_month = datetime.date(curr_year, curr_month, 1)
                if first_of_month > as_of_date:
                    break

                # New calendar year: apply carry forward cap
                if curr_month == 1 and first_of_month > hire_date:
                    carry_forward = min(cumulative_balance, carry_max)
                    forfeited = cumulative_balance - carry_forward
                    if forfeited > 0:
                        ledger_entries.append({
                            "ledger_id": format_leave_ledger_id(ledger_idx),
                            "employee_id": emp_id,
                            "policy_id": pol_id,
                            "entry_type": "FORFEIT",
                            "days": -round(forfeited, 2),
                            "effective_date": first_of_month.isoformat(),
                            "reference_id": f"CARRY_CAP_{curr_year}",
                            "created_at": f"{first_of_month.isoformat()}T00:00:01Z",
                            "notes": f"Forfeiture exceeding carry-forward cap {carry_max} days",
                        })
                        ledger_idx += 1
                    cumulative_balance = carry_forward
                    year_accrued = 0.0

                # Accrue monthly rate if below annual cap
                credit = min(monthly_rate, max(0.0, annual_cap - year_accrued))
                if credit > 0:
                    ledger_entries.append({
                        "ledger_id": format_leave_ledger_id(ledger_idx),
                        "employee_id": emp_id,
                        "policy_id": pol_id,
                        "entry_type": "ACCRUAL",
                        "days": round(credit, 2),
                        "effective_date": first_of_month.isoformat(),
                        "reference_id": f"ACCRUAL_{curr_year}_{curr_month:02d}",
                        "created_at": f"{first_of_month.isoformat()}T00:01:00Z",
                        "notes": f"Standard monthly accrual for {curr_year}-{curr_month:02d}",
                    })
                    ledger_idx += 1
                    year_accrued += credit
                    cumulative_balance += credit

                # Increment month
                if curr_month == 12:
                    curr_month = 1
                    curr_year += 1
                else:
                    curr_month += 1

    ledger_entries.sort(key=lambda e: (e["employee_id"], e["effective_date"], e["ledger_id"]))
    return ledger_entries


def generate_leave_module(
    scale_config: ScaleConfig,
    employees: List[Dict[str, Any]],
    leave_policies: List[Dict[str, Any]],
    approval_rules: List[Dict[str, Any]],
    calendar_engine: CalendarEngine,
    rng: random.Random,
) -> LeaveBundle:
    """Generate leave requests, route approvals, record ledger usages, and log decisions."""
    # 1. Generate baseline accruals
    ledger_entries = generate_initial_accruals(employees, leave_policies, REFERENCE_DATE)

    # Fast lookup caches
    emp_map = {e["employee_id"]: e for e in employees}
    pol_map = {p["policy_id"]: p for p in leave_policies}
    pol_by_name = {p["policy_name"]: p for p in leave_policies}

    # Running available balance by (employee_id, policy_id)
    running_balances: Dict[Tuple[str, str], float] = {}
    for entry in ledger_entries:
        key = (entry["employee_id"], entry["policy_id"])
        running_balances[key] = running_balances.get(key, 0.0) + float(entry["days"])

    # HR and Director approver pools
    hr_approvers = [e["employee_id"] for e in employees if e.get("is_hr_approver") and e["status"] == "ACTIVE"]
    if not hr_approvers:
        hr_approvers = [e["employee_id"] for e in employees if e["job_level"] >= 4]

    # Target number of requests
    target_requests = scale_config.num_leave_requests

    # Policy distribution weights
    policy_weights = [
        ("Annual", 0.60),
        ("Sick", 0.22),
        ("Casual", 0.10),
        ("Parental", 0.04),
        ("Comp-Off", 0.03),
        ("Unpaid", 0.01),
    ]

    requests: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    approval_steps: List[Dict[str, Any]] = []
    decision_logs: List[Dict[str, Any]] = []

    req_idx = 1
    event_idx = 1
    ledger_idx = len(ledger_entries) + 1
    dec_idx = 1

    # Track approved date spans per employee to test overlap and maintain baseline purity
    approved_spans_by_emp: Dict[str, List[Tuple[datetime.date, datetime.date]]] = {}

    # Reason code map by policy
    reasons_by_policy = {
        "Annual": ["VACATION", "FAMILY", "PERSONAL"],
        "Sick": ["ILLNESS", "EMERGENCY"],
        "Casual": ["PERSONAL", "FAMILY", "EMERGENCY"],
        "Parental": ["MATERNITY_PATERNITY"],
        "Comp-Off": ["PERSONAL", "VACATION"],
        "Unpaid": ["PERSONAL", "FAMILY"],
    }

    # Generate requests
    for _ in range(target_requests):
        req_id = format_leave_request_id(req_idx)
        req_idx += 1

        # Select employee (active or on_leave)
        candidate_emps = [e for e in employees if e["status"] in ("ACTIVE", "ON_LEAVE")]
        emp = rng.choice(candidate_emps)
        emp_id = emp["employee_id"]
        country = emp["country"]
        hire_date = datetime.date.fromisoformat(emp["hire_date"])

        # Select policy
        r_pol = rng.random()
        cum = 0.0
        selected_pol_name = "Annual"
        for name, weight in policy_weights:
            cum += weight
            if r_pol <= cum:
                selected_pol_name = name
                break
        pol = pol_by_name[selected_pol_name]
        pol_id = pol["policy_id"]

        # Date range generation
        # Seasonality: peak leave in June-August and Nov-Dec
        month_weights = [1, 1, 1, 1, 2, 3, 3, 3, 1, 1, 3, 3]
        total_mw = sum(month_weights)
        r_m = rng.randint(1, total_mw)
        cum_m = 0
        chosen_month = 6
        for m_idx, w in enumerate(month_weights, 1):
            cum_m += w
            if r_m <= cum_m:
                chosen_month = m_idx
                break

        chosen_day = rng.randint(1, 28)
        # Year 2026
        start_date = datetime.date(2026, chosen_month, chosen_day)
        if start_date < hire_date:
            start_date = hire_date + datetime.timedelta(days=rng.randint(15, 60))

        # Duration based on policy
        if selected_pol_name == "Annual":
            # 1 to 15 days, median 3-5 days
            dur_choice = rng.random()
            if dur_choice < 0.60:
                duration_cal_days = rng.randint(1, 4)
            elif dur_choice < 0.90:
                duration_cal_days = rng.randint(5, 10)
            else:
                duration_cal_days = rng.randint(11, 15)
        elif selected_pol_name == "Sick":
            duration_cal_days = rng.choice([1, 1, 2, 2, 3, 4, 5])
        elif selected_pol_name == "Casual":
            duration_cal_days = rng.choice([1, 1, 2, 3])
        elif selected_pol_name == "Parental":
            duration_cal_days = rng.randint(30, 90)
        elif selected_pol_name == "Comp-Off":
            duration_cal_days = rng.choice([1, 2, 3])
        else:  # Unpaid
            duration_cal_days = rng.randint(5, 20)

        end_date = start_date + datetime.timedelta(days=duration_cal_days - 1)

        # Compute calendar and working days metrics
        cal_days, bz_days, wk_days, hol_days = derive_date_metrics(
            calendar_engine, start_date, end_date, country
        )
        if bz_days == 0:
            # If purely on weekend, adjust end_date by 1 weekday
            end_date += datetime.timedelta(days=2)
            cal_days, bz_days, wk_days, hol_days = derive_date_metrics(
                calendar_engine, start_date, end_date, country
            )

        # Submit date: typically before start_date, biased to weekdays
        notice_days = int(pol["min_notice_days"])
        if selected_pol_name == "Sick":
            submit_offset = rng.randint(0, 1)  # same day or day after
        else:
            submit_offset = rng.randint(notice_days, notice_days + 14)

        submit_date = start_date - datetime.timedelta(days=submit_offset)
        if submit_date < hire_date:
            submit_date = hire_date

        reason_code = rng.choice(reasons_by_policy[selected_pol_name])
        comments = f"Requested {selected_pol_name.lower()} leave for {reason_code.lower().replace('_', ' ')}."

        # Evaluate against rules
        current_bal = running_balances.get((emp_id, pol_id), 0.0)

        # Check overlap against previously approved spans
        has_overlap = False
        emp_spans = approved_spans_by_emp.get(emp_id, [])
        for span_start, span_end in emp_spans:
            if not (end_date < span_start or start_date > span_end):
                has_overlap = True
                break

        # Check limits
        is_exceeding_max = bz_days > int(pol["max_consecutive_days"])
        is_insufficient_bal = (bz_days > current_bal) and (selected_pol_name != "Unpaid")

        # Determine decision and lifecycle
        # In baseline, introduce a few clean, natural rejections (e.g. balance, overlap, limit)
        # to satisfy baseline coverage requirements
        if has_overlap:
            decision = "REJECT"
            final_status = "REJECTED"
            rule_id = "LV-002"
            dec_reason_code = "OVERLAPPING_LEAVE_REQUEST"
            dec_reason_text = "Leave request intersects with an existing scheduled leave period."
        elif is_insufficient_bal:
            decision = "REJECT"
            final_status = "REJECTED"
            rule_id = "LV-001"
            dec_reason_code = "INSUFFICIENT_BALANCE"
            dec_reason_text = f"Requested duration ({bz_days} days) exceeds available balance ({current_bal:.2f} days)."
        elif is_exceeding_max:
            decision = "REJECT"
            final_status = "REJECTED"
            rule_id = "LV-003"
            dec_reason_code = "EXCEEDS_MAX_CONSECUTIVE_DAYS"
            dec_reason_text = f"Requested days ({bz_days}) exceeds policy limit ({pol['max_consecutive_days']} days)."
        else:
            decision = "APPROVE"
            final_status = "CONSUMED" if end_date < REFERENCE_DATE else "APPROVED"
            rule_id = "LV-001"
            dec_reason_code = "POLICY_COMPLIANT_APPROVED"
            dec_reason_text = "Request satisfies balance, notice, and policy constraints."

        req_row = {
            "request_id": req_id,
            "employee_id": emp_id,
            "policy_id": pol_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "calendar_days": cal_days,
            "business_days": bz_days,
            "weekend_days_in_span": wk_days,
            "holiday_days_in_span": hol_days,
            "submit_date": submit_date.isoformat(),
            "status": final_status,
            "reason_code": reason_code,
            "comments": comments,
        }
        requests.append(req_row)

        # State transition events:
        # Event 1: DRAFT -> SUBMITTED
        submit_dt = datetime.datetime.combine(submit_date, datetime.time(9, 0, 0))
        events.append({
            "event_id": format_leave_request_event_id(event_idx),
            "request_id": req_id,
            "from_status": "DRAFT",
            "to_status": "SUBMITTED",
            "actor_id": emp_id,
            "timestamp": submit_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": "REQUEST_SUBMITTED",
            "comment": "Initial submission by requester.",
        })
        event_idx += 1

        # Event 2: SUBMITTED -> PENDING_APPROVAL
        routed_dt = submit_dt + datetime.timedelta(minutes=5)
        events.append({
            "event_id": format_leave_request_event_id(event_idx),
            "request_id": req_id,
            "from_status": "SUBMITTED",
            "to_status": "PENDING_APPROVAL",
            "actor_id": "EMP-000001",  # System default actor
            "timestamp": routed_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": "ROUTED_FOR_APPROVAL",
            "comment": "System automated routing to approvers.",
        })
        event_idx += 1

        # Determine approval routing steps
        if bz_days <= 5 and selected_pol_name != "Parental":
            steps_rules = [("ARUL-11", "MANAGER", 1)]
        elif bz_days <= 15 and selected_pol_name != "Parental":
            steps_rules = [("ARUL-12", "MANAGER", 1), ("ARUL-13", "HR", 2)]
        else:
            steps_rules = [("ARUL-14", "MANAGER", 1), ("ARUL-15", "HR", 2), ("ARUL-16", "DIRECTOR", 3)]

        manager_id = emp["manager_id"] or "EMP-000001"
        dir_id = emp_map.get(manager_id, {}).get("manager_id") or manager_id

        # Instantiate approval steps
        step_dt = routed_dt + datetime.timedelta(hours=1)
        for rule_code, role_needed, step_num in steps_rules:
            step_id = format_approval_step_id(req_id, step_num)

            if role_needed == "MANAGER":
                approver_id = manager_id
                approver_lvl = emp_map.get(approver_id, {}).get("job_level", 3)
            elif role_needed == "HR":
                approver_id = rng.choice(hr_approvers)
                approver_lvl = emp_map.get(approver_id, {}).get("job_level", 4)
            else:  # DIRECTOR
                approver_id = dir_id
                approver_lvl = emp_map.get(approver_id, {}).get("job_level", 4)

            step_status = "APPROVED" if decision == "APPROVE" else "REJECTED"
            step_decision = "APPROVE" if decision == "APPROVE" else "REJECT"

            approval_steps.append({
                "step_id": step_id,
                "request_id": req_id,
                "step_number": step_num,
                "rule_id": rule_code,
                "approver_id": approver_id,
                "level": approver_lvl,
                "due_date": (submit_date + datetime.timedelta(days=3)).isoformat(),
                "status": step_status,
                "decided_at": step_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "decision": step_decision,
                "reason_code": dec_reason_code,
                "comment": f"Step {step_num} review: {dec_reason_text}",
            })
            step_dt += datetime.timedelta(hours=2)

        # Transition Event 3: PENDING_APPROVAL -> APPROVED or REJECTED
        last_approver = approval_steps[-1]["approver_id"]
        last_ts = approval_steps[-1]["decided_at"]
        final_decision_dt = step_dt
        events.append({
            "event_id": format_leave_request_event_id(event_idx),
            "request_id": req_id,
            "from_status": "PENDING_APPROVAL",
            "to_status": "APPROVED" if decision == "APPROVE" else "REJECTED",
            "actor_id": last_approver,
            "timestamp": final_decision_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": dec_reason_code,
            "comment": dec_reason_text,
        })
        event_idx += 1

        # If approved and in past, add APPROVED -> CONSUMED
        if decision == "APPROVE":
            # Record USAGE in ledger!
            usage_date = start_date if start_date <= REFERENCE_DATE else submit_date
            ledger_entries.append({
                "ledger_id": format_leave_ledger_id(ledger_idx),
                "employee_id": emp_id,
                "policy_id": pol_id,
                "entry_type": "USAGE",
                "days": -round(float(bz_days), 2),
                "effective_date": usage_date.isoformat(),
                "reference_id": req_id,
                "created_at": last_ts,
                "notes": f"Consumption for leave request {req_id}",
            })
            ledger_idx += 1
            running_balances[(emp_id, pol_id)] = current_bal - bz_days
            approved_spans_by_emp.setdefault(emp_id, []).append((start_date, end_date))

            if final_status == "CONSUMED":
                consumed_dt = datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
                if consumed_dt <= final_decision_dt:
                    consumed_dt = final_decision_dt + datetime.timedelta(days=1)
                events.append({
                    "event_id": format_leave_request_event_id(event_idx),
                    "request_id": req_id,
                    "from_status": "APPROVED",
                    "to_status": "CONSUMED",
                    "actor_id": "EMP-000001",
                    "timestamp": consumed_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "reason_code": "LEAVE_PERIOD_COMPLETED",
                    "comment": "Automated system update: leave interval concluded.",
                })
                event_idx += 1

        # Decision Log Entry
        decision_logs.append({
            "decision_id": format_decision_id(dec_idx),
            "subject_id": req_id,
            "decision": decision,
            "reason_code": dec_reason_code,
            "reason_text": dec_reason_text,
            "rule_id": rule_id,
            "inputs_snapshot_json": json.dumps({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "business_days": bz_days,
                "available_balance": current_bal,
                "notice_days": submit_offset,
                "policy_cap": pol["annual_cap"],
            }),
            "timestamp": last_ts,
        })
        dec_idx += 1

    # Sort all arrays deterministically
    requests.sort(key=lambda r: r["request_id"])
    events.sort(key=lambda e: (e["request_id"], e["timestamp"], e["event_id"]))
    approval_steps.sort(key=lambda s: (s["request_id"], s["step_number"], s["step_id"]))
    decision_logs.sort(key=lambda d: d["decision_id"])
    ledger_entries.sort(key=lambda l: (l["employee_id"], l["effective_date"], l["ledger_id"]))

    # Derive finalized LeaveBalances from full ledger
    derived_balances = derive_leave_balances(
        employees, leave_policies, ledger_entries, requests, REFERENCE_DATE_STR
    )

    return LeaveBundle(
        ledger_entries=ledger_entries,
        balances=derived_balances,
        requests=requests,
        events=events,
        approval_steps=approval_steps,
        decision_logs=decision_logs,
    )
