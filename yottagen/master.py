"""Master data generator for YottaGen.

Generates:
- CostCenter
- Employee (organizational hierarchy, countries, roles, authority)
- EmployeeCostCenterAssignment (effective dates)
- LeavePolicy (6 policies)
- ExpensePolicy
- ApprovalRule, ApprovalRuleCategory, ApprovalRuleCountry
"""

from __future__ import annotations

import datetime
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from yottagen.config import (
    BASE_CURRENCY,
    COUNTRIES,
    COUNTRY_CURRENCY,
    COUNTRY_WEIGHTS,
    DEFAULT_SEED,
    EXPENSE_CATEGORIES,
    REFERENCE_DATE,
    ScaleConfig,
)
from yottagen.ids import (
    format_approval_rule_id,
    format_cost_center_assignment_id,
    format_cost_center_id,
    format_employee_id,
    format_expense_policy_id,
    format_leave_policy_id,
    format_rule_category_id,
    format_rule_country_id,
)

# Realistic synthetic name pools by country
NAMES_BY_COUNTRY = {
    "IN": {
        "first": ["Aarav", "Pooja", "Vikram", "Ananya", "Rohan", "Sneha", "Aditya", "Neha", "Rahul", "Priya", "Karthik", "Divya", "Siddharth", "Meera", "Arjun", "Kavya"],
        "last": ["Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Choudhury", "Gupta", "Mehta", "Rao", "Joshi", "Bhat", "Deshmukh", "Menon", "Singh"],
        "cities": ["Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi", "Chennai"],
    },
    "US": {
        "first": ["James", "Emma", "Michael", "Olivia", "William", "Sophia", "Alexander", "Isabella", "Ethan", "Charlotte", "Daniel", "Amelia", "David", "Harper"],
        "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin"],
        "cities": ["New York", "San Francisco", "Austin", "Seattle", "Chicago", "Boston"],
    },
    "UK": {
        "first": ["Oliver", "Amelia", "George", "Isla", "Harry", "Ava", "Noah", "Grace", "Jack", "Freya", "Leo", "Lily", "Arthur", "Mia"],
        "last": ["Davies", "Evans", "Clarke", "Walker", "Wright", "Robinson", "Wood", "Thompson", "White", "Watson", "Edwards", "Green"],
        "cities": ["London", "Manchester", "Edinburgh", "Bristol", "Cambridge"],
    },
    "DE": {
        "first": ["Lukas", "Hannah", "Leon", "Emma", "Maximilian", "Mia", "Paul", "Sophia", "Felix", "Lena", "Jonas", "Leah", "Tim"],
        "last": ["Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann"],
        "cities": ["Berlin", "Munich", "Frankfurt", "Hamburg", "Stuttgart"],
    },
    "SG": {
        "first": ["Wei", "Mei", "Jian", "Hui", "Jun", "Xin", "Zhi", "Yan", "Boon", "Siew", "Kai", "Ling"],
        "last": ["Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh", "Teo", "Low"],
        "cities": ["Singapore"],
    },
}

COST_CENTER_SPECS = [
    ("ENG", "Engineering", "Technology", 5000000.0),
    ("SALES", "Sales & Business Dev", "Commercial", 3000000.0),
    ("MKT", "Marketing & Growth", "Commercial", 1500000.0),
    ("GNA", "General & Administrative", "Operations", 1000000.0),
    ("PROD", "Product Management", "Technology", 2000000.0),
    ("HR", "People Operations", "Human Resources", 800000.0),
    ("FIN", "Finance & Accounting", "Finance", 900000.0),
    ("OPS", "Operations & IT Infrastructure", "Operations", 1200000.0),
]


@dataclass
class MasterDataBundle:
    cost_centers: List[Dict[str, Any]]
    employees: List[Dict[str, Any]]
    employee_cost_center_assignments: List[Dict[str, Any]]
    leave_policies: List[Dict[str, Any]]
    expense_policies: List[Dict[str, Any]]
    approval_rules: List[Dict[str, Any]]
    approval_rule_categories: List[Dict[str, Any]]
    approval_rule_countries: List[Dict[str, Any]]


