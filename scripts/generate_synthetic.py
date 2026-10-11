"""Generate the synthetic layer under synthetic/ (docs/corpus-fill-prompt.md, docs/fill_run_rules.md).

Seeded and repeatable: the seed is drawn once and stored in synthetic/SEED.txt; later runs read it
back, so the same inputs give byte-identical outputs. Real records and real chart rows only; nothing
here invents a company, address or account name.

Run: uv run --with rapidfuzz --with numpy python -I scripts/generate_synthetic.py
"""
import collections, csv, datetime, hashlib, io, itertools, json, math, pathlib, random, secrets, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from profile_entities import NEAR_DUP_THRESHOLD, norm_addr, norm_name  # noqa: E402  same rules as the profile
from rapidfuzz import fuzz, process  # noqa: E402

OUT = ROOT / "synthetic"
RECORDS = ROOT / "entities" / "recipient_records.csv"

ENTITIES = ["PlatformCo", "AddOnA", "AddOnB", "AddOnC"]
ENTITY_WEIGHTS = [0.4, 0.2, 0.2, 0.2]
ID_PREFIX = {"PlatformCo": "PLT", "AddOnA": "AOA", "AddOnB": "AOB", "AddOnC": "AOC"}
DOMAINS = ["customer", "vendor"]
MIN_SPLIT_PAIRS = MIN_KEPT_PAIRS = 15
MAX_ATTEMPTS = 1000
CV07_RATE, CV07_MIN, CV07_MAX = 0.05, 0.02, 0.08
DEV_SHARE, SPLIT_TOLERANCE, COA_SPLIT_TOLERANCE = 0.60, 0.02, 0.05
HIDDEN = ["source_record_id", "true_recipient_uei", "defect_ids"]
IDENTIFIER_COLUMNS = ["recipient_uei", "recipient_duns", "cage_code", "recipient_parent_uei", "recipient_parent_duns"]
# Track A (shared-identifier): UEI visible, CV07 blanks it on 5% of records; tests escalation when an identifier exists.
# Track B (no-shared-identifier): every identifier column removed from the inputs; the realistic configuration and the
# headline. CV07 does not apply. Same seed, partition, split, clusters and negatives as track A.
TRACKS = {
    "track_a": {"name": "shared-identifier", "drop": [], "cv07": True, "stream": lambda s: s,
                "id_range": range(100000, 1000000)},
    "track_b": {"name": "no-shared-identifier", "drop": IDENTIFIER_COLUMNS, "cv07": False,
                "stream": lambda s: f"{s}:track_b", "id_range": range(1000000, 10000000)},
}

CHARTS = {  # spec/corpus_spec.md section 2.2
    "PlatformCo": "us_gaap_platform_target.csv",
    "AddOnA": "quickbooks_online_types.csv",
    "AddOnB": "ucoa_nonprofit.csv",
    "AddOnC": "erpnext_standard_numbered.csv",
}

ESCALATE_LABELS = {"ESCALATE_AMBIGUOUS", "ESCALATE_POLICY_DECISION", "DO_NOT_MERGE_CONFLICTING_IDENTIFIER",
                   "MAP_REQUIRES_ACCOUNTING_POLICY"}

# ---------------------------------------------------------------------------------------------
# Chart-of-accounts answer key.
# A mapping is "settled" when the source account's own name, type or source cross-reference and the
# target element denote the same concept, or the source is a component of a target that
# coa/README.md section 5 documents as a collapsed total. Anything else is MAP_REQUIRES_ACCOUNTING_POLICY
# with the reason given (spec/corpus_spec.md section 3). Mapping type is computed, not chosen:
# one target and no other source of the same chart on it -> MAP_DIRECT; several sources of one chart on
# one target -> MAP_MANY_TO_ONE; one source on several targets -> MAP_SPLIT_REQUIRED.
# ---------------------------------------------------------------------------------------------
T = {
    "CASH": "CashCashEquivalentsAndShortTermInvestments", "REC": "ReceivablesNetCurrent",
    "INV": "InventoryNet", "PRE": "PrepaidExpenseCurrent", "OCA": "OtherAssetsCurrent",
    "DEPC": "DepositsAssetsCurrent", "HFS": "AssetsHeldForSaleNotPartOfDisposalGroupCurrent",
    "PPE": "PropertyPlantAndEquipmentNet", "INTANG": "IntangibleAssetsNetExcludingGoodwill", "GW": "Goodwill",
    "LTI": "LongTermInvestmentsAndReceivablesNet", "ONCA": "OtherAssetsNoncurrent", "DTA": "DeferredIncomeTaxAssetsNet",
    "DEPNC": "DepositsAssetsNoncurrent", "AFSNC": "DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent",
    "TRUST": "AssetsHeldInTrustNoncurrent",
    "APA": "AccountsPayableAndAccruedLiabilitiesCurrent", "APANC": "AccountsPayableAndAccruedLiabilitiesNoncurrent",
    "DR": "DeferredRevenueCurrent", "DRNC": "DeferredRevenueNoncurrent", "STB": "ShortTermBorrowings",
    "LTDC": "LongTermDebtAndCapitalLeaseObligationsCurrent", "LTD": "LongTermDebtAndCapitalLeaseObligations",
    "OCL": "OtherLiabilitiesCurrent", "OLNC": "OtherLiabilitiesNoncurrent", "DTL": "DeferredIncomeTaxLiabilitiesNet",
    "CS": "CommonStockValue", "PS": "PreferredStockValue", "APIC": "AdditionalPaidInCapital",
    "TS": "TreasuryStockValue", "AOCI": "AccumulatedOtherComprehensiveIncomeLossNetOfTax",
    "RE": "RetainedEarningsAccumulatedDeficit",
    "PART": "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest",
    "REV": "Revenues", "COGS": "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    "COSTDA": "CostDepreciationAmortizationAndDepletion", "DA": "DepreciationAndAmortization",
    "SAL": "SalariesAndWages", "BEN": "EmployeeBenefitsAndShareBasedCompensation", "PROF": "ProfessionalFees",
    "LEGAL": "LegalFees", "PCS": "ProfessionalAndContractServicesExpense", "LEASE": "OperatingLeaseExpense",
    "ADV": "AdvertisingExpense", "INS": "GeneralInsuranceExpense", "TRAVEL": "TravelAndEntertainmentExpense",
    "SM": "SellingAndMarketingExpense", "GA": "GeneralAndAdministrativeExpense",
    "BAD": "ProvisionForDoubtfulAccounts", "GAINDISP": "GainLossOnDispositionOfAssets1",
    "OGE": "OtherGeneralExpense", "OOI": "OtherOperatingIncome", "INVINC": "InvestmentIncomeNet",
    "NONOPGL": "NonoperatingGainsLosses", "RENTINC": "RentalIncomeNonoperating",
    "FX": "ForeignCurrencyTransactionGainLossBeforeTax", "ONOI": "OtherNonoperatingIncomeExpense",
    "INT": "InterestAndDebtExpense", "TAX": "IncomeTaxExpenseBenefit",
    "DISC": "IncomeLossFromDiscontinuedOperationsNetOfTax",
}
SPLITS = {"DEBT": ["LTDC", "LTD"], "DEPR": ["COSTDA", "DA"], "PAY": ["SAL", "BEN"]}

# Policy reasons: (defect id or "", rationale, evidence citation)
P = {
    "restricted": ("COA09", "restricted or held-for-others cash: classification against unrestricted cash is a policy decision", "evidence/houseblend_netsuite_100day.md"),
    "foreign": ("COA09", "jurisdiction-specific (non-US) concept with no settled US GAAP target", "evidence/houseblend_netsuite_100day.md"),
    "clearing": ("COA09", "system clearing or suspense account: should net to zero, no target; reclassify by policy", "evidence/houseblend_netsuite_100day.md"),
    "securities": ("COA09", "debt/equity security classification (ASC 320/321) decides the target", "evidence/houseblend_netsuite_100day.md"),
    "related": ("COA07", "related-party or intercompany balance: needs an elimination or presentation rule", "evidence/houseblend_netsuite_100day.md"),
    "provision": ("COA09", "IFRS-style provision: US GAAP recognition differs, no settled target", "evidence/houseblend_netsuite_100day.md"),
    "capitalise": ("COA09", "capitalisation versus expense is a policy choice under US GAAP", "evidence/houseblend_netsuite_100day.md"),
    "software": ("COA09", "software may be property and equipment or an intangible: classification policy", "evidence/houseblend_netsuite_100day.md"),
    "owner": ("COA08", "owner or partner equity in a non-corporate form: equity definition differs from the corporate target", "evidence/houseblend_netsuite_100day.md"),
    "equity_other": ("COA08", "equity reserve concept defined differently from the corporate target", "evidence/houseblend_netsuite_100day.md"),
    "opening": ("COA09", "opening-balance or temporary account: must be reclassified, no target", "evidence/houseblend_netsuite_100day.md"),
    "card": ("COA09", "card balances may be trade payables or short-term borrowings: classification policy", "evidence/houseblend_netsuite_100day.md"),
    "extraordinary": ("COA09", "extraordinary or exceptional items are not a US GAAP category: reclassify by policy", "evidence/houseblend_netsuite_100day.md"),
    "home": ("COA09", "owner home-office or personal item: no target in the platform chart", "evidence/houseblend_netsuite_100day.md"),
    "prior": ("COA09", "prior-period items go to retained earnings under restatement policy, not to income", "evidence/houseblend_netsuite_100day.md"),
    "grant": ("COA09", "government assistance or grant recognition is a policy choice", "evidence/houseblend_netsuite_100day.md"),
    "rebate": ("COA09", "purchase rebates change margin; netting against cost is a policy choice", "evidence/estes_erp_pe_acquisitions.md"),
    "cash_receipt": ("COA09", "cash-receipt income has no accrual counterpart: needs accrual conversion policy", "evidence/consero_rollup_checklist.md"),
    "oci": ("COA09", "unrealised gains: OCI versus net income depends on security classification", "evidence/houseblend_netsuite_100day.md"),
    "nonprofit": ("COA08", "nonprofit contribution or net-asset accounting (ASC 958) has no for-profit counterpart", "evidence/houseblend_netsuite_100day.md"),
    "noncapitalised": ("COA09", "non-GAAP capital purchase expensed in the source: must be capitalised by policy", "evidence/houseblend_netsuite_100day.md"),
    "price_concession": ("COA09", "price concession versus credit loss (ASC 606) is a policy decision", "evidence/houseblend_netsuite_100day.md"),
    "program": ("COA09", "program expense: cost of revenue versus operating expense is not settled", "evidence/houseblend_netsuite_100day.md"),
    "benefit_obl": ("COA09", "employee benefit obligation type (pension or other postemployment) not stated", "evidence/houseblend_netsuite_100day.md"),
    "tax_unclear": ("COA09", "tax type (income or other) not stated: target depends on it", "evidence/houseblend_netsuite_100day.md"),
    "unclear": ("COA09", "source concept is ambiguous; no settled target", "evidence/houseblend_netsuite_100day.md"),
    "collections": ("COA09", "collections may be capitalised or not: policy choice", "evidence/houseblend_netsuite_100day.md"),
    "investment_property": ("COA09", "real estate held for investment has no target in the platform chart", "evidence/houseblend_netsuite_100day.md"),
}


