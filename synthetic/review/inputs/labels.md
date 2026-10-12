# Chart-of-accounts outcome labels

Inputs for an independent mapping of each add-on chart onto the platform target chart. The charts in this folder
are exactly as the benchmark presents them: `PlatformCo_chart.csv` is the platform target, and `AddOnA_chart.csv`,
`AddOnB_chart.csv`, `AddOnC_chart.csv` are the three add-on source charts. `charts.json` tags AddOn A
`cash_basis: true`: it keeps cash-basis books, and its accrual accounts are absent from its chart.

## Labels (exactly one per mapping row)

- `MAP_DIRECT`: the source account is the same concept as one target account, and no other account of the same add-on chart maps to that target.
- `MAP_MANY_TO_ONE`: the source account maps to one target account that two or more accounts of the same add-on chart also roll into.
- `MAP_SPLIT_REQUIRED`: the source account's balance must be divided across two or more target accounts.
- `MAP_REQUIRES_ACCOUNTING_POLICY`: no target can be settled without an accounting-policy or business decision, so the mapping is escalated rather than guessed.
- `EXCLUDE_OR_RETIRED_ACCOUNT`: the source account is unused or obsolete and should be retired rather than mapped.

## Rows to produce

Columns: `addon, source_code, target_code, mapping_type, business_decision_required, rationale`.

- `addon`: `AddOnA`, `AddOnB` or `AddOnC`.
- One row per postable source account: in `AddOnA_chart.csv` every row with a `parent_code` (QuickBooks detail types;
  rows without one are account-type categories); in `AddOnB_chart.csv` every four-digit code that is no other row's
  `parent_code`; in `AddOnC_chart.csv` every row whose `description` starts with `ledger account`.
- AddOn A is cash basis. For each platform target account that it can no longer populate on an accrual basis,
  add one row with `source_code` `cash_basis::<target_code>` and `target_code` that target account.
- `target_code`: a `gl_code` from `PlatformCo_chart.csv`; several codes joined with `;` for `MAP_SPLIT_REQUIRED`;
  may be empty for `MAP_REQUIRES_ACCOUNTING_POLICY` and `EXCLUDE_OR_RETIRED_ACCOUNT`.
- `business_decision_required`: `true` or `false`.
