# Results

Run: `main-sdxlfast` (SDXL base 1.0, template N1, 750 images, 15 seeds, codebook v1.0).
Numbers below are copied from `results/main-sdxlfast/` and from the site's results table. Intervals are 95%
seed-cluster bootstrap intervals; differences are in percentage points (pp) of images showing the feature.
**Status: final. The main run, the exploratory analyses and the replication (seeds 15-29) are complete.**

## 1. Labeling quality (agreement with 90 blind manual labels)

| Main test | Both defined | Kappa | AC1 | Gate |
|---|---|---|---|---|
| Formal attire | 76 | 0.69 | 0.77 | passed |
| Smile with teeth | 73 | 0.96 | 0.98 | passed |
| Political symbol | 76 | 0.30 | 0.88 | **failed** (manual prevalence 13%, above the 10% limit for the AC1 route) |

14 of the 90 validation images were judged not assessable (illustrated, no clear single person, or torso not visible);
the automated labeler agreed on this (kappa 0.91). Political symbol was therefore demoted to an estimate with no p-value,
as DEVIATIONS D5 requires. It was not relabeled to rescue it.

## 2. Main tests: Democrat minus Republican

| Feature | Difference (pp) | Interval | Holm p | Non-political baseline (Rotary minus association) |
|---|---|---|---|---|
| Formal attire | -1.0 | -7.4 to +5.8 | 0.84 | +22.7 (13.0 to 33.7) |
| Smile with teeth | +6.4 | -0.7 to +12.7 | 0.28 | +12.7 (8.6 to 17.0) |
| Political symbol | +1.4 | -2.0 to +6.4 | not tested | +3.6 (0.7 to 7.1) |

Reading: this design did not detect a Democrat-versus-Republican difference in any of the three features. The intervals
are wide, so only large differences are ruled out. "Not detected" is not "no difference".
The baseline matters: swapping Rotary Club for neighborhood association moved formal attire by about 23 pp, while
swapping Democrat for Republican moved it by about 1 pp. The method can see a label effect when one exists.

## 3. Each label compared with no label (descriptive; `vs_none.csv`)

- Formal attire: Democrat +16.0 pp (4.3 to 26.4), Republican +16.3 (2.7 to 29.3), association -14.3 (-24.3 to -4.3).
- Smile with teeth: every label raises it (Democrat +44.5, Republican +35.6, Rotary +55.6, association +43.5).
- Political symbol: Democrat +11.0 (0.0 to 27.3), Republican +9.4 (0.0 to 25.5), Rotary +3.6, association 0.0.

Caution: the no-label prompt also lacks the phrase "who is", so "label versus no label" mixes the label with a
wording change. Compare labels with each other, not with the baseline, for claims about politics.
Both parties move formal attire and political symbols in the same direction by similar amounts.

## 4. Exploratory, after the main results were seen (DEVIATIONS D17)

15 exploratory features, no significance claims. Two passed the agreement check and have intervals above zero:
glasses +6.4 pp (2.7 to 10.0) and jewelry or watch +8.3 pp (2.4 to 14.5) for Democrat. With 15 features,
a few intervals away from zero are expected by chance. Treat as leads. Features that failed agreement are not discussed.

Stated group and gender: Democrat-minus-Republican differences by stated group are small and the intervals wide.
The gap in smile difference relative to white is positive for Asian (+15.4 pp, 3.9 to 28.6), Black (+15.4, 0.0 to 31.8) and
Hispanic (+11.5, 0.0 to 25.0), but with 21 comparisons about one interval is expected to exclude zero by chance.
No evidence of a stated-race-by-party interaction that I would call robust.

Apparent age, no group stated (25 to 28 images per label with a defined age): the organization labels draw older-looking
people (60 plus: association 100%, Rotary 86%) than the party labels (Democrat 30%, Republican 15%). Democrat and
Republican are not distinguishable. The no-label prompt draws the youngest (28% under 35).

## 5. Apparent skin tone, no group stated (DEVIATIONS D17, D18)

**First pass (seeds 0-14, one annotator, blind, 3 bins).** Share of images judged light / dark:
Republican 88.5% / 0%; Democrat 44.4% / 18.5%; Rotary 53.8% / 0%; association 7.7% / 73.1%; no label 8% / 12%.
Democrat minus Republican, paired by seed: dark +21.4 pp (6.7 to 39.3), light -46.4 pp (-57.7 to -33.3),
mean tone score +0.68 (0.43 to 0.96). Test-retest agreement on 20 duplicates: kappa 0.86.
Absolute shares are not meaningful (they depend on one annotator's bins); the ordering across labels is the result.

**Replication (seeds 15-29, 150 new images, no group stated, same prompts and settings).** Prediction written before generation (D18): same sign, interval excludes zero. **It held.**
Share of images judged light / dark: Republican 75.9% / 0%; Democrat 53.6% / 25.0%; Rotary 86.7% / 3.3%; association 6.7% / 80.0%; no label 3.4% / 3.4%.
Democrat minus Republican, paired by seed: dark +26.7 pp (13.3 to 43.3), light -20.0 pp (-36.7 to -6.7), mean tone score +0.47 (0.23 to 0.73).
By stated gender: women +0.64 (0.29 to 1.00), men +0.29 (0.00 to 0.71). Test-retest on 20 duplicates: 20 of 20 labels repeated.
The effect is smaller than in the first pass, as expected when a result is first noticed after the fact. The organization labels also replicated in order: association mostly dark-looking (73%, then 80%), Rotary mostly light-looking (54%, then 87%).
Absolute shares move between runs and are not meaningful on their own; the ordering across labels is the result.

## 6. What this does and does not show

- It shows what this model draws under these prompts. In the no-race-stated arm, the party label and the
  organization labels are associated with different apparent skin tone and age.
- It does not show why (training data, text encoder, sampler), whether any difference harms anyone, or anything
  about real partisans.
- One model, one template, 15 seeds per cell, one annotator, coarse bins. Only large differences are detectable.
