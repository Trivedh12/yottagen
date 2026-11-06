# YottaGen Data Dictionary & Schema Specification

> **Notice**: Generated deterministically from `yottagen/schema.py` (Single Source of Truth).
> Code, SQL DDL, and documentation are guaranteed strictly synchronized.

## 1. Entity Overview & Cardinality

| Entity / Table | Category | Description | Primary Key | ID Pattern |
|---|---|---|---|---|
| `cost_center` | Core | Operational cost centers for budgeting and organizational financial allocation. | `cost_center_id` | `^CC-\d{3,6}$` |
| `employee` | Core | Comprehensive employee record including organizational hierarchy, geography, and authority. | `employee_id` | `^EMP-\d{6}$` |
| `holiday_calendar` | Supporting | Statutory and public holidays by country used for business-day computations. | `holiday_id` | `^HOL-\d{6}$` |
| `leave_policy` | Core | Formal leave policy governing accrual, entitlements, notice periods, and limits. | `policy_id` | `^LPOL-\d{2}$` |
| `leave_balance_ledger` | Supporting | Immutable, append-only journal of all leave accrual, consumption, and adjustment events. | `ledger_id` | `^LBLED-\d{6}$` |
| `leave_balance` | Core | Point-in-time materialized balance derived purely from the leave ledger. | `balance_id` | `^LBAL-\d{6}$` |
| `leave_request` | Core | Formal leave application submitted by an employee with calendar and business duration metrics. | `request_id` | `^LVE-2026-\d{6}$` |
| `leave_request_event` | Event | Immutable audit trail of state transitions for each leave application. | `event_id` | `^LVEV-\d{6}$` |
| `expense_policy` | Core | Corporate travel and business expense policy rules and threshold ceilings. | `policy_id` | `^EPOL-\d{2}$` |
| `expense_claim` | Core | Expense claim header aggregating line items with cost center allocation and derived amounts. | `claim_id` | `^EXP-2026-\d{6}$` |
| `expense_line` | Core | Granular expense item including currency conversion and embedded cryptographic receipt metadata. | `line_id` | `^EXPL-EXP-2026-\d{6}-\d{2}$` |
| `expense_claim_event` | Event | Immutable lifecycle audit log for expense claim state changes. | `event_id` | `^EXPV-\d{6}$` |
| `approval_rule` | Core | Configurable business rules defining required authority, tier thresholds, and approval steps. | `rule_id` | `^ARUL-\d{2}$` |
| `approval_rule_category` | Bridge | N:M bridge linking ApprovalRules to applicable expense categories. | `rule_category_id` | `^ARC-\d{6}$` |
| `approval_rule_country` | Bridge | N:M bridge linking ApprovalRules to applicable employee country jurisdictions. | `rule_country_id` | `^ARCTRY-\d{6}$` |
| `approval_step` | Core | Materialized approval step recording individual approver decision, timestamp, and audit trail. | `step_id` | `^APR-(LVE-2026-\d{6}|EXP-2026-\d{6})-\d{2}$` |
| `employee_cost_center_assignment` | Bridge | Historical and current mapping of employees to cost centers with effective date bounds. | `assignment_id` | `^ECCA-\d{6}$` |
| `decision_log` | Audit | Exhaustive decision audit log capturing reason codes, applied rules, and inputs snapshots. | `decision_id` | `^DEC-\d{6}$` |
| `reimbursement` | Core | Disbursement records issued exclusively for fully approved, eligible expense claims. | `reimbursement_id` | `^RMB-2026-\d{6}$` |

## 2. Entity Relationships & Cardinality Matrix

