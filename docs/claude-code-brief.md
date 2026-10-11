# Claude Code brief: assemble the roll-up integration benchmark scaffold

## Goal
Gather real public data and evidence into a versioned repo so a separate LLM can fill in the synthetic layer later. Do not generate any synthetic records, mappings, or answer keys in this pass. Everything you produce here must be real, downloaded, or cited.

## Repo layout to create
```
bolt-on-integration/
  README.md
  sources/           # raw downloads, untouched
  evidence/          # case-study extracts with citations
  schemas/           # field specs derived from evidence
  coa/               # real public charts of accounts
  entities/          # real public entity records
  er-benchmarks/     # public entity-resolution datasets
  spec/              # defect taxonomy + corpus spec (templates with blanks)
  scripts/           # download and profiling scripts
  MANIFEST.json      # every file, its source URL, download date, SHA-256
```

## Task 1: Real entity records (customers and vendors)
- Pull recipient records from the USAspending API (no key needed). Target 3,000 to 5,000 recipients from a single state and two or three NAICS groups in services (for example dental or medical offices, HVAC and plumbing contractors, staffing). Capture: recipient name, parent recipient name, UEI, parent UEI, address fields, business types.
- If SAM.gov public entity extract is reachable without an account, pull matching entities for the same UEIs to get legal name versus DBA variants. If it requires login, skip and note it in README.
- Write `scripts/profile_entities.py` that reports naturally occurring messiness: near-duplicate names, shared addresses, parent-child pairs, missing fields. Save the report to `entities/profile.md`. This tells us which defects are already real and which must be injected.

## Task 2: Real charts of accounts
Download or transcribe at least four public charts into `coa/` as CSV with columns: gl_code, account_name, account_type, normal_balance, description, parent_code.
- QuickBooks Online default chart (Intuit documentation)
- Xero default chart
- A nonprofit chart (Unified Chart of Accounts or a published university chart)
- A municipal or government chart (any published one)
- Optional: a subset of the US GAAP XBRL taxonomy for the income statement and balance sheet

Note which will be the platform target (recommend the GAAP-aligned or QuickBooks one) and which three are add-on sources. Do not create mappings.

## Task 3: Entity-resolution benchmarks
Download Abt-Buy, Amazon-Google, and DBLP-ACM from the Leipzig DBS benchmark page (or the deepmatcher Datasets.md links). Store in `er-benchmarks/` with their gold match files. Write `scripts/er_baseline.py` that runs a simple fuzzy-match baseline (rapidfuzz, threshold sweep) and reports precision, recall, F1 per dataset to `er-benchmarks/baseline_results.md`. This is the external validation track.

## Task 4: Evidence extracts
For each source below, fetch the page and write a one-page extract in `evidence/` with: URL, date fetched, direct quotes under 15 words each, and a bullet list of every failure mode, field, workflow gate, or timing claim it makes. Mark each as primary, practitioner, or vendor.
- Consero Global roll-up strategy resource (496-item checklist, 180 integrations, cash-to-accrual)
- SSA & Company dental roll-up integration playbook case
- PMI Stack ERP consolidation after merger
- Houseblend NetSuite M&A 100-day playbook PDF
- Estes Group ERP decisions behind PE acquisitions
- AlixPartners integration-ready platform
- PwC 2026 M&A Integration Survey (the 46% figure)
- McKinsey PE M&A integrations
- CohnReznick add-on acquisitions
If a page is unreachable, say so in the extract and move on.

## Task 5: Defect taxonomy template
Create `spec/defect_taxonomy.md` as a table with these columns, one row per defect type, populated only where evidence supports it:
| id | defect | domain (customer/vendor/coa) | example | expected outcome label | source citation | present naturally in real data? (from Task 1 profile) | must be injected? |

Expected outcome labels: AUTO_RESOLVE_MATCH, AUTO_RESOLVE_NON_MATCH, ESCALATE_AMBIGUOUS, ESCALATE_POLICY_DECISION, DO_NOT_MERGE_CONFLICTING_IDENTIFIER, MAP_DIRECT, MAP_MANY_TO_ONE, MAP_SPLIT_REQUIRED, MAP_REQUIRES_ACCOUNTING_POLICY, EXCLUDE_OR_RETIRED_ACCOUNT.

Leave the "must be injected" column and the final example wording as blanks marked `[FILL]` where the evidence doesn't settle it. Do not invent defects that no source describes.

## Task 6: Corpus spec template
Create `spec/corpus_spec.md` describing: the scenario (PE-backed multi-site services platform plus three add-ons), the schemas from Task 2 and Task 1 fields, the three answer-key layers (record pair, entity cluster, decision label), the dev/holdout split rule, and the metric definitions (precision, recall, F1, mapping accuracy, safe automation rate, correct escalation rate, unsafe automation rate, evidence completeness). Mark every synthetic design decision as `[FILL]`.

## Task 7: Manifest and README
- MANIFEST.json with SHA-256 for every file in sources/, coa/, entities/, er-benchmarks/.
- README.md: what is real, what is a template, what the next LLM pass is allowed to change (only `[FILL]` fields and new files under a `synthetic/` folder), and a bias statement: the person building the tool must not see `synthetic/holdout/` answer keys.

## Rules
- No synthetic records. No mappings. No answer keys.
- Every claim in evidence/ gets a URL and date.
- Quotes under 15 words.
- If a download needs credentials, stop and note it; do not work around it.
- Report at the end: what was fetched, what failed, file counts, and the naturally occurring defect rates from the profile.
