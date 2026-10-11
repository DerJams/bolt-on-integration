"""Build real entity records from the untouched USAspending zip in sources/usaspending/.

One output row per distinct recipient *record variant*: the combination of identifiers,
names, parent, address and business types exactly as reported on awards. The same UEI can
therefore appear on several rows when agencies reported it with different name or address
spellings. That is real, naturally occurring master-data messiness and is kept on purpose.

Excluded on purpose: phone and fax numbers and highly compensated officer names (personal
data, not needed for the benchmark).

Output: entities/recipient_records.csv
"""
import csv, glob, io, pathlib, zipfile, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "usaspending"
OUT = ROOT / "entities" / "recipient_records.csv"

KEY_FIELDS = [
    "recipient_uei", "recipient_duns", "cage_code",
    "recipient_name", "recipient_name_raw", "recipient_doing_business_as_name",
    "recipient_parent_uei", "recipient_parent_duns", "recipient_parent_name", "recipient_parent_name_raw",
    "recipient_address_line_1", "recipient_address_line_2", "recipient_city_name",
    "recipient_county_name", "recipient_state_code", "recipient_zip_4_code", "recipient_country_code",
]
# Business-type flag columns in the contract award summary file (value "t" when set).
FLAG_START, FLAG_END = "alaskan_native_corporation_owned_firm", "historically_underutilized_business_zone_hubzone_firm"
SKIP_FLAGS = {"organizational_type", "contracting_officers_determination_of_business_size",
              "contracting_officers_determination_of_business_size_code"}


def truthy(v):
    return v.strip().lower() in {"t", "true", "y", "yes", "1"}


def main():
    zpath = sorted(SRC.glob("PrimeAwardSummariesAndSubawards_*.zip"))[-1]
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.startswith("Contracts_PrimeAwardSummaries"))
        reader = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", newline=""))
        cols = reader.fieldnames
        flags = [c for c in cols[cols.index(FLAG_START): cols.index(FLAG_END) + 1] if c not in SKIP_FLAGS]
        groups = collections.OrderedDict()
        for row in reader:
            btypes = ";".join(c for c in flags if truthy(row.get(c, "")))
            org_type = row.get("organizational_type", "").strip()
            key = tuple(row[f].strip() for f in KEY_FIELDS) + (btypes, org_type)
            g = groups.setdefault(key, {"n_awards": 0, "naics": set(), "first": None, "last": None})
            g["n_awards"] += 1
            g["naics"].add(row["naics_code"])
            for d in (row.get("award_base_action_date", ""), row.get("award_latest_action_date", "")):
                d = d[:10]
                if d:
                    g["first"] = d if not g["first"] or d < g["first"] else g["first"]
                    g["last"] = d if not g["last"] or d > g["last"] else g["last"]

    header = ["record_id"] + KEY_FIELDS + ["business_types", "organizational_type",
              "naics_codes", "n_awards", "first_seen", "last_seen"]
    ordered = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][4], kv[0][10]))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, (key, g) in enumerate(ordered, 1):
            w.writerow([f"R{i:05d}", *key, ";".join(sorted(g["naics"])), g["n_awards"],
                        g["first"] or "", g["last"] or ""])
    print(f"source: {zpath.name}/{name}")
    print(f"records: {len(ordered)}  unique UEIs: {len({k[0] for k in groups})}")


if __name__ == "__main__":
    main()
