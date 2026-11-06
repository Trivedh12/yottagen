"""Expense management and reimbursement engine for YottaGen.

Generates:
- ExpenseClaims with 1-10 lines (realistic log-normal skew)
- Local currency and base currency conversions with fixed rates
- Embedded cryptographic receipt metadata (receipt_id, SHA-256 hash, filename)
- Rule-based routing and ApprovalStep generation
- Append-only lifecycle events (ExpenseClaimEvent)
- DecisionLog audit records
- Eligible Reimbursements strictly derived from approved claims
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from yottagen.config import (
    BASE_CURRENCY,
    COUNTRY_CURRENCY,
    EXCHANGE_RATES_TO_USD,
    EXPENSE_CATEGORIES,
    REFERENCE_DATE,
    REFERENCE_DATE_STR,
    ScaleConfig,
)
from yottagen.derive import derive_expense_claim_totals, derive_reimbursement_amount
from yottagen.ids import (
    format_approval_step_id,
    format_decision_id,
    format_expense_claim_event_id,
    format_expense_claim_id,
    format_expense_line_id,
    format_receipt_id,
    format_reimbursement_id,
    format_transaction_ref,
)
from yottagen.routing import resolve_expense_approval_path


@dataclass
class ExpenseBundle:
    claims: List[Dict[str, Any]]
    lines: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    approval_steps: List[Dict[str, Any]]
    reimbursements: List[Dict[str, Any]]
    decision_logs: List[Dict[str, Any]]


MERCHANTS_BY_CATEGORY = {
    "TRAVEL": ["Delta Air Lines", "United Airlines", "Lufthansa", "British Airways", "Air India", "Singapore Airlines", "Uber Corp", "Amtrak"],
    "LODGING": ["Marriott International", "Hilton Hotels", "Hyatt Regency", "Taj Hotels", "Premier Inn", "Mercure Hotels"],
    "MEALS": ["Pret A Manger", "Starbucks Coffee", "The Capital Grille", "Olive Garden", "Saravanaa Bhavan", "Bavarian Bistro"],
    "CLIENT_ENTERTAINMENT": ["Ocean Prime", "The Grill Steakhouse", "Morton's The Steakhouse", "Bukhara", "Zuma London"],
    "SOFTWARE": ["JetBrains", "GitHub Enterprise", "Amazon Web Services", "Atlassian Cloud", "Datadog", "Slack Technologies"],
    "EQUIPMENT": ["Apple Store", "Dell Direct", "Lenovo Enterprise", "CDW Corporation", "Logitech Direct"],
    "TRAINING": ["O'Reilly Media", "Coursera Enterprise", "Linux Foundation", "AWS Training & Certification", "Gartner Events"],
    "MISC": ["Office Depot", "Staples Business", "FedEx Office", "DHL Express"],
}

PURPOSES = [
    "Q1 Strategic Enterprise Sales Outreach",
    "Global Engineering Hackathon and Architecture Review",
    "Key Customer Executive Steering Committee",
    "Cloud Infrastructure Scaling and Security Audit",
    "Technical Training and Professional Certification",
    "Regional Operations and Site Reliability Workshop",
    "Product Roadmap Planning and User Research",
    "Supplier Partnership and Vendor QBR",
]


def generate_expense_module(
    scale_config: ScaleConfig,
    employees: List[Dict[str, Any]],
    expense_policies: List[Dict[str, Any]],
    approval_rules: List[Dict[str, Any]],
    rng: random.Random,
    start_dec_idx: int = 1000,
) -> ExpenseBundle:
    """Generate expense claims, line items, receipt hashes, approval workflows, and reimbursements."""
    num_claims = scale_config.num_expense_claims
    policy = expense_policies[0]
    policy_id = policy["policy_id"]

    emp_map = {e["employee_id"]: e for e in employees}
    finance_approvers = [
        e["employee_id"]
        for e in employees
        if e.get("is_finance_approver") and e.get("status") == "ACTIVE"
    ]
    if not finance_approvers:
        finance_approvers = [e["employee_id"] for e in employees if e["job_level"] >= 4]

    claims: List[Dict[str, Any]] = []
    lines: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    approval_steps: List[Dict[str, Any]] = []
    reimbursements: List[Dict[str, Any]] = []
    decision_logs: List[Dict[str, Any]] = []

    claim_idx = 1
    event_idx = 1
    rcp_idx = 1
    rmb_idx = 1
    dec_idx = start_dec_idx

    # Seen receipt hashes for duplicate tracking
    seen_receipt_hashes: Set[str] = set()

    for _ in range(num_claims):
        claim_id = format_expense_claim_id(claim_idx)
        claim_idx += 1

        # Select claimant
        candidate_emps = [e for e in employees if e["status"] in ("ACTIVE", "ON_LEAVE")]
        emp = rng.choice(candidate_emps)
        emp_id = emp["employee_id"]
        country = emp["country"]
        currency = COUNTRY_CURRENCY[country]
        rate_to_base = EXCHANGE_RATES_TO_USD[currency]
        hire_date = datetime.date.fromisoformat(emp["hire_date"])

        # Determine number of lines (realistic distribution: 1-10, median ~2-3)
        r_lines = rng.random()
        if r_lines < 0.50:
            num_lines = rng.choice([1, 2])
        elif r_lines < 0.85:
            num_lines = rng.choice([3, 4, 5])
        else:
            num_lines = rng.randint(6, 10)

        # Dates: spread over 2026 up to as_of_date
        month = rng.randint(1, 10)
        day = rng.randint(1, 28)
        claim_date = datetime.date(2026, month, day)
        if claim_date < hire_date:
            claim_date = hire_date + datetime.timedelta(days=rng.randint(10, 45))
        if claim_date > REFERENCE_DATE:
            claim_date = REFERENCE_DATE - datetime.timedelta(days=rng.randint(5, 30))

        # Submit date is same day or 1-3 days after claim assembly
        submit_date = claim_date + datetime.timedelta(days=rng.randint(0, 3))
        if submit_date > REFERENCE_DATE:
            submit_date = REFERENCE_DATE

        purpose = rng.choice(PURPOSES)
        claim_lines: List[Dict[str, Any]] = []

        # Generate each line item
        for line_no in range(1, num_lines + 1):
            line_id = format_expense_line_id(claim_id, line_no)
            cat = rng.choice(EXPENSE_CATEGORIES)
            merchant = rng.choice(MERCHANTS_BY_CATEGORY[cat])

            # Expense date within 7 days prior to claim date
            exp_date = claim_date - datetime.timedelta(days=rng.randint(0, 6))
            if exp_date < hire_date:
                exp_date = hire_date

            # Log-normal realistic pricing in USD base, then converted to local currency
            # Include boundary conditions occasionally (exactly $100, $150, $180, $250, $1000, $5000)
            boundary_r = rng.random()
            if boundary_r < 0.02:
                amount_base = 100.00
            elif boundary_r < 0.04:
                amount_base = 150.00
            elif boundary_r < 0.06:
                amount_base = 180.00
            elif boundary_r < 0.08:
                amount_base = 250.00
            elif boundary_r < 0.09:
                amount_base = 1000.00
            elif boundary_r < 0.10:
                amount_base = 5000.00
            else:
                if cat == "MEALS":
                    amount_base = round(math.exp(rng.gauss(3.3, 0.4)), 2)  # ~$27
                elif cat == "LODGING":
                    amount_base = round(math.exp(rng.gauss(5.1, 0.3)), 2)  # ~$164
                elif cat == "TRAVEL":
                    amount_base = round(math.exp(rng.gauss(5.8, 0.5)), 2)  # ~$330
                elif cat == "EQUIPMENT":
                    amount_base = round(math.exp(rng.gauss(5.5, 0.6)), 2)  # ~$245
                elif cat == "CLIENT_ENTERTAINMENT":
                    amount_base = round(math.exp(rng.gauss(4.8, 0.5)), 2)  # ~$120
                elif cat == "SOFTWARE":
                    amount_base = round(math.exp(rng.gauss(4.4, 0.5)), 2)  # ~$81
                elif cat == "TRAINING":
                    amount_base = round(math.exp(rng.gauss(6.0, 0.4)), 2)  # ~$400
                else:
                    amount_base = round(math.exp(rng.gauss(3.8, 0.5)), 2)  # ~$45

            amount_base = max(5.00, round(amount_base, 2))
            amount_local = round(amount_base / rate_to_base, 2)
            # Re-reconcile amount_base exactly
            amount_base = round(amount_local * rate_to_base, 2)

            # Receipt metadata
            # Baseline: ~97% have receipts, ~3% miss receipts to test rule EX-001
            has_receipt = 1
            if amount_base > 25.0 and rng.random() < 0.03:
                has_receipt = 0

            if has_receipt:
                rcp_id = format_receipt_id(rcp_idx)
                rcp_idx += 1
                raw_hash_seed = f"RECEIPT_{claim_id}_{line_no}_{merchant}_{amount_local}_{exp_date.isoformat()}"
                receipt_hash = hashlib.sha256(raw_hash_seed.encode("utf-8")).hexdigest()
                receipt_date = exp_date.isoformat()
                file_name = f"receipt_{claim_id}_{line_no:02d}.pdf"
            else:
                rcp_id = ""
                receipt_hash = ""
                receipt_date = ""
                file_name = ""

            line_rec = {
                "line_id": line_id,
                "claim_id": claim_id,
                "line_number": line_no,
                "expense_date": exp_date.isoformat(),
                "category": cat,
                "description": f"{cat.title()} expense with {merchant}",
                "amount_local": amount_local,
                "currency": currency,
                "exchange_rate_to_base": rate_to_base,
                "amount_base": amount_base,
                "merchant_name": merchant,
                "receipt_id": rcp_id,
                "receipt_hash": receipt_hash,
                "receipt_date": receipt_date,
                "has_receipt": has_receipt,
                "file_name": file_name,
                "is_disallowed": 0,
            }
            claim_lines.append(line_rec)
            lines.append(line_rec)

        # Derive claim totals
        tot_local, tot_base, line_count = derive_expense_claim_totals(claim_lines)

        # Evaluate against rules
        # Rule EX-001: Receipt required above threshold $25
        missing_receipt = any(
            float(l["amount_base"]) > float(policy["receipt_required_threshold"])
            and not int(l["has_receipt"])
            for l in claim_lines
        )
        # Rule EX-003: Policy limit breach > $10,000
        exceeds_max_cap = tot_base > float(policy["max_claim_amount"])

        if missing_receipt:
            decision = "REJECT"
            final_status = "REJECTED"
            rule_id = "EX-001"
            dec_reason_code = "RECEIPT_MANDATORY_BREACH"
            dec_reason_text = "Claim contains line items exceeding threshold without valid receipt substantiation."
        elif exceeds_max_cap:
            decision = "REJECT"
            final_status = "REJECTED"
            rule_id = "EX-003"
            dec_reason_code = "EXCEEDS_POLICY_MAX_CLAIM"
            dec_reason_text = f"Claim total (${tot_base:.2f}) exceeds maximum allowed ceiling (${policy['max_claim_amount']:.2f})."
        else:
            decision = "APPROVE"
            final_status = "REIMBURSED"  # Concludes into reimbursement
            rule_id = "AP-001"
            dec_reason_code = "POLICY_COMPLIANT_APPROVED"
            dec_reason_text = "Claim adheres to expense policy guidelines and receipts verified."

        claim_rec = {
            "claim_id": claim_id,
            "employee_id": emp_id,
            "cost_center_id": emp["cost_center_id"],
            "policy_id": policy_id,
            "claim_date": claim_date.isoformat(),
            "submit_date": submit_date.isoformat(),
            "purpose": purpose,
            "currency": currency,
            "total_amount_local": tot_local,
            "total_amount_base": tot_base,
            "status": final_status,
            "line_count": line_count,
        }
        claims.append(claim_rec)

        # Generate Lifecycle Events
        submit_dt = datetime.datetime.combine(submit_date, datetime.time(10, 0, 0))
        events.append({
            "event_id": format_expense_claim_event_id(event_idx),
            "claim_id": claim_id,
            "from_status": "DRAFT",
            "to_status": "SUBMITTED",
            "actor_id": emp_id,
            "timestamp": submit_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": "CLAIM_SUBMITTED",
            "comment": "Claim submitted with itemized receipts.",
        })
        event_idx += 1

        routed_dt = submit_dt + datetime.timedelta(minutes=5)
        events.append({
            "event_id": format_expense_claim_event_id(event_idx),
            "claim_id": claim_id,
            "from_status": "SUBMITTED",
            "to_status": "PENDING_APPROVAL",
            "actor_id": "EMP-000001",
            "timestamp": routed_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": "ROUTED_FOR_APPROVAL",
            "comment": "Automated workflow engine assigned approval authority path.",
        })
        event_idx += 1

        # Resolve Approval Steps using routing engine
        resolved_steps = resolve_expense_approval_path(
            claim_rec, claim_lines, emp, emp_map, finance_approvers
        )

        step_dt = routed_dt + datetime.timedelta(hours=2)
        for s in resolved_steps:
            step_id = format_approval_step_id(claim_id, s.step_number)
            step_status = "APPROVED" if decision == "APPROVE" else "REJECTED"
            step_decision = "APPROVE" if decision == "APPROVE" else "REJECT"

            approval_steps.append({
                "step_id": step_id,
                "request_id": claim_id,
                "step_number": s.step_number,
                "rule_id": s.rule_id,
                "approver_id": s.approver_id,
                "level": s.approver_level,
                "due_date": (submit_date + datetime.timedelta(days=s.due_days)).isoformat(),
                "status": step_status,
                "decided_at": step_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "decision": step_decision,
                "reason_code": dec_reason_code,
                "comment": f"{s.description} Verdict: {step_decision}.",
            })
            step_dt += datetime.timedelta(hours=4)

        # PENDING_APPROVAL -> APPROVED or REJECTED
        last_step = approval_steps[-1]
        decision_dt = step_dt
        events.append({
            "event_id": format_expense_claim_event_id(event_idx),
            "claim_id": claim_id,
            "from_status": "PENDING_APPROVAL",
            "to_status": "APPROVED" if decision == "APPROVE" else "REJECTED",
            "actor_id": last_step["approver_id"],
            "timestamp": decision_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason_code": dec_reason_code,
            "comment": dec_reason_text,
        })
        event_idx += 1

        # Decision Log
        decision_logs.append({
            "decision_id": format_decision_id(dec_idx),
            "subject_id": claim_id,
            "decision": decision,
            "reason_code": dec_reason_code,
            "reason_text": dec_reason_text,
            "rule_id": rule_id,
            "inputs_snapshot_json": json.dumps({
                "total_amount_local": tot_local,
                "total_amount_base": tot_base,
                "currency": currency,
                "line_count": line_count,
                "has_missing_receipt": missing_receipt,
                "approver_depth": len(resolved_steps),
            }),
            "timestamp": decision_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        dec_idx += 1

        # If APPROVED: create Reimbursement and transition to REIMBURSED
        if decision == "APPROVE":
            reimb_amount = derive_reimbursement_amount(claim_lines)
            pay_days_offset = rng.randint(3, 7)
            pay_date = submit_date + datetime.timedelta(days=pay_days_offset)
            pay_dt = datetime.datetime.combine(pay_date, datetime.time(16, 0, 0))
            if pay_dt <= decision_dt:
                pay_dt = decision_dt + datetime.timedelta(days=2)
                pay_date = pay_dt.date()

            rmb_rec = {
                "reimbursement_id": format_reimbursement_id(rmb_idx),
                "claim_id": claim_id,
                "employee_id": emp_id,
                "payment_method": "DIRECT_DEPOSIT",
                "currency": currency,
                "amount": reimb_amount,
                "payment_date": pay_date.isoformat(),
                "transaction_reference": format_transaction_ref(rmb_idx),
                "status": "PROCESSED",
            }
            reimbursements.append(rmb_rec)
            rmb_idx += 1

            # Event: APPROVED -> REIMBURSED
            events.append({
                "event_id": format_expense_claim_event_id(event_idx),
                "claim_id": claim_id,
                "from_status": "APPROVED",
                "to_status": "REIMBURSED",
                "actor_id": finance_approvers[0],
                "timestamp": pay_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "reason_code": "REIMBURSEMENT_PROCESSED",
                "comment": f"Payment executed via Direct Deposit. Ref: {rmb_rec['transaction_reference']}",
            })
            event_idx += 1

    # Deterministic sorting
    claims.sort(key=lambda c: c["claim_id"])
    lines.sort(key=lambda l: (l["claim_id"], l["line_number"]))
    events.sort(key=lambda e: (e["claim_id"], e["timestamp"], e["event_id"]))
    approval_steps.sort(key=lambda s: (s["request_id"], s["step_number"], s["step_id"]))
    reimbursements.sort(key=lambda r: r["reimbursement_id"])
    decision_logs.sort(key=lambda d: d["decision_id"])

    return ExpenseBundle(
        claims=claims,
        lines=lines,
        events=events,
        approval_steps=approval_steps,
        reimbursements=reimbursements,
        decision_logs=decision_logs,
    )
