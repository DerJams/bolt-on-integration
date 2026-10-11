"""Fuzzy-match baseline for the Leipzig ER benchmarks (Abt-Buy, Amazon-Google, DBLP-ACM).

Method: lowercase + strip punctuation (rapidfuzz default_process), score every
left x right pair on one name/title field with fuzz.token_set_ratio
(rapidfuzz.process.cdist, all cores), keep the single best right record per
left record (top-1 blocking), then predict a match when that best score >= the
threshold. Sweep thresholds and score against the gold perfect mapping.

Usage:
    uv run --with rapidfuzz --with pandas python -I scripts/er_baseline.py [--root er-benchmarks]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process, utils

DATASETS = [
    # name, dir, left file, left field, right file, right field, gold file, gold left col, gold right col
    ("Abt-Buy", "abt-buy", "Abt.csv", "name", "Buy.csv", "name",
     "abt_buy_perfectMapping.csv", "idAbt", "idBuy"),
    ("Amazon-Google", "amazon-google", "Amazon.csv", "title", "GoogleProducts.csv", "name",
     "Amzon_GoogleProducts_perfectMapping.csv", "idAmazon", "idGoogleBase"),
    ("DBLP-ACM", "dblp-acm", "DBLP2.csv", "title", "ACM.csv", "title",
     "DBLP-ACM_perfectMapping.csv", "idDBLP", "idACM"),
]
THRESHOLDS = list(range(50, 100, 5))
COMMAND = "uv run --with rapidfuzz --with pandas python -I scripts/er_baseline.py"


def read_csv(path: Path) -> tuple[pd.DataFrame, str]:
    """Read a CSV as strings, trying UTF-8 first and falling back to latin-1."""
    raw = path.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
    return df, enc


def prf(pred: set, gold: set) -> tuple[int, float, float, float]:
    tp = len(pred & gold)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(gold) if gold else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return tp, p, r, f


def run_dataset(root: Path, spec) -> dict:
    name, d, lf, lfield, rf, rfield, gf, gl, gr = spec
    left, lenc = read_csv(root / d / lf)
    right, renc = read_csv(root / d / rf)
    gold_df, genc = read_csv(root / d / gf)
    gold = set(zip(gold_df[gl], gold_df[gr]))

    lids, rids = left["id"].tolist(), right["id"].tolist()
    lset, rset = set(lids), set(rids)
    gold_missing = sum(1 for a, b in gold if a not in lset or b not in rset)

    scores = process.cdist(
        left[lfield].tolist(), right[rfield].tolist(),
        scorer=fuzz.token_set_ratio, processor=utils.default_process,
        dtype=np.uint8, workers=-1,
    )
    best_j = scores.argmax(axis=1)
    best_s = scores[np.arange(len(lids)), best_j]
    # top-1 blocking ceiling: recall if every top-1 candidate were accepted
    cand_all = {(lids[i], rids[best_j[i]]) for i in range(len(lids))}
    ceiling = len(cand_all & gold) / len(gold)

    rows = []
    for t in THRESHOLDS:
        pred = {(lids[i], rids[best_j[i]]) for i in np.nonzero(best_s >= t)[0]}
        tp, p, r, f = prf(pred, gold)
        rows.append({"threshold": t, "predicted": len(pred), "tp": tp,
                     "precision": p, "recall": r, "f1": f})
    best = max(rows, key=lambda x: x["f1"])
    return {
        "name": name, "dir": d, "left": lf, "right": rf, "lfield": lfield, "rfield": rfield,
        "n_left": len(left), "n_right": len(right), "n_gold": len(gold),
        "gold_rows": len(gold_df), "gold_missing": gold_missing,
        "enc": f"{lf}={lenc}, {rf}={renc}, {gf}={genc}",
        "ceiling": ceiling, "rows": rows, "best": best,
    }


def to_markdown(results: list[dict]) -> str:
    today = dt.date.today().isoformat()
    out = [
        "# Entity-resolution fuzzy baseline results", "",
        f"Run date: {today}", "",
        f"Command (from repo root `C:\\Users\\James\\rollup-bench`): `{COMMAND}`", "",
        "Method: rapidfuzz `fuzz.token_set_ratio` on one name/title field with "
        "`utils.default_process` (lowercase, strip non-alphanumerics), full "
        "left x right score matrix via `process.cdist`, top-1 right record per left "
        "record as the block, predicted match when the top-1 score >= threshold. "
        "Precision, recall and F1 are computed against the gold perfect mapping. "
        "The top-1 recall ceiling is the recall at threshold 0, i.e. the share of "
        "gold pairs that top-1 blocking can find at all.", "",
        "## Best threshold per dataset", "",
        "| Dataset | Fields (left vs right) | Left | Right | Gold pairs | Best threshold | Precision | Recall | F1 | Top-1 recall ceiling |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        b = r["best"]
        out.append(
            f"| {r['name']} | {r['lfield']} vs {r['rfield']} | {r['n_left']} | {r['n_right']} | "
            f"{r['n_gold']} | {b['threshold']} | {b['precision']:.3f} | {b['recall']:.3f} | "
            f"{b['f1']:.3f} | {r['ceiling']:.3f} |")
    for r in results:
        out += ["", f"## {r['name']} sweep", "",
                f"Files: `{r['dir']}/{r['left']}` ({r['n_left']} records) vs "
                f"`{r['dir']}/{r['right']}` ({r['n_right']} records). "
                f"Decoded as: {r['enc']}. Gold pairs: {r['n_gold']} "
                f"(rows in file: {r['gold_rows']}, pairs referencing ids absent from the tables: {r['gold_missing']}).", "",
                "| Threshold | Predicted | TP | Precision | Recall | F1 |",
                "|---:|---:|---:|---:|---:|---:|"]
        for row in r["rows"]:
            out.append(f"| {row['threshold']} | {row['predicted']} | {row['tp']} | "
                       f"{row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent / "er-benchmarks"))
    args = ap.parse_args()
    root = Path(args.root)
    results = [run_dataset(root, spec) for spec in DATASETS]
    for r in results:
        b = r["best"]
        print(f"{r['name']}: n={r['n_left']}x{r['n_right']} gold={r['n_gold']} "
              f"best t={b['threshold']} P={b['precision']:.3f} R={b['recall']:.3f} F1={b['f1']:.3f}")
    (root / "baseline_results.md").write_text(to_markdown(results), encoding="utf-8")
    print(f"wrote {root / 'baseline_results.md'}")


if __name__ == "__main__":
    main()
