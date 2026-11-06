"""Single source of truth schema definition for YottaGen entities.

Used by:
- Data dictionary documentation generation (markdown, csv, json)
- SQL DDL generation (schema.sql)
- Invariant and type validator (validate.py)
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class FieldDef:
    name: str
    field_type: str  # string, integer, float, boolean, date, timestamp, json
    sql_type: str
    required: bool
    pk: bool
    fk: Optional[str]  # "target_table.target_field" or None
    allowed_values: Optional[List[str]]
    units: Optional[str]
    uniqueness: bool
    validation_rule: str
    description: str


@dataclass(frozen=True)
class RelationshipDef:
    parent_table: str
    child_table: str
    fk_field: str
    cardinality: str  # "1:1", "1:N", "N:M"
    is_optional: bool
    has_effective_dates: bool
    description: str


@dataclass(frozen=True)
class TableDef:
    name: str
    category: str  # Core, Supporting, Event, Bridge, Audit
    description: str
    id_prefix: str
    id_pattern: str
    fields: List[FieldDef]


# Legal state transitions per specification
LEAVE_REQUEST_TRANSITIONS: Dict[str, Set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"PENDING_APPROVAL", "CANCELLED", "REJECTED"},
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"CANCELLED", "CONSUMED"},
    "REJECTED": set(),
    "CANCELLED": set(),
    "CONSUMED": set(),
}

EXPENSE_CLAIM_TRANSITIONS: Dict[str, Set[str]] = {
    "DRAFT": {"SUBMITTED", "REJECTED"},
    "SUBMITTED": {"PENDING_APPROVAL", "REJECTED"},
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "RETURNED_FOR_INFO"},
    "RETURNED_FOR_INFO": {"SUBMITTED", "REJECTED"},
    "APPROVED": {"REIMBURSED"},
    "REJECTED": set(),
    "REIMBURSED": set(),
}

APPROVAL_STEP_TRANSITIONS: Dict[str, Set[str]] = {
    "PENDING": {"APPROVED", "REJECTED", "SKIPPED", "ESCALATED"},
    "APPROVED": set(),
    "REJECTED": set(),
    "SKIPPED": set(),
    "ESCALATED": {"APPROVED", "REJECTED"},
}

SCHEMA_TABLES: List[TableDef] = [
    TableDef(
        name="cost_center",
        category="Core",
        description="Operational cost centers for budgeting and organizational financial allocation.",
        id_prefix="CC-",
        id_pattern=r"^CC-\d{3,6}$",
        fields=[
            FieldDef("cost_center_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^CC-\\d{3,6}$", "Unique cost center identifier."),
            FieldDef("code", "string", "VARCHAR(32)", True, False, None, ["ENG", "SALES", "MKT", "GNA", "PROD", "HR", "FIN", "OPS"], None, True, "Upper alphanumeric code", "Cost center functional code."),
            FieldDef("name", "string", "VARCHAR(128)", True, False, None, None, None, False, "Non-empty string", "Human readable cost center department name."),
            FieldDef("department", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty string", "Department grouping."),
            FieldDef("manager_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Cost center owner/approver employee ID."),
            FieldDef("budget_currency", "string", "VARCHAR(3)", True, False, None, ["USD"], "ISO 4217", False, "Currency code USD", "Budget currency denomination."),
            FieldDef("annual_budget", "float", "NUMERIC(14,2)", True, False, None, None, "USD", False, "Value >= 0.0", "Approved annual budget allocation."),
            FieldDef("status", "string", "VARCHAR(16)", True, False, None, ["ACTIVE", "INACTIVE"], None, False, "Enum ACTIVE, INACTIVE", "Operational status."),
        ],
    ),
    TableDef(
        name="employee",
        category="Core",
        description="Comprehensive employee record including organizational hierarchy, geography, and authority.",
        id_prefix="EMP-",
        id_pattern=r"^EMP-\d{6}$",
        fields=[
            FieldDef("employee_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^EMP-\\d{6}$", "Unique employee identifier."),
            FieldDef("first_name", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty string", "Synthetic first name."),
            FieldDef("last_name", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty string", "Synthetic last name."),
            FieldDef("email", "string", "VARCHAR(128)", True, False, None, None, None, True, "Ends with @example.com", "Synthetic corporate email address."),
            FieldDef("country", "string", "VARCHAR(2)", True, False, None, ["IN", "US", "UK", "DE", "SG"], "ISO 3166-1", False, "Enum IN, US, UK, DE, SG", "Primary country of employment."),
            FieldDef("city", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty string", "Work location city."),
            FieldDef("hire_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date <= as_of_date", "Official date of hire."),
            FieldDef("termination_date", "date", "DATE", False, False, None, None, "YYYY-MM-DD", False, "Date >= hire_date or empty", "Termination date if separated."),
            FieldDef("status", "string", "VARCHAR(16)", True, False, None, ["ACTIVE", "TERMINATED", "ON_LEAVE"], None, False, "Enum status", "Employment status."),
            FieldDef("employee_type", "string", "VARCHAR(16)", True, False, None, ["FULL_TIME", "CONTRACT"], None, False, "Enum employee_type", "Worker classification."),
            FieldDef("job_level", "integer", "INTEGER", True, False, None, ["1", "2", "3", "4", "5", "6"], "Level 1-6", False, "Integer 1 to 6", "Hierarchy level (1=IC, 6=CEO)."),
            FieldDef("job_title", "string", "VARCHAR(128)", True, False, None, None, None, False, "Non-empty string", "Role title."),
            FieldDef("grade", "string", "VARCHAR(8)", True, False, None, ["L1", "L2", "L3", "L4", "L5", "L6"], None, False, "Enum L1-L6", "Compensation/authority grade."),
            FieldDef("manager_id", "string", "VARCHAR(32)", False, False, "employee.employee_id", None, None, False, "FK to Employee self or empty for CEO", "Direct manager employee ID."),
            FieldDef("cost_center_id", "string", "VARCHAR(32)", True, False, "cost_center.cost_center_id", None, None, False, "FK to CostCenter", "Primary allocated cost center."),
            FieldDef("is_finance_approver", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Whether employee has Finance sign-off authority."),
            FieldDef("is_hr_approver", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Whether employee has HR sign-off authority."),
            FieldDef("role", "string", "VARCHAR(32)", True, False, None, ["REQUESTER", "APPROVER", "PROCESS_OWNER", "OPS_ANALYST", "SYSTEM_ADMIN"], None, False, "Enum role", "Primary persona/responsibility."),
        ],
    ),
    TableDef(
        name="holiday_calendar",
        category="Supporting",
        description="Statutory and public holidays by country used for business-day computations.",
        id_prefix="HOL-",
        id_pattern=r"^HOL-\d{6}$",
        fields=[
            FieldDef("holiday_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^HOL-\\d{6}$", "Unique holiday calendar entry ID."),
            FieldDef("country", "string", "VARCHAR(2)", True, False, None, ["IN", "US", "UK", "DE", "SG"], "ISO 3166-1", False, "Enum country", "Country code."),
            FieldDef("holiday_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Valid date", "Calendar date of the holiday."),
            FieldDef("holiday_name", "string", "VARCHAR(128)", True, False, None, None, None, False, "Non-empty string", "Official holiday name."),
            FieldDef("is_half_day", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Whether the holiday counts as a half working day."),
        ],
    ),
    TableDef(
        name="leave_policy",
        category="Core",
        description="Formal leave policy governing accrual, entitlements, notice periods, and limits.",
        id_prefix="LPOL-",
        id_pattern=r"^LPOL-\d{2}$",
        fields=[
            FieldDef("policy_id", "string", "VARCHAR(16)", True, True, None, None, None, True, "Regex ^LPOL-\\d{2}$", "Unique leave policy identifier."),
            FieldDef("policy_name", "string", "VARCHAR(64)", True, False, None, ["Annual", "Sick", "Casual", "Parental", "Unpaid", "Comp-Off"], None, True, "Enum policy_name", "Name of leave category."),
            FieldDef("description", "string", "VARCHAR(255)", True, False, None, None, None, False, "Non-empty string", "Summary of policy terms."),
            FieldDef("country_scope", "string", "VARCHAR(8)", True, False, None, ["ALL", "IN", "US", "UK", "DE", "SG"], None, False, "Country scope or ALL", "Jurisdiction applicability."),
            FieldDef("accrual_days_per_month", "float", "NUMERIC(5,2)", True, False, None, None, "days/month", False, "Value >= 0.0", "Monthly earned leave rate."),
            FieldDef("annual_cap", "float", "NUMERIC(5,2)", True, False, None, None, "days/year", False, "Value >= 0.0", "Maximum annual accrual entitlement."),
            FieldDef("carry_forward_max", "float", "NUMERIC(5,2)", True, False, None, None, "days", False, "Value >= 0.0", "Maximum days carried into subsequent calendar year."),
            FieldDef("min_notice_days", "integer", "INTEGER", True, False, None, None, "days", False, "Value >= 0", "Lead time required before leave commences."),
            FieldDef("max_consecutive_days", "integer", "INTEGER", True, False, None, None, "days", False, "Value > 0", "Maximum contiguous calendar/business span allowed."),
            FieldDef("requires_doc_after_days", "integer", "INTEGER", True, False, None, None, "days", False, "Value >= 0", "Consecutive days after which medical certificate is mandatory."),
            FieldDef("allows_negative_balance", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Whether deficit balance is permitted."),
            FieldDef("approval_levels_by_duration", "integer", "INTEGER", True, False, None, ["1", "2", "3"], "Levels", False, "1, 2, or 3", "Default required approval depth."),
            FieldDef("effective_from", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date format", "Policy inception date."),
            FieldDef("effective_to", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date >= effective_from", "Policy sunset/expiration date."),
        ],
    ),
    TableDef(
        name="leave_balance_ledger",
        category="Supporting",
        description="Immutable, append-only journal of all leave accrual, consumption, and adjustment events.",
        id_prefix="LBLED-",
        id_pattern=r"^LBLED-\d{6}$",
        fields=[
            FieldDef("ledger_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^LBLED-\\d{6}$", "Unique ledger entry identifier."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Impacted employee."),
            FieldDef("policy_id", "string", "VARCHAR(16)", True, False, "leave_policy.policy_id", None, None, False, "FK to LeavePolicy", "Governing leave policy."),
            FieldDef("entry_type", "string", "VARCHAR(32)", True, False, None, ["ACCRUAL", "USAGE", "ADJUSTMENT", "CARRY_FORWARD", "FORFEIT"], None, False, "Enum entry_type", "Ledger posting type."),
            FieldDef("days", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Signed float", "Day delta (+ for credit, - for debit)."),
            FieldDef("effective_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date format", "Posting valuation date."),
            FieldDef("reference_id", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty string", "Source request ID or SYSTEM."),
            FieldDef("created_at", "timestamp", "TIMESTAMP", True, False, None, None, "ISO 8601", False, "Timestamp", "Audit creation timestamp."),
            FieldDef("notes", "string", "VARCHAR(255)", False, False, None, None, None, False, "String", "Ledger narrative."),
        ],
    ),
    TableDef(
        name="leave_balance",
        category="Core",
        description="Point-in-time materialized balance derived purely from the leave ledger.",
        id_prefix="LBAL-",
        id_pattern=r"^LBAL-\d{6}$",
        fields=[
            FieldDef("balance_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^LBAL-\\d{6}$", "Unique balance snapshot identifier."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Employee ID."),
            FieldDef("policy_id", "string", "VARCHAR(16)", True, False, "leave_policy.policy_id", None, None, False, "FK to LeavePolicy", "Policy ID."),
            FieldDef("as_of_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Reference date", "Valuation date of the balance calculation."),
            FieldDef("opening_balance", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Float >= 0.0", "Starting balance at period start."),
            FieldDef("accrued_days", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Float >= 0.0", "Cumulative accrued days."),
            FieldDef("used_days", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Float >= 0.0", "Total APPROVED leave days consumed."),
            FieldDef("adjusted_days", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Signed float", "Manual/statutory ledger adjustments."),
            FieldDef("pending_days", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "Float >= 0.0", "Days currently tied in pending requests."),
            FieldDef("closing_balance", "float", "NUMERIC(6,2)", True, False, None, None, "days", False, "closing = opening + accrued + adjusted - used", "Net available leave balance."),
        ],
    ),
    TableDef(
        name="leave_request",
        category="Core",
        description="Formal leave application submitted by an employee with calendar and business duration metrics.",
        id_prefix="LVE-2026-",
        id_pattern=r"^LVE-2026-\d{6}$",
        fields=[
            FieldDef("request_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^LVE-2026-\\d{6}$", "Unique leave request identifier."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Applicant employee ID."),
            FieldDef("policy_id", "string", "VARCHAR(16)", True, False, "leave_policy.policy_id", None, None, False, "FK to LeavePolicy", "Requested policy ID."),
            FieldDef("start_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "start_date <= end_date", "First day of requested leave."),
            FieldDef("end_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "end_date >= start_date", "Last day of requested leave."),
            FieldDef("calendar_days", "integer", "INTEGER", True, False, None, None, "days", False, "end - start + 1", "Total elapsed calendar days."),
            FieldDef("business_days", "integer", "INTEGER", True, False, None, None, "days", False, "Excludes weekends and holidays", "Net chargeable working days."),
            FieldDef("weekend_days_in_span", "integer", "INTEGER", True, False, None, None, "days", False, "Weekend count", "Count of Saturdays and Sundays in interval."),
            FieldDef("holiday_days_in_span", "integer", "INTEGER", True, False, None, None, "days", False, "Holiday count", "Count of official holidays in interval."),
            FieldDef("submit_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "submit_date <= start_date", "Submission date."),
            FieldDef("status", "string", "VARCHAR(32)", True, False, None, ["DRAFT", "SUBMITTED", "PENDING_APPROVAL", "APPROVED", "REJECTED", "CANCELLED", "CONSUMED"], None, False, "Enum status", "Current lifecycle status."),
            FieldDef("reason_code", "string", "VARCHAR(32)", True, False, None, ["VACATION", "ILLNESS", "FAMILY", "MATERNITY_PATERNITY", "PERSONAL", "EMERGENCY"], None, False, "Enum reason_code", "Applicant stated rationale."),
            FieldDef("comments", "string", "VARCHAR(255)", False, False, None, None, None, False, "Text", "Applicant comments."),
        ],
    ),
    TableDef(
        name="leave_request_event",
        category="Event",
        description="Immutable audit trail of state transitions for each leave application.",
        id_prefix="LVEV-",
        id_pattern=r"^LVEV-\d{6}$",
        fields=[
            FieldDef("event_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^LVEV-\\d{6}$", "Unique leave transition event identifier."),
            FieldDef("request_id", "string", "VARCHAR(32)", True, False, "leave_request.request_id", None, None, False, "FK to LeaveRequest", "Subject leave request."),
            FieldDef("from_status", "string", "VARCHAR(32)", True, False, None, None, None, False, "Valid status", "Pre-transition status."),
            FieldDef("to_status", "string", "VARCHAR(32)", True, False, None, None, None, False, "Valid status", "Post-transition status."),
            FieldDef("actor_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Employee ID executing action."),
            FieldDef("timestamp", "timestamp", "TIMESTAMP", True, False, None, None, "ISO 8601", False, "Timestamp format", "Time transition occurred."),
            FieldDef("reason_code", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty code", "Audit reason code."),
            FieldDef("comment", "string", "VARCHAR(255)", False, False, None, None, None, False, "Text", "Actor comment."),
        ],
    ),
    TableDef(
        name="expense_policy",
        category="Core",
        description="Corporate travel and business expense policy rules and threshold ceilings.",
        id_prefix="EPOL-",
        id_pattern=r"^EPOL-\d{2}$",
        fields=[
            FieldDef("policy_id", "string", "VARCHAR(16)", True, True, None, None, None, True, "Regex ^EPOL-\\d{2}$", "Unique expense policy identifier."),
            FieldDef("policy_name", "string", "VARCHAR(64)", True, False, None, None, None, True, "Non-empty string", "Policy title."),
            FieldDef("currency", "string", "VARCHAR(3)", True, False, None, ["USD"], "ISO 4217", False, "USD", "Reference currency."),
            FieldDef("daily_meal_limit", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value > 0.0", "Per-diem meal cap per traveler."),
            FieldDef("receipt_required_threshold", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value >= 0.0", "Threshold above which receipt is mandatory (e.g. 25.00)."),
            FieldDef("max_claim_amount", "float", "NUMERIC(12,2)", True, False, None, None, "USD", False, "Value > 0.0", "Absolute ceiling per claim before special board escalation."),
            FieldDef("entertainment_per_person_limit", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value > 0.0", "Client entertainment per-head limit."),
            FieldDef("equipment_auto_approval_limit", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value >= 0.0", "IT equipment limit requiring department head signoff."),
            FieldDef("lodging_daily_limit_in", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value > 0.0", "Daily lodging cap for India."),
            FieldDef("lodging_daily_limit_de", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "Value > 0.0", "Daily lodging cap for Germany."),
            FieldDef("effective_from", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date format", "Policy inception date."),
            FieldDef("effective_to", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date >= effective_from", "Policy sunset date."),
        ],
    ),
    TableDef(
        name="expense_claim",
        category="Core",
        description="Expense claim header aggregating line items with cost center allocation and derived amounts.",
        id_prefix="EXP-2026-",
        id_pattern=r"^EXP-2026-\d{6}$",
        fields=[
            FieldDef("claim_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^EXP-2026-\\d{6}$", "Unique expense claim header identifier."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Claimant employee ID."),
            FieldDef("cost_center_id", "string", "VARCHAR(32)", True, False, "cost_center.cost_center_id", None, None, False, "FK to CostCenter", "Chargeable cost center."),
            FieldDef("policy_id", "string", "VARCHAR(16)", True, False, "expense_policy.policy_id", None, None, False, "FK to ExpensePolicy", "Governing expense policy."),
            FieldDef("claim_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "claim_date <= submit_date", "Date claim was assembled."),
            FieldDef("submit_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "submit_date <= as_of_date", "Submission date for approval."),
            FieldDef("purpose", "string", "VARCHAR(255)", True, False, None, None, None, False, "Non-empty string", "Business justification."),
            FieldDef("currency", "string", "VARCHAR(3)", True, False, None, ["USD", "INR", "GBP", "EUR", "SGD"], "ISO 4217", False, "Local currency code", "Claim primary local currency."),
            FieldDef("total_amount_local", "float", "NUMERIC(12,2)", True, False, None, None, "local currency", False, "Sum of line amount_local", "Total claim amount in local currency."),
            FieldDef("total_amount_base", "float", "NUMERIC(12,2)", True, False, None, None, "USD", False, "Sum of line amount_base", "Total claim amount normalized to base USD."),
            FieldDef("status", "string", "VARCHAR(32)", True, False, None, ["DRAFT", "SUBMITTED", "PENDING_APPROVAL", "APPROVED", "REJECTED", "RETURNED_FOR_INFO", "REIMBURSED"], None, False, "Enum status", "Lifecycle status."),
            FieldDef("line_count", "integer", "INTEGER", True, False, None, None, "count", False, "Integer 1-10", "Number of constituent expense line items."),
        ],
    ),
    TableDef(
        name="expense_line",
        category="Core",
        description="Granular expense item including currency conversion and embedded cryptographic receipt metadata.",
        id_prefix="EXPL-",
        id_pattern=r"^EXPL-EXP-2026-\d{6}-\d{2}$",
        fields=[
            FieldDef("line_id", "string", "VARCHAR(64)", True, True, None, None, None, True, "Regex ^EXPL-EXP-2026-\\d{6}-\\d{2}$", "Unique line item identifier."),
            FieldDef("claim_id", "string", "VARCHAR(32)", True, False, "expense_claim.claim_id", None, None, False, "FK to ExpenseClaim", "Parent expense claim ID."),
            FieldDef("line_number", "integer", "INTEGER", True, False, None, None, "index", False, "1 to 10", "Sequential line number within claim."),
            FieldDef("expense_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "expense_date <= claim submit_date", "Date expense was incurred."),
            FieldDef("category", "string", "VARCHAR(32)", True, False, None, ["TRAVEL", "LODGING", "MEALS", "CLIENT_ENTERTAINMENT", "SOFTWARE", "EQUIPMENT", "TRAINING", "MISC"], None, False, "Enum category", "Expense category."),
            FieldDef("description", "string", "VARCHAR(255)", True, False, None, None, None, False, "Non-empty string", "Itemized purchase narrative."),
            FieldDef("amount_local", "float", "NUMERIC(10,2)", True, False, None, None, "local currency", False, "amount_local > 0.0", "Incurred amount in vendor currency."),
            FieldDef("currency", "string", "VARCHAR(3)", True, False, None, ["USD", "INR", "GBP", "EUR", "SGD"], "ISO 4217", False, "Currency enum", "Transaction currency."),
            FieldDef("exchange_rate_to_base", "float", "NUMERIC(8,4)", True, False, None, None, "rate", False, "rate > 0.0", "Fixed currency conversion rate to USD."),
            FieldDef("amount_base", "float", "NUMERIC(10,2)", True, False, None, None, "USD", False, "amount_local * exchange_rate", "Converted value in USD."),
            FieldDef("merchant_name", "string", "VARCHAR(128)", True, False, None, None, None, False, "Non-empty string", "Vendor / merchant name."),
            FieldDef("receipt_id", "string", "VARCHAR(32)", False, False, None, None, None, False, "Regex ^RCP-\\d{6}$ or empty", "Embedded receipt identifier."),
            FieldDef("receipt_hash", "string", "VARCHAR(64)", False, False, None, None, "SHA-256 hex", False, "64 hex chars or empty", "Deterministic SHA-256 hash of receipt metadata."),
            FieldDef("receipt_date", "date", "DATE", False, False, None, None, "YYYY-MM-DD", False, "Valid date or empty", "Date stamped on physical receipt."),
            FieldDef("has_receipt", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Receipt presence flag."),
            FieldDef("file_name", "string", "VARCHAR(128)", False, False, None, None, None, False, "Filename or empty", "Synthetic receipt scan filename."),
            FieldDef("is_disallowed", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Flag if disallowed by auditor/approver."),
        ],
    ),
    TableDef(
        name="expense_claim_event",
        category="Event",
        description="Immutable lifecycle audit log for expense claim state changes.",
        id_prefix="EXPV-",
        id_pattern=r"^EXPV-\d{6}$",
        fields=[
            FieldDef("event_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^EXPV-\\d{6}$", "Unique expense transition event identifier."),
            FieldDef("claim_id", "string", "VARCHAR(32)", True, False, "expense_claim.claim_id", None, None, False, "FK to ExpenseClaim", "Subject claim."),
            FieldDef("from_status", "string", "VARCHAR(32)", True, False, None, None, None, False, "Valid status", "Previous claim status."),
            FieldDef("to_status", "string", "VARCHAR(32)", True, False, None, None, None, False, "Valid status", "New claim status."),
            FieldDef("actor_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Acting employee/system ID."),
            FieldDef("timestamp", "timestamp", "TIMESTAMP", True, False, None, None, "ISO 8601", False, "Timestamp", "Transition timestamp."),
            FieldDef("reason_code", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty code", "Lifecycle reason code."),
            FieldDef("comment", "string", "VARCHAR(255)", False, False, None, None, None, False, "Text", "Reviewer/system remarks."),
        ],
    ),
    TableDef(
        name="approval_rule",
        category="Core",
        description="Configurable business rules defining required authority, tier thresholds, and approval steps.",
        id_prefix="ARUL-",
        id_pattern=r"^ARUL-\d{2}$",
        fields=[
            FieldDef("rule_id", "string", "VARCHAR(16)", True, True, None, None, None, True, "Regex ^ARUL-\\d{2}$", "Unique approval rule identifier."),
            FieldDef("rule_code", "string", "VARCHAR(32)", True, False, None, None, None, True, "Unique rule code", "Standard mnemonic rule code."),
            FieldDef("name", "string", "VARCHAR(128)", True, False, None, None, None, False, "Non-empty string", "Rule title."),
            FieldDef("entity_type", "string", "VARCHAR(16)", True, False, None, ["LEAVE", "EXPENSE"], None, False, "LEAVE or EXPENSE", "Target business domain."),
            FieldDef("min_amount", "float", "NUMERIC(12,2)", True, False, None, None, "USD", False, "min_amount >= 0.0", "Minimum threshold in USD."),
            FieldDef("max_amount", "float", "NUMERIC(12,2)", True, False, None, None, "USD", False, "max_amount >= min_amount", "Upper threshold ceiling in USD."),
            FieldDef("min_duration_days", "integer", "INTEGER", True, False, None, None, "days", False, "days >= 0", "Minimum leave duration for rule applicability."),
            FieldDef("max_duration_days", "integer", "INTEGER", True, False, None, None, "days", False, "days >= min_duration_days", "Maximum leave duration."),
            FieldDef("required_role", "string", "VARCHAR(32)", True, False, None, ["MANAGER", "DIRECTOR", "VP", "FINANCE", "HR", "CFO"], None, False, "Enum role", "Organizational role required to approve."),
            FieldDef("min_approver_level", "integer", "INTEGER", True, False, None, ["1", "2", "3", "4", "5", "6"], "Level", False, "Integer 1-6", "Minimum job level required."),
            FieldDef("step_number", "integer", "INTEGER", True, False, None, ["1", "2", "3", "4"], "Step", False, "Integer 1-4", "Sequential step index in multi-level workflow."),
            FieldDef("description", "string", "VARCHAR(255)", True, False, None, None, None, False, "Text", "Rule explanation."),
        ],
    ),
    TableDef(
        name="approval_rule_category",
        category="Bridge",
        description="N:M bridge linking ApprovalRules to applicable expense categories.",
        id_prefix="ARC-",
        id_pattern=r"^ARC-\d{6}$",
        fields=[
            FieldDef("rule_category_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^ARC-\\d{6}$", "Bridge record ID."),
            FieldDef("rule_id", "string", "VARCHAR(16)", True, False, "approval_rule.rule_id", None, None, False, "FK to ApprovalRule", "Target approval rule."),
            FieldDef("category", "string", "VARCHAR(32)", True, False, None, ["ALL", "TRAVEL", "LODGING", "MEALS", "CLIENT_ENTERTAINMENT", "SOFTWARE", "EQUIPMENT", "TRAINING", "MISC"], None, False, "Expense category or ALL", "Scoped expense category."),
        ],
    ),
    TableDef(
        name="approval_rule_country",
        category="Bridge",
        description="N:M bridge linking ApprovalRules to applicable employee country jurisdictions.",
        id_prefix="ARCTRY-",
        id_pattern=r"^ARCTRY-\d{6}$",
        fields=[
            FieldDef("rule_country_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^ARCTRY-\\d{6}$", "Bridge record ID."),
            FieldDef("rule_id", "string", "VARCHAR(16)", True, False, "approval_rule.rule_id", None, None, False, "FK to ApprovalRule", "Target approval rule."),
            FieldDef("country", "string", "VARCHAR(8)", True, False, None, ["ALL", "IN", "US", "UK", "DE", "SG"], None, False, "Country code or ALL", "Scoped country jurisdiction."),
        ],
    ),
    TableDef(
        name="approval_step",
        category="Core",
        description="Materialized approval step recording individual approver decision, timestamp, and audit trail.",
        id_prefix="APR-",
        id_pattern=r"^APR-(LVE-2026-\d{6}|EXP-2026-\d{6})-\d{2}$",
        fields=[
            FieldDef("step_id", "string", "VARCHAR(64)", True, True, None, None, None, True, "Regex ^APR-(LVE|EXP)...-\\d{2}$", "Unique approval step identifier."),
            FieldDef("request_id", "string", "VARCHAR(32)", True, False, None, None, None, False, "FK to LeaveRequest or ExpenseClaim", "Subject request or claim identifier."),
            FieldDef("step_number", "integer", "INTEGER", True, False, None, ["1", "2", "3", "4"], "Step", False, "Integer 1-4", "Sequential sequence number."),
            FieldDef("rule_id", "string", "VARCHAR(16)", True, False, "approval_rule.rule_id", None, None, False, "FK to ApprovalRule", "Enforced rule."),
            FieldDef("approver_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Assigned approver employee ID."),
            FieldDef("level", "integer", "INTEGER", True, False, None, ["1", "2", "3", "4", "5", "6"], "Level", False, "Integer 1-6", "Approver hierarchy level."),
            FieldDef("due_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Valid date", "Target completion deadline."),
            FieldDef("status", "string", "VARCHAR(16)", True, False, None, ["PENDING", "APPROVED", "REJECTED", "SKIPPED", "ESCALATED"], None, False, "Enum status", "Step lifecycle status."),
            FieldDef("decided_at", "timestamp", "TIMESTAMP", False, False, None, None, "ISO 8601", False, "Timestamp or empty", "Decision execution timestamp."),
            FieldDef("decision", "string", "VARCHAR(16)", True, False, None, ["APPROVE", "REJECT", "ESCALATE", "SKIP", "PENDING"], None, False, "Enum decision", "Action rendered."),
            FieldDef("reason_code", "string", "VARCHAR(64)", True, False, None, None, None, False, "Non-empty code", "Structured decision reason code."),
            FieldDef("comment", "string", "VARCHAR(255)", False, False, None, None, None, False, "Text", "Approver rationale comment."),
        ],
    ),
    TableDef(
        name="employee_cost_center_assignment",
        category="Bridge",
        description="Historical and current mapping of employees to cost centers with effective date bounds.",
        id_prefix="ECCA-",
        id_pattern=r"^ECCA-\d{6}$",
        fields=[
            FieldDef("assignment_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^ECCA-\\d{6}$", "Unique assignment identifier."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Assigned employee."),
            FieldDef("cost_center_id", "string", "VARCHAR(32)", True, False, "cost_center.cost_center_id", None, None, False, "FK to CostCenter", "Assigned cost center."),
            FieldDef("allocation_percentage", "float", "NUMERIC(5,2)", True, False, None, None, "percentage", False, "Between 1.0 and 100.0", "Budget allocation weight."),
            FieldDef("effective_from", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "Date format", "Start of assignment window."),
            FieldDef("effective_to", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "effective_to >= effective_from", "End of assignment window."),
            FieldDef("is_primary", "boolean", "BOOLEAN", True, False, None, ["0", "1", "true", "false"], "Boolean", False, "0 or 1", "Primary cost center flag."),
        ],
    ),
    TableDef(
        name="decision_log",
        category="Audit",
        description="Exhaustive decision audit log capturing reason codes, applied rules, and inputs snapshots.",
        id_prefix="DEC-",
        id_pattern=r"^DEC-\d{6}$",
        fields=[
            FieldDef("decision_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^DEC-\\d{6}$", "Unique decision audit identifier."),
            FieldDef("subject_id", "string", "VARCHAR(32)", True, False, None, None, None, False, "LVE or EXP ID", "Target leave request or expense claim ID."),
            FieldDef("decision", "string", "VARCHAR(32)", True, False, None, ["APPROVE", "REJECT", "ESCALATE", "RETURN_FOR_INFO", "AUTO_APPROVED"], None, False, "Enum decision", "Final rendered verdict."),
            FieldDef("reason_code", "string", "VARCHAR(64)", True, False, None, None, None, False, "Structured code", "Standardized decision reason code."),
            FieldDef("reason_text", "string", "VARCHAR(255)", True, False, None, None, None, False, "Human readable explanation", "Explanatory decision narrative."),
            FieldDef("rule_id", "string", "VARCHAR(32)", True, False, None, None, None, False, "Rule identifier", "Triggering policy or approval rule ID."),
            FieldDef("inputs_snapshot_json", "json", "TEXT", True, False, None, None, "JSON", False, "Valid JSON string", "Serialized snapshot of input parameters evaluated."),
            FieldDef("timestamp", "timestamp", "TIMESTAMP", True, False, None, None, "ISO 8601", False, "Timestamp", "Audit logging timestamp."),
        ],
    ),
    TableDef(
        name="reimbursement",
        category="Core",
        description="Disbursement records issued exclusively for fully approved, eligible expense claims.",
        id_prefix="RMB-2026-",
        id_pattern=r"^RMB-2026-\d{6}$",
        fields=[
            FieldDef("reimbursement_id", "string", "VARCHAR(32)", True, True, None, None, None, True, "Regex ^RMB-2026-\\d{6}$", "Unique reimbursement payment identifier."),
            FieldDef("claim_id", "string", "VARCHAR(32)", True, False, "expense_claim.claim_id", None, None, False, "FK to ExpenseClaim", "Parent approved expense claim ID."),
            FieldDef("employee_id", "string", "VARCHAR(32)", True, False, "employee.employee_id", None, None, False, "FK to Employee", "Payee employee ID."),
            FieldDef("payment_method", "string", "VARCHAR(32)", True, False, None, ["DIRECT_DEPOSIT", "WIRE_TRANSFER", "PAYROLL"], None, False, "Enum payment_method", "Treasury disbursement channel."),
            FieldDef("currency", "string", "VARCHAR(3)", True, False, None, ["USD", "INR", "GBP", "EUR", "SGD"], "ISO 4217", False, "Currency enum", "Disbursement currency."),
            FieldDef("amount", "float", "NUMERIC(12,2)", True, False, None, None, "Currency", False, "amount > 0.0", "Total disbursed amount (sum of approved lines)."),
            FieldDef("payment_date", "date", "DATE", True, False, None, None, "YYYY-MM-DD", False, "payment_date >= approval date", "Date payment was executed."),
            FieldDef("transaction_reference", "string", "VARCHAR(64)", True, False, None, None, None, True, "Regex ^TXN-\\d{8}$", "Bank transaction reference number."),
            FieldDef("status", "string", "VARCHAR(16)", True, False, None, ["PROCESSED", "PENDING", "FAILED"], None, False, "Enum status", "Disbursement processing status."),
        ],
    ),
]

SCHEMA_RELATIONSHIPS: List[RelationshipDef] = [
    RelationshipDef("cost_center", "employee", "cost_center_id", "1:N", False, False, "Cost center allocates primary budget to multiple employees."),
    RelationshipDef("employee", "cost_center", "manager_id", "1:N", False, False, "Employee manages cost centers."),
    RelationshipDef("employee", "employee", "manager_id", "1:N", True, False, "Self-referential supervisory reporting hierarchy (CEO has no manager)."),
    RelationshipDef("employee", "employee_cost_center_assignment", "employee_id", "1:N", False, True, "Historical cost center assignments over time."),
    RelationshipDef("cost_center", "employee_cost_center_assignment", "cost_center_id", "1:N", False, True, "Cost center assignment bridge."),
    RelationshipDef("employee", "leave_balance_ledger", "employee_id", "1:N", False, False, "Ledger accruals and usages per employee."),
    RelationshipDef("leave_policy", "leave_balance_ledger", "policy_id", "1:N", False, False, "Ledger postings governed by leave policy."),
    RelationshipDef("employee", "leave_balance", "employee_id", "1:N", False, False, "Materialized balance snapshots per employee."),
    RelationshipDef("leave_policy", "leave_balance", "policy_id", "1:N", False, False, "Materialized balance snapshots per policy."),
    RelationshipDef("employee", "leave_request", "employee_id", "1:N", False, False, "Employee files multiple leave requests."),
    RelationshipDef("leave_policy", "leave_request", "policy_id", "1:N", False, False, "Leave requests filed against specific policy."),
    RelationshipDef("leave_request", "leave_request_event", "request_id", "1:N", False, False, "Append-only lifecycle events per leave request."),
    RelationshipDef("employee", "leave_request_event", "actor_id", "1:N", False, False, "Employee acting on leave request transition."),
    RelationshipDef("expense_policy", "expense_claim", "policy_id", "1:N", False, False, "Expense claim governed by expense policy."),
    RelationshipDef("employee", "expense_claim", "employee_id", "1:N", False, False, "Employee files multiple expense claims."),
    RelationshipDef("cost_center", "expense_claim", "cost_center_id", "1:N", False, False, "Expense claim charged to cost center."),
    RelationshipDef("expense_claim", "expense_line", "claim_id", "1:N", False, False, "Expense claim contains 1 to 10 expense lines."),
    RelationshipDef("expense_claim", "expense_claim_event", "claim_id", "1:N", False, False, "Append-only lifecycle events per expense claim."),
    RelationshipDef("employee", "expense_claim_event", "actor_id", "1:N", False, False, "Employee acting on expense claim transition."),
    RelationshipDef("approval_rule", "approval_rule_category", "rule_id", "1:N", False, False, "Approval rule mapped to expense categories (N:M via bridge)."),
    RelationshipDef("approval_rule", "approval_rule_country", "rule_id", "1:N", False, False, "Approval rule mapped to countries (N:M via bridge)."),
    RelationshipDef("approval_rule", "approval_step", "rule_id", "1:N", False, False, "Approval steps instantiated from approval rules."),
    RelationshipDef("employee", "approval_step", "approver_id", "1:N", False, False, "Employee assigned as approver on step."),
    RelationshipDef("expense_claim", "reimbursement", "claim_id", "1:1", True, False, "Approved expense claim yields exactly one reimbursement (1:1 baseline)."),
    RelationshipDef("employee", "reimbursement", "employee_id", "1:N", False, False, "Reimbursement disbursements to employee."),
]

TABLES_BY_NAME: Dict[str, TableDef] = {t.name: t for t in SCHEMA_TABLES}


def generate_data_dictionary_md() -> str:
    """Generate comprehensive Markdown documentation for all entities, fields, relationships, and lifecycles."""
    lines: List[str] = [
        "# YottaGen Data Dictionary & Schema Specification",
        "",
        "> **Notice**: Generated deterministically from `yottagen/schema.py` (Single Source of Truth).",
        "> Code, SQL DDL, and documentation are guaranteed strictly synchronized.",
        "",
        "## 1. Entity Overview & Cardinality",
        "",
        "| Entity / Table | Category | Description | Primary Key | ID Pattern |",
        "|---|---|---|---|---|",
    ]
    for table in SCHEMA_TABLES:
        pk_field = next((f.name for f in table.fields if f.pk), "None")
        lines.append(f"| `{table.name}` | {table.category} | {table.description} | `{pk_field}` | `{table.id_pattern}` |")

    lines.extend([
        "",
        "## 2. Entity Relationships & Cardinality Matrix",
        "",
        "| Parent Entity | Child Entity | Foreign Key | Cardinality | Optional | Effective Dates | Description |",
        "|---|---|---|---|---|---|---|",
    ])
    for rel in SCHEMA_RELATIONSHIPS:
        lines.append(f"| `{rel.parent_table}` | `{rel.child_table}` | `{rel.fk_field}` | {rel.cardinality} | {'Yes' if rel.is_optional else 'No'} | {'Yes' if rel.has_effective_dates else 'No'} | {rel.description} |")

    lines.extend([
        "",
        "## 3. Entity Lifecycle State Machines",
        "",
        "### 3.1 LeaveRequest Lifecycle",
        "```",
        "  [DRAFT] ---------> [SUBMITTED] ---------> [PENDING_APPROVAL] ---------> [APPROVED] ---------> [CONSUMED]",
        "     |                   |                         |                         |",
        "     +-> [CANCELLED]     +-> [CANCELLED]           +-> [REJECTED]            +-> [CANCELLED]",
        "                                                   |",
        "                                                   +-> [CANCELLED]",
        "```",
        "- **Permitted Transitions**:",
    ])
    for src, dsts in sorted(LEAVE_REQUEST_TRANSITIONS.items()):
        dst_str = ", ".join(f"`{d}`" for d in sorted(dsts)) if dsts else "*Terminal State*"
        lines.append(f"  - `{src}` &rarr; {dst_str}")

    lines.extend([
        "",
        "### 3.2 ExpenseClaim Lifecycle",
        "```",
        "  [DRAFT] ---------> [SUBMITTED] ---------> [PENDING_APPROVAL] ---------> [APPROVED] ---------> [REIMBURSED]",
        "     |                                             |",
        "     +-> [REJECTED]                                +-> [REJECTED]",
        "                                                   |",
        "                                                   +-> [RETURNED_FOR_INFO] --(resubmit)--> [SUBMITTED]",
        "```",
        "- **Permitted Transitions**:",
    ])
    for src, dsts in sorted(EXPENSE_CLAIM_TRANSITIONS.items()):
        dst_str = ", ".join(f"`{d}`" for d in sorted(dsts)) if dsts else "*Terminal State*"
        lines.append(f"  - `{src}` &rarr; {dst_str}")

    lines.extend([
        "",
        "### 3.3 ApprovalStep Lifecycle",
        "- **Permitted Transitions**:",
    ])
    for src, dsts in sorted(APPROVAL_STEP_TRANSITIONS.items()):
        dst_str = ", ".join(f"`{d}`" for d in sorted(dsts)) if dsts else "*Terminal State*"
        lines.append(f"  - `{src}` &rarr; {dst_str}")

    lines.extend([
        "",
        "## 4. Comprehensive Field Specifications",
        "",
    ])

    for table in SCHEMA_TABLES:
        lines.extend([
            f"### Table: `{table.name}`",
            f"*{table.description}* (Category: **{table.category}**, ID Prefix: `{table.id_prefix}`)",
            "",
            "| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ])
        for f in table.fields:
            fk_str = f"`{f.fk}`" if f.fk else "-"
            enums_str = f"`{', '.join(f.allowed_values[:5])}{'...' if len(f.allowed_values) > 5 else ''}`" if f.allowed_values else "-"
            units_str = f.units if f.units else "-"
            lines.append(
                f"| `{f.name}` | {f.field_type} | `{f.sql_type}` | {'Yes' if f.required else 'No'} | {'PK' if f.pk else '-'} | {fk_str} | {enums_str} | {units_str} | {'Yes' if f.uniqueness else '-'} | {f.validation_rule} | {f.description} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def generate_data_dictionary_csv() -> str:
    """Generate CSV version of data dictionary."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "table_name",
        "table_category",
        "field_name",
        "field_type",
        "sql_type",
        "is_required",
        "is_pk",
        "fk_reference",
        "allowed_values",
        "units",
        "is_unique",
        "validation_rule",
        "description",
    ])
    for table in SCHEMA_TABLES:
        for f in table.fields:
            writer.writerow([
                table.name,
                table.category,
                f.name,
                f.field_type,
                f.sql_type,
                f.required,
                f.pk,
                f.fk or "",
                ";".join(f.allowed_values) if f.allowed_values else "",
                f.units or "",
                f.uniqueness,
                f.validation_rule,
                f.description,
            ])
    return output.getvalue()


