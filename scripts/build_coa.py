"""Build cleaned chart-of-accounts CSVs in coa/ from the raw files in sources/coa/.

Run from the repo root:
    uv run --with xlrd python -I -X utf8 scripts/build_coa.py

Every output row comes from a published source file. No accounts are invented and
no mappings between charts are created. Output columns (fixed order):
    gl_code, account_name, account_type, normal_balance, description, parent_code
Cells are left empty when the source does not supply a value. Where normal_balance
is derived, it follows only the standard rule (asset/expense debit;
liability/equity/revenue credit) unless the source itself marks the account as a
contra; README.md says which applies per chart.
"""
from __future__ import annotations

import ast
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "coa"
OUT = ROOT / "coa"
COLUMNS = ["gl_code", "account_name", "account_type", "normal_balance", "description", "parent_code"]

STANDARD_BALANCE = {
    "asset": "debit",
    "expense": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
}
FLIP = {"debit": "credit", "credit": "debit"}


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    codes = [r["gl_code"] for r in rows if r["gl_code"]]
    dupes = {c for c in codes if codes.count(c) > 1}
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else str(r.get(k)).strip()) for k in COLUMNS})
    print(f"{name}: {len(rows)} rows" + (f" (duplicate gl_code values kept as in source: {sorted(dupes)})" if dupes else ""))


def num_text(v) -> str:
    """Render a spreadsheet cell as text without inventing precision."""
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return str(v).strip()


# ---------------------------------------------------------------------------
# 1. UCOA (Unified Chart of Accounts v3.0, CAN/NCCS)
# ---------------------------------------------------------------------------
UCOA_CLASS_TYPE = {
    "1": "asset",
    "2": "liability",
    "3": "equity",
    "4": "revenue",
    "5": "revenue",
    "6": "revenue",
    "7": "expense",
    "8": "expense",
    "9": "expense",
}
UCOA_XREF_COLS = [
    (1, "UCOA v2.2 account"),
    (3, "Illustrative GAAP exhibit line"),
    (4, "Form 990 line"),
    (5, "Form 990-EZ line"),
    (6, "OMB A-122 cost principle"),
    (7, "United Way of America Accounting Guide"),
    (8, "Tennessee Policy 03 template"),
]


def build_ucoa() -> list[dict]:
    import xlrd

    book = xlrd.open_workbook(str(SRC / "ucoa_nonprofit" / "UCOA-version 3.xls"))
    sheet = book.sheet_by_name("pages 1-6")
    # Layout rules observed in the source sheet:
    #   * column A holds a single digit for class headers (1 Assets ... 9 Non-GAAP expenses);
    #   * non-indented 4-digit codes ending in "00" are group headers (e.g. 1000 Cash:, 7000 Grants...);
    #   * indented rows directly below a group header (no blank row in between) belong to that group;
    #   * a blank row ends the group, so indented rows after a blank row (e.g. 2410, 9910) and
    #     non-indented detail codes (e.g. 1810, 1950) are attached to the class header only.
    rows: list[dict] = []
    cur_class = cur_group = None
    for r in range(sheet.nrows):
        vals = sheet.row_values(r)
        c0, name_raw = vals[0], vals[2]
        name = str(name_raw).strip()
        if c0 in ("", None) and not name:
            cur_group = None  # blank row closes the current group
            continue
        code = suffix = None
        if isinstance(c0, float):
            code = str(int(c0))
        elif isinstance(c0, str) and re.fullmatch(r"\d{4}-\*\*\*", c0.strip()):
            code, suffix = c0.strip()[:4], c0.strip()[4:]
        else:
            continue  # totals and column headings such as "version 3.0", "Account", "Number"
        if len(code) == 1:  # class header
            cur_class, cur_group = code, None
            rows.append(dict(gl_code=code, account_name=name, account_type=UCOA_CLASS_TYPE[code],
                             normal_balance=STANDARD_BALANCE[UCOA_CLASS_TYPE[code]],
                             description="UCOA class header", parent_code=""))
            continue
        acct_type = UCOA_CLASS_TYPE[cur_class]
        indented = str(name_raw).startswith(" ")
        if not indented and suffix is None and code.endswith("00"):
            cur_group = code
            rows.append(dict(gl_code=code, account_name=name.rstrip(":").strip(), account_type=acct_type,
                             normal_balance=STANDARD_BALANCE[acct_type], description="UCOA group header",
                             parent_code=cur_class))
            continue
        parent = cur_group if (indented and cur_group) else cur_class
        xref = []
        contra = False
        for idx, label in UCOA_XREF_COLS:
            v = num_text(vals[idx])
            if v:
                xref.append(f"{label}: {v}")
                if "contra" in v.lower():
                    contra = True
        if suffix:
            xref.append("Account number takes an activity-code suffix (-***) per UCOA page 7")
        bal = STANDARD_BALANCE[acct_type]
        if contra:
            bal = FLIP[bal]
            xref.append("Marked contra in source; normal_balance flipped")
        rows.append(dict(gl_code=code, account_name=name, account_type=acct_type, normal_balance=bal,
                         description="; ".join(xref), parent_code=parent))
    return rows


