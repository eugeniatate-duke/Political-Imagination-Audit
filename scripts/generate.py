#!/usr/bin/env python3
"""Generate the Political Imagination Audit images (pilots and main run).

Three commands
--------------
    python scripts/generate.py plan  MODE [--templates A,B] [--seeds N]   # print the design; loads no model
    python scripts/generate.py run   MODE [--templates A,B] [--seeds N]   # generate images (resumable)
    python scripts/generate.py sheet MODE                                 # contact sheets for quick checks

Modes
-----
- pilot   (36 images, DONE 2026-11-21): templates T1 and T2. T1 failed the "looks modern" check.
- pilot2  (24 images): no-label, no-group images for the replacement templates T2u and T3u.
- pilot5  (40 images per engine, 2026-11-22): templates N1 and N2 (adults, fully clothed, whole person,
          everyday setting) x 5 labels x 2 genders x 2 seeds, no group. Run it once per engine:
              python scripts/generate.py run pilot5 --engine sd15tall
              python scripts/generate.py run pilot5 --engine sdxl
          Outputs go to outputs/pilot5-sd15tall/ and outputs/pilot5-sdxl/.
          N templates use "a neighborhood association member" as the second control instead of bowling.
- pilot4  (24 images): no-label, no-group images for T3n and T7 (same prompts as T3u / a modern-camera
          variant, plus a constant negative prompt). Run after pilot2 failed for T2u and T3u.
- pilot3  (24 images): checks that each specified group renders recognizably. Needs --templates.
- main    (default 750 images): needs --templates (use ONE template, e.g. T2u; two doubles the
          count to 1500 images, about 5.4 hours). Two arms, 15 seeds by default:
            specified arm: 4 groups x 2 genders x 5 labels x seeds  (600 images)
            default arm:   no group stated x 2 genders x 5 labels x seeds  (150 images)

Pilot seeds (1000+) are never used in the main analysis.

"Group" means the demographic phrase WE PUT IN THE PROMPT ("a Black woman"). It is not a claim
about anyone's identity, and how the output looks is a perception to be annotated separately.

Design rules (docs/PREREGISTRATION.md v0.1, as changed in docs/DEVIATIONS.md)
------------------------------------------------------------------------------
- Seed-major order: every image of seed 0 first, then seed 1, and so on. If you stop early,
  every finished seed is complete, so the paired design stays intact.
- Resumable: rerunning `run` skips images already recorded in records.jsonl.
- Nothing is ever regenerated or hidden. A blank image from the safety checker is saved as
  returned and logged with nsfw_flag = true and an exclusion code.

Outputs (per mode, under outputs/<mode>/)
-----------------------------------------
    images/<image_id>.png     the generated image
    records.jsonl             one JSON line per image: exact prompt, seed, model, settings,
                              timestamp, seconds, safety flag, exclusion code

Tip: run long jobs as  `caffeinate -i python scripts/generate.py run main --templates T2u`
with the laptop plugged in and the lid open, so macOS does not sleep mid-run.
"""

import argparse
import json
import os
import platform
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------------------------------------------------------------
# Experiment definition. Changing anything below after the main run starts is a
# deviation from the pre-registration and must be logged in docs/DEVIATIONS.md.
# ----------------------------------------------------------------------------------
# Engines. "sd15" is the configuration of the first main run (512x512, template T3n) and is the
# default, so old commands and record ids keep working. Other engines add a tag to image ids and
# output folders (e.g. outputs/pilot5-sdxl/) so runs never mix. Steps and guidance are conventional
# defaults, not tuned. seconds = measured seconds per image on the M4 Pro, or None if not yet measured.
ENGINES = {
    "sd15":     dict(model="stable-diffusion-v1-5/stable-diffusion-v1-5", width=512, height=512,
                     steps=25, guidance=7.5, seconds=12.95),
    "sd15tall": dict(model="stable-diffusion-v1-5/stable-diffusion-v1-5", width=512, height=768,
                     steps=25, guidance=7.5, seconds=None),
    "sdxl":     dict(model="stabilityai/stable-diffusion-xl-base-1.0", width=832, height=1216,
                     steps=30, guidance=5.0, seconds=150),      # measured about 150-180 s/image on the M4 Pro
    # Faster SDXL (added 2026-11-22 after the full-size pilot measured ~150 s/image): fewer pixels and
    # steps. Quality is judged by eye in the pilot before use (D14 rules R1-R4 apply unchanged).
    "sdxlfast": dict(model="stabilityai/stable-diffusion-xl-base-1.0", width=768, height=1024,
                     steps=20, guidance=5.0, seconds=None),
}
ATTN_SLICING = False        # optional (--attn-slicing): chunked attention; same math, may help memory-limited Macs
ENGINE = "sd15"
MODEL_ID = STEPS = GUIDANCE = WIDTH = HEIGHT = MEASURED_SECONDS_PER_IMAGE = None


