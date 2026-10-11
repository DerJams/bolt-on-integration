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
| Real industry framing of PlatformCo (which NAICS group it is in) | NAICS 2382, building equipment contractors (electrical, plumbing, HVAC): a multi-site services business | Largest NAICS group in the real record pool (2,743 UEIs, `entities/profile.md`). No evidence extract names an industry for the generic case (`evidence/ssa_dental_rollup_playbook.md` is dental), so this is framing only and changes no generated data |
| Which NAICS groups the add-ons are in | NAICS 2382 for all three add-ons | Consolidating onto the parent suits businesses that closely resemble each other (`evidence/estes_erp_pe_acquisitions.md`); different verticals are kept separate (`evidence/pmistack_erp_consolidation.md`). Framing only |
| Whether each entity's records serve as customer master, vendor master, or both | Both. Each entity holds a customer master and a vendor master. Each group of linked UEIs is drawn into one domain (seeded, 50/50); a UEI is in the same domain in every entity, so no candidate pair crosses domains | Customers and suppliers both need golden records (`evidence/pmistack_erp_consolidation.md`) and review before a move (`evidence/estes_erp_pe_acquisitions.md`). The 50/50 draw is a design parameter; no evidence sets it |
| Integration depth assumed (full, hybrid financial spine, reporting-only) | Hybrid financial spine: one chart of accounts, GL and consolidation; customer and vendor masters governed centrally; operational systems left in place | Option 2 in `evidence/pmistack_erp_consolidation.md`; matches the stated goal of common financial reporting and master-data governance |

## 2. Schemas

### 2.1 Customer and vendor master

Fields as in `schemas/entity_master.md`. These come from the real USAspending records in `entities/recipient_records.csv`.

| decision | value | rationale and citation |
|---|---|---|
| Fields exposed to the system under test (hidden: defect tag, source UEI if withheld) | Every column of `entities/recipient_records.csv` under a new `record_id`. Hidden, in `answer_key/<domain>/records_hidden.csv`: source record id, true UEI, defect ids | Identifiers, names and addresses are the cleanup fields named in `evidence/pmistack_erp_consolidation.md`; hidden columns hold only answer-key data (`docs/corpus-fill-prompt.md` Task 2) |
| Whether `recipient_uei` is visible, masked, or partly withheld per entity | Visible in every entity; blanked only on the injected CV07 records (438 of 8,800, 5% per domain per entity) | Tax identifiers are standard master-data fields (`evidence/pmistack_erp_consolidation.md`); a missing one is CV07 (`evidence/estes_erp_pe_acquisitions.md`). Consequence: a same-UEI matcher reaches pairwise F1 0.95 on dev, so the difficulty sits in the escalation items |
| Record id scheme per entity (must not leak cluster membership) | `<prefix>-<6 random digits>`, prefixes PLT, AOA, AOB, AOC, drawn from the seed; rows shuffled | Ids and row order carry no cluster information, as this row requires; the format is a design parameter |

### 2.2 Chart of accounts

Columns as in `schemas/chart_of_accounts.md`. Charts are in `coa/`; see `coa/README.md` for provenance.

| decision | value | rationale and citation |
|---|---|---|
| Platform target chart | `coa/us_gaap_platform_target.csv` (280 accounts derived from the GAAP subset by the rule and named expansion in `coa/README.md` section 5) | The platform sets one standard chart and each add-on is mapped onto it (`evidence/consero_rollup_checklist.md`); the full 951-row reporting taxonomy is too fine to receive many-to-one mappings, so an operating-size chart is derived from it reproducibly |
| AddOn A source chart | `coa/quickbooks_online_types.csv` | QuickBooks Online is named as the transitional system small acquired entities arrive on (`evidence/pmistack_erp_consolidation.md`) |
| AddOn B source chart | `coa/ucoa_nonprofit.csv` | Account definitions differ across systems, here net assets versus equity (`evidence/houseblend_netsuite_100day.md`) |
| AddOn C source chart | `coa/erpnext_standard_numbered.csv` | Acquired companies run a spread of small-business ERPs with their own numbered charts, separate from the parent's (`evidence/estes_erp_pe_acquisitions.md`) |
| Subset of each chart used (all rows, or a filtered subset) | All rows are kept in the input charts. Mapped: postable accounts only, i.e. QuickBooks detail types (274; type rows are categories), UCOA leaf accounts (180), ERPNext ledger accounts (54). AddOn A loses 16 accounts and 2 emptied type headers to COA05 | Like transactions are mapped so they land together (`evidence/houseblend_netsuite_100day.md`); the cash-basis removal follows `evidence/consero_rollup_checklist.md` |

