# YottaGen Invariant Validation Summary

**Overall Verdict**: **PASS** (8/8 checks passed)

## Validation Results Matrix

| Check ID | Category | Invariant Rule | Status | Violations | Unexplained | Remarks |
|---|---|---|---|---|---|---|
| `VAL-PK-001` | Integrity | Primary Key Uniqueness | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-FK-002` | Integrity | Foreign Key Referential Integrity | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-ID-003` | Conformance | Canonical ID Format Regexes | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-ENUM-004` | Conformance | Allowed Enum Values | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-MATH-005` | Reconciliation | Arithmetic & Financial Reconciliation | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-DATE-006` | Chronology | Chronological Order Consistency | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-LIFE-007` | Lifecycle | Lifecycle Legal Transitions & Monotonic History | **PASS** | 0 | 0 | Clean - 0 unexplained |
| `VAL-GT-008` | GroundTruth | Ground Truth Anomaly Reconciliation | **PASS** | 0 | 0 | Clean - 0 unexplained |

## Invariant Rule Explanations

- **Primary Key Uniqueness (`VAL-PK-001`)**: Verifies strict uniqueness of primary keys across all 19 entities.
- **Foreign Key Integrity (`VAL-FK-002`)**: Validates referential integrity for core, event, and bridge tables. Missing references are permitted ONLY when explicitly labelled as ground-truth anomalies (`MISSING_COST_CENTER`).
- **Canonical ID Patterns (`VAL-ID-003`)**: Enforces canonical regular expression patterns (e.g. `EMP-000001`, `EXP-2026-000001`).
- **Enum Values (`VAL-ENUM-004`)**: Ensures all status codes, categories, and countries match schema definitions.
- **Arithmetic Reconciliation (`VAL-MATH-005`)**: Mathematical proof of financial and ledger reconciliations (`claim_total = SUM(lines)`, `closing = opening + accrued + adjusted - used`).
- **Chronological Order (`VAL-DATE-006`)**: Validates sequential order of hire dates, leave spans, submission dates, approval times, and disbursement dates.
- **Lifecycle State Transitions (`VAL-LIFE-007`)**: Enforces state machines and monotonic timestamps for leave requests and expense claims.
- **Ground Truth Reconciliation (`VAL-GT-008`)**: Confirms every injected anomaly type is registered and matched in `ground_truth.csv`.
