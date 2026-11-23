#!/usr/bin/env python3
"""EXPLORATORY: does the Democrat-vs-Republican contrast depend on the stated group or gender,
and does the party label shift the apparent age of the generated person?

    python scripts/explore_by_group.py --mode main-sdxlfast

Added after the main results were seen (see docs/DEVIATIONS.md). Nothing here is a main test, no p-values
are produced, and 15 seeds split into subgroups give very wide intervals. Read the intervals, not the
point estimates. Apparent age comes from the automated labeler only unless agreement_multiclass.csv shows
it was validated against the manual labels; it is an impression of how a synthetic person looks.

Outputs (results/<mode>/):
  explore_DR_by_group.csv     Democrat minus Republican, per stated group and per stated gender
  explore_group_gap.csv       how much the Democrat-minus-Republican difference in one stated group
                              differs from that in white (stated), with a seed-cluster bootstrap interval
  explore_age_by_label.csv    apparent-age shares per label, overall and in the no-group-stated arm
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as an
import codebook as cb

READINGS = ["formal_attire", "smile_teeth", "political_symbol", "glasses", "jewelry_or_watch"]
AGE = {"age_60_plus": "60_plus", "age_under_35": "under_35"}


def add_age_columns(df):
    """1 / 0 / NaN indicators for apparent age bands (NaN if not labeled, unclear or not assessable)."""
    col = df["apparent_age_band"] if "apparent_age_band" in df else pd.Series(np.nan, index=df.index)
    for name, band in AGE.items():
        y = (col == band).astype(float)
        y[col.isna() | (col == "unclear") | (df["assessable"] == "no")] = np.nan
        df[name] = y
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--results", default="results")
    ap.add_argument("--labels-file", default="labels_vlm.jsonl")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    df = add_age_columns(an.load_frame(Path(args.out) / args.mode, args.labels_file, args.model))
    labeled = df[df.labeled & ~df.blank]
    seeds = np.array(sorted(labeled.seed.unique()))
    rng = np.random.default_rng(an.RNG_SEED)
    idx = an.boot_idx(len(seeds), rng)
    readings = READINGS + list(AGE)

    # 1. Democrat minus Republican inside each stated group and each stated gender
    rows, per_group_seed = [], {}
    for dim in ("group", "gender"):
        for val, part in labeled.groupby(dim):
            for rd in readings:
                r = an.contrast(part, "dem", "rep", rd, seeds, idx, rng)
                rows.append(dict(dimension=dim, value=val, reading=rd, DR_rd=r["rd"], DR_lo=r["lo"],
                                 DR_hi=r["hi"], blocks_used=r["n_blocks_valid"], blocks_total=r["n_blocks"]))
                if dim == "group":
                    per_group_seed[(val, rd)] = r["per_seed"]
    res = Path(args.results) / args.mode
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(res / "explore_DR_by_group.csv", index=False, float_format="%.4f")

    # 2. gap between a stated group's Democrat-minus-Republican difference and white's
    gaps = []
    for rd in readings:
        base = per_group_seed.get(("white", rd))
        if base is None:
            continue
        for g in sorted({k[0] for k in per_group_seed if k[0] not in ("white", "none")}):
            d = per_group_seed[(g, rd)] - base
            if np.all(np.isnan(d)):
                continue
            est = np.nanmean(d[idx], axis=1)
            lo, hi = np.nanpercentile(est, [2.5, 97.5])
            gaps.append(dict(reading=rd, group=g, reference="white", gap=float(np.nanmean(d)), lo=lo, hi=hi))
    pd.DataFrame(gaps).to_csv(res / "explore_group_gap.csv", index=False, float_format="%.4f")

    # 3. apparent age by label (descriptive, with Wilson intervals)
    age_rows = []
    for scope, part in (("all", labeled), ("no_group_stated", labeled[labeled.group == "none"])):
        for lab, sub in part.groupby("label_key"):
            for name in AGE:
                y = sub[name].dropna()
                lo, hi = an.wilson(int(y.sum()), len(y))
                age_rows.append(dict(scope=scope, label=lab, reading=name, n_defined=len(y),
                                     share=float(y.mean()) if len(y) else np.nan, lo=lo, hi=hi))
    pd.DataFrame(age_rows).to_csv(res / "explore_age_by_label.csv", index=False, float_format="%.4f")

    with pd.option_context("display.width", 200, "display.max_rows", 200, "display.float_format", "{:.3f}".format):
        t = pd.DataFrame(rows)
        print("Democrat minus Republican by stated group (proportion difference, 95% seed-bootstrap interval)")
        print(t[t.dimension == "group"].pivot(index="reading", columns="value", values="DR_rd").to_string())
        print("\nIntervals that exclude zero (exploratory, expect some by chance):")
        sig = t[(t.DR_lo > 0) | (t.DR_hi < 0)][["dimension", "value", "reading", "DR_rd", "DR_lo", "DR_hi"]]
        print(sig.to_string(index=False) if len(sig) else "none")
        print("\nApparent age shares, no group stated:")
        a = pd.DataFrame(age_rows)
        print(a[a.scope == "no_group_stated"].pivot(index="label", columns="reading", values="share").to_string())
    print(f"\nTables in {res}/")


if __name__ == "__main__":
    main()
