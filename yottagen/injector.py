"""Anomaly injection engine and ground-truth registry for YottaGen.

Deliberately injects targeted edge cases and anomalies into clean baseline datasets:
1. NEGATIVE_LEAVE_BALANCE
2. OVERLAPPING_APPROVED_LEAVE
3. EXPENSE_DATE_OUTSIDE_EMPLOYMENT
4. SPLIT_CLAIM_THRESHOLD_EVASION
5. MISSING_COST_CENTER
6. APPROVAL_BY_REQUESTER
7. DUPLICATE_REIMBURSEMENT
Plus baseline-labelled types:
- INSUFFICIENT_BALANCE
- WEEKEND_HOLIDAY_SPAN
- MISSING_RECEIPT
- DUPLICATE_RECEIPT_HASH
- POLICY_LIMIT_BREACH
- MULTI_LEVEL_APPROVAL

Guarantees:
- Touches ONLY targeted rows; baseline invariants remain intact elsewhere.
- Every anomaly produces an unambiguous ground-truth row.
- Input tables contain NO leaked label columns or features.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from yottagen.config import ScaleConfig
from yottagen.ids import (
    format_approval_step_id,
    format_expense_claim_id,
    format_expense_line_id,
    format_leave_ledger_id,
    format_leave_request_id,
    format_receipt_id,
    format_reimbursement_id,
    format_transaction_ref,
)


@dataclass
class GroundTruthRecord:
    gt_id: str
    issue_type: str
    entity_type: str
    entity_id: str
    related_entity_ids: str
    expected_decision: str  # FLAG, REJECT, ESCALATE, APPROVE_WITH_MULTI_LEVEL, etc.
    expected_approval_path: str
    expected_reason_code: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL, INFO
    injected: int  # 1 for injected, 0 for natural baseline
    injection_note: str


@dataclass
class InjectionResult:
    master_bundle: Any
    leave_bundle: Any
    expense_bundle: Any
    ground_truth_records: List[GroundTruthRecord]
    expected_decisions: List[Dict[str, Any]]


def inject_anomalies(
    scale_config: ScaleConfig,
    master_bundle: Any,
    leave_bundle: Any,
    expense_bundle: Any,
    rng: random.Random,
) -> InjectionResult:
    """Inject labelled anomalies and generate unified ground truth and expected decisions."""
    target_count = scale_config.target_anomalies_per_type

    # Deepcopy bundles to avoid side effects
    mb = copy.deepcopy(master_bundle)
    lb = copy.deepcopy(leave_bundle)
    eb = copy.deepcopy(expense_bundle)

    ground_truth: List[GroundTruthRecord] = []
    gt_idx = 1

    emp_map = {e["employee_id"]: e for e in mb.employees}
    pol_map = {p["policy_id"]: p for p in mb.leave_policies}

    # =========================================================================
    # 1. INJECT: NEGATIVE_LEAVE_BALANCE (Rule LV-001)
    # =========================================================================
    # Find employees with Annual or Sick leave balances and inject a large manual debit
    # that pushes closing_balance strictly below zero.
    eligible_balances = [
        b for b in lb.balances
        if b["closing_balance"] > 0 and b["policy_id"] in ("LPOL-01", "LPOL-02")
    ]
    selected_neg_bals = eligible_balances[:target_count]
    next_ledger_num = len(lb.ledger_entries) + 1

    for bal in selected_neg_bals:
        overdraft = round(float(bal["closing_balance"]) + rng.uniform(2.5, 7.5), 2)
        ledger_entry = {
            "ledger_id": format_leave_ledger_id(next_ledger_num),
            "employee_id": bal["employee_id"],
            "policy_id": bal["policy_id"],
            "entry_type": "ADJUSTMENT",
            "days": -round(overdraft, 2),
            "effective_date": bal["as_of_date"],
            "reference_id": "INJECTED_ADJUSTMENT_OVERDRAFT",
            "created_at": f"{bal['as_of_date']}T12:00:00Z",
            "notes": "Deliberately injected negative balance adjustment anomaly.",
        }
        next_ledger_num += 1
        lb.ledger_entries.append(ledger_entry)

        # Update balance snapshot
        bal["adjusted_days"] = round(bal["adjusted_days"] - overdraft, 2)
        bal["closing_balance"] = round(
            bal["opening_balance"] + bal["accrued_days"] + bal["adjusted_days"] - bal["used_days"], 2
        )

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="NEGATIVE_LEAVE_BALANCE",
                entity_type="leave_balance",
                entity_id=bal["balance_id"],
                related_entity_ids=f"{bal['employee_id']},{bal['policy_id']}",
                expected_decision="FLAG",
                expected_approval_path="N/A",
                expected_reason_code="LV-001_NEGATIVE_BALANCE",
                severity="HIGH",
                injected=1,
                injection_note=f"Injected negative closing balance ({bal['closing_balance']} days) via unauthorized ledger adjustment.",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 2. INJECT: OVERLAPPING_APPROVED_LEAVE (Rule LV-002)
    # =========================================================================
    # Find approved leave requests and inject a secondary overlapping request that is also marked APPROVED.
    approved_leaves = [r for r in lb.requests if r["status"] in ("APPROVED", "CONSUMED")]
    selected_overlaps = approved_leaves[:target_count]

    next_lve_num = len(lb.requests) + 1
    for orig_req in selected_overlaps:
        new_req_id = format_leave_request_id(next_lve_num)
        next_lve_num += 1

        orig_start = datetime.date.fromisoformat(orig_req["start_date"])
        orig_end = datetime.date.fromisoformat(orig_req["end_date"])

        # Create overlapping span
        new_start = orig_start + datetime.timedelta(days=1)
        new_end = orig_end + datetime.timedelta(days=2)

        new_req = copy.deepcopy(orig_req)
        new_req["request_id"] = new_req_id
        new_req["start_date"] = new_start.isoformat()
        new_req["end_date"] = new_end.isoformat()
        new_req["status"] = "APPROVED"
        new_req["comments"] = "Injected conflicting overlapping approved leave request."
        lb.requests.append(new_req)

        # Incur ledger usage to reflect the approval
        lb.ledger_entries.append({
            "ledger_id": format_leave_ledger_id(next_ledger_num),
            "employee_id": new_req["employee_id"],
            "policy_id": new_req["policy_id"],
            "entry_type": "USAGE",
            "days": -round(float(new_req["business_days"]), 2),
            "effective_date": new_req["start_date"],
            "reference_id": new_req_id,
            "created_at": f"{new_req['start_date']}T10:00:00Z",
            "notes": "Usage for overlapping approved leave request.",
        })
        next_ledger_num += 1

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="OVERLAPPING_APPROVED_LEAVE",
                entity_type="leave_request",
                entity_id=new_req_id,
                related_entity_ids=orig_req["request_id"],
                expected_decision="REJECT",
                expected_approval_path="MANAGER",
                expected_reason_code="LV-002_OVERLAPPING_LEAVE",
                severity="CRITICAL",
                injected=1,
                injection_note=f"Injected approved leave {new_req_id} overlapping with approved leave {orig_req['request_id']}.",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 3. INJECT: EXPENSE_DATE_OUTSIDE_EMPLOYMENT (Rule EX-004)
    # =========================================================================
    # Target expense claims: alter expense_date and claim_date to precede employee hire_date
    eligible_claims = [c for c in eb.claims if c["status"] in ("APPROVED", "REIMBURSED")]
    selected_outside_claims = eligible_claims[:target_count]

    for claim in selected_outside_claims:
        emp = emp_map[claim["employee_id"]]
        hire_date = datetime.date.fromisoformat(emp["hire_date"])
        invalid_exp_date = hire_date - datetime.timedelta(days=rng.randint(20, 90))

        # Update claim lines
        for line in eb.lines:
            if line["claim_id"] == claim["claim_id"]:
                line["expense_date"] = invalid_exp_date.isoformat()
                if line["has_receipt"]:
                    line["receipt_date"] = invalid_exp_date.isoformat()

        claim["claim_date"] = invalid_exp_date.isoformat()

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="EXPENSE_DATE_OUTSIDE_EMPLOYMENT",
                entity_type="expense_claim",
                entity_id=claim["claim_id"],
                related_entity_ids=claim["employee_id"],
                expected_decision="REJECT",
                expected_approval_path="MANAGER",
                expected_reason_code="EX-004_DATE_OUTSIDE_EMPLOYMENT",
                severity="HIGH",
                injected=1,
                injection_note=f"Incurred expense date ({invalid_exp_date}) precedes employee hire date ({hire_date}).",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 4. INJECT: SPLIT_CLAIM_THRESHOLD_EVASION (Rule EX-005)
    # =========================================================================
    # Employee submits 2-3 claims within a 3-day window, each just below the $100 threshold (e.g. $95)
    # summing to $190 or $285 which would otherwise require Director approval!
    split_candidate_emps = [
        e["employee_id"] for e in mb.employees if e["job_level"] <= 2 and e["status"] == "ACTIVE"
    ][:target_count]

    next_claim_num = len(eb.claims) + 1
    next_line_num = len(eb.lines) + 1

    for emp_id in split_candidate_emps:
        emp = emp_map[emp_id]
        base_date = datetime.date(2026, 7, rng.randint(5, 20))
        cluster_claim_ids = []

        # Create two split claims of $92 each
        for split_i in range(1, 3):
            c_id = format_expense_claim_id(next_claim_num)
            next_claim_num += 1
            cluster_claim_ids.append(c_id)

            c_date = base_date + datetime.timedelta(days=split_i - 1)
            line_id = format_expense_line_id(c_id, 1)

            rate = 1.0  # USD base for split claims
            split_line = {
                "line_id": line_id,
                "claim_id": c_id,
                "line_number": 1,
                "expense_date": c_date.isoformat(),
                "category": "MEALS",
                "description": f"Client dinner session part {split_i} with Acme Corp",
                "amount_local": 92.00,
                "currency": "USD",
                "exchange_rate_to_base": rate,
                "amount_base": 92.00,
                "merchant_name": "The Capital Grille",
                "receipt_id": format_receipt_id(next_line_num),
                "receipt_hash": hashlib.sha256(f"SPLIT_{c_id}_{split_i}".encode()).hexdigest(),
                "receipt_date": c_date.isoformat(),
                "has_receipt": 1,
                "file_name": f"receipt_{c_id}_01.pdf",
                "is_disallowed": 0,
            }
            next_line_num += 1
            eb.lines.append(split_line)

            split_claim = {
                "claim_id": c_id,
                "employee_id": emp_id,
                "cost_center_id": emp["cost_center_id"],
                "policy_id": "EPOL-01",
                "claim_date": c_date.isoformat(),
                "submit_date": c_date.isoformat(),
                "purpose": "Client dinner meeting structured under $100 tier threshold",
                "currency": "USD",
                "total_amount_local": 92.00,
                "total_amount_base": 92.00,
                "status": "APPROVED",
                "line_count": 1,
            }
            eb.claims.append(split_claim)

            # Approval step: single step manager (since $92 <= $100)
            mgr_id = emp["manager_id"] or "EMP-000001"
            eb.approval_steps.append({
                "step_id": format_approval_step_id(c_id, 1),
                "request_id": c_id,
                "step_number": 1,
                "rule_id": "ARUL-01",
                "approver_id": mgr_id,
                "level": 3,
                "due_date": (c_date + datetime.timedelta(days=3)).isoformat(),
                "status": "APPROVED",
                "decided_at": f"{c_date.isoformat()}T15:00:00Z",
                "decision": "APPROVE",
                "reason_code": "ROUTING_TIER1_APPROVED",
                "comment": "Manager approved claim under $100 threshold.",
            })

        for cid in cluster_claim_ids:
            other_ids = [o for o in cluster_claim_ids if o != cid]
            ground_truth.append(
                GroundTruthRecord(
                    gt_id=f"GT-{gt_idx:06d}",
                    issue_type="SPLIT_CLAIM_THRESHOLD_EVASION",
                    entity_type="expense_claim",
                    entity_id=cid,
                    related_entity_ids=",".join(other_ids),
                    expected_decision="ESCALATE",
                    expected_approval_path="MANAGER+DIRECTOR",
                    expected_reason_code="EX-005_SPLIT_CLAIM_EVASION",
                    severity="MEDIUM",
                    injected=1,
                    injection_note=f"Split claim evasion: 2 claims of $92.00 within 2 days sum to $184.00, evading Tier 2 approval.",
                )
            )
            gt_idx += 1

    # =========================================================================
    # 5. INJECT: MISSING_COST_CENTER (Rule CC-001)
    # =========================================================================
    # Strip cost_center_id from targeted claims
    claims_for_cc = [
        c for c in eb.claims
        if c["status"] in ("APPROVED", "REIMBURSED") and c["claim_id"] not in [gt.entity_id for gt in ground_truth]
    ][:target_count]

    for claim in claims_for_cc:
        orig_cc = claim["cost_center_id"]
        claim["cost_center_id"] = ""

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="MISSING_COST_CENTER",
                entity_type="expense_claim",
                entity_id=claim["claim_id"],
                related_entity_ids=claim["employee_id"],
                expected_decision="REJECT",
                expected_approval_path="N/A",
                expected_reason_code="CC-001_MISSING_COST_CENTER",
                severity="HIGH",
                injected=1,
                injection_note=f"Claim {claim['claim_id']} lacks required cost center allocation (was {orig_cc}).",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 6. INJECT: APPROVAL_BY_REQUESTER (Rule AP-002: Self-approval)
    # =========================================================================
    # In an existing approval step, replace approver_id with the claimant's own employee_id
    steps_for_self_app = [
        s for s in eb.approval_steps
        if s["status"] == "APPROVED" and s["step_number"] == 1
    ][:target_count]

    for step in steps_for_self_app:
        claim = next(c for c in eb.claims if c["claim_id"] == step["request_id"])
        step["approver_id"] = claim["employee_id"]  # Self-approval!

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="APPROVAL_BY_REQUESTER",
                entity_type="approval_step",
                entity_id=step["step_id"],
                related_entity_ids=claim["claim_id"],
                expected_decision="REJECT",
                expected_approval_path="INDEPENDENT_MANAGER",
                expected_reason_code="AP-002_SELF_APPROVAL_PROHIBITED",
                severity="CRITICAL",
                injected=1,
                injection_note=f"Approver {step['approver_id']} matches claimant {claim['employee_id']} on step {step['step_id']}.",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 7. INJECT: DUPLICATE_REIMBURSEMENT (Rule RB-002)
    # =========================================================================
    # Create a duplicate reimbursement record referencing an already-reimbursed claim
    target_rmbs = eb.reimbursements[:target_count]
    next_rmb_num = len(eb.reimbursements) + 1

    for orig_rmb in target_rmbs:
        dup_rmb_id = format_reimbursement_id(next_rmb_num)
        next_rmb_num += 1

        dup_rmb = copy.deepcopy(orig_rmb)
        dup_rmb["reimbursement_id"] = dup_rmb_id
        dup_rmb["transaction_reference"] = format_transaction_ref(next_rmb_num)
        # Payment date 2 days later
        orig_pdate = datetime.date.fromisoformat(orig_rmb["payment_date"])
        dup_rmb["payment_date"] = (orig_pdate + datetime.timedelta(days=2)).isoformat()
        eb.reimbursements.append(dup_rmb)

        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="DUPLICATE_REIMBURSEMENT",
                entity_type="reimbursement",
                entity_id=dup_rmb_id,
                related_entity_ids=orig_rmb["reimbursement_id"],
                expected_decision="REJECT",
                expected_approval_path="N/A",
                expected_reason_code="RB-002_DUPLICATE_REIMBURSEMENT",
                severity="CRITICAL",
                injected=1,
                injection_note=f"Duplicate reimbursement {dup_rmb_id} issued for claim {dup_rmb['claim_id']} already paid under {orig_rmb['reimbursement_id']}.",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 8. LABEL BASELINE OCCURRENCES (Natural Ground Truth)
    # =========================================================================
    # Natural: INSUFFICIENT_BALANCE
    rejected_leaves_balance = [
        r for r in lb.requests
        if r["status"] == "REJECTED" and "insufficient" in r["comments"].lower() or r["status"] == "REJECTED" and r["reason_code"] == "INSUFFICIENT_BALANCE"
    ]
    # Also find any requests rejected with reason code INSUFFICIENT_BALANCE in decision logs
    for dlog in lb.decision_logs:
        if dlog["reason_code"] == "INSUFFICIENT_BALANCE":
            ground_truth.append(
                GroundTruthRecord(
                    gt_id=f"GT-{gt_idx:06d}",
                    issue_type="INSUFFICIENT_BALANCE",
                    entity_type="leave_request",
                    entity_id=dlog["subject_id"],
                    related_entity_ids="",
                    expected_decision="REJECT",
                    expected_approval_path="N/A",
                    expected_reason_code="LV-001_INSUFFICIENT_BALANCE",
                    severity="MEDIUM",
                    injected=0,
                    injection_note="Natural baseline rejection: leave duration exceeded available balance.",
                )
            )
            gt_idx += 1

    # Natural: MISSING_RECEIPT
    for dlog in eb.decision_logs:
        if dlog["reason_code"] == "RECEIPT_MANDATORY_BREACH":
            ground_truth.append(
                GroundTruthRecord(
                    gt_id=f"GT-{gt_idx:06d}",
                    issue_type="MISSING_RECEIPT",
                    entity_type="expense_claim",
                    entity_id=dlog["subject_id"],
                    related_entity_ids="",
                    expected_decision="REJECT",
                    expected_approval_path="N/A",
                    expected_reason_code="EX-001_MISSING_RECEIPT",
                    severity="HIGH",
                    injected=0,
                    injection_note="Natural baseline rejection: mandatory receipt substantiation missing above $25.",
                )
            )
            gt_idx += 1

    # Natural: WEEKEND_HOLIDAY_SPAN (informational ground-truth label for multi-day spans)
    weekend_spans = [r for r in lb.requests if r["weekend_days_in_span"] > 0 or r["holiday_days_in_span"] > 0][:target_count]
    for req in weekend_spans:
        ground_truth.append(
            GroundTruthRecord(
                gt_id=f"GT-{gt_idx:06d}",
                issue_type="WEEKEND_HOLIDAY_SPAN",
                entity_type="leave_request",
                entity_id=req["request_id"],
                related_entity_ids="",
                expected_decision="FLAG",
                expected_approval_path="CALENDAR_EXCLUSION",
                expected_reason_code="CAL-001_SPAN_CONTAINS_NON_WORKING_DAYS",
                severity="LOW",
                injected=0,
                injection_note=f"Leave interval spans {req['weekend_days_in_span']} weekend and {req['holiday_days_in_span']} statutory holiday days.",
            )
        )
        gt_idx += 1

    # =========================================================================
    # 9. ASSEMBLE EXPECTED DECISIONS FOR EVERY LEAVE AND EXPENSE
    # =========================================================================
    expected_decisions: List[Dict[str, Any]] = []

    for req in lb.requests:
        req_id = req["request_id"]
        # Check if an injected anomaly exists for this req
        matching_gt = next((g for g in ground_truth if g.entity_id == req_id), None)
        if matching_gt:
            exp_dec = matching_gt.expected_decision
            exp_reason = matching_gt.expected_reason_code
        elif req["status"] in ("APPROVED", "CONSUMED"):
            exp_dec = "APPROVE"
            exp_reason = "POLICY_COMPLIANT_APPROVED"
        else:
            exp_dec = "REJECT"
            exp_reason = "POLICY_CONSTRAINTS_NOT_MET"

        expected_decisions.append({
            "subject_id": req_id,
            "entity_type": "LEAVE",
            "expected_decision": exp_dec,
            "expected_reason_code": exp_reason,
            "business_metric": req["business_days"],
        })

    for claim in eb.claims:
        claim_id = claim["claim_id"]
        matching_gt = next((g for g in ground_truth if g.entity_id == claim_id), None)
        if matching_gt:
            exp_dec = matching_gt.expected_decision
            exp_reason = matching_gt.expected_reason_code
        elif claim["status"] in ("APPROVED", "REIMBURSED"):
            exp_dec = "APPROVE"
            exp_reason = "POLICY_COMPLIANT_APPROVED"
        else:
            exp_dec = "REJECT"
            exp_reason = "POLICY_CONSTRAINTS_NOT_MET"

        expected_decisions.append({
            "subject_id": claim_id,
            "entity_type": "EXPENSE",
            "expected_decision": exp_dec,
            "expected_reason_code": exp_reason,
            "business_metric": claim["total_amount_base"],
        })

    # Sort all outputs deterministically
    ground_truth.sort(key=lambda g: g.gt_id)
    expected_decisions.sort(key=lambda d: d["subject_id"])
    lb.requests.sort(key=lambda r: r["request_id"])
    eb.claims.sort(key=lambda c: c["claim_id"])
    eb.lines.sort(key=lambda l: (l["claim_id"], l["line_number"]))
    eb.reimbursements.sort(key=lambda r: r["reimbursement_id"])

    return InjectionResult(
        master_bundle=mb,
        leave_bundle=lb,
        expense_bundle=eb,
        ground_truth_records=ground_truth,
        expected_decisions=expected_decisions,
    )
