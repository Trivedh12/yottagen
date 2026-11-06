# YottaGen Modeling Assumptions & Synthetic Parameters

This document details all business, calendar, financial, and organizational assumptions incorporated into the YottaGen synthetic data generator and rule engine.

---

## 1. Temporal & Reference Anchors

1. **Fixed Reference "As-Of" Date**:
   - Pinned strictly to `2026-10-22` across all modules.
   - All balance calculations, tenure calculations, and lifecycle statuses are evaluated relative to this cutoff date.
   - `datetime.now()` is prohibited to ensure byte-level reproducibility.
2. **Deterministic Pseudorandom Generation**:
   - A single seeded `random.Random(seed)` instance is passed explicitly through all functions.
   - Default seed is `20261022`.
3. **Tenure Window**:
   - Company founding and earliest employee hire dates start in `2015-01-15`.
   - Leave requests and expense claims are distributed throughout the calendar year 2026 up to and slightly beyond the reference date (for future scheduled leaves).

---

## 2. Calendar, Weekends, and Holidays

1. **Standard Working Week**:
   - Defined as Monday through Friday (5 working days).
   - Saturdays and Sundays are non-working weekend days.
2. **Statutory Holiday Calendars**:
   - Supported jurisdictions: India (`IN`), United States (`US`), United Kingdom (`UK`), Germany (`DE`), and Singapore (`SG`).
   - Statutory holidays falling on a weekend are not double-counted; the calendar engine computes:
     $$\text{calendar\_days} = \text{business\_days} + \text{weekend\_days\_in\_span} + \text{holiday\_days\_in\_span}$$
   - Business days chargeable against an employee's leave balance exclude both weekends and weekday public holidays for their primary country of employment.

---

## 3. Financial & Currency Conversions

1. **Base Currency**:
   - United States Dollar (`USD`) is the reporting base currency.
2. **Fixed Exchange Rates**:
   - Fixed conversion rates to USD:
     - `USD`: $1.0000$
     - `EUR`: $1.0800$
     - `GBP`: $1.2800$
     - `SGD`: $0.7400$
     - `INR`: $0.0120$
   - All foreign transactions store both `amount_local` and the converted `amount_base`.
3. **Threshold Normalization**:
   - Approval routing rules and threshold tiers evaluate the claim's normalized `total_amount_base` in USD.

---

## 4. Organizational Hierarchy & Supervisory Chain

1. **Acyclic Hierarchy**:
   - Exactly one Chief Executive Officer (`CEO`, Level 6) at the root of the hierarchy.
   - Every other employee reports to a manager of equal or higher job level (`job_level >= 3` for line managers).
   - Managers are hired strictly on or before their subordinate reports (`manager.hire_date <= report.hire_date`).
2. **Segregation of Duties & Self-Approval Prohibition**:
   - Requesters are strictly prohibited from approving their own expense claims or leave requests.
   - When the CEO or top executives submit claims, approval is routed to the CFO, a senior VP peer, or an executive board delegate.

---

## 5. Expense Substantiation & Fraud Heuristics

1. **Receipt Substantiation**:
   - Receipts are mandatory for any individual line item exceeding $\$25.00$ base USD equivalent.
   - Receipts contain embedded cryptographic SHA-256 hashes generated from the itemized transaction tuple.
2. **Split-Claim Evasion**:
   - An employee submitting multiple claims within a rolling 3-day window to the same merchant or category where each claim is $\le \$100$ but their cumulative sum exceeds $\$100$ is flagged as an evasion attempt.

---

## 6. Leave Balance Accrual Architecture

1. **Ledger-Based Accounting**:
   - Leave balances are never stored as mutable counters.
   - Balances are derived point-in-time from an immutable journal of postings (`ACCRUAL`, `USAGE`, `ADJUSTMENT`, `CARRY_FORWARD`, `FORFEIT`).
   - Annual vacation leave accrues on the 1st of each calendar month at $1.75$ days/month (capped at $21$ days/year), with a maximum year-end carry-forward of $5.0$ days.
