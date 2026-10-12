"""Adopt an independent chart-of-accounts mapping key and report how far it disagrees with the current one.

Run: python -I synthetic/review/compare_keys.py <independent.csv> [--root synthetic] [--dry-run]

The independent CSV has columns: addon, source_code, target_code, mapping_type, business_decision_required, rationale
(see review/inputs/labels.md). Each row becomes mapping id "<addon>::<source_code>" and goes to dev or holdout by
the mapping ids of the current key, so the split does not move.

Steps:
1. Validate: known add-on, label from the taxonomy, every target code in the platform chart, true/false decision
   flag, no duplicate ids, and the same set of mapping ids as the current key. Any failure stops the script with
   nothing written.
2. Report the per-row disagreement rate against the generated key (the archive once it exists) (a row disagrees when mapping type, target set or
   business_decision_required differs; target is ignored when both keys say MAP_REQUIRES_ACCOUNTING_POLICY or
   EXCLUDE_OR_RETIRED_ACCOUNT). Holdout is reported as counts only; row-level detail is written for dev only.
3. Unless --dry-run: archive each current key as coa_mappings_claude.csv next to it (first adoption only, so the
   archive always holds the generated key), write the independent key as coa_mappings.csv and coa decisions.csv in
   both tracks, save a copy of the input as review/independent_key.csv, and update synthetic/MANIFEST.json.

Re-running scripts/generate_synthetic.py restores the generated key; run this script again afterwards.
"""
import argparse, collections, csv, datetime, hashlib, io, json, pathlib, shutil, sys

LABELS = {"MAP_DIRECT", "MAP_MANY_TO_ONE", "MAP_SPLIT_REQUIRED", "MAP_REQUIRES_ACCOUNTING_POLICY",
          "EXCLUDE_OR_RETIRED_ACCOUNT"}
NO_TARGET = {"MAP_REQUIRES_ACCOUNTING_POLICY", "EXCLUDE_OR_RETIRED_ACCOUNT"}
TYPE_DEFECT = {"MAP_DIRECT": "COA01", "MAP_MANY_TO_ONE": "COA02", "MAP_SPLIT_REQUIRED": "COA03"}
ADDONS = {"addona": "AddOnA", "addon a": "AddOnA", "a": "AddOnA", "addonb": "AddOnB", "addon b": "AddOnB", "b": "AddOnB",
          "addonc": "AddOnC", "addon c": "AddOnC", "c": "AddOnC"}
TRACKS, SPLITS = ["track_a", "track_b"], ["dev", "holdout"]
HEADER = ["mapping_id", "entity", "source_code", "source_account_name", "source_present", "target_code",
          "mapping_type", "rationale", "business_decision_required", "defect_ids", "citation"]


def read(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def write_csv(path, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))


def targets(s):
    return frozenset(x.strip() for x in (s or "").split(";") if x.strip())


