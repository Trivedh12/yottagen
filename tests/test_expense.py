"""Tests for expense module generation, reconciliation, routing tiers, and reimbursements."""

import random
import pytest
from yottagen.config import SCALE_CONFIGS
from yottagen.expense import generate_expense_module
from yottagen.master import generate_master_data
from yottagen.schema import EXPENSE_CLAIM_TRANSITIONS


def test_expense_module_reconciliation_and_reimbursement():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)

    bundle = generate_expense_module(
        scale,
        master.employees,
        master.expense_policies,
        master.approval_rules,
        rng,
    )

    # 1. Check claim counts
    assert len(bundle.claims) == scale.num_expense_claims
    assert len(bundle.lines) >= scale.num_expense_claims

    # 2. Line arithmetic reconciliation
    lines_by_claim = {}
    for line in bundle.lines:
        lines_by_claim.setdefault(line["claim_id"], []).append(line)

    for claim in bundle.claims:
        c_lines = lines_by_claim[claim["claim_id"]]
        assert len(c_lines) == claim["line_count"]

        sum_local = round(sum(l["amount_local"] for l in c_lines), 2)
        sum_base = round(sum(l["amount_base"] for l in c_lines), 2)
        assert abs(sum_local - claim["total_amount_local"]) < 1e-3
        assert abs(sum_base - claim["total_amount_base"]) < 1e-3

    # 3. Reimbursement validation
    claim_map = {c["claim_id"]: c for c in bundle.claims}
    for rmb in bundle.reimbursements:
        claim = claim_map[rmb["claim_id"]]
        # Claim must have been approved/reimbursed
        assert claim["status"] == "REIMBURSED"
        # Amount matches approved lines
        c_lines = lines_by_claim[claim["claim_id"]]
        expected_amt = round(sum(l["amount_local"] for l in c_lines if not l["is_disallowed"]), 2)
        assert abs(rmb["amount"] - expected_amt) < 1e-3
        assert rmb["payment_date"] >= claim["submit_date"]

    # 4. Check no self approval in baseline
    for step in bundle.approval_steps:
        claim = claim_map[step["request_id"]]
        assert step["approver_id"] != claim["employee_id"], f"Self-approval detected in step {step['step_id']}"


def test_routing_tiers_and_thresholds():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)

    bundle = generate_expense_module(
        scale,
        master.employees,
        master.expense_policies,
        master.approval_rules,
        rng,
    )

    steps_by_claim = {}
    for s in bundle.approval_steps:
        steps_by_claim.setdefault(s["request_id"], []).append(s)

    for claim in bundle.claims:
        steps = steps_by_claim[claim["claim_id"]]
        base_amt = claim["total_amount_base"]
        if base_amt <= 100.0:
            assert len(steps) >= 1
        elif base_amt <= 1000.0:
            assert len(steps) >= 2
        elif base_amt <= 5000.0:
            assert len(steps) >= 3
        else:
            assert len(steps) == 4
