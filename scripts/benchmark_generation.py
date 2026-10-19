#!/usr/bin/env python3
"""Benchmark Stable Diffusion 1.5 on Apple Silicon (MPS) for the Political Imagination Audit.

Why this exists
---------------
Before fixing the audit's sample size we need two measured facts, not guesses:

1. SPEED: how long one 512x512 image takes on this machine, so we can budget
   the number of images (and therefore annotation hours).
2. EMBEDDING FEASIBILITY: the Tier-2 interventions (interpolation, direction
   ablation) feed *precomputed prompt embeddings* to the pipeline. This script
   checks that doing so reproduces the image made from the plain text prompt.

It also records safety-checker flags, because images the checker blanks are
"failed generations" that must appear in the audit record.

Usage
-----
    python scripts/benchmark_generation.py --n 20 --steps 25
    python scripts/benchmark_generation.py --n 20 --fp32      # if fp16 gives black images

Outputs go to outputs/benchmark/ (images + benchmark.json).

NOTE: written without access to an M4 machine, so it has been syntax-checked
but not run. Treat the first run as part of the benchmark and report any error.
"""

import argparse
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import diffusers
import numpy as np
import torch
from diffusers import StableDiffusionPipeline

# Repo id as listed on the Hugging Face hub; check the model card for the license
# and record the exact commit hash of the download in the audit metadata.
MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
PROMPT = "A portrait photograph of a woman, head and shoulders."


def pick_device() -> str:
    """Use Apple's Metal backend when available, otherwise fall back to CPU."""
    return "mps" if torch.backends.mps.is_available() else "cpu"


def encode_text(pipe, prompt: str, device: str):
    """Return (conditional, unconditional) text embeddings for `prompt`.

    Recent diffusers versions return a tuple (prompt_embeds, negative_prompt_embeds).
    We pass negative_prompt="" so the unconditional branch matches the default.
    """
    out = pipe.encode_prompt(prompt, device, 1, True, negative_prompt="")
    if isinstance(out, tuple) and len(out) >= 2:
        return out[0], out[1]
    raise RuntimeError(
        "Unexpected return type from encode_prompt; check your diffusers version "
        f"(installed: {diffusers.__version__})."
    )


def is_black(img) -> bool:
    """True if the image is entirely black (safety-checker blanking or an fp16 failure)."""
    return img.convert("L").getextrema()[1] == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="number of timed images")
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--fp32", action="store_true", help="use float32 instead of float16")
    ap.add_argument("--out", type=str, default="outputs/benchmark")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = pick_device()
    dtype = torch.float32 if (args.fp32 or device == "cpu") else torch.float16
    print(f"device={device} dtype={dtype} torch={torch.__version__} diffusers={diffusers.__version__}")

    # The safety checker stays ON (default behavior). If it blanks portraits unevenly
    # across labels, that is itself an audit finding, so we log flags rather than hide them.
    pipe = StableDiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=dtype).to(device)
    pipe.set_progress_bar_config(disable=True)

    def generate(seed: int, **kwargs):
        # Seed on CPU so the starting noise is identical across devices and runs.
        gen = torch.Generator(device="cpu").manual_seed(seed)
        return pipe(
            height=512,
            width=512,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            generator=gen,
            **kwargs,
        )

    # Warm-up pass (untimed): the first MPS call compiles kernels and is not representative.
    print("warm-up...")
    _ = generate(seed=12345, prompt=PROMPT)

    # ---- 1. Speed ---------------------------------------------------------
    times, flagged, black, first_img = [], 0, 0, None
    for seed in range(args.n):
        t0 = time.perf_counter()
        res = generate(seed=seed, prompt=PROMPT)
        times.append(time.perf_counter() - t0)

        img = res.images[0]
        flags = res.nsfw_content_detected
        if flags and flags[0]:
            flagged += 1
        if is_black(img):
            black += 1
        if seed == 0:
            first_img = img
        img.save(out_dir / f"seed{seed:03d}.png")
        print(f"seed {seed:3d}: {times[-1]:.2f}s")

    mean_t = statistics.mean(times)
    print(f"\nmean {mean_t:.2f}s | median {statistics.median(times):.2f}s "
          f"| min {min(times):.2f}s | max {max(times):.2f}s")
    projections = {}
    for n_images in (750, 1200, 1700):
        hours = n_images * mean_t / 3600
        projections[str(n_images)] = round(hours, 2)
        print(f"projected generation time for {n_images} images: {hours:.1f} h")
    print(f"safety-checker flagged: {flagged}/{args.n} | all-black images: {black}/{args.n}")

    # ---- 2. Embedding feasibility ----------------------------------------
    # Generate seed 0 again from precomputed embeddings; it should look like the
    # text-prompt version. Small differences can come from fp16 numerics.
    print("\nchecking precomputed prompt_embeds path...")
    cond, uncond = encode_text(pipe, PROMPT, device)
    res_emb = generate(seed=0, prompt_embeds=cond, negative_prompt_embeds=uncond)
    emb_img = res_emb.images[0]
    emb_img.save(out_dir / "seed000_from_embeds.png")
    diff = float(np.abs(
        np.asarray(first_img, dtype=np.int16) - np.asarray(emb_img, dtype=np.int16)
    ).mean())
    verdict = "PASS" if diff < 3.0 else "CHECK (inspect the two seed000 images by eye)"
    print(f"mean abs pixel difference (0-255 scale): {diff:.2f} -> {verdict}")
    print(f"embedding shape: {tuple(cond.shape)}  (sequence length x hidden size per image)")

    # ---- 3. Save everything needed to reproduce the benchmark ------------
    record = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "device": device,
        "dtype": str(dtype),
        "torch": torch.__version__,
        "diffusers": diffusers.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "steps": args.steps,
        "guidance_scale": args.guidance,
        "prompt": PROMPT,
        "n_timed": args.n,
        "seconds_per_image": {
            "mean": mean_t,
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
        },
        "projected_hours": projections,
        "safety_flagged": flagged,
        "all_black": black,
        "embeds_mean_abs_pixel_diff": diff,
        "embeds_verdict": verdict,
    }
    (out_dir / "benchmark.json").write_text(json.dumps(record, indent=2))
    print(f"\nwrote {out_dir / 'benchmark.json'}")


if __name__ == "__main__":
    main()
