# Why would an image model draw a party? Literature notes and site copy (draft v1)

Status: draft, written 2026-11-22 from the full PDFs of four papers supplied by the author:
Ahler & Sood (2018), Rothschild et al. (2018), Steed & Caliskan (2021), Bianchi et al. (2023).
It is not a literature review. Other papers considered earlier in the project are not used here until
they have been read. Nothing here claims that this project is the first of its kind.

## 1. What each paper supports, and what it does not

| Paper | What the authors did | What they report | What it does NOT show for this project |
|---|---|---|---|
| Ahler & Sood (2018), *Journal of Politics* 80(3): "The Parties in Our Heads" | Survey of 1,000 Americans (YouGov, March 2015) asking them to estimate the share of each party's supporters who belong to party-stereotypical groups; MTurk experiments testing alternative explanations and the effect of giving correct information. | Large, systematic overestimates of party-stereotypical groups (for example, 32% of Democrats thought to be LGBT vs 6.3% actual; 38% of Republicans thought to earn over $250,000 vs 2.2%). Misperceptions are widely shared, larger for the out-party, associated with partisan affect, and shrink when correct information is given. | Anything about images or models. It documents what people believe about party composition, not how anything is depicted. |
| Rothschild, Howat, Shafranek & Busby (2018), *Political Behavior*: "Pigeonholing Partisans" | Open-ended survey: respondents listed four words or phrases for each party's supporters. Three samples in 2016 (undergraduates N = 548, MTurk N = 954, national non-probability N = 861); structural topic models. | Top terms for Democrats include liberal, open minded, caring, youth, minorities; for Republicans conservative, rich, white, prejudiced, senior citizens, religious (their Table 1). Many answers match the parties' actual composition; content varies with political knowledge, interest and own party. People who describe partisans mainly through traits show markedly higher affective and ideological polarization. | A causal claim, a current claim (2016 data, convenience samples), or anything visual. Several terms are evaluations (for example "prejudiced", "ignorant") that a portrait cannot show. |
| Steed & Caliskan (2021), FAccT: image representations learned with unsupervised pre-training contain human-like biases | Image Embedding Association Test on two ImageNet-2012 pre-trained models (iGPT, SimCLRv2); replicated 8 documented human bias tests; compared with statistics of online image datasets; small qualitative image-completion case study (10 StyleGAN faces, 8 completions each). | Significant human-like associations in several tests, not all; the authors note that a non-significant test does not mean a model is bias-free and that some tests used under 10 images. In the case study, 52.5% of completions of female faces showed a bikini or low-cut top; for male faces 7.5% were shirtless or low-cut and 42.5% wore suits or career attire. | It is about image representations and completion, not text-to-image generation, not Stable Diffusion, and not political identity. The case study is 10 faces. |
| Bianchi et al. (2023), FAccT: "Easily Accessible Text-to-Image Generation Amplifies Demographic Stereotypes at Large Scale" | Stable Diffusion (plus a look at DALL-E): 100 images per prompt, for example "A photo of the face of [descriptor]", for traits, occupations, objects with and without a continent, nationalities, and counter-stereotype modifiers. Race and gender of generated faces scored by a model-based measure: the nearest CLIP archetype built from Chicago Face Dataset images. | Stereotyped images from prompts with no identity words; for software developers 99% of images were scored "white" vs 56% in the workforce statistics they cite; everyday objects default to North American appearance; counter-stereotype wording did not remove the patterns. The authors deliberately foreground striking examples and qualitative analysis. | No political identities (the main text does not study them). The race and gender scores are a model-based proxy with three race categories, not ground truth. The text I read does not state a Stable Diffusion version, so do not compare their numbers with ours directly. |

Where to check each number: Ahler & Sood, abstract and the "Perceptions of party composition" section;
Rothschild et al., Table 1; Steed & Caliskan, Table 1 and the image-completion case study after it;
Bianchi et al., Sections 2.2 and 2.3 and Figure 4.

## 2. How the papers fit together

1. **Established for people (Ahler & Sood; Rothschild et al.).** Many Americans hold simplified, partly
   inaccurate pictures of partisans, and those pictures relate to how they feel about the other side.
2. **Established for related models (Steed & Caliskan; Bianchi et al.).** Image models trained on web
   images encode human-like associations, and a text-to-image model can produce stereotyped images from
   ordinary prompts, including prompts without identity words.
3. **Open, and what this project asks.** When only the party label in a prompt changes, does a
   text-to-image model draw the person differently? None of the four papers tests this. If
   differences appear, they describe the output of one model under one prompt setup. They do not show
   why (training data, text encoder, image model are all candidates), and they say nothing about what
   real partisans look like.

## 3. Design consequences to state on the site

- Our prompts suppress some outputs (illustration styles, bare torsos). That narrows what the audit can
  see, which matters given Steed & Caliskan's finding of sexualized completions in a different model.
- Like Bianchi et al., we study a publicly available model. Unlike them we show every sample and measure
  with a written codebook and paired seeds, instead of foregrounding striking examples.
- Automated labels are validated against 90 blind manual labels; they are a measurement aid, not ground truth.

## 4. Draft site copy (fill the bracketed result after analysis)

**A picture in the head.** Ask Americans what a typical Democrat or Republican is like and they answer
quickly. Surveys find these pictures are simplified, and sometimes far off: in one study people guessed
that about a third of Democrats are gay, lesbian or bisexual (about 6% are) and that nearly four in ten
Republicans earn over $250,000 a year (about 2% do). Those pictures are not harmless: the more people
think of the other side through traits, the more they dislike and distrust it.
*(Ahler & Sood 2018; Rothschild et al. 2018. These studies are about people, not about AI.)*

**Models learn from our pictures too.** Image generators are trained on huge collections of pictures
and captions from the web. Researchers have found that such models can pick up human-like
associations, and that ordinary prompts, with no mention of race or gender, can produce stereotyped
people. *(Steed & Caliskan 2021; Bianchi et al. 2023. Neither tested political identity.)*

**So we asked.** We gave one image generator the same request again and again and changed one word:
"a Democrat", "a Republican", two non-political group labels, or no label. Same seed, same setting
words, same everything else. [One sentence on the result goes here: what differed, what did not, and how
sure we are.]

**What this does not tell you.** These people are synthetic. They are not what Democrats or Republicans
look like, and a difference here would not show why the model behaves this way. It would show an
association in one model's output.

## 5. Wording rules

- Say "the image generator drew" and "association in the output". Do not say "the AI thinks" or "Republicans look like".
- Mark every statement as Established (cited), Hypothesis, or Our result.
- Use "association" for what we measure. Use "stereotype" only when comparing to the human literature, and say it is an interpretation.
- "No difference detected" is not "no bias". Say how large an effect the design could detect.
- Always label generated people as synthetic and link any shown image to the full results.
