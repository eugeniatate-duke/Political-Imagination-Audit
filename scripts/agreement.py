#!/usr/bin/env python3
"""Agreement between your blind manual labels and the automated (VLM) labels, and the D5 gate.

    python scripts/agreement.py --mode main-sdxl
    (expects outputs/validation/manual_labels.csv and outputs/validation/manifest_PRIVATE.csv,
     and outputs/<mode>/labels_vlm.jsonl for the same 90 images)

For each binary reading in scripts/codebook.py it reports, on the images where BOTH annotators gave a
definite answer: raw agreement, manual prevalence, Cohen's kappa and Gwet's AC1 with bootstrap 95%
intervals (resampling images), and whether the reading passes the gate in docs/DEVIATIONS.md D5:

    pass = (kappa >= 0.6, or AC1 >= 0.8 when manual prevalence is under 10%)
           and at least 5 yes and 5 no among the manual labels

Readings that fail are reported as unreliable and are excluded from the primary family by analyze.py
(`--gate results/<mode>/agreement.json`); they are never hand-corrected. Why AC1 as well as kappa: kappa
collapses when a feature is rare even if the two annotators almost always agree.

Also written: agreement_multiclass.csv (Cohen's kappa for multi-valued fields, informational),
disagreements.csv (every image where the annotators differ, for your review AFTER the gate is computed),
and a count of images where one annotator said "unclear" and the other did not, because that changes who
is counted in the analysis.

Honest limits: 90 images give wide intervals; one human annotator (you) whose own perceptions shape the
reference; agreement shows the two annotators align, not that either is correct.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import codebook as cb

N_BOOT = 2000
RNG_SEED = 20261122


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = float((a == b).mean())
    pe = sum(float((a == k).mean()) * float((b == k).mean()) for k in np.union1d(a, b))
    return np.nan if pe >= 1 else (po - pe) / (1 - pe)


def gwet_ac1(a, b):
    """Gwet's AC1 for two raters and a binary (0/1) rating."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    pa = float((a == b).mean())
    pi = (a.mean() + b.mean()) / 2
    pe = 2 * pi * (1 - pi)
    return np.nan if pe >= 1 else (pa - pe) / (1 - pe)


def binary_reading(df, field, positive, name):
    """1 / 0 / NaN for one reading from a table with codebook field columns (same rule as analyze.py)."""
    col = df[field] if field in df else pd.Series(np.nan, index=df.index)
    y = (col == positive).astype(float)
    undefined = col.isna() | (col == "unclear")
    if name != "not_assessable":
        undefined |= (df["assessable"] == "no")
    y[undefined] = np.nan
    return y


def boot_ci(fn, a, b, rng):
    n = len(a)
    vals = []
    for _ in range(N_BOOT):
        i = rng.integers(0, n, n)
        vals.append(fn(a[i], b[i]))
    return np.nanpercentile(vals, [2.5, 97.5]) if not np.all(np.isnan(vals)) else (np.nan, np.nan)