| Parent Entity | Child Entity | Foreign Key | Cardinality | Optional | Effective Dates | Description |
|---|---|---|---|---|---|---|
| `cost_center` | `employee` | `cost_center_id` | 1:N | No | No | Cost center allocates primary budget to multiple employees. |
| `employee` | `cost_center` | `manager_id` | 1:N | No | No | Employee manages cost centers. |
| `employee` | `employee` | `manager_id` | 1:N | Yes | No | Self-referential supervisory reporting hierarchy (CEO has no manager). |
| `employee` | `employee_cost_center_assignment` | `employee_id` | 1:N | No | Yes | Historical cost center assignments over time. |
| `cost_center` | `employee_cost_center_assignment` | `cost_center_id` | 1:N | No | Yes | Cost center assignment bridge. |
| `employee` | `leave_balance_ledger` | `employee_id` | 1:N | No | No | Ledger accruals and usages per employee. |
| `leave_policy` | `leave_balance_ledger` | `policy_id` | 1:N | No | No | Ledger postings governed by leave policy. |
| `employee` | `leave_balance` | `employee_id` | 1:N | No | No | Materialized balance snapshots per employee. |
| `leave_policy` | `leave_balance` | `policy_id` | 1:N | No | No | Materialized balance snapshots per policy. |
| `employee` | `leave_request` | `employee_id` | 1:N | No | No | Employee files multiple leave requests. |
| `leave_policy` | `leave_request` | `policy_id` | 1:N | No | No | Leave requests filed against specific policy. |
| `leave_request` | `leave_request_event` | `request_id` | 1:N | No | No | Append-only lifecycle events per leave request. |
| `employee` | `leave_request_event` | `actor_id` | 1:N | No | No | Employee acting on leave request transition. |
| `expense_policy` | `expense_claim` | `policy_id` | 1:N | No | No | Expense claim governed by expense policy. |
| `employee` | `expense_claim` | `employee_id` | 1:N | No | No | Employee files multiple expense claims. |
| `cost_center` | `expense_claim` | `cost_center_id` | 1:N | No | No | Expense claim charged to cost center. |
| `expense_claim` | `expense_line` | `claim_id` | 1:N | No | No | Expense claim contains 1 to 10 expense lines. |
| `expense_claim` | `expense_claim_event` | `claim_id` | 1:N | No | No | Append-only lifecycle events per expense claim. |
| `employee` | `expense_claim_event` | `actor_id` | 1:N | No | No | Employee acting on expense claim transition. |
| `approval_rule` | `approval_rule_category` | `rule_id` | 1:N | No | No | Approval rule mapped to expense categories (N:M via bridge). |
| `approval_rule` | `approval_rule_country` | `rule_id` | 1:N | No | No | Approval rule mapped to countries (N:M via bridge). |
| `approval_rule` | `approval_step` | `rule_id` | 1:N | No | No | Approval steps instantiated from approval rules. |
| `employee` | `approval_step` | `approver_id` | 1:N | No | No | Employee assigned as approver on step. |
| `expense_claim` | `reimbursement` | `claim_id` | 1:1 | Yes | No | Approved expense claim yields exactly one reimbursement (1:1 baseline). |
| `employee` | `reimbursement` | `employee_id` | 1:N | No | No | Reimbursement disbursements to employee. |

## 3. Entity Lifecycle State Machines

### 3.1 LeaveRequest Lifecycle
```
  [DRAFT] ---------> [SUBMITTED] ---------> [PENDING_APPROVAL] ---------> [APPROVED] ---------> [CONSUMED]
     |                   |                         |                         |
     +-> [CANCELLED]     +-> [CANCELLED]           +-> [REJECTED]            +-> [CANCELLED]
                                                   |
                                                   +-> [CANCELLED]
```
- **Permitted Transitions**:
  - `APPROVED` &rarr; `CANCELLED`, `CONSUMED`
  - `CANCELLED` &rarr; *Terminal State*
  - `CONSUMED` &rarr; *Terminal State*
  - `DRAFT` &rarr; `CANCELLED`, `SUBMITTED`
  - `PENDING_APPROVAL` &rarr; `APPROVED`, `CANCELLED`, `REJECTED`
  - `REJECTED` &rarr; *Terminal State*
  - `SUBMITTED` &rarr; `CANCELLED`, `PENDING_APPROVAL`, `REJECTED`

### 3.2 ExpenseClaim Lifecycle
```
  [DRAFT] ---------> [SUBMITTED] ---------> [PENDING_APPROVAL] ---------> [APPROVED] ---------> [REIMBURSED]
     |                                             |
     +-> [REJECTED]                                +-> [REJECTED]
                                                   |
                                                   +-> [RETURNED_FOR_INFO] --(resubmit)--> [SUBMITTED]
```
- **Permitted Transitions**:
  - `APPROVED` &rarr; `REIMBURSED`
  - `DRAFT` &rarr; `REJECTED`, `SUBMITTED`
  - `PENDING_APPROVAL` &rarr; `APPROVED`, `REJECTED`, `RETURNED_FOR_INFO`
  - `REIMBURSED` &rarr; *Terminal State*
  - `REJECTED` &rarr; *Terminal State*
  - `RETURNED_FOR_INFO` &rarr; `REJECTED`, `SUBMITTED`
  - `SUBMITTED` &rarr; `PENDING_APPROVAL`, `REJECTED`

### 3.3 ApprovalStep Lifecycle
- **Permitted Transitions**:
  - `APPROVED` &rarr; *Terminal State*
  - `ESCALATED` &rarr; `APPROVED`, `REJECTED`
  - `PENDING` &rarr; `APPROVED`, `ESCALATED`, `REJECTED`, `SKIPPED`
  - `REJECTED` &rarr; *Terminal State*
  - `SKIPPED` &rarr; *Terminal State*

