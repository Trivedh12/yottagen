"""Tests for master data generation, organizational hierarchy, and constraints."""

import datetime
import random
import pytest
from yottagen.config import SCALE_CONFIGS
from yottagen.master import generate_master_data


def test_master_data_starter_scale():
    rng = random.Random(20261022)
    bundle = generate_master_data(SCALE_CONFIGS["starter"], rng)
    assert len(bundle.employees) == 40
    assert len(bundle.cost_centers) == 8
    assert len(bundle.leave_policies) == 6
    assert len(bundle.expense_policies) == 1
    assert len(bundle.employee_cost_center_assignments) == 40


def test_master_data_full_scale():
    rng = random.Random(20261022)
    bundle = generate_master_data(SCALE_CONFIGS["full"], rng)
    assert len(bundle.employees) == 400
    assert len(bundle.cost_centers) == 8
    assert len(bundle.leave_policies) == 6


def test_hierarchy_acyclic_and_hire_date_ordering():
    rng = random.Random(20261022)
    bundle = generate_master_data(SCALE_CONFIGS["full"], rng)
    emp_map = {e["employee_id"]: e for e in bundle.employees}

    ceo_count = 0
    for emp in bundle.employees:
        mgr_id = emp["manager_id"]
        if not mgr_id:
            ceo_count += 1
            assert emp["job_level"] == 6
            continue

        # Manager must exist
        assert mgr_id in emp_map
        mgr = emp_map[mgr_id]

        # Manager level must be >= report level
        assert mgr["job_level"] >= emp["job_level"]

        # Manager hired on or before report
        emp_hire = datetime.date.fromisoformat(emp["hire_date"])
        mgr_hire = datetime.date.fromisoformat(mgr["hire_date"])
        assert mgr_hire <= emp_hire, f"Manager {mgr_id} ({mgr_hire}) hired after report {emp['employee_id']} ({emp_hire})"

        # Walk up tree to ensure acyclic and reaches CEO
        visited = set()
        curr = emp["employee_id"]
        while curr:
            assert curr not in visited, f"Cycle detected at {curr}"
            visited.add(curr)
            curr = emp_map[curr]["manager_id"]

    assert ceo_count == 1, "Exactly one CEO required"