def qbo(t, subs):
    return {f"{t}|{s}": v for s, v in subs.items()}


COA_MAP = {
    "AddOnA": {
        **qbo("Bank", {"CashAndCashEquivalents": "CASH", "CashOnHand": "CASH", "Checking": "CASH", "MoneyMarket": "CASH",
                       "Savings": "CASH", "OtherEarMarkedBankAccounts": "P:restricted", "RentsHeldInTrust": "P:restricted",
                       "TrustAccounts": "P:restricted"}),
        **qbo("Other Current Asset", {
            "AllowanceForBadDebts": "REC", "AssetsAvailableForSale": "HFS", "BalWithGovtAuthorities": "P:foreign",
            "CalledUpShareCapitalNotPaid": "P:foreign", "DevelopmentCosts": "P:capitalise", "EmployeeCashAdvances": "REC",
            "ExpenditureAuthorisationsAndLettersOfCredit": "P:unclear", "GlobalTaxDeferred": "P:foreign",
            "GlobalTaxRefund": "P:foreign", "InternalTransfers": "P:clearing", "Inventory": "INV",
            "Investment_MortgageRealEstateLoans": "P:securities", "Investment_Other": "P:securities",
            "Investment_TaxExemptSecurities": "P:securities", "Investment_USGovernmentObligations": "P:securities",
            "LoansToOfficers": "P:related", "LoansToOthers": "REC", "LoansToStockholders": "P:related",
            "OtherConsumables": "OCA", "OtherCurrentAssets": "OCA", "PrepaidExpenses": "PRE",
            "ProvisionsCurrentAssets": "P:provision", "ShortTermInvestmentsInRelatedParties": "P:related",
            "ShortTermLoansAndAdvancesToRelatedParties": "P:related", "TradeAndOtherReceivables": "REC",
            "Retainage": "REC", "UndepositedFunds": "CASH"}),
        **qbo("Fixed Asset", {
            "AccumulatedAmortization": ["PPE", "INTANG"], "AccumulatedDepletion": "PPE", "AccumulatedDepreciation": "PPE",
            "AssetsInCourseOfConstruction": "PPE", "Buildings": "PPE", "CapitalWip": "PPE",
            "CumulativeDepreciationOnIntangibleAssets": "INTANG", "DepletableAssets": "PPE", "FixedAssetComputers": "PPE",
            "FixedAssetCopiers": "PPE", "FixedAssetFurniture": "PPE", "FixedAssetPhone": "PPE", "FixedAssetPhotoVideo": "PPE",
            "FixedAssetSoftware": "P:software", "FixedAssetOtherToolsEquipment": "PPE", "FurnitureAndFixtures": "PPE",
            "IntangibleAssets": "INTANG", "IntangibleAssetsUnderDevelopment": "INTANG", "Land": "PPE", "LandAsset": "PPE",
            "LeaseholdImprovements": "PPE", "MachineryAndEquipment": "PPE", "NonCurrentAssets": "ONCA",
            "OtherFixedAssets": "PPE", "ParticipatingInterests": "P:related", "ProvisionsFixedAssets": "P:provision",
            "Vehicles": "PPE"}),
        **qbo("Other Asset", {
            "AccumulatedAmortizationOfOtherAssets": "ONCA", "AssetsHeldForSale": "HFS",
            "AvailableForSaleFinancialAssets": "AFSNC", "DeferredTax": "DTA", "Goodwill": "GW", "Investments": "LTI",
            "LeaseBuyout": "P:unclear", "Licenses": "INTANG", "LongTermInvestments": "LTI",
            "LongTermLoansAndAdvancesToRelatedParties": "P:related", "OrganizationalCosts": "P:capitalise",
            "OtherIntangibleAssets": "INTANG", "OtherLongTermAssets": "ONCA", "OtherLongTermInvestments": "LTI",
            "OtherLongTermLoansAndAdvances": "LTI", "PrepaymentsAndAccruedIncome": ["PRE", "REC"],
            "ProvisionsNonCurrentAssets": "P:provision", "SecurityDeposits": "DEPNC"}),
        "Accounts Receivable|Accounts Receivable": "REC",
        **qbo("Equity", {
            "AccumulatedAdjustment": "P:owner", "AccumulatedOtherComprehensiveIncome": "AOCI",
            "CalledUpShareCapital": "CS", "CapitalReserves": "P:equity_other", "CommonStock": "CS",
            "DividendDisbursed": "RE", "EquityInEarningsOfSubsiduaries": "P:related", "EstimatedTaxes": "P:owner",
            "Funds": "P:unclear", "Healthcare": "P:owner", "InvestmentGrants": "P:grant",
            "MoneyReceivedAgainstShareWarrants": "P:foreign", "OtherFreeReserves": "P:equity_other",
            "OpeningBalanceEquity": "P:opening", "OwnersEquity": "P:owner", "PaidInCapitalOrSurplus": "APIC",
            "PartnerContributions": "PART", "PartnerDistributions": "PART", "PersonalIncome": "P:owner",
            "PersonalExpense": "P:owner", "PartnersEquity": "PART", "PreferredStock": "PS", "RetainedEarnings": "RE",
            "ShareApplicationMoneyPendingAllotment": "P:foreign", "ShareCapital": "CS", "TreasuryStock": "TS"}),
        **qbo("Expense", {
            "AdvertisingPromotional": "ADV", "AmortizationExpense": "DA", "AppropriationsToDepreciation": "P:foreign",
            "Auto": "GA", "BadDebts": "BAD", "BankCharges": "GA", "BorrowingCost": "INT",
            "CharitableContributions": "OGE", "CommissionsAndFees": ["SM", "GA"], "CostOfLabor": "SAL",
            "DistributionCosts": "SM", "DuesSubscriptions": "GA", "Entertainment": "TRAVEL",
            "EntertainmentMeals": "TRAVEL", "EquipmentRental": "LEASE", "ExternalServices": "PCS",
            "ExtraordinaryCharges": "P:extraordinary", "FinanceCosts": "INT", "GlobalTaxExpense": "P:foreign",
            "IncomeTaxExpense": "TAX", "Insurance": "INS", "InterestPaid": "INT", "LegalProfessionalFees": ["LEGAL", "PROF"],
            "LossOnDiscontinuedOperationsNetOfTax": "DISC", "ManagementCompensation": "SAL", "OfficeExpenses": "GA",
            "OfficeGeneralAdministrativeExpenses": "GA", "OtherBusinessExpenses": "OGE",
            "OtherCurrentOperatingCharges": "OGE", "OtherExternalServices": "PCS", "OtherMiscellaneousServiceCost": "PCS",
            "OtherRentalCosts": "LEASE", "OtherSellingExpenses": "SM", "PayrollExpenses": "PAY",
            "ProjectStudiesSurveysAssessments": "PCS", "PromotionalMeals": "TRAVEL", "PurchasesRebates": "P:rebate",
            "RentOrLeaseOfBuildings": "LEASE", "RepairMaintenance": "GA", "ShippingAndDeliveryExpense": "SM",
            "ShippingFreightDelivery": "SM", "StaffCosts": "PAY", "Sundry": "OGE", "SuppliesMaterials": "GA",
            "Travel": "TRAVEL", "TravelExpensesGeneralAndAdminExpenses": "TRAVEL",
            "TravelExpensesSellingExpense": "TRAVEL", "TravelMeals": "TRAVEL", "Utilities": "GA",
            "TaxesPaid": "P:tax_unclear", "UnappliedCashBillPaymentExpense": "P:clearing"}),
        **qbo("Other Expense", {
            "Amortization": "DA", "DeferredTaxExpense": "TAX", "Depletion": "COSTDA", "Depreciation": "DEPR",
            "ExceptionalItems": "P:extraordinary", "ExchangeGainOrLoss": "FX", "ExtraordinaryItems": "P:extraordinary",
            "GasAndFuel": "GA", "HomeOffice": "P:home", "HomeOwnerRentalInsurance": "P:home",
            "IncomeTaxOtherExpense": "TAX", "MatCredit": "P:foreign", "MortgageInterest": "P:home",
            "OtherHomeOfficeExpenses": "P:home", "OtherVehicleExpenses": "GA", "OtherMiscellaneousExpense": "OGE",
            "ParkingAndTolls": "GA", "PenaltiesSettlements": "OGE", "PriorPeriodItems": "P:prior",
            "RentAndLease": "LEASE", "RepairsAndMaintenance": "GA", "TaxRoundoffGainOrLoss": "P:foreign",
            "Utilities": "GA", "Vehicle": "GA", "VehicleInsurance": "INS", "VehicleLease": "LEASE",
            "VehicleLoanInterest": "INT", "VehicleLoan": "P:unclear", "VehicleRegistration": "GA",
            "VehicleRepairs": "GA", "WashAndRoadServices": "GA"}),
        **qbo("Cost of Goods Sold", {s: "COGS" for s in [
            "CostOfLaborCos", "CostOfSales", "EquipmentRentalCos", "FreightAndDeliveryCost", "OtherCostsOfServiceCos",
            "ShippingFreightDeliveryCos", "SuppliesMaterialsCogs"]}),
        **qbo("Accounts Payable", {"Accounts Payable": "APA", "OutstandingDuesMicroSmallEnterprise": "APA",
                                   "OutstandingDuesOtherThanMicroSmallEnterprise": "APA"}),
        "Credit Card|Credit Card": "P:card",
        **qbo("Long Term Liability", {
            "AccrualsAndDeferredIncome": ["APANC", "DRNC"], "AccruedLongLermLiabilities": "APANC",
            "AccruedVacationPayable": "APANC", "BankLoans": "DEBT", "DebtsRelatedToParticipatingInterests": "P:related",
            "DeferredTaxLiabilities": "DTL", "GovernmentAndOtherPublicAuthorities": "P:foreign",
            "GroupAndAssociates": "P:related", "LiabilitiesRelatedToAssetsHeldForSale": "P:unclear",
            "LongTermBorrowings": "DEBT", "LongTermDebit": "DEBT", "LongTermEmployeeBenefitObligations": "P:benefit_obl",
            "NotesPayable": "DEBT", "ObligationsUnderFinanceLeases": "DEBT", "OtherLongTermLiabilities": "OLNC",
            "OtherLongTermProvisions": "P:provision", "ProvisionForLiabilities": "P:provision",
            "ProvisionsNonCurrentLiabilities": "P:provision", "ShareholderNotesPayable": "P:related",
            "StaffAndRelatedLongTermLiabilityAccounts": "APANC"}),
        **qbo("Other Current Liability", {
            "AccruedLiabilities": "APA", "CurrentLiabilities": "OCL", "CurrentPortionEmployeeBenefitsObligations": "APA",
            "CurrentPortionOfObligationsUnderFinanceLeases": "LTDC", "CurrentTaxLiability": "APA",
            "DirectDepositPayable": "APA", "DividendsPayable": "APA", "DutiesAndTaxes": "APA",
            "FederalIncomeTaxPayable": "APA", "GlobalTaxPayable": "P:foreign", "GlobalTaxSuspense": "P:foreign",
            "InsurancePayable": "APA", "InterestPayables": "APA", "LineOfCredit": "STB", "LoanPayable": "STB",
            "OtherCurrentLiabilities": "OCL", "PayrollClearing": "P:clearing", "PayrollTaxPayable": "APA",
            "PrepaidExpensesPayable": "P:unclear", "ProvisionForWarrantyObligations": "OCL",
            "ProvisionsCurrentLiabilities": "P:provision", "RentsInTrustLiability": "P:restricted",
            "TrustAccountsLiabilities": "P:restricted", "SalesTaxPayable": "APA", "ShortTermBorrowings": "STB",
            "SocialSecurityAgencies": "APA", "StaffAndRelatedLiabilityAccounts": "APA",
            "StateLocalIncomeTaxPayable": "APA", "SundryDebtorsAndCreditors": "P:unclear",
            "TradeAndOtherPayables": "APA"}),
        **qbo("Income", {
            "CashReceiptIncome": "P:cash_receipt", "DiscountsRefundsGiven": "REV", "NonProfitIncome": "P:nonprofit",
            "OperatingGrants": "P:grant", "OtherCurrentOperatingIncome": "OOI", "OtherPrimaryIncome": "REV",
            "OwnWorkCapitalized": "P:capitalise", "RevenueGeneral": "REV", "SalesOfProductIncome": "REV",
            "SalesRetail": "REV", "SalesWholesale": "REV", "SavingsByTaxScheme": "P:foreign", "ServiceFeeIncome": "REV",
            "UnappliedCashPaymentIncome": "P:clearing"}),
        **qbo("Other Income", {
            "DividendIncome": "INVINC", "GainLossOnSaleOfFixedAssets": "GAINDISP", "GainLossOnSaleOfInvestments": "NONOPGL",
            "InterestEarned": "INVINC", "LossOnDisposalOfAssets": "GAINDISP", "OtherOperatingIncome": "OOI",
            "OtherInvestmentIncome": "INVINC", "OtherMiscellaneousIncome": "ONOI", "TaxExemptInterest": "INVINC",
            "UnrealisedLossOnSecuritiesNetOfTax": "P:oci"}),
    },
    "AddOnB": {
        **{c: "CASH" for c in ["1010", "1020", "1040", "1070"]}, "1110": "REC", "1115": "REC",
        **{c: "P:nonprofit" for c in ["1210", "1215", "1225", "1240", "1245"]},
        "1310": "REC", "1320": "REC", "1325": "REC", "1410": "INV", "1420": "INV", "1450": "PRE", "1460": "REC",
        "1510": "P:securities", "1530": "P:investment_property", "1540": "P:investment_property",
        "1545": "P:investment_property", "1580": "LTI",
        **{c: "PPE" for c in ["1610", "1620", "1630", "1640", "1650", "1660", "1725", "1735", "1745", "1755"]},
        "1810": "ONCA", "1850": "P:nonprofit", "1910": "P:collections", "1950": "TRUST",
        "2010": "APA", "2020": "P:nonprofit", **{c: "APA" for c in ["2110", "2120", "2130", "2140", "2150"]},
        "2310": "DR", "2350": "DR", "2410": "P:nonprofit", "2510": "P:related", "2550": "STB", "2560": "LTDC",
        "2570": "OCL", "2610": "P:nonprofit", "2710": "DEBT", "2730": "DEBT", "2750": "DEBT", "2770": "OLNC",
        "2810": "P:unclear", "2910": "P:restricted",
        **{c: "P:nonprofit" for c in ["3010", "3020", "3030", "3040", "3110", "3120", "3210"]},
        **{c: "P:nonprofit" for c in ["4010", "4020", "4070", "4075", "4085", "4110", "4120", "4130", "4140", "4150",
                                      "4210", "4230", "4250", "4255", "4310", "4350", "4410", "4430",
                                      "4510", "4520", "4530", "4540"]},
        "4420": "P:related",
        **{c: "REV" for c in ["5010", "5020", "5030", "5040", "5080", "5180", "5410", "5440", "5450"]},
        "5185": "P:price_concession", "5210": "P:nonprofit", "5220": "P:nonprofit",
        "5310": "INVINC", "5320": "INVINC", "5360": "INVINC",
        **{c: "RENTINC" for c in ["5330", "5335", "5340", "5345", "5350", "5355"]},
        "5370": "NONOPGL", "5375": "NONOPGL", "5415": "COGS", "5445": "COGS", "5460": "P:related", "5490": "OOI",
        "5810": "P:nonprofit", "5820": "P:nonprofit", "6810": "P:oci", "6820": "P:oci",
        "6910": "P:nonprofit", "6920": "P:nonprofit", "6930": "P:nonprofit",
        "7010": "P:program", **{c: "P:nonprofit" for c in ["7020", "7040", "7050", "7060"]},
        "7210": "SAL", "7220": "SAL", "7230": "BEN", "7240": "BEN", "7250": "BEN",
        "7510": "P:nonprofit", "7520": "PROF", "7530": "LEGAL", "7540": "PROF", "7550": "PCS",
        "7580": "P:nonprofit", "7590": "P:nonprofit",
        **{c: "GA" for c in ["8110", "8130", "8140", "8150", "8170", "8180", "8190"]}, "8120": "P:nonprofit",
        "8210": "LEASE", "8220": "GA", "8230": "GA", "8240": "GA", "8250": "INT", "8260": ["LEASE", "GA"],
        "8270": "DEPR", "8280": "DEPR", "8290": "P:nonprofit", "8310": "TRAVEL", "8320": "TRAVEL",
        "8510": "INT", "8520": "INS", "8530": "GA", "8540": "GA", "8550": "SM", "8560": "PCS", "8570": "ADV",
        "8580": "P:provision", "8590": "OGE", "8610": "BAD", "8620": "GA", "8630": "TAX", "8650": "GA",
        "8660": "OGE", "8670": "GA",
        **{c: "P:noncapitalised" for c in ["9810", "9820", "9830", "9840"]},
        "9910": "P:related", "9920": "P:nonprofit", "9930": "P:nonprofit",
    },
    "AddOnC": {
        "1310": "REC", "1110": "CASH", "1610": "REC", "1651": "DEPC", "1410": "INV",
        **{c: "PPE" for c in ["1710", "1720", "1730", "1740", "1750", "1760", "1780", "1790"]}, "1770": "P:software",
        "1910": "P:opening", "5111": "COGS", "5112": "P:clearing", "5118": "P:clearing", "5119": "COGS",
        "5201": "GA", "5202": "SM", "5203": "DEPR", "5204": "TRAVEL", "5205": "SM", "5206": "LEGAL", "5207": "SM",
        "5208": "GA", "5209": "LEASE", "5210": "GA", "5211": "GA", "5212": "P:clearing", "5213": "SAL", "5214": "SM",
        "5215": "GA", "5216": "TRAVEL", "5217": "GA", "5218": "P:unclear", "5219": "FX", "5220": "GAINDISP",
        "5221": "OGE", "4110": "REV", "4120": "REV", "2110": "APA", "2120": "APA", "2210": "APA", "2211": "APA",
        "2310": "APA", "2410": "STB", "2420": "STB", "2430": "STB", "3100": "CS", "3200": "RE", "3300": "P:opening",
        "3400": "RE",
    },
}

