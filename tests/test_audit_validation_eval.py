"""Tests for validator, audit engine, and evaluation metric pipeline."""

import copy
import random
import pytest
from yottagen.calendar import CalendarEngine, build_holiday_calendar
from yottagen.config import SCALE_CONFIGS
from yottagen.expense import generate_expense_module
from yottagen.injector import inject_anomalies
from yottagen.leave import generate_leave_module
from yottagen.master import generate_master_data
from yottagen.audit import run_audit
from yottagen.validate import validate_dataset
from yottagen.evaluate import evaluate_audit_results


def build_test_dataset():
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
    inj_res = inject_anomalies(scale, master, leave, expense, rng)

    tables = {
        "cost_center": inj_res.master_bundle.cost_centers,
        "employee": inj_res.master_bundle.employees,
        "employee_cost_center_assignment": inj_res.master_bundle.employee_cost_center_assignments,
        "holiday_calendar": [
            {
                "holiday_id": h.holiday_id,
                "country": h.country,
                "holiday_date": h.holiday_date,
                "holiday_name": h.holiday_name,
                "is_half_day": h.is_half_day,
            }
            for h in holidays
        ],
        "leave_policy": inj_res.master_bundle.leave_policies,
        "expense_policy": inj_res.master_bundle.expense_policies,
        "approval_rule": inj_res.master_bundle.approval_rules,
        "approval_rule_category": inj_res.master_bundle.approval_rule_categories,
        "approval_rule_country": inj_res.master_bundle.approval_rule_countries,
        "leave_balance_ledger": inj_res.leave_bundle.ledger_entries,
        "leave_balance": inj_res.leave_bundle.balances,
        "leave_request": inj_res.leave_bundle.requests,
        "leave_request_event": inj_res.leave_bundle.events,
        "expense_claim": inj_res.expense_bundle.claims,
        "expense_line": inj_res.expense_bundle.lines,
        "expense_claim_event": inj_res.expense_bundle.events,
        "approval_step": inj_res.expense_bundle.approval_steps,
        "decision_log": inj_res.leave_bundle.decision_logs + inj_res.expense_bundle.decision_logs,
        "reimbursement": inj_res.expense_bundle.reimbursements,
    }
    return tables, inj_res, cal_engine


def test_validator_clean_pass():
    tables, inj_res, cal_engine = build_test_dataset()
    summary = validate_dataset(tables, inj_res.ground_truth_records, cal_engine)
    assert summary.overall_status == "PASS"
    assert summary.failed_checks == 0


def test_validator_detects_deliberate_corruption():
    tables, inj_res, cal_engine = build_test_dataset()
    corrupted_tables = copy.deepcopy(tables)

    # Deliberately corrupt PK uniqueness by adding a duplicate employee ID
    dup_emp = copy.deepcopy(corrupted_tables["employee"][0])
    corrupted_tables["employee"].append(dup_emp)

    summary = validate_dataset(corrupted_tables, inj_res.ground_truth_records, cal_engine)
    assert summary.overall_status == "FAIL"
    pk_check = next(c for c in summary.checks if c.check_id == "VAL-PK-001")
    assert pk_check.status == "FAIL"
    assert pk_check.violations_count > 0


def test_audit_detection_and_evaluation_accuracy():
    tables, inj_res, cal_engine = build_test_dataset()
    findings = run_audit(tables)
    assert len(findings) > 0

    all_decisions = inj_res.leave_bundle.decision_logs + inj_res.expense_bundle.decision_logs
    all_steps = inj_res.leave_bundle.approval_steps + inj_res.expense_bundle.approval_steps

    report = evaluate_audit_results(
        findings,
        inj_res.ground_truth_records,
        inj_res.expected_decisions,
        all_decisions,
        all_steps,
        tables,
    )

    # High detection accuracy on injected anomalies
    assert report.macro_f1 >= 0.85
    assert report.micro_f1 >= 0.85
    assert report.decision_accuracy >= 0.90
    assert report.approval_path_accuracy == 1.0
