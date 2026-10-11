# Corpus spec: roll-up integration benchmark

Status: template. Every synthetic design decision is marked `[FILL]`. The later pass may replace only `[FILL]` markers, each with a concrete decision and a one-line rationale citing an `evidence/` file (or "prompt-specified" where `docs/fill_run_rules.md` allows it). All other text is fixed.

## 1. Scenario

A PE-backed, multi-site services platform ("PlatformCo") has acquired three smaller add-ons ("AddOn A", "AddOn B", "AddOn C"). Each add-on keeps its own chart of accounts and its own customer and vendor masters at close. The integration goal is common financial reporting and master-data governance on the platform.

Evidence for the shape of the problem:
- A standard chart is set on the platform and each add-on is mapped onto it: `evidence/consero_rollup_checklist.md`.
- Customers and suppliers need golden records; the same customers sit in several databases: `evidence/pmistack_erp_consolidation.md`.
- Duplicate customers and incomplete supplier records carry into the parent ERP if not cleaned before cutover: `evidence/estes_erp_pe_acquisitions.md`.
- CoA harmonisation and master data are 100-day work items: `evidence/houseblend_netsuite_100day.md`.

No new company identities are created. All customer and vendor records come from `entities/recipient_records.csv`; all accounts come from `coa/`.

| decision | value | rationale and citation |
|---|---|---|
| Real industry framing of PlatformCo (which NAICS group it is in) | [FILL] | [FILL] |
| Which NAICS groups the add-ons are in | [FILL] | [FILL] |
| Whether each entity's records serve as customer master, vendor master, or both | [FILL] | [FILL] |
| Integration depth assumed (full, hybrid financial spine, reporting-only) | [FILL] | [FILL] |

## 2. Schemas

### 2.1 Customer and vendor master

Fields as in `schemas/entity_master.md`. These come from the real USAspending records in `entities/recipient_records.csv`.

| decision | value | rationale and citation |
|---|---|---|
| Fields exposed to the system under test (hidden: defect tag, source UEI if withheld) | [FILL] | [FILL] |
| Whether `recipient_uei` is visible, masked, or partly withheld per entity | [FILL] | [FILL] |
| Record id scheme per entity (must not leak cluster membership) | [FILL] | [FILL] |

### 2.2 Chart of accounts

Columns as in `schemas/chart_of_accounts.md`. Charts are in `coa/`; see `coa/README.md` for provenance.

| decision | value | rationale and citation |
|---|---|---|
| Platform target chart | `coa/us_gaap_platform_target.csv` (270 accounts derived from the GAAP subset by the rule in `coa/README.md` section 5) | The platform sets one standard chart and each add-on is mapped onto it (`evidence/consero_rollup_checklist.md`); the full 951-row reporting taxonomy is too fine to receive many-to-one mappings, so an operating-size chart is derived from it reproducibly |
| AddOn A source chart | `coa/quickbooks_online_types.csv` | QuickBooks Online is named as the transitional system small acquired entities arrive on (`evidence/pmistack_erp_consolidation.md`) |
| AddOn B source chart | `coa/ucoa_nonprofit.csv` | Account definitions differ across systems, here net assets versus equity (`evidence/houseblend_netsuite_100day.md`) |
| AddOn C source chart | `coa/erpnext_standard_numbered.csv` | Acquired companies run a spread of small-business ERPs with their own numbered charts, separate from the parent's (`evidence/estes_erp_pe_acquisitions.md`) |
| Subset of each chart used (all rows, or a filtered subset) | [FILL] | [FILL] |

## 3. Answer key layers

Three layers, produced for customers, vendors, and chart of accounts. Outcome labels come only from `spec/defect_taxonomy.md`.

1. **Record pair**: `record_pairs.csv` with `record_id_a, record_id_b, same_entity (true/false)`.
2. **Entity cluster**: `entity_clusters.csv` with `record_id, cluster_id, is_golden_record`, after the survivorship rule.
3. **Decision label**: `decisions.csv` with `record_id or mapping_id, outcome_label, rationale`. For the chart of accounts, `coa_mappings.csv` with `source_code, target_code, mapping_type, rationale, business_decision_required`.

| decision | value | rationale and citation |
|---|---|---|
| Ground-truth rule for "same entity" (for example: same UEI) | [FILL] | [FILL] |
| How parent-child pairs are labelled in `record_pairs.csv` | [FILL] | [FILL] |
| Candidate pair set for `record_pairs.csv` (all pairs within blocks, or sampled negatives; how many) | [FILL] | [FILL] |
| Survivorship rule for the golden record (field by field) | [FILL] | [FILL] |
| Criteria for `business_decision_required = true` in CoA mappings | [FILL] | [FILL] |

Where evidence does not settle a CoA mapping, the label is `MAP_REQUIRES_ACCOUNTING_POLICY`, not a guess.

## 4. Dev / holdout split

Fixed by `docs/fill_run_rules.md`: split by entity cluster, not by record, so that no pair crosses folders. Ratio is 60/40 per entity (prompt-specified). Answer keys go in the matching folder. The person building the tool under test must not see `synthetic/holdout/` answer keys.

| decision | value | rationale and citation |
|---|---|---|
| How CoA rows are split (by source account, by target account group) | [FILL] | [FILL] |
| Tolerance for the 60/40 ratio after cluster-level splitting | [FILL] | [FILL] |

## 5. Partition and injection

| decision | value | rationale and citation |
|---|---|---|
| Seed | [FILL] | prompt-specified |
| Relative size of PlatformCo vs each add-on | [FILL] | [FILL] |
| Partition constraint (minimum split and kept-together natural duplicate pairs) | at least 15 split across entities, at least 15 kept together; re-draw until met; record attempts | prompt-specified (`docs/fill_run_rules.md`) |
| Injection rate per defect | 2 to 8 percent of records per domain per entity, after partition | prompt-specified |
| Per-defect rate within that range | [FILL] | [FILL] |

## 6. Metrics

Definitions are fixed. Thresholds and weightings are `[FILL]`.

- **Precision** (pair level): of predicted same-entity pairs, the share that are same-entity in the key.
- **Recall** (pair level): of same-entity pairs in the key, the share predicted.
- **F1**: harmonic mean of precision and recall.
- **Mapping accuracy** (CoA): share of source accounts whose predicted target code and mapping type both equal the key.
- **Safe automation rate**: share of all items the system resolved automatically (any `AUTO_RESOLVE_*` or `MAP_DIRECT` / `MAP_MANY_TO_ONE` / `MAP_SPLIT_REQUIRED` / `EXCLUDE_OR_RETIRED_ACCOUNT` without escalation) where the decision equals the key.
- **Correct escalation rate**: of items whose key label is an `ESCALATE_*`, `DO_NOT_MERGE_CONFLICTING_IDENTIFIER`, or `MAP_REQUIRES_ACCOUNTING_POLICY` label, the share the system escalated or withheld instead of acting.
- **Unsafe automation rate**: share of all items the system resolved automatically where the key says escalate, do-not-merge, or requires-policy, or where the automatic decision is wrong.
- **Evidence completeness**: share of the system's decisions that include the fields named as required for that label (record ids compared, matching fields, rule or citation used).

| decision | value | rationale and citation |
|---|---|---|
| Headline metric and pass thresholds | [FILL] | [FILL] |
| Required evidence fields per decision for evidence completeness | [FILL] | [FILL] |
| Whether an unsafe automation carries a heavier penalty than a missed automation | [FILL] | [FILL] |
