#!/usr/bin/env python3
"""Sensitivity simulation for the paired Democrat-vs-Republican test in scripts/analyze.py.

    python scripts/power_sim.py                  # prints a table, writes results/power_sim.csv

Question: with S seeds (clusters) and B blocks per seed, how large must a true difference in the rate of a
yes/no feature be before the primary test usually detects it?

Model (ALL parameters are assumptions, not estimates from data):
  - each seed has a random effect u_s ~ N(0, sigma^2) on the logit of the feature rate (images that share
    a seed look alike, so blocks within a seed are correlated);
  - Democrat has rate p_s + RD/2 and Republican p_s - RD/2 in every block of seed s, where
    p_s = expit(logit(p0) + u_s) and RD is the true risk difference;
  - each block yields one yes/no outcome per label (independent given the seed);
  - test = exact sign-flip permutation over per-seed mean differences, as in analyze.py;
  - alpha = 0.05 for one test, and 0.0125 (Bonferroni for the 4 primary readings; Holm is slightly less strict).

Read the output as "which effect sizes are even detectable at this sample size", not as a forecast.
Blocks per seed: 10 = 5 group arms (4 stated groups + default) x 2 genders. Missing ("unclear") labels reduce this.
"""
import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd


def expit(x):
    return 1 / (1 + np.exp(-x))


def simulate(S, B, p0, sigma, rd, rng, sims=1000, chunk=250):
    """Return (power at 0.05, power at 0.0125) for one design cell."""
    signs = np.array(list(itertools.product([-1.0, 1.0], repeat=S)))        # 2^S x S
    hits05 = hits0125 = 0
    done = 0
    while done < sims:
        n = min(chunk, sims - done)
        u = rng.normal(0, sigma, size=(n, S))
        p = expit(np.log(p0 / (1 - p0)) + u)[:, :, None]                    # n x S x 1
        pa = np.clip(p + rd / 2, 0.001, 0.999)
        pb = np.clip(p - rd / 2, 0.001, 0.999)
        ya = rng.random((n, S, B)) < pa
        yb = rng.random((n, S, B)) < pb
        x = (ya.astype(float) - yb.astype(float)).mean(axis=2)             # n x S per-seed mean difference
        obs = np.abs(x.mean(axis=1))                                        # n
        perm = np.abs(signs @ x.T) / S                                      # 2^S x n
        pval = (perm >= obs[None, :] - 1e-12).mean(axis=0)
        hits05 += int((pval < 0.05).sum())
        hits0125 += int((pval < 0.0125).sum())
        done += n
    return hits05 / sims, hits0125 / sims


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--seeds", default="10,15", help="comma-separated numbers of seeds to try")
    ap.add_argument("--blocks", type=int, default=10, help="blocks per seed")
    ap.add_argument("--out", default="results/power_sim.csv")
    args = ap.parse_args()

    rng = np.random.default_rng(20261122)
    rows = []
    for S in [int(s) for s in args.seeds.split(",")]:
        for p0 in (0.2, 0.5):
            for sigma in (0.5, 1.0):
                for rd in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
                    a, b = simulate(S, args.blocks, p0, sigma, rd, rng, args.sims)
                    rows.append(dict(seeds=S, blocks_per_seed=args.blocks, base_rate=p0, seed_sd_logit=sigma,
                                     true_rd=rd, power_alpha_0_05=a, power_alpha_0_0125=b))
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, float_format="%.3f")
    with pd.option_context("display.width", 160, "display.float_format", "{:.2f}".format):
        print(df.to_string(index=False))
    print(f"\nwrote {args.out}. rd = 0 rows show the false-positive rate (expect at or below the alpha).")


if __name__ == "__main__":
    main()
