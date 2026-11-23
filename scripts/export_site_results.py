#!/usr/bin/env python3
"""Turn the analysis tables into the small JSON file the exhibit site reads.

Usage (from the repository root, after scripts/analyze.py has run):
    python scripts/export_site_results.py --mode main-sdxlfast --out site

Reads  results/<mode>/contrasts.csv and results/<mode>/manifest.json
Writes site/data/results.json

Only numbers that analyze.py produced are copied; nothing is computed or rounded here beyond JSON.
Rows are split into "rows" (main tests, including any main test that failed the labeling agreement
check, which is shown as an estimate with no p-value) and "exploratory" (estimates only).
Estimates are proportions (0.05 = 5 percentage points); the page multiplies by 100.
"""
import argparse
import json
import math
from pathlib import Path

import pandas as pd

NAMES = {
    "formal_attire": "Formal attire (blazer or button-up)",
    "smile_teeth": "Smile with teeth showing",
    "political_symbol": "Political symbol (flag, sign, button)",
    "scene_city_street": "Setting: city street or sidewalk",
    "scene_residential": "Setting: residential street or home",
    "scene_shop_cafe_market": "Setting: shop, cafe or market",
    "scene_plaza_park": "Setting: plaza, park or green space",
    "scene_event_meeting": "Setting: event or meeting space",
    "scene_wall_or_facade": "Setting: wall or building front",
    "scene_leisure_or_sports": "Setting: leisure or sports venue",
    "glasses": "Glasses",
    "jewelry_or_watch": "Jewelry or watch",
    "arms_crossed": "Arms crossed",
    "emblem_or_text": "Emblem, badge or text on clothing",
    "held_object_any": "Holding an object",
    "bare_torso": "Bare torso",
    "visible_distortion": "Visible distortion",
    "not_assessable": "Not assessable (illustration or no clear person)",
}


def num(x):
    """JSON cannot hold NaN: return None for missing values."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def mark(row, prefix):
    rd, lo, hi = num(row.get(f"{prefix}_rd")), num(row.get(f"{prefix}_lo")), num(row.get(f"{prefix}_hi"))
    if rd is None or lo is None or hi is None:
        return None
    return {"rd": rd, "lo": lo, "hi": hi}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, help="run tag, e.g. main-sdxlfast")
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="site")
    args = ap.parse_args()

    res = Path(args.results) / args.mode
    contrasts = pd.read_csv(res / "contrasts.csv")
    manifest = json.loads((res / "manifest.json").read_text())

    main_rows, exploratory = [], []
    for _, r in contrasts.iterrows():
        dr = mark(r, "DR")
        if dr is None:                      # nothing estimable for this feature (for example no variation)
            continue
        dr["p_holm"] = num(r.get("DR_p_holm"))
        family = r["family"]
        entry = {"reading": r["reading"], "name": NAMES.get(r["reading"], r["reading"]), "dr": dr, "ctrl": mark(r, "CTRL")}
        if family == "primary":
            entry["status"] = "main test"
            main_rows.append(entry)
        elif family == "failed_gate":
            entry["status"] = "main test, but the automated labels did not agree well enough with the manual ones: estimate only"
            main_rows.append(entry)
        else:
            entry["status"] = "exploratory: estimate only"
            exploratory.append(entry)

    out = {
        "run": manifest.get("mode"), "codebook_version": manifest.get("codebook_version"),
        "n_images": manifest.get("n_images"), "n_labeled": manifest.get("n_labeled"),
        "n_seeds": manifest.get("n_seeds_used"), "controls": manifest.get("controls"),
        "rows": main_rows, "exploratory": exploratory,
    }
    path = Path(args.out) / "data" / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}: {len(main_rows)} main rows, {len(exploratory)} exploratory rows")


if __name__ == "__main__":
    main()
