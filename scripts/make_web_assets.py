#!/usr/bin/env python3
"""Make web-sized thumbnails and one JSON data file for the exhibit site.

Why: the full-size PNGs (about 1 MB each) are far too big for the repository or a static site.
This script writes small JPEG thumbnails plus a single data file that lists EVERY record in the run,
including blank or excluded images (they get thumb = null and keep their exclusion code), so the
site can show the complete audit record and link each example back to it. The full-resolution
originals stay in outputs/ and are published separately (for example as a GitHub Release).

Usage (from the repository root):
    python scripts/make_web_assets.py --run outputs/main-sdxlfast --out site

Writes:
    site/img/<image_id>.jpg    thumbnails (default 384 px wide, aspect ratio kept, no metadata)
    site/data/images.json      one entry per record: id, thumb, seed, label_key, group, gender, template,
                               prompt, engine, exclusion_code, and the automated labels if present

Safe to re-run: existing thumbnails are skipped unless --force is given.
The images are synthetic (AI-generated); they are not photographs of real people.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image


def read_jsonl(path):
    """Read a JSON-lines file, skipping a half-written last line left by a crash."""
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="run folder, e.g. outputs/main-sdxlfast")
    ap.add_argument("--out", default="site", help="site folder to write into (default: site)")
    ap.add_argument("--thumb-width", type=int, default=384)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--labels-file", default="labels_vlm.jsonl", help="labels file inside the run folder")
    ap.add_argument("--force", action="store_true", help="rebuild thumbnails that already exist")
    args = ap.parse_args()

    run, out = Path(args.run), Path(args.out)
    records = {}
    for r in read_jsonl(run / "records.jsonl"):
        records[r["image_id"]] = r                      # the last line for an id wins
    if not records:
        sys.exit(f"no records found in {run / 'records.jsonl'}")

    labels = {}
    for r in read_jsonl(run / args.labels_file):
        if r.get("fields"):
            labels[r["image_id"]] = r["fields"]         # the last line for an id wins

    (out / "img").mkdir(parents=True, exist_ok=True)
    (out / "data").mkdir(parents=True, exist_ok=True)

    entries, made, skipped, missing, total_bytes = [], 0, 0, 0, 0
    for image_id, r in sorted(records.items()):
        thumb = None
        if not r.get("exclusion_code"):
            src = run / r["file"]
            dst = out / "img" / f"{image_id}.jpg"
            if not src.exists():
                missing += 1
            else:
                if args.force or not dst.exists():
                    with Image.open(src) as im:
                        im = im.convert("RGB")
                        h = round(im.height * args.thumb_width / im.width)
                        im = im.resize((args.thumb_width, h), Image.LANCZOS)
                        im.save(dst, "JPEG", quality=args.quality, optimize=True, progressive=True)
                    made += 1
                else:
                    skipped += 1
                thumb = f"img/{image_id}.jpg"
                total_bytes += dst.stat().st_size
        entries.append({
            "id": image_id, "thumb": thumb, "seed": r["seed"], "template": r["template"],
            "label_key": r["label_key"], "group": r["group"], "gender": r["gender"],
            "prompt": r["prompt"], "engine": r.get("engine"),
            "exclusion_code": r.get("exclusion_code"),
            "labels": labels.get(image_id),
        })

    (out / "data" / "images.json").write_text(json.dumps(entries, indent=1))
    print(f"{len(entries)} records written to {out / 'data' / 'images.json'}")
    print(f"thumbnails: {made} made, {skipped} already present, {missing} source images missing")
    print(f"excluded (no thumbnail): {sum(1 for e in entries if e['exclusion_code'])}")
    print(f"labels attached: {sum(1 for e in entries if e['labels'])}")
    print(f"thumbnail total: {total_bytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