# ---------------------------------------------------------------------------
# 2. QuickBooks Online account types and detail types (Intuit API reference)
# ---------------------------------------------------------------------------
QBO_CLASS = {"ASSET": "asset", "EQUITY": "equity", "EXPENSE": "expense", "LIABILITY": "liability", "REVENUE": "revenue"}
QBO_SKIP = {"ACCOUNT TYPE", "ACCOUNT SUB TYPE", "Default"}


def build_qbo() -> list[dict]:
    text = (SRC / "quickbooks_online" / "intuit_api_account_types_subtypes.txt").read_text(encoding="utf-8")
    body = text.split("-----BEGIN RENDERED TEXT-----", 1)[1].split("-----END RENDERED TEXT-----", 1)[0]
    body = body.split("Hide child attributes", 1)[1]
    rows: list[dict] = []
    cls = None
    seen: set[str] = set()
    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        items = []
        for ln in lines:
            if ln in QBO_CLASS:
                cls = QBO_CLASS[ln]
            elif ln not in QBO_SKIP:
                items.append(ln)
        if not items:
            continue
        acct_type, subtypes = items[0], items[1:]
        rows.append(dict(gl_code=acct_type, account_name=acct_type, account_type=cls,
                         normal_balance=STANDARD_BALANCE[cls],
                         description="QBO AccountType (AccountTypeEnum value)", parent_code=""))
        for st in subtypes:
            is_default = st.endswith("(default)")
            st_name = st.replace("(default)", "").strip()
            code = f"{acct_type}|{st_name}"
            if code in seen:
                continue  # e.g. "Utilities" is listed twice under Expense in the source
            seen.add(code)
            rows.append(dict(gl_code=code, account_name=st_name, account_type=cls,
                             normal_balance=STANDARD_BALANCE[cls],
                             description="QBO AccountSubType (detail type)" + ("; marked (default) for this account type in source" if is_default else ""),
                             parent_code=acct_type))
    return rows


# ---------------------------------------------------------------------------
# 3. ERPNext "Standard with Numbers" chart (frappe/erpnext, GPL-3.0)
# ---------------------------------------------------------------------------
# The source is a Python module. It is parsed with `ast` and never imported or executed.
# Account names are wrapped in the translation call _("..."); the parser unwraps them.
ERPNEXT_FILE = SRC / "erpnext_standard_numbered" / "standard_chart_of_accounts_with_account_number.py"
ERPNEXT_PROPS = {"account_type", "account_number", "is_group", "root_type", "tax_rate", "account_currency"}
ERPNEXT_ROOT = {"Asset": "asset", "Liability": "liability", "Equity": "equity",
                "Income": "revenue", "Expense": "expense"}
# ERPNext account_type values that are contra to their root type.
ERPNEXT_CONTRA = {"Accumulated Depreciation"}


