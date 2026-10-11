"""Score a system's predictions against one track and split of the answer key.

Run: python -I scripts/score.py --track b --split dev --pred path/to/predictions [--json]

Tracks (synthetic/README.md): b = no-shared-identifier, the realistic configuration and the headline;
a = shared-identifier, which tests escalation behaviour when an identifier exists. The key folder is
synthetic/track_<track>/<split>; --key overrides it.

Predictions folder:
  <domain>/clusters.csv   (domain = customer or vendor) columns: record_id, cluster
                          Records with the same `cluster` value are predicted to be one entity. Records not
                          listed are singletons.
  decisions.csv           columns: domain, item_type, item_id, outcome_label, target_code,
                          evidence_record_ids, evidence_fields, evidence_rule
                          - pair:    item_id "<record_id>|<record_id>" (sorted), domain customer/vendor
                          - record:  item_id a record_id
                          - cluster: item_id any record_id of the entity the decision is about
                          - mapping: domain coa, item_id "<entity>::<source_code>", or
                                     "AddOnA::cash_basis::<target_code>" for a target the cash-basis chart cannot feed;
                                     outcome_label is the mapping type; target_code ';'-joined for splits
                          `;` separates multiple ids, fields or targets.

Ground truth (spec/corpus_spec.md section 3, docs/injection_decisions.md):
  - Two records are the same entity when they share a cluster in answer_key/<domain>/entity_clusters.csv.
  - Pairs marked "unknown" in record_pairs.csv are excluded from pairwise precision and recall; their count is
    reported separately, with how many of them the system merged.
  - A pair item with no explicit decision takes the decision implied by the predicted clusters
    (same cluster: AUTO_RESOLVE_MATCH, otherwise AUTO_RESOLVE_NON_MATCH) when both records appear in a
    clusters file; otherwise it counts as not decided.
"""
import argparse, collections, csv, json, pathlib

AUTO = {"AUTO_RESOLVE_MATCH", "AUTO_RESOLVE_NON_MATCH", "MAP_DIRECT", "MAP_MANY_TO_ONE", "MAP_SPLIT_REQUIRED",
        "EXCLUDE_OR_RETIRED_ACCOUNT"}
ESCALATE = {"ESCALATE_AMBIGUOUS", "ESCALATE_POLICY_DECISION", "DO_NOT_MERGE_CONFLICTING_IDENTIFIER",
            "MAP_REQUIRES_ACCOUNTING_POLICY"}
LABELS = AUTO | ESCALATE
NO_TARGET = {"MAP_REQUIRES_ACCOUNTING_POLICY", "EXCLUDE_OR_RETIRED_ACCOUNT"}
DOMAINS = ["customer", "vendor"]


def read(p):
    p = pathlib.Path(p)
    return list(csv.DictReader(open(p, encoding="utf-8", newline=""))) if p.exists() else []


def ids(s):
    return [x for x in (s or "").split(";") if x]


def c2(n):
    return n * (n - 1) // 2


def pairwise(key, pred, domain):
    true_cl = {r["record_id"]: r["cluster_id"] for r in read(key / "answer_key" / domain / "entity_clusters.csv")}
    pred_rows = read(pred / domain / "clusters.csv")
    pred_cl = {r["record_id"]: r["cluster"] for r in pred_rows if r["record_id"] in true_cl}
    for rid in true_cl:  # unlisted records are singletons
        pred_cl.setdefault(rid, f"__single__{rid}")
    unknown = [(r["record_id_a"], r["record_id_b"]) for r in read(key / "answer_key" / domain / "record_pairs.csv")
               if r["same_entity"] == "unknown"]
    inter = collections.Counter((pred_cl[r], true_cl[r]) for r in true_cl)
    tp = sum(c2(n) for n in inter.values())
    true_pairs = sum(c2(n) for n in collections.Counter(true_cl.values()).values())
    pred_pairs = sum(c2(n) for n in collections.Counter(pred_cl.values()).values())
    unknown_merged = sum(1 for a, b in unknown if pred_cl[a] == pred_cl[b])
    pred_pairs -= unknown_merged  # unknown pairs are never same-cluster in the key, so tp is unaffected
    p = tp / pred_pairs if pred_pairs else 0.0
    r = tp / true_pairs if true_pairs else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f, "true_pairs": true_pairs, "predicted_pairs": pred_pairs,
            "true_positive_pairs": tp, "unknown_pairs_excluded": len(unknown), "unknown_pairs_merged": unknown_merged,
            "records_in_clusters_file": len(pred_rows)}, pred_cl if pred_rows else None, true_cl