## 3. Answer key layers

Three layers, produced for customers, vendors, and chart of accounts. Outcome labels come only from `spec/defect_taxonomy.md`.

1. **Record pair**: `record_pairs.csv` with `record_id_a, record_id_b, same_entity (true/false)`.
2. **Entity cluster**: `entity_clusters.csv` with `record_id, cluster_id, is_golden_record`, after the survivorship rule.
3. **Decision label**: `decisions.csv` with `record_id or mapping_id, outcome_label, rationale`. For the chart of accounts, `coa_mappings.csv` with `source_code, target_code, mapping_type, rationale, business_decision_required`.

| decision | value | rationale and citation |
|---|---|---|
| Ground-truth rule for "same entity" (for example: same UEI) | Same UEI: `match`. Different UEIs: `non-match`, except pairs with identical or near-identical normalized names (CV06) or a shared normalized street address and ZIP5: `unknown`. Name similarity overrides hierarchy, and hierarchy overrides shared address. `record_pairs.csv` puts match, non-match or unknown in `same_entity` (owner instruction, 2026-10-11) | UEI is the registered identifier (`evidence/pmistack_erp_consolidation.md`); `entities/profile.md` leaves cross-UEI identities unresolved, so they are unknown (`docs/injection_decisions.md`) |
| How parent-child pairs are labelled in `record_pairs.csv` | `non-match`, decision AUTO_RESOLVE_NON_MATCH (CV09); siblings under one reported parent the same. 30 of the 54 parent-child UEI pairs also share a name and are `unknown` (CV06 takes precedence) | Each legal entity is its own subsidiary in one hierarchy (`evidence/houseblend_netsuite_100day.md`) |
| Candidate pair set for `record_pairs.csv` (all pairs within blocks, or sampled negatives; how many) | Per folder and domain: every same-UEI pair; every record pair of the CV06, parent-child, sibling and shared-address UEI pairs; plus negatives sampled from same-ZIP5, different-UEI pairs, as many as the match pairs. Scoring derives the truth for any other pair from `entity_clusters.csv` | Blocking on location follows address standardisation (`evidence/pmistack_erp_consolidation.md`); the negative count is a design parameter |
| Survivorship rule for the golden record (field by field) | Golden record: latest `last_seen`, then most awards, then the PlatformCo record. UEI: true UEI. DUNS and CAGE: most frequent non-blank. Legal name and address: the golden record's. DBA, parent, business types, organizational type: most recent non-blank. NAICS: union. Each value's source record is in `golden_records.csv` | Golden records for customers and suppliers (`evidence/pmistack_erp_consolidation.md`); the platform is the reference template (`evidence/consero_rollup_checklist.md`). The recency order is a design parameter |
| Criteria for `business_decision_required = true` in CoA mappings | True for MAP_SPLIT_REQUIRED (an allocation rule is needed) and MAP_REQUIRES_ACCOUNTING_POLICY (no settled target, related party, net assets, cash basis). False for MAP_DIRECT and MAP_MANY_TO_ONE. A mapping counts as settled when the source account's own name, type or cross-reference names the target concept, or a part of a collapsed target total (`coa/README.md` section 5) | `evidence/houseblend_netsuite_100day.md` (like transactions land together; dummy accounts; elimination rules); `evidence/consero_rollup_checklist.md` (cash to accrual) |

