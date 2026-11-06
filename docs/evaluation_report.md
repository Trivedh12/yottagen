# YottaGen Audit Evaluation & Operational KPI Report

## 1. Executive Summary & Accuracy Scores

- **Macro F1 Score**: `0.9966`
- **Micro F1 Score**: `0.9993`
- **Overall Precision**: `1.0000`
- **Overall Recall**: `0.9987`
- **Decision Accuracy**: `0.9458`
- **Approval Path Routing Accuracy**: `1.0000`
- **Reimbursement Eligibility Accuracy**: `1.0000`

## 2. Per-Issue Type Precision, Recall, and F1 Metrics

| Issue / Anomaly Type | Support | TP | FP | FN | Precision | Recall | F1 Score |
|---|---|---|---|---|---|---|---|
| `APPROVAL_BY_REQUESTER` | 15 | 15 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `DUPLICATE_REIMBURSEMENT` | 15 | 15 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `EXPENSE_DATE_OUTSIDE_EMPLOYMENT` | 15 | 15 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `INSUFFICIENT_BALANCE` | 24 | 24 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `MISSING_COST_CENTER` | 15 | 15 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `MISSING_RECEIPT` | 94 | 94 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `NEGATIVE_LEAVE_BALANCE` | 15 | 15 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `OVERLAPPING_APPROVED_LEAVE` | 15 | 14 | 0 | 1 | 1.0000 | 0.9333 | **0.9655** |
| `SPLIT_CLAIM_THRESHOLD_EVASION` | 30 | 30 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| `WEEKEND_HOLIDAY_SPAN` | 531 | 531 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |

## 3. Operational KPIs & Workflow Telemetry

### 3.1 Approval Turnaround Hours (p50 / p90 by Job Level)
| Job Level | Role Authority | p50 Turnaround (hrs) | p90 Turnaround (hrs) |
|---|---|---|---|
| Level 3 | Line Manager | 7.5h | 7.5h |
| Level 4 | Director | 11.0h | 11.0h |
| Level 5 | Vice President | 14.5h | 14.5h |
| Level 6 | CEO / Board | 15.0h | 15.0h |

### 3.2 Rejection Rate by Country Jurisdiction
| Country | Rejection Rate (%) |
|---|---|
| `DE` | 10.91% |
| `IN` | 10.31% |
| `SG` | 7.78% |
| `UK` | 11.65% |
| `US` | 6.27% |

### 3.3 Rejection Rate by Expense Category
| Category | Rejection Rate (%) |
|---|---|
| `CLIENT_ENTERTAINMENT` | 15.85% |
| `EQUIPMENT` | 12.08% |
| `LODGING` | 16.39% |
| `MEALS` | 12.57% |
| `MISC` | 13.51% |
| `SOFTWARE` | 12.96% |
| `TRAINING` | 11.32% |
| `TRAVEL` | 15.00% |

### 3.4 Approval Depth Distribution
| Depth (Steps) | Scope / Tiers | Claims & Requests |
|---|---|---|
| 1 Step(s) | Single Manager Review | 157 |
| 2 Step(s) | Manager + Dept Head / HR | 360 |
| 3 Step(s) | Manager + Director + Finance | 483 |
| 4 Step(s) | Executive VP / CFO Review | 30 |

### 3.5 Financial & Policy Utilization Highlights
- **Missing Receipts Volume**: `3.02%` of incurred line items.
- **Total Disbursed Reimbursements**: `$24,137,146.79`.
- **Leave Entitlement Utilization by Policy**:
  - Policy `LPOL-01`: **4.30%** consumed vs accrued.
  - Policy `LPOL-02`: **1.53%** consumed vs accrued.
  - Policy `LPOL-03`: **1.22%** consumed vs accrued.
  - Policy `LPOL-04`: **0.00%** consumed vs accrued.
  - Policy `LPOL-05`: **0.00%** consumed vs accrued.
  - Policy `LPOL-06`: **0.00%** consumed vs accrued.
