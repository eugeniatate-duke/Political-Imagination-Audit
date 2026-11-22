#!/usr/bin/env python3
"""Paired analysis of the Political Imagination Audit.

    python scripts/analyze.py --mode main-sdxl                      # after labeling
    python scripts/analyze.py --mode main --labels-file labels_vlm.jsonl

What it measures
----------------
Each image has a label (Democrat, Republican, two non-political controls, or none), a gender and a
group stated in the prompt, and a seed. Images that share a seed, group and gender form a BLOCK: the
only difference inside a block is the label, so differences are paired. Blocks that share a seed are
not independent (same starting noise), so the SEED is the unit of resampling (15 seeds = 15 clusters).

For every binary reading in scripts/codebook.py (e.g. formal_attire = yes) and each pair of labels:
    risk difference RD = mean over seeds of (mean over blocks of  y_A - y_B)
    95% interval: seed-cluster bootstrap (resample seeds with replacement)
    p-value: exact sign-flip permutation over seeds (valid under "A and B are interchangeable")
Contrasts:
    DR       Democrat - Republican                                   (the question)
    CTRL     control 1 - control 2 (non-political pair)              (the baseline for "any label swap")
    EXCESS   |RD_DR| - |RD_CTRL|, bootstrap interval only            (is the party swap larger than the baseline?)
    vs none  each label minus the no-label image                     (descriptive)
Only the four PRIMARY_READINGS get p-values for DR, with Holm correction across the four. All other
readings are exploratory: estimates and intervals, no significance claims. With 15 seeds only large
effects are detectable (see docs/PREREGISTRATION.md and scripts/power_sim.py); intervals will be wide.

Calibration (tests/test_analyze.py, synthetic null with seed effects, 15 seeds): the permutation test
rejected at 3% for a nominal 5% (conservative, as exact tests on few clusters are), but the nominal 95%
percentile-bootstrap interval contained the true value of 0 only about 91% of the time. With 15 seed
clusters the bootstrap intervals are therefore somewhat too narrow; report them as approximate.

Images with a blank (safety checker) or no label are excluded and counted in quality.csv. An outcome of
"unclear" (or an image coded assessable = no) is missing for that reading; a block contributes to a
contrast only if both images are defined. Missingness counts are written next to every estimate.

Outputs: results/<mode>/*.csv and manifest.json.  Needs only numpy and pandas.
"""
import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import codebook as cb

N_BOOT = 5000
RNG_SEED = 20261122


# ----------------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------------
def load_frame(out_dir, labels_file, model):
    """One row per generated image, with binary readings as 1 / 0 / NaN columns."""
    recs = pd.DataFrame([json.loads(l) for l in (out_dir / "records.jsonl").read_text().splitlines() if l.strip()])
    labels = {}
    for line in (out_dir / labels_file).read_text().splitlines():
        r = json.loads(line)
        if r.get("error") or not r.get("fields"):
            continue
        if model and r["model"] != model:
            continue
        labels[r["image_id"]] = r["fields"]
    df = recs.merge(pd.DataFrame.from_dict(labels, orient="index").rename_axis("image_id").reset_index(),
                    on="image_id", how="left")
    df["blank"] = df["exclusion_code"].notna()
    df["labeled"] = df["assessable"].notna()
    for name, (field, positive) in cb.BINARY_READINGS.items():
        col = df[field] if field in df else pd.Series(np.nan, index=df.index)
        y = (col == positive).astype(float)
        undefined = col.isna() | (col == "unclear")
        if name != "not_assessable":
            undefined |= (df["assessable"] == "no")
        y[undefined] = np.nan
        df[name] = y
    return df


# ----------------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------------
def seed_means(df, a, b, reading):
    """Per-seed mean of the paired difference y_a - y_b over blocks; also counts. NaN if no valid block."""
    keys = ["seed", "group", "gender"]
    w = df[df.label_key.isin([a, b])].pivot_table(index=keys, columns="label_key", values=reading, aggfunc="first",
                                                   dropna=False)
    if a not in w or b not in w:
        return pd.Series(dtype=float), 0, 0
    n_blocks = len(w)
    w = w.dropna(subset=[a, b])
    d = (w[a] - w[b]).groupby(level="seed").mean()
    return d, len(w), n_blocks


def boot_idx(n, rng, B=N_BOOT):
    return rng.integers(0, n, size=(B, n))


def boot_ci(per_seed, idx):
    est = np.nanmean(per_seed[idx], axis=1)
    return np.nanpercentile(est, [2.5, 97.5])


