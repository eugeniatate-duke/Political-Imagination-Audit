# Analysis plan (v1.0, dated 2026-11-22)

Political Imagination Audit. This plan was written **before any image was labeled and before any
result existed**. It is a dated, version-controlled plan with a change log (`docs/DEVIATIONS.md`), not an
externally time-stamped pre-registration (see D0). The first run's images (SD 1.5, template T3n) were
generated and partly viewed before this was written; the second batch's engine and template are chosen by
the D14 rules and filled in below before labeling starts.

Fill in before labeling, then commit: **engine = sdxlfast (SDXL base 1.0, 768x1024, 20 steps) , template = N1 , seeds completed = ______** (D15)

## 1. Question and scope

**Primary question.** In one text-to-image model, when a prompt is held constant except for the group label
and the same random seed is used, does the *depicted person* differ visibly between "a Democrat" and "a
Republican", and is that difference larger than the difference produced by swapping two non-political
group labels?

This audit studies the model's **outputs under explicit prompts**. It does not say what Democrats or
Republicans look like, does not use real people's photographs, and does not build or test any classifier
that infers politics from a face or body. All images are synthetic. What a generated image shows is a
property of the model and the prompt, not of any real group.

## 2. Design

- **Factors.** Label (5): Democrat, Republican, Rotary Club member, neighborhood association member (the
  two non-political controls), and no label. Gender stated in the prompt (woman, man). Group stated in the
  prompt (Black, white, Hispanic, Asian, or none stated = the model's default). Seeds (15 planned).
- **Pairing.** A *block* is one (seed, group, gender). Inside a block only the label changes, so labels are
  compared within block. Blocks that share a seed are not independent (same starting noise), so the
  **seed is the unit of resampling**.
- **Controls.** Rotary versus neighborhood association is the matched non-political pair: it measures how
  much images change when *any* two group labels are swapped. The no-label image shows the model's default.
- **Records.** Every generated image is kept with its exact prompt, negative prompt, seed, model snapshot,
  settings and timestamp. Blank images (safety checker) are logged and excluded from labeling, never
  regenerated. An earlier 750-image run (SD 1.5, template T3n, bowling control) remains in the record as
  run A and is analyzed separately and labeled as such.
- **Stop rule.** Seed-major generation; stop at 12:00 PST on 2026-11-23 (moved from 06:00, D15) or at 15 seeds; analysis uses
  complete seeds only (minimum 8).

## 3. Outcomes

Defined in `docs/CODEBOOK.md` (frozen as v1.0 before labeling) and `scripts/codebook.py`. Annotators and
the automated labeler see only the image. Three **primary** yes/no readings: formal attire (blazer or
button-up shirt), smile with teeth showing, and explicit political symbol (a flag counts anywhere in the
image). Scene categories are exploratory (D16). All other readings (glasses, jewelry, arms crossed, emblems or text, held object, bare
torso, visible distortion, not assessable) are **exploratory**.

Automated labels are validated on 90 blind manual labels by one annotator. A reading enters the primary
family only if agreement passes the gate (kappa >= 0.6, or AC1 >= 0.8 when prevalence is under 10%, and at
least 5 yes and 5 no among the 90). Readings that fail are reported as unreliable, not hand-corrected.

## 3b. Hypotheses

- **H1 (label effect, confirmatory).** For at least one primary reading, the Democrat minus Republican risk
  difference is not zero. Test: exact sign-flip permutation over seeds, Holm-corrected across the primary
  readings that passed the gate, alpha = 0.05. If none is significant, H1 is **not supported**; that is not
  evidence of no effect, because only large effects are detectable (section 5).
- **H2 (beyond the baseline, interval-based).** For a primary reading with a significant H1, the party swap
  changes the image more than the control swap: the 95% bootstrap interval of
  EXCESS = |RD(Dem - Rep)| - |RD(Rotary - Association)| excludes 0. No p-value is computed for EXCESS.
- **H3 (descriptive).** Democrat-versus-Republican differences vary by stated group and by gender. Estimates
  with intervals only; no tests.
- **H4 (descriptive).** Adding any label changes the model's default: each label minus the no-label image.

## 4. Analysis (implemented in `scripts/analyze.py`)

1. Per reading and label pair: risk difference = mean over seeds of (mean over valid blocks of y_A - y_B).
2. 95% interval by seed-cluster bootstrap (5000 resamples). In a synthetic null with 15 seeds this interval
   contained the truth about 91% of the time, so it is somewhat too narrow; report as approximate.
3. p-values only for the primary readings on Democrat minus Republican; Holm correction across them.
4. Missing outcomes ("unclear", or image coded not assessable) are dropped from that reading; a block counts
   only if both images are defined. Blocks used are reported beside every estimate.
5. Quality: blank, not-assessable, visible-distortion and bare-torso rates per label, group and gender.
6. Robustness: the primary table is repeated without blocks that contain a visibly distorted image.
7. Subgroups by group and by gender: descriptive.
8. All images appear in `results/<run>/` tables; exhibit images on the site link back to the full record.

## 5. Sensitivity (`scripts/power_sim.py`; every parameter is an assumption)

Simulated detection rates for the Democrat-versus-Republican test, 10 blocks per seed, seed-level
random effects on the logit scale (sd 0.5 to 1.0), base rate 0.2 to 0.5, 600 simulations per cell:

| True risk difference | 15 seeds, alpha 0.05 | 15 seeds, alpha 0.0125 (4 readings) | 10 seeds, alpha 0.05 |
|---|---|---|---|
| 0.05 | 10 to 14% | 2 to 4% | 4 to 8% |
| 0.10 | 30 to 45% | 14 to 22% | 18 to 29% |
| 0.15 | 67 to 81% | 42 to 61% | 39 to 58% |
| 0.20 | 91 to 97% | 71 to 89% | 67 to 84% |
| 0.30 | about 100% | 99 to 100% | 97 to 100% |

False-positive rate at a true difference of 0 was at or below 4% for alpha 0.05. In plain terms: **effects
smaller than about 15 percentage points will often be missed**, and a non-significant result is not
evidence of no difference. EXCESS has no test and is weaker still.

## 6. Interpreting results

- A difference between labels is evidence of an **association in the model's outputs** under this prompt, not
  proof of harm, intent, or real-world accuracy. The relevant concern depends on context (for example
  stereotyped depictions in generated media, or a model that renders party as a visual shortcut).
- Identical outputs do not establish fairness: the model may differ elsewhere, on other prompts, or in how
  the groups and genders are rendered. Differences by stated group are not claims about those groups.
- A controlled prompt audit cannot show *why*: training data, text-encoder behavior and decoding are not
  inspected. Explanations on the site are labeled hypotheses with literature, not findings.

## 7. Limitations (stated up front)

One model per batch, one prompt template, 15 seeds, coarse US group categories, an English prompt with US
party labels, a constant negative prompt that narrows clothing and style variation, a single human
annotator, an automated labeler with its own biases, and a sample too small for small effects. Images
sometimes show distortions or stock-photo styling; their rates are measured and reported.

## 8. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-22 | First written version. Engine and template filled in after pilot5 (D14). |
| 1.1 | 2026-11-22 | Engine and template filled in (D15). Primary family reduced from four readings to three; scene made exploratory (D16). |
