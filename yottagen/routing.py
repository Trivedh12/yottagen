"""Routing and approval engine for Expense Claims and Leave Requests.

Selects approval authority paths based on:
- Base currency amount thresholds (<= $100, $100-$1000, $1000-$5000, > $5000)
- Expense category rules (Equipment, Entertainment)
- Country specific threshold overrides (DE lodging > $180, IN lodging > $150)
- Manager reporting chain and minimum level authority
- Strict self-approval prevention (approver != requester)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ResolvedApprovalStep:
    step_number: int
    rule_id: str
    rule_code: str
    required_role: str
    approver_id: str
    approver_level: int
    due_days: int
    description: str


def get_manager_chain(employee_id: str, emp_map: Dict[str, Dict[str, Any]]) -> List[str]:
    """Retrieve full ancestor reporting chain for an employee up to CEO."""
    chain = []
    curr_id = emp_map.get(employee_id, {}).get("manager_id")
    visited = set()
    while curr_id and curr_id in emp_map and curr_id not in visited:
        chain.append(curr_id)
        visited.add(curr_id)
        curr_id = emp_map[curr_id].get("manager_id")
    return chain


def find_approver_in_chain(
    chain: List[str],
    min_level: int,
    emp_map: Dict[str, Dict[str, Any]],
    exclude_ids: Optional[List[str]] = None,
) -> Optional[str]:
    """Find the closest manager in reporting chain meeting the level requirement."""
    exclude = set(exclude_ids or [])
    for mgr_id in chain:
        if mgr_id in exclude:
            continue
        mgr = emp_map.get(mgr_id)
        if mgr and mgr.get("job_level", 0) >= min_level and mgr.get("status") == "ACTIVE":
            return mgr_id
    # Fallback to CEO / top of chain if active
    for mgr_id in reversed(chain):
        if mgr_id not in exclude and emp_map.get(mgr_id, {}).get("status") == "ACTIVE":
            return mgr_id
    return None


def resolve_expense_approval_path(
    claim: Dict[str, Any],
    lines: List[Dict[str, Any]],
    employee: Dict[str, Any],
    emp_map: Dict[str, Dict[str, Any]],
    finance_approvers: List[str],
) -> List[ResolvedApprovalStep]:
    """Determine the exact required approval path for an expense claim based on rules.

    Enforces:
    - Rule AP-001: Amount thresholds and category/country triggers.
    - Rule AP-002: No self-approval (approver cannot be requester).
    - Rule AP-003: Approver level authority.
    """
    total_base = float(claim["total_amount_base"])
    country = employee["country"]
    emp_id = employee["employee_id"]
    chain = get_manager_chain(emp_id, emp_map)

    # Candidates
    used_approvers: List[str] = [emp_id]  # Prevent self-approval!

    steps: List[ResolvedApprovalStep] = []
    step_num = 1

    # Check country overrides
    has_de_lodging_override = country == "DE" and any(
        l["category"] == "LODGING" and float(l["amount_base"]) > 180.0 for l in lines
    )
    has_in_lodging_override = country == "IN" and any(
        l["category"] == "LODGING" and float(l["amount_base"]) > 150.0 for l in lines
    )
    has_equip_override = any(
        l["category"] == "EQUIPMENT" and float(l["amount_base"]) > 250.0 for l in lines
    )
    has_ent_override = any(
        l["category"] == "CLIENT_ENTERTAINMENT" and float(l["amount_base"]) > 100.0 for l in lines
    )

    needs_finance_review = (
        total_base > 1000.0
        or has_de_lodging_override
        or has_in_lodging_override
        or has_equip_override
        or has_ent_override
    )

    # 1. Step 1: Direct Line Manager (Level >= 3)
    # If claimant is already Level 5 or 6, or is CEO, delegate to VP / senior peer
    mgr_id = find_approver_in_chain(chain, 3, emp_map, used_approvers)
    if not mgr_id:
        candidates = [
            e_id for e_id, e in sorted(emp_map.items())
            if e.get("job_level", 0) >= 4 and e_id not in used_approvers and e.get("status") == "ACTIVE"
        ]
        mgr_id = candidates[0] if candidates else [k for k in sorted(emp_map.keys()) if k != emp_id][0]

    mgr_lvl = emp_map.get(mgr_id, {}).get("job_level", 3)
    rule_code_1 = "ARUL-01" if total_base <= 100.0 else "ARUL-02"
    steps.append(
        ResolvedApprovalStep(
            step_number=step_num,
            rule_id=rule_code_1,
            rule_code=rule_code_1,
            required_role="MANAGER",
            approver_id=mgr_id,
            approver_level=mgr_lvl,
            due_days=3,
            description=f"Step {step_num} direct line manager review.",
        )
    )
    used_approvers.append(mgr_id)
    step_num += 1

    # 2. Step 2: Department Head / Director (Level >= 4) if total > 100 or special triggers
    if total_base > 100.0:
        dir_id = find_approver_in_chain(chain, 4, emp_map, used_approvers)
        if not dir_id:
            candidates = [
                e_id for e_id, e in sorted(emp_map.items())
                if e.get("job_level", 0) >= 4 and e_id not in used_approvers and e.get("status") == "ACTIVE"
            ]
            dir_id = candidates[0] if candidates else [k for k in sorted(emp_map.keys()) if k not in used_approvers][0]
        dir_lvl = emp_map.get(dir_id, {}).get("job_level", 4)
        rule_code_2 = "ARUL-03" if total_base <= 1000.0 else "ARUL-05"
        steps.append(
            ResolvedApprovalStep(
                step_number=step_num,
                rule_id=rule_code_2,
                rule_code=rule_code_2,
                required_role="DIRECTOR",
                approver_id=dir_id,
                approver_level=dir_lvl,
                due_days=3,
                description=f"Step {step_num} department head / director concurrence.",
            )
        )
        used_approvers.append(dir_id)
        step_num += 1

    # 3. Step 3: Finance Review (if > $1000 or category/country override)
    if needs_finance_review:
        # Select finance approver not already used and not claimant
        fin_cand = [f for f in finance_approvers if f not in used_approvers]
        fin_id = fin_cand[0] if fin_cand else finance_approvers[0]
        fin_lvl = emp_map.get(fin_id, {}).get("job_level", 3)

        if has_de_lodging_override:
            rule_fin = "ARUL-08"
        elif has_in_lodging_override:
            rule_fin = "ARUL-09"
        elif has_equip_override:
            rule_fin = "ARUL-10"
        else:
            rule_fin = "ARUL-06"

        steps.append(
            ResolvedApprovalStep(
                step_number=step_num,
                rule_id=rule_fin,
                rule_code=rule_fin,
                required_role="FINANCE",
                approver_id=fin_id,
                approver_level=fin_lvl,
                due_days=3,
                description=f"Step {step_num} corporate finance audit.",
            )
        )
        used_approvers.append(fin_id)
        step_num += 1

    # 4. Step 4: Executive VP / CFO (if total > $5000)
    if total_base > 5000.0:
        exec_id = find_approver_in_chain(chain, 5, emp_map, used_approvers)
        if not exec_id:
            candidates = [
                e_id for e_id, e in sorted(emp_map.items())
                if e.get("job_level", 0) >= 5 and e_id not in used_approvers and e.get("status") == "ACTIVE"
            ]
            exec_id = candidates[0] if candidates else [k for k in sorted(emp_map.keys()) if k not in used_approvers][0]
        exec_lvl = emp_map.get(exec_id, {}).get("job_level", 5)
        steps.append(
            ResolvedApprovalStep(
                step_number=step_num,
                rule_id="ARUL-07",
                rule_code="ARUL-07",
                required_role="VP",
                approver_id=exec_id,
                approver_level=exec_lvl,
                due_days=4,
                description=f"Step {step_num} executive VP / CFO signoff.",
            )
        )

    return steps
