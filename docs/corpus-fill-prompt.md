# Fill-in pass (run as a seeded Python script)

Prerequisites: the brief has been run, the repo exists, and the "must be injected" column in `spec/defect_taxonomy.md` has been set from `docs/injection_decisions.md`.

You are generating the synthetic layer of a benchmark for private-equity bolt-on data integration. A repository has already been assembled with real public data and evidence. Your job is to fill in only what is marked `[FILL]` and to create the files under `synthetic/`. You must not modify anything under `sources/`, `coa/`, `entities/`, `er-benchmarks/`, or `evidence/`, except to add the UEI counts to `entities/profile.md`. Do all generation in one seeded Python script, `scripts/generate_synthetic.py`, so the run repeats exactly.

### Read first
1. `README.md`
2. `spec/corpus_spec.md`
3. `spec/defect_taxonomy.md`
4. `docs/injection_decisions.md`
5. `docs/fill_run_rules.md`
6. `entities/profile.md`
7. The `evidence/` extracts

### Scenario
A PE-backed multi-site services platform (PlatformCo) has acquired three smaller businesses (AddOn A, B, C). Each add-on has its own chart of accounts and its own customer and vendor masters. The integration goal is common financial reporting and master-data governance. Use only the real entity records in `entities/` and the real charts in `coa/`. Do not invent company identities.

### Task 1: Assign real records to entities
- Partition the real entity records into PlatformCo, AddOn A, AddOn B, AddOn C with a constrained random draw: generate a seed, record it in `synthetic/SEED.txt`, draw a partition, and re-draw until at least 15 natural duplicate or parent-child pairs (from `entities/profile.md`) are split across entities and at least 15 are kept within one entity. Record the number of attempts. Do not choose the partition by hand.
- Assign charts per `spec/corpus_spec.md`.

### Task 2: Inject defects
- Inject only CV07 and COA05, per `docs/injection_decisions.md`.
- CV07: blank the primary UEI on a random subset of records, 2 to 8 percent per domain per entity, counted after partition. Tag each corrupted record with the defect id in a hidden column.
- COA05: apply to AddOn A only. Remove accounts receivable, accounts payable, accrued liabilities, prepaid expenses, deferred revenue, and accumulated depreciation from its chart; tag the chart cash_basis=true; label every mapping that would have targeted a removed account MAP_REQUIRES_ACCOUNTING_POLICY with rationale "source is cash-basis; accrual conversion required". Record removed accounts in `synthetic/injection_log.json`.
- Do not add defect types not in the taxonomy. If one seems missing, write it to `synthetic/PROPOSED_DEFECTS.md` and do not apply it.
- Record exact injection rates in `synthetic/injection_log.json`.

### Task 3: Fill the `[FILL]` fields
- In `spec/defect_taxonomy.md`, complete example wording only. Do not touch the "must be injected" column.
- In `spec/corpus_spec.md`, complete every `[FILL]` with a concrete decision and a one-line rationale. Cite an `evidence/` extract where one applies; for the seed, injection rates, and split ratio, cite "prompt-specified."
- Do not change text not marked `[FILL]`.

### Task 4: Build the answer key
Produce three layers, for customers, vendors, and chart of accounts:
1. `record_pairs.csv`: pairs of record ids with match truth "match", "non-match", or "unknown". Same-name-different-UEI pairs are "unknown".
2. `entity_clusters.csv`: cluster id per record and the chosen golden record with survivorship rule applied.
3. `decisions.csv`: one outcome label from the taxonomy per record or mapping, plus a short rationale. Same-name-different-UEI pairs get DO_NOT_MERGE_CONFLICTING_IDENTIFIER.
For chart-of-accounts mappings, produce `coa_mappings.csv` with source code, target code, mapping type, rationale, and whether a business decision is required. Where evidence does not settle a mapping, label it MAP_REQUIRES_ACCOUNTING_POLICY rather than guessing.

### Task 5: Split and freeze
- Split 60/40 into `synthetic/dev/` and `synthetic/holdout/` by entity cluster, not by record, so no pair crosses folders. Use the seed. Answer keys go in the matching folder.
- Compute SHA-256 in code for every file created and write `synthetic/MANIFEST.json` with the hashes, the seed, the attempt count from Task 1, and the system date obtained in code.
- Write `synthetic/GENERATION_REPORT.md`: counts per entity and domain, injection rates, natural versus injected defect counts, number of escalations, number of "unknown" pairs, and any taxonomy rows you could not apply and why.
- Write `scripts/score.py` that reads a predictions file and the answer key and reports: pairwise precision, recall, F1 (excluding "unknown" pairs, reporting their count), mapping accuracy, safe automation rate, correct escalation rate, unsafe automation rate, evidence completeness.

### Rules
- Transform real records only. Never invent companies, addresses, or account names.
- Every synthetic design choice cites an `evidence/` file or "prompt-specified."
- Do not describe holdout answer keys beyond counts.
- If anything is contradictory or impossible, stop, write `synthetic/BLOCKERS.md`, and do not improvise.