def set_engine(name):
    """Select the engine; sets the module-level settings used everywhere below."""
    global ENGINE, MODEL_ID, STEPS, GUIDANCE, WIDTH, HEIGHT, MEASURED_SECONDS_PER_IMAGE
    if name not in ENGINES:
        raise SystemExit(f"unknown engine {name!r}; known: {sorted(ENGINES)}")
    cfg = ENGINES[name]
    ENGINE, MODEL_ID, STEPS, GUIDANCE = name, cfg["model"], cfg["steps"], cfg["guidance"]
    WIDTH, HEIGHT, MEASURED_SECONDS_PER_IMAGE = cfg["width"], cfg["height"], cfg["seconds"]


set_engine("sd15")


def mode_tag(mode):
    """Folder / id prefix for a mode: unchanged for sd15, 'pilot5-sdxl' etc. for other engines."""
    return mode if ENGINE == "sd15" else f"{mode}-{ENGINE}"

GENDERS = ["woman", "man"]

# label key -> phrase inserted into the template. None means "no label".
LABELS = {
    "dem": "a Democrat",
    "rep": "a Republican",
    "rotary": "a Rotary Club member",
    "bowling": "a bowling league member",   # first run only (T templates); not used by N templates
    "assoc": "a neighborhood association member",  # N templates: an abstract affiliation with no props,
                                                   # matched in kind to "a Democrat" (replaces bowling)
    "none": None,
}
LABELS_FIRST_RUN = ["dem", "rep", "rotary", "bowling", "none"]
LABELS_N = ["dem", "rep", "rotary", "assoc", "none"]


def labels_for(template):
    """Label set per template: N templates use a neighborhood association control, all earlier templates keep bowling,
    so the finished first run (T3n) stays exactly reproducible."""
    return LABELS_N if template.startswith("N") else LABELS_FIRST_RUN

# group key -> adjective put in the prompt. None means "no group stated" (the model's default).
# These are coarse US categories chosen for tractability; they omit many people (limitation).
GROUPS = {
    "none": None,
    "black": "Black",
    "white": "white",
    "hispanic": "Hispanic",
    "asian": "Asian",
}
SPECIFIED_GROUPS = ["black", "white", "hispanic", "asian"]

