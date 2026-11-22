#!/usr/bin/env python3
"""Label generated images with a local vision-language model served by Ollama.

The model sees ONLY the image and the codebook instructions (scripts/codebook.py). It never sees
the prompt, label, group, gender, seed or template, so it cannot read the answer off the prompt.

Setup (once):
    brew install ollama            # or install the Ollama app from ollama.com
    ollama serve                   # leave running in another terminal (the app does this for you)
    ollama pull qwen2.5vl:7b       # about 6 GB

Usage:
    python scripts/label_vlm.py --limit 20                    # speed and sanity trial
    python scripts/label_vlm.py --ids-file outputs/validation/validation_ids.txt   # the 90 images
    python scripts/label_vlm.py                               # all non-blank images (resumable)

Output: outputs/main/labels_vlm.jsonl, one line per image with the model name, the raw reply,
the validated fields and any fields that had to be reset to "unclear" (invalid_fields).
Automated labels are NOT ground truth: they are validated against manual labels (docs/CODEBOOK.md
section 4), and fields that fail the agreement gate are dropped from the analysis.
"""
import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import codebook as cb


def load_jsonl(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[rec["image_id"]] = rec          # the last line for an id wins
    return out


def ask_model(host, model, image_path, timeout=300):
    """One chat call with the image and the schema. Returns the reply text."""
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    payload = {
        "model": model,
        "stream": False,
        "format": cb.json_schema(),                    # constrained decoding to the codebook values
        "options": {"temperature": 0, "seed": 0},      # as deterministic as the server allows
        "messages": [{"role": "user", "content": cb.instructions(), "images": [b64]}],
    }
    req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["message"]["content"]


def validate(raw_text):
    """Parse the reply; reset anything outside the codebook to 'unclear' and record what was reset."""
    invalid, fields = [], {}
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        data = {}
        invalid.append("__unparseable__")
    for name, (vals, _d) in cb.FIELDS.items():
        v = data.get(name)
        if v in vals:
            fields[name] = v
        else:
            fields[name] = "unclear"
            invalid.append(name)
    if fields["assessable"] == "no":                   # enforce the codebook rule
        for name in cb.FIELDS:
            if name != "assessable":
                fields[name] = "unclear"
    fields["formal_attire"] = cb.derive_formal_attire(fields)
    return fields, invalid


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", default="main")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--model", default="qwen2.5vl:7b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=None, help="label only the next N images")
    ap.add_argument("--ids-file", default=None, help="text file of image_ids to label (one per line)")
    ap.add_argument("--labels-file", default="labels_vlm.jsonl")
    args = ap.parse_args()

    out_dir = Path(args.out) / args.mode
    records = load_jsonl(out_dir / "records.jsonl")
    labels_path = out_dir / args.labels_file
    done = {i for i, r in load_jsonl(labels_path).items()
            if not r.get("error") and r.get("model") == args.model}

    wanted = None
    if args.ids_file:
        wanted = [l.strip() for l in Path(args.ids_file).read_text().splitlines() if l.strip()]
        unknown = [i for i in wanted if i not in records]
        if unknown:
            raise SystemExit(f"{len(unknown)} ids in {args.ids_file} are not in records.jsonl, e.g. {unknown[:3]}")
    ids = wanted if wanted is not None else sorted(records)
    # Blank images (safety checker or all-black) are never labeled.
    todo = [i for i in ids if records[i]["exclusion_code"] is None and i not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f"{len(todo)} images to label with {args.model} ({len(done)} already done)")

    started, n_err, n_invalid = time.perf_counter(), 0, Counter()
    for k, image_id in enumerate(todo, 1):
        rec = records[image_id]
        t0 = time.perf_counter()
        row = {"image_id": image_id, "model": args.model, "codebook_version": cb.CODEBOOK_VERSION,
               "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        try:
            try:
                raw = ask_model(args.host, args.model, out_dir / rec["file"])
            except (urllib.error.URLError, TimeoutError):      # one retry for a transient failure
                time.sleep(2)
                raw = ask_model(args.host, args.model, out_dir / rec["file"])
            fields, invalid = validate(raw)
            row.update(fields=fields, invalid_fields=invalid, raw_response=raw, error=None)
            n_invalid.update(invalid)
        except Exception as exc:  # noqa: BLE001  (log and continue; the id is retried on the next run)
            row.update(fields=None, invalid_fields=[], raw_response=None, error=f"{type(exc).__name__}: {exc}")
            n_err += 1
        row["seconds"] = round(time.perf_counter() - t0, 2)
        with labels_path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
            fh.flush()
        eta = (len(todo) - k) * (time.perf_counter() - started) / k / 60
        print(f"[{k}/{len(todo)}] {image_id} {row['seconds']}s eta {eta:.0f} min"
              + (f"  ERROR {row['error']}" if row["error"] else ""), flush=True)
        if n_err >= 3 and n_err == k:
            raise SystemExit("first 3 calls failed. Is `ollama serve` running and is the model pulled?")

    print(f"\ndone. errors: {n_err}. fields reset to unclear because the reply was invalid: {dict(n_invalid)}")
    print(f"labels: {labels_path}")


if __name__ == "__main__":
    main()
