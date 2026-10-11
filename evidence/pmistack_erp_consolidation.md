# PMI Stack: ERP Consolidation After Merger, the Roll-Up Operator's Field Guide

- URL fetched: https://pmistack.com/blog/erp-consolidation-after-merger
- Date fetched: 2026-10-11 (the page has no publication date; its footer shows 2026)
- Author: Dylan Harrocks, founder of PMI Stack
- Source class: vendor (small London firm selling technical post-merger integration services to roll-ups)
- Reachable: yes (raw HTML saved to sources/evidence_pages/pmistack_erp_consolidation_after_merger.html)

## Direct quotes (max 3)
1. "you can't migrate mess. Clean first, migrate second."
2. "ERP should be _last_ in your migration sequence"
3. "Parallel running is non-negotiable for ERP."

## Summary
A practical guide offering three integration depths (full, hybrid "financial spine", reporting-only) plus a keep-separate option. It lays out a four-phase, 26-week timeline and puts heavy weight on master data cleanup (golden records, deduplication) before migration. Its statistics are secondary citations to KPMG, Bain and Gartner, not original data.

## Extracted claims
- [gate] Option 1, full consolidation: one ERP, one chart of accounts, unified processes.
- [timing] Full consolidation takes about 3 to 6 months.
- [gate] Option 2, hybrid: unify the financial spine (CoA, GL, consolidation) and leave operational modules flexible.
- [timing] Hybrid takes about 2 to 3 months.
- [gate] Option 3, reporting-only: leave the target ERP in place and sync data for reporting.
- [timing] Reporting-only takes about 2 to 4 weeks.
- [gate] Keep separate for small tuck-ins (under about 10 people), different verticals or geographies, or test-and-learn deals.
- [timing] Phase 1, weeks 1 to 4: Day 1 readiness and a "minimum viable integration", ideally begun during diligence.
- [timing] Phase 2, weeks 5 to 16: data migration and cutover.
- [timing] Phase 3, weeks 17 to 20: hypercare covering the first 30 days after go-live.
- [timing] Phase 4, weeks 21 to 26 and then ongoing: optimisation, legacy decommissioning, tech-debt cleanup.
- [gate] Minimum viable integration on Day 1: on-time payroll, uninterrupted invoicing, statutory compliance, and consolidated reporting (manual is allowed in month one).
- [field] Map the legacy CoA to the platform CoA, decide on new GL codes, and agree how historical financials are restated.
- [failure-mode] Legacy CoA bloat, for example 1,200 GL codes, most of them unused.
- [field] Build golden records for customers, suppliers, products and employees.
- [failure-mode] Duplicate customer records across several databases (example: the same customers held in three databases).
- [field] Standardise names, addresses and tax identifiers (VAT numbers), and validate payment terms and credit limits.
- [gate] Assign master data ownership and set an update process going forward.
- [metric] Budget 30 to 40% of migration effort for data preparation. Example: 5 weeks of cleansing, then 2 weeks of migration.
- [gate] Expect manual dedupe work even with automated deduplication.
- [gate] Go live at the start of a financial period and keep a rollback plan.
- [gate] Run in parallel for at least one full accounting cycle, preferably two, and compare month-end outputs line by line.
- [gate] Complete UAT before go-live and hold daily stand-ups for the first two weeks.
- [timing] Sunset policy: consider forcing migration when a legacy system is still running 12+ months after acquisition.
- [metric] Timelines running at double the benchmark usually point to resourcing, governance or data quality.
- [failure-mode] Underestimating data quality and master data governance.
- [failure-mode] Migrating systems faster than people change behaviour, so users revert, keep shadow spreadsheets and reconcile by hand.
- [field] Interim single source of truth: a data warehouse or consolidation layer (Power BI, Domo, structured Excel).
- [field] ERP selection criteria: multi-entity consolidation, role-based permissions, APIs, cloud-native design.
- [field] Named target ERPs: Sage Intacct, NetSuite, Dynamics Business Central, Acumatica. Xero for small entities, QuickBooks Online as transitional, on-prem systems such as Sage 50 as sunset candidates.
- [metric] Secondary citations, not checked against the originals: 83% of M&A deals fail to boost shareholder returns (attributed to KPMG), 83% of data migrations fail or overrun (attributed to Gartner), 84% of IT integrations hit significant issues (attributed to Gartner).
- [field] TSA not mentioned (absence noted).