def generate_data_dictionary_json() -> str:
    """Generate JSON representation of the entire schema specification."""
    data = {
        "version": "1.0.0",
        "tables": [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "id_prefix": t.id_prefix,
                "id_pattern": t.id_pattern,
                "fields": [asdict(f) for f in t.fields],
            }
            for t in SCHEMA_TABLES
        ],
        "relationships": [asdict(r) for r in SCHEMA_RELATIONSHIPS],
        "lifecycles": {
            "leave_request": {k: sorted(list(v)) for k, v in LEAVE_REQUEST_TRANSITIONS.items()},
            "expense_claim": {k: sorted(list(v)) for k, v in EXPENSE_CLAIM_TRANSITIONS.items()},
            "approval_step": {k: sorted(list(v)) for k, v in APPROVAL_STEP_TRANSITIONS.items()},
        },
    }
    return json.dumps(data, indent=2) + "\n"


def generate_sql_ddl() -> str:
    """Generate clean SQLite-compatible SQL DDL CREATE TABLE statements with primary keys, foreign keys, and indexes."""
    lines: List[str] = [
        "-- ============================================================================",
        "-- YottaGen Schema DDL (Generated from yottagen/schema.py)",
        "-- ============================================================================",
        "PRAGMA foreign_keys = ON;",
        "",
    ]

    for table in SCHEMA_TABLES:
        lines.append(f"-- Table: {table.name} ({table.category})")
        lines.append(f"CREATE TABLE IF NOT EXISTS {table.name} (")
        col_defs = []
        for f in table.fields:
            clause = f"    {f.name} {f.sql_type}"
            if f.pk:
                clause += " PRIMARY KEY"
            elif f.required:
                clause += " NOT NULL"
            if f.uniqueness and not f.pk:
                clause += " UNIQUE"
            col_defs.append(clause)

        # Foreign key clauses
        for f in table.fields:
            if f.fk:
                target_table, target_col = f.fk.split(".")
                col_defs.append(f"    FOREIGN KEY ({f.name}) REFERENCES {target_table}({target_col})")

        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("")

        # Indexes for foreign keys and common query lookups
        for f in table.fields:
            if f.fk:
                idx_name = f"idx_{table.name}_{f.name}"
                lines.append(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table.name}({f.name});")
        lines.append("")

    return "\n".join(lines)


def export_documentation(output_dir: str = "docs") -> None:
    """Write docs/data_dictionary.md, .csv, and .json."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "data_dictionary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(generate_data_dictionary_md())
    with open(os.path.join(output_dir, "data_dictionary.csv"), "w", encoding="utf-8", newline="\n") as f:
        f.write(generate_data_dictionary_csv())
    with open(os.path.join(output_dir, "data_dictionary.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(generate_data_dictionary_json())