Where evidence does not settle a CoA mapping, the label is `MAP_REQUIRES_ACCOUNTING_POLICY`, not a guess.

## 4. Dev / holdout split

Fixed by `docs/fill_run_rules.md`: split by entity cluster, not by record, so that no pair crosses folders. Ratio is 60/40 per entity (prompt-specified). Answer keys go in the matching folder. The person building the tool under test must not see `synthetic/holdout/` answer keys.

| decision | value | rationale and citation |
|---|---|---|
| How CoA rows are split (by source account, by target account group) | By target account within each add-on: all rows on one target, plus rows linked to it by a split, go to one folder; policy rows with no target are split one by one; 60/40 per add-on | Keeps many-to-one groups whole, as entity clusters are kept whole (`docs/fill_run_rules.md` rule 2); ratio prompt-specified |
| Tolerance for the 60/40 ratio after cluster-level splitting | Records: 60% ± 2 points per entity and domain (achieved 60.1% to 61.1%). CoA rows: 60% ± 5 points per add-on (achieved 59.3% to 60.0%). The generator stops if either is exceeded | Ratio prompt-specified; tolerances are design parameters, wider for CoA because many-to-one groups are large relative to the charts |

## 5. Partition and injection

| decision | value | rationale and citation |
|---|---|---|
| Seed | 3391519676 (drawn once with `secrets`, stored in `synthetic/SEED.txt`) | prompt-specified |
| Relative size of PlatformCo vs each add-on | Each record drawn independently: 40% PlatformCo, 20% each add-on (3,574 / 1,752 / 1,774 / 1,700 records) | The platform is the larger base that add-ons are mapped onto (`evidence/consero_rollup_checklist.md`, `evidence/alixpartners_integration_ready_platform.md`); the weights are a design parameter |
| Partition constraint (minimum split and kept-together natural duplicate pairs) | at least 15 split across entities, at least 15 kept together; re-draw until met; record attempts | prompt-specified (`docs/fill_run_rules.md`) |
| Injection rate per defect | 2 to 8 percent of records per domain per entity, after partition | prompt-specified |
| Per-defect rate within that range | CV07: 5% of records per domain per entity (4.96% to 5.03% achieved). COA05: AddOn A only, 16 of 274 ledger accounts (5.84%) | prompt-specified (`docs/fill_run_rules.md` rule 3); COA05 scope set by the repo owner |

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
| Headline metric and pass thresholds | Headline: unsafe automation rate. Pass on holdout: unsafe automation at most 1% and correct escalation at least 90%. Pairwise F1, mapping accuracy and safe automation rate reported alongside | Uncorrected data spreads into the parent after cutover (`evidence/estes_erp_pe_acquisitions.md`); manual review is expected even with automation (`evidence/pmistack_erp_consolidation.md`). No extract gives numbers: thresholds are design parameters for the repo owner to confirm |
| Required evidence fields per decision for evidence completeness | Pair: both record ids, at least one field compared, the rule or citation. Record: its id, the missing or conflicting field, the rule. Cluster: two or more record ids, the conflicting field, the rule. Mapping: the target code (not needed for MAP_REQUIRES_ACCOUNTING_POLICY or EXCLUDE_OR_RETIRED_ACCOUNT) and the rule or citation | Follows the metric definition above (record ids, matching fields, rule or citation); an owner for every record (`evidence/estes_erp_pe_acquisitions.md`) |
| Whether an unsafe automation carries a heavier penalty than a missed automation | Yes, through the pass rule: unsafe automation is capped at 1%, while a missed automation only lowers the safe automation rate. No composite weighting | Bad data spreads into the parent ERP (`evidence/estes_erp_pe_acquisitions.md`); clean first, migrate second (`evidence/pmistack_erp_consolidation.md`) |
