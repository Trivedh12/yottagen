# YottaGen Corporate Governance & Policy Rule Catalogue

Comprehensive catalogue of operational policy and audit rules implemented across the YottaGen rule engine and independent audit module.

---

## 1. Leave Rules (`LV-*`)

### `LV-001`: Leave Balance Sufficiency & Overdraft Prohibition
- **Domain**: Leave Management
- **Rule Statement**: An employee cannot submit leave requests exceeding their currently available net balance (`closing_balance`), nor can ledger adjustments produce a negative closing balance.
- **Enforcement**: Evaluated before approval; requests exceeding balance are rejected with `INSUFFICIENT_BALANCE`.
- **Audit Action**: Flags any `leave_balance` where `closing_balance < 0.0`.
- **Severity**: HIGH

### `LV-002`: Overlapping Approved Leave Prohibition
- **Domain**: Leave Management
- **Rule Statement**: An employee cannot have two active or approved leave intervals that intersect in calendar dates `[start_date, end_date]`.
- **Enforcement**: Rejected during submission if another approved leave exists for the same employee within the date span.
- **Audit Action**: Pairwise interval intersection check `max(start1, start2) <= min(end1, end2)`.
- **Severity**: CRITICAL

### `LV-003`: Policy Notice Period & Duration Limits
- **Domain**: Leave Management
- **Rule Statement**: Leave requests must observe the policy minimum notice days (`submit_date <= start_date - min_notice_days`) and must not exceed `max_consecutive_days`.
- **Enforcement**: Violations trigger rejection or require elevated director override.
- **Audit Action**: Flags requests violating duration ceilings.
- **Severity**: MEDIUM

---

## 2. Expense Rules (`EX-*`)

### `EX-001`: Mandatory Receipt Substantiation
- **Domain**: Business Expenses
- **Rule Statement**: Any expense line item exceeding the statutory policy threshold ($25.00 USD equivalent) must have a valid receipt attached (`has_receipt = 1`) with verifiable receipt metadata and SHA-256 hash.
- **Enforcement**: Missing receipts above $25 result in claim rejection or return for information.
- **Audit Action**: Scans all line items with `amount_base > 25.0` and `has_receipt == 0`.
- **Severity**: HIGH

### `EX-002`: Duplicate Receipt Hash Detection
- **Domain**: Fraud Prevention & Audit
- **Rule Statement**: Cryptographic receipt hashes (`receipt_hash`) must be unique across all expense lines. Reusing a receipt scan across multiple lines or claims is strictly prohibited.
- **Enforcement**: Reject duplicate receipt submissions.
- **Audit Action**: Groups line items by `receipt_hash` to detect duplicates.
- **Severity**: CRITICAL

### `EX-003`: Maximum Claim Ceiling Breach
- **Domain**: Budgetary Control
- **Rule Statement**: Individual expense claims cannot exceed the absolute policy cap of $10,000.00 USD. Claims above this limit require formal board/treasury authorization.
- **Enforcement**: Claims exceeding $10,000 are rejected by the workflow engine.
- **Audit Action**: Scans for `total_amount_base > 10000.0`.
- **Severity**: HIGH

### `EX-004`: Active Employment Window Adherence
- **Domain**: Compliance
- **Rule Statement**: All incurred expenses must occur strictly within the employee's active tenure: `hire_date <= expense_date <= termination_date`.
- **Enforcement**: Expenses outside active employment are rejected.
- **Audit Action**: Cross-references employee `hire_date` and `termination_date` with line `expense_date`.
- **Severity**: HIGH

### `EX-005`: Split-Claim Approval Threshold Evasion
- **Domain**: Anti-Structuring & Fraud Detection
- **Rule Statement**: Employees are prohibited from splitting a single purchase into multiple claims within a short rolling window (3 days) to evade multi-tier approval thresholds (e.g., submitting two $92 claims to avoid the $100 Director review threshold).
- **Enforcement**: Workflow engine aggregates clustered submissions.
- **Audit Action**: Detects rolling 3-day clusters by claimant where each claim is $\le \$100$ but their sum exceeds $\$100$.
- **Severity**: MEDIUM

---

## 3. Approval Authority & Workflow Rules (`AP-*`)

### `AP-001`: Tiered Approval Threshold Alignment
- **Domain**: Organizational Governance
- **Rule Statement**: Approval authority paths must adhere strictly to expense value tiers:
  - $\le \$100$: Direct Line Manager (Level $\ge 3$)
  - $\$100 - \$1,000$: Manager + Department Head / Director (Level $\ge 4$)
  - $\$1,000 - \$5,000$: Manager + Director + Finance Approver
  - $> \$5,000$: Manager + Director + Finance + Executive VP / CFO (Level $\ge 5$)
- **Enforcement**: Automated routing graph generation.
- **Severity**: HIGH

### `AP-002`: Prohibition of Self-Approval
- **Domain**: Segregation of Duties
- **Rule Statement**: A requester cannot approve their own submission under any circumstances (`approver_id != claimant_id`).
- **Enforcement**: The routing engine excludes the requester from potential approver pools and delegates to a superior or corporate peer.
- **Audit Action**: Detects `approval_step.approver_id == claimant_id`.
- **Severity**: CRITICAL

### `AP-003`: Approver Hierarchy Authority
- **Domain**: Delegation of Authority
- **Rule Statement**: An assigned approver must possess a job level matching or exceeding the rule requirement (`approver.job_level >= rule.min_approver_level`).
- **Enforcement**: Validated during step instantiation.
- **Audit Action**: Verifies approver authority level.
- **Severity**: MEDIUM

---

## 4. Reimbursement & Financial Rules (`RB-*`, `CC-*`)

### `RB-001`: Disbursement Exclusively for Approved Claims
- **Domain**: Financial Treasury
- **Rule Statement**: Reimbursements (`RMB-2026-*`) can only be generated for claims that have completed the full approval workflow with final status `APPROVED` or `REIMBURSED`.
- **Enforcement**: Treasury disbursement pipeline triggers only upon final step signoff.
- **Audit Action**: Validates parent claim lifecycle status.
- **Severity**: CRITICAL

### `RB-002`: Prohibition of Duplicate Reimbursements
- **Domain**: Treasury & Disbursement Control
- **Rule Statement**: An expense claim is entitled to exactly one reimbursement payment. Multiple disbursements for a single claim ID represent duplicate payments.
- **Enforcement**: System prevents multiple payment records per claim.
- **Audit Action**: Detects multiple `reimbursement` records sharing the same `claim_id`.
- **Severity**: CRITICAL

### `CC-001`: Mandatory Valid Cost Center Allocation
- **Domain**: Managerial Accounting
- **Rule Statement**: Every expense claim must specify an active, valid operational cost center (`cost_center_id`). Claims with missing or non-existent cost centers cannot be approved or reimbursed.
- **Enforcement**: Required field in schema and submission validation.
- **Audit Action**: Flags claims where `cost_center_id` is empty or unresolved.
- **Severity**: HIGH
