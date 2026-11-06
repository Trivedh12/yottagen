# YottaGen Architectural Design Decisions & Trade-Offs

This document explains the rationale behind key engineering and architectural decisions in YottaGen to facilitate rigorous technical reviews and interview defenses.

---

## 1. Why Ledger-Based Leave Balances Instead of Mutable Counters?

### Context & Problem
In naive HR and ERP implementations, employee leave balance is frequently modeled as a single mutable database column (e.g., `balance = balance - requested_days`). When bugs, race conditions, retroactive policy changes, or manual adjustments occur, mutable columns destroy auditability, making it impossible to reconstruct historical balances or verify why a balance became negative.

### Decision
YottaGen implements a **double-entry append-only accounting ledger** (`LeaveBalanceLedger`).
- **Postings**: Every change in entitlement is recorded as an immutable ledger transaction with a specific `entry_type` (`ACCRUAL`, `USAGE`, `ADJUSTMENT`, `CARRY_FORWARD`, `FORFEIT`), signed day delta, effective date, and source reference.
- **Materialized Snapshot**: `LeaveBalance` is a read-only materialized view derived purely from summing ledger postings:
  $$\text{closing\_balance} = \text{opening\_balance} + \text{accrued\_days} + \text{adjusted\_days} - \text{used\_days}$$
- **Benefits**:
  1. Complete historical reconstruction for any past date.
  2. Mathematical reconciliation guaranteed by `derive.py` and audited by `validate.py`.
  3. SOX/IFRS regulatory compliance: no retroactive overwriting of balances.

---

## 2. Why an Independent Audit Engine (`audit.py`) Decoupled from Ground Truth?

### Context & Problem
In many synthetic data and evaluation benchmarks, the detector "cheats" by reading the ground-truth labels directly or utilizing features created by the injector (data leakage). This produces artificially high metrics that fail in real-world deployment where ground-truth labels do not exist.

### Decision
YottaGen strictly separates generation, ground truth, and detection:
- `yottagen/injector.py` injects anomalies into clean tables and writes labels to a physically distinct directory `<out>/ground_truth/`.
- `yottagen/audit.py` reads **ONLY** the raw input tables (`<out>/inputs/*.csv|json`). It has zero access to ground truth, `is_anomaly` flags, or injection notes.
- A dedicated test (`tests/test_injection.py::test_no_data_leakage_in_input_tables`) scans every header and value in input tables to enforce zero label leakage.
- `yottagen/evaluate.py` acts as an external evaluation arbiter, comparing audit findings against ground truth to produce unbiased precision, recall, and F1 metrics.

---

## 3. Why Append-Only State Transition History (`LeaveRequestEvent`, `ExpenseClaimEvent`)?

### Context & Problem
When entities transition through states (`DRAFT` &rarr; `SUBMITTED` &rarr; `PENDING_APPROVAL` &rarr; `APPROVED` &rarr; `REIMBURSED`), simply updating the `status` column overwrites the history. Operations analysts cannot determine who approved what, when approvals occurred, or whether SLAs were met.

### Decision
Every lifecycle transition generates an immutable event record:
- Contains `from_status`, `to_status`, `actor_id`, ISO `timestamp`, and `reason_code`.
- Events are strictly monotonic in time.
- Validated against formal finite state machines (`LEAVE_REQUEST_TRANSITIONS` and `EXPENSE_CLAIM_TRANSITIONS`). Discontinuous chains or illegal transitions cause validation failure (`VAL-LIFE-007`).

---

## 4. How Split-Claim Detection (`EX-005`) Works & Trade-Offs

### Context & Problem
Employees attempting to bypass approval authority (e.g., Director sign-off required for expenses over $\$100$) may split a $\$184$ dinner into two separate claims of $\$92$ submitted on successive days.

### Decision & Algorithm
The detector in `yottagen/audit.py` applies a **temporal rolling window and threshold proximity ratio**:
1. Group claims by claimant employee (`employee_id`).
2. Sort claims chronologically by `submit_date`.
3. Evaluate a rolling 3-day window $[t, t + 3\text{ days}]$.
4. Identify candidate clusters where:
   - Each claim is below the target approval tier ($\text{claim.total\_amount\_base} \le \$100.00$).
   - The cumulative cluster total strictly exceeds the threshold ($\sum \text{claim.total\_amount\_base} > \$100.00$).
5. **Trade-offs**:
   - *False Positives*: A traveling employee might legitimately incur two genuine $\$90$ meals on back-to-back days. In production, this can be refined by incorporating merchant similarity (Levenshtein distance) and time-of-day checks.
   - *False Negatives*: Claims spaced 4 days apart evade the 3-day window. A wider window increases false positives; 3 days was selected as the optimal balance for corporate T&E audit.

---

## 5. Single Source of Truth (`schema.py`)

### Context & Problem
In data platforms, data dictionaries, database DDL (`CREATE TABLE`), and application validation code often drift out of sync over time as schemas evolve.

### Decision
`yottagen/schema.py` is the **single authoritative source of truth**:
- Defines entity models, fields, types, constraints, regexes, and enums.
- Dynamically generates `docs/data_dictionary.md`, `.csv`, and `.json`.
- Dynamically generates SQLite DDL `schema.sql` and seed scripts `seed.sql`.
- Directly powers `validate.py` invariant checks.
- Code and documentation drift is architecturally prevented.