def signflip_p(x, rng, max_exact=16, n_mc=100_000):
    """Two-sided sign-flip permutation p for mean(x) = 0 over seed-level values (NaNs dropped)."""
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0 or np.all(x == 0):
        return 1.0
    obs = abs(x.mean())
    if n <= max_exact:
        signs = np.array(list(itertools.product([-1, 1], repeat=n)), dtype=float)
    else:
        signs = rng.choice([-1.0, 1.0], size=(n_mc, n))
    perm = np.abs((signs * x).mean(axis=1))
    return float((perm >= obs - 1e-12).mean())


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (dict name -> p)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def contrast(df, a, b, reading, seeds, idx, rng, test=False):
    """RD with seed-cluster bootstrap interval (and optional permutation p) for label a minus label b."""
    d, n_valid, n_blocks = seed_means(df, a, b, reading)
    per_seed = d.reindex(seeds).to_numpy(dtype=float)
    if np.all(np.isnan(per_seed)):
        return dict(rd=np.nan, lo=np.nan, hi=np.nan, p=np.nan, n_blocks_valid=0, n_blocks=n_blocks, per_seed=per_seed)
    rd = float(np.nanmean(per_seed))
    lo, hi = boot_ci(per_seed, idx)
    p = signflip_p(per_seed, rng) if test else np.nan
    return dict(rd=rd, lo=float(lo), hi=float(hi), p=p, n_blocks_valid=n_valid, n_blocks=n_blocks, per_seed=per_seed)


