#!/usr/bin/env python3
"""Integrity check for a finished generation run. Prints numbers only; shows no images.

    python scripts/check_run.py            # checks outputs/main
    python scripts/check_run.py --mode main --out outputs

It answers: did every planned image get generated exactly once, are all image files present,
and how many blanks (safety checker or other) are there per label, gender and group?
Blank rates that differ by label would bias the analysis, so they are reported up front.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="main")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()

    out_dir = Path(args.out) / args.mode
    rec_path = out_dir / "records.jsonl"
    records, bad_lines = {}, 0
    for line in rec_path.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        records[r["image_id"]] = r          # a repeated id would silently collapse here
    n_lines = sum(1 for _ in rec_path.read_text().splitlines())
    recs = list(records.values())

    print(f"records: {len(recs)} unique ids ({n_lines} lines, {bad_lines} unreadable)")
    missing_files = [r["image_id"] for r in recs if not (out_dir / r["file"]).exists()]
    print(f"missing image files: {len(missing_files)}")

    templates = Counter(r["template"] for r in recs)
    print(f"templates: {dict(templates)}")
    models = Counter((r["model_id"], r["model_snapshot"][:10], r["dtype"], r["device"]) for r in recs)
    print(f"model/dtype/device: {dict(models)}")

    seeds = Counter(r["seed"] for r in recs)
    per_seed = Counter(seeds.values())
    print(f"seeds: {len(seeds)} distinct; images per seed -> number of seeds: {dict(per_seed)}")

    blanks = [r for r in recs if r["exclusion_code"]]
    print(f"\nblank images: {len(blanks)} of {len(recs)} ({100 * len(blanks) / max(len(recs), 1):.1f}%)")
    print("exclusion codes:", dict(Counter(r["exclusion_code"] for r in blanks)))

    for key in ("label_key", "gender", "group"):
        tot, bl = Counter(r[key] for r in recs), Counter(r[key] for r in blanks)
        row = ", ".join(f"{k}: {bl[k]}/{tot[k]}" for k in sorted(tot))
        print(f"blanks by {key:9s} {row}")

    # Blanks per seed show whether a few seeds account for most of them.
    by_seed = defaultdict(int)
    for r in blanks:
        by_seed[r["seed"]] += 1
    if by_seed:
        print("blanks by seed:", dict(sorted(by_seed.items())))

    secs = [r["generation_seconds"] for r in recs]
    print(f"\ngeneration time: {sum(secs) / 3600:.2f} h total, {sum(secs) / len(secs):.1f} s/image mean")


if __name__ == "__main__":
    main()
