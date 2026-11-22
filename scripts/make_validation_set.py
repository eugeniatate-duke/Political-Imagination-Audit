#!/usr/bin/env python3
"""Build the blind manual-labeling set (90 images by default) and the keyboard labeling tool.

    python scripts/make_validation_set.py            # after the codebook is frozen

Creates outputs/validation/:
    images/v001.png ...        copies of the sampled images under neutral names (no label, group,
                               gender or seed is visible in a file name or on the page)
    label_tool.html            open in a browser; label with the keyboard; export manual_labels.csv
    validation_ids.txt         real image_ids, for `label_vlm.py --ids-file`
    manifest_PRIVATE.csv       v-id -> image_id. DO NOT OPEN while labeling (it would unblind you).

Sampling: 18 random non-blank images per label (5 labels = 90), fixed seed, shuffled. Groups and
genders are mixed by chance, not balanced. The sample is stratified by label because the label
contrasts are the point of the audit; with 18 per label, agreement estimates are rough (reported
with bootstrap intervals).
"""
import argparse
import csv
import json
import random
import shutil
from pathlib import Path

import codebook as cb

SEED = 20261122

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Blind labeling tool</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;display:flex;height:100vh;background:#f6f6f4;color:#222}
 #left{flex:0 0 560px;padding:12px;display:flex;flex-direction:column;align-items:center}
 #left img{width:512px;height:512px;border:1px solid #bbb;background:#fff}
 #right{flex:1;padding:12px 18px;overflow:auto}
 .field{padding:6px 8px;margin:3px 0;border-radius:6px;border:1px solid transparent}
 .field.cur{background:#fff;border-color:#2a6fdb}
 .field b{display:inline-block;min-width:210px}
 .opt{display:inline-block;margin:2px 6px 2px 0;padding:2px 7px;border:1px solid #bbb;border-radius:4px;cursor:pointer;background:#fafafa}
 .opt.sel{background:#2a6fdb;color:#fff;border-color:#2a6fdb}
 .def{font-size:12px;color:#666;margin:2px 0 0 0}
 button{margin:4px 6px 4px 0;padding:6px 10px}
 #bar{margin:6px 0;font-size:14px}
</style></head><body>
<div id="left">
  <div id="bar"></div>
  <img id="img" alt="image to label">
  <div style="margin-top:8px;font-size:13px;color:#555;text-align:center">
   Keys: <b>1-8</b> pick option, <b>u</b> = unclear, <b>Backspace</b> = back one field,
   <b>[</b> previous image, <b>]</b> next image. Picking <i>assessable = no</i> fills the rest as unclear.
  </div>
  <div style="margin-top:8px">
   <button id="dl">Download CSV (do this every ~20 images)</button>
  </div>
</div>
<div id="right"><div id="fields"></div></div>
<script>
const FIELDS = __FIELDS__;          // [{name, values, def}]
const IMAGES = __IMAGES__;          // ["images/v001.png", ...]
const STORE = "label_tool_v1_" + IMAGES.length;

// LOGIC-START  (pure functions; unit-tested in tests/test_label_tool.py)
function newState(n){return {idx:0, fi:0, answers:Array.from({length:n},()=>({}))};}
function applyKey(s, key){
  const f = FIELDS[s.fi], a = s.answers[s.idx];
  if(key === "Backspace"){ if(s.fi>0){s.fi--;} else if(s.idx>0){s.idx--; s.fi=FIELDS.length-1;} return s; }
  if(key === "[" ){ if(s.idx>0){s.idx--; s.fi=0;} return s; }
  if(key === "]" ){ if(s.idx<s.answers.length-1){s.idx++; s.fi=0;} return s; }
  let val = null;
  if(key === "u"){ val = f.values.includes("unclear") ? "unclear" : null; }
  else if(/^[1-9]$/.test(key)){ val = f.values[parseInt(key,10)-1] || null; }
  if(val === null) return s;
  a[f.name] = val;
  if(f.name === "assessable" && val === "no"){           // codebook rule: everything else unclear
    FIELDS.forEach(g => { if(g.name !== "assessable") a[g.name] = "unclear"; });
    if(s.idx < s.answers.length-1){ s.idx++; s.fi = 0; } else { s.fi = FIELDS.length-1; }
    return s;
  }
  if(s.fi < FIELDS.length-1){ s.fi++; }
  else if(s.idx < s.answers.length-1){ s.idx++; s.fi = 0; }
  return s;
}
function formalAttire(a){
  if(a.assessable === "no") return "unclear";
  if(!a.top_type || a.top_type === "unclear") return "unclear";
  return (a.top_type === "jacket_or_blazer" || a.top_type === "button_up_shirt") ? "yes" : "no";
}
function toCsv(answers){
  const cols = FIELDS.map(f => f.name).concat(["formal_attire"]);
  const rows = [["v_id"].concat(cols).join(",")];
  answers.forEach((a, i) => {
    const vid = "v" + String(i+1).padStart(3, "0");
    rows.push([vid].concat(FIELDS.map(f => a[f.name] || "")).concat([formalAttire(a)]).join(","));
  });
  return rows.join("\n") + "\n";
}
// LOGIC-END

let S = newState(IMAGES.length);
try { const saved = JSON.parse(localStorage.getItem(STORE)); if(saved && saved.answers.length === IMAGES.length) S = saved; } catch(e) {}
function save(){ try { localStorage.setItem(STORE, JSON.stringify(S)); } catch(e) {} }
function render(){
  document.getElementById("img").src = IMAGES[S.idx];
  const done = S.answers.filter(a => FIELDS.every(f => a[f.name])).length;
  document.getElementById("bar").textContent = "Image " + (S.idx+1) + " of " + IMAGES.length + "  |  fully labeled: " + done;
  const box = document.getElementById("fields"); box.innerHTML = "";
  FIELDS.forEach((f, k) => {
    const d = document.createElement("div"); d.className = "field" + (k === S.fi ? " cur" : "");
    const t = document.createElement("b"); t.textContent = f.name; d.appendChild(t);
    f.values.forEach((v, j) => {
      const o = document.createElement("span");
      o.className = "opt" + (S.answers[S.idx][f.name] === v ? " sel" : "");
      o.textContent = (j+1) + " " + v;
      o.onclick = () => { S.fi = k; S = applyKey(S, String(j+1)); save(); render(); };
      d.appendChild(o);
    });
    if(k === S.fi){ const p = document.createElement("div"); p.className = "def"; p.textContent = f.def; d.appendChild(p); }
    box.appendChild(d);
  });
}
document.addEventListener("keydown", e => {
  if(e.metaKey || e.ctrlKey || e.altKey) return;
  S = applyKey(S, e.key); save(); render();
});
document.getElementById("dl").onclick = () => {
  const blob = new Blob([toCsv(S.answers)], {type:"text/csv"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "manual_labels.csv"; a.click();
};
render();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", default="main")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--per-label", type=int, default=18)
    args = ap.parse_args()

    out_dir = Path(args.out) / args.mode
    records = [json.loads(l) for l in (out_dir / "records.jsonl").read_text().splitlines() if l.strip()]
    eligible = [r for r in records if r["exclusion_code"] is None]

    rng = random.Random(SEED)
    chosen = []
    for label in sorted({r["label_key"] for r in eligible}):
        pool = sorted((r for r in eligible if r["label_key"] == label), key=lambda r: r["image_id"])
        if len(pool) < args.per_label:
            raise SystemExit(f"only {len(pool)} usable images for label {label}")
        chosen += rng.sample(pool, args.per_label)
    rng.shuffle(chosen)

    val_dir = Path(args.out) / "validation"
    (val_dir / "images").mkdir(parents=True, exist_ok=True)
    manifest, images = [], []
    for i, r in enumerate(chosen, 1):
        vid = f"v{i:03d}"
        shutil.copyfile(out_dir / r["file"], val_dir / "images" / f"{vid}.png")
        manifest.append((vid, r["image_id"]))
        images.append(f"images/{vid}.png")

    with (val_dir / "manifest_PRIVATE.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["v_id", "image_id"])
        w.writerows(manifest)
    (val_dir / "validation_ids.txt").write_text("\n".join(i for _v, i in manifest) + "\n")

    fields = [{"name": n, "values": v, "def": d} for n, (v, d) in cb.FIELDS.items()]
    html = HTML.replace("__FIELDS__", json.dumps(fields)).replace("__IMAGES__", json.dumps(images))
    (val_dir / "label_tool.html").write_text(html)
    print(f"wrote {len(chosen)} images and label_tool.html to {val_dir}")
    print("Open label_tool.html in your browser. Do not open manifest_PRIVATE.csv until you are done.")


if __name__ == "__main__":
    main()
