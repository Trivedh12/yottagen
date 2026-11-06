"""Global configuration and deterministic constants for YottaGen."""

import datetime
from dataclasses import dataclass
from typing import Dict, List

DEFAULT_SEED: int = 20261022
REFERENCE_DATE_STR: str = "2026-10-22"
REFERENCE_DATE: datetime.date = datetime.date(2026, 10, 22)

# Exchange rates fixed to Base Currency (USD)
BASE_CURRENCY: str = "USD"
EXCHANGE_RATES_TO_USD: Dict[str, float] = {
    "USD": 1.0000,
    "EUR": 1.0800,
    "GBP": 1.2800,
    "SGD": 0.7400,
    "INR": 0.0120,
}

# Country allocations and local currencies
COUNTRIES: List[str] = ["IN", "US", "UK", "DE", "SG"]
COUNTRY_CURRENCY: Dict[str, str] = {
    "IN": "INR",
    "US": "USD",
    "UK": "GBP",
    "DE": "EUR",
    "SG": "SGD",
}
COUNTRY_WEIGHTS: Dict[str, float] = {
    "IN": 0.45,
    "US": 0.25,
    "UK": 0.12,
    "DE": 0.10,
    "SG": 0.08,
}

# Expense categories
EXPENSE_CATEGORIES: List[str] = [
    "TRAVEL",
    "LODGING",
    "MEALS",
    "CLIENT_ENTERTAINMENT",
    "SOFTWARE",
    "EQUIPMENT",
    "TRAINING",
    "MISC",
]

# ID Formats
ID_PREFIXES: Dict[str, str] = {
    "Employee": "EMP-",
    "LeavePolicy": "LPOL-",
    "LeaveBalance": "LBAL-",
    "LeaveBalanceLedger": "LBLED-",
    "LeaveRequest": "LVE-2026-",
    "LeaveRequestEvent": "LVEV-",
    "ExpensePolicy": "EPOL-",
    "ExpenseClaim": "EXP-2026-",
    "ExpenseLine": "EXPL-",
    "ExpenseClaimEvent": "EXPV-",
    "CostCenter": "CC-",
    "EmployeeCostCenterAssignment": "ECCA-",
    "ApprovalRule": "ARUL-",
    "ApprovalRuleCategory": "ARC-",
    "ApprovalRuleCountry": "ARCTRY-",
    "ApprovalStep": "APR-",
    "DecisionLog": "DEC-",
    "Reimbursement": "RMB-2026-",
    "HolidayCalendar": "HOL-",
}


@dataclass(frozen=True)
class ScaleConfig:
    name: str
    num_employees: int
    num_leave_policies: int
    num_leave_requests: int
    num_expense_claims: int
    target_anomalies_per_type: int


SCALE_CONFIGS: Dict[str, ScaleConfig] = {
    "starter": ScaleConfig(
        name="starter",
        num_employees=40,
        num_leave_policies=6,
        num_leave_requests=80,
        num_expense_claims=100,
        target_anomalies_per_type=2,
    ),
    "full": ScaleConfig(
        name="full",
        num_employees=400,
        num_leave_policies=6,
        num_leave_requests=800,
        num_expense_claims=1000,
        target_anomalies_per_type=15,
    ),
}
