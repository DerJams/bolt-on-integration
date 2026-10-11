# coa/: real public charts of accounts

Every row in these CSVs comes from a published source file kept untouched under `sources/coa/<chart_name>/`. Nothing here is invented, and no mappings between charts exist in this folder.

Rebuild all five CSVs from `sources/` with:

```
uv run --with xlrd python -I -X utf8 scripts/build_coa.py
```

All CSVs share the same columns, in this order: `gl_code, account_name, account_type, normal_balance, description, parent_code`. A cell is empty when the source does not give the value. UTF-8, LF line endings, standard CSV quoting.

Fetch date for every source below: 2026-10-11.

## Summary

| File | Chart | Rows | Role |
|---|---|---|---|
| `us_gaap_platform_target.csv` | Operating-size chart derived from the GAAP subset below, plus named core operating expense accounts (section 5) | 280 | Platform target |
| `us_gaap_xbrl_2026_subset.csv` | FASB US GAAP Financial Reporting Taxonomy 2026, classified balance sheet + income statement | 951 | Reference: the base the platform target is derived from |
| `quickbooks_online_types.csv` | QuickBooks Online account types and detail types (Intuit API reference) | 289 | Add-on source 1 |
| `ucoa_nonprofit.csv` | Unified Chart of Accounts v3.0 (CAN / NCCS, Urban Institute) | 228 | Add-on source 2 |
| `erpnext_standard_numbered.csv` | ERPNext "Standard with Numbers" chart (frappe/erpnext, GPL-3.0) | 80 | Add-on source 3 |
| (none) | Xero default chart | 0 | Not fetched: needs a Xero login (see Failures) |

## Recommendation: target versus add-on sources

- **Platform target: `us_gaap_platform_target.csv`, derived from the US GAAP XBRL 2026 subset (section 5).** Reason: the GAAP taxonomy is the only GAAP-aligned source here with stable unique IDs, a full parent/child hierarchy and a source-given debit/credit balance on every monetary element. The full 951-row subset is a reporting taxonomy, finer than every add-on chart, so a 280-account operating chart is derived from it to make many-to-one mappings possible.
- **Add-on sources: QuickBooks Online types, UCOA nonprofit, ERPNext numbered standard chart.** These represent three acquired entities with different bookkeeping conventions (small-business software taxonomy, nonprofit fund accounting, open-source small-business ERP with numbered accounts).
- If the platform needs to be a QuickBooks shop instead, the QuickBooks file can serve as the target, but it holds account types and detail types only (no default account names or numbers), so it is a weaker target. No mappings have been created in either case.

## 1. US GAAP XBRL taxonomy 2026 subset

- **File:** `us_gaap_xbrl_2026_subset.csv` (951 rows)
- **Raw source:** `sources/coa/us_gaap_xbrl_2026/us-gaap-2026.zip` (7,387,980 bytes, taxonomy files dated 2025-11-25)
- **URL:** https://xbrl.fasb.org/us-gaap/2026/us-gaap-2026.zip
- **Terms:** the schema header says "Authorized Uses are Set Forth at https://xbrl.fasb.org/terms/TaxonomiesTermsConditions.html". Not reviewed in detail; check before redistribution outside this repo.
- **Subset rule:** two presentation networks only, `stm/us-gaap-stm-sfp-cls-pre-2026.xml` (Statement of Financial Position, Classified) and `stm/us-gaap-stm-soi-pre-2026.xml` (Statement of Income). Kept: monetary line items (`xbrli:monetaryItemType`) and the abstract headers that contain at least one of them. Dropped: tables, axes, domain members, and non-monetary items such as share counts and per-share amounts.
- **Columns:**
  - `gl_code`: element QName, e.g. `us-gaap:Cash` (source identifier).
  - `account_name`: standard label from `us-gaap-lab-2026.xml`.
  - `description`: documentation label from `us-gaap-doc-2026.xml` (empty for 169 rows, almost all abstract headers, where the taxonomy has no documentation).
  - `normal_balance`: the element's `xbrli:balance` attribute, as given by the source (not derived). Empty for 170 abstract headers, which carry no balance.
  - `parent_code`: nearest kept ancestor in the presentation tree.
  - `account_type`: **derived**. Balance sheet rows take `asset`, `liability`, `equity` or `temporary_equity` from the abstract they sit under (AssetsAbstract, LiabilitiesAbstract, the equity abstracts, TemporaryEquityAbstract). All income statement rows are labelled `income_statement` because the taxonomy does not split revenue from expense; use `normal_balance` for that. Four header/total rows (e.g. `us-gaap:StatementLineItems`, `us-gaap:LiabilitiesAndStockholdersEquity`) have no type.