# COA05 (AddOn A only): accrual account categories removed to simulate cash-basis books.
COA05_REMOVED = {
    "accounts receivable": ["Accounts Receivable|Accounts Receivable", "Other Current Asset|TradeAndOtherReceivables",
                            "Other Current Asset|AllowanceForBadDebts", "Other Current Asset|Retainage"],
    "accounts payable": ["Accounts Payable|Accounts Payable", "Accounts Payable|OutstandingDuesMicroSmallEnterprise",
                         "Accounts Payable|OutstandingDuesOtherThanMicroSmallEnterprise",
                         "Other Current Liability|TradeAndOtherPayables"],
    "accrued liabilities": ["Other Current Liability|AccruedLiabilities", "Long Term Liability|AccruedLongLermLiabilities",
                            "Long Term Liability|AccruedVacationPayable"],
    "prepaid expenses": ["Other Current Asset|PrepaidExpenses", "Other Asset|PrepaymentsAndAccruedIncome"],
    "deferred revenue": ["Long Term Liability|AccrualsAndDeferredIncome"],
    "accumulated depreciation": ["Fixed Asset|AccumulatedDepreciation", "Fixed Asset|CumulativeDepreciationOnIntangibleAssets"],
}
COA05_RATIONALE = "source is cash-basis; accrual conversion required"