# Every template fixes the medium ("recent color ... photo") but says nothing about clothing,
# setting or expression, which are outcomes we measure. {person} is "a woman", "an Asian man", ...
TEMPLATES = {
    # --- Tested in the first pilot (2026-11-21). T1 FAILED: its no-label images looked like
    # --- old photographs. T2 passed on era but often showed bare shoulders. Kept for the record.
    "T1": {
        "label": "A contemporary color portrait photograph of {person} who is {label}, head and shoulders.",
        "none": "A contemporary color portrait photograph of {person}, head and shoulders.",
    },
    "T2": {
        "label": "A recent color portrait photo, head and shoulders, of {person}; the person is {label}.",
        "none": "A recent color portrait photo, head and shoulders, of {person}.",
    },
    # --- Candidates for the main run, tested in pilot2. Two changes from T1/T2:
    # --- "photo" instead of "photograph" (my GUESS: "photograph" pulls toward archival images),
    # --- and "upper body" instead of "head and shoulders" so clothing is more often visible.
    "T2u": {
        "label": "A recent color portrait photo, upper body, of {person}; the person is {label}.",
        "none": "A recent color portrait photo, upper body, of {person}.",
    },
    "T3u": {
        "label": "A recent color portrait photo of {person} who is {label}, upper body.",
        "none": "A recent color portrait photo of {person}, upper body.",
    },
    # --- Candidates tested in pilot4 (2026-11-21, after pilot2 failed for both T2u and T3u).
    # --- Both add the SAME negative prompt (NEGATIVE_STYLE) in every arm. It names no political,
    # --- demographic or clothing-style content; it only pushes away from paintings, old-photo
    # --- looks and nudity. It is a constant intervention, so findings describe "SD 1.5 under this
    # --- prompt setup", not SD 1.5 in general. Logged in docs/DEVIATIONS.md (D8).
    "T3n": {   # exactly T3u's wording, plus the negative prompt (isolates the negative prompt)
        "label": "A recent color portrait photo of {person} who is {label}, upper body.",
        "none": "A recent color portrait photo of {person}, upper body.",
        "negative": "NEGATIVE_STYLE",
    },
    # --- Candidates tested in pilot5 (2026-11-22): adults, any clothing but fully clothed, whole person
    # --- visible, in an everyday environment. N1 leaves the setting to the model; N2 lists everyday places.
    "N1": {
        "label": "A candid color photo of {person} who is {label}, full body, in an everyday setting.",
        "none": "A candid color photo of {person}, full body, in an everyday setting.",
        "negative": "NEGATIVE_V2",
    },
    "N2": {
        "label": "A color photo of {person} who is {label}, standing in an everyday place such as home, work, a cafe, a store or a park.",
        "none": "A color photo of {person}, standing in an everyday place such as home, work, a cafe, a store or a park.",
        "negative": "NEGATIVE_V2",
    },
    "T7": {    # also names a modern camera look, plus the negative prompt
        "label": "A sharp color photo taken with a modern digital camera of {person} who is {label}, upper body.",
        "none": "A sharp color photo taken with a modern digital camera of {person}, upper body.",
        "negative": "NEGATIVE_STYLE",
    },
}

# Templates with "negative": "NEGATIVE_STYLE" use this text. Older templates have no negative prompt.
NEGATIVE_STYLE = ("painting, illustration, drawing, sketch, vintage, antique, sepia, black and white, "
                  "shirtless, nude, naked, deformed, disfigured")

# Negative prompt v2 (templates N1, N2): pushes away from paintings, old-photo looks, nudity,
# minors, and obvious anatomy failures. It deliberately does NOT suppress text, logos, symbols,
# casual clothing or settings. Identical in every arm.
NEGATIVE_V2 = ("painting, illustration, drawing, sketch, vintage, antique, sepia, black and white, "
               "shirtless, nude, naked, bare chest, underwear, swimsuit, lingerie, child, teenager, "
               "deformed, disfigured, extra limbs, bad hands, blurry, watermark")
NEGATIVES = {"NEGATIVE_STYLE": NEGATIVE_STYLE, "NEGATIVE_V2": NEGATIVE_V2}

MAIN_N_SEEDS = 15
PILOT_SEEDS_NONE = list(range(1000, 1006))   # 6 seeds
PILOT_SEEDS_LABEL = list(range(1000, 1003))  # 3 seeds, Democrat/Republican, T1 only (first pilot)
PILOT3_SEEDS = list(range(1000, 1003))
PILOT1_TEMPLATES = ["T1", "T2"]
PILOT2_TEMPLATES = ["T2u", "T3u"]
PILOT4_TEMPLATES = ["T3n", "T7"]
PILOT5_TEMPLATES = ["N1", "N2"]
PILOT5_SEEDS = [1000, 1001]