def evidence_ok(p, item_type):
    rec, fields, rule = ids(p.get("evidence_record_ids")), ids(p.get("evidence_fields")), (p.get("evidence_rule") or "").strip()
    if item_type == "pair":
        return set(p["item_id"].split("|")) <= set(rec) and bool(fields) and bool(rule)
    if item_type == "record":
        return p["item_id"] in rec and bool(fields) and bool(rule)
    if item_type == "cluster":
        return len(set(rec)) >= 2 and bool(fields) and bool(rule)
    if item_type == "mapping":
        return bool(rule) and (p["outcome_label"] in NO_TARGET or bool(ids(p.get("target_code"))))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", choices=["a", "b"], required=True)
    ap.add_argument("--split", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent.parent / "synthetic"))
    ap.add_argument("--key", help="answer-key folder; overrides --root/--track/--split")
    ap.add_argument("--pred", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    key = pathlib.Path(a.key) if a.key else pathlib.Path(a.root) / f"track_{a.track}" / a.split
    pred = pathlib.Path(a.pred)
    if not (key / "answer_key").is_dir():
        ap.error(f"no answer key at {key}")

    out = {"key": str(key), "track": a.track, "split": a.split, "pairwise": {}}
    pred_clusters, true_clusters = {}, {}
    for d in DOMAINS:
        out["pairwise"][d], pred_clusters[d], true_clusters[d] = pairwise(key, pred, d)
    tot = {k: sum(out["pairwise"][d][k] for d in DOMAINS) for k in ["true_pairs", "predicted_pairs", "true_positive_pairs",
                                                                   "unknown_pairs_excluded", "unknown_pairs_merged"]}
    p = tot["true_positive_pairs"] / tot["predicted_pairs"] if tot["predicted_pairs"] else 0.0
    r = tot["true_positive_pairs"] / tot["true_pairs"] if tot["true_pairs"] else 0.0
    out["pairwise"]["all"] = dict(tot, precision=p, recall=r, f1=2 * p * r / (p + r) if p + r else 0.0)

    preds = read(pred / "decisions.csv")
    bad_labels = sorted({x["outcome_label"] for x in preds} - LABELS)
    explicit = {}
    cluster_pred = collections.defaultdict(list)
    for x in preds:
        if x["item_type"] == "cluster":
            cid = true_clusters.get(x["domain"], {}).get(x["item_id"])
            if cid:
                cluster_pred[(x["domain"], cid)].append(x)
        else:
            explicit.setdefault((x["domain"], x["item_type"], x["item_id"]), x)

    items = []  # (domain, item_type, item_id, key_label, key_target)
    for d in DOMAINS:
        for k in read(key / "answer_key" / d / "decisions.csv"):
            items.append((d, k["item_type"], k["item_id"], k["outcome_label"], None))
    coa = read(key / "answer_key" / "coa" / "coa_mappings.csv")
    for k in coa:
        items.append(("coa", "mapping", k["mapping_id"], k["mapping_type"], set(ids(k["target_code"]))))

    n = len(items)
    safe = unsafe = undecided = 0
    esc_key = esc_hit = 0
    map_correct = 0
    for d, t, iid, klabel, ktarget in items:
        target_ok = True
        if t == "cluster":
            ps = cluster_pred.get((d, iid), [])
            plabel = next((x["outcome_label"] for x in ps if x["outcome_label"] in ESCALATE), ps[0]["outcome_label"] if ps else None)
        else:
            x = explicit.get((d, t, iid))
            plabel = x["outcome_label"] if x else None
            if t == "mapping" and x:
                target_ok = klabel in NO_TARGET or set(ids(x.get("target_code"))) == ktarget
            if plabel is None and t == "pair" and pred_clusters.get(d) is not None:
                ra, rb = iid.split("|")
                pc = pred_clusters[d]
                plabel = "AUTO_RESOLVE_MATCH" if pc[ra] == pc[rb] else "AUTO_RESOLVE_NON_MATCH"
        if t == "mapping" and plabel == klabel and target_ok:
            map_correct += 1
        if plabel is None:
            undecided += 1
        elif plabel in AUTO:
            if plabel == klabel and target_ok and klabel not in ESCALATE:
                safe += 1
            else:
                unsafe += 1
        if klabel in ESCALATE:
            esc_key += 1
            esc_hit += plabel in ESCALATE

    ev_n = len(preds)
    ev_ok = sum(1 for x in preds if evidence_ok(x, x["item_type"]))
    out.update({
        "mapping_accuracy": map_correct / len(coa) if coa else 0.0, "mapping_items": len(coa),
        "decision_items": n, "undecided_items": undecided,
        "safe_automation_rate": safe / n if n else 0.0,
        "unsafe_automation_rate": unsafe / n if n else 0.0,
        "correct_escalation_rate": esc_hit / esc_key if esc_key else 0.0, "escalation_items": esc_key,
        "evidence_completeness": ev_ok / ev_n if ev_n else 0.0, "explicit_decisions": ev_n,
        "unknown_labels_in_predictions": bad_labels,
    })
    if a.json:
        print(json.dumps(out, indent=2))
        return
    print(f"Track {a.track} ({'no-shared-identifier' if a.track == 'b' else 'shared-identifier'}), key: {key}")
    for d in DOMAINS + ["all"]:
        x = out["pairwise"][d]
        print(f"  pairwise {d:8s}  P {x['precision']:.4f}  R {x['recall']:.4f}  F1 {x['f1']:.4f}  "
              f"(unknown pairs excluded: {x['unknown_pairs_excluded']:,}, merged by system: {x['unknown_pairs_merged']:,})")
    print(f"  mapping accuracy          {out['mapping_accuracy']:.4f}  ({len(coa)} mappings)")
    print(f"  safe automation rate      {out['safe_automation_rate']:.4f}  ({n:,} decision items, {undecided:,} undecided)")
    print(f"  unsafe automation rate    {out['unsafe_automation_rate']:.4f}")
    print(f"  correct escalation rate   {out['correct_escalation_rate']:.4f}  ({esc_key:,} escalation items)")
    print(f"  evidence completeness     {out['evidence_completeness']:.4f}  ({ev_n:,} explicit decisions)")
    if bad_labels:
        print(f"  WARNING: labels not in the taxonomy: {bad_labels}")


if __name__ == "__main__":
    main()
