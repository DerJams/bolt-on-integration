# Houseblend: M&A Integration, a 100-Day NetSuite Financial Systems Plan

- URL fetched: https://www.houseblend.io/articles/en/centjoursintegrationfusionsacquisitionsplannetsuite (HTML article, published 2025-11-05)
- PDF: the page shows a "Download PDF" button, but no direct PDF URL was exposed and none was found by search, so the HTML version was used.
- Date fetched: 2026-10-11 (the first 100,000 of about 110,000 characters were read)
- Source class: vendor (NetSuite consultancy). The article compiles secondary statistics; it holds no original data.
- Reachable: yes (raw HTML saved to sources/evidence_pages/houseblend_netsuite_100day.html)
- Related Houseblend articles found but not fetched: "NetSuite M&A Integration: 100-Day Consolidation Playbook" (2026-04-21) and "NetSuite M&A Integration: 100-Day Playbook & COA Setup" (2026-06-06).

## Direct quotes (max 3)
1. "the first 100 days is crucial to jump-starting a successful merger" (quoted from FM Magazine)
2. "it's basically a false start" (FM Magazine, quoting Global PMI Partners)
3. "Few closely held companies have the systems in place to make deals happen smoothly" (quoted from NetSuite)

## Summary
A long-form guide that splits the first 100 days into pre-close, Day 1 and four later windows, each with finance-system tasks in NetSuite OneWorld. It is strong on CoA harmonization, subsidiaries, intercompany and cutover validation. It says nothing on TSAs or cash-to-accrual. The article itself notes that research gives only weak support to first-100-day activity predicting long-term success.

## Extracted claims
- [timing] Pre-close: form an IMO, draft a unified CoA, map data fields and GL accounts, and do a dry run of the consolidated close about 30 days before Day 1.
- [timing] Day 1: keep payroll and payables running, map or merge target bank accounts, enable OneWorld subsidiaries and intercompany settings, and communicate to stakeholders.
- [timing] Days 2 to 30: harmonize the CoA, load baseline data, configure the subsidiary structure, publish test consolidated financials.
- [timing] Days 31 to 60: retire redundant systems, standardize policies, configure eliminations and currency translation, run a full test consolidated close.
- [timing] Days 61 to 90: automate recurring consolidations, build dashboards, review variance against synergy targets.
- [timing] Days 91 to 100: archive legacy systems, lock down roles and security, record lessons learned.
- [failure-mode] Differing charts of accounts are among the most common consolidation problems; like transactions must be mapped so they land together.
- [failure-mode] Mismatched CoAs may force placeholder or dummy accounts to reconcile.
- [gate] A single shared CoA, with legacy codes migrated in a one-time cleanup, ideally by the first close.
- [failure-mode] Field definitions differ across ERPs (for example "revenue" vs "sales"), forcing manual entries or reconciliations.
- [field] Customer and vendor data exported and loaded early (days 2 to 30); customer master and vendor terms confirmed by Day 100.
- [failure-mode] Duplicate customers and vendors should be cleaned before cutover; consultants say pre-cutover cleanup pays off.
- [gate] Master data (customers, items, open AR and AP balances) must be loaded before go-live.
- [field] Each legal entity is a subsidiary in one hierarchy; subledgers close locally and roll up.
- [field] One consolidation currency at the top; P&L translated at average rates and balance sheet at closing rates.
- [field] Multi-book for parallel GAAP (for example IFRS and US GAAP).
- [failure-mode] Partial ownership, equity-method or minority interests may need tools outside the ERP or spreadsheets.
- [gate] Define the intercompany framework (elimination accounts, automatic matching of intercompany AR/AP) before heavy use.
- [field] Set up consolidation currency gain/loss accounts so translation effects do not hit income unexpectedly.
- [field] Revenue recognition policy alignment (shipment vs invoicing) is part of harmonization.
- [gate] Extract, clean and transform data weeks before cutover; validate that trial balances match within agreed tolerances.
- [field] Load channels: CSV import and API for open AR/AP invoices, open POs and master data; middleware (Boomi, Celigo, MuleSoft) for ongoing legacy feeds.
- [failure-mode] Case cited: the client's limited bandwidth to supply data delayed a QuickBooks-to-NetSuite cutover.
- [failure-mode] Manual spreadsheet consolidation, delayed reporting and mistrust of data.
- [failure-mode] Unplanned payroll or billing disruption, key staff loss, culture clash.
- [failure-mode] Underestimating data cleanup and over-relying on spreadsheets.
- [failure-mode] Delaying the plan or skipping early action produces a "false start".
- [metric] Secondary: 70 to 90% of deals underperform (attributed to DealStream/IMAA); about 70% of mergers miss expectations (McKinsey via IMAA).
- [metric] Secondary: about 37% of CFOs "very involved" in integration (McKinsey); nearly 40% of CFOs do not fully trust their financial data (CTM File).
- [metric] Secondary: one CFO spent 3 to 4 hours monthly on manual consolidation (Greenstep); reconciliation time cut by more than 50% with integration tools (Data Calculus).
- [metric] Cites the Angwin study: little overall support that first-100-day activity predicts long-term success (significant only for older deals).
- [field] No explicit cash-to-accrual or TSA content (absence noted).
