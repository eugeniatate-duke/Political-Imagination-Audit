# Deviations log

This file records every change from the project's original plan (see D0), plus the decisions made along the way. Each entry gives the date, what changed, why, and what it costs scientifically. Entries D0 to D11 were written **before the first main run** (SD 1.5, template T3n); D12 and D13 after it; D14 before the second batch.

Purpose: a reader can separate what was planned from what was decided after seeing data. If a choice is not in `docs/ANALYSIS_PLAN.md` or in this file, it was not made before the analysis. References below to "section N" or "H1-H6" point to the original v0.1 draft, which is not in this repository (D0).

## Status of the original plan

- **D0 (rewritten 2026-11-22).** The project began with a v0.1 plan drafted 2026-10-19 in conversation. **That draft is not in this repository and was never committed**, so it has no external timestamp and its text cannot be inspected here. The analysis plan is therefore written down in `docs/ANALYSIS_PLAN.md` (dated 2026-11-22), after the first run's images were generated and partly viewed, but before any label, agreement figure or result existed. This project is **not** a time-stamped pre-registration; it is a dated plan with a change log. Data seen before the first main run: the 20 benchmark images (2026-10-19), pilot (36 images), pilot2 (24) and pilot4 (24), all with pilot seeds (1000 and above), which are never used in the main analysis; plus seed 0 of the first main run (50 images), which I viewed before launching the remaining seeds and which IS part of that run's data (see D10).

## Design changes (reason for all: submission and poster day is 2026-11-24, 8:00 am PST; the project was compressed to fit about 2.5 days)

- **D1. Sample size and templates. SUPERSEDED by D8 and D9.** The original compressed plan was 30 seeds x 2 templates (T1, T2) x 2 genders x 5 labels = 600 images, dropping template T3 and the unanchored T0 arm. T1 and T2 were then dropped (D8) and the group factor was added (D9). The sensitivity simulation in section 8 of the pre-registration does not apply to the final design; `scripts/power_sim.py` must be re-run with the final block counts before any power statement is reported.

- **D2. Pilot size.** Pilots are small by design: pilot (36 images: no-label on T1 and T2, 6 seeds; plus Democrat and Republican on T1, 3 seeds), pilot2 (24: T2u and T3u, no label), pilot4 (24: T3n and T7, no label), versus the 120 planned. They check only that a template produces contemporary color portraits. They do not set the number of seeds (fixed at 15 by the deadline and generation time) and are not used to estimate annotation speed. Pilot decisions used no-label images only.

- **D3. Annotation: automated labels are primary.** The pre-registration made blind manual coding primary. Instead, a local vision-language model labels every image from the image alone (it never sees the prompt, label or condition), and I hand-label **90 images** drawn at random from the main run, blind to condition, to measure agreement per feature.
  *Cost:* the labeler has its own biases and errors, 90 labels give only rough agreement estimates, and I am not a neutral rater. Results are claims about this labeler's reading of the images, validated on a small sample. Section 7 items 1 to 6 are otherwise replaced by this procedure.
  *Order of operations (to limit researcher freedom):* (1) freeze the codebook; (2) hand-label the 90 validation images and label all images automatically; (3) compute agreement per feature; (4) fix the primary feature list using agreement only; (5) only then compute any difference between labels.

- **D4. No self-agreement relabel.** Section 7 item 3 (re-code 15% at least 7 days later) is impossible in the time available. Replaced by the manual-versus-automated agreement in D3.

- **D5. Primary feature gate.** Section 4.4's filter (at least 5 yes and 5 no among 100 pilot images) cannot be applied to a 36-image pilot. Replaced by: a feature enters the primary family only if manual-versus-automated agreement on the 90 validation images is kappa >= 0.6 (or Gwet's AC1 >= 0.8 when prevalence is under 10%), and it has at least 5 yes and 5 no in the validation sample. Other features are reported as exploratory. For multi-valued fields the gate applies to the binary reading used in the analysis.

- **D6. Tier 3 dropped.** The LLM-rewriting pipeline arms (H6) will not be run. Mentioned only as future work.

- **D7. Tier 2 status.** Not run as of 2026-11-22. If it is run later, it will be labeled exploratory in all outputs and logged here.

- **D8. Template selection (2026-11-21).** Pilot: T1 failed the era check (no-label images looked like old photographs); T2 passed on era but often showed bare shoulders. Pilot2: T2u and T3u both failed (judged by eye from contact sheets: roughly 3 to 5 of 10 and 5 to 6 of 9 usable among non-blank images; 5 of 24 blank, concentrated on seeds 1001 and 1002 for women). The eligibility rule in D2 (at least 11 of 12) could not be met when 2 to 3 of 12 were blank, so I restated it as proportions **before seeing pilot4**: among non-blank no-label images, at most 1 failure (stylized, archival, or not one person) and at least 75% showing clothing on the torso; blanks are reported separately, not gated. Pilot4 added a constant negative prompt to every arm: `painting, illustration, drawing, sketch, vintage, antique, sepia, black and white, shirtless, nude, naked, deformed, disfigured`. Result: 0 of 24 blank; T3n 11 of 12 clean; T7 also 11 of 12 clothed but about 4 of 12 drifted from portraits (action poses, cropped heads). **T3n selected**: `A recent color portrait photo of {person} who is {label}, upper body.` (no-label form: `... of {person}, upper body.`).
  *Cost:* the negative prompt narrows clothing variation (it suppresses bare torsos and stylization), so results describe "Stable Diffusion 1.5 under this prompt setup", not the model's unconstrained behavior. One template means paraphrase stability (H2) is not tested in the main run.

