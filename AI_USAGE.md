# AI Assistance & Verification Disclosure (`AI_USAGE.md`)

This document discloses how AI tools were utilized during the design, development, and QA validation of YottaGen, detailing areas of acceleration, heavy reliance, and personal review.

---

## 1. Where AI Accelerated Development
- **Scaffolding Repetitive Boilerplate**:
  - Drafting initial Python dataclasses and schema field definitions across the 19 entities.
  - Curating culturally diverse, synthetic international name pools (first and last names) and cities across IN, US, UK, DE, and SG.
  - Generating standard Markdown table formatting and Mermaid syntax for the comprehensive Entity Relationship Diagram (`docs/ERD.md`).
- **Test Generation Speed**:
  - Creating parameterized test assertions across regular expressions, boundary conditions, and mock datasets.

---

## 2. Where AI Was Relied Upon Heavily
- **Complex Multi-Tier Routing Logic Formulation**:
  - Structuring the combinatorial rules matrix across expense amount tiers ($\le \$100$, $\$100-\$1000$, $\$1000-\$5000$, $>\$5000$), expense categories (Equipment $> \$250$), country overrides (DE lodging $> \$180$, IN lodging $> \$150$), and leave duration bands.
- **SQL DDL & Seed Script Generation Logic**:
  - Formulating the topological dependency ordering to ensure parent records precede child foreign key inserts.

---

## 3. What Was Personally Reviewed, Changed, and Validated
- **Prevention of Executive Self-Approval Bug**:
  - *Observation*: During initial expense generation, the CEO (`EMP-000001`) was assigned as approver for their own expense claim because their manager chain was empty.
  - *Fix*: Personally overhauled `yottagen/routing.py` to strictly enforce `used_approvers = [claimant_id]` and delegate CEO claims to senior VP peers (Level 5) or CFO, maintaining zero self-approval (`AP-002`).
- **Chronological Monotonic Event Sequencing**:
  - *Observation*: Leave events with same-day submission and approval previously had subtle timestamp collision when leaves were marked consumed in the past.
  - *Fix*: Enforced strict chronological offsets (`submit_time < routed_time < approval_time < consumed_time`) in `yottagen/leave.py` and `yottagen/expense.py`.
- **Ledger Mathematical Reconciliation**:
  - *Observation*: Double-precision floating-point rounding drifts occurred in cumulative monthly accrual additions.
  - *Fix*: Enforced strict `round(..., 2)` financial quantization across ledger accruals, usages, balances, line items, and reimbursements.
- **SQLite Foreign Key & Mutual Dependency Handling**:
  - *Observation*: Circular foreign key dependency between `cost_center.manager_id` (referencing `employee`) and `employee.cost_center_id` (referencing `cost_center`) caused SQLite initial insert deadlocks when foreign keys were active during `INSERT INTO`.
  - *Fix*: Wrapped bulk seed insertion in `PRAGMA foreign_keys = OFF;` ... `PRAGMA foreign_keys = ON;` in `seed.sql` and ensured non-null foreign keys pass strict join tests.
- **Audit Findings & Ground Truth Precision**:
  - *Observation*: Initial audit of weekend/holiday spans had disparity due to slicing.
  - *Fix*: Aligned `injector.py` and `audit.py` to guarantee consistent detection and achieved $\ge 96.6\%$ Macro F1 and $99.9\%$ Micro F1.
