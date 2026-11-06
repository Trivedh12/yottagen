# YottaGen Reproducibility & Determinism Verification Report

- **Primary Reference Seed**: `20261022`
- **Perturbed Verification Seed**: `99999999`
- **Scale Configuration**: `starter`
- **Overall Bit-for-Bit Determinism Result**: **PASS**

## File-by-File SHA-256 Checksum Verification Table

| Relative File Path | Run A (Seed 20261022) | Run B (Seed 20261022) | Run C (Seed 99999999) | Deterministic (A==B) | Sensitive (A!=C) |
|---|---|---|---|---|---|
| `ground_truth/expected_decisions.csv` | `9e1b6aad6508...` | `9e1b6aad6508...` | `9c401e6cc8d9...` | **PASS** | PASS |
| `ground_truth/expected_decisions.json` | `a4062579da53...` | `a4062579da53...` | `3e05f715c0c5...` | **PASS** | PASS |
| `ground_truth/ground_truth.csv` | `a7052a1590dc...` | `a7052a1590dc...` | `5422bc6d8763...` | **PASS** | PASS |
| `ground_truth/ground_truth.json` | `b82c9da229e2...` | `b82c9da229e2...` | `376e6f272ae6...` | **PASS** | PASS |
| `inputs/approval_rule.csv` | `724df0003453...` | `724df0003453...` | `724df0003453...` | **PASS** | IDENTICAL |
| `inputs/approval_rule.json` | `80031c58125d...` | `80031c58125d...` | `80031c58125d...` | **PASS** | IDENTICAL |
| `inputs/approval_rule_category.csv` | `231733ba1b2c...` | `231733ba1b2c...` | `231733ba1b2c...` | **PASS** | IDENTICAL |
| `inputs/approval_rule_category.json` | `35c5793ed02b...` | `35c5793ed02b...` | `35c5793ed02b...` | **PASS** | IDENTICAL |
| `inputs/approval_rule_country.csv` | `868e8e0c51c3...` | `868e8e0c51c3...` | `868e8e0c51c3...` | **PASS** | IDENTICAL |
| `inputs/approval_rule_country.json` | `d2af70aabd41...` | `d2af70aabd41...` | `d2af70aabd41...` | **PASS** | IDENTICAL |
| `inputs/approval_step.csv` | `94b4514012f4...` | `94b4514012f4...` | `17d7f98c3de5...` | **PASS** | PASS |
| `inputs/approval_step.json` | `8759306751ea...` | `8759306751ea...` | `b32d94c6914f...` | **PASS** | PASS |
| `inputs/cost_center.csv` | `ce9812a5bfb7...` | `ce9812a5bfb7...` | `99aebd6b1a5e...` | **PASS** | PASS |
| `inputs/cost_center.json` | `60ca81408c5e...` | `60ca81408c5e...` | `73ee42b63061...` | **PASS** | PASS |
| `inputs/decision_log.csv` | `2bd4f03659c4...` | `2bd4f03659c4...` | `3f3fddf6c5d7...` | **PASS** | PASS |
| `inputs/decision_log.json` | `af904a46e7ed...` | `af904a46e7ed...` | `f1fd38938bdf...` | **PASS** | PASS |
| `inputs/employee.csv` | `f70bbd91d94b...` | `f70bbd91d94b...` | `86b368b94eca...` | **PASS** | PASS |
| `inputs/employee.json` | `d6abe571fb90...` | `d6abe571fb90...` | `f771b26310bd...` | **PASS** | PASS |
| `inputs/employee_cost_center_assignment.csv` | `09b4f9c39396...` | `09b4f9c39396...` | `38f7e3f94064...` | **PASS** | PASS |
| `inputs/employee_cost_center_assignment.json` | `86136ba17a74...` | `86136ba17a74...` | `3491fa1d5d29...` | **PASS** | PASS |
| `inputs/expense_claim.csv` | `a71cbfd73ede...` | `a71cbfd73ede...` | `8bbcb6fb5eb9...` | **PASS** | PASS |
| `inputs/expense_claim.json` | `ac8dd9e99470...` | `ac8dd9e99470...` | `682fdd8445c9...` | **PASS** | PASS |
| `inputs/expense_claim_event.csv` | `2f07a6b3e872...` | `2f07a6b3e872...` | `93dbf1e91f7d...` | **PASS** | PASS |
| `inputs/expense_claim_event.json` | `466341b345c5...` | `466341b345c5...` | `e05272a0e3bf...` | **PASS** | PASS |
| `inputs/expense_line.csv` | `273bb8835fb2...` | `273bb8835fb2...` | `d84c9bc1a294...` | **PASS** | PASS |
| `inputs/expense_line.json` | `d3c80e64e6bd...` | `d3c80e64e6bd...` | `3968e6bd7ee9...` | **PASS** | PASS |
| `inputs/expense_policy.csv` | `2c3a36030474...` | `2c3a36030474...` | `2c3a36030474...` | **PASS** | PASS |
| `inputs/expense_policy.json` | `203043391d2e...` | `203043391d2e...` | `203043391d2e...` | **PASS** | PASS |
| `inputs/holiday_calendar.csv` | `15f7e210a043...` | `15f7e210a043...` | `15f7e210a043...` | **PASS** | IDENTICAL |
| `inputs/holiday_calendar.json` | `628bb3a219a8...` | `628bb3a219a8...` | `628bb3a219a8...` | **PASS** | IDENTICAL |
| `inputs/leave_balance.csv` | `729443a0148d...` | `729443a0148d...` | `01ea66e399b3...` | **PASS** | PASS |
| `inputs/leave_balance.json` | `2a7d0a45c888...` | `2a7d0a45c888...` | `f2d67fd6aaa4...` | **PASS** | PASS |
| `inputs/leave_balance_ledger.csv` | `fed43175d91e...` | `fed43175d91e...` | `8239f393a0e3...` | **PASS** | PASS |
| `inputs/leave_balance_ledger.json` | `5ba0ee26a3b4...` | `5ba0ee26a3b4...` | `bff0b3d3afe0...` | **PASS** | PASS |
| `inputs/leave_policy.csv` | `996c1b32d916...` | `996c1b32d916...` | `996c1b32d916...` | **PASS** | PASS |
| `inputs/leave_policy.json` | `34bddecf5243...` | `34bddecf5243...` | `34bddecf5243...` | **PASS** | PASS |
| `inputs/leave_request.csv` | `9e2497fac1f4...` | `9e2497fac1f4...` | `91a3f02fdae4...` | **PASS** | PASS |
| `inputs/leave_request.json` | `013a192a5a42...` | `013a192a5a42...` | `61e65f0903d1...` | **PASS** | PASS |
| `inputs/leave_request_event.csv` | `a23d92dd11b0...` | `a23d92dd11b0...` | `25f76ce186fe...` | **PASS** | PASS |
| `inputs/leave_request_event.json` | `b01630ec5187...` | `b01630ec5187...` | `0012c6ae01e9...` | **PASS** | PASS |
| `inputs/reimbursement.csv` | `946923e620ad...` | `946923e620ad...` | `967851e46340...` | **PASS** | PASS |
| `inputs/reimbursement.json` | `a8d5b249e218...` | `a8d5b249e218...` | `b2c3434b5cc2...` | **PASS** | PASS |
| `sql/schema.sql` | `7806ef175173...` | `7806ef175173...` | `7806ef175173...` | **PASS** | PASS |
| `sql/seed.sql` | `9988a32cf8bd...` | `9988a32cf8bd...` | `6095ad8f1aa6...` | **PASS** | PASS |

## Determinism Architecture & Guarantees

1. **Single Random Stream**: All stochastic choices flow through a single `random.Random(seed)` instance explicitly passed to all generator functions.
2. **Fixed Reference As-Of Date**: Pinned to `2026-10-22` without reliance on `datetime.now()` or environment clocks.
3. **Topological & Lexicographical Ordering**: All collections, maps, and database inserts are sorted deterministically before output.
4. **Cross-Platform Canonical Formatting**: Files are serialized with strict `newline='\n'` and explicit fixed column sequences.