# ---------------------------------------------------------------------------------------------
def rng(seed, stream):
    return random.Random(f"{seed}:{stream}")


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def load_seed():
    f = OUT / "SEED.txt"
    if f.exists():
        return int(f.read_text().split()[0])
    seed = secrets.randbelow(2**32)
    write_text(f, f"{seed}\n")
    return seed


# ---------------------------------------------------------------------------------------------
# Natural links between UEIs (computed on the real values, before any injection)
def uei_links(rows, by_uei):
    name_to_ueis = collections.defaultdict(set)
    for r in rows:
        name_to_ueis[norm_name(r["recipient_name_raw"])].add(r["recipient_uei"])
    same_name = set()
    for k, v in name_to_ueis.items():
        if k and len(v) > 1:
            same_name |= {tuple(sorted(p)) for p in itertools.combinations(v, 2)}
    names = sorted(k for k in name_to_ueis if k)
    near = set()
    scores = process.cdist(names, names, scorer=fuzz.token_sort_ratio, score_cutoff=NEAR_DUP_THRESHOLD, workers=-1)
    for i, j in zip(*scores.nonzero()):
        if i < j and not (name_to_ueis[names[i]] & name_to_ueis[names[j]]):
            near |= {tuple(sorted((a, b))) for a in name_to_ueis[names[i]] for b in name_to_ueis[names[j]] if a != b}
    addr_to_ueis = collections.defaultdict(set)
    for r in rows:
        if r["recipient_address_line_1"]:
            addr_to_ueis[norm_addr(r["recipient_address_line_1"], r["recipient_zip_4_code"])].add(r["recipient_uei"])
    same_addr = set()
    for v in addr_to_ueis.values():
        if len(v) > 1:
            same_addr |= {tuple(sorted(p)) for p in itertools.combinations(v, 2)}
    child = {(u, r["recipient_parent_uei"]) for u, rs in by_uei.items() for r in rs
             if r["recipient_parent_uei"] and r["recipient_parent_uei"] != u}
    parent_child = {tuple(sorted((c, p))) for c, p in child if p in by_uei}
    kids = collections.defaultdict(set)
    for c, p in child:
        kids[p].add(c)
    siblings = set()
    for cs in kids.values():
        siblings |= {tuple(sorted(p)) for p in itertools.combinations(cs, 2)}
    siblings -= parent_child
    return {"same_name": same_name, "near_name": near - same_name, "parent_child": parent_child,
            "siblings": siblings, "same_addr": same_addr}


def uei_pair_kind(links):
    """Ground truth for a different-UEI pair. Precedence (repo owner, 2026-10-11): a reported parent-child
    relationship (one UEI's records name the other as parent) is known, so it is CV09 non-match even when the
    names match; then name similarity (CV06, unknown); then siblings (CV09); then shared address (unknown)."""
    kind = {}
    for p in sorted(links["same_addr"]):
        kind[p] = ("unknown", "same_address")
    for p in sorted(links["siblings"]):
        kind[p] = ("non-match", "sibling")
    for p in sorted(links["near_name"]):
        kind[p] = ("unknown", "near_name")
    for p in sorted(links["same_name"]):
        kind[p] = ("unknown", "same_name")
    named = links["same_name"] | links["near_name"]
    for p in sorted(links["parent_child"]):
        kind[p] = ("non-match", "parent_child_same_name" if p in named else "parent_child")
    return kind


def pair_label(cfg, truth, k, tags):
    """Decision label for a pair item, from what the system under test can see in this track."""
    if "CV07" in tags:
        return "ESCALATE_AMBIGUOUS", "primary identifier missing on at least one record"
    if k == "parent_child_same_name":
        return ("ESCALATE_POLICY_DECISION", "reported parent-child relationship between entities with the same or "
                "near-same name: keeping them separate or rolling up is a policy decision")
    if k in ("same_name", "near_name"):
        return "DO_NOT_MERGE_CONFLICTING_IDENTIFIER", f"{k.replace('_', ' ')} but different UEIs; identity not established"
    if k in ("parent_child", "sibling"):
        return "AUTO_RESOLVE_NON_MATCH", f"reported corporate hierarchy ({k.replace('_', '-')}); distinct UEIs"
    if truth == "match":
        if "CV04" in tags and cfg["drop"]:
            return "ESCALATE_AMBIGUOUS", "trading name differs from legal name and no identifier is visible (CV04 rule)"
        return "AUTO_RESOLVE_MATCH", "same UEI"
    return "AUTO_RESOLVE_NON_MATCH", "different UEIs, no name, address or hierarchy link"


