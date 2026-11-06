"""Deterministic, immutable ID formatting and generation utilities for YottaGen."""

import re
from typing import Optional


def format_employee_id(index: int) -> str:
    """Format employee ID as EMP-000001."""
    return f"EMP-{index:06d}"


def format_cost_center_id(index: int) -> str:
    """Format cost center ID as CC-100..."""
    return f"CC-{100 + index:03d}"


def format_leave_policy_id(index: int) -> str:
    """Format leave policy ID as LPOL-01..."""
    return f"LPOL-{index:02d}"


def format_expense_policy_id(index: int) -> str:
    """Format expense policy ID as EPOL-01..."""
    return f"EPOL-{index:02d}"


def format_approval_rule_id(index: int) -> str:
    """Format approval rule ID as ARUL-01..."""
    return f"ARUL-{index:02d}"


def format_holiday_id(index: int) -> str:
    """Format holiday ID as HOL-000001..."""
    return f"HOL-{index:06d}"


def format_leave_ledger_id(index: int) -> str:
    """Format leave balance ledger ID as LBLED-000001..."""
    return f"LBLED-{index:06d}"


def format_leave_balance_id(index: int) -> str:
    """Format leave balance ID as LBAL-000001..."""
    return f"LBAL-{index:06d}"


def format_leave_request_id(index: int, year: int = 2026) -> str:
    """Format leave request ID as LVE-2026-000001..."""
    return f"LVE-{year}-{index:06d}"


def format_leave_request_event_id(index: int) -> str:
    """Format leave request event ID as LVEV-000001..."""
    return f"LVEV-{index:06d}"


def format_expense_claim_id(index: int, year: int = 2026) -> str:
    """Format expense claim ID as EXP-2026-000001..."""
    return f"EXP-{year}-{index:06d}"


def format_expense_line_id(claim_id: str, line_number: int) -> str:
    """Format expense line ID as EXPL-<claim-id>-01..."""
    return f"EXPL-{claim_id}-{line_number:02d}"


def format_expense_claim_event_id(index: int) -> str:
    """Format expense claim event ID as EXPV-000001..."""
    return f"EXPV-{index:06d}"


def format_approval_step_id(request_or_claim_id: str, step_number: int) -> str:
    """Format approval step ID as APR-<request-id>-01..."""
    return f"APR-{request_or_claim_id}-{step_number:02d}"


def format_reimbursement_id(index: int, year: int = 2026) -> str:
    """Format reimbursement ID as RMB-2026-000001..."""
    return f"RMB-{year}-{index:06d}"


def format_decision_id(index: int) -> str:
    """Format decision log ID as DEC-000001..."""
    return f"DEC-{index:06d}"


def format_rule_category_id(index: int) -> str:
    """Format rule category bridge ID as ARC-000001..."""
    return f"ARC-{index:06d}"


def format_rule_country_id(index: int) -> str:
    """Format rule country bridge ID as ARCTRY-000001..."""
    return f"ARCTRY-{index:06d}"


def format_cost_center_assignment_id(index: int) -> str:
    """Format employee cost center assignment ID as ECCA-000001..."""
    return f"ECCA-{index:06d}"


def format_receipt_id(index: int) -> str:
    """Format embedded receipt ID as RCP-000001..."""
    return f"RCP-{index:06d}"


def format_transaction_ref(index: int) -> str:
    """Format bank transaction reference as TXN-00000001..."""
    return f"TXN-{index:08d}"


ID_REGEX_PATTERNS = {
    "employee": re.compile(r"^EMP-\d{6}$"),
    "cost_center": re.compile(r"^CC-\d{3,6}$"),
    "leave_policy": re.compile(r"^LPOL-\d{2}$"),
    "expense_policy": re.compile(r"^EPOL-\d{2}$"),
    "approval_rule": re.compile(r"^ARUL-\d{2}$"),
    "holiday_calendar": re.compile(r"^HOL-\d{6}$"),
    "leave_balance_ledger": re.compile(r"^LBLED-\d{6}$"),
    "leave_balance": re.compile(r"^LBAL-\d{6}$"),
    "leave_request": re.compile(r"^LVE-2026-\d{6}$"),
    "leave_request_event": re.compile(r"^LVEV-\d{6}$"),
    "expense_claim": re.compile(r"^EXP-2026-\d{6}$"),
    "expense_line": re.compile(r"^EXPL-EXP-2026-\d{6}-\d{2}$"),
    "expense_claim_event": re.compile(r"^EXPV-\d{6}$"),
    "approval_step": re.compile(r"^APR-(LVE-2026-\d{6}|EXP-2026-\d{6})-\d{2}$"),
    "reimbursement": re.compile(r"^RMB-2026-\d{6}$"),
    "decision_log": re.compile(r"^DEC-\d{6}$"),
    "approval_rule_category": re.compile(r"^ARC-\d{6}$"),
    "approval_rule_country": re.compile(r"^ARCTRY-\d{6}$"),
    "employee_cost_center_assignment": re.compile(r"^ECCA-\d{6}$"),
}


def validate_id_format(table_name: str, id_value: str) -> bool:
    """Validate that an ID string matches the canonical regular expression pattern for its entity."""
    pattern = ID_REGEX_PATTERNS.get(table_name)
    if not pattern:
        return True
    return bool(pattern.match(id_value))
