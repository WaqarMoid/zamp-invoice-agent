# Golden Pipeline Regression Results

| Fixture | Expected Decision | Key Assertions | Status |
|---|---|---|---|
| F01 | APPROVE | Clean two-way match (invoice to PO), all checks PASS | PASS |
| F02 | REVIEW | Over-billing 14 trips vs 10 trips unbilled (C15 FLAG) | PASS |
| F03 | REVIEW | Inferred PO-2026-0431 with 100% score (C10 FLAG) | PASS |
| F04 | REJECT | Duplicate of seed invoice BIS-INV-2026-0089 (C09 REJECT) | PASS |
| F05 | HOLD | Bank account change alert differs from master (C07 HOLD) | PASS |
| F06 | APPROVE | Split PO within 10-trip balance, fully billed (C15 PASS) | PASS |
| F07 | APPROVE | Tax-inclusive pricing 5% converted to net (C21 INFO) | PASS |
| F08 | REJECT | Inactive vendor + closed PO + outside validity | PASS |
| F09 | REVIEW | Missing invoice number and date (C01 FLAG) | PASS |

### Sequence Scenarios
- **F06 then F02**: F02 detects remaining = 0 trips, over by 14 trips.
- **F01 then F01**: Exact duplicate rejected, `same_file_as_run` linked.
- **F02 human approve**: Overrun approved, PO becomes `OVERBILLED` at 108%.
- **F05 human review**: Bank verification guard enforced (422 without verification).