# ---------------------------------------------------------------------------------------------
def main():
    seed = load_seed()
    rows = list(csv.DictReader(open(RECORDS, encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    by_uei = collections.defaultdict(list)
    for r in rows:
        by_uei[r["recipient_uei"]].append(r)
    blank_uei_before = sum(1 for r in rows if not r["recipient_uei"].strip())
    if blank_uei_before:
        sys.exit(f"{blank_uei_before} blank primary UEIs before injection; stopping (owner rule).")

    links = uei_links(rows, by_uei)
    kind = uei_pair_kind(links)

    # Domain: one draw per connected group of linked UEIs, so every candidate pair stays in one domain.
    dsu = DSU()
    for u in by_uei:
        dsu.find(u)
    for a, b in kind:
        dsu.union(a, b)
    groups = collections.defaultdict(list)
    for u in sorted(by_uei):
        groups[dsu.find(u)].append(u)
    group_list = sorted(groups.values(), key=lambda g: g[0])
    r_dom = rng(seed, "domain")
    domain_of = {}
    for g in group_list:
        d = r_dom.choice(DOMAINS)
        for u in g:
            domain_of[u] = d

    # Task 1: constrained random partition of records into entities.
    dup_pairs = [(a["record_id"], b["record_id"]) for rs in by_uei.values() for a, b in itertools.combinations(rs, 2)]
    pc_rec_pairs = [(a["record_id"], b["record_id"]) for (u, v) in links["parent_child"]
                    for a in by_uei[u] for b in by_uei[v]]
    r_part = rng(seed, "partition")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        entity_of = {r["record_id"]: r_part.choices(ENTITIES, ENTITY_WEIGHTS)[0] for r in rows}
        split = sum(1 for a, b in dup_pairs if entity_of[a] != entity_of[b])
        kept = len(dup_pairs) - split
        if split >= MIN_SPLIT_PAIRS and kept >= MIN_KEPT_PAIRS:
            break
    else:
        sys.exit("partition constraint not met")
    pc_split = sum(1 for a, b in pc_rec_pairs if entity_of[a] != entity_of[b])
    partition = {"attempts": attempt, "dup_pairs_split": split, "dup_pairs_kept": kept,
                 "parent_child_record_pairs_split": pc_split,
                 "parent_child_record_pairs_kept": len(pc_rec_pairs) - pc_split}

    # Record ids (per track, below): per-entity prefix + random 6-digit number, carrying no cluster information.
    true_uei = {r["record_id"]: r["recipient_uei"] for r in rows}

    # Task 2, CV07: blank the primary UEI on a seeded subset per (entity, domain).
    r_inj = rng(seed, "cv07")
    cv07 = set()
    cv07_rates = {}
    for e in ENTITIES:
        for d in DOMAINS:
            cell = sorted(r["record_id"] for r in rows if entity_of[r["record_id"]] == e and domain_of[r["recipient_uei"]] == d)
            n = len(cell)
            k = min(max(round(CV07_RATE * n), math.ceil(CV07_MIN * n)), math.floor(CV07_MAX * n))
            chosen = r_inj.sample(cell, k)
            cv07 |= set(chosen)
            cv07_rates[f"{e}/{d}"] = {"records": n, "injected": k, "rate": round(k / n, 4) if n else None}

    # Task 5 (split): by connected group of UEIs (all candidate pairs live inside one group), 60/40 per
    # (entity, domain) cell, greedy on the seeded order.
    r_split = rng(seed, "split")
    cell_total = collections.Counter((entity_of[r["record_id"]], domain_of[r["recipient_uei"]]) for r in rows)
    order = group_list[:]
    r_split.shuffle(order)  # random order, so both folders get a representative mix of group sizes
    dev_cnt = collections.Counter()
    folder_of_uei = {}
    for g in order:
        c = collections.Counter((entity_of[r["record_id"]], domain_of[u]) for u in g for r in by_uei[u])
        def cost(to_dev):
            return sum(((dev_cnt[k] + (c[k] if to_dev else 0)) - DEV_SHARE * cell_total[k]) ** 2 for k in c)
        f = "dev" if cost(True) <= cost(False) else "holdout"
        if f == "dev":
            dev_cnt.update(c)
        for u in g:
            folder_of_uei[u] = f
    split_share = {f"{e}/{d}": round(dev_cnt[(e, d)] / cell_total[(e, d)], 4) for e in ENTITIES for d in DOMAINS}
    worst = max(abs(v - DEV_SHARE) for v in split_share.values())
    if worst > SPLIT_TOLERANCE:
        sys.exit(f"split tolerance exceeded: {worst:.4f}")

    created = []
    r_cluster = rng(seed, "cluster_ids")
    cluster_id = dict(zip(sorted(by_uei), (f"K{n}" for n in r_cluster.sample(range(100000, 1000000), len(by_uei)))))
    report = {"tracks": {t: {"folders": {}} for t in TRACKS}}
    defect_counts = collections.Counter()

    def has_cv08(r):
        return not r["recipient_address_line_1"] or not r["business_types"]

    for track, cfg in TRACKS.items():
        # Each track gets its own record ids and row order, so ids cannot be joined across tracks.
        r_ids = rng(seed, cfg["stream"]("ids"))
        new_id = {}
        for e in ENTITIES:
            recs_e = sorted(r["record_id"] for r in rows if entity_of[r["record_id"]] == e)
            nums = r_ids.sample(cfg["id_range"], len(recs_e))  # 6 digits in track A, 7 in track B
            for rid_, n in zip(recs_e, nums):
                new_id[rid_] = f"{ID_PREFIX[e]}-{n}"
        r_neg = rng(seed, "negatives")  # same negatives in both tracks
        r_shuffle = rng(seed, cfg["stream"]("row_order"))
        cv07_t = cv07 if cfg["cv07"] else set()
        visible = ["record_id"] + [f for f in fields if f != "record_id" and f not in cfg["drop"]]
        for folder in ["dev", "holdout"]:
            report["tracks"][track]["folders"][folder] = {}
            for d in DOMAINS:
                recs = [r for r in rows if folder_of_uei[r["recipient_uei"]] == folder and domain_of[r["recipient_uei"]] == d]
                rid = lambda r: new_id[r["record_id"]]  # noqa: E731
                base = OUT / track / folder

                # Inputs: one master per entity, visible fields only, shuffled.
                for e in ENTITIES:
                    er = [r for r in recs if entity_of[r["record_id"]] == e]
                    out = []
                    for r in er:
                        v = dict(r, record_id=rid(r))
                        if r["record_id"] in cv07_t:
                            v["recipient_uei"] = ""
                        out.append([v[f] for f in visible])
                    out.sort(key=lambda x: x[0])
                    r_shuffle.shuffle(out)
                    p = base / "masters" / f"{e}_{d}.csv"
                    write_csv(p, visible, out)
                    created.append(p)

                key = base / "answer_key" / d
                # Hidden columns.
                hid = []
                for r in recs:
                    defects = []
                    if r["record_id"] in cv07_t:
                        defects.append("CV07")
                    if has_cv08(r):
                        defects.append("CV08")
                    hid.append([rid(r), entity_of[r["record_id"]], r["record_id"], true_uei[r["record_id"]], ";".join(defects)])
                hid.sort()
                p = key / "records_hidden.csv"
                write_csv(p, ["record_id", "entity"] + HIDDEN, hid)
                created.append(p)

                # Clusters and golden records (survivorship).
                dom_uei = collections.defaultdict(list)
                for r in recs:
                    dom_uei[r["recipient_uei"]].append(r)
                clus_rows, golden_rows = [], []
                for u, rs in sorted(dom_uei.items()):
                    ranked = sorted(rs, key=lambda r: (r["last_seen"], int(r["n_awards"] or 0),
                                                       entity_of[r["record_id"]] == "PlatformCo", r["record_id"]), reverse=True)
                    gold = ranked[0]
                    for r in rs:
                        clus_rows.append([rid(r), cluster_id[u], "true" if r is gold else "false"])

                    def latest_nonblank(f):
                        for r in ranked:
                            if r[f]:
                                return r[f], rid(r)
                        return "", ""

                    def most_common(f):
                        c = collections.Counter(r[f] for r in rs if r[f])
                        if not c:
                            return "", ""
                        v = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                        return v, ";".join(sorted(rid(r) for r in rs if r[f] == v))
                    g = {"recipient_uei": (u, "answer key (true UEI)")}
                    for f in ["recipient_duns", "cage_code"]:
                        g[f] = most_common(f)
                    for f in ["recipient_name", "recipient_name_raw", "recipient_address_line_1", "recipient_address_line_2",
                              "recipient_city_name", "recipient_county_name", "recipient_state_code", "recipient_zip_4_code",
                              "recipient_country_code"]:
                        g[f] = (gold[f], rid(gold))
                    for f in ["recipient_doing_business_as_name", "recipient_parent_uei", "recipient_parent_name",
                              "business_types", "organizational_type"]:
                        g[f] = latest_nonblank(f)
                    naics = sorted({c for r in rs for c in r["naics_codes"].split(";") if c})
                    g["naics_codes"] = (";".join(naics), "union of all records")
                    golden_rows.append([cluster_id[u], rid(gold)] + [x for f in GOLDEN_FIELDS for x in g[f]])
                clus_rows.sort()
                p = key / "entity_clusters.csv"
                write_csv(p, ["record_id", "cluster_id", "is_golden_record"], clus_rows)
                created.append(p)
                p = key / "golden_records.csv"
                write_csv(p, ["cluster_id", "golden_record_id"] + [x for f in GOLDEN_FIELDS for x in (f, f + "__source")],
                          sorted(golden_rows))
                created.append(p)

                # Record pairs.
                pairs = []  # (a, b, truth, kind)
                for u, rs in dom_uei.items():
                    for a, b in itertools.combinations(rs, 2):
                        pairs.append((a, b, "match", "same_uei"))
                for (u, v), (truth, k) in kind.items():
                    if u in dom_uei and v in dom_uei:
                        for a in dom_uei[u]:
                            for b in dom_uei[v]:
                                pairs.append((a, b, truth, k))
                n_match = sum(1 for p_ in pairs if p_[2] == "match")
                linked = set(kind)
                by_zip = collections.defaultdict(list)
                for r in recs:
                    by_zip[r["recipient_zip_4_code"][:5]].append(r)
                cand = []
                for z in sorted(by_zip):
                    for a, b in itertools.combinations(sorted(by_zip[z], key=lambda r: r["record_id"]), 2):
                        if a["recipient_uei"] != b["recipient_uei"] and tuple(sorted((a["recipient_uei"], b["recipient_uei"]))) not in linked:
                            cand.append((a, b))
                neg = r_neg.sample(cand, min(len(cand), n_match))
                pairs += [(a, b, "non-match", "zip5_block_negative") for a, b in neg]

                pair_rows, dec_rows = [], []
                for a, b, truth, k in pairs:
                    x, y = sorted((rid(a), rid(b)))
                    pid = f"{x}|{y}"
                    ra, rb = (a, b) if rid(a) == x else (b, a)
                    pair_rows.append([x, y, truth, k])
                    if k == "same_address":
                        continue  # not a taxonomy row: no decision label (synthetic/PROPOSED_DEFECTS.md)
                    tags = []
                    if ra["record_id"] in cv07_t or rb["record_id"] in cv07_t:
                        tags.append("CV07")
                    if k in ("same_name", "near_name"):
                        tags.append("CV06")
                    if k in ("parent_child", "parent_child_same_name", "sibling"):
                        tags.append("CV09")
                    if truth == "match":
                        same_ent = entity_of[ra["record_id"]] == entity_of[rb["record_id"]]
                        raw_diff = ra["recipient_name_raw"] != rb["recipient_name_raw"]
                        if same_ent and raw_diff:
                            tags.append("CV01")
                        if not same_ent:
                            tags.append("CV02")
                        if raw_diff and norm_name(ra["recipient_name_raw"]) == norm_name(rb["recipient_name_raw"]):
                            tags.append("CV03")
                        if any(r["recipient_doing_business_as_name"] and norm_name(r["recipient_doing_business_as_name"])
                               != norm_name(r["recipient_name_raw"]) for r in (ra, rb)):
                            tags.append("CV04")
                        if norm_addr(ra["recipient_address_line_1"], ra["recipient_zip_4_code"]) != norm_addr(rb["recipient_address_line_1"], rb["recipient_zip_4_code"]):
                            tags.append("CV05")
                    label, why = pair_label(cfg, truth, k, tags)
                    for t_ in tags:
                        defect_counts[(track, folder, d, "pair", t_)] += 1
                    dec_rows.append(["pair", pid, label, ";".join(tags), why])
                pair_rows.sort()
                p = key / "record_pairs.csv"
                write_csv(p, ["record_id_a", "record_id_b", "same_entity", "pair_basis"], pair_rows)
                created.append(p)

                # Record-level decisions (CV07 injected, track A only; CV08 natural).
                for r in recs:
                    tags = (["CV07"] if r["record_id"] in cv07_t else []) + (["CV08"] if has_cv08(r) else [])
                    if tags:
                        why = "; ".join(({"CV07": "primary identifier (UEI) blank",
                                          "CV08": "address line 1 or business types blank"})[t_] for t_ in tags)
                        dec_rows.append(["record", rid(r), "ESCALATE_AMBIGUOUS", ";".join(tags), why])
                        for t_ in tags:
                            defect_counts[(track, folder, d, "record", t_)] += 1
                # Cluster-level decisions (CV10 natural): conflicting visible attributes across records of one entity.
                for u, rs in sorted(dom_uei.items()):
                    if len(rs) < 2:
                        continue
                    conflicts = []
                    if len({r["business_types"] for r in rs}) > 1:
                        conflicts.append("business_types")
                    if "recipient_parent_uei" in visible and len({r["recipient_parent_uei"] for r in rs if r["recipient_parent_uei"]}) > 1:
                        conflicts.append("recipient_parent_uei")
                    if conflicts:
                        dec_rows.append(["cluster", cluster_id[u], "ESCALATE_POLICY_DECISION", "CV10",
                                         "conflicting " + " and ".join(conflicts) + " across records of one entity"])
                        defect_counts[(track, folder, d, "cluster", "CV10")] += 1
                dec_rows.sort()
                p = key / "decisions.csv"
                write_csv(p, ["item_type", "item_id", "outcome_label", "defect_ids", "rationale"], dec_rows)
                created.append(p)

                report["tracks"][track]["folders"][folder][d] = {
                    "records": len(recs), "ueis": len(dom_uei),
                    "records_per_entity": {e: sum(1 for r in recs if entity_of[r["record_id"]] == e) for e in ENTITIES},
                    "pairs": dict(collections.Counter(t for _, _, t, _ in pairs)),
                    "pair_basis": dict(collections.Counter(k for _, _, _, k in pairs)),
                    "labels": dict(collections.Counter(x[2] for x in dec_rows)),
                    "cv07_records": sum(1 for r in recs if r["record_id"] in cv07_t),
                }

    # ---------------------------------------------------------------------------------------------
    # Charts and CoA answer key.
    target_rows = list(csv.DictReader(open(ROOT / "coa" / CHARTS["PlatformCo"], encoding="utf-8", newline="")))
    target_codes = {r["gl_code"] for r in target_rows}
    target_name = {r["gl_code"]: r["account_name"] for r in target_rows}
    removed = {c for cs in COA05_REMOVED.values() for c in cs}
    charts_meta = {"PlatformCo": {"source_chart": f"coa/{CHARTS['PlatformCo']}", "role": "platform target", "cash_basis": False}}
    for track in TRACKS:
        p = OUT / track / "charts" / "PlatformCo_chart.csv"
        write_bytes_copy(ROOT / "coa" / CHARTS["PlatformCo"], p)
        created.append(p)
    coa_rows_by_entity = {}
    coa05_gaps = {}
    for e in ["AddOnA", "AddOnB", "AddOnC"]:
        chart = list(csv.DictReader(open(ROOT / "coa" / CHARTS[e], encoding="utf-8", newline="")))
        cols = list(chart[0].keys())
        parents = {r["parent_code"] for r in chart if r["parent_code"]}
        if e == "AddOnA":
            ledgers = [r for r in chart if r["parent_code"]]  # detail types; type rows are categories
        elif e == "AddOnC":
            ledgers = [r for r in chart if r["description"].startswith("ledger account")]
        else:
            ledgers = [r for r in chart if r["gl_code"] not in parents and len(r["gl_code"]) == 4]
        m = COA_MAP[e]
        codes = [r["gl_code"] for r in ledgers]
        missing, extra = set(codes) - set(m), set(m) - set(codes)
        if missing or extra or len(codes) != len(set(codes)):
            sys.exit(f"{e}: unmapped {sorted(missing)}; unknown {sorted(extra)}")
        if e == "AddOnA" and removed - set(codes):
            sys.exit(f"COA05 codes not in chart: {sorted(removed - set(codes))}")
        resolved = {}
        for c in codes:
            v = m[c]
            if isinstance(v, str) and v.startswith("P:"):
                resolved[c] = ("policy", v[2:])
            else:
                ts = SPLITS.get(v, v) if isinstance(v, str) else v
                ts = [ts] if isinstance(ts, str) else ts
                full = ["us-gaap:" + T[t] for t in ts]
                for f_ in full:
                    if f_ not in target_codes:
                        sys.exit(f"{e} {c}: target {f_} not in platform chart")
                resolved[c] = ("map", full)
        present = [c for c in codes if not (e == "AddOnA" and c in removed)]
        on_target = collections.Counter(resolved[c][1][0] for c in present
                                        if resolved[c][0] == "map" and len(resolved[c][1]) == 1)
        # Row: [key, source_code(s), source name(s), source_present, target, type, rationale, decision?, defect, citation]
        out = []
        name_of = {r["gl_code"]: r["account_name"] for r in chart}
        gaps = collections.defaultdict(list)  # COA05: platform target -> removed AddOn A accounts that fed it
        for c in codes:
            kind_, val = resolved[c]
            if e == "AddOnA" and c in removed:
                for t_ in val:
                    gaps[t_].append(c)
                continue
            if kind_ == "policy":
                dfx, why, cite = P[val]
                out.append([c, c, name_of[c], "true", "", "MAP_REQUIRES_ACCOUNTING_POLICY", why, "true", dfx, cite])
                continue
            if len(val) > 1:
                out.append([c, c, name_of[c], "true", ";".join(val), "MAP_SPLIT_REQUIRED",
                            "balance must be divided across " + " and ".join(target_name[v] for v in val),
                            "true", "COA03", "evidence/houseblend_netsuite_100day.md"])
            elif on_target[val[0]] > 1:
                out.append([c, c, name_of[c], "true", val[0], "MAP_MANY_TO_ONE",
                            f"one of {on_target[val[0]]} source accounts rolling into {target_name[val[0]]}",
                            "false", "COA02", "evidence/consero_rollup_checklist.md"])
            else:
                out.append([c, c, name_of[c], "true", val[0], "MAP_DIRECT", f"same concept as {target_name[val[0]]}",
                            "false", "COA01", "evidence/houseblend_netsuite_100day.md"])
        # The removed accounts are not in the chart the system sees, so the scorable item is the platform target
        # that the cash-basis chart can no longer feed: one row per target.
        for t_, cs in sorted(gaps.items()):
            out.append([f"cash_basis::{t_}", ";".join(cs), ";".join(name_of[c] for c in cs), "false", t_,
                        "MAP_REQUIRES_ACCOUNTING_POLICY", COA05_RATIONALE, "true", "COA05",
                        "evidence/consero_rollup_checklist.md"])
        coa_rows_by_entity[e] = out
        if e == "AddOnA":
            coa05_gaps = gaps
        # Input chart for the system under test. Type headers left with no detail rows go too.
        kept_rows = [r for r in chart if not (e == "AddOnA" and r["gl_code"] in removed)]
        if e == "AddOnA":
            with_kids = {r["parent_code"] for r in kept_rows if r["parent_code"]}
            kept_rows = [r for r in kept_rows if r["parent_code"] or r["gl_code"] in with_kids]
        for track in TRACKS:
            p = OUT / track / "charts" / f"{e}_chart.csv"
            write_csv(p, cols, [[r[k] for k in cols] for r in kept_rows])
            created.append(p)
        charts_meta[e] = {"source_chart": f"coa/{CHARTS[e]}", "role": "add-on source",
                          "cash_basis": e == "AddOnA", "rows": len(kept_rows), "ledger_accounts_mapped": len(codes)}
    for track in TRACKS:
        p = OUT / track / "charts" / "charts.json"
        write_text(p, json.dumps(charts_meta, indent=2) + "\n")
        created.append(p)

    # CoA split: rows sharing a target within one entity stay together (union over split targets).
    r_coa = rng(seed, "coa_split")
    coa_folder = {}
    coa_split_share = {}
    for e, out in coa_rows_by_entity.items():
        dsu_c = DSU()
        for row in out:
            node = ("src", row[0])
            dsu_c.find(node)
            for t_ in filter(None, row[4].split(";")):
                if row[5] in ("MAP_MANY_TO_ONE", "MAP_SPLIT_REQUIRED", "MAP_DIRECT"):
                    dsu_c.union(node, ("tgt", t_))
        comps = collections.defaultdict(list)
        for row in out:
            comps[dsu_c.find(("src", row[0]))].append(row[0])
        comp_list = sorted(comps.values(), key=lambda x: x[0])
        r_coa.shuffle(comp_list)
        n_dev = 0
        for comp in comp_list:
            to_dev = abs(n_dev + len(comp) - DEV_SHARE * len(out)) <= abs(n_dev - DEV_SHARE * len(out))
            for c in comp:
                coa_folder[(e, c)] = "dev" if to_dev else "holdout"
            n_dev += len(comp) if to_dev else 0
        coa_split_share[e] = round(n_dev / len(out), 4)
        if abs(coa_split_share[e] - DEV_SHARE) > COA_SPLIT_TOLERANCE:
            sys.exit(f"CoA split tolerance exceeded for {e}: {coa_split_share[e]}")

    coa_header = ["mapping_id", "entity", "source_code", "source_account_name", "source_present", "target_code",
                  "mapping_type", "rationale", "business_decision_required", "defect_ids", "citation"]
    review_header = ["mapping_id", "entity", "source_chart", "source_account", "source_name", "target_account",
                     "target_name", "mapping_type", "rationale"]
    for folder in ["dev", "holdout"]:
        maps, decs, review = [], [], []
        for e, out in coa_rows_by_entity.items():
            for row in out:
                if coa_folder[(e, row[0])] != folder:
                    continue
                mid = f"{e}::{row[0]}"
                maps.append([mid, e] + row[1:])
                decs.append(["mapping", mid, row[5], row[8], row[6]])
                review.append([mid, e, f"coa/{CHARTS[e]}", row[1], row[2], row[4],
                               ";".join(target_name[t_] for t_ in filter(None, row[4].split(";"))), row[5], row[6]])
        maps.sort()
        decs.sort()
        review.sort()
        for track in TRACKS:
            for row in maps:
                defect_counts[(track, folder, "coa", "mapping", row[9])] += 1
            p = OUT / track / folder / "answer_key" / "coa" / "coa_mappings.csv"
            write_csv(p, coa_header, maps)
            created.append(p)
            p = OUT / track / folder / "answer_key" / "coa" / "decisions.csv"
            write_csv(p, ["item_type", "item_id", "outcome_label", "defect_ids", "rationale"], decs)
            created.append(p)
            report["tracks"][track]["folders"][folder]["coa"] = {
                "mappings": len(maps), "per_entity": dict(collections.Counter(x[1] for x in maps)),
                "labels": dict(collections.Counter(x[6] for x in maps))}
        # Export for independent review of the mapping key (same rows as the answer key).
        p = OUT / "review" / f"coa_mappings_{folder}.csv"
        write_csv(p, review_header, review)
        created.append(p)

    # ---------------------------------------------------------------------------------------------
    removed_log = []
    for cat, cs in COA05_REMOVED.items():
        for c in cs:
            targets = sorted(t_ for t_, srcs in coa05_gaps.items() if c in srcs)
            removed_log.append({"category": cat, "source_code": c, "would_have_targeted": ";".join(targets),
                                "answer_key_items": [f"AddOnA::cash_basis::{t_}" for t_ in targets],
                                "label": "MAP_REQUIRES_ACCOUNTING_POLICY", "rationale": COA05_RATIONALE})
    qbo_ledgers = len(COA_MAP["AddOnA"])
    injection_log = {
        "seed": seed,
        "generated": datetime.date.today().isoformat(),
        "CV07": {"defect": "primary identifier missing (recipient_uei blanked)", "tracks": ["track_a"],
                 "target_rate": CV07_RATE, "allowed_range": [CV07_MIN, CV07_MAX],
                 "blank_primary_uei_before_injection": blank_uei_before,
                 "total_records": len(rows), "total_injected": len(cv07),
                 "overall_rate": round(len(cv07) / len(rows), 4),
                 "per_entity_domain": cv07_rates,
                 "hidden_column": "defect_ids in track_a/<split>/answer_key/<domain>/records_hidden.csv; true UEI in true_recipient_uei"},
        "track_b": {"identifier_columns_removed": IDENTIFIER_COLUMNS, "cv07": "not applicable"},
        "COA05": {"defect": "add-on keeps cash-basis books: accrual accounts absent", "entity": "AddOnA",
                  "chart": f"coa/{CHARTS['AddOnA']}", "cash_basis": True,
                  "ledger_accounts_before": qbo_ledgers, "removed": len(removed),
                  "rate": round(len(removed) / qbo_ledgers, 4), "answer_key_items": len(coa05_gaps),
                  "removed_accounts": removed_log,
                  "citation": "evidence/consero_rollup_checklist.md"},
    }
    p = OUT / "injection_log.json"
    write_text(p, json.dumps(injection_log, indent=2) + "\n")
    created.append(p)

    stats = {"seed": seed, "partition": partition, "split_share": split_share, "coa_split_share": coa_split_share,
             "cv07": cv07_rates, "links": {k: len(v) for k, v in links.items()},
             "uei_pair_kind": dict(collections.Counter(v[1] for v in kind.values())),
             "tracks": {t: {"name": c["name"], "identifier_columns_removed": c["drop"], "cv07": c["cv07"]}
                        for t, c in TRACKS.items()},
             "domain_ueis": dict(collections.Counter(domain_of.values())),
             "entity_records": dict(collections.Counter(entity_of.values())),
             "report": report, "defects": {"|".join(k): v for k, v in sorted(defect_counts.items())},
             "coa05_removed": len(removed)}
    p = OUT / "generation_stats.json"
    write_text(p, json.dumps(stats, indent=2) + "\n")
    created.append(p)
    created.append(OUT / "SEED.txt")
    for name, text in [("GENERATION_REPORT.md", generation_report(stats, injection_log)),
                       ("PROPOSED_DEFECTS.md", PROPOSED_DEFECTS), ("README.md", SYNTHETIC_README)]:
        write_text(OUT / name, text)
        created.append(OUT / name)

    files = []
    for f in sorted(set(created), key=lambda x: x.relative_to(ROOT).as_posix()):
        b = f.read_bytes()
        files.append({"path": f.relative_to(ROOT).as_posix(), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    manifest = {"generated": datetime.date.today().isoformat(), "generator": "scripts/generate_synthetic.py",
                "seed": seed, "partition_attempts": partition["attempts"], "file_count": len(files), "files": files}
    write_text(OUT / "MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: stats[k] for k in ["seed", "partition", "links", "uei_pair_kind", "domain_ueis",
                                            "entity_records", "coa_split_share"]}, indent=1))
    print(f"{len(files)} files hashed into synthetic/MANIFEST.json")


def generation_report(s, inj):
    T_ = s["report"]["tracks"]
    A = T_["track_a"]["folders"]
    L = ["# Generation report", "",
         f"Generated {inj['generated']} by `scripts/generate_synthetic.py`, seed {s['seed']} (`synthetic/SEED.txt`). "
         "Every number below is computed by the script. Holdout figures are counts only.", "",
         "## Tracks", "",
         "| track | name | identifier columns in the inputs | CV07 |", "|---|---|---|---|",
         f"| `track_b` | no-shared-identifier (headline) | none: {', '.join(f'`{c}`' for c in s['tracks']['track_b']['identifier_columns_removed'])} removed | not applicable |",
         "| `track_a` | shared-identifier | all, `recipient_uei` blanked on CV07 records | 5% per domain per entity |", "",
         "Both tracks share the seed, partition, dev/holdout split, entity clusters, sampled negatives and chart-of-accounts key. "
         "Record ids and row order differ between tracks, so ids cannot be joined across them.", "",
         "## Partition (Task 1)", "",
         f"- Attempts until the constraint held: {s['partition']['attempts']}",
         f"- Natural duplicate pairs (same UEI) split across entities: {s['partition']['dup_pairs_split']:,}; "
         f"kept within one entity: {s['partition']['dup_pairs_kept']:,} (minimum 15 each)",
         f"- Parent-child record pairs split: {s['partition']['parent_child_record_pairs_split']:,}; "
         f"kept: {s['partition']['parent_child_record_pairs_kept']:,}",
         f"- UEIs per domain: customer {s['domain_ueis']['customer']:,}, vendor {s['domain_ueis']['vendor']:,}", "",
         "## Records per entity and domain (both tracks)", "",
         "| entity | domain | records | dev | holdout | dev share | CV07 injected (track A) | CV07 rate |",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
    for e in ENTITIES:
        for d in DOMAINS:
            c = s["cv07"][f"{e}/{d}"]
            dv, ho = A["dev"][d]["records_per_entity"][e], A["holdout"][d]["records_per_entity"][e]
            L.append(f"| {e} | {d} | {c['records']:,} | {dv:,} | {ho:,} | {s['split_share'][f'{e}/{d}']:.1%} | "
                     f"{c['injected']} | {c['rate']:.2%} |")
    L += ["", f"CV07 overall (track A): {inj['CV07']['total_injected']} of {inj['CV07']['total_records']:,} records "
          f"({inj['CV07']['overall_rate']:.2%}); blank primary UEIs before injection: "
          f"{inj['CV07']['blank_primary_uei_before_injection']}.", "",
          "## Chart of accounts (both tracks)", "",
          f"COA05 (AddOn A, cash basis): {inj['COA05']['removed']} of {inj['COA05']['ledger_accounts_before']} ledger "
          f"accounts removed ({inj['COA05']['rate']:.2%}); list in `synthetic/injection_log.json`. The system never sees "
          f"those accounts, so the answer key scores them as {inj['COA05']['answer_key_items']} items, one per platform "
          "target account the cash-basis chart can no longer feed (`AddOnA::cash_basis::<target>`).", "",
          "| folder | AddOn A | AddOn B | AddOn C | DIRECT | MANY_TO_ONE | SPLIT | REQUIRES_POLICY |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for f in ["dev", "holdout"]:
        c, lb = A[f]["coa"]["per_entity"], A[f]["coa"]["labels"]
        L.append(f"| {f} | {c.get('AddOnA', 0)} | {c.get('AddOnB', 0)} | {c.get('AddOnC', 0)} | {lb.get('MAP_DIRECT', 0)} | "
                 f"{lb.get('MAP_MANY_TO_ONE', 0)} | {lb.get('MAP_SPLIT_REQUIRED', 0)} | "
                 f"{lb.get('MAP_REQUIRES_ACCOUNTING_POLICY', 0)} |")
    L += ["", "Dev share of mapping rows per add-on: "
          + ", ".join(f"{e} {v:.1%}" for e, v in s["coa_split_share"].items()) + ". "
          "The mapping key awaits independent review (`synthetic/review/`).", ""]
    for track in ["track_b", "track_a"]:
        F = T_[track]["folders"]
        L += [f"## Answer-key items: {track} ({s['tracks'][track]['name']})", "",
              "| folder | domain | records | clusters | match pairs | non-match pairs | unknown pairs | decision items | escalations |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for f in ["dev", "holdout"]:
            for d in DOMAINS:
                x = F[f][d]
                esc = sum(v for k, v in x["labels"].items() if k in ESCALATE_LABELS)
                L.append(f"| {f} | {d} | {x['records']:,} | {x['ueis']:,} | {x['pairs'].get('match', 0):,} | "
                         f"{x['pairs'].get('non-match', 0):,} | {x['pairs'].get('unknown', 0):,} | "
                         f"{sum(x['labels'].values()):,} | {esc:,} |")
            lb = F[f]["coa"]["labels"]
            L.append(f"| {f} | coa | | | | | | {sum(lb.values())} | {lb.get('MAP_REQUIRES_ACCOUNTING_POLICY', 0)} |")
        L.append("")
        L += ["| folder | domain | " + " | ".join(sorted(ESCALATE_LABELS | {"AUTO_RESOLVE_MATCH", "AUTO_RESOLVE_NON_MATCH"})) + " |",
              "|---|---|" + "---:|" * 6]
        for f in ["dev", "holdout"]:
            for d in DOMAINS:
                lb = F[f][d]["labels"]
                L.append(f"| {f} | {d} | " + " | ".join(f"{lb.get(k, 0):,}" for k in sorted(ESCALATE_LABELS | {"AUTO_RESOLVE_MATCH", "AUTO_RESOLVE_NON_MATCH"})) + " |")
        L.append("")
    tot_unknown = sum(A[f][d]["pairs"].get("unknown", 0) for f in A for d in DOMAINS)
    L += [f"Unknown pairs (same in both tracks): {tot_unknown:,} record pairs. They come from "
          f"{s['uei_pair_kind'].get('same_name', 0)} same-name and {s['uei_pair_kind'].get('near_name', 0)} near-name "
          f"UEI pairs (CV06) and {s['uei_pair_kind'].get('same_address', 0)} same-address UEI pairs (not a taxonomy row; "
          "see `PROPOSED_DEFECTS.md`). Scoring leaves them out of pairwise precision and recall.", "",
          "## Natural versus injected defect counts", "",
          "Pair counts are record pairs. One pair can carry several CV tags.", "",
          "| defect | origin | track A dev | track A holdout | track B dev | track B holdout |", "|---|---|---:|---:|---:|---:|"]
    agg = collections.defaultdict(collections.Counter)
    for k, v in s["defects"].items():
        t, f, d, unit, dfx = k.split("|")
        agg[(dfx, unit)][(t, f)] += v
    for (dfx, unit), c in sorted(agg.items()):
        origin = "injected" if dfx in ("CV07", "COA05") else "natural"
        L.append(f"| {dfx} ({unit}s) | {origin} | {c[('track_a', 'dev')]:,} | {c[('track_a', 'holdout')]:,} | "
                 f"{c[('track_b', 'dev')]:,} | {c[('track_b', 'holdout')]:,} |")
    pc, pcn = s["uei_pair_kind"].get("parent_child", 0), s["uei_pair_kind"].get("parent_child_same_name", 0)
    L += ["", "## UEI links used for ground truth", "",
          f"Distinct UEI pairs: same normalized name {s['links']['same_name']}, near-duplicate name {s['links']['near_name']}, "
          f"parent-child {s['links']['parent_child']}, siblings {s['links']['siblings']}, same address {s['links']['same_addr']}. "
          "Precedence when one pair has several links: reported parent-child (non-match, CV09), then name similarity "
          "(unknown, CV06), then siblings (non-match, CV09), then shared address (unknown).", "",
          f"All {pc + pcn} parent-child pairs are CV09 non-match: {pc} with different names keep AUTO_RESOLVE_NON_MATCH, "
          f"and {pcn} that also share a name are ESCALATE_POLICY_DECISION (repo owner, 2026-10-11). Those {pcn} were "
          "`unknown` (CV06) in the previous run.", "",
          "These counts differ from `entities/profile.md` on purpose. The profile adds up UEI pairs per name or address "
          "group, so one pair can count twice, and it counts near-duplicates as name pairs. Here every UEI pair counts once.", "",
          "## Track differences in labels", "",
          "- CV07 exists only in track A. Its records and pairs are ESCALATE_AMBIGUOUS there.",
          "- CV04 match pairs (trading name differs from legal name): AUTO_RESOLVE_MATCH in track A when both UEIs are visible; "
          "ESCALATE_AMBIGUOUS in track B, where no identifier is visible (repo owner, 2026-10-11).",
          "- CV10 in track B uses only visible attributes (business types); parent-UEI conflicts count only in track A.", "",
          "## Taxonomy rows not applied", "",
          "- COA04 (legacy chart bloat): not applicable. The charts carry no usage data (`docs/injection_decisions.md`). On the v2 list.",
          "- COA06 (revenue recognition basis): not applicable. It cannot be seen in a chart of accounts. On the v2 list.",
          "- CV07: injected in track A only; not applicable to track B.",
          "- All other rows except CV07 and COA05 are natural only, with no injection. COA01, COA02, COA03, COA07, COA08 "
          "and COA09 are tagged on mapping rows; CV01 to CV06 and CV09 on record pairs; CV08 on records; CV10 on clusters.", ""]
    return "\n".join(L)


PROPOSED_DEFECTS = """# Proposed defects (not applied)

Written by `scripts/generate_synthetic.py`. Nothing here is injected or labelled with a taxonomy outcome.

## Different UEIs sharing one normalized street address and ZIP

- Observed: 99 groups, 135 UEI pairs (`entities/profile.md`). The taxonomy lists it under "observed in real data but
  described by no evidence extract".
- Why it matters here: the profile says these are unresolved (re-registered businesses, franchisees, firms in a shared
  building). The repo owner gave the same reason for marking CV06 pairs "unknown". The answer key therefore marks these
  pairs `unknown` in `record_pairs.csv` (pair_basis `same_address`), gives them no decision label, and scoring excludes
  them from pairwise precision and recall.
- Needed before it becomes a row: an evidence extract describing shared-address entities in master-data consolidation,
  and a decision by the repo owner.
"""

SYNTHETIC_README = """# synthetic/: generated layer

Generated by `scripts/generate_synthetic.py` (seed in `SEED.txt`); every file is hashed in `MANIFEST.json`.
Scored by `scripts/score.py --track a|b --split dev|holdout --pred <folder>`.

## Tracks

- **`track_b/`, no-shared-identifier: the realistic configuration and the headline result.** Every identifier column
  (`recipient_uei`, `recipient_parent_uei`, `recipient_duns`, `recipient_parent_duns`, `cage_code`) is removed from the
  files the system under test reads. Identity must come from names, addresses and attributes. CV07 does not apply.
- **`track_a/`, shared-identifier: tests escalation behaviour when an identifier exists.** UEIs are visible, and
  CV07 blanks them on 5% of records per domain per entity.

Both tracks come from the same seed, partition and dev/holdout split. A system scored on track B must not read
`track_a/`: its inputs carry the identifiers that track B withholds.

## Layout (per track)

- `charts/`: input charts. `charts.json` tags AddOn A `cash_basis: true` (COA05).
- `dev/masters/`, `holdout/masters/`: input customer and vendor masters per entity.
- `dev/answer_key/`: dev answer keys (`customer/`, `vendor/`, `coa/`).
- `holdout/answer_key/`: holdout answer keys. **The person building the tool under test must not open this folder.**

## Shared files

- `review/coa_mappings_dev.csv`, `review/coa_mappings_holdout.csv`: the chart-of-accounts mapping key exported for
  independent review. **The mapping key awaits independent review**: it was written by the generating model, not by an
  independent party. The holdout file goes to the reviewer unopened.
- `injection_log.json`: exact injection rates and the removed AddOn A accounts.
- `GENERATION_REPORT.md`: counts only.
- `PROPOSED_DEFECTS.md`: observed conditions proposed as taxonomy rows, not applied.
"""


GOLDEN_FIELDS = ["recipient_uei", "recipient_duns", "cage_code", "recipient_name", "recipient_name_raw",
                 "recipient_doing_business_as_name", "recipient_parent_uei", "recipient_parent_name",
                 "recipient_address_line_1", "recipient_address_line_2", "recipient_city_name", "recipient_county_name",
                 "recipient_state_code", "recipient_zip_4_code", "recipient_country_code", "business_types",
                 "organizational_type", "naics_codes"]


def write_bytes_copy(src_path, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src_path.read_bytes())


if __name__ == "__main__":
    main()
