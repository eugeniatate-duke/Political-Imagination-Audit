#!/usr/bin/env python3
"""Write site/data/skintone.json from the skin-tone analysis tables (exploratory section of the site).

    python scripts/export_skintone_site.py --run "First pass (seeds 0-14)=main-sdxlfast" \
                                           --run "Replication (seeds 15-29)=replicate-sdxlfast"

Each --run is "<title shown on the site>=<mode folder under results/>". Reads, per run:
results/<mode>/skintone_rates.csv, skintone_contrasts.csv, skintone_by_gender.csv, skintone_retest.json.
Until this file exists, the site shows nothing for this section. Numbers are copied, never recomputed.
Shares are among images where a tone could be judged; 'medium' is 1 - light - dark.
"""
import argparse
import json
import math
from pathlib import Path

import pandas as pd

LABELS = {"dem": "a Democrat", "rep": "a Republican", "rotary": "a Rotary Club member",
          "assoc": "a neighborhood association member", "none": "no label"}


def num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True, help='"Title=mode" (repeat for several runs)')
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="site")
    args = ap.parse_args()

    runs = []
    for spec in args.run:
        title, mode = spec.rsplit("=", 1)
        d = Path(args.results) / mode
        rates = pd.read_csv(d / "skintone_rates.csv")
        shares = {}
        for key in LABELS:
            sub = rates[rates.label == key].set_index("reading")
            if sub.empty:
                continue
            light, dark = num(sub.at["tone_light", "share"]), num(sub.at["tone_dark", "share"])
            n_def, n_tot = int(sub.at["tone_light", "n_defined"]), int(sub.at["tone_light", "n_total"])
            shares[key] = dict(name=LABELS[key], light=light, dark=dark,
                               medium=None if light is None or dark is None else max(0.0, 1 - light - dark),
                               n_defined=n_def, n_total=n_tot)
        c = pd.read_csv(d / "skintone_contrasts.csv")
        contrasts = [dict(contrast=r.contrast, reading=r.reading, rd=num(r.rd), lo=num(r.lo), hi=num(r.hi),
                          blocks_used=int(r.blocks_used), blocks_total=int(r.blocks_total))
                     for r in c.itertuples() if r.contrast in ("dem minus rep", "rotary minus assoc")]
        g = pd.read_csv(d / "skintone_by_gender.csv")
        by_gender = [dict(gender=r.gender, reading=r.reading, rd=num(r.rd), lo=num(r.lo), hi=num(r.hi),
                          blocks_used=int(r.blocks_used), blocks_total=int(r.blocks_total)) for r in g.itertuples()]
        retest = json.loads((d / "skintone_retest.json").read_text())
        runs.append(dict(title=title, mode=mode, shares=shares, contrasts=contrasts, by_gender=by_gender, retest=retest))

    path = Path(args.out) / "data" / "skintone.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(runs=runs), indent=1))
    print(f"wrote {path} with {len(runs)} run(s)")


if __name__ == "__main__":
    main()
