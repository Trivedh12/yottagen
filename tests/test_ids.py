"""Tests for canonical ID formatting and regex compliance."""

import pytest
from yottagen.ids import (
    ID_REGEX_PATTERNS,
    format_approval_rule_id,
    format_approval_step_id,
    format_cost_center_assignment_id,
    format_cost_center_id,
    format_decision_id,
    format_employee_id,
    format_expense_claim_event_id,
    format_expense_claim_id,
    format_expense_line_id,
    format_expense_policy_id,
    format_holiday_id,
    format_leave_balance_id,
    format_leave_ledger_id,
    format_leave_policy_id,
    format_leave_request_event_id,
    format_leave_request_id,
    format_reimbursement_id,
    format_rule_category_id,
    format_rule_country_id,
    validate_id_format,
)


def test_employee_id_format():
    emp_id = format_employee_id(1)
    assert emp_id == "EMP-000001"
    assert validate_id_format("employee", emp_id)
    assert not validate_id_format("employee", "EMP-1")


def test_leave_request_id_format():
    lve_id = format_leave_request_id(42)
    assert lve_id == "LVE-2026-000042"
    assert validate_id_format("leave_request", lve_id)


def test_expense_claim_id_format():
    exp_id = format_expense_claim_id(105)
    assert exp_id == "EXP-2026-000105"
    assert validate_id_format("expense_claim", exp_id)


def test_expense_line_id_format():
    claim_id = format_expense_claim_id(1)
    line_id = format_expense_line_id(claim_id, 3)
    assert line_id == "EXPL-EXP-2026-000001-03"
    assert validate_id_format("expense_line", line_id)


def test_approval_step_id_format():
    claim_id = format_expense_claim_id(1)
    step_id_exp = format_approval_step_id(claim_id, 2)
    assert step_id_exp == "APR-EXP-2026-000001-02"
    assert validate_id_format("approval_step", step_id_exp)

    lve_id = format_leave_request_id(7)
    step_id_lve = format_approval_step_id(lve_id, 1)
    assert step_id_lve == "APR-LVE-2026-000007-01"
    assert validate_id_format("approval_step", step_id_lve)


def test_reimbursement_id_format():
    rmb_id = format_reimbursement_id(12)
    assert rmb_id == "RMB-2026-000012"
    assert validate_id_format("reimbursement", rmb_id)


def test_all_entity_formats():
    assert validate_id_format("cost_center", format_cost_center_id(0))
    assert validate_id_format("leave_policy", format_leave_policy_id(1))
    assert validate_id_format("expense_policy", format_expense_policy_id(1))
    assert validate_id_format("approval_rule", format_approval_rule_id(1))
    assert validate_id_format("holiday_calendar", format_holiday_id(1))
    assert validate_id_format("leave_balance_ledger", format_leave_ledger_id(1))
    assert validate_id_format("leave_balance", format_leave_balance_id(1))
    assert validate_id_format("leave_request_event", format_leave_request_event_id(1))
    assert validate_id_format("expense_claim_event", format_expense_claim_event_id(1))
    assert validate_id_format("decision_log", format_decision_id(1))
    assert validate_id_format("approval_rule_category", format_rule_category_id(1))
    assert validate_id_format("approval_rule_country", format_rule_country_id(1))
    assert validate_id_format("employee_cost_center_assignment", format_cost_center_assignment_id(1))
