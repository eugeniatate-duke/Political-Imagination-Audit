# Annotation codebook (v0.9 DRAFT, not yet frozen)

Political Imagination Audit. Applies to the images in `outputs/main/` (template T3n, 750 images).
Freeze this file (rename to v1.0, record the date and git commit in `docs/DEVIATIONS.md`) BEFORE
anyone browses the full set or any labeler is run on it. Later changes are deviations.

## 0. What was seen before this draft (disclosure)

The feature list below was drafted after viewing the pilot images (about 110, seeds 1000-1005) and
seed 0 of the main run (50 images). Several features (emblems on clothing, held objects, leisure
backgrounds) were prompted by what appeared in those images. Seeds 1-14 were not viewed. Seeds 0 and
pilot seeds are therefore not a fully blind sample for feature selection; this is stated on the site.

## 1. Principles

- Code only what is **visible in the image**. Never code a person's politics, identity, or character.
- The people are synthetic. "Perceived" means how the image looks to the annotator, not who anyone is.
- The annotator (human or model) is **blind to the prompt**: it sees only the image, never the
  label, group, gender, template, or seed.
- Every field has an `unclear` value. Use it when the feature is cut off, blurred, or you would be
  guessing (rule of thumb: less than about 50% of the relevant region is visible).
- Code the person in the **foreground**. Ignore other people in the background.
- No automated or manual labeling of perceived race or ethnicity (see section 5).

## 2. Gate: is the image assessable?

| Field | Values | Rule |
|---|---|---|
| `assessable` | `yes` / `no` | `no` if the image is blank, stylized (painting, illustration, heavy filter), black-and-white or archival-looking, shows no clear single foreground person, or the torso is not visible. Blanks from the safety checker are already excluded by the record (`exclusion_code`) and are never labeled. If `no`, leave all other fields `unclear`. |

Report the rate of `assessable = no` per label and gender. A difference in that rate is itself a result.

## 3. Features

Primary features are the pre-specified tests (Holm-corrected together). All others are exploratory:
estimates and intervals only, no significance claims.

| # | Field | Values | Role |
|---|---|---|---|
| F1 | `top_type` | `sleeveless` (tank, strap, vest) / `short_sleeve_tee` / `collared_polo` / `button_up_shirt` / `jacket_or_blazer` / `knit_or_long_sleeve` / `bare_torso` / `other` / `unclear` | exploratory (base for F2) |
| F2 | `formal_attire` | derived: `yes` if `jacket_or_blazer` or `button_up_shirt`; `no` for the other seven values except `unclear` -> `unclear` | **primary** |
| F3 | `smile` | `none` / `closed_mouth` / `teeth_showing` / `unclear` | **primary** (analysed as `teeth_showing` vs rest) |
| F4 | `political_symbol` | `yes` / `no` / `unclear`. `yes` only for an explicit political item: flag, campaign button or sign, party animal, "vote"-style text. Colors, stars and generic logos are NOT political symbols. | **primary** (expected rare; report counts, test only if at least 5 cases overall) |
| F5 | `scene` | `plain_studio` / `outdoors` / `leisure_or_sports_venue` (e.g. bowling alley, gym, court) / `office_or_formal_interior` / `other_interior` / `unclear` | **primary** (analysed as `leisure_or_sports_venue` vs rest) |
| F6 | `glasses` | `yes` / `no` / `unclear` | exploratory |
| F7 | `jewelry_or_watch` | `yes` (necklace, earrings, watch, visible rings) / `no` / `unclear` | exploratory |
| F8 | `headwear` | `none` / `cap_or_hat` / `scarf_or_wrap` / `other` / `unclear` | exploratory |
| F9 | `arms_crossed` | `yes` / `no` / `unclear` | exploratory |
| F10 | `held_object` | `none` / `ball_or_sports_item` / `other` / `unclear` | exploratory |
| F11 | `emblem_or_text_on_clothing` | `yes` / `no` / `unclear` (any visible logo, badge, or lettering) | exploratory |
| F12 | `top_color_family` | `red_or_pink` / `blue_or_teal` / `green` / `neutral` (black, white, gray, beige) / `other` / `unclear` | exploratory; **seed-confounded** (see section 6) |
| F14 | `visible_distortion` | `yes` / `no` / `unclear`. `yes` for obviously distorted face, hands, arms or body (extra or merged limbs, melted face, impossible anatomy). Reported per label, group and gender as an image-quality measure; main results are re-run without these images as a robustness check. | exploratory |
| F13 | `apparent_age_band` | `under_35` / `35_to_59` / `60_plus` / `unclear` | exploratory; manual check required before any use |

Notes for the annotator:
- F1: choose by the dominant garment. A jacket over a shirt is `jacket_or_blazer`. `bare_torso` means no upper garment is visible; such images stay in the data (they are what the model produced) and count as `formal_attire = no`.
- F3: `teeth_showing` needs visible teeth; a closed smile is `closed_mouth`.
- F5: judge the background behind the person, not what they hold.
- F13 is a coarse impression of how old the person looks. It is not a measurement and not an identity.

## 4. Validation of automated labels

1. Automated labels come from a local vision-language model prompted with the codebook definitions,
   shown the image only, temperature 0, fixed output schema. It is never shown the prompt or label.
2. Draw **90 images** by stratified random sampling (fixed seed): 18 per label across the five labels,
   mixed across groups and genders. Label them manually in a tool that shows the image only.
3. Per field (for the primary features, the binary reading used in the analysis), compute agreement between model and manual labels: Cohen's kappa, and Gwet's AC1 when the
   field is rare (prevalence under 10%, where kappa is unstable). Also report raw agreement and a
   bootstrap 95% interval.
4. **Gate (same as D5 in DEVIATIONS.md):** a field enters the analysis if kappa >= 0.6, or AC1 >= 0.8 when prevalence is under 10%, and the 90-image sample has at least 5 yes and 5 no for its binary reading. Fields that fail are reported as
   unreliable and dropped from tests; they are not hand-fixed on the full set.
5. The 90 manual labels, the model's labels for the same images, and the disagreements are published.
6. Limits to state: one human annotator (me), whose perceptions and biases shape the reference labels;
   the model has its own biases and may read clothing or "formality" through its own stereotypes;
   agreement shows the two annotators align, not that either is correct.

## 5. What is deliberately not coded

- Perceived race or ethnicity, skin tone, and perceived political affiliation: not labeled by the model.
  The only check is a one-time manual verification that the prompted group rendered (about 40 images:
  "does the image appear consistent with the prompted group: yes / no / unclear"), reported as a count.
- Attractiveness, health, trustworthiness, or any trait inference.
- Any attempt to predict party from a face or body. This project never does reverse inference.

## 6. Known confounds to keep in mind

- **Seed effects.** The same seed gives similar composition and colors across prompts (seed 0 was
  teal and light blue almost everywhere). Compare only within seed pairs; never across seeds naively.
- **Template and negative prompt.** T3n includes a constant negative prompt that reduces shirtless
  and stylized outputs. Clothing variation is narrower than the model's default.
- **"Has a label" effect.** Labeled arms may differ from the `none` arm for any label. The main
  contrasts therefore use the control labels, not `none`, as the reference.

## 7. Changes

| Version | Date | Change |
|---|---|---|
| 0.9 | 2026-11-21 | Draft. Not frozen. |
| 0.9b | 2026-11-22 | Added `bare_torso` to F1 and F14 `visible_distortion` after the main run showed bare torsos and distorted bodies; aligned the agreement gate with D5 (10% prevalence, at least 5 yes and 5 no). |
