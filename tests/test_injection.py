"""Tests for anomaly injection, ground truth generation, and data leakage prevention."""

import random
import pytest
from yottagen.calendar import CalendarEngine, build_holiday_calendar
from yottagen.config import SCALE_CONFIGS
from yottagen.expense import generate_expense_module
from yottagen.injector import inject_anomalies
from yottagen.leave import generate_leave_module
from yottagen.master import generate_master_data

FORBIDDEN_LEAKAGE_COLUMNS = {
    "issue_type",
    "is_anomaly",
    "anomaly",
    "ground_truth",
    "gt_id",
    "injection_note",
    "is_injected",
    "expected_decision",
}


def test_anomaly_injection_and_counts():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)
    holidays = build_holiday_calendar(2015, 2027)
    cal_engine = CalendarEngine(holidays)

    leave = generate_leave_module(
        scale, master.employees, master.leave_policies, master.approval_rules, cal_engine, rng
    )
    expense = generate_expense_module(
        scale, master.employees, master.expense_policies, master.approval_rules, rng
    )

    result = inject_anomalies(scale, master, leave, expense, rng)

    # Verify that each injected issue type is present in ground truth
    issue_types = {gt.issue_type for gt in result.ground_truth_records if gt.injected == 1}
    required_injected_types = {
        "NEGATIVE_LEAVE_BALANCE",
        "OVERLAPPING_APPROVED_LEAVE",
        "EXPENSE_DATE_OUTSIDE_EMPLOYMENT",
        "SPLIT_CLAIM_THRESHOLD_EVASION",
        "MISSING_COST_CENTER",
        "APPROVAL_BY_REQUESTER",
        "DUPLICATE_REIMBURSEMENT",
    }
    for req_type in required_injected_types:
        assert req_type in issue_types, f"Missing injected issue type: {req_type}"


def test_no_data_leakage_in_input_tables():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)
    holidays = build_holiday_calendar(2015, 2027)
    cal_engine = CalendarEngine(holidays)

    leave = generate_leave_module(
        scale, master.employees, master.leave_policies, master.approval_rules, cal_engine, rng
    )
    expense = generate_expense_module(
        scale, master.employees, master.expense_policies, master.approval_rules, rng
    )

    result = inject_anomalies(scale, master, leave, expense, rng)

    # Check all entity tables in bundles
    all_table_records = {
        "cost_center": result.master_bundle.cost_centers,
        "employee": result.master_bundle.employees,
        "employee_cost_center_assignment": result.master_bundle.employee_cost_center_assignments,
        "leave_policy": result.master_bundle.leave_policies,
        "expense_policy": result.master_bundle.expense_policies,
        "approval_rule": result.master_bundle.approval_rules,
        "approval_rule_category": result.master_bundle.approval_rule_categories,
        "approval_rule_country": result.master_bundle.approval_rule_countries,
        "leave_balance_ledger": result.leave_bundle.ledger_entries,
        "leave_balance": result.leave_bundle.balances,
        "leave_request": result.leave_bundle.requests,
        "leave_request_event": result.leave_bundle.events,
        "expense_claim": result.expense_bundle.claims,
        "expense_line": result.expense_bundle.lines,
        "expense_claim_event": result.expense_bundle.events,
        "approval_step": result.expense_bundle.approval_steps,
        "reimbursement": result.expense_bundle.reimbursements,
    }

    for table_name, records in all_table_records.items():
        if not records:
            continue
        first_row = records[0]
        for col_name in first_row.keys():
            assert (
                col_name.lower() not in FORBIDDEN_LEAKAGE_COLUMNS
            ), f"Leaked column '{col_name}' found in input table '{table_name}'!"
