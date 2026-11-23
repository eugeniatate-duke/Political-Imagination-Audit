#!/usr/bin/env python3
"""EXPLORATORY add-on: build a blind labeling tool for apparent skin tone in the NO-GROUP arm.

    python scripts/make_skintone_set.py --run outputs/main-sdxlfast

Question: when the prompt states no race, does the person the model draws look different in apparent
skin tone under the Democrat label than under the Republican label (and the other labels)?
This is an impression of how a SYNTHETIC image looks. It is not anyone's identity, it is affected by
lighting and photo style, and it was added after the main results were seen (see docs/DEVIATIONS.md).

Writes outputs/skintone/:
  images/sNNN.png          every non-blank no-group image (150 expected), shuffled, anonymous names,
                           plus a few DUPLICATES (different names) so you can later check your own consistency
  label_tool.html          open in a browser; keys 1/2/3 = light/medium/dark, u = unclear, [ ] = prev/next
  manifest_PRIVATE.csv     maps sNNN -> image_id (do not open before you finish labeling)
"""
import argparse
import csv
import json
import random
import shutil
from pathlib import Path

from PIL import Image

SEED = 20261123
N_DUP = 20
MAX_H = 1024

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Skin tone labeling (blind)</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;display:flex;height:100vh;background:#f6f6f4;color:#222}
 #left{flex:0 0 55%;padding:12px;display:flex;flex-direction:column;align-items:center}
 #left img{max-width:100%;max-height:92vh;width:auto;height:auto;object-fit:contain;border:1px solid #bbb;background:#fff}
 #right{flex:1;padding:14px 20px;overflow:auto}
 .opt{display:block;margin:8px 0;padding:10px 12px;border:1px solid #bbb;border-radius:6px;cursor:pointer;background:#fafafa}
 .opt.sel{background:#2a6fdb;color:#fff;border-color:#2a6fdb}
 .def{font-size:13px;opacity:.85;margin-top:2px}
 button{margin:4px 6px 4px 0;padding:6px 10px}
</style></head><body>
<div id="left"><div id="bar" style="margin:6px 0;font-size:14px"></div><img id="img" alt="image to label"></div>
<div id="right">
 <h3 style="margin-top:0">Apparent skin tone of the person in the picture</h3>
 <p style="font-size:13px">Judge the skin you can see (face, neck, hands) as it looks in this picture. Do not guess ethnicity, nationality or politics.
 Compensate for shadow and color cast as well as you can. Use <b>unclear</b> if the skin is not visible enough, the image is an illustration or no single person is clear.
 Decide by your first impression, then move on. Do not compare with earlier images.</p>
 <div class="opt" data-v="light"><b>1  light</b><div class="def">Among the lightest skin tones you see in everyday photos.</div></div>
 <div class="opt" data-v="medium"><b>2  medium</b><div class="def">In the middle: light-brown, olive, tan, or in between light and dark.</div></div>
 <div class="opt" data-v="dark"><b>3  dark</b><div class="def">Among the darkest skin tones you see in everyday photos.</div></div>
 <div class="opt" data-v="unclear"><b>u  unclear</b><div class="def">Cannot judge, or not a clear photo of one person.</div></div>
 <p style="font-size:13px;color:#555">Keys: 1 2 3 u pick and advance. Backspace clears. [ previous, ] next. Progress saves in this browser.</p>
 <button id="dl">Download CSV</button> <button id="jump">Go to first unlabeled</button>
 <div id="status" style="font-size:13px;margin-top:8px"></div>
</div>
<script>
const IDS = __IDS__;
const KEY = "skintone_labels_v1";
let labels = {}; try{ labels = JSON.parse(localStorage.getItem(KEY)||"{}"); }catch(e){}
let i = 0;
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(labels)); }catch(e){} }
function show(){
  const id = IDS[i];
  document.getElementById("img").src = "images/"+id+".png";
  const done = Object.keys(labels).length;
  document.getElementById("bar").textContent = (i+1)+" / "+IDS.length+"   labeled: "+done;
  document.querySelectorAll(".opt").forEach(o=>o.classList.toggle("sel", labels[id]===o.dataset.v));
}
function set(v){ labels[IDS[i]] = v; save(); if(i<IDS.length-1) i++; show(); }
document.addEventListener("keydown", e=>{
  if(e.key==="1") set("light"); else if(e.key==="2") set("medium"); else if(e.key==="3") set("dark");
  else if(e.key==="u") set("unclear");
  else if(e.key==="Backspace"){ delete labels[IDS[i]]; save(); show(); }
  else if(e.key==="["){ i=Math.max(0,i-1); show(); } else if(e.key==="]"){ i=Math.min(IDS.length-1,i+1); show(); }
});
document.querySelectorAll(".opt").forEach(o=>o.onclick=()=>set(o.dataset.v));
document.getElementById("jump").onclick=()=>{ const k=IDS.findIndex(x=>!labels[x]); if(k>=0){i=k;show();} };
document.getElementById("dl").onclick=()=>{
  const rows=["s_id,apparent_skin_tone"].concat(IDS.map(x=>x+","+(labels[x]||"")));
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([rows.join("\n")+"\n"],{type:"text/csv"}));
  a.download="skintone_labels.csv"; a.click();
  const miss=IDS.filter(x=>!labels[x]).length; document.getElementById("status").textContent = miss? miss+" images have no label yet (blank in the CSV).":"All labeled.";
};
show();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="run folder, e.g. outputs/main-sdxlfast")
    ap.add_argument("--out", default="outputs/skintone")
    args = ap.parse_args()
    run, out = Path(args.run), Path(args.out)
    recs = [json.loads(l) for l in (run / "records.jsonl").read_text().splitlines() if l.strip()]
    pick = [r for r in recs if r["group"] == "none" and not r.get("exclusion_code")]
    if not pick:
        raise SystemExit("no usable no-group images found")
    rng = random.Random(SEED)
    dups = rng.sample(pick, min(N_DUP, len(pick)))
    items = [(r, False) for r in pick] + [(r, True) for r in dups]
    rng.shuffle(items)
    shutil.rmtree(out, ignore_errors=True)
    (out / "images").mkdir(parents=True)
    manifest, ids = [], []
    for n, (r, is_dup) in enumerate(items, 1):
        sid = f"s{n:03d}"
        im = Image.open(run / r["file"]).convert("RGB")
        if im.height > MAX_H:
            im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
        im.save(out / "images" / f"{sid}.png")
        manifest.append(dict(s_id=sid, image_id=r["image_id"], is_duplicate=int(is_dup)))
        ids.append(sid)
    with open(out / "manifest_PRIVATE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["s_id", "image_id", "is_duplicate"])
        w.writeheader()
        w.writerows(manifest)
    (out / "label_tool.html").write_text(HTML.replace("__IDS__", json.dumps(ids)))
    print(f"{len(pick)} images + {len(dups)} duplicates = {len(ids)} to label. Open {out}/label_tool.html")


if __name__ == "__main__":
    main()