# ----------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------
def build_tables(df, controls, rng):
    labeled = df[df.labeled & ~df.blank]
    seeds = np.array(sorted(labeled.seed.unique()))
    idx = boot_idx(len(seeds), rng)
    c1, c2 = controls
    rows, primary_p = [], {}
    for reading in cb.BINARY_READINGS:
        is_primary = reading in cb.PRIMARY_READINGS
        dr = contrast(labeled, "dem", "rep", reading, seeds, idx, rng, test=is_primary)
        ct = contrast(labeled, c1, c2, reading, seeds, idx, rng)
        if not (np.isnan(dr["rd"]) or np.isnan(ct["rd"])):
            ex_obs = abs(dr["rd"]) - abs(ct["rd"])
            ex_boot = np.abs(np.nanmean(dr["per_seed"][idx], axis=1)) - np.abs(np.nanmean(ct["per_seed"][idx], axis=1))
            ex_lo, ex_hi = np.nanpercentile(ex_boot, [2.5, 97.5])
        else:
            ex_obs = ex_lo = ex_hi = np.nan
        if is_primary:
            primary_p[reading] = dr["p"]
        rows.append(dict(
            reading=reading, family="primary" if is_primary else "exploratory",
            DR_rd=dr["rd"], DR_lo=dr["lo"], DR_hi=dr["hi"], DR_p=dr["p"],
            DR_blocks_used=dr["n_blocks_valid"], DR_blocks_total=dr["n_blocks"],
            CTRL_rd=ct["rd"], CTRL_lo=ct["lo"], CTRL_hi=ct["hi"],
            CTRL_blocks_used=ct["n_blocks_valid"],
            EXCESS=ex_obs, EXCESS_lo=ex_lo, EXCESS_hi=ex_hi,
        ))
    contrasts = pd.DataFrame(rows)
    adj = holm({k: v for k, v in primary_p.items() if not np.isnan(v)})
    contrasts["DR_p_holm"] = contrasts.reading.map(adj)

    # each label versus no label (descriptive)
    vs_none = []
    for reading in cb.BINARY_READINGS:
        for lab in ["dem", "rep", c1, c2]:
            r = contrast(labeled, lab, "none", reading, seeds, idx, rng)
            vs_none.append(dict(reading=reading, label=lab, rd_vs_none=r["rd"], lo=r["lo"], hi=r["hi"],
                                blocks_used=r["n_blocks_valid"]))
    # DR by subgroup (descriptive: bootstrap intervals only)
    subgroup = []
    for dim in ("group", "gender"):
        for val, part in labeled.groupby(dim):
            for reading in cb.PRIMARY_READINGS:
                r = contrast(part, "dem", "rep", reading, seeds, idx, rng)
                subgroup.append(dict(dimension=dim, value=val, reading=reading, DR_rd=r["rd"], lo=r["lo"],
                                     hi=r["hi"], blocks_used=r["n_blocks_valid"]))
    # robustness: drop blocks where either image shows visible distortion
    rob = []
    distorted = labeled[labeled.visible_distortion == 1][["seed", "group", "gender"]].drop_duplicates()
    if len(distorted):
        key = labeled.set_index(["seed", "group", "gender"]).index
        clean = labeled[~key.isin(distorted.set_index(["seed", "group", "gender"]).index)]
    else:
        clean = labeled
    for reading in cb.PRIMARY_READINGS:
        r = contrast(clean, "dem", "rep", reading, seeds, idx, rng, test=True)
        rob.append(dict(reading=reading, DR_rd=r["rd"], lo=r["lo"], hi=r["hi"], p=r["p"],
                        blocks_used=r["n_blocks_valid"], blocks_dropped_for_distortion=len(distorted)))
    # rates with Wilson intervals, per label (and per label x group, label x gender)
    rates = []
    for reading in cb.BINARY_READINGS:
        for dims in (["label_key"], ["label_key", "group"], ["label_key", "gender"]):
            for keys, part in labeled.groupby(dims):
                y = part[reading].dropna()
                lo, hi = wilson(int(y.sum()), len(y))
                keys = keys if isinstance(keys, tuple) else (keys,)
                rows_ = dict(reading=reading, by="+".join(dims), cell=" / ".join(map(str, keys)),
                             n_defined=len(y), n_total=len(part), rate=float(y.mean()) if len(y) else np.nan,
                             lo=lo, hi=hi)
                rates.append(rows_)
    # quality: blanks, not assessable, distortion, per label x group x gender
    quality = df.groupby(["label_key", "group", "gender"]).agg(
        n=("image_id", "size"), blank=("blank", "sum"),
        not_assessable=("not_assessable", "sum"), visible_distortion=("visible_distortion", "sum"),
        bare_torso=("bare_torso", "sum")).reset_index()
    return contrasts, pd.DataFrame(vs_none), pd.DataFrame(subgroup), pd.DataFrame(rob), pd.DataFrame(rates), quality, seeds


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", default="main", help="output folder tag, e.g. main or main-sdxl")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--labels-file", default="labels_vlm.jsonl")
    ap.add_argument("--model", default=None, help="labeler model name to use (default: any)")
    ap.add_argument("--controls", default=None, help="two control label keys; default from the template")
    ap.add_argument("--results", default="results")
    args = ap.parse_args()

    out_dir = Path(args.out) / args.mode
    df = load_frame(out_dir, args.labels_file, args.model)
    templates = sorted(df.template.unique())
    if args.controls:
        controls = args.controls.split(",")
    else:
        controls = ["rotary", "assoc"] if all(t.startswith("N") for t in templates) else ["rotary", "bowling"]
    assert len(controls) == 2, "need exactly two control labels"
    if not df.labeled.any():
        raise SystemExit("no labeled images found; run scripts/label_vlm.py first")

    rng = np.random.default_rng(RNG_SEED)
    contrasts, vs_none, subgroup, rob, rates, quality, seeds = build_tables(df, controls, rng)

    res = Path(args.results) / args.mode
    res.mkdir(parents=True, exist_ok=True)
    for name, t in [("contrasts", contrasts), ("vs_none", vs_none), ("subgroup_DR", subgroup),
                    ("robustness_no_distortion", rob), ("rates", rates), ("quality", quality)]:
        t.to_csv(res / f"{name}.csv", index=False, float_format="%.4f")
    manifest = dict(
        created_utc=datetime.now(timezone.utc).isoformat(), mode=args.mode, templates=templates,
        controls=controls, n_images=int(len(df)), n_blank=int(df.blank.sum()), n_labeled=int(df.labeled.sum()),
        n_seeds_used=int(len(seeds)), seeds=[int(s) for s in seeds], codebook_version=cb.CODEBOOK_VERSION,
        n_boot=N_BOOT, rng_seed=RNG_SEED, labeler_models=sorted(
            {json.loads(l)["model"] for l in (out_dir / args.labels_file).read_text().splitlines() if l.strip()}),
    )
    (res / "manifest.json").write_text(json.dumps(manifest, indent=2))

    show = contrasts[["reading", "family", "DR_rd", "DR_lo", "DR_hi", "DR_p_holm", "CTRL_rd", "EXCESS", "EXCESS_lo", "EXCESS_hi"]]
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:.3f}".format):
        print(show.to_string(index=False))
    print(f"\n{len(seeds)} seeds, {manifest['n_labeled']} labeled images. Tables in {res}/")
    print("Reminder: intervals are wide with this many seeds; exploratory rows have no significance claims.")


if __name__ == "__main__":
    main()
