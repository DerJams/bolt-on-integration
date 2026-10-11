# rollup-bench

A benchmark scaffold for private-equity roll-up data integration: matching customer and vendor masters, and mapping charts of accounts, across a platform company and three add-ons.

This repo holds the **real layer** only: public data, cited evidence, schemas, and spec templates. A later pass adds a **synthetic layer** (partition, injected defects, answer keys) under `synthetic/`. The brief that produced this repo is `docs/claude-code-brief.md`. Rules set for the later pass are in `docs/fill_run_rules.md`.

## What is real

| folder | contents | provenance |
|---|---|---|
| `sources/` | raw downloads, untouched | `MANIFEST.json` (URL, date, SHA-256 per file) |
| `entities/` | 8,800 real recipient record variants (4,035 UEIs) from USAspending federal contract awards, plus `profile.md` with naturally occurring messiness | `scripts/fetch_usaspending.py`, `scripts/build_entities.py`, `scripts/profile_entities.py` |
| `coa/` | four real public charts of accounts as CSV (US GAAP XBRL subset, QuickBooks Online types, UCOA nonprofit, ERPNext numbered small-business chart), plus a 280-account platform target derived from the GAAP subset by a documented rule | `coa/README.md`, `scripts/build_coa.py` |
| `er-benchmarks/` | Abt-Buy, Amazon-Google, DBLP-ACM with gold mappings, plus a rapidfuzz baseline | `er-benchmarks/README.md`, `scripts/er_baseline.py` |
| `evidence/` | one-page extracts of 9 practitioner, vendor and survey sources, each with URL and fetch date | `evidence/INDEX.md` |
| `schemas/` | field specs for the master records and charts, tied to evidence | |

### Entity scope

Recipients located in California on federal contracts (award types A to D) with action dates in FY2008 to FY2026, in three service NAICS groups: building equipment contractors (2382: HVAC, plumbing, electrical), offices of physicians, dentists and other health practitioners (6211, 6212, 6213), and employment services (5613: staffing). Each row is one distinct combination of identifiers, names, parent, address and business-type flags as reported on awards, so the same UEI can appear on several rows. That variation is real and is kept on purpose. Phone and fax numbers and officer names are not copied out of the source file.

The pool includes some public bodies (counties, the University of California) and some sole proprietors whose recipient name is a personal name, exactly as USAspending publishes them.

## What is a template

- `spec/defect_taxonomy.md`: defect rows backed by evidence. The "must be injected?" column and some example wording are `[FILL]`.
- `spec/corpus_spec.md`: scenario, schemas, answer-key layers, split rule, metric definitions. Every synthetic design decision is `[FILL]`.

## What the next pass may change

Only:
1. `[FILL]` markers in `spec/defect_taxonomy.md` and `spec/corpus_spec.md`. The "must be injected?" column is filled by the repo owner, not by the pass (`docs/fill_run_rules.md`, rule 7).
2. New files under `synthetic/`.

Nothing under `sources/`, `coa/`, `entities/`, `er-benchmarks/`, `evidence/`, `schemas/` or `scripts/` may be edited. No new companies, addresses or account names may be invented; only real records may be transformed.

## Before making this repo public

Delete `sources/` (and rewrite git history so it is gone from past commits too) before the repo is made public. It holds third-party material whose terms do not allow republishing here: saved copies of the evidence web pages, the FASB taxonomy zip (terms not reviewed), the UCOA package (redistribution only as the complete package with its notice), and the Leipzig benchmark zips. `MANIFEST.json` keeps each file's source URL and SHA-256, so the files can be re-fetched and verified.

## Bias statement

The person building or tuning the tool under test must not see the `synthetic/holdout/` answer keys, and reports may describe the holdout only by counts. If the same person runs the synthetic pass and builds the tool, results on the holdout are not independent.

## Known gaps and failures

- **SAM.gov entity data: skipped.** The Entity Management API and extract downloads require an API key tied to a SAM.gov account (https://open.gsa.gov/api/entity-api/). Legal versus DBA name variants are still present in the USAspending records (`recipient_name_raw`, `recipient_name`, `recipient_doing_business_as_name`).
- **Xero default chart: not fetched.** It needs a Xero login. See `coa/README.md`.
- **QuickBooks Online:** Intuit publishes no numbered default chart. The CSV holds Intuit's official account types and detail types instead, with Intuit's own identifiers as codes.
- **UCOA:** the live NCCS pages return HTTP 403 to scripts. The original files were taken from Internet Archive copies of the NCCS links.
- **Evidence:** PwC (HTTP 403) and McKinsey (timeouts) could not be read. Their extracts hold search-snippet claims only, marked unverified. The Houseblend PDF link was not exposed, so the HTML article was used.
- **Entity count:** contract data alone gives 4,035 UEIs at the 4-digit NAICS group level. The narrower 6-digit codes (for example 621210 dental offices alone) give far fewer.

## Reproduce

```bash
python -I scripts/fetch_usaspending.py
python -I scripts/build_entities.py
uv run --with rapidfuzz --with numpy python -I scripts/profile_entities.py
uv run --with xlrd python -I -X utf8 scripts/build_coa.py
uv run --with rapidfuzz --with pandas python -I scripts/er_baseline.py
python -I scripts/build_manifest.py
```

A fresh USAspending download can differ slightly from the one in `sources/` as agencies revise records. The checked-in zip is the frozen copy.
