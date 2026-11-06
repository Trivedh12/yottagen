"""Tests for leave module accruals, ledger reconciliation, business days, and routing."""

import random
import pytest
from yottagen.calendar import CalendarEngine, build_holiday_calendar
from yottagen.config import SCALE_CONFIGS
from yottagen.leave import generate_leave_module
from yottagen.master import generate_master_data
from yottagen.schema import LEAVE_REQUEST_TRANSITIONS


def test_leave_module_generation_and_reconciliation():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)
    holidays = build_holiday_calendar(2015, 2027)
    cal_engine = CalendarEngine(holidays)

    bundle = generate_leave_module(
        scale,
        master.employees,
        master.leave_policies,
        master.approval_rules,
        cal_engine,
        rng,
    )

    # 1. Check counts
    assert len(bundle.requests) == scale.num_leave_requests
    assert len(bundle.balances) == scale.num_employees * scale.num_leave_policies
    assert len(bundle.ledger_entries) > 0
    assert len(bundle.events) > 0

    # 2. Arithmetic reconciliation of balances
    for bal in bundle.balances:
        reconciled = (
            bal["opening_balance"]
            + bal["accrued_days"]
            + bal["adjusted_days"]
            - bal["used_days"]
        )
        assert abs(round(reconciled, 2) - bal["closing_balance"]) < 1e-4

    # 3. Check legal state transitions for events
    events_by_req = {}
    for ev in bundle.events:
        events_by_req.setdefault(ev["request_id"], []).append(ev)

    for req_id, ev_list in events_by_req.items():
        # verify chain
        for i in range(len(ev_list) - 1):
            from_st = ev_list[i]["to_status"]
            to_st = ev_list[i + 1]["from_status"]
            assert from_st == to_st, f"Discontinuous event chain for {req_id}: {from_st} != {to_st}"
            # verify transition is legal
            allowed = LEAVE_REQUEST_TRANSITIONS.get(ev_list[i]["from_status"], set())
            assert ev_list[i]["to_status"] in allowed, f"Illegal transition {ev_list[i]['from_status']} -> {ev_list[i]['to_status']}"


def test_leave_multi_level_approval_steps():
    scale = SCALE_CONFIGS["starter"]
    rng = random.Random(20261022)
    master = generate_master_data(scale, rng)
    holidays = build_holiday_calendar(2015, 2027)
    cal_engine = CalendarEngine(holidays)

    bundle = generate_leave_module(
        scale,
        master.employees,
        master.leave_policies,
        master.approval_rules,
        cal_engine,
        rng,
    )

    steps_by_req = {}
    for st in bundle.approval_steps:
        steps_by_req.setdefault(st["request_id"], []).append(st)

    for req in bundle.requests:
        steps = steps_by_req.get(req["request_id"], [])
        bz = req["business_days"]
        pol = req["policy_id"]
        # Parental is LPOL-04
        if bz <= 5 and pol != "LPOL-04":
            assert len(steps) == 1
        elif bz <= 15 and pol != "LPOL-04":
            assert len(steps) == 2
        else:
            assert len(steps) == 3