- **Transcription notes:** an element can appear more than once in a presentation tree. The first occurrence (depth-first, by arc order) is kept and 295 repeats were dropped so `gl_code` stays unique. `us-gaap:StatementLineItems` is shared by both networks, so the income statement subtree hangs under the same root as the balance sheet subtree.

## 2. QuickBooks Online account types and detail types

- **File:** `quickbooks_online_types.csv` (289 rows: 15 account types + 274 detail types)
- **Raw source:** `sources/coa/quickbooks_online/intuit_api_account_types_subtypes.txt`, the rendered text of the AccountType / AccountSubType tables, copied verbatim with a provenance header. The page is a JavaScript single-page app; its static HTML holds no table data, so the rendered text is the saved copy.
- **URL:** https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account (Account entity, "Show child attributes" expanded)
- **Terms:** none shown on the page; Intuit developer documentation.
- **Why not a default chart:** Intuit does not publish a fixed, numbered QBO default chart. The help article "Account type and detail types in QuickBooks Online" (https://quickbooks.intuit.com/learn-support/en-us/help-article/chart-accounts/learn-account-detail-types-chart-accounts/L2gCy0rfy_US_en_US) explains types but does not list them. The public sample company (https://qbo.intuit.com/redir/testdrive) sits behind a reCAPTCHA, which was not attempted. The official API reference list of types and detail types was used instead. No account numbers were made up.
- **Columns:**
  - `gl_code`: built only from source identifiers. Account type rows use the AccountType value (e.g. `Other Current Asset`); detail type rows use `AccountType|AccountSubType` (e.g. `Bank|CashOnHand`). The pipe join is needed because some subtypes repeat across types (`Utilities`) or equal their type name (`Accounts Receivable`, `Accounts Payable`, `Credit Card`).
  - `account_name`: the AccountType or AccountSubType string as printed.
  - `account_type`: the source's classification heading (ASSET, EQUITY, EXPENSE, LIABILITY, REVENUE), lower-cased. Cost of Goods Sold sits under EXPENSE in the source.
  - `normal_balance`: **derived** by the standard rule from `account_type`. Contra detail types (e.g. `AllowanceForBadDebts`, `AccumulatedDepreciation`) are not adjusted because the source does not mark them.
  - `description`: notes whether the row is a type or detail type and whether the source marks it `(default)`.
  - `parent_code`: the AccountType for detail type rows; empty for type rows.
- **Transcription notes:** each type block in the source starts with a "Default" layout label, which was skipped. `Utilities` is listed twice under Expense; kept once. Spellings are as published (e.g. `AccruedLongLermLiabilities`, `EquityInEarningsOfSubsiduaries`, `LongTermDebit`).

## 3. Unified Chart of Accounts (UCOA) v3.0, nonprofit

- **File:** `ucoa_nonprofit.csv` (228 rows: 9 class headers, 39 group headers, 180 accounts)
- **Raw sources:** `sources/coa/ucoa_nonprofit/`
  - `UCOA-version 3.xls` (parsed; sheet "pages 1-6")
  - `UCOA version 3 .zip` (the full UCOA v3 toolkit: xls, keyword list, QuickBooks IIF/QBB)
  - `UCOA PUBLIC LICENSE v.1.1.pdf`
  - `nccs_projects_ucoa.cfm.html` (the NCCS project page that linked the files)
- **URLs:** the live NCCS pages (nccs.urban.org) return HTTP 403 to scripted requests, so the files were retrieved from the Internet Archive copies of the original NCCS links:
  - http://web.archive.org/web/20100114053415id_/http://nccsdataweb.urban.org/kbfiles/402/UCOA-version%203.xls
  - http://web.archive.org/web/20100114053448id_/http://nccsdataweb.urban.org/kbfiles/400/UCOA%20version%203%20.zip
  - http://web.archive.org/web/20110105095317id_/http://nccsdataweb.urban.org/kbfiles/405/UCOA%20PUBLIC%20LICENSE%20v.%201.1.pdf
  - http://web.archive.org/web/20070604183128id_/http://www.nccs.urban.org/projects/ucoa.cfm
- **License:** CAN/NCCS Public License v1.1, copyright 2002 California Association of Nonprofits and National Center for Charitable Statistics. Royalty-free use, copying and modification are allowed; redistribution requires no fee, the entire UCOA package as released, and the copyright notice. The full package zip and the license are kept in `sources/` for that reason.
- **Columns:**
  - `gl_code`: UCOA v3.0 account number. Revenue and expense numbers are printed as `NNNN-***` in the source; the `-***` activity-code suffix was removed from the code and noted in `description`.
  - `account_name`: as printed, with leading indentation and trailing colons removed.
  - `account_type`: from the source class (1 asset, 2 liability, 3 equity/net assets, 4 to 6 revenue, 7 to 9 expense). Class 9 is titled "Non-GAAP expenses" in the source and includes capital purchases marked "capitalized".
  - `normal_balance`: **derived** by the standard rule, except rows the source marks as contra ("(contra)" in the GAAP exhibit column or "contra 1a" in the Form 990 column), which are flipped and say so in `description`.
  - `description`: the source's cross-reference columns, labelled: UCOA v2.2 account, illustrative GAAP exhibit line, Form 990 line, Form 990-EZ line, OMB A-122 cost principle, United Way of America Accounting Guide, Tennessee Policy 03 template. Form 990 line numbers refer to the pre-2008 form.
  - `parent_code`: group header (e.g. 1000) or class header (e.g. 1).
- **Transcription notes:** "Total ..." rows and the page 7 activity-code table (program/M&G/fundraising suffixes) are not accounts and were excluded. A blank row in the source ends a group, so indented rows that follow a blank row (2410, 2610, 2810, 2910, 9910 to 9930) and non-indented detail codes (1810, 1850, 1910, 1950) are attached to their class header rather than guessed into a group. The standalone xls (438,784 bytes) is a different byte copy from the one inside the zip (422,400 bytes); the standalone file was parsed.

## 4. ERPNext standard chart with account numbers (small business)

- **File:** `erpnext_standard_numbered.csv` (80 rows: 27 asset, 14 liability, 5 equity, 5 revenue, 29 expense)
- **Raw sources:** `sources/coa/erpnext_standard_numbered/`
  - `standard_chart_of_accounts_with_account_number.py`: ERPNext's "Standard with Numbers" chart template, the numbered variant of the default chart offered when a company is created.
  - `license.txt`: the repository's GNU GPL v3 license.
- **URLs** (pinned to commit `bfd8100d42162048248b7b947f2e21fdf7999a91`, the head of branch `version-15` on 2026-10-11):
  - https://raw.githubusercontent.com/frappe/erpnext/bfd8100d42162048248b7b947f2e21fdf7999a91/erpnext/accounts/doctype/account/chart_of_accounts/verified/standard_chart_of_accounts_with_account_number.py
  - https://raw.githubusercontent.com/frappe/erpnext/bfd8100d42162048248b7b947f2e21fdf7999a91/license.txt
- **License:** GNU GPL v3 (file header: "Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors"). The license file is kept alongside the source.
- **Why ERPNext over the alternatives:** Odoo's US companies use its generic chart (`addons/account/data/template/account.account-generic_coa.csv`, 44 flat accounts with no hierarchy or descriptions). ERPNext's numbered chart has a full group hierarchy and its own account types, so `parent_code` comes from the source. The GnuCash template was not evaluated.
- **Parsing:** the source is a Python module. `scripts/build_coa.py` reads it with `ast` and `ast.literal_eval`, unwrapping the `_("...")` translation calls. The module is never imported or executed.
- **Columns:**
  - `gl_code`: the source `account_number`. Two group accounts carry a range as their number (`1100-1600` Current Assets, `2100-2400` Current Liabilities), kept as published.
  - `account_name`: the dictionary key as published (e.g. `Debtors`, `Creditors`, `Softwares`).
  - `account_type`: **derived** from the source `root_type` of the top-level group (Asset, Liability, Equity, Income as `revenue`, Expense).
  - `normal_balance`: **derived** by the standard rule, flipped for the one row whose ERPNext account type is `Accumulated Depreciation` (noted in `description`).
  - `description`: `group account` or `ledger account`, plus the ERPNext `account_type` where the source gives one (e.g. `Receivable`, `Bank`, `Fixed Asset`).
  - `parent_code`: the `account_number` of the enclosing group.
- **Transcription notes:** source order is kept (depth-first). Some names reflect the project's Indian origin (`TDS Payable`, `Duties and Taxes`); kept as published. `Employee Advances` carries ERPNext account type `Payable` under assets in the source; kept as published.
- **Replaces:** Washington State BARS (City/Town), removed on 2026-10-11 at the repo owner's request in favour of a small-business chart.

## 5. Platform target derived from the GAAP subset

- **File:** `us_gaap_platform_target.csv` (280 rows: 34 group accounts, 246 ledger accounts; 74 asset, 65 liability, 37 equity, 7 temporary equity, 95 income statement, 2 untyped headers)
- **Why:** the 951-row subset is a reporting taxonomy, not an operating chart. It is finer than every add-on chart, which leaves no room for many-to-one mappings. This file is an operating-size chart derived from it by a fixed size rule, plus a short named list of core operating expense accounts. No element is renamed and no account is invented; every row is a real us-gaap element.
- **Built by:** `build_gaap_platform()` in `scripts/build_coa.py`. Inputs: `us_gaap_xbrl_2026_subset.csv`, the `totalLabel` arcs in the two statement networks (`stm/us-gaap-stm-sfp-cls-pre-2026.xml`, `stm/us-gaap-stm-soi-pre-2026.xml`), and, for named elements, the label, documentation and balance from `elts/` plus every presentation network in the taxonomy zip.
- **Size rule:**
  1. Start from the 951-row subset (section 1) without its shared root `us-gaap:StatementLineItems`. Each `[Abstract]` element is a group.
  2. A group's **total** is the child that the presentation linkbase presents with `preferredLabel="http://www.xbrl.org/2003/role/totalLabel"`. Of 169 groups, 160 have one.
  3. A group's **size** is the number of elements in its subtree within the subset (the group plus all descendants).
  4. Walk the groups top-down, in presentation order. **Expand** a group if any of these holds:
     - its size is at least **35** (`PLATFORM_MIN_GROUP_SIZE`)
     - it has no total
     - it is a target group of the named expansion below

     An expanded group is written as a group account. Its total is dropped, because the group account stands for that sum. Its child groups are visited by the same rule, and its other children are written as ledger accounts. Those ledger accounts' own descendants, if any, are dropped.
  5. Otherwise **collapse** the group: its total element is written as one ledger account, in the group's place, under the nearest expanded group.
  6. Every column value is copied from the subset row except `parent_code`, which points to the nearest kept group, and `description`, which is prefixed with `group account`, `ledger account`, or `ledger account; stands for collapsed group <QName>`.
- **Named expansion** (`PLATFORM_NAMED_EXPANSION`):
  7. For each entry, look up the element by name in the full taxonomy (`elts/us-gaap-2026.xsd` and the label and documentation linkbases), wherever it is presented.
  8. If the size rule already placed the element, leave it where it is. Otherwise add it as a ledger account under the entry's target group. It goes after the group's existing subtree, with `account_type` `income_statement` and `description` prefixed `ledger account; named expansion; presented in <networks>`.

| requested | element used | placed under | result | presentation networks that carry it (`dis/` disclosure, `stm/` statement; `us-gaap-` prefix and `-pre-2026.xml` suffix dropped) |
|---|---|---|---|---|
| `SalariesAndWages` (or `LaborAndRelatedExpense`) | `SalariesAndWages` | SG&A group | added | `dis/dis-crcgen` |
| `EmployeeBenefitsAndShareBasedCompensation` | same | SG&A group | added | `dis/dis-crcgen` |
| `ProfessionalFees` | same | SG&A group | added | `dis/dis-invco`, `dis/dis-otherexp`, `stm/stm-soi-int`, `stm/stm-soi-sbi` |
| `CostOfServices` | `CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization` (`CostOfServices` does not exist in the 2026 taxonomy; this is the closest real element) | unchanged: cost-of-revenue group, under `us-gaap:CostOfGoodsAndServicesSoldAbstract` | already in size-rule output | `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm` |
| `DepreciationDepletionAndAmortization` | `DepreciationAndAmortization` (the requested element exists but is presented only in cash-flow and disclosure networks; this is its income-statement counterpart, labelled "Depreciation, Depletion and Amortization, Nonproduction") | unchanged: `us-gaap:OperatingCostsAndExpensesAbstract` | already in size-rule output | `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-ins`, `stm/stm-soi-int`, `stm/stm-soi-re`, `stm/stm-soi-reit`, `stm/stm-soi-sbi` |
| `OperatingLeaseExpense` (or occupancy) | `OperatingLeaseExpense` | SG&A group | added | `dis/dis-leas`, `dis/dis-otherexp`, `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-ins`, `stm/stm-soi-re`, `stm/stm-soi-reit` |
| `AdvertisingExpense` | same | SG&A group | added | `dis/dis-otherexp`, `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-ins`, `stm/stm-soi-int`, `stm/stm-soi-re`, `stm/stm-soi-reit`, `stm/stm-soi-sbi` |
| `GeneralInsuranceExpense` | same | SG&A group | added | `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-ins`, `stm/stm-soi-re`, `stm/stm-soi-reit`, `stm/stm-soi-sbi` |
| `ProvisionForDoubtfulAccounts` | same (current label "Accounts Receivable, Credit Loss Expense (Reversal)") | unchanged: `us-gaap:OperatingExpensesAbstract` | already in size-rule output | `dis/dis-cecl`, `dis/dis-dise`, `dis/dis-rlnro`, `dis/dis-sr`, `stm/stm-scf-indir`, `stm/stm-scf-inv`, `stm/stm-scf-re`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-ins`, `stm/stm-soi-re`, `stm/stm-soi-reit` |
| `TravelAndEntertainmentExpense` | same | SG&A group | added | `dis/dis-otherexp`, `dis/dis-sr`, `stm/stm-soi`, `stm/stm-soi-egm`, `stm/stm-soi-re`, `stm/stm-soi-reit`, `stm/stm-soi-sbi` |

SG&A group = `us-gaap:SellingGeneralAndAdministrativeExpenseAbstract`. Four of the added elements (`OperatingLeaseExpense`, `AdvertisingExpense`, `GeneralInsuranceExpense`, `TravelAndEntertainmentExpense`) are already in the 951-row subset, inside the SG&A group's collapsed sub-groups. They were missing only because the size rule collapsed them. The other three come from outside the two statement networks.

- **Threshold choice:** before the named expansion, sizes 30, 35, 40 and 50 give 318, 270, 242 and 201 rows. 35 was chosen to land inside the requested 200 to 300 range. The named expansion adds 10 rows: SG&A becomes a group with three collapsed-total ledgers plus seven named ledgers, replacing one ledger. Change `PLATFORM_MIN_GROUP_SIZE` or the list and rerun to regenerate.
- **Effect:**
  - 73 ledger accounts are collapsed groups. Examples: receivables fold into `us-gaap:ReceivablesNetCurrent`, and payables and accruals into `us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent`.
  - Inside SG&A, the collapsed totals `us-gaap:SellingAndMarketingExpense` and `us-gaap:GeneralAndAdministrativeExpense` sit beside the named accounts. In this operating chart they act as residual "other selling and marketing" and "other G&A" accounts. In the taxonomy those totals include advertising, insurance, travel and lease expense; here, amounts posted to the named accounts are not also posted to the totals.
- **Known limits:** the size rule is structural. It keeps some industry-specific leaves that sit directly under large groups (for example crypto assets, regulatory assets, lease investment lines). These are real taxonomy elements and are left as unused targets.

## Failures

- **Xero default chart: not fetched (needs credentials).** Xero Central's "Import a chart of accounts" article says the template file is downloaded from inside a Xero organisation or the demo company (both need a login). The Xero Partner Hub chart templates also need a login. Xero Central search redirects to login.xero.com. The legacy public template links (`https://go.xero.com/GeneralLedger/ChartOfAccountsDownloader.aspx?Download=ExampleAUGST` and similar, found in an archived 2015 Xero help page) now return HTTP 500 and have no Internet Archive copy. The Xero developer docs list only the system accounts (Accounts Receivable, Accounts Payable, GST/VAT, Retained Earnings, etc.), not the full default chart, so no Xero rows were written. Stopped there as instructed.
- **QuickBooks Online sample company (test drive):** blocked by reCAPTCHA; not attempted. The Intuit API type/detail-type list was used instead (see section 2).
- **NCCS live pages:** HTTP 403 for scripted requests; Internet Archive copies of the original NCCS file links were used (see section 3).
