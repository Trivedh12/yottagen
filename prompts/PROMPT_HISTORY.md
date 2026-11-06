# Prompt History

## Master Prompt (Submission Prompt)

```text
You are a senior data engineer and QA architect. Build a COMPLETE, runnable, reproducible synthetic-data generator, validator, rule engine and evaluation harness for this problem. This is a graded hiring challenge, so every requirement below is mandatory. Do not skip, stub or simplify anything. Work in the phases listed at the end, run every command yourself, fix every failure, and show me the real output.

# 1. PROBLEM
Route leave and expense requests using policy, balances, budgets and approval authority. The solution must expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Complexity is medium: multiple related entities, conditional rules, at least one exception path, and meaningful evaluation metrics.
Actors: business requester, process owner, approver, operations analyst, system administrator.

# 2. TECH AND CONSTRAINTS
- Python 3.10+, standard library only for the generator (random.Random(seed), csv, json, sqlite3, hashlib, argparse, datetime, dataclasses). Optional: pytest for tests. No paid services, no network calls, no external data (so provenance is purely synthetic).
- Fully deterministic: use a single random.Random(seed) passed through all functions. Never use datetime.now(), uuid4 or unseeded randomness. Use a fixed reference "as-of" date (2026-10-22). Iterate in sorted order. Write files with newline="\n" and a fixed column order, so outputs are byte-identical.
- Default seed 20261022. Scale is parameterized: `--scale starter|full` (starter ~ 40 employees/80 leave/100 expense claims; full = 400 employees, 6 leave policies, 800 leave requests, 1,000 expense claims with 1-10 lines each) or explicit `--employees --leave-requests --expense-claims`. Starter and full use the same generator code.
- CLI: `python -m yottagen generate --seed 20261022 --scale full --out data/full` plus subcommands `validate`, `audit`, `evaluate`, `repro-check`, `all`. Also provide a Makefile with targets: setup, generate, validate, audit, evaluate, test, repro, all.
- No secrets, no real personal data (all names/emails synthetic, emails on example.com).

# 3. REPOSITORY STRUCTURE
```
README.md
Makefile
requirements.txt              (pytest only)
yottagen/                     (package: config.py, calendar.py, master.py, leave.py, expense.py, routing.py,
                               injector.py, derive.py, export.py, validate.py, audit.py, evaluate.py, repro.py, cli.py)
tests/                        (pytest: ids, business days, accrual, routing thresholds, FK integrity, anomaly injection,
                               ground-truth separation, reproducibility)