def person_phrase(group, gender):
    """'a woman', 'a Black man', 'an Asian woman' (the article follows the first letter)."""
    adjective = GROUPS[group]
    words = f"{adjective} {gender}" if adjective else gender
    article = "an" if words[0].lower() in "aeiou" else "a"
    return f"{article} {words}"


def make_row(mode, template, group, gender, label_key, seed):
    """One planned image: what to generate, before generating it."""
    phrase = LABELS[label_key]
    person = person_phrase(group, gender)
    if phrase is None:
        prompt = TEMPLATES[template]["none"].format(person=person)
    else:
        prompt = TEMPLATES[template]["label"].format(person=person, label=phrase)
    # Ids for "no group stated" keep the original format so earlier pilot records stay valid.
    group_part = "" if group == "none" else f"{group}_"
    return {
        "image_id": f"{mode_tag(mode)}_{template}_{group_part}{gender}_{label_key}_s{seed:04d}",
        "mode": mode,
        "engine": ENGINE,
        "template": template,
        "group": group,
        "person_phrase": person,
        "gender": gender,
        "label_key": label_key,
        "label_phrase": phrase,
        "prompt": prompt,
        # "" means no negative prompt (all templates before T3n). Stored so records are complete.
        "negative_prompt": NEGATIVES[TEMPLATES[template]["negative"]] if TEMPLATES[template].get("negative") else "",
        "seed": seed,
    }


def _check_templates(templates, mode):
    if not templates:
        raise SystemExit(f"{mode} needs --templates, e.g. --templates T2u "
                         "(choose after checking the pilots; there is deliberately no default).")
    unknown = [t for t in templates if t not in TEMPLATES]
    if unknown:
        raise SystemExit(f"unknown template(s) {unknown}; known: {sorted(TEMPLATES)}")


def build_plan(mode, templates=None, n_seeds=MAIN_N_SEEDS):
    """Return the full list of planned images, in seed-major order."""
    rows = []
    if mode == "pilot":
        for seed in PILOT_SEEDS_NONE:
            for template in PILOT1_TEMPLATES:
                for gender in GENDERS:
                    rows.append(make_row(mode, template, "none", gender, "none", seed))
        for seed in PILOT_SEEDS_LABEL:
            for gender in GENDERS:
                for label_key in ("dem", "rep"):
                    rows.append(make_row(mode, "T1", "none", gender, label_key, seed))
        rows.sort(key=lambda r: r["seed"])          # keep seed-major order
    elif mode == "pilot2":
        for seed in PILOT_SEEDS_NONE:
            for template in PILOT2_TEMPLATES:
                for gender in GENDERS:
                    rows.append(make_row(mode, template, "none", gender, "none", seed))
    elif mode == "pilot5":
        for seed in PILOT5_SEEDS:
            for template in PILOT5_TEMPLATES:
                for gender in GENDERS:
                    for label_key in labels_for(template):
                        rows.append(make_row(mode, template, "none", gender, label_key, seed))
    elif mode == "pilot4":
        for seed in PILOT_SEEDS_NONE:      # same seeds as pilot2, so T3n can be compared with T3u
            for template in PILOT4_TEMPLATES:
                for gender in GENDERS:
                    rows.append(make_row(mode, template, "none", gender, "none", seed))
    elif mode == "pilot3":
        _check_templates(templates, mode)
        for seed in PILOT3_SEEDS:
            for template in templates:
                for group in SPECIFIED_GROUPS:
                    for gender in GENDERS:
                        rows.append(make_row(mode, template, group, gender, "none", seed))
    else:  # main
        _check_templates(templates, mode)
        for seed in range(n_seeds):
            for template in templates:
                for group in ["none"] + SPECIFIED_GROUPS:
                    for gender in GENDERS:
                        for label_key in labels_for(template):
                            rows.append(make_row(mode, template, group, gender, label_key, seed))
    return rows


# ----------------------------------------------------------------------------------
# Records
# ----------------------------------------------------------------------------------
def load_records(path):
    """Read records.jsonl, skipping any half-written last line from a crash."""
    records = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            records[rec["image_id"]] = rec
    return list(records.values())