def evaluate(manual, model):
    """Return (reading table, multiclass table, disagreement table, gate dict)."""
    rng = np.random.default_rng(RNG_SEED)
    rows, gate = [], {}
    for name, (field, positive) in cb.BINARY_READINGS.items():
        ym = binary_reading(manual, field, positive, name)
        yv = binary_reading(model, field, positive, name)
        both = ym.notna() & yv.notna()
        a, b = ym[both].to_numpy(), yv[both].to_numpy()
        n = len(a)
        n_yes, n_no = int((a == 1).sum()), int((a == 0).sum())
        prev = float(a.mean()) if n else np.nan
        kappa = cohen_kappa(a, b) if n else np.nan
        ac1 = gwet_ac1(a, b) if n else np.nan
        k_lo, k_hi = boot_ci(cohen_kappa, a, b, rng) if n else (np.nan, np.nan)
        c_lo, c_hi = boot_ci(gwet_ac1, a, b, rng) if n else (np.nan, np.nan)
        enough = n_yes >= 5 and n_no >= 5
        strong = (not np.isnan(kappa) and kappa >= 0.6) or (prev < 0.10 and not np.isnan(ac1) and ac1 >= 0.8)
        passed = bool(enough and strong)
        why = "ok" if passed else ("fewer than 5 yes or 5 no" if not enough else "agreement below threshold")
        gate[name] = passed
        rows.append(dict(
            reading=name, n_both_defined=n, n_manual_defined=int(ym.notna().sum()),
            n_model_defined=int(yv.notna().sum()),
            one_unclear_other_not=int((ym.notna() != yv.notna()).sum()),
            manual_yes=n_yes, manual_no=n_no, prevalence=prev,
            raw_agreement=float((a == b).mean()) if n else np.nan,
            kappa=kappa, kappa_lo=k_lo, kappa_hi=k_hi, ac1=ac1, ac1_lo=c_lo, ac1_hi=c_hi,
            gate_passed=passed, gate_note=why, primary=name in cb.PRIMARY_READINGS))
    multi = []
    for field, (vals, _d) in cb.FIELDS.items():
        if len(vals) <= 2 or field not in manual or field not in model:
            continue
        ok = manual[field].notna() & model[field].notna()
        a, b = manual.loc[ok, field].to_numpy(), model.loc[ok, field].to_numpy()
        multi.append(dict(field=field, n=len(a), raw_agreement=float((a == b).mean()) if len(a) else np.nan,
                          cohen_kappa=cohen_kappa(a, b) if len(a) else np.nan))
    dis = []
    for field in cb.FIELDS:
        if field in manual and field in model:
            d = manual.index[(manual[field] != model[field]) & manual[field].notna() & model[field].notna()]
            dis += [dict(image_id=i, field=field, manual=manual.at[i, field], model=model.at[i, field]) for i in d]
    return pd.DataFrame(rows), pd.DataFrame(multi), pd.DataFrame(dis), gate


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", default="main")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--validation", default=None, help="folder with manual_labels.csv and manifest_PRIVATE.csv")
    ap.add_argument("--labels-file", default="labels_vlm.jsonl")
    ap.add_argument("--model", default=None, help="labeler model name (default: any)")
    ap.add_argument("--results", default="results")
    args = ap.parse_args()

    val = Path(args.validation) if args.validation else Path(args.out) / "validation"
    manifest = pd.read_csv(val / "manifest_PRIVATE.csv")
    manual = pd.read_csv(val / "manual_labels.csv", dtype=str).merge(manifest, on="v_id").set_index("image_id")
    manual = manual.replace({"": np.nan})
    labels = {}
    for line in (Path(args.out) / args.mode / args.labels_file).read_text().splitlines():
        r = json.loads(line)
        if r.get("error") or not r.get("fields") or (args.model and r["model"] != args.model):
            continue
        labels[r["image_id"]] = r["fields"]
    model = pd.DataFrame.from_dict(labels, orient="index")
    common = manual.index.intersection(model.index)
    if len(common) == 0:
        raise SystemExit("no image appears in both the manual labels and the model labels")
    missing = len(manual) - len(common)
    if missing:
        print(f"warning: {missing} manually labeled images have no model label (blank or not yet labeled)")
    manual, model = manual.loc[common], model.loc[common]
    manual = manual.assign(formal_attire=manual.apply(cb.derive_formal_attire, axis=1)) \
        if "formal_attire" not in manual else manual

    table, multi, dis, gate = evaluate(manual, model)
    res = Path(args.results) / args.mode
    res.mkdir(parents=True, exist_ok=True)
    table.to_csv(res / "agreement.csv", index=False, float_format="%.3f")
    multi.to_csv(res / "agreement_multiclass.csv", index=False, float_format="%.3f")
    dis.to_csv(res / "disagreements.csv", index=False)
    (res / "agreement.json").write_text(json.dumps(gate, indent=2))

    show = table[["reading", "n_both_defined", "manual_yes", "manual_no", "raw_agreement", "kappa", "ac1",
                  "gate_passed", "gate_note"]]
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:.2f}".format):
        print(show.to_string(index=False))
    print(f"\n{len(common)} images compared. Tables in {res}/")
    failed_primary = [r for r in cb.PRIMARY_READINGS if not gate.get(r, False)]
    if failed_primary:
        print("PRIMARY readings that FAIL the gate (will be dropped from the primary family):", failed_primary)


if __name__ == "__main__":
    main()
