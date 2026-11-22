#!/usr/bin/env bash
# Unattended chain: pilot5 for both engines, then a SPECULATIVE SDXL main run.
#
#   caffeinate -i bash scripts/run_pilot_then_main.sh
#
# The main run (template N1, 750 images, seed-major, resumable) starts only if the SDXL pilot passes the
# technical gate: all 40 images exist, at least 36 are non-blank, and the mean time is at most 67 s per
# image (D14 rule R4: 750 images in at most 14 hours). Whether SDXL/N1 is actually the right choice is
# decided afterwards by eye (rules R1-R3 in docs/DEVIATIONS.md D14). If it is not, stop the run with
# Ctrl-C; images already made stay in the audit record and are logged as an unselected run.
# Every command is resumable: running this script again skips images that already exist.

python scripts/generate.py run pilot5 --engine sd15tall 2>&1 | tee pilot5_sd15tall.log
python scripts/generate.py run pilot5 --engine sdxl 2>&1 | tee pilot5_sdxl.log

python - <<'PY'
import json, sys
try:
    r = [json.loads(l) for l in open("outputs/pilot5-sdxl/records.jsonl") if l.strip()]
except FileNotFoundError:
    print("GATE FAILED: no SDXL pilot records"); sys.exit(1)
ok = sum(1 for x in r if x["exclusion_code"] is None)
mean = sum(x["generation_seconds"] for x in r) / max(len(r), 1)
print(f"GATE: {len(r)} images, {ok} non-blank, mean {mean:.0f} s/image (limit 67)")
sys.exit(0 if len(r) == 40 and ok >= 36 and mean <= 67 else 1)
PY
if [ $? -eq 0 ]; then
  echo "Gate passed: starting speculative SDXL main run (template N1)."
  python scripts/generate.py run main --engine sdxl --templates N1 2>&1 | tee main_sdxl.log
else
  echo "Gate failed: NOT starting the main run. Send the contact sheets and logs to Claude."
fi
