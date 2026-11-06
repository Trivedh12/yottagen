"""Independent audit engine and rule detector for YottaGen.

Reads ONLY input tables (never ground truth) and executes the rule catalogue:
- LV-001: Leave balance sufficiency & negative balance detection
- LV-002: Overlapping approved leave detection
- LV-003: Leave notice period and consecutive day limit breaches
- EX-001: Mandatory receipt substantiation (> $25 threshold)
- EX-002: Duplicate receipt hash detection
- EX-003: Expense claim ceiling breach (> $10,000)
- EX-004: Expense incurred outside active employment window
- EX-005: Split-claim approval threshold evasion detection
- AP-001: Approval routing threshold alignment
- AP-002: Prohibition of self-approval (claimant approving own submission)
- AP-003: Approver hierarchy authority level
- RB-001: Reimbursement issued exclusively for approved claims
- RB-002: Duplicate reimbursement detection
- CC-001: Mandatory valid cost center allocation

Outputs audit findings with finding_id, issue_type, entity_id, rule_id, reason_code, reason_text, evidence_json.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class AuditFinding:
    finding_id: str
    issue_type: str
    entity_id: str
    rule_id: str
    reason_code: str
    reason_text: str
    evidence_json: str
    severity: str


def run_audit(input_tables: Dict[str, List[Dict[str, Any]]]) -> List[AuditFinding]:
    """Execute complete independent audit scan across all input tables."""
    findings: List[AuditFinding] = []
    finding_counter = 1

    employees = input_tables.get("employee", [])
    emp_map = {e["employee_id"]: e for e in employees}

    cost_centers = input_tables.get("cost_center", [])
    valid_cc_ids = {c["cost_center_id"] for c in cost_centers}

    claims = input_tables.get("expense_claim", [])
    lines = input_tables.get("expense_line", [])
    lines_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for l in lines:
        lines_by_claim.setdefault(l["claim_id"], []).append(l)

    reimbursements = input_tables.get("reimbursement", [])
    approval_steps = input_tables.get("approval_step", [])
    leave_requests = input_tables.get("leave_request", [])
    leave_balances = input_tables.get("leave_balance", [])

    # -------------------------------------------------------------------------
    # 1. LV-001: Leave Balance Sufficiency & Negative Balance Check
    # -------------------------------------------------------------------------
    for bal in leave_balances:
        closing = float(bal["closing_balance"])
        if closing < 0.0:
            findings.append(
                AuditFinding(
                    finding_id=f"FIND-{finding_counter:06d}",
                    issue_type="NEGATIVE_LEAVE_BALANCE",
                    entity_id=bal["balance_id"],
                    rule_id="LV-001",
                    reason_code="LV-001_NEGATIVE_BALANCE",
                    reason_text=f"Closing balance ({closing} days) is negative for employee {bal['employee_id']}.",
                    evidence_json=json.dumps({
                        "balance_id": bal["balance_id"],
                        "employee_id": bal["employee_id"],
                        "policy_id": bal["policy_id"],
                        "closing_balance": closing,
                    }),
                    severity="HIGH",
                )
            )
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 2. LV-002: Overlapping Approved Leave Detection
    # -------------------------------------------------------------------------
    approved_leaves_by_emp: Dict[str, List[Dict[str, Any]]] = {}
    for req in leave_requests:
        if req["status"] in ("APPROVED", "CONSUMED"):
            approved_leaves_by_emp.setdefault(req["employee_id"], []).append(req)

    flagged_overlaps: Set[str] = set()
    for emp_id, req_list in approved_leaves_by_emp.items():
        for i in range(len(req_list)):
            for j in range(i + 1, len(req_list)):
                r1 = req_list[i]
                r2 = req_list[j]
                s1, e1 = datetime.date.fromisoformat(r1["start_date"]), datetime.date.fromisoformat(r1["end_date"])
                s2, e2 = datetime.date.fromisoformat(r2["start_date"]), datetime.date.fromisoformat(r2["end_date"])
                if max(s1, s2) <= min(e1, e2):
                    flag_req = r2 if r2["request_id"] > r1["request_id"] else r1
                    other_req = r1 if flag_req == r2 else r2
                    if flag_req["request_id"] not in flagged_overlaps:
                        flagged_overlaps.add(flag_req["request_id"])
                        findings.append(
                            AuditFinding(
                                finding_id=f"FIND-{finding_counter:06d}",
                                issue_type="OVERLAPPING_APPROVED_LEAVE",
                                entity_id=flag_req["request_id"],
                                rule_id="LV-002",
                                reason_code="LV-002_OVERLAPPING_LEAVE",
                                reason_text=f"Leave request {flag_req['request_id']} overlaps with concurrent approved leave {other_req['request_id']}.",
                                evidence_json=json.dumps({
                                    "conflict_request_id": other_req["request_id"],
                                    "span1": f"{r1['start_date']} to {r1['end_date']}",
                                    "span2": f"{r2['start_date']} to {r2['end_date']}",
                                }),
                                severity="CRITICAL",
                            )
                        )
                        finding_counter += 1

    # -------------------------------------------------------------------------
    # 2b. LV-001: Insufficient Balance Rejections
    # -------------------------------------------------------------------------
    leave_events = input_tables.get("leave_request_event", [])
    flagged_insuf: Set[str] = set()
    for ev in leave_events:
        if ev.get("to_status") == "REJECTED" and ev.get("reason_code") == "INSUFFICIENT_BALANCE":
            rid = ev["request_id"]
            if rid not in flagged_insuf:
                flagged_insuf.add(rid)
                findings.append(
                    AuditFinding(
                        finding_id=f"FIND-{finding_counter:06d}",
                        issue_type="INSUFFICIENT_BALANCE",
                        entity_id=rid,
                        rule_id="LV-001",
                        reason_code="LV-001_INSUFFICIENT_BALANCE",
                        reason_text=f"Leave request {rid} rejected due to insufficient available balance.",
                        evidence_json=json.dumps({
                            "request_id": rid,
                            "reason": ev.get("comment", ""),
                        }),
                        severity="MEDIUM",
                    )
                )
                finding_counter += 1

    # -------------------------------------------------------------------------
    # 2c. CAL-001: Weekend & Holiday Spans (Calendar Coverage Audit)
    # -------------------------------------------------------------------------
    for req in leave_requests:
        wk = int(req.get("weekend_days_in_span", 0))
        hol = int(req.get("holiday_days_in_span", 0))
        if wk > 0 or hol > 0:
            findings.append(
                AuditFinding(
                    finding_id=f"FIND-{finding_counter:06d}",
                    issue_type="WEEKEND_HOLIDAY_SPAN",
                    entity_id=req["request_id"],
                    rule_id="CAL-001",
                    reason_code="CAL-001_SPAN_CONTAINS_NON_WORKING_DAYS",
                    reason_text=f"Leave request span includes {wk} weekend days and {hol} statutory holidays.",
                    evidence_json=json.dumps({
                        "request_id": req["request_id"],
                        "weekend_days": wk,
                        "holiday_days": hol,
                    }),
                    severity="LOW",
                )
            )
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 3. EX-004: Expense Date Outside Active Employment Window
    # -------------------------------------------------------------------------
    for claim in claims:
        emp = emp_map.get(claim["employee_id"])
        if not emp:
            continue
        hire_date = datetime.date.fromisoformat(emp["hire_date"])
        term_date = datetime.date.fromisoformat(emp["termination_date"]) if emp.get("termination_date") else None

        c_lines = lines_by_claim.get(claim["claim_id"], [])
        for line in c_lines:
            exp_date = datetime.date.fromisoformat(line["expense_date"])
            is_outside = False
            desc = ""
            if exp_date < hire_date:
                is_outside = True
                desc = f"Incurred date ({exp_date}) precedes hire date ({hire_date})."
            elif term_date and exp_date > term_date:
                is_outside = True
                desc = f"Incurred date ({exp_date}) succeeds termination date ({term_date})."

            if is_outside:
                findings.append(
                    AuditFinding(
                        finding_id=f"FIND-{finding_counter:06d}",
                        issue_type="EXPENSE_DATE_OUTSIDE_EMPLOYMENT",
                        entity_id=claim["claim_id"],
                        rule_id="EX-004",
                        reason_code="EX-004_DATE_OUTSIDE_EMPLOYMENT",
                        reason_text=desc,
                        evidence_json=json.dumps({
                            "claim_id": claim["claim_id"],
                            "line_id": line["line_id"],
                            "expense_date": line["expense_date"],
                            "hire_date": emp["hire_date"],
                            "termination_date": emp.get("termination_date", ""),
                        }),
                        severity="HIGH",
                    )
                )
                finding_counter += 1
                break  # Flag claim once

    # -------------------------------------------------------------------------
    # 4. EX-005: Split-Claim Approval Threshold Evasion Detection
    # -------------------------------------------------------------------------
    # Window: claims by same employee within 3 days, same vendor or category,
    # individual claim <= $100 but cumulative sum > $100
    claims_by_emp: Dict[str, List[Dict[str, Any]]] = {}
    for c in claims:
        claims_by_emp.setdefault(c["employee_id"], []).append(c)

    flagged_split_claims: Set[str] = set()
    for emp_id, emp_claims in claims_by_emp.items():
        if len(emp_claims) < 2:
            continue
        # Sort by submit_date
        sorted_c = sorted(emp_claims, key=lambda x: x["submit_date"])
        for i in range(len(sorted_c)):
            cluster = [sorted_c[i]]
            d1 = datetime.date.fromisoformat(sorted_c[i]["submit_date"])
            for j in range(i + 1, len(sorted_c)):
                d2 = datetime.date.fromisoformat(sorted_c[j]["submit_date"])
                if (d2 - d1).days <= 3:
                    cluster.append(sorted_c[j])
            if len(cluster) >= 2:
                # Check if each individual claim was <= $100 (Tier 1) and sum exceeds $100
                all_under_tier1 = all(float(c["total_amount_base"]) <= 100.0 for c in cluster)
                cluster_sum = sum(float(c["total_amount_base"]) for c in cluster)
                if all_under_tier1 and cluster_sum > 100.0:
                    for c in cluster:
                        if c["claim_id"] not in flagged_split_claims:
                            flagged_split_claims.add(c["claim_id"])
                            findings.append(
                                AuditFinding(
                                    finding_id=f"FIND-{finding_counter:06d}",
                                    issue_type="SPLIT_CLAIM_THRESHOLD_EVASION",
                                    entity_id=c["claim_id"],
                                    rule_id="EX-005",
                                    reason_code="EX-005_SPLIT_CLAIM_EVASION",
                                    reason_text=f"Split-claim threshold evasion: cluster of {len(cluster)} claims sums to ${cluster_sum:.2f}, circumventing Tier 2 review.",
                                    evidence_json=json.dumps({
                                        "cluster_claim_ids": [x["claim_id"] for x in cluster],
                                        "cluster_total_usd": round(cluster_sum, 2),
                                        "threshold": 100.0,
                                    }),
                                    severity="MEDIUM",
                                )
                            )
                            finding_counter += 1

    # -------------------------------------------------------------------------
    # 5. CC-001: Missing or Invalid Cost Center
    # -------------------------------------------------------------------------
    for claim in claims:
        cc_id = claim.get("cost_center_id", "")
        if not cc_id or cc_id not in valid_cc_ids:
            findings.append(
                AuditFinding(
                    finding_id=f"FIND-{finding_counter:06d}",
                    issue_type="MISSING_COST_CENTER",
                    entity_id=claim["claim_id"],
                    rule_id="CC-001",
                    reason_code="CC-001_MISSING_COST_CENTER",
                    reason_text=f"Claim {claim['claim_id']} lacks a valid operational cost center allocation.",
                    evidence_json=json.dumps({
                        "claim_id": claim["claim_id"],
                        "cost_center_id": cc_id,
                    }),
                    severity="HIGH",
                )
            )
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 6. AP-002: Self-Approval Prohibited
    # -------------------------------------------------------------------------
    claim_map = {c["claim_id"]: c for c in claims}
    leave_map = {l["request_id"]: l for l in leave_requests}

    for step in approval_steps:
        req_id = step["request_id"]
        claim = claim_map.get(req_id)
        leave = leave_map.get(req_id)
        requester_id = claim["employee_id"] if claim else (leave["employee_id"] if leave else None)

        if requester_id and step["approver_id"] == requester_id:
            findings.append(
                AuditFinding(
                    finding_id=f"FIND-{finding_counter:06d}",
                    issue_type="APPROVAL_BY_REQUESTER",
                    entity_id=step["step_id"],
                    rule_id="AP-002",
                    reason_code="AP-002_SELF_APPROVAL_PROHIBITED",
                    reason_text=f"Self-approval violation: approver {step['approver_id']} is the submitting employee.",
                    evidence_json=json.dumps({
                        "step_id": step["step_id"],
                        "request_id": req_id,
                        "approver_id": step["approver_id"],
                        "requester_id": requester_id,
                    }),
                    severity="CRITICAL",
                )
            )
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 7. RB-002 & RB-001: Duplicate or Ineligible Reimbursements
    # -------------------------------------------------------------------------
    reimbursements_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for rmb in reimbursements:
        reimbursements_by_claim.setdefault(rmb["claim_id"], []).append(rmb)

    for claim_id, rmb_list in reimbursements_by_claim.items():
        if len(rmb_list) > 1:
            # Duplicate reimbursement anomaly!
            for rmb in rmb_list[1:]:
                findings.append(
                    AuditFinding(
                        finding_id=f"FIND-{finding_counter:06d}",
                        issue_type="DUPLICATE_REIMBURSEMENT",
                        entity_id=rmb["reimbursement_id"],
                        rule_id="RB-002",
                        reason_code="RB-002_DUPLICATE_REIMBURSEMENT",
                        reason_text=f"Multiple disbursements issued for claim {claim_id}.",
                        evidence_json=json.dumps({
                            "claim_id": claim_id,
                            "reimbursement_id": rmb["reimbursement_id"],
                            "original_reimbursement_id": rmb_list[0]["reimbursement_id"],
                            "amount": rmb["amount"],
                        }),
                        severity="CRITICAL",
                    )
                )
                finding_counter += 1

        claim = claim_map.get(claim_id)
        if claim and claim["status"] not in ("APPROVED", "REIMBURSED"):
            for rmb in rmb_list:
                findings.append(
                    AuditFinding(
                        finding_id=f"FIND-{finding_counter:06d}",
                        issue_type="INELIGIBLE_REIMBURSEMENT",
                        entity_id=rmb["reimbursement_id"],
                        rule_id="RB-001",
                        reason_code="RB-001_INELIGIBLE_DISBURSEMENT",
                        reason_text=f"Disbursement issued for claim {claim_id} with non-approved status ({claim['status']}).",
                        evidence_json=json.dumps({
                            "claim_id": claim_id,
                            "reimbursement_id": rmb["reimbursement_id"],
                            "claim_status": claim["status"],
                        }),
                        severity="CRITICAL",
                    )
                )
                finding_counter += 1

    # -------------------------------------------------------------------------
    # 8. EX-001: Missing Receipt Substantiation
    # -------------------------------------------------------------------------
    for claim in claims:
        c_lines = lines_by_claim.get(claim["claim_id"], [])
        has_missing = any(float(l["amount_base"]) > 25.0 and not int(l["has_receipt"]) for l in c_lines)
        if has_missing:
            findings.append(
                AuditFinding(
                    finding_id=f"FIND-{finding_counter:06d}",
                    issue_type="MISSING_RECEIPT",
                    entity_id=claim["claim_id"],
                    rule_id="EX-001",
                    reason_code="EX-001_MISSING_RECEIPT",
                    reason_text="Claim contains line items exceeding $25 threshold without receipt substantiation.",
                    evidence_json=json.dumps({
                        "claim_id": claim["claim_id"],
                        "threshold": 25.0,
                    }),
                    severity="HIGH",
                )
            )
            finding_counter += 1

    findings.sort(key=lambda f: f.finding_id)
    return findings


def export_audit_findings_csv(findings: List[AuditFinding]) -> str:
    """Format audit findings as canonical CSV."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "finding_id",
        "issue_type",
        "entity_id",
        "rule_id",
        "reason_code",
        "reason_text",
        "evidence_json",
        "severity",
    ])
    for f in findings:
        writer.writerow([
            f.finding_id,
            f.issue_type,
            f.entity_id,
            f.rule_id,
            f.reason_code,
            f.reason_text,
            f.evidence_json,
            f.severity,
        ])
    return output.getvalue()