- **D9. Demographic-group factor (2026-11-21).** Main run: 4 groups stated in the prompt (Black, white, Hispanic, Asian) x 2 genders x 5 labels x 15 seeds, one template (600 images), plus a default arm with no group stated (150 images) = **750 images**, supersedes D1's sample size. Reason: to test what the model draws by default for each label, and whether label effects differ by specified group.
  *Cost:* about 30 paired images per group x label cell, so group-specific effects are detectable only if large; the groups are coarse US categories that omit many people. The group is a prompt input, not a claim about anyone's identity; how outputs look is a perception. Perceived race is not labeled automatically; a manual check of about 40 images confirms that the prompted groups rendered, reported as a count.

- **D10. Codebook drafted after seeing some images (2026-11-21).** Codebook v0.9 was drafted after I viewed the pilot images and seed 0 of the main run (about 160 images); seeds 1 to 14 were not viewed. The feature list is therefore not fully blind for those images. Primary features (Holm-corrected together): formal_attire, smile (teeth showing), political_symbol, scene (leisure or sports venue). All others are exploratory.

- **D11. Observed-pattern caveat (2026-11-21).** In seed 0, Democrat and Republican images looked near-identical for most pairs while control labels (bowling, Rotary) changed images visibly. This was seen before analysis. The pre-registered contrasts (political versus control labels) are unchanged; no wording was altered to enlarge a label effect.

## After the first main run

- **D12. Main run completed (2026-11-22, written after the run).** 750 of 750 images generated, 15 seeds complete, 0 missing files, fp16 on Apple MPS, 2.84 h. 2 images (0.3%) were blank from the safety checker (seed 6, seed 11; one Democrat and one no-label, both men); both are logged and excluded from labeling, not regenerated. The run's `model_snapshot` field recorded "unknown" because the hash lookup failed at run time; the snapshot hash read from the local cache after the run is `451f4fe16113bff5a5d2269ed5ad43b0592e9a14` (assumes the cached weights were not changed during the run).

- **D13. Codebook v0.9b (2026-11-22, after the main run, before any labeling).** Added `bare_torso` to `top_type` and a `visible_distortion` field, because the generated images include bare torsos and distorted anatomy that the v0.9 fields could not record. Both additions were prompted by my looking at some images from the main run. Images with these features stay in the data; `visible_distortion` is reported per label, group and gender, and main results are re-run without those images as a robustness check. The agreement gate wording in the codebook was aligned with D5.

- **D14 (2026-11-22, before pilot5 was judged).** Second batch. The first run (SD 1.5, 512 px, T3n) showed bare torsos, distorted bodies and bowling props and did not depict people in everyday settings. Changes: (a) new templates N1 and N2 with negative prompt v2 (adults, fully clothed, whole person, everyday setting; text, logos and symbols are not suppressed); (b) the bowling control is replaced by "a neighborhood association member", an abstract affiliation matched in kind to a party label (Rotary stays); (c) pilot5 (40 images per engine) compares SD 1.5 at 512x768 and SDXL base 1.0 at 832x1216 (30 steps, guidance 5.0). Template and engine are chosen by these rules only, not by Democrat-versus-Republican differences: R1 at least 80% look like real photographs with no obvious anatomical distortion; R2 at least 90% fully clothed; R3 at least 70% show an everyday setting; R4 projected time for 750 images at most 14 hours. If both engines pass, SDXL; if one passes, that one; if neither, the higher R1 with the shortfall reported; N1 unless it fails R3 and N2 passes. (d) Stop rule: seed-major; stop at 06:00 PST on 2026-11-23 or at 15 seeds; analysis uses complete seeds only (minimum 8). (e) The 750-image T3n run stays in the audit record as run A (SD 1.5, bowling control). (f) To use idle machine time, an SDXL/N1 main run starts automatically if the SDXL pilot passes a technical gate (40 images, at least 36 non-blank, at most 67 s per image) BEFORE R1-R3 are judged by eye; those images are used only if the rules select SDXL/N1, otherwise they stay in the record as an unselected run.
  *Cost:* these changes followed my looking at first-run images (for realism and content reasons, not label differences), and the new batch has no strong positive control (bowling remains in run A).

## D15: Second-batch engine selection (2026-11-22)