def flag(s):
    v = (s or "").strip().lower()
    return {"true": "true", "false": "false", "yes": "true", "no": "false", "1": "true", "0": "false"}.get(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("independent")
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    src = pathlib.Path(a.independent)

    current = {}
    split_of = {}
    for sp in SPLITS:
        kdir = root / "track_a" / sp / "answer_key" / "coa"
        base = kdir / "coa_mappings_claude.csv"  # always compare against the generated key
        for r in read(base if base.exists() else kdir / "coa_mappings.csv"):
            current[r["mapping_id"]] = r
            split_of[r["mapping_id"]] = sp
    platform = {r["gl_code"] for r in read(root / "track_a" / "charts" / "PlatformCo_chart.csv")}

    errors, indep = [], {}
    rows = read(src)
    need = {"addon", "source_code", "target_code", "mapping_type", "business_decision_required", "rationale"}
    if not rows or not need <= set(rows[0]):
        sys.exit(f"missing columns: {sorted(need - set(rows[0] if rows else []))}")
    for i, r in enumerate(rows, start=2):
        addon = ADDONS.get((r["addon"] or "").strip().lower())
        mid = f"{addon}::{(r['source_code'] or '').strip()}"
        mt = (r["mapping_type"] or "").strip()
        ts = targets(r["target_code"])
        bdr = flag(r["business_decision_required"])
        if not addon:
            errors.append(f"line {i}: unknown addon {r['addon']!r}")
        if mt not in LABELS:
            errors.append(f"line {i}: label {mt!r} is not a chart-of-accounts label")
        if bdr is None:
            errors.append(f"line {i}: business_decision_required {r['business_decision_required']!r} is not true/false")
        if ts - platform:
            errors.append(f"line {i}: target(s) not in the platform chart: {sorted(ts - platform)}")
        if mt not in NO_TARGET and not ts:
            errors.append(f"line {i}: {mt} needs a target_code")
        if mt == "MAP_SPLIT_REQUIRED" and len(ts) < 2:
            errors.append(f"line {i}: MAP_SPLIT_REQUIRED needs two or more targets")
        if mid in indep:
            errors.append(f"line {i}: duplicate mapping {mid}")
        indep[mid] = {"mt": mt, "ts": ts, "bdr": bdr, "rationale": (r["rationale"] or "").strip()}
    unknown = sorted(set(indep) - set(current))
    missing = sorted(set(current) - set(indep))
    if unknown:
        errors.append(f"{len(unknown)} rows match no mapping id in the current key, e.g. {unknown[:5]}")
    if missing:
        n_dev = sum(1 for m in missing if split_of[m] == "dev")
        errors.append(f"{len(missing)} mapping ids of the current key have no row ({n_dev} dev, {len(missing) - n_dev} holdout); "
                      f"dev examples: {[m for m in missing if split_of[m] == 'dev'][:5]}")
    if errors:
        print("Not adopted. Fix these first:")
        print("\n".join("  " + e for e in errors[:50]))
        sys.exit(1)

    # Disagreement against the current key.
    stats = collections.defaultdict(collections.Counter)
    dev_rows = []
    for mid, cur in current.items():
        new, sp = indep[mid], split_of[mid]
        ct, cts, cb = cur["mapping_type"], targets(cur["target_code"]), cur["business_decision_required"]
        d_type = new["mt"] != ct
        d_target = not (new["mt"] in NO_TARGET and ct in NO_TARGET) and new["ts"] != cts
        d_bdr = new["bdr"] != cb
        any_d = d_type or d_target or d_bdr
        for scope in (sp, f"{sp}/{cur['entity']}", "all"):
            stats[scope].update(rows=1, disagree=any_d, type=d_type, target=d_target, bdr=d_bdr)
        if sp == "dev" and any_d:
            dev_rows.append([mid, ct, cur["target_code"], cb, new["mt"], ";".join(sorted(new["ts"])), new["bdr"],
                             ";".join(k for k, v in (("type", d_type), ("target", d_target), ("decision_flag", d_bdr)) if v),
                             new["rationale"]])
    lines = ["| scope | rows | disagreeing rows | rate | type differs | target differs | decision flag differs |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for scope in sorted(stats, key=lambda s: (s != "all", s)):
        c = stats[scope]
        lines.append(f"| {scope} | {c['rows']} | {c['disagree']} | {c['disagree'] / c['rows']:.1%} | {c['type']} | "
                     f"{c['target']} | {c['bdr']} |")
    print("\n".join(lines))
    if a.dry_run:
        print("Dry run: nothing written.")
        return

    review = root / "review"
    write_csv(review / "disagreements_dev.csv",
              ["mapping_id", "current_type", "current_target", "current_decision_required", "independent_type",
               "independent_target", "independent_decision_required", "differs_in", "independent_rationale"],
              sorted(dev_rows))
    shutil.copyfile(src, review / "independent_key.csv")
    changed = [review / "disagreements_dev.csv", review / "independent_key.csv"]
    for track in TRACKS:
        for sp in SPLITS:
            kdir = root / track / sp / "answer_key" / "coa"
            archive = kdir / "coa_mappings_claude.csv"
            if not archive.exists():
                shutil.copyfile(kdir / "coa_mappings.csv", archive)
                changed.append(archive)
            cur_rows = {r["mapping_id"]: r for r in read(archive)}
            out, decs = [], []
            for mid in sorted(m for m in current if split_of[m] == sp):
                c, n = cur_rows[mid], indep[mid]
                if n["mt"] in TYPE_DEFECT:
                    dfx = TYPE_DEFECT[n["mt"]]
                elif c["mapping_type"] in NO_TARGET:
                    dfx = c["defect_ids"]  # COA05/07/08/09 tags describe the source account, not the mapping
                else:
                    dfx = "COA05" if mid.startswith("AddOnA::cash_basis::") else ""
                out.append([mid, c["entity"], c["source_code"], c["source_account_name"], c["source_present"],
                            ";".join(sorted(n["ts"])), n["mt"], n["rationale"], n["bdr"], dfx,
                            "independent review (synthetic/review/independent_key.csv)"])
                decs.append(["mapping", mid, n["mt"], dfx, n["rationale"]])
            write_csv(kdir / "coa_mappings.csv", HEADER, out)
            write_csv(kdir / "decisions.csv", ["item_type", "item_id", "outcome_label", "defect_ids", "rationale"], decs)
            changed += [kdir / "coa_mappings.csv", kdir / "decisions.csv"]
    report = review / "ADOPTION_REPORT.md"
    report.write_bytes(("# Independent mapping key adopted\n\n"
                        f"Adopted {datetime.date.today().isoformat()} from `{src.name}` by `synthetic/review/compare_keys.py`. "
                        "The generated key is archived as `coa_mappings_claude.csv` in each `answer_key/coa/` folder. "
                        "Holdout figures are counts only.\n\n" + "\n".join(lines) + "\n").encode("utf-8"))
    changed.append(report)

    # Refresh synthetic/MANIFEST.json for every file written here.
    mpath = root / "MANIFEST.json"
    if mpath.exists():
        man = json.loads(mpath.read_text(encoding="utf-8"))
        entries = {f["path"]: f for f in man["files"]}
        for f in changed + [root / "review" / "compare_keys.py"]:
            if not f.exists():
                continue
            b = f.read_bytes()
            rel = "synthetic/" + f.resolve().relative_to(root.resolve()).as_posix()  # manifest paths are repo-relative
            entries[rel] = {"path": rel, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
        man["files"] = [entries[k] for k in sorted(entries)]
        man["file_count"] = len(man["files"])
        man["coa_key"] = f"independent review, adopted {datetime.date.today().isoformat()}"
        mpath.write_bytes((json.dumps(man, indent=2) + "\n").encode("utf-8"))
    print(f"Adopted. {len(changed)} files written; generated key archived as coa_mappings_claude.csv.")


if __name__ == "__main__":
    main()