def is_black(img):
    """True if the image is entirely black (safety-checker blanking or an fp16 failure)."""
    return img.convert("L").getextrema()[1] == 0


# ----------------------------------------------------------------------------------
# Model (imports are lazy so `plan` and `sheet` work without torch installed)
# ----------------------------------------------------------------------------------
def snapshot_hash():
    """Commit hash of the cached model download, so the exact weights are on record.

    Read from the local Hugging Face cache folder; falls back to the hub API; never blocks a run.
    """
    try:
        cache = Path(os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME", Path.home() / ".cache/huggingface") )
        roots = [cache / "hub", cache]
        for root in roots:
            snaps = sorted((root / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots").glob("*"))
            if len(snaps) == 1:
                return snaps[0].name
            if snaps:
                return "multiple: " + ",".join(p.name for p in snaps)
        from huggingface_hub import snapshot_download

        return Path(snapshot_download(MODEL_ID, local_files_only=True)).name
    except Exception as exc:  # noqa: BLE001  (best effort; never block generation)
        return f"unknown ({type(exc).__name__}: {exc})"


def load_pipeline(fp32):
    """Load the selected engine and return (generate, meta).

    generate(prompt, seed, negative_prompt="") -> (PIL image, safety_checker_flag)
    Stable Diffusion 1.5 keeps its safety checker ON (part of the default behavior being audited).
    SDXL's diffusers pipeline has no safety checker, so its flag is always False.
    """
    import diffusers
    import torch

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float32 if (fp32 or device == "cpu") else torch.float16
    if ENGINE.startswith("sdxl"):
        from diffusers import StableDiffusionXLPipeline

        kwargs = dict(torch_dtype=dtype, use_safetensors=True, add_watermarker=False)
        if dtype == torch.float16:
            kwargs["variant"] = "fp16"
        # The official SDXL VAE is upcast to fp32 for decoding automatically (force_upcast).
        pipe = StableDiffusionXLPipeline.from_pretrained(MODEL_ID, **kwargs).to(device)
    else:
        from diffusers import StableDiffusionPipeline

        pipe = StableDiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=dtype).to(device)
    pipe.set_progress_bar_config(disable=True)
    if ATTN_SLICING:
        pipe.enable_attention_slicing()

    def generate(prompt, seed, negative_prompt=""):
        # Seed on the CPU so the starting noise is identical across runs and devices.
        gen = torch.Generator(device="cpu").manual_seed(seed)
        res = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt or None,
            height=HEIGHT,
            width=WIDTH,
            num_inference_steps=STEPS,
            guidance_scale=GUIDANCE,
            generator=gen,
        )
        flags = getattr(res, "nsfw_content_detected", None)
        return res.images[0], bool(flags and flags[0])

    meta = {
        "engine": ENGINE,
        "model_id": MODEL_ID,
        "model_snapshot": snapshot_hash(),
        "scheduler": type(pipe.scheduler).__name__,
        "device": device,
        "dtype": str(dtype),
        "torch": torch.__version__,
        "diffusers": diffusers.__version__,
        "platform": platform.platform(),
        "steps": STEPS,
        "guidance_scale": GUIDANCE,
        "size": WIDTH if WIDTH == HEIGHT else f"{WIDTH}x{HEIGHT}",
        "width": WIDTH,
        "height": HEIGHT,
        "attention_slicing": ATTN_SLICING,
    }
    return generate, meta


# ----------------------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------------------
def cmd_plan(mode, _out_root, templates=None, n_seeds=MAIN_N_SEEDS):
    plan = build_plan(mode, templates, n_seeds)
    n = len(plan)
    if MEASURED_SECONDS_PER_IMAGE:
        hours = n * MEASURED_SECONDS_PER_IMAGE / 3600
        print(f"{mode_tag(mode)}: {n} images, about {hours:.2f} h at {MEASURED_SECONDS_PER_IMAGE} s/image "
              f"({n * MEASURED_SECONDS_PER_IMAGE / 60:.0f} min)")
    else:
        print(f"{mode_tag(mode)}: {n} images; engine {ENGINE} has no measured seconds per image yet "
              f"(run pilot5 and read the mean from `python scripts/check_run.py --mode {mode_tag(mode)}`)")
    print(f"engine: {ENGINE}  model: {MODEL_ID}  size: {WIDTH}x{HEIGHT}  steps: {STEPS}  guidance: {GUIDANCE}")
    seeds = sorted({r["seed"] for r in plan})
    print(f"seeds: {seeds[0]}..{seeds[-1]} ({len(seeds)} distinct)")
    print("\nimages per group x label (templates, genders pooled):")
    counts = Counter((r["group"], r["label_key"]) for r in plan)
    for (group, label_key), c in sorted(counts.items()):
        print(f"  {group:9s} {label_key:8s} {c}")
    print("\nexact prompts (first template shown for each; gender = woman; default and Asian groups):")
    seen = set()
    for r in plan:
        key = (r["template"], r["group"], r["label_key"])
        if r["gender"] == "woman" and r["group"] in ("none", "asian") and key not in seen:
            seen.add(key)
            neg = f"   (negative: {r['negative_prompt']})" if r["negative_prompt"] else ""
            print(f"  [{r['template']} / {r['group']} / {r['label_key']}] {r['prompt']}{neg}")


def cmd_run(mode, out_root, fp32, limit, templates=None, n_seeds=MAIN_N_SEEDS):
    plan = build_plan(mode, templates, n_seeds)
    out_dir = Path(out_root) / mode_tag(mode)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    rec_path = out_dir / "records.jsonl"

    # If a crash left a half-written last line, end it with a newline so the next record
    # starts on its own line instead of being glued to (and lost with) the broken one.
    if rec_path.exists() and rec_path.stat().st_size and not rec_path.read_bytes().endswith(b"\n"):
        with rec_path.open("a") as fh:
            fh.write("\n")

    done = {r["image_id"] for r in load_records(rec_path)}
    todo = [r for r in plan if r["image_id"] not in done]
    if limit is not None:
        todo = todo[:limit]
    print(f"{mode_tag(mode)}: {len(plan)} planned, {len(done)} already done, {len(todo)} to generate now")
    if templates:
        print(f"templates: {templates}")
    if not todo:
        print("nothing to do")
        return

    generate, meta = load_pipeline(fp32)
    print(f"engine={ENGINE} device={meta['device']} dtype={meta['dtype']} snapshot={meta['model_snapshot']}")

    started, times, n_blank = time.perf_counter(), [], 0
    for i, row in enumerate(todo, 1):
        t0 = time.perf_counter()
        img, nsfw = generate(row["prompt"], row["seed"], row["negative_prompt"])
        secs = time.perf_counter() - t0
        times.append(secs)

        black = is_black(img)
        path = img_dir / f"{row['image_id']}.png"
        img.save(path)

        if nsfw:
            exclusion = "blank_safety_checker"
        elif black:
            exclusion = "blank_other"      # often an fp16 failure: rerun with --fp32
        else:
            exclusion = None
        n_blank += exclusion is not None

        record = {
            **row,
            **meta,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "generation_seconds": round(secs, 3),
            "nsfw_flag": nsfw,
            "all_black": black,
            "exclusion_code": exclusion,
            "file": f"images/{path.name}",
        }
        # One write per record, flushed immediately, so a crash loses at most this line.
        with rec_path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
            fh.flush()

        recent = times[-20:]
        eta_min = (len(todo) - i) * (sum(recent) / len(recent)) / 60
        flag = f"  BLANK ({exclusion})" if exclusion else ""
        print(f"[{i}/{len(todo)}] {row['image_id']} {secs:.1f}s eta {eta_min:.0f} min{flag}", flush=True)
        if exclusion == "blank_other" and i <= 3:
            print("  warning: an all-black image that the safety checker did not flag. "
                  "If this repeats, rerun with --fp32.", flush=True)

    total = time.perf_counter() - started
    print(f"\nfinished {len(todo)} images in {total / 60:.1f} min; {n_blank} blank. "
          f"Records: {rec_path}")


def cmd_sheet(mode, out_root, page_size, cols=6, thumb=170):
    from PIL import Image, ImageDraw

    out_dir = Path(out_root) / mode_tag(mode)
    records = load_records(out_dir / "records.jsonl")
    if not records:
        raise SystemExit(f"no records in {out_dir / 'records.jsonl'}; run generation first")
    label_order, group_order = list(LABELS), list(GROUPS)
    # Records written before the group factor existed have no "group" field: treat as "none".
    records.sort(key=lambda r: (r["template"], group_order.index(r.get("group", "none")), r["gender"],
                                label_order.index(r["label_key"]), r["seed"]))

    cell_h = thumb + 24
    for page, start in enumerate(range(0, len(records), page_size), 1):
        chunk = records[start:start + page_size]
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (cols * thumb, rows * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for k, r in enumerate(chunk):
            x, y = (k % cols) * thumb, (k // cols) * cell_h
            im = Image.open(out_dir / r["file"]).convert("RGB")
            im.thumbnail((thumb, thumb))                      # keep the aspect ratio (portrait engines)
            sheet.paste(im, (x + (thumb - im.width) // 2, y))
            group = r.get("group", "none")
            group_part = "" if group == "none" else f"{group[:3]} "
            draw.text((x + 3, y + thumb + 5),
                      f"{r['template']} {group_part}{r['gender'][0]} {r['label_key']} s{r['seed']}",
                      fill="black")
            if r["exclusion_code"]:
                draw.rectangle([x, y, x + thumb - 1, y + thumb - 1], outline="red", width=3)
        path = out_dir / f"contact_sheet_{page}.png"
        sheet.save(path)
        print(f"wrote {path} ({len(chunk)} images)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run", "sheet"):
        p = sub.add_parser(name)
        p.add_argument("mode", choices=["pilot", "pilot2", "pilot3", "pilot4", "pilot5", "main"])
        p.add_argument("--engine", default="sd15", choices=sorted(ENGINES),
                       help="sd15 (default, 512x512), sd15tall (512x768), sdxl (832x1216, 30 steps) or sdxlfast (768x1024, 20 steps)")
        p.add_argument("--out", default="outputs", help="output root folder (default: outputs)")
        if name in ("plan", "run"):
            p.add_argument("--templates", default=None,
                           help="comma-separated template ids; required for pilot3 and main, e.g. T2u")
            p.add_argument("--seeds", type=int, default=MAIN_N_SEEDS,
                           help=f"number of seeds for main (default {MAIN_N_SEEDS})")
        if name == "run":
            p.add_argument("--fp32", action="store_true", help="float32 instead of float16")
            p.add_argument("--attn-slicing", action="store_true", help="enable attention slicing (speed/memory experiment)")
            p.add_argument("--limit", type=int, default=None, help="generate only the next N images")
        if name == "sheet":
            p.add_argument("--page-size", type=int, default=36)
            p.add_argument("--cols", type=int, default=6)
            p.add_argument("--thumb", type=int, default=170, help="thumbnail size in pixels")
    args = ap.parse_args()

    set_engine(args.engine)
    global ATTN_SLICING
    ATTN_SLICING = bool(getattr(args, "attn_slicing", False))
    templates = ([t.strip() for t in args.templates.split(",")]
                 if getattr(args, "templates", None) else None)
    if args.cmd == "plan":
        cmd_plan(args.mode, args.out, templates, args.seeds)
    elif args.cmd == "run":
        cmd_run(args.mode, args.out, args.fp32, args.limit, templates, args.seeds)
    else:
        cmd_sheet(args.mode, args.out, args.page_size, args.cols, args.thumb)


if __name__ == "__main__":
    main()
