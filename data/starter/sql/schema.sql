-- ============================================================================
-- YottaGen Schema DDL (Generated from yottagen/schema.py)
-- ============================================================================
PRAGMA foreign_keys = ON;

-- Table: cost_center (Core)
CREATE TABLE IF NOT EXISTS cost_center (
    cost_center_id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    department VARCHAR(64) NOT NULL,
    manager_id VARCHAR(32) NOT NULL,
    budget_currency VARCHAR(3) NOT NULL,
    annual_budget NUMERIC(14,2) NOT NULL,
    status VARCHAR(16) NOT NULL,
    FOREIGN KEY (manager_id) REFERENCES employee(employee_id)
);

CREATE INDEX IF NOT EXISTS idx_cost_center_manager_id ON cost_center(manager_id);

-- Table: employee (Core)
CREATE TABLE IF NOT EXISTS employee (
    employee_id VARCHAR(32) PRIMARY KEY,
    first_name VARCHAR(64) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    email VARCHAR(128) NOT NULL UNIQUE,
    country VARCHAR(2) NOT NULL,
    city VARCHAR(64) NOT NULL,
    hire_date DATE NOT NULL,
    termination_date DATE,
    status VARCHAR(16) NOT NULL,
    employee_type VARCHAR(16) NOT NULL,
    job_level INTEGER NOT NULL,
    job_title VARCHAR(128) NOT NULL,
    grade VARCHAR(8) NOT NULL,
    manager_id VARCHAR(32),
    cost_center_id VARCHAR(32) NOT NULL,
    is_finance_approver BOOLEAN NOT NULL,
    is_hr_approver BOOLEAN NOT NULL,
    role VARCHAR(32) NOT NULL,
    FOREIGN KEY (manager_id) REFERENCES employee(employee_id),
    FOREIGN KEY (cost_center_id) REFERENCES cost_center(cost_center_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_manager_id ON employee(manager_id);
CREATE INDEX IF NOT EXISTS idx_employee_cost_center_id ON employee(cost_center_id);

-- Table: holiday_calendar (Supporting)
CREATE TABLE IF NOT EXISTS holiday_calendar (
    holiday_id VARCHAR(32) PRIMARY KEY,
    country VARCHAR(2) NOT NULL,
    holiday_date DATE NOT NULL,
    holiday_name VARCHAR(128) NOT NULL,
    is_half_day BOOLEAN NOT NULL
);


-- Table: leave_policy (Core)
CREATE TABLE IF NOT EXISTS leave_policy (
    policy_id VARCHAR(16) PRIMARY KEY,
    policy_name VARCHAR(64) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL,
    country_scope VARCHAR(8) NOT NULL,
    accrual_days_per_month NUMERIC(5,2) NOT NULL,
    annual_cap NUMERIC(5,2) NOT NULL,
    carry_forward_max NUMERIC(5,2) NOT NULL,
    min_notice_days INTEGER NOT NULL,
    max_consecutive_days INTEGER NOT NULL,
    requires_doc_after_days INTEGER NOT NULL,
    allows_negative_balance BOOLEAN NOT NULL,
    approval_levels_by_duration INTEGER NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL
);


-- Table: leave_balance_ledger (Supporting)
CREATE TABLE IF NOT EXISTS leave_balance_ledger (
    ledger_id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL,
    policy_id VARCHAR(16) NOT NULL,
    entry_type VARCHAR(32) NOT NULL,
    days NUMERIC(6,2) NOT NULL,
    effective_date DATE NOT NULL,
    reference_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    notes VARCHAR(255),
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (policy_id) REFERENCES leave_policy(policy_id)
);

CREATE INDEX IF NOT EXISTS idx_leave_balance_ledger_employee_id ON leave_balance_ledger(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_ledger_policy_id ON leave_balance_ledger(policy_id);

-- Table: leave_balance (Core)
CREATE TABLE IF NOT EXISTS leave_balance (
    balance_id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL,
    policy_id VARCHAR(16) NOT NULL,
    as_of_date DATE NOT NULL,
    opening_balance NUMERIC(6,2) NOT NULL,
    accrued_days NUMERIC(6,2) NOT NULL,
    used_days NUMERIC(6,2) NOT NULL,
    adjusted_days NUMERIC(6,2) NOT NULL,
    pending_days NUMERIC(6,2) NOT NULL,
    closing_balance NUMERIC(6,2) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (policy_id) REFERENCES leave_policy(policy_id)
);

CREATE INDEX IF NOT EXISTS idx_leave_balance_employee_id ON leave_balance(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_policy_id ON leave_balance(policy_id);

-- Table: leave_request (Core)
CREATE TABLE IF NOT EXISTS leave_request (
    request_id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL,
    policy_id VARCHAR(16) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    calendar_days INTEGER NOT NULL,
    business_days INTEGER NOT NULL,
    weekend_days_in_span INTEGER NOT NULL,
    holiday_days_in_span INTEGER NOT NULL,
    submit_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL,
    reason_code VARCHAR(32) NOT NULL,
    comments VARCHAR(255),
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (policy_id) REFERENCES leave_policy(policy_id)
);

CREATE INDEX IF NOT EXISTS idx_leave_request_employee_id ON leave_request(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_policy_id ON leave_request(policy_id);

-- Table: leave_request_event (Event)
CREATE TABLE IF NOT EXISTS leave_request_event (
    event_id VARCHAR(32) PRIMARY KEY,
    request_id VARCHAR(32) NOT NULL,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    actor_id VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    comment VARCHAR(255),
    FOREIGN KEY (request_id) REFERENCES leave_request(request_id),
    FOREIGN KEY (actor_id) REFERENCES employee(employee_id)
);

CREATE INDEX IF NOT EXISTS idx_leave_request_event_request_id ON leave_request_event(request_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_event_actor_id ON leave_request_event(actor_id);

-- Table: expense_policy (Core)
CREATE TABLE IF NOT EXISTS expense_policy (
    policy_id VARCHAR(16) PRIMARY KEY,
    policy_name VARCHAR(64) NOT NULL UNIQUE,
    currency VARCHAR(3) NOT NULL,
    daily_meal_limit NUMERIC(10,2) NOT NULL,
    receipt_required_threshold NUMERIC(10,2) NOT NULL,
    max_claim_amount NUMERIC(12,2) NOT NULL,
    entertainment_per_person_limit NUMERIC(10,2) NOT NULL,
    equipment_auto_approval_limit NUMERIC(10,2) NOT NULL,
    lodging_daily_limit_in NUMERIC(10,2) NOT NULL,
    lodging_daily_limit_de NUMERIC(10,2) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL
);


-- Table: expense_claim (Core)
CREATE TABLE IF NOT EXISTS expense_claim (
    claim_id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL,
    cost_center_id VARCHAR(32),
    policy_id VARCHAR(16) NOT NULL,
    claim_date DATE NOT NULL,
    submit_date DATE NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    total_amount_local NUMERIC(12,2) NOT NULL,
    total_amount_base NUMERIC(12,2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    line_count INTEGER NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (cost_center_id) REFERENCES cost_center(cost_center_id),
    FOREIGN KEY (policy_id) REFERENCES expense_policy(policy_id)
);

CREATE INDEX IF NOT EXISTS idx_expense_claim_employee_id ON expense_claim(employee_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_cost_center_id ON expense_claim(cost_center_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_policy_id ON expense_claim(policy_id);

-- Table: expense_line (Core)
CREATE TABLE IF NOT EXISTS expense_line (
    line_id VARCHAR(64) PRIMARY KEY,
    claim_id VARCHAR(32) NOT NULL,
    line_number INTEGER NOT NULL,
    expense_date DATE NOT NULL,
    category VARCHAR(32) NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount_local NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    exchange_rate_to_base NUMERIC(8,4) NOT NULL,
    amount_base NUMERIC(10,2) NOT NULL,
    merchant_name VARCHAR(128) NOT NULL,
    receipt_id VARCHAR(32),
    receipt_hash VARCHAR(64),
    receipt_date DATE,
    has_receipt BOOLEAN NOT NULL,
    file_name VARCHAR(128),
    is_disallowed BOOLEAN NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES expense_claim(claim_id)
);

CREATE INDEX IF NOT EXISTS idx_expense_line_claim_id ON expense_line(claim_id);

-- Table: expense_claim_event (Event)
CREATE TABLE IF NOT EXISTS expense_claim_event (
    event_id VARCHAR(32) PRIMARY KEY,
    claim_id VARCHAR(32) NOT NULL,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    actor_id VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    comment VARCHAR(255),
    FOREIGN KEY (claim_id) REFERENCES expense_claim(claim_id),
    FOREIGN KEY (actor_id) REFERENCES employee(employee_id)
);

CREATE INDEX IF NOT EXISTS idx_expense_claim_event_claim_id ON expense_claim_event(claim_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_event_actor_id ON expense_claim_event(actor_id);

-- Table: approval_rule (Core)
CREATE TABLE IF NOT EXISTS approval_rule (
    rule_id VARCHAR(16) PRIMARY KEY,
    rule_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    entity_type VARCHAR(16) NOT NULL,
    min_amount NUMERIC(12,2) NOT NULL,
    max_amount NUMERIC(12,2) NOT NULL,
    min_duration_days INTEGER NOT NULL,
    max_duration_days INTEGER NOT NULL,
    required_role VARCHAR(32) NOT NULL,
    min_approver_level INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    description VARCHAR(255) NOT NULL
);


-- Table: approval_rule_category (Bridge)
CREATE TABLE IF NOT EXISTS approval_rule_category (
    rule_category_id VARCHAR(32) PRIMARY KEY,
    rule_id VARCHAR(16) NOT NULL,
    category VARCHAR(32) NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES approval_rule(rule_id)
);

CREATE INDEX IF NOT EXISTS idx_approval_rule_category_rule_id ON approval_rule_category(rule_id);

-- Table: approval_rule_country (Bridge)
CREATE TABLE IF NOT EXISTS approval_rule_country (
    rule_country_id VARCHAR(32) PRIMARY KEY,
    rule_id VARCHAR(16) NOT NULL,
    country VARCHAR(8) NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES approval_rule(rule_id)
);

CREATE INDEX IF NOT EXISTS idx_approval_rule_country_rule_id ON approval_rule_country(rule_id);

-- Table: approval_step (Core)
CREATE TABLE IF NOT EXISTS approval_step (
    step_id VARCHAR(64) PRIMARY KEY,
    request_id VARCHAR(32) NOT NULL,
    step_number INTEGER NOT NULL,
    rule_id VARCHAR(16) NOT NULL,
    approver_id VARCHAR(32) NOT NULL,
    level INTEGER NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(16) NOT NULL,
    decided_at TIMESTAMP,
    decision VARCHAR(16) NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    comment VARCHAR(255),
    FOREIGN KEY (rule_id) REFERENCES approval_rule(rule_id),
    FOREIGN KEY (approver_id) REFERENCES employee(employee_id)
);

CREATE INDEX IF NOT EXISTS idx_approval_step_rule_id ON approval_step(rule_id);
CREATE INDEX IF NOT EXISTS idx_approval_step_approver_id ON approval_step(approver_id);

-- Table: employee_cost_center_assignment (Bridge)
CREATE TABLE IF NOT EXISTS employee_cost_center_assignment (
    assignment_id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL,
    cost_center_id VARCHAR(32) NOT NULL,
    allocation_percentage NUMERIC(5,2) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    is_primary BOOLEAN NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (cost_center_id) REFERENCES cost_center(cost_center_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_cost_center_assignment_employee_id ON employee_cost_center_assignment(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_cost_center_assignment_cost_center_id ON employee_cost_center_assignment(cost_center_id);

-- Table: decision_log (Audit)
CREATE TABLE IF NOT EXISTS decision_log (
    decision_id VARCHAR(32) PRIMARY KEY,
    subject_id VARCHAR(32) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    reason_text VARCHAR(255) NOT NULL,
    rule_id VARCHAR(32) NOT NULL,
    inputs_snapshot_json TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);


-- Table: reimbursement (Core)
CREATE TABLE IF NOT EXISTS reimbursement (
    reimbursement_id VARCHAR(32) PRIMARY KEY,
    claim_id VARCHAR(32) NOT NULL,
    employee_id VARCHAR(32) NOT NULL,
    payment_method VARCHAR(32) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payment_date DATE NOT NULL,
    transaction_reference VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES expense_claim(claim_id),
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
);

CREATE INDEX IF NOT EXISTS idx_reimbursement_claim_id ON reimbursement(claim_id);
CREATE INDEX IF NOT EXISTS idx_reimbursement_employee_id ON reimbursement(employee_id);

