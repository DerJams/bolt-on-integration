# Injection decisions for spec/defect_taxonomy.md

Decided by: an independent reviewing model, OpenAI GPT-6 Astra Ultra (as labeled in the ChatGPT interface), 2026-10-11.
Purpose: decide which taxonomy defects are artificially injected into the benchmark, made by a party with no access to and no stake in the tool under evaluation. James Thornton supplied the inputs (taxonomy, entity profile, corpus spec, chart README, evidence extracts) and the decision criteria; the decisions and justifications below are the reviewing model's, verbatim.

### Decisions

| row id | decision (yes / no / not applicable) | criterion applied (1 to 5) | one-sentence justification citing the specific evidence file or profile statistic |
|---|---|---:|---|
| CV01 | no | 2 | `profile.md` reports multiple raw legal-name spellings for 537 UEIs (13.3%), including 245 (6.1%) whose names still differ after normalization. |
| CV02 | no | 2 | `profile.md` reports 1,582 UEIs with multiple variants and 18,567 same-UEI pairs, supplying existing records for the cross-master duplication described in `pmistack_erp_consolidation.md`. |
| CV03 | no | 2 | `profile.md` reports raw-versus-normalized name differences in 3,451 records (39.2%), so name-formatting variation is already meaningful. |
| CV04 | no | 3 | `pmistack_erp_consolidation.md` recommends name standardization but does not specifically document trading-name versus legal-name aliases, and no other evidence extract supplies that support. |
| CV05 | no | 2 | `profile.md` reports multiple normalized addresses for 591 UEIs (14.6%) and formatting-only differences for another 26 UEIs. |
| CV06 | no | 3 | `pmistack_erp_consolidation.md` discusses identifier standardization and manual deduplication but does not establish that similar names with different identifiers represent distinct legal entities. |
| CV07 | yes | 1 | `estes_erp_pe_acquisitions.md` documents incomplete supplier records, `pmistack_erp_consolidation.md` identifies identifiers as cleanup fields, and taxonomy row CV07 reports zero blank primary UEIs. |
| CV08 | no | 2 | `profile.md` reports missing counties in 34.6% of records and missing business types in 3.9%, already supplying meaningful address or classification incompleteness. |
| CV09 | no | 2 | `profile.md` reports 436 UEIs with a different parent, 54 included child-parent pairs and 40 sibling groups. |
| CV10 | no | 2 | `profile.md` reports conflicting business-type flags for 1,211 UEIs (30.0%) and changing parent UEIs for 129 (3.2%), so conflicts already exist in available attributes. |
| COA01 | no | 4 | `coa/README.md` §§2–5 documents unrelated code schemes and differing terminology across the real charts, including ERPNext's "Debtors" and the target's receivables concepts. |
| COA02 | no | 4 | `coa/README.md` §5 identifies 73 target ledger accounts representing collapsed groups, including combined payables and accruals, which naturally provide many-to-one mapping conditions. |
| COA03 | no | 4 | ERPNext's 28 income-statement accounts versus the target's 77, together with the target's expense expansion in `coa/README.md` §5, provide the coarse-source/finer-target structure for split-required mappings. |
| COA04 | not applicable | 5 | Although `pmistack_erp_consolidation.md` documents unused legacy accounts, the taxonomy explicitly states that the supplied charts lack the usage data needed to identify them. |
| COA05 | yes | 1 | `consero_rollup_checklist.md` explicitly documents cash-basis add-ons, while taxonomy row COA05 reports that all four charts contain accrual accounts, leaving its absent-accrual-account condition unrepresented. |
| COA06 | not applicable | 5 | `houseblend_netsuite_100day.md` documents shipment-versus-invoicing recognition differences, but the taxonomy explicitly states that recognition basis is unobservable in these charts. |
| COA07 | no | 4 | The existing UCOA affiliate accounts identified in the taxonomy already supply the intercompany condition requiring elimination rules described in `houseblend_netsuite_100day.md`. |
| COA08 | no | 3 | `houseblend_netsuite_100day.md` discusses differing definitions and parallel IFRS/US GAAP books but does not document nonprofit net-assets versus for-profit equity integration. |
| COA09 | no | 4 | The UCOA affiliate operating accounts and absent corresponding platform accounts documented under COA07 already supply a structural target gap of the kind described in `houseblend_netsuite_100day.md`. |

### Flags

- **Unsupported specificity — CV04, CV06 and COA08:** Their cited extracts do not document the particular defects as stated; CV04's 551 natural DBA differences and COA08's natural net-asset rows independently reinforce the decision against injection.
- **Profile–taxonomy disagreement — CV06:** The taxonomy calls these distinct legal entities, but `profile.md` explicitly leaves cross-UEI identities unresolved and includes businesses that re-registered; the 154 identical-name and 39 near-name pairs do not establish distinct-entity ground truth.
- **Unsubstantiated profile statistic — CV07:** Zero blank UEIs is asserted in the taxonomy but omitted from `profile.md`'s missing-field table; the decision uses that reported zero, not an independently verified profile count.
- **Structural evidence — COA02, COA03 and COA09:** "Not established without mappings" does not establish absence; the supplied chart structure supports no injection, although the practitioner extracts do not explicitly demonstrate every mapping cardinality.
- **Applicability — COA04–COA06 and CV10:** Missing usage or recognition-policy information is not a measured zero; COA05's yes applies to absent accrual accounts, since account presence alone does not establish bookkeeping basis, and CV10 remains applicable through its available attributes.
- **Missing defects:** No additional evidence-supported, applicable defect was established beyond the taxonomy and its expressly listed exclusions.

### Consequences for the fill run (added by the repo owner, 2026-10-11)

- Inject: CV07, COA05. Not applicable: COA04, COA06. All other rows: no injection.
- CV07: blank primary UEI count verified at 0 across 8,800 rows before injection.
- CV06: decisions.csv keeps DO_NOT_MERGE_CONFLICTING_IDENTIFIER; record_pairs.csv marks these pairs "unknown" and scoring excludes them from pairwise precision and recall.
- COA05: cash-basis simulation applied to AddOn A only, by removing accrual account categories; affected mappings labeled MAP_REQUIRES_ACCOUNTING_POLICY.
- COA04 and COA06 go on the v2 list: testable once transaction history and recognition policy are added to the corpus.
