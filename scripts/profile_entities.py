"""Profile naturally occurring messiness in entities/recipient_records.csv.

Writes entities/profile.md. Counts only real conditions in the downloaded records; nothing
here is injected. Run: uv run --with rapidfuzz --with numpy python -I scripts/profile_entities.py
"""
import csv, collections, datetime, itertools, pathlib, re
from rapidfuzz import fuzz, process

ROOT = pathlib.Path(__file__).resolve().parent.parent
IN = ROOT / "entities" / "recipient_records.csv"
OUT = ROOT / "entities" / "profile.md"
NEAR_DUP_THRESHOLD = 92  # token_sort_ratio on normalized names, different UEIs

SUFFIXES = r"\b(INCORPORATED|INC|CORPORATION|CORP|CO|COMPANY|LLC|L L C|LLP|LP|LTD|LIMITED|PC|P C|PLLC|DBA|THE)\b"
ADDR_ABBR = {"SUITE": "STE", "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "ROAD": "RD",
             "DRIVE": "DR", "NUMBER": "#", "NO": "#", "UNIT": "#", "STE": "#", "PARKWAY": "PKWY",
             "HIGHWAY": "HWY", "COURT": "CT", "LANE": "LN", "PLACE": "PL", "CIRCLE": "CIR"}


def norm_name(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_addr(a, z):
    toks = re.sub(r"[^A-Z0-9# ]", " ", a.upper()).split()
    return " ".join(ADDR_ABBR.get(t, t) for t in toks) + "|" + z[:5]


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "n/a"


def main():
    rows = list(csv.DictReader(open(IN, encoding="utf-8", newline="")))
    n = len(rows)
    by_uei = collections.defaultdict(list)
    for r in rows:
        by_uei[r["recipient_uei"]].append(r)
    U = len(by_uei)
    L = []  # report lines

    def distinct(rs, f):
        return {r[f] for r in rs if r[f]}

    # Within-UEI variation (same real entity, several master-record spellings)
    multi = {u: rs for u, rs in by_uei.items() if len(rs) > 1}
    name_var = {u for u, rs in by_uei.items() if len(distinct(rs, "recipient_name_raw")) > 1}
    name_var_norm = {u for u, rs in by_uei.items() if len({norm_name(r["recipient_name_raw"]) for r in rs}) > 1}
    addr_var = {u for u, rs in by_uei.items()
                if len({norm_addr(r["recipient_address_line_1"], r["recipient_zip_4_code"]) for r in rs}) > 1}
    addr_fmt_only = {u for u, rs in by_uei.items()
                     if len({(r["recipient_address_line_1"], r["recipient_zip_4_code"][:5]) for r in rs}) > 1
                     and len({norm_addr(r["recipient_address_line_1"], r["recipient_zip_4_code"]) for r in rs}) == 1}
    duns_var = {u for u, rs in by_uei.items() if len(distinct(rs, "recipient_duns")) > 1}
    cage_var = {u for u, rs in by_uei.items() if len(distinct(rs, "cage_code")) > 1}
    parent_var = {u for u, rs in by_uei.items() if len(distinct(rs, "recipient_parent_uei")) > 1}
    btype_var = {u for u, rs in by_uei.items() if len({r["business_types"] for r in rs}) > 1}
    within_pairs = sum(len(rs) * (len(rs) - 1) // 2 for rs in by_uei.values())

    # Raw versus normalized name, DBA
    raw_vs_clean = sum(1 for r in rows if r["recipient_name_raw"] and r["recipient_name_raw"] != r["recipient_name"])
    dba = [r for r in rows if r["recipient_doing_business_as_name"]]
    dba_diff = [r for r in dba if norm_name(r["recipient_doing_business_as_name"]) != norm_name(r["recipient_name_raw"])]

    # Across-UEI conditions (different identifiers)
    name_to_ueis = collections.defaultdict(set)
    for r in rows:
        name_to_ueis[norm_name(r["recipient_name_raw"])].add(r["recipient_uei"])
    same_name_diff_uei = {k: v for k, v in name_to_ueis.items() if k and len(v) > 1}
    same_name_pairs = sum(len(v) * (len(v) - 1) // 2 for v in same_name_diff_uei.values())

    names = sorted(k for k in name_to_ueis if k)
    near = []
    scores = process.cdist(names, names, scorer=fuzz.token_sort_ratio, score_cutoff=NEAR_DUP_THRESHOLD, workers=-1)
    for i, j in zip(*scores.nonzero()):
        if i < j and not (name_to_ueis[names[i]] & name_to_ueis[names[j]]):
            near.append((names[i], names[j], int(scores[i, j])))

    addr_to_ueis = collections.defaultdict(set)
    for r in rows:
        if r["recipient_address_line_1"]:
            addr_to_ueis[norm_addr(r["recipient_address_line_1"], r["recipient_zip_4_code"])].add(r["recipient_uei"])
    shared_addr = {k: v for k, v in addr_to_ueis.items() if len(v) > 1}
    shared_addr_pairs = sum(len(v) * (len(v) - 1) // 2 for v in shared_addr.values())

    # Parent-child
    child = {(u, r["recipient_parent_uei"]) for u, rs in by_uei.items() for r in rs
             if r["recipient_parent_uei"] and r["recipient_parent_uei"] != u}
    child_ueis = {c for c, _ in child}
    parent_in_set = {(c, p) for c, p in child if p in by_uei}
    siblings = collections.defaultdict(set)
    for c, p in child:
        siblings[p].add(c)
    sib_groups = {p: cs for p, cs in siblings.items() if len(cs) > 1}
    parent_name_mismatch = sum(1 for c, p in parent_in_set
                               if norm_name(by_uei[p][0]["recipient_name_raw"]) not in
                               {norm_name(r["recipient_parent_name_raw"] or r["recipient_parent_name"]) for r in by_uei[c]})

    # Missing fields
    fields = ["recipient_uei", "recipient_duns", "cage_code", "recipient_doing_business_as_name", "recipient_parent_uei",
              "recipient_parent_name", "recipient_address_line_1", "recipient_address_line_2",
              "recipient_city_name", "recipient_county_name", "recipient_zip_4_code", "business_types"]
    zip5_only = sum(1 for r in rows if len(r["recipient_zip_4_code"]) == 5)
    sole = {u for u, rs in by_uei.items() if any("sole_proprietorship" in r["business_types"] for r in rs)}
    lower = sum(1 for r in rows if any(c.islower() for c in r["recipient_name_raw"]))
    naics_groups = collections.Counter()
    for u, rs in by_uei.items():
        for g in {c[:4] for r in rs for c in r["naics_codes"].split(";")}:
            naics_groups[g] += 1

    L += [f"# Entity profile: naturally occurring messiness",
          "",
          f"Generated {datetime.date.today().isoformat()} by `scripts/profile_entities.py` from "
          f"`entities/recipient_records.csv`. Every count below is a real condition in the downloaded "
          f"USAspending records. Nothing has been injected.",
          "",
          "## Population",
          "",
          f"| measure | value |", "|---|---:|",
          f"| record variants (rows) | {n:,} |",
          f"| unique recipient UEIs | {U:,} |",
          f"| UEIs with more than one record variant | {len(multi):,} ({pct(len(multi), U)}) |",
          f"| max record variants for one UEI | {max(len(v) for v in by_uei.values())} |",
          "",
          "UEIs by NAICS group (a UEI can appear in more than one):",
          "",
          "| NAICS group | UEIs |", "|---|---:|"]
    L += [f"| {g} | {c:,} |" for g, c in sorted(naics_groups.items())]
    L += ["",
          "## Same identifier, different master-record content (natural duplicates)",
          "",
          "A *natural duplicate pair* is two record variants that share a UEI. "
          f"There are **{within_pairs:,}** such pairs.",
          "",
          "| condition | UEIs affected | share of UEIs |", "|---|---:|---:|",
          f"| raw legal name spelled more than one way | {len(name_var):,} | {pct(len(name_var), U)} |",
          f"| ...and still different after suffix/punctuation normalization | {len(name_var_norm):,} | {pct(len(name_var_norm), U)} |",
          f"| more than one address (after abbreviation normalization) | {len(addr_var):,} | {pct(len(addr_var), U)} |",
          f"| address differs only in formatting | {len(addr_fmt_only):,} | {pct(len(addr_fmt_only), U)} |",
          f"| more than one DUNS | {len(duns_var):,} | {pct(len(duns_var), U)} |",
          f"| more than one CAGE code | {len(cage_var):,} | {pct(len(cage_var), U)} |",
          f"| more than one parent UEI over time | {len(parent_var):,} | {pct(len(parent_var), U)} |",
          f"| business-type flags disagree across records | {len(btype_var):,} | {pct(len(btype_var), U)} |",
          "",
          "## Name forms within a record",
          "",
          "| condition | records | share of records |", "|---|---:|---:|",
          f"| raw name differs from USAspending-normalized name | {raw_vs_clean:,} | {pct(raw_vs_clean, n)} |",
          f"| DBA name present | {len(dba):,} | {pct(len(dba), n)} |",
          f"| DBA present and materially different from legal name | {len(dba_diff):,} | {pct(len(dba_diff), n)} |",
          f"| name contains lowercase letters (mixed case) | {lower:,} | {pct(lower, n)} |",
          "",
          "## Different identifiers, similar entity (cross-UEI)",
          "",
          "| condition | groups | UEI pairs |", "|---|---:|---:|",
          f"| identical normalized name, different UEIs | {len(same_name_diff_uei):,} | {same_name_pairs:,} |",
          f"| near-duplicate names (token_sort_ratio >= {NEAR_DUP_THRESHOLD}), no shared UEI | n/a | {len(near):,} |",
          f"| same normalized street address + ZIP5, different UEIs | {len(shared_addr):,} | {shared_addr_pairs:,} |",
          "",
          "These are not resolved here. Some are the same business re-registered, some are distinct "
          "franchisees or sibling entities, some are unrelated firms in a shared building.",
          "",
          "## Corporate hierarchy",
          "",
          "| condition | value |", "|---|---:|",
          f"| UEIs reporting a parent UEI different from their own | {len(child_ueis):,} ({pct(len(child_ueis), U)}) |",
          f"| child-parent pairs where the parent is also in this record set | {len(parent_in_set):,} |",
          f"| ...where the child's reported parent name does not match the parent's own legal name | {parent_name_mismatch:,} |",
          f"| parents with two or more child UEIs in the set (sibling groups) | {len(sib_groups):,} |",
          "",
          "## Missing and partial fields",
          "",
          "| field | blank records | share |", "|---|---:|---:|"]
    L += [f"| {f} | {sum(1 for r in rows if not r[f]):,} | {pct(sum(1 for r in rows if not r[f]), n)} |" for f in fields]
    L += [f"| ZIP is 5-digit only (no +4) | {zip5_only:,} | {pct(zip5_only, n)} |",
          "",
          f"Primary identifier: {sum(1 for r in rows if not r['recipient_uei']):,} records have a blank "
          f"`recipient_uei`. The {sum(1 for r in rows if not r['recipient_parent_uei']):,} blank "
          "`recipient_parent_uei` values are natural data and are kept as published.",
          "",
          f"UEIs flagged as sole proprietorships: {len(sole):,}. Their recipient names may be personal names "
          "of practitioners, as published by USAspending.",
          "",
          "## Examples (real, shown for orientation only)",
          ""]
    # Examples skip sole proprietorships so personal names are not repeated in the report.
    for u in sorted(name_var_norm - sole)[:5]:
        L.append(f"- UEI `{u}`: " + " / ".join(sorted(distinct(by_uei[u], "recipient_name_raw"))[:4]))
    L.append("")
    cred = re.compile(r"\b(MD|DDS|DMD|DO|OD|DPM|PHD|PSYD|NP|RN|PT|LCSW|MFT|DC)$")
    near_ex = [t for t in near if not ((name_to_ueis[t[0]] | name_to_ueis[t[1]]) & sole)
               and not cred.search(t[0]) and not cred.search(t[1])]
    for a, b, s in sorted(near_ex, key=lambda t: -t[2])[:5]:
        L.append(f"- near-duplicate across UEIs ({s}): `{a}` vs `{b}`")
    L += ["",
          "## Implication for the defect taxonomy",
          "",
          "Rows in `spec/defect_taxonomy.md` cite these sections in the column "
          "\"present naturally in real data?\". A condition with a non-trivial count above is present "
          "naturally. Whether it must also be injected is left to the repo owner (`[FILL]`).",
          ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
