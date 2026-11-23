#!/usr/bin/env python3
"""EXPLORATORY: apparent skin tone by label in the no-group arm (see scripts/make_skintone_set.py).

    python scripts/analyze_skintone.py --run outputs/main-sdxlfast --mode main-sdxlfast

Reads outputs/skintone/{manifest_PRIVATE.csv, skintone_labels.csv} (save the downloaded CSV under that name).
Uses the FIRST labeling of each image; the duplicate copies are used only to measure your own consistency
(test-retest agreement), which limits how far the results can be trusted.

Outputs (results/<mode>/):  skintone_rates.csv, skintone_contrasts.csv, skintone_retest.json
Estimates use the same paired design as analyze.py (seed = resampling unit, bootstrap interval). No p-values:
this is exploratory, one annotator, 15 seeds, coarse bins, and skin tone in a picture depends on lighting.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as an

SCORE = {"light": 0.0, "medium": 1.0, "dark": 2.0}


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--dir", default="outputs/skintone")
    ap.add_argument("--results", default="results")
    ap.add_argument("--controls", default="rotary,assoc", help="the two non-political label keys")
    args = ap.parse_args()

    d = Path(args.dir)
    man = pd.read_csv(d / "manifest_PRIVATE.csv", dtype=str)
    lab = pd.read_csv(d / "skintone_labels.csv", dtype=str).replace({"": np.nan})
    m = man.merge(lab, on="s_id")
    m["is_duplicate"] = m.is_duplicate.astype(int)
    recs = pd.DataFrame([json.loads(l) for l in (Path(args.run) / "records.jsonl").read_text().splitlines() if l.strip()])
    # first labeling per image = the non-duplicate copy
    first = m[m.is_duplicate == 0].merge(recs[["image_id", "seed", "group", "gender", "label_key"]], on="image_id")
    n_unlabeled = int(first.apparent_skin_tone.isna().sum())
    first["tone"] = first.apparent_skin_tone.where(first.apparent_skin_tone.isin(SCORE))   # unclear -> NaN
    first["tone_dark"] = (first.tone == "dark").astype(float).where(first.tone.notna())
    first["tone_light"] = (first.tone == "light").astype(float).where(first.tone.notna())
    first["tone_score"] = first.tone.map(SCORE)

    # test-retest on the duplicate pairs (both labeled)
    dup = m[m.is_duplicate == 1].merge(m[m.is_duplicate == 0][["image_id", "apparent_skin_tone"]], on="image_id",
                                       suffixes=("_dup", "_first"))
    both = dup.dropna(subset=["apparent_skin_tone_dup", "apparent_skin_tone_first"])
    retest = dict(n_pairs=int(len(both)), raw_agreement=float((both.apparent_skin_tone_dup == both.apparent_skin_tone_first).mean())
                  if len(both) else None,
                  kappa=cohen_kappa(both.apparent_skin_tone_dup, both.apparent_skin_tone_first) if len(both) else None,
                  n_images_unlabeled=n_unlabeled)

    rng = np.random.default_rng(an.RNG_SEED)
    seeds = np.array(sorted(first.seed.astype(int).unique()))
    first["seed"] = first.seed.astype(int)
    idx = an.boot_idx(len(seeds), rng)
    c1, c2 = args.controls.split(",")

    rates = []
    for lab_key, sub in first.groupby("label_key"):
        for col in ("tone_light", "tone_dark"):
            y = sub[col].dropna()
            lo, hi = an.wilson(int(y.sum()), len(y))
            rates.append(dict(label=lab_key, reading=col, n_defined=len(y), n_total=len(sub),
                              share=float(y.mean()) if len(y) else np.nan, lo=lo, hi=hi))
    rows = []
    for a, b in (("dem", "rep"), (c1, c2), ("dem", "none"), ("rep", "none"), (c1, "none"), (c2, "none")):
        for reading in ("tone_dark", "tone_light", "tone_score"):
            r = an.contrast(first, a, b, reading, seeds, idx, rng)
            rows.append(dict(contrast=f"{a} minus {b}", reading=reading, rd=r["rd"], lo=r["lo"], hi=r["hi"],
                             blocks_used=r["n_blocks_valid"], blocks_total=r["n_blocks"]))
    res = Path(args.results) / args.mode
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rates).to_csv(res / "skintone_rates.csv", index=False, float_format="%.4f")
    pd.DataFrame(rows).to_csv(res / "skintone_contrasts.csv", index=False, float_format="%.4f")
    (res / "skintone_retest.json").write_text(json.dumps(retest, indent=2))

    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print("Share of images by apparent skin tone, per label (undefined = unclear):")
        print(pd.DataFrame(rates).pivot(index="label", columns="reading", values="share").to_string())
        print("\nPaired contrasts (proportion or mean-score difference, 95% seed-bootstrap interval):")
        print(pd.DataFrame(rows).to_string(index=False))
    print("\nTest-retest on your duplicate labels:", retest)
    print("Exploratory, one annotator. 'tone_score' is 0 light, 1 medium, 2 dark.")


if __name__ == "__main__":
    main()