- Pilot5 timings: SD 1.5 tall 27.2 s/image (40 images, 0 blank); SDXL 832x1216, 30 steps 148.4 s/image (7 images), fails R4 (gate 67 s); SDXL fast 768x1024, 20 steps 48.8 s/image (10 images, 0 blank), passes R4.
- The sdxlfast setting was added after the full-size timing was seen. It was not in D14.
- R1-R3 were judged by eye from contact sheets at thumbnail size, not formally counted.
- Decision: under D14 (both engines pass, so SDXL), run main with engine sdxlfast, template N1, 15 seeds. The speculative-start script was never used for main.
- Stop rule changed from 06:00 Mon to 12:00 Mon because the project deadline is Tue 08:00 and projected generation time is about 10.2 h. Complete seeds only; minimum 8 unchanged.
- N2 as a paraphrase arm is undecided and will get its own entry if run.

## D16: Codebook v0.9c and primary family (2026-11-22)

- Seen before this change: about 100 images from seeds 0-7 of main-sdxlfast (five contact-sheet pages).
- Changed: F5 scene categories rewritten for everyday settings; the scene reading removed from the primary family (it was built for the first run's bowling control and no leisure or sports setting appeared); primary readings are now formal_attire, smile_teeth, political_symbol, Holm over at most three. F4: flags count anywhere in the image. F11: badges, name tags and lanyards count.
- Effect of the change: a smaller Holm family is slightly less conservative.
- Observed before labeling, not tested: illustrated or poster-style images concentrated in seed 7 (handled by assessable = no); flags in Dem and Rep images in the same seeds but not in the Rotary or association images seen. Any test of these is post hoc.


Codebook v1.0 was frozen in commit 4e7850d (branch feat/annotation-and-exhibit, merged to main) on 2026-11-22, before any labeling.

## D17 (2026-11-23): post hoc exploratory analyses after the main results were seen
Main results (analyze.py) were viewed at about 08:25. Afterwards, three exploratory analyses were added that were not in
docs/ANALYSIS_PLAN.md: (a) Democrat-minus-Republican by stated group and gender and apparent age by label
(scripts/explore_by_group.py); (b) apparent skin tone in the no-group arm (scripts/make_skintone_set.py,
scripts/analyze_skintone.py): 150 images plus 20 duplicates, labeled blind by one annotator in three bins (light, medium, dark,
unclear), finished about 09:20. The Democrat-vs-Republican contrast was named before labeling. Result: Republican 88.5% light
vs Democrat 44.4%; Democrat minus Republican on mean tone score +0.68 (95% seed-bootstrap interval 0.43 to 0.96). Own
test-retest agreement kappa 0.86 on 20 pairs. No p-values; exploratory.

Democrat minus Republican on apparent skin tone, no race stated:

	Dark	Light	Mean tone score	Blocks used
Women	+38.5 pp (13.3 to 64.3)	−69.2 pp (−92.3 to −41.7)	+1.08 (0.67 to 1.46)	13 of 15
Men	0.0	−23.1 pp (−46.7 to 0.0)	+0.23 (0.00 to 0.47)	13 of 15
women +1.08, 0.67 to 1.46; men +0.23, 0.00 to 0.47 

## D18 (2026-11-23, [time]): replication run, written BEFORE generating
New mode `replicate` in scripts/generate.py: seeds 15-29, no-group arm only, engine sdxlfast, template N1, same negative prompt
and settings as the main run (150 images, folder outputs/replicate-sdxlfast). Prediction (stated before seeing any
image): in the replication, Democrat minus Republican on mean skin-tone score has the same sign as in D17 and the interval
excludes zero. If not, the D17 result is reported as not replicated. Labeling will again be blind, with 20 duplicates.

Added before labeling the replication (2026-11-23, [time]): secondary prediction, from the first-pass by-gender
table (women: Democrat minus Republican mean tone score +1.08, interval 0.67 to 1.46; men: +0.23, interval 0.00 to 0.47).
In the replication, the women's contrast has the same sign with an interval that excludes zero; the men's contrast
has the same sign and a smaller magnitude. If the women's interval includes zero, the first-pass result is not replicated.

## D18 outcome (2026-11-23, [time])
Replication (seeds 15-29, 150 images, labeled blind with 20 duplicates, duplicates agreed 20 of 20): Democrat minus Republican
mean tone score +0.47 (95% seed-bootstrap interval 0.23 to 0.73); dark +26.7 pp (13.3 to 43.3); light -20.0 pp (-36.7 to -6.7).
Women +0.64 (0.29 to 1.00); men +0.29 (0.00 to 0.71). Both predictions held: same sign with an interval excluding zero overall and for women;
men smaller. Effect sizes were smaller than in the first pass (+0.68 overall, +1.08 for women), the usual pattern for a result
first noticed after the fact. Apparent skin tone is one annotator's impression of synthetic images; absolute shares are not stable across runs.
