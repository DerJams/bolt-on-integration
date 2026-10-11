"""Write MANIFEST.json: every file under sources/, coa/, entities/, er-benchmarks/ with its
source URL, download date and SHA-256.

`download_date` is the file's last-modified date (UTC). Files produced by a script from other
repo files are marked `derived_by` instead of a source URL.
"""
import datetime, hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRS = ["sources", "coa", "entities", "er-benchmarks"]

LEIPZIG = "https://dbs.uni-leipzig.de/files/datasets/"
ERPNEXT = "https://raw.githubusercontent.com/frappe/erpnext/bfd8100d42162048248b7b947f2e21fdf7999a91/"
# Longest matching prefix wins. Values: ("url", ...) or ("derived", script).
SOURCE_MAP = {
    "sources/usaspending/PrimeAwardSummariesAndSubawards_": ("url", json.loads(
        (ROOT / "sources/usaspending/download_request.json").read_text())["file_url"]),
    "sources/usaspending/download_request.json": ("derived", "scripts/fetch_usaspending.py (request log)"),
    "sources/er/Abt-Buy.zip": ("url", LEIPZIG + "Abt-Buy.zip"),
    "sources/er/Amazon-GoogleProducts.zip": ("url", LEIPZIG + "Amazon-GoogleProducts.zip"),
    "sources/er/DBLP-ACM.zip": ("url", LEIPZIG + "DBLP-ACM.zip"),
    "sources/evidence_pages/alixpartners": ("url", "https://www.alixpartners.com/insights/102k22b/scaling-ma-5-keys-to-an-integration-ready-platform/"),
    "sources/evidence_pages/cohnreznick": ("url", "https://www.cohnreznick.com/insights/how-top-pe-firms-are-winning-with-add-on-acquisitions"),
    "sources/evidence_pages/consero": ("url", "https://conseroglobal.com/resources/roll-up-strategy/"),
    "sources/evidence_pages/estes": ("url", "https://www.estesgrp.com/blog/the-erp-decisions-behind-successful-private-equity-acquisitions/"),
    "sources/evidence_pages/houseblend": ("url", "https://www.houseblend.io/articles/en/centjoursintegrationfusionsacquisitionsplannetsuite"),
    "sources/evidence_pages/pmistack": ("url", "https://pmistack.com/blog/erp-consolidation-after-merger"),
    "sources/evidence_pages/ssa": ("url", "https://ssaandco.com/case-studies/developed-integration-playbook-to-improve-speed-to-ebitda-by-25-for-pe-owned-dental-roll-up/"),
    "sources/coa/us_gaap_xbrl_2026/": ("url", "https://xbrl.fasb.org/us-gaap/2026/us-gaap-2026.zip"),
    "sources/coa/quickbooks_online/": ("url", "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account"),
    "sources/coa/ucoa_nonprofit/UCOA-version 3.xls": ("url", "http://web.archive.org/web/20100114053415id_/http://nccsdataweb.urban.org/kbfiles/402/UCOA-version%203.xls"),
    "sources/coa/ucoa_nonprofit/UCOA version 3 .zip": ("url", "http://web.archive.org/web/20100114053448id_/http://nccsdataweb.urban.org/kbfiles/400/UCOA%20version%203%20.zip"),
    "sources/coa/ucoa_nonprofit/UCOA PUBLIC LICENSE": ("url", "http://web.archive.org/web/20110105095317id_/http://nccsdataweb.urban.org/kbfiles/405/UCOA%20PUBLIC%20LICENSE%20v.%201.1.pdf"),
    "sources/coa/ucoa_nonprofit/nccs_projects_ucoa.cfm.html": ("url", "http://web.archive.org/web/20070604183128id_/http://www.nccs.urban.org/projects/ucoa.cfm"),
    "sources/coa/erpnext_standard_numbered/standard_chart": ("url", ERPNEXT + "erpnext/accounts/doctype/account/chart_of_accounts/verified/standard_chart_of_accounts_with_account_number.py"),
    "sources/coa/erpnext_standard_numbered/license.txt": ("url", ERPNEXT + "license.txt"),
    "coa/README.md": ("derived", "hand-written provenance notes"),
    "coa/": ("derived", "scripts/build_coa.py"),
    "entities/recipient_records.csv": ("derived", "scripts/build_entities.py"),
    "entities/profile.md": ("derived", "scripts/profile_entities.py"),
    "er-benchmarks/baseline_results.md": ("derived", "scripts/er_baseline.py"),
    "er-benchmarks/README.md": ("derived", "hand-written provenance notes"),
    "er-benchmarks/abt-buy/": ("url", LEIPZIG + "Abt-Buy.zip (extracted)"),
    "er-benchmarks/amazon-google/": ("url", LEIPZIG + "Amazon-GoogleProducts.zip (extracted)"),
    "er-benchmarks/dblp-acm/": ("url", LEIPZIG + "DBLP-ACM.zip (extracted)"),
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = []
    for d in DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            key = max((k for k in SOURCE_MAP if rel.startswith(k)), key=len, default=None)
            kind, val = SOURCE_MAP[key] if key else ("unmapped", None)
            entry = {"path": rel, "bytes": p.stat().st_size, "sha256": sha256(p),
                     "download_date": datetime.datetime.fromtimestamp(
                         p.stat().st_mtime, datetime.UTC).date().isoformat()}
            entry["source_url" if kind == "url" else "derived_by" if kind == "derived" else "unmapped"] = val
            files.append(entry)
    unmapped = [f["path"] for f in files if "unmapped" in f]
    out = {"generated": datetime.date.today().isoformat(), "file_count": len(files), "files": files}
    (ROOT / "MANIFEST.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{len(files)} files written to MANIFEST.json; unmapped: {unmapped or 'none'}")


if __name__ == "__main__":
    main()