class _UnwrapTranslate(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "_" and len(node.args) == 1:
            return node.args[0]
        return self.generic_visit(node)


def build_erpnext() -> list[dict]:
    tree = ast.parse(ERPNEXT_FILE.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get")
    ret = next(n for n in ast.walk(fn) if isinstance(n, ast.Return))
    chart = ast.literal_eval(_UnwrapTranslate().visit(ret.value))
    rows: list[dict] = []

    def walk(name: str, node: dict, root: str, parent: str) -> None:
        root = ERPNEXT_ROOT.get(node.get("root_type", ""), root)
        children = [(k, v) for k, v in node.items() if k not in ERPNEXT_PROPS and isinstance(v, dict)]
        code = str(node.get("account_number", ""))
        etype = node.get("account_type", "")
        balance = STANDARD_BALANCE.get(root, "")
        notes = ["group account" if (children or node.get("is_group")) else "ledger account"]
        if etype:
            notes.append(f"ERPNext account_type: {etype}")
        if etype in ERPNEXT_CONTRA and balance:
            balance = FLIP[balance]
            notes.append("contra (normal balance flipped from root type)")
        rows.append(dict(gl_code=code, account_name=name, account_type=root, normal_balance=balance,
                         description="; ".join(notes), parent_code=parent))
        for k, v in children:
            walk(k, v, root, code)

    for name, node in chart.items():
        walk(name, node, "", "")
    return rows

# ---------------------------------------------------------------------------
# 4. US GAAP Financial Reporting Taxonomy 2026 (FASB): classified balance sheet
#    and income statement presentation networks, monetary line items only
# ---------------------------------------------------------------------------
XL = "{http://www.w3.org/1999/xlink}"
XS = "{http://www.w3.org/2001/XMLSchema}"
XBRLI = "{http://www.xbrl.org/2003/instance}"
LINK = "{http://www.xbrl.org/2003/linkbase}"
STD_LABEL = "http://www.xbrl.org/2003/role/label"
DOC_LABEL = "http://www.xbrl.org/2003/role/documentation"
TOTAL_LABEL = "http://www.xbrl.org/2003/role/totalLabel"
GAAP_NETWORKS = [
    ("us-gaap-2026/stm/us-gaap-stm-sfp-cls-pre-2026.xml", "sfp"),
    ("us-gaap-2026/stm/us-gaap-stm-soi-pre-2026.xml", "soi"),
]
SFP_TYPE_BY_ANCESTOR = {
    "us-gaap_AssetsAbstract": "asset",
    "us-gaap_LiabilitiesAbstract": "liability",
    "us-gaap_TemporaryEquityAbstract": "temporary_equity",
    "us-gaap_StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract": "equity",
    "us-gaap_StockholdersEquityNumberOfSharesParValueAndOtherDisclosuresAbstract": "equity",
    "us-gaap_PartnersCapitalIncludingPortionAttributableToNoncontrollingInterestAbstract": "equity",
    "us-gaap_PartnersCapitalNumberOfUnitsParValueAndOtherDisclosuresAbstract": "equity",
    "us-gaap_LimitedLiabilityCompanyLLCMembersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract": "equity",
}


def _labels(zf: zipfile.ZipFile, member: str, role: str) -> dict[str, str]:
    root = ET.fromstring(zf.read(member))
    out: dict[str, str] = {}
    for link in root.iter(LINK + "labelLink"):
        locs, res, arcs = {}, {}, []
        for e in link:
            tag = e.tag
            if tag == LINK + "loc":
                locs[e.get(XL + "label")] = e.get(XL + "href").split("#")[1]
            elif tag == LINK + "label" and e.get(XL + "role") == role:
                res[e.get(XL + "label")] = (e.text or "").strip()
            elif tag == LINK + "labelArc":
                arcs.append((e.get(XL + "from"), e.get(XL + "to")))
        for f, t in arcs:
            if f in locs and t in res:
                out.setdefault(locs[f], res[t])
    return out


def build_gaap() -> tuple[list[dict], int, set[tuple[str, str]]]:
    zpath = SRC / "us_gaap_xbrl_2026" / "us-gaap-2026.zip"
    with zipfile.ZipFile(zpath) as zf:
        schema = ET.fromstring(zf.read("us-gaap-2026/elts/us-gaap-2026.xsd"))
        elts = {}
        for e in schema.iter(XS + "element"):
            elts[e.get("id")] = dict(name=e.get("name"), type=e.get("type"), abstract=e.get("abstract") == "true",
                                     subst=e.get("substitutionGroup"), balance=e.get(XBRLI + "balance") or "")
        std = _labels(zf, "us-gaap-2026/elts/us-gaap-lab-2026.xml", STD_LABEL)
        doc = _labels(zf, "us-gaap-2026/elts/us-gaap-doc-2026.xml", DOC_LABEL)
        rows: list[dict] = []
        seen: set[str] = set()
        dup_dropped = 0
        totals: set[tuple[str, str]] = set()  # (group, child) arcs the taxonomy marks as the group total
        for member, net in GAAP_NETWORKS:
            root = ET.fromstring(zf.read(member))
            locs, kids, has_parent = {}, defaultdict(list), set()
            for e in root.iter(LINK + "loc"):
                locs[e.get(XL + "label")] = e.get(XL + "href").split("#")[1]
            for e in root.iter(LINK + "presentationArc"):
                f, t = locs[e.get(XL + "from")], locs[e.get(XL + "to")]
                kids[f].append((float(e.get("order", "0")), t))
                if e.get("preferredLabel") == TOTAL_LABEL and f in elts and t in elts:
                    totals.add(("us-gaap:" + elts[f]["name"], "us-gaap:" + elts[t]["name"]))
                has_parent.add(t)
            roots = [k for k in kids if k not in has_parent]

            def is_line_item(eid: str) -> bool:
                el = elts.get(eid)
                return bool(el) and el["subst"] == "xbrli:item" and "domainItemType" not in (el["type"] or "")

            memo: dict[str, bool] = {}

            def keep(eid: str) -> bool:
                """Monetary line items, plus abstract headers that contain at least one."""
                if eid not in memo:
                    el = elts.get(eid)
                    if not is_line_item(eid):
                        memo[eid] = False
                    elif el["abstract"]:
                        memo[eid] = any(keep(c) for _, c in kids[eid])
                    else:
                        memo[eid] = el["type"] == "xbrli:monetaryItemType"
                return memo[eid]

            def walk(eid: str, parent_kept: str, sfp_type: str):
                nonlocal dup_dropped
                t = SFP_TYPE_BY_ANCESTOR.get(eid, sfp_type)
                next_parent = parent_kept
                if keep(eid):
                    el = elts[eid]
                    code = "us-gaap:" + el["name"]
                    if code in seen:
                        dup_dropped += 1
                    else:
                        seen.add(code)
                        acct_type = t if net == "sfp" else "income_statement"
                        rows.append(dict(gl_code=code, account_name=std.get(eid, el["name"]),
                                         account_type=acct_type, normal_balance=el["balance"],
                                         description=doc.get(eid, ""), parent_code=parent_kept))
                    next_parent = code
                for _, c in sorted(kids[eid]):
                    walk(c, next_parent, t)

            for r in roots:
                walk(r, "", "")
    return rows, dup_dropped, totals


# ---------------------------------------------------------------------------
# 5. Platform target: an operating-size chart derived from the GAAP subset
# ---------------------------------------------------------------------------
# Selection rule (also in coa/README.md). Start from the 951-row subset above, without its
# shared root us-gaap:StatementLineItems. Walk each [Abstract] group top-down:
#   - Expand the group if its presentation subtree in the subset has at least
#     PLATFORM_MIN_GROUP_SIZE elements (the group itself plus all descendants), or if the
#     taxonomy marks no total for it. An expanded group becomes a group account; its children
#     are visited in presentation order; its own total element is dropped, because the group
#     account stands for that sum.
#   - Otherwise collapse it: the group's total element (the child the taxonomy presents with
#     the totalLabel role) becomes one ledger account in the group's place.
# Non-abstract children of an expanded group are kept as ledger accounts, with their own
# descendants (if any) dropped. All column values are copied from the subset row.
PLATFORM_MIN_GROUP_SIZE = 35


def build_gaap_platform(rows: list[dict], totals: set[tuple[str, str]]) -> list[dict]:
    by = {r["gl_code"]: r for r in rows}
    kids: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        kids[r["parent_code"]].append(r["gl_code"])
    total_of = {g: c for g, c in totals if g in by and c in by and by[c]["parent_code"] == g}
    is_group = lambda c: by[c]["account_name"].endswith("[Abstract]")
    size_memo: dict[str, int] = {}

    def size(c: str) -> int:
        if c not in size_memo:
            size_memo[c] = 1 + sum(size(k) for k in kids[c])
        return size_memo[c]

    out: list[dict] = []

    def add(code: str, parent: str, note: str) -> None:
        r = dict(by[code])
        r["parent_code"] = parent
        r["description"] = note + (". " + r["description"] if r["description"] else "")
        out.append(r)

    def visit(g: str, parent: str) -> None:
        if size(g) >= PLATFORM_MIN_GROUP_SIZE or g not in total_of:
            add(g, parent, "group account")
            for k in kids[g]:
                if total_of.get(g) == k:
                    continue
                if is_group(k):
                    visit(k, g)
                else:
                    add(k, g, "ledger account")
        else:
            add(total_of[g], parent, f"ledger account; stands for collapsed group {g}")

    for top in kids["us-gaap:StatementLineItems"]:
        if is_group(top):
            visit(top, "")
        else:
            add(top, "", "ledger account")
    return out


def main() -> int:
    write_csv("ucoa_nonprofit.csv", build_ucoa())
    write_csv("quickbooks_online_types.csv", build_qbo())
    write_csv("erpnext_standard_numbered.csv", build_erpnext())
    gaap_rows, dropped, totals = build_gaap()
    write_csv("us_gaap_xbrl_2026_subset.csv", gaap_rows)
    write_csv("us_gaap_platform_target.csv", build_gaap_platform(gaap_rows, totals))
    print(f"us_gaap_xbrl_2026_subset.csv: {dropped} repeated presentation occurrences dropped (first occurrence kept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