## 4. Comprehensive Field Specifications

### Table: `cost_center`
*Operational cost centers for budgeting and organizational financial allocation.* (Category: **Core**, ID Prefix: `CC-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `cost_center_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^CC-\d{3,6}$ | Unique cost center identifier. |
| `code` | string | `VARCHAR(32)` | Yes | - | - | `ENG, SALES, MKT, GNA, PROD...` | - | Yes | Upper alphanumeric code | Cost center functional code. |
| `name` | string | `VARCHAR(128)` | Yes | - | - | - | - | - | Non-empty string | Human readable cost center department name. |
| `department` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty string | Department grouping. |
| `manager_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Cost center owner/approver employee ID. |
| `budget_currency` | string | `VARCHAR(3)` | Yes | - | - | `USD` | ISO 4217 | - | Currency code USD | Budget currency denomination. |
| `annual_budget` | float | `NUMERIC(14,2)` | Yes | - | - | - | USD | - | Value >= 0.0 | Approved annual budget allocation. |
| `status` | string | `VARCHAR(16)` | Yes | - | - | `ACTIVE, INACTIVE` | - | - | Enum ACTIVE, INACTIVE | Operational status. |

### Table: `employee`
*Comprehensive employee record including organizational hierarchy, geography, and authority.* (Category: **Core**, ID Prefix: `EMP-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `employee_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^EMP-\d{6}$ | Unique employee identifier. |
| `first_name` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty string | Synthetic first name. |
| `last_name` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty string | Synthetic last name. |
| `email` | string | `VARCHAR(128)` | Yes | - | - | - | - | Yes | Ends with @example.com | Synthetic corporate email address. |
| `country` | string | `VARCHAR(2)` | Yes | - | - | `IN, US, UK, DE, SG` | ISO 3166-1 | - | Enum IN, US, UK, DE, SG | Primary country of employment. |
| `city` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty string | Work location city. |
| `hire_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date <= as_of_date | Official date of hire. |
| `termination_date` | date | `DATE` | No | - | - | - | YYYY-MM-DD | - | Date >= hire_date or empty | Termination date if separated. |
| `status` | string | `VARCHAR(16)` | Yes | - | - | `ACTIVE, TERMINATED, ON_LEAVE` | - | - | Enum status | Employment status. |
| `employee_type` | string | `VARCHAR(16)` | Yes | - | - | `FULL_TIME, CONTRACT` | - | - | Enum employee_type | Worker classification. |
| `job_level` | integer | `INTEGER` | Yes | - | - | `1, 2, 3, 4, 5...` | Level 1-6 | - | Integer 1 to 6 | Hierarchy level (1=IC, 6=CEO). |
| `job_title` | string | `VARCHAR(128)` | Yes | - | - | - | - | - | Non-empty string | Role title. |
| `grade` | string | `VARCHAR(8)` | Yes | - | - | `L1, L2, L3, L4, L5...` | - | - | Enum L1-L6 | Compensation/authority grade. |
| `manager_id` | string | `VARCHAR(32)` | No | - | `employee.employee_id` | - | - | - | FK to Employee self or empty for CEO | Direct manager employee ID. |
| `cost_center_id` | string | `VARCHAR(32)` | Yes | - | `cost_center.cost_center_id` | - | - | - | FK to CostCenter | Primary allocated cost center. |
| `is_finance_approver` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Whether employee has Finance sign-off authority. |
| `is_hr_approver` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Whether employee has HR sign-off authority. |
| `role` | string | `VARCHAR(32)` | Yes | - | - | `REQUESTER, APPROVER, PROCESS_OWNER, OPS_ANALYST, SYSTEM_ADMIN` | - | - | Enum role | Primary persona/responsibility. |

### Table: `holiday_calendar`
*Statutory and public holidays by country used for business-day computations.* (Category: **Supporting**, ID Prefix: `HOL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `holiday_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^HOL-\d{6}$ | Unique holiday calendar entry ID. |
| `country` | string | `VARCHAR(2)` | Yes | - | - | `IN, US, UK, DE, SG` | ISO 3166-1 | - | Enum country | Country code. |
| `holiday_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Valid date | Calendar date of the holiday. |
| `holiday_name` | string | `VARCHAR(128)` | Yes | - | - | - | - | - | Non-empty string | Official holiday name. |
| `is_half_day` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Whether the holiday counts as a half working day. |

### Table: `leave_policy`
*Formal leave policy governing accrual, entitlements, notice periods, and limits.* (Category: **Core**, ID Prefix: `LPOL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `policy_id` | string | `VARCHAR(16)` | Yes | PK | - | - | - | Yes | Regex ^LPOL-\d{2}$ | Unique leave policy identifier. |
| `policy_name` | string | `VARCHAR(64)` | Yes | - | - | `Annual, Sick, Casual, Parental, Unpaid...` | - | Yes | Enum policy_name | Name of leave category. |
| `description` | string | `VARCHAR(255)` | Yes | - | - | - | - | - | Non-empty string | Summary of policy terms. |
| `country_scope` | string | `VARCHAR(8)` | Yes | - | - | `ALL, IN, US, UK, DE...` | - | - | Country scope or ALL | Jurisdiction applicability. |
| `accrual_days_per_month` | float | `NUMERIC(5,2)` | Yes | - | - | - | days/month | - | Value >= 0.0 | Monthly earned leave rate. |
| `annual_cap` | float | `NUMERIC(5,2)` | Yes | - | - | - | days/year | - | Value >= 0.0 | Maximum annual accrual entitlement. |
| `carry_forward_max` | float | `NUMERIC(5,2)` | Yes | - | - | - | days | - | Value >= 0.0 | Maximum days carried into subsequent calendar year. |
| `min_notice_days` | integer | `INTEGER` | Yes | - | - | - | days | - | Value >= 0 | Lead time required before leave commences. |
| `max_consecutive_days` | integer | `INTEGER` | Yes | - | - | - | days | - | Value > 0 | Maximum contiguous calendar/business span allowed. |
| `requires_doc_after_days` | integer | `INTEGER` | Yes | - | - | - | days | - | Value >= 0 | Consecutive days after which medical certificate is mandatory. |
| `allows_negative_balance` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Whether deficit balance is permitted. |
| `approval_levels_by_duration` | integer | `INTEGER` | Yes | - | - | `1, 2, 3` | Levels | - | 1, 2, or 3 | Default required approval depth. |
| `effective_from` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date format | Policy inception date. |
| `effective_to` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date >= effective_from | Policy sunset/expiration date. |

### Table: `leave_balance_ledger`
*Immutable, append-only journal of all leave accrual, consumption, and adjustment events.* (Category: **Supporting**, ID Prefix: `LBLED-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `ledger_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^LBLED-\d{6}$ | Unique ledger entry identifier. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Impacted employee. |
| `policy_id` | string | `VARCHAR(16)` | Yes | - | `leave_policy.policy_id` | - | - | - | FK to LeavePolicy | Governing leave policy. |
| `entry_type` | string | `VARCHAR(32)` | Yes | - | - | `ACCRUAL, USAGE, ADJUSTMENT, CARRY_FORWARD, FORFEIT` | - | - | Enum entry_type | Ledger posting type. |
| `days` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Signed float | Day delta (+ for credit, - for debit). |
| `effective_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date format | Posting valuation date. |
| `reference_id` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty string | Source request ID or SYSTEM. |
| `created_at` | timestamp | `TIMESTAMP` | Yes | - | - | - | ISO 8601 | - | Timestamp | Audit creation timestamp. |
| `notes` | string | `VARCHAR(255)` | No | - | - | - | - | - | String | Ledger narrative. |

### Table: `leave_balance`
*Point-in-time materialized balance derived purely from the leave ledger.* (Category: **Core**, ID Prefix: `LBAL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `balance_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^LBAL-\d{6}$ | Unique balance snapshot identifier. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Employee ID. |
| `policy_id` | string | `VARCHAR(16)` | Yes | - | `leave_policy.policy_id` | - | - | - | FK to LeavePolicy | Policy ID. |
| `as_of_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Reference date | Valuation date of the balance calculation. |
| `opening_balance` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Float >= 0.0 | Starting balance at period start. |
| `accrued_days` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Float >= 0.0 | Cumulative accrued days. |
| `used_days` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Float >= 0.0 | Total APPROVED leave days consumed. |
| `adjusted_days` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Signed float | Manual/statutory ledger adjustments. |
| `pending_days` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | Float >= 0.0 | Days currently tied in pending requests. |
| `closing_balance` | float | `NUMERIC(6,2)` | Yes | - | - | - | days | - | closing = opening + accrued + adjusted - used | Net available leave balance. |

### Table: `leave_request`
*Formal leave application submitted by an employee with calendar and business duration metrics.* (Category: **Core**, ID Prefix: `LVE-2026-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `request_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^LVE-2026-\d{6}$ | Unique leave request identifier. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Applicant employee ID. |
| `policy_id` | string | `VARCHAR(16)` | Yes | - | `leave_policy.policy_id` | - | - | - | FK to LeavePolicy | Requested policy ID. |
| `start_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | start_date <= end_date | First day of requested leave. |
| `end_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | end_date >= start_date | Last day of requested leave. |
| `calendar_days` | integer | `INTEGER` | Yes | - | - | - | days | - | end - start + 1 | Total elapsed calendar days. |
| `business_days` | integer | `INTEGER` | Yes | - | - | - | days | - | Excludes weekends and holidays | Net chargeable working days. |
| `weekend_days_in_span` | integer | `INTEGER` | Yes | - | - | - | days | - | Weekend count | Count of Saturdays and Sundays in interval. |
| `holiday_days_in_span` | integer | `INTEGER` | Yes | - | - | - | days | - | Holiday count | Count of official holidays in interval. |
| `submit_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | submit_date <= start_date | Submission date. |
| `status` | string | `VARCHAR(32)` | Yes | - | - | `DRAFT, SUBMITTED, PENDING_APPROVAL, APPROVED, REJECTED...` | - | - | Enum status | Current lifecycle status. |
| `reason_code` | string | `VARCHAR(32)` | Yes | - | - | `VACATION, ILLNESS, FAMILY, MATERNITY_PATERNITY, PERSONAL...` | - | - | Enum reason_code | Applicant stated rationale. |
| `comments` | string | `VARCHAR(255)` | No | - | - | - | - | - | Text | Applicant comments. |

### Table: `leave_request_event`
*Immutable audit trail of state transitions for each leave application.* (Category: **Event**, ID Prefix: `LVEV-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `event_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^LVEV-\d{6}$ | Unique leave transition event identifier. |
| `request_id` | string | `VARCHAR(32)` | Yes | - | `leave_request.request_id` | - | - | - | FK to LeaveRequest | Subject leave request. |
| `from_status` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | Valid status | Pre-transition status. |
| `to_status` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | Valid status | Post-transition status. |
| `actor_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Employee ID executing action. |
| `timestamp` | timestamp | `TIMESTAMP` | Yes | - | - | - | ISO 8601 | - | Timestamp format | Time transition occurred. |
| `reason_code` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty code | Audit reason code. |
| `comment` | string | `VARCHAR(255)` | No | - | - | - | - | - | Text | Actor comment. |

### Table: `expense_policy`
*Corporate travel and business expense policy rules and threshold ceilings.* (Category: **Core**, ID Prefix: `EPOL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `policy_id` | string | `VARCHAR(16)` | Yes | PK | - | - | - | Yes | Regex ^EPOL-\d{2}$ | Unique expense policy identifier. |
| `policy_name` | string | `VARCHAR(64)` | Yes | - | - | - | - | Yes | Non-empty string | Policy title. |
| `currency` | string | `VARCHAR(3)` | Yes | - | - | `USD` | ISO 4217 | - | USD | Reference currency. |
| `daily_meal_limit` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value > 0.0 | Per-diem meal cap per traveler. |
| `receipt_required_threshold` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value >= 0.0 | Threshold above which receipt is mandatory (e.g. 25.00). |
| `max_claim_amount` | float | `NUMERIC(12,2)` | Yes | - | - | - | USD | - | Value > 0.0 | Absolute ceiling per claim before special board escalation. |
| `entertainment_per_person_limit` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value > 0.0 | Client entertainment per-head limit. |
| `equipment_auto_approval_limit` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value >= 0.0 | IT equipment limit requiring department head signoff. |
| `lodging_daily_limit_in` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value > 0.0 | Daily lodging cap for India. |
| `lodging_daily_limit_de` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | Value > 0.0 | Daily lodging cap for Germany. |
| `effective_from` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date format | Policy inception date. |
| `effective_to` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date >= effective_from | Policy sunset date. |

### Table: `expense_claim`
*Expense claim header aggregating line items with cost center allocation and derived amounts.* (Category: **Core**, ID Prefix: `EXP-2026-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `claim_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^EXP-2026-\d{6}$ | Unique expense claim header identifier. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Claimant employee ID. |
| `cost_center_id` | string | `VARCHAR(32)` | Yes | - | `cost_center.cost_center_id` | - | - | - | FK to CostCenter | Chargeable cost center. |
| `policy_id` | string | `VARCHAR(16)` | Yes | - | `expense_policy.policy_id` | - | - | - | FK to ExpensePolicy | Governing expense policy. |
| `claim_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | claim_date <= submit_date | Date claim was assembled. |
| `submit_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | submit_date <= as_of_date | Submission date for approval. |
| `purpose` | string | `VARCHAR(255)` | Yes | - | - | - | - | - | Non-empty string | Business justification. |
| `currency` | string | `VARCHAR(3)` | Yes | - | - | `USD, INR, GBP, EUR, SGD` | ISO 4217 | - | Local currency code | Claim primary local currency. |
| `total_amount_local` | float | `NUMERIC(12,2)` | Yes | - | - | - | local currency | - | Sum of line amount_local | Total claim amount in local currency. |
| `total_amount_base` | float | `NUMERIC(12,2)` | Yes | - | - | - | USD | - | Sum of line amount_base | Total claim amount normalized to base USD. |
| `status` | string | `VARCHAR(32)` | Yes | - | - | `DRAFT, SUBMITTED, PENDING_APPROVAL, APPROVED, REJECTED...` | - | - | Enum status | Lifecycle status. |
| `line_count` | integer | `INTEGER` | Yes | - | - | - | count | - | Integer 1-10 | Number of constituent expense line items. |

### Table: `expense_line`
*Granular expense item including currency conversion and embedded cryptographic receipt metadata.* (Category: **Core**, ID Prefix: `EXPL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `line_id` | string | `VARCHAR(64)` | Yes | PK | - | - | - | Yes | Regex ^EXPL-EXP-2026-\d{6}-\d{2}$ | Unique line item identifier. |
| `claim_id` | string | `VARCHAR(32)` | Yes | - | `expense_claim.claim_id` | - | - | - | FK to ExpenseClaim | Parent expense claim ID. |
| `line_number` | integer | `INTEGER` | Yes | - | - | - | index | - | 1 to 10 | Sequential line number within claim. |
| `expense_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | expense_date <= claim submit_date | Date expense was incurred. |
| `category` | string | `VARCHAR(32)` | Yes | - | - | `TRAVEL, LODGING, MEALS, CLIENT_ENTERTAINMENT, SOFTWARE...` | - | - | Enum category | Expense category. |
| `description` | string | `VARCHAR(255)` | Yes | - | - | - | - | - | Non-empty string | Itemized purchase narrative. |
| `amount_local` | float | `NUMERIC(10,2)` | Yes | - | - | - | local currency | - | amount_local > 0.0 | Incurred amount in vendor currency. |
| `currency` | string | `VARCHAR(3)` | Yes | - | - | `USD, INR, GBP, EUR, SGD` | ISO 4217 | - | Currency enum | Transaction currency. |
| `exchange_rate_to_base` | float | `NUMERIC(8,4)` | Yes | - | - | - | rate | - | rate > 0.0 | Fixed currency conversion rate to USD. |
| `amount_base` | float | `NUMERIC(10,2)` | Yes | - | - | - | USD | - | amount_local * exchange_rate | Converted value in USD. |
| `merchant_name` | string | `VARCHAR(128)` | Yes | - | - | - | - | - | Non-empty string | Vendor / merchant name. |
| `receipt_id` | string | `VARCHAR(32)` | No | - | - | - | - | - | Regex ^RCP-\d{6}$ or empty | Embedded receipt identifier. |
| `receipt_hash` | string | `VARCHAR(64)` | No | - | - | - | SHA-256 hex | - | 64 hex chars or empty | Deterministic SHA-256 hash of receipt metadata. |
| `receipt_date` | date | `DATE` | No | - | - | - | YYYY-MM-DD | - | Valid date or empty | Date stamped on physical receipt. |
| `has_receipt` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Receipt presence flag. |
| `file_name` | string | `VARCHAR(128)` | No | - | - | - | - | - | Filename or empty | Synthetic receipt scan filename. |
| `is_disallowed` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Flag if disallowed by auditor/approver. |

### Table: `expense_claim_event`
*Immutable lifecycle audit log for expense claim state changes.* (Category: **Event**, ID Prefix: `EXPV-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `event_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^EXPV-\d{6}$ | Unique expense transition event identifier. |
| `claim_id` | string | `VARCHAR(32)` | Yes | - | `expense_claim.claim_id` | - | - | - | FK to ExpenseClaim | Subject claim. |
| `from_status` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | Valid status | Previous claim status. |
| `to_status` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | Valid status | New claim status. |
| `actor_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Acting employee/system ID. |
| `timestamp` | timestamp | `TIMESTAMP` | Yes | - | - | - | ISO 8601 | - | Timestamp | Transition timestamp. |
| `reason_code` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty code | Lifecycle reason code. |
| `comment` | string | `VARCHAR(255)` | No | - | - | - | - | - | Text | Reviewer/system remarks. |

### Table: `approval_rule`
*Configurable business rules defining required authority, tier thresholds, and approval steps.* (Category: **Core**, ID Prefix: `ARUL-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `rule_id` | string | `VARCHAR(16)` | Yes | PK | - | - | - | Yes | Regex ^ARUL-\d{2}$ | Unique approval rule identifier. |
| `rule_code` | string | `VARCHAR(32)` | Yes | - | - | - | - | Yes | Unique rule code | Standard mnemonic rule code. |
| `name` | string | `VARCHAR(128)` | Yes | - | - | - | - | - | Non-empty string | Rule title. |
| `entity_type` | string | `VARCHAR(16)` | Yes | - | - | `LEAVE, EXPENSE` | - | - | LEAVE or EXPENSE | Target business domain. |
| `min_amount` | float | `NUMERIC(12,2)` | Yes | - | - | - | USD | - | min_amount >= 0.0 | Minimum threshold in USD. |
| `max_amount` | float | `NUMERIC(12,2)` | Yes | - | - | - | USD | - | max_amount >= min_amount | Upper threshold ceiling in USD. |
| `min_duration_days` | integer | `INTEGER` | Yes | - | - | - | days | - | days >= 0 | Minimum leave duration for rule applicability. |
| `max_duration_days` | integer | `INTEGER` | Yes | - | - | - | days | - | days >= min_duration_days | Maximum leave duration. |
| `required_role` | string | `VARCHAR(32)` | Yes | - | - | `MANAGER, DIRECTOR, VP, FINANCE, HR...` | - | - | Enum role | Organizational role required to approve. |
| `min_approver_level` | integer | `INTEGER` | Yes | - | - | `1, 2, 3, 4, 5...` | Level | - | Integer 1-6 | Minimum job level required. |
| `step_number` | integer | `INTEGER` | Yes | - | - | `1, 2, 3, 4` | Step | - | Integer 1-4 | Sequential step index in multi-level workflow. |
| `description` | string | `VARCHAR(255)` | Yes | - | - | - | - | - | Text | Rule explanation. |

### Table: `approval_rule_category`
*N:M bridge linking ApprovalRules to applicable expense categories.* (Category: **Bridge**, ID Prefix: `ARC-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `rule_category_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^ARC-\d{6}$ | Bridge record ID. |
| `rule_id` | string | `VARCHAR(16)` | Yes | - | `approval_rule.rule_id` | - | - | - | FK to ApprovalRule | Target approval rule. |
| `category` | string | `VARCHAR(32)` | Yes | - | - | `ALL, TRAVEL, LODGING, MEALS, CLIENT_ENTERTAINMENT...` | - | - | Expense category or ALL | Scoped expense category. |

### Table: `approval_rule_country`
*N:M bridge linking ApprovalRules to applicable employee country jurisdictions.* (Category: **Bridge**, ID Prefix: `ARCTRY-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `rule_country_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^ARCTRY-\d{6}$ | Bridge record ID. |
| `rule_id` | string | `VARCHAR(16)` | Yes | - | `approval_rule.rule_id` | - | - | - | FK to ApprovalRule | Target approval rule. |
| `country` | string | `VARCHAR(8)` | Yes | - | - | `ALL, IN, US, UK, DE...` | - | - | Country code or ALL | Scoped country jurisdiction. |

### Table: `approval_step`
*Materialized approval step recording individual approver decision, timestamp, and audit trail.* (Category: **Core**, ID Prefix: `APR-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `step_id` | string | `VARCHAR(64)` | Yes | PK | - | - | - | Yes | Regex ^APR-(LVE|EXP)...-\d{2}$ | Unique approval step identifier. |
| `request_id` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | FK to LeaveRequest or ExpenseClaim | Subject request or claim identifier. |
| `step_number` | integer | `INTEGER` | Yes | - | - | `1, 2, 3, 4` | Step | - | Integer 1-4 | Sequential sequence number. |
| `rule_id` | string | `VARCHAR(16)` | Yes | - | `approval_rule.rule_id` | - | - | - | FK to ApprovalRule | Enforced rule. |
| `approver_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Assigned approver employee ID. |
| `level` | integer | `INTEGER` | Yes | - | - | `1, 2, 3, 4, 5...` | Level | - | Integer 1-6 | Approver hierarchy level. |
| `due_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Valid date | Target completion deadline. |
| `status` | string | `VARCHAR(16)` | Yes | - | - | `PENDING, APPROVED, REJECTED, SKIPPED, ESCALATED` | - | - | Enum status | Step lifecycle status. |
| `decided_at` | timestamp | `TIMESTAMP` | No | - | - | - | ISO 8601 | - | Timestamp or empty | Decision execution timestamp. |
| `decision` | string | `VARCHAR(16)` | Yes | - | - | `APPROVE, REJECT, ESCALATE, SKIP, PENDING` | - | - | Enum decision | Action rendered. |
| `reason_code` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Non-empty code | Structured decision reason code. |
| `comment` | string | `VARCHAR(255)` | No | - | - | - | - | - | Text | Approver rationale comment. |

### Table: `employee_cost_center_assignment`
*Historical and current mapping of employees to cost centers with effective date bounds.* (Category: **Bridge**, ID Prefix: `ECCA-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `assignment_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^ECCA-\d{6}$ | Unique assignment identifier. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Assigned employee. |
| `cost_center_id` | string | `VARCHAR(32)` | Yes | - | `cost_center.cost_center_id` | - | - | - | FK to CostCenter | Assigned cost center. |
| `allocation_percentage` | float | `NUMERIC(5,2)` | Yes | - | - | - | percentage | - | Between 1.0 and 100.0 | Budget allocation weight. |
| `effective_from` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | Date format | Start of assignment window. |
| `effective_to` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | effective_to >= effective_from | End of assignment window. |
| `is_primary` | boolean | `BOOLEAN` | Yes | - | - | `0, 1, true, false` | Boolean | - | 0 or 1 | Primary cost center flag. |

### Table: `decision_log`
*Exhaustive decision audit log capturing reason codes, applied rules, and inputs snapshots.* (Category: **Audit**, ID Prefix: `DEC-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `decision_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^DEC-\d{6}$ | Unique decision audit identifier. |
| `subject_id` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | LVE or EXP ID | Target leave request or expense claim ID. |
| `decision` | string | `VARCHAR(32)` | Yes | - | - | `APPROVE, REJECT, ESCALATE, RETURN_FOR_INFO, AUTO_APPROVED` | - | - | Enum decision | Final rendered verdict. |
| `reason_code` | string | `VARCHAR(64)` | Yes | - | - | - | - | - | Structured code | Standardized decision reason code. |
| `reason_text` | string | `VARCHAR(255)` | Yes | - | - | - | - | - | Human readable explanation | Explanatory decision narrative. |
| `rule_id` | string | `VARCHAR(32)` | Yes | - | - | - | - | - | Rule identifier | Triggering policy or approval rule ID. |
| `inputs_snapshot_json` | json | `TEXT` | Yes | - | - | - | JSON | - | Valid JSON string | Serialized snapshot of input parameters evaluated. |
| `timestamp` | timestamp | `TIMESTAMP` | Yes | - | - | - | ISO 8601 | - | Timestamp | Audit logging timestamp. |

### Table: `reimbursement`
*Disbursement records issued exclusively for fully approved, eligible expense claims.* (Category: **Core**, ID Prefix: `RMB-2026-`)

| Field Name | Type | SQL Type | Req | PK | FK | Allowed Values / Enums | Units | Unique | Validation Rule | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| `reimbursement_id` | string | `VARCHAR(32)` | Yes | PK | - | - | - | Yes | Regex ^RMB-2026-\d{6}$ | Unique reimbursement payment identifier. |
| `claim_id` | string | `VARCHAR(32)` | Yes | - | `expense_claim.claim_id` | - | - | - | FK to ExpenseClaim | Parent approved expense claim ID. |
| `employee_id` | string | `VARCHAR(32)` | Yes | - | `employee.employee_id` | - | - | - | FK to Employee | Payee employee ID. |
| `payment_method` | string | `VARCHAR(32)` | Yes | - | - | `DIRECT_DEPOSIT, WIRE_TRANSFER, PAYROLL` | - | - | Enum payment_method | Treasury disbursement channel. |
| `currency` | string | `VARCHAR(3)` | Yes | - | - | `USD, INR, GBP, EUR, SGD` | ISO 4217 | - | Currency enum | Disbursement currency. |
| `amount` | float | `NUMERIC(12,2)` | Yes | - | - | - | Currency | - | amount > 0.0 | Total disbursed amount (sum of approved lines). |
| `payment_date` | date | `DATE` | Yes | - | - | - | YYYY-MM-DD | - | payment_date >= approval date | Date payment was executed. |
| `transaction_reference` | string | `VARCHAR(64)` | Yes | - | - | - | - | Yes | Regex ^TXN-\d{8}$ | Bank transaction reference number. |
| `status` | string | `VARCHAR(16)` | Yes | - | - | `PROCESSED, PENDING, FAILED` | - | - | Enum status | Disbursement processing status. |