def generate_leave_policies() -> List[Dict[str, Any]]:
    """Generate exactly 6 deterministic leave policies."""
    policies = [
        {
            "policy_id": format_leave_policy_id(1),
            "policy_name": "Annual",
            "description": "Standard paid vacation leave accrued monthly.",
            "country_scope": "ALL",
            "accrual_days_per_month": 1.75,
            "annual_cap": 21.0,
            "carry_forward_max": 5.0,
            "min_notice_days": 3,
            "max_consecutive_days": 15,
            "requires_doc_after_days": 0,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 2,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
        {
            "policy_id": format_leave_policy_id(2),
            "policy_name": "Sick",
            "description": "Paid sick leave for personal illness or medical recovery.",
            "country_scope": "ALL",
            "accrual_days_per_month": 1.0,
            "annual_cap": 12.0,
            "carry_forward_max": 0.0,
            "min_notice_days": 0,
            "max_consecutive_days": 10,
            "requires_doc_after_days": 3,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 1,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
        {
            "policy_id": format_leave_policy_id(3),
            "policy_name": "Casual",
            "description": "Casual leave for urgent personal affairs and short breaks.",
            "country_scope": "ALL",
            "accrual_days_per_month": 0.5,
            "annual_cap": 6.0,
            "carry_forward_max": 0.0,
            "min_notice_days": 1,
            "max_consecutive_days": 3,
            "requires_doc_after_days": 0,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 1,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
        {
            "policy_id": format_leave_policy_id(4),
            "policy_name": "Parental",
            "description": "Maternity, paternity, or adoption leave.",
            "country_scope": "ALL",
            "accrual_days_per_month": 0.0,
            "annual_cap": 90.0,
            "carry_forward_max": 0.0,
            "min_notice_days": 30,
            "max_consecutive_days": 90,
            "requires_doc_after_days": 1,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 3,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
        {
            "policy_id": format_leave_policy_id(5),
            "policy_name": "Unpaid",
            "description": "Leave without pay for approved extended absences.",
            "country_scope": "ALL",
            "accrual_days_per_month": 0.0,
            "annual_cap": 30.0,
            "carry_forward_max": 0.0,
            "min_notice_days": 7,
            "max_consecutive_days": 30,
            "requires_doc_after_days": 0,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 2,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
        {
            "policy_id": format_leave_policy_id(6),
            "policy_name": "Comp-Off",
            "description": "Compensatory time off earned for approved weekend work.",
            "country_scope": "ALL",
            "accrual_days_per_month": 0.0,
            "annual_cap": 10.0,
            "carry_forward_max": 2.0,
            "min_notice_days": 2,
            "max_consecutive_days": 5,
            "requires_doc_after_days": 0,
            "allows_negative_balance": 0,
            "approval_levels_by_duration": 1,
            "effective_from": "2015-01-01",
            "effective_to": "2030-12-31",
        },
    ]
    policies.sort(key=lambda p: p["policy_id"])
    return policies


def generate_expense_policies() -> List[Dict[str, Any]]:
    """Generate global corporate expense policy."""
    policies = [
        {
            "policy_id": format_expense_policy_id(1),
            "policy_name": "Standard Travel & Expense Policy 2026",
            "currency": BASE_CURRENCY,
            "daily_meal_limit": 75.0,
            "receipt_required_threshold": 25.0,
            "max_claim_amount": 10000.0,
            "entertainment_per_person_limit": 100.0,
            "equipment_auto_approval_limit": 250.0,
            "lodging_daily_limit_in": 150.0,
            "lodging_daily_limit_de": 180.0,
            "effective_from": "2020-01-01",
            "effective_to": "2030-12-31",
        }
    ]
    return policies


def generate_approval_rules() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate multi-tier approval rules and bridges for expenses and leave."""
    rules = [
        # Expense Tier 1: <= $100 -> Manager
        {
            "rule_id": format_approval_rule_id(1),
            "rule_code": "APR-EXP-TIER1",
            "name": "Expense <= $100 Direct Manager Review",
            "entity_type": "EXPENSE",
            "min_amount": 0.0,
            "max_amount": 100.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "Standard expense claims under $100 require immediate line manager approval.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Expense Tier 2: $100 - $1,000 -> Step 1: Manager, Step 2: Director/Dept Head
        {
            "rule_id": format_approval_rule_id(2),
            "rule_code": "APR-EXP-TIER2-MGR",
            "name": "Expense $100-$1000 Step 1 Manager Review",
            "entity_type": "EXPENSE",
            "min_amount": 100.0,
            "max_amount": 1000.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "Claims between $100 and $1,000 require manager approval as step 1.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(3),
            "rule_code": "APR-EXP-TIER2-HEAD",
            "name": "Expense $100-$1000 Step 2 Department Head Review",
            "entity_type": "EXPENSE",
            "min_amount": 100.0,
            "max_amount": 1000.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "DIRECTOR",
            "min_approver_level": 4,
            "step_number": 2,
            "description": "Claims between $100 and $1,000 require department head signoff as step 2.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Expense Tier 3: $1,000 - $5,000 -> Step 1: Manager, Step 2: Director, Step 3: Finance
        {
            "rule_id": format_approval_rule_id(4),
            "rule_code": "APR-EXP-TIER3-MGR",
            "name": "Expense $1000-$5000 Step 1 Manager",
            "entity_type": "EXPENSE",
            "min_amount": 1000.0,
            "max_amount": 5000.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "High value claims require manager signoff.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(5),
            "rule_code": "APR-EXP-TIER3-DIR",
            "name": "Expense $1000-$5000 Step 2 Director",
            "entity_type": "EXPENSE",
            "min_amount": 1000.0,
            "max_amount": 5000.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "DIRECTOR",
            "min_approver_level": 4,
            "step_number": 2,
            "description": "High value claims require director concurrence.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(6),
            "rule_code": "APR-EXP-TIER3-FIN",
            "name": "Expense $1000-$5000 Step 3 Finance Review",
            "entity_type": "EXPENSE",
            "min_amount": 1000.0,
            "max_amount": 5000.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "FINANCE",
            "min_approver_level": 3,
            "step_number": 3,
            "description": "High value claims require corporate finance audit.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Expense Tier 4: > $5,000 -> Step 4 VP / CFO
        {
            "rule_id": format_approval_rule_id(7),
            "rule_code": "APR-EXP-TIER4-EXEC",
            "name": "Expense > $5000 Executive VP / CFO Approval",
            "entity_type": "EXPENSE",
            "min_amount": 5000.0,
            "max_amount": 999999.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "VP",
            "min_approver_level": 5,
            "step_number": 4,
            "description": "Executive signoff for large expenditures.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Country specific overrides: DE Lodging > 180 USD requires Finance
        {
            "rule_id": format_approval_rule_id(8),
            "rule_code": "APR-EXP-DE-LODGING",
            "name": "Germany Lodging Above Cap Finance Review",
            "entity_type": "EXPENSE",
            "min_amount": 180.0,
            "max_amount": 999999.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "FINANCE",
            "min_approver_level": 3,
            "step_number": 2,
            "description": "DE hotel rates exceeding 180 USD daily cap require finance audit.",
            "categories": ["LODGING"],
            "countries": ["DE"],
        },
        # Country specific overrides: IN Lodging > 150 USD requires Finance
        {
            "rule_id": format_approval_rule_id(9),
            "rule_code": "APR-EXP-IN-LODGING",
            "name": "India Lodging Above Cap Finance Review",
            "entity_type": "EXPENSE",
            "min_amount": 150.0,
            "max_amount": 999999.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "FINANCE",
            "min_approver_level": 3,
            "step_number": 2,
            "description": "India hotel rates exceeding 150 USD daily cap require finance audit.",
            "categories": ["LODGING"],
            "countries": ["IN"],
        },
        # Equipment over $250 requires Director + Finance
        {
            "rule_id": format_approval_rule_id(10),
            "rule_code": "APR-EXP-EQUIP-FIN",
            "name": "Equipment > $250 Finance Signoff",
            "entity_type": "EXPENSE",
            "min_amount": 250.0,
            "max_amount": 999999.0,
            "min_duration_days": 0,
            "max_duration_days": 0,
            "required_role": "FINANCE",
            "min_approver_level": 3,
            "step_number": 2,
            "description": "IT equipment exceeding $250 requires IT/Finance signoff.",
            "categories": ["EQUIPMENT"],
            "countries": ["ALL"],
        },
        # Leave Rules:
        # Standard Leave <= 5 days: manager
        {
            "rule_id": format_approval_rule_id(11),
            "rule_code": "APR-LVE-STANDARD",
            "name": "Leave <= 5 Days Direct Manager Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 1,
            "max_duration_days": 5,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "Short leave up to 5 business days approved by direct manager.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Extended Leave 6-15 days: Step 1: Manager, Step 2: HR
        {
            "rule_id": format_approval_rule_id(12),
            "rule_code": "APR-LVE-EXT-MGR",
            "name": "Leave 6-15 Days Step 1 Manager Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 6,
            "max_duration_days": 15,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "Extended leave step 1 manager approval.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(13),
            "rule_code": "APR-LVE-EXT-HR",
            "name": "Leave 6-15 Days Step 2 HR Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 6,
            "max_duration_days": 15,
            "required_role": "HR",
            "min_approver_level": 3,
            "step_number": 2,
            "description": "Extended leave step 2 HR compliance verification.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        # Long Leave > 15 days or Parental: Step 1: Manager, Step 2: HR, Step 3: Director
        {
            "rule_id": format_approval_rule_id(14),
            "rule_code": "APR-LVE-PAR-MGR",
            "name": "Leave > 15 Days Step 1 Manager Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 16,
            "max_duration_days": 365,
            "required_role": "MANAGER",
            "min_approver_level": 3,
            "step_number": 1,
            "description": "Extended / parental leave step 1 manager approval.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(15),
            "rule_code": "APR-LVE-PAR-HR",
            "name": "Leave > 15 Days Step 2 HR Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 16,
            "max_duration_days": 365,
            "required_role": "HR",
            "min_approver_level": 3,
            "step_number": 2,
            "description": "Extended / parental leave step 2 HR review.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
        {
            "rule_id": format_approval_rule_id(16),
            "rule_code": "APR-LVE-PAR-DIR",
            "name": "Leave > 15 Days Step 3 Director Review",
            "entity_type": "LEAVE",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "min_duration_days": 16,
            "max_duration_days": 365,
            "required_role": "DIRECTOR",
            "min_approver_level": 4,
            "step_number": 3,
            "description": "Extended / parental leave step 3 department director approval.",
            "categories": ["ALL"],
            "countries": ["ALL"],
        },
    ]

    rule_rows = []
    category_bridges = []
    country_bridges = []
    cat_idx = 1
    ctry_idx = 1

    for r in rules:
        categories = r.pop("categories")
        countries = r.pop("countries")
        rule_rows.append(r)

        for cat in categories:
            category_bridges.append({
                "rule_category_id": format_rule_category_id(cat_idx),
                "rule_id": r["rule_id"],
                "category": cat,
            })
            cat_idx += 1

        for ctry in countries:
            country_bridges.append({
                "rule_country_id": format_rule_country_id(ctry_idx),
                "rule_id": r["rule_id"],
                "country": ctry,
            })
            ctry_idx += 1

    rule_rows.sort(key=lambda r: r["rule_id"])
    category_bridges.sort(key=lambda b: b["rule_category_id"])
    country_bridges.sort(key=lambda b: b["rule_country_id"])
    return rule_rows, category_bridges, country_bridges


def generate_master_data(scale_config: ScaleConfig, rng: random.Random) -> MasterDataBundle:
    """Generate all master records: CostCenter, Employee hierarchy, Policies, Rules, Bridges."""
    num_employees = scale_config.num_employees

    # 1. Generate CostCenters
    cost_centers = []
    for idx, (code, name, dept, budget) in enumerate(COST_CENTER_SPECS):
        cost_centers.append({
            "cost_center_id": format_cost_center_id(idx),
            "code": code,
            "name": name,
            "department": dept,
            "manager_id": "",  # Assigned after employees are created
            "budget_currency": BASE_CURRENCY,
            "annual_budget": budget,
            "status": "ACTIVE",
        })

    # 2. Build Employee Hierarchy
    # Calculate target counts per level
    # Level 6: 1 (CEO)
    # Level 5: ~5 VPs (or 2 for starter)
    # Level 4: ~15 Directors (or 4 for starter)
    # Level 3: ~50 Managers (or 8 for starter)
    # Level 2 & 1: ICs (rest)
    if num_employees <= 50:
        n_l6 = 1
        n_l5 = 2
        n_l4 = 4
        n_l3 = 8
        n_l2 = 12
        n_l1 = num_employees - (n_l6 + n_l5 + n_l4 + n_l3 + n_l2)
    else:
        n_l6 = 1
        n_l5 = 5
        n_l4 = 15
        n_l3 = 50
        n_l2 = int(num_employees * 0.35)
        n_l1 = num_employees - (n_l6 + n_l5 + n_l4 + n_l3 + n_l2)

    level_counts = [
        (6, n_l6, "L6", ["Chief Executive Officer"]),
        (5, n_l5, "L5", ["Vice President Engineering", "Vice President Sales", "Vice President Operations", "Vice President Human Resources", "Chief Financial Officer"]),
        (4, n_l4, "L4", ["Engineering Director", "Sales Director", "Marketing Director", "Finance Director", "HR Director", "Operations Director", "Product Director"]),
        (3, n_l3, "L3", ["Engineering Manager", "Sales Manager", "Marketing Manager", "Finance Manager", "People Partner Manager", "DevOps Manager", "Support Manager"]),
        (2, n_l2, "L2", ["Senior Software Engineer", "Senior Account Executive", "Senior Product Designer", "Senior Financial Analyst", "HR Specialist", "Senior DevOps Engineer"]),
        (1, n_l1, "L1", ["Software Engineer", "Sales Associate", "Marketing Specialist", "Junior Financial Analyst", "Operations Coordinator", "QA Associate"]),
    ]

    employees: List[Dict[str, Any]] = []
    employees_by_level: Dict[int, List[str]] = {lvl: [] for lvl in range(1, 7)}
    emp_counter = 1

    # Deterministic hire date generator ensuring managers are hired before reports
    # Base hire year range per level
    level_hire_bounds = {
        6: (datetime.date(2015, 1, 15), datetime.date(2015, 6, 1)),
        5: (datetime.date(2015, 6, 2), datetime.date(2017, 12, 31)),
        4: (datetime.date(2017, 1, 1), datetime.date(2019, 12, 31)),
        3: (datetime.date(2019, 1, 1), datetime.date(2022, 12, 31)),
        2: (datetime.date(2021, 1, 1), datetime.date(2024, 12, 31)),
        1: (datetime.date(2023, 1, 1), datetime.date(2026, 9, 30)),
    }

    # Generate from CEO (Level 6) downwards to guarantee parent managers exist and hire dates precede reports
    emp_map: Dict[str, Dict[str, Any]] = {}

    for level, count, grade, title_options in level_counts:
        for _ in range(count):
            emp_id = format_employee_id(emp_counter)
            emp_counter += 1

            # Determine country deterministically based on country weights
            country_r = rng.random()
            if country_r < 0.45:
                country = "IN"
            elif country_r < 0.70:
                country = "US"
            elif country_r < 0.82:
                country = "UK"
            elif country_r < 0.92:
                country = "DE"
            else:
                country = "SG"

            name_pool = NAMES_BY_COUNTRY[country]
            first_name = rng.choice(name_pool["first"])
            last_name = rng.choice(name_pool["last"])
            city = rng.choice(name_pool["cities"])
            email = f"{first_name.lower()}.{last_name.lower()}{emp_id[4:]}@example.com"

            # Assign manager
            if level == 6:
                manager_id = ""  # CEO
                min_hire, max_hire = level_hire_bounds[6]
            else:
                parent_level = level + 1 if level < 5 else 6
                potential_managers = employees_by_level[parent_level]
                if not potential_managers and parent_level < 6:
                    potential_managers = employees_by_level[6]
                manager_id = rng.choice(potential_managers) if potential_managers else ""
                
                # Report's hire date must be strictly >= manager's hire date
                mgr_hire = datetime.date.fromisoformat(emp_map[manager_id]["hire_date"]) if manager_id else datetime.date(2015, 1, 1)
                min_bound, max_bound = level_hire_bounds[level]
                min_hire = max(mgr_hire + datetime.timedelta(days=1), min_bound)
                if min_hire > max_bound:
                    max_hire = min_hire + datetime.timedelta(days=365)
                else:
                    max_hire = max_bound

            # Pick hire date between min_hire and max_hire
            day_delta = (max_hire - min_hire).days
            hire_offset = rng.randint(0, max(0, day_delta))
            hire_date = min_hire + datetime.timedelta(days=hire_offset)
            if hire_date > REFERENCE_DATE:
                hire_date = REFERENCE_DATE - datetime.timedelta(days=rng.randint(30, 90))

            # Status and termination
            # ~5% terminated, ~5% on leave, ~90% active
            # CEO, VPs, Directors are never terminated in baseline
            status_r = rng.random()
            if level <= 3 and status_r < 0.05:
                status = "TERMINATED"
                term_days_after = rng.randint(60, 400)
                term_date = min(hire_date + datetime.timedelta(days=term_days_after), REFERENCE_DATE)
                termination_date = term_date.isoformat()
            elif level <= 3 and status_r < 0.10:
                status = "ON_LEAVE"
                termination_date = ""
            else:
                status = "ACTIVE"
                termination_date = ""

            employee_type = "CONTRACT" if (level <= 2 and rng.random() < 0.10) else "FULL_TIME"
            title = rng.choice(title_options)

            # Assign cost center
            # Map title or level to appropriate cost center
            if "Engineer" in title or "DevOps" in title or "QA" in title:
                cc_code = "ENG"
            elif "Sales" in title or "Account" in title:
                cc_code = "SALES"
            elif "Marketing" in title:
                cc_code = "MKT"
            elif "Financial" in title or "Finance" in title or "CFO" in title:
                cc_code = "FIN"
            elif "HR" in title or "People" in title:
                cc_code = "HR"
            elif "Product" in title:
                cc_code = "PROD"
            elif "Operations" in title or "Support" in title:
                cc_code = "OPS"
            else:
                cc_code = "GNA"

            target_cc = next(c for c in cost_centers if c["code"] == cc_code)
            cost_center_id = target_cc["cost_center_id"]

            # Role and approver flags
            is_finance = 1 if (cc_code == "FIN" and level >= 3) else 0
            is_hr = 1 if (cc_code == "HR" and level >= 3) else 0

            if "CEO" in title or "CFO" in title or "Vice President" in title:
                role = "PROCESS_OWNER"
            elif is_finance or is_hr:
                role = "PROCESS_OWNER"
            elif "Operations" in title and level >= 3:
                role = "OPS_ANALYST"
            elif "Support" in title or "QA" in title:
                role = "SYSTEM_ADMIN" if rng.random() < 0.2 else "REQUESTER"
            elif level >= 3:
                role = "APPROVER"
            else:
                role = "REQUESTER"

            rec = {
                "employee_id": emp_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "country": country,
                "city": city,
                "hire_date": hire_date.isoformat(),
                "termination_date": termination_date,
                "status": status,
                "employee_type": employee_type,
                "job_level": level,
                "job_title": title,
                "grade": grade,
                "manager_id": manager_id,
                "cost_center_id": cost_center_id,
                "is_finance_approver": is_finance,
                "is_hr_approver": is_hr,
                "role": role,
            }

            employees.append(rec)
            employees_by_level[level].append(emp_id)
            emp_map[emp_id] = rec

    # Assign Cost Center Managers (from Level 4 / Level 5 employees in that department)
    for cc in cost_centers:
        matching_mgrs = [
            e["employee_id"]
            for e in employees
            if e["cost_center_id"] == cc["cost_center_id"] and e["job_level"] >= 4 and e["status"] == "ACTIVE"
        ]
        if not matching_mgrs:
            matching_mgrs = [
                e["employee_id"] for e in employees if e["job_level"] >= 4 and e["status"] == "ACTIVE"
            ]
        cc["manager_id"] = sorted(matching_mgrs)[0]

    # 3. Build EmployeeCostCenterAssignments (bridge)
    ecca_list: List[Dict[str, Any]] = []
    ecca_idx = 1
    for emp in employees:
        ecca_list.append({
            "assignment_id": format_cost_center_assignment_id(ecca_idx),
            "employee_id": emp["employee_id"],
            "cost_center_id": emp["cost_center_id"],
            "allocation_percentage": 100.0,
            "effective_from": emp["hire_date"],
            "effective_to": "2099-12-31",
            "is_primary": 1,
        })
        ecca_idx += 1

    # Sort all lists deterministically
    cost_centers.sort(key=lambda c: c["cost_center_id"])
    employees.sort(key=lambda e: e["employee_id"])
    ecca_list.sort(key=lambda a: a["assignment_id"])

    # 4. Generate Policies and Rules
    leave_policies = generate_leave_policies()
    expense_policies = generate_expense_policies()
    approval_rules, category_bridges, country_bridges = generate_approval_rules()

    return MasterDataBundle(
        cost_centers=cost_centers,
        employees=employees,
        employee_cost_center_assignments=ecca_list,
        leave_policies=leave_policies,
        expense_policies=expense_policies,
        approval_rules=approval_rules,
        approval_rule_categories=category_bridges,
        approval_rule_countries=country_bridges,
    )