data/starter/ data/full/      (committed outputs: CSV + JSON + SQL)
docs/data_dictionary.md  docs/data_dictionary.csv  docs/data_dictionary.json
docs/ERD.md                   (Mermaid ERD + cardinality table + lifecycle diagrams)
docs/ASSUMPTIONS.md  docs/DECISIONS.md  docs/LIMITATIONS.md
docs/validation_summary.md    (generated)  docs/evaluation_report.md (generated)  docs/reproducibility_report.md (generated)
source_manifest.json          (states: no external data used; synthetic only; public reference used for schema inspiration only)
prompts/PROMPT_HISTORY.md     (every prompt I submit to any AI tool, verbatim, including this master prompt)
AI_USAGE.md                   (where AI accelerated, where I relied on it heavily, what I personally reviewed/changed/validated)
```
Make meaningful, incremental git commits (one per phase). Give me the commit messages.

# 4. ENTITIES (all required, each with a PK and FKs, documented cardinality, effective dates and lifecycle)
Core: Employee, LeavePolicy, LeaveBalance, LeaveRequest, ExpensePolicy, ExpenseClaim, ExpenseLine, CostCenter, ApprovalRule, ApprovalStep, Reimbursement.
Supporting (add these to satisfy "bridge tables", "event history" and "holiday" requirements):
- HolidayCalendar (country, date, name) for IN, US, UK, DE, SG.
- LeaveBalanceLedger (append-only accrual/usage/adjustment events; LeaveBalance is derived from it).
- LeaveRequestEvent and ExpenseClaimEvent (append-only state-transition history: event_id, entity_id, from_status, to_status, actor_id, timestamp, reason_code). Never overwrite history.
- ApprovalRuleCategory (bridge, N:M between ApprovalRule and expense category) and ApprovalRuleCountry (bridge, N:M with country).
- EmployeeCostCenterAssignment (bridge with effective_from/effective_to, so employees can change cost center).
- ReceiptMetadata embedded in ExpenseLine: receipt_id, receipt_hash (SHA-256 hex), vendor, receipt_date, has_receipt, currency, file_name. No actual files.
- DecisionLog (audit trail: decision_id, subject_id, decision, reason_code, reason_text, rule_id, inputs_snapshot_json, timestamp) so ALL decision reasons are auditable.

ID conventions (zero-padded, immutable, identical everywhere they are referenced):
- EMP-000001
- LVE-2026-000001
- EXP-2026-000001
- EXPL-<claim-id>-01 (e.g., EXPL-EXP-2026-000001-01)
- APR-<request-id>-01 (request-id = LVE-... or EXP-..., e.g., APR-EXP-2026-000001-01, step number increments)
- RMB-2026-000001
Define consistent formats for the other IDs too (LPOL-01, LBAL-..., EPOL-..., CC-100, ARUL-01, LVEV-..., EXPV-..., DEC-...).

# 5. DATA DICTIONARY (Step 1, do first)
For every entity and every field, specify: type, required/optional, allowed values (enums), units (currency, days), uniqueness, validation rule, PK/FK. Generate docs/data_dictionary.md/.csv/.json from a single Python schema definition (schema.py) that is ALSO used by the validator and by the SQL DDL generator, so docs and code can't drift.
Document the cardinality of every relationship (1:1, 1:N, N:M), optional relationships, effective dates, and lifecycle states:
- LeaveRequest: DRAFT -> SUBMITTED -> PENDING_APPROVAL -> APPROVED | REJECTED | CANCELLED (cancel allowed from SUBMITTED/PENDING/APPROVED); APPROVED -> CONSUMED optional.
- ExpenseClaim: DRAFT -> SUBMITTED -> PENDING_APPROVAL -> APPROVED | REJECTED | RETURNED_FOR_INFO -> (resubmit) ; APPROVED -> REIMBURSED. Reimbursement exists only after final approval.
- ApprovalStep: PENDING -> APPROVED | REJECTED | SKIPPED | ESCALATED.
Only legal transitions are allowed (encode a transition table and validate it).

# 6. GENERATION LOGIC (parents first, then children and events)
Order: CostCenter, Employee hierarchy, HolidayCalendar, LeavePolicy, ExpensePolicy, ApprovalRule (+ bridges), LeaveBalanceLedger/LeaveBalance, LeaveRequest (+events), ExpenseClaim, ExpenseLine, ApprovalStep, DecisionLog, Reimbursement.
- Employees (400): realistic hierarchy (1 CEO, ~5 VPs, ~15 directors, ~50 managers, rest ICs; manager_id FK to self, no cycles, manager hired before reports), countries IN (~45%), US, UK, DE, SG, grades, job levels, hire_date spread over 2015-2026, ~5% with termination_date, status ACTIVE/TERMINATED/ON_LEAVE, employee_type FULL_TIME/CONTRACT, and a finance-approver/HR flag for process owners. Include roles for requester, approver, process owner, ops analyst and system admin.
- LeavePolicy (exactly 6): e.g., Annual, Sick, Casual, Parental, Unpaid, Comp-Off. Fields: accrual_days_per_month, annual_cap, carry_forward_max, min_notice_days, max_consecutive_days, requires_doc_after_days, country scope, effective_from/to, allows_negative_balance (false except for a flagged exception), approval_levels_by_duration.
- LeaveBalance: compute accrual month-by-month from max(hire_date, policy start) to as-of date, apply carry-forward and caps, subtract APPROVED usage and expose PENDING. closing = opening + accrued + adjusted - used. Derive from the ledger, never random.
- LeaveRequest (800): date ranges; business_days computed excluding weekends AND the employee's country holidays; fields calendar_days, business_days, weekend_days_in_span, holiday_days_in_span. Status and decision are produced by the rule engine from balance, notice, policy limits, overlap, and approval authority. NOT random labels.
- ExpenseClaim (1000) with 1-10 lines each (realistic skew: most 1-4 lines). Categories: TRAVEL, LODGING, MEALS, CLIENT_ENTERTAINMENT, SOFTWARE, EQUIPMENT, TRAINING, MISC. Line amounts in local currency plus fixed-rate conversion to a base currency (document rates). claim.total_amount = SUM(lines) (derived). Each claim has cost_center_id, expense_date range, submit_date, and receipts metadata.
- Routing engine (routing.py) selects the approval path by amount (base-currency thresholds), category, country and manager chain. Example documented rules: <= 100: manager; 100-1000: manager + department head; > 1000 or CLIENT_ENTERTAINMENT/EQUIPMENT over limit: manager + director + finance; > 5000: + VP/CFO; country-specific overrides (e.g., DE and IN require finance review for lodging over X); leave > 5 business days: manager + HR; leave > 15 business days or PARENTAL: manager + HR + director. Approver must have authority (grade/level >= rule min_level), must not be the requester, and must be in the requester's chain unless an escalation/delegation applies. Every step is written as an ApprovalStep with approver_id, level, rule_id, due date, decision, decided_at, comment, reason_code.
- Reimbursement (RMB-2026-000001...): created ONLY for ExpenseClaims whose final ApprovalStep is APPROVED and which passed eligibility (no unresolved flags). amount = SUM of approved lines minus any disallowed lines. payment_date after final approval date. One per claim (except where the labelled duplicate_reimbursement anomaly is injected).
- All derived values (totals, balances, business days, statuses, dates, scores) are computed from source records in derive.py. Never generate them independently.
- Distributions must be realistic with meaningful variation: log-normal expense amounts per category, seasonality in leave, weekday-biased submissions, approval turnaround times with a long tail, approval/rejection rates that depend on rules, not coin flips. Include normal, boundary (amount exactly at threshold, balance exactly zero, leave ending the day before a holiday, exactly at max days), failure and exception cases.

# 7. BASELINE COVERAGE (must appear in the data)
Overlapping leave, insufficient balance, weekend/holiday spans, missing receipt, duplicate receipt hash, policy limit breach, multi-level approval.

# 8. INJECTED, LABELLED EDGE CASES (Step 5, injected AFTER valid baseline records exist)
Inject each as a deliberate anomaly into a clean baseline, touching only the targeted rows. Never silently corrupt unrelated rows. Each anomaly gets a ground-truth row. At full scale inject at least ~12-25 per type (scale proportionally for starter, min 2):
1. NEGATIVE_LEAVE_BALANCE
2. OVERLAPPING_APPROVED_LEAVE (same employee, two APPROVED requests with intersecting dates)
3. EXPENSE_DATE_OUTSIDE_EMPLOYMENT (before hire_date or after termination_date)
4. SPLIT_CLAIM_THRESHOLD_EVASION (same employee, same vendor/category, multiple claims within a few days, each just under an approval threshold but summing over it)
5. MISSING_COST_CENTER
6. APPROVAL_BY_REQUESTER (self-approval)
7. DUPLICATE_REIMBURSEMENT (two RMB records for one claim)
Plus baseline-labelled types: INSUFFICIENT_BALANCE, WEEKEND_HOLIDAY_SPAN, MISSING_RECEIPT, DUPLICATE_RECEIPT_HASH, POLICY_LIMIT_BREACH, MULTI_LEVEL_APPROVAL (the last as an expected-decision label).
Keep a registry in injector.py: (issue_type, entity, entity_id, related_ids, injection_description, expected_detection_rule, severity).

# 9. GROUND TRUTH (Step 7)
Write a SEPARATE `ground_truth.csv` and `ground_truth.json` in `<out>/ground_truth/`, with columns: gt_id, issue_type, entity_type, entity_id, related_entity_ids, expected_decision (e.g., FLAG/REJECT/ESCALATE/APPROVE_WITH_MULTI_LEVEL), expected_approval_path, expected_reason_code, severity, injected(bool), injection_note. Also include a `expected_decisions` file giving the expected routing/decision for EVERY leave request and expense claim, derived from the documented rules.
The input tables must NOT contain issue_type, is_anomaly, ground_truth or any label column or leaked feature. Add a test that scans every input file's headers and values for leakage. Directory layout: `<out>/inputs/*.csv|json`, `<out>/ground_truth/*`, `<out>/sql/`.

# 10. RULE ENGINE / AUDIT (so "decision reasons are auditable")
audit.py is an INDEPENDENT detector that reads only the input files (never ground truth) and applies the documented rules to flag anomalies, recompute expected approval paths and produce an `audit_findings.csv` with: finding_id, issue_type, entity_id, rule_id, reason_code, human-readable reason, evidence JSON. Define a rule catalogue (docs/RULES.md) with rule IDs (e.g., LV-001 balance sufficiency, LV-002 overlap, LV-003 notice period, EX-001 receipt required, EX-002 duplicate receipt hash, EX-003 limit breach, EX-004 employment-date window, EX-005 split-claim detection with a window and a threshold-proximity ratio, AP-001 approval path matches thresholds, AP-002 no self-approval, AP-003 approver authority, RB-001 reimbursement only for approved eligible claims, RB-002 no duplicate reimbursement, CC-001 cost center required).

# 11. VALIDATION (Step 8)
validate.py checks and writes docs/validation_summary.md and .json with PASS/FAIL per check and counts: primary-key uniqueness for every table; foreign-key integrity for every relationship (including bridge tables and event tables); allowed enums; date ordering (hire <= leave start <= end, submit <= approval <= payment, effective_from <= effective_to); arithmetic reconciliation (claim total = sum of lines, balance closing = opening + accrued + adjusted - used, business days recomputed from calendar, reimbursement amount = approved lines); lifecycle transitions legal per the transition table and event history monotonic in time; duplicate checks (IDs, receipt hashes, reimbursements); ID format regexes. Distinguish: baseline invariants must have ZERO violations; every violation that exists must be explained by a ground-truth row (unexplained = FAIL, label-without-violation = FAIL). Exit non-zero on failure.

# 12. EVALUATION METRICS (measurable outputs)
evaluate.py compares audit_findings against ground_truth and writes docs/evaluation_report.md/.json: per-issue-type precision, recall, F1 and support; confusion summary; overall micro/macro F1; approval-path accuracy (derived path vs expected); decision accuracy; reimbursement eligibility accuracy; plus operational metrics: approval turnaround p50/p90 by level, rejection rate by category/country, auto-routing distribution by approval depth, % of claims with missing receipts, leave utilization per policy, total reimbursed amount, exception rate by country. Provide a few simple charts as PNG only if matplotlib is optional/installed; otherwise ASCII/Markdown tables (do not require heavy dependencies).

# 13. EXPORTS (Step 9)
For every table: CSV, JSON (array of objects), plus `sql/schema.sql` (CREATE TABLE with PK, FK, CHECK, UNIQUE where valid, and indexes) and `sql/seed.sql` (INSERT statements). Load the SQL into an in-memory SQLite DB in a test and run join-validation queries (every FK join returns the full child count). Also write `manifest.json` containing the seed, generator version, command, scale, row counts, and SHA-256 per file.

# 14. REPRODUCIBILITY (Step 10)
`repro-check` regenerates the full dataset twice into temp dirs with the same seed, compares row counts and SHA-256 of every file, and writes docs/reproducibility_report.md with a PASS/FAIL table. Also show that a different seed yields different checksums. Run it for real and paste the output.

# 15. TESTS
pytest suite (fast, offline) covering: ID formats/uniqueness, business-day calculation with weekends and holidays (incl. boundary dates), accrual math, routing at exact thresholds (boundary values), self-approval prevention in baseline, reimbursement-only-after-approval, each anomaly injector producing exactly its labelled rows, ground-truth non-leakage, validator catching a deliberately broken dataset, SQL load/join integrity, and reproducibility. All tests must pass with `make test`.

# 16. README (must let a stranger run it in minutes)
Include: overview; architecture diagram; quick start (`python -m venv`, install, `make all`); expected outputs and folder tree; CLI reference; how to run starter vs full; entity list with cardinalities (link to ERD); the routing rule tables; the anomaly catalogue with counts; how I verified correctness (validation, audit-vs-ground-truth metrics, tests, reproducibility results with actual numbers); assumptions; limitations and next steps; environment needs and runtime; a note on AI usage linking AI_USAGE.md and prompts/PROMPT_HISTORY.md; and a lawful-provenance statement (no external data; synthetic only).

# 17. HONESTY AND QUALITY BAR
- Everything you claim in the docs must be true and reflect actual command output. Don't invent numbers; paste real ones.
- If any requirement can't be met, state it plainly in docs/LIMITATIONS.md instead of hiding it.
- Keep code readable, typed, commented where the logic is non-obvious, with docstrings on every rule referencing its rule ID.
- Explain the key design decisions in docs/DECISIONS.md (why ledger-based balances, why independent audit module, why append-only events, how split-claim detection works, trade-offs) so I can defend them in an interview.

# 18. EXECUTION PHASES (stop after each, run it, show output, then continue)
Phase 1: scaffold repo, config, schema.py (single source of truth), ID generators, data dictionary generation.
Phase 2: master data (CostCenter, Employee, Holiday, policies, rules and bridges).
Phase 3: leave module (ledger, balances, requests, events, engine).
Phase 4: expense module (claims, lines, receipts, routing, approval steps, reimbursements, events, decision log).
Phase 5: anomaly injector + ground-truth export.
Phase 6: validator + audit + evaluation.
Phase 7: exports (CSV/JSON/SQL/manifest), SQLite join check, repro-check.
Phase 8: tests, README, docs, AI_USAGE.md, PROMPT_HISTORY.md, final `make all`, final checklist verifying every item in sections 3-16 with evidence.
At the end, output a requirement-by-requirement compliance table (requirement -> file/command -> result) and a list of commit messages.
```
