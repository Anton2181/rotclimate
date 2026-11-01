# Language and culture areas from below — 1 November 2026

The map's owner asked for culture areas that do not start from the drawn
polities, since the empire is multicultural. They should grow from the land
and be compared with the polities only at the end. Four layers are planned:

1. forager language territories;
2. farming spread from climate-defined hearths;
3. culture areas from related languages within easy travel;
4. a divergence map against the polities.

## Layer 1: forager language territories, the Australia test (not adopted)

**Plan:** `calibration/language_areas_20261101/plan.json`, frozen before
the run. **Script:** `scripts/language_areas_earth.py`.

**The model** follows Gavin et al. (2017, *Global Ecology and
Biogeography* 26: 584–591):
- groups fill empty land;
- the environment caps their density;
- a group splits when it passes a maximum population.

Gavin et al. used rainfall as the cap and reported 406 languages against
407, with R² 0.56 for the richness pattern. Here the cap is FORGE's density
(configuration D) on a 0.5° grid of mainland Australia (2,819 cells). The
split size comes from Binford's Australian groups: the 75th percentile of
their recorded populations, 1,296 people. Nothing is fitted to languages.

**The target** is Glottolog's 369 mainland Australian languages.

| split size | simulated languages | richness R² (2° blocks) | Spearman |
|---|---:|---:|---:|
| 1,296 (Binford's 75th percentile) | 625 ± 29 | 0.267 | 0.40 |
| 1,124 (twice the median) | 722 ± 33 | 0.283 | 0.41 |
| reference: richness from log density (fitted) | | 0.248 | |

FORGE's total for Australia is about 477,000 people, inside the usual
range of pre-colonial estimates (300,000 to 1,000,000).

**Verdict: not adopted.** The adoption rule required a count within ±25 %
of 369 and R² ≥ 0.30. The process model does beat the plain density
correlation (as Gavin et al. found), but it makes too many languages.

Two lessons:
1. **Binford's groups are smaller than languages.** His Australian "groups"
   are often dialect groups or local bands; their median is 562 people,
   while Glottolog's count implies about 1,300 people per language.
2. **History concentrates languages.** Glottolog crowds into Arnhem Land
   and Cape York, home of the non-Pama-Nyungan families. That diversity
   comes from deep history, not density alone.

**The next design** calibrates the split size out of sample: fit it on
another continent's foragers (Glottolog languages over North America's
forager regions), then test on Australia. It also adds a rainfall-capacity
variant, so FORGE can be compared with Gavin et al.'s own cap.

## Layer 1b: split size calibrated on North America, tested blind on Australia (not adopted)

**Plan:** `calibration/language_areas_20261101/plan_1b.json`, frozen before
the run. **Script:** `scripts/language_areas_earth.py --stage 1b`.
**Output:** `output/language_areas_20261101/layer1b.json` and
`layer1b.png`.

The split size is chosen in western and northern North America (6,968
cells at 0.5°, 211 Glottolog languages): the value whose mean simulated
count is nearest 211. It is then applied blind to mainland Australia. The
fill is now frontier-driven: the same rules, run faster.

| density cap | calibrated split size | North American population | Australian languages (369) | richness R² | Spearman |
|---|---:|---:|---:|---:|---:|
| FORGE | 3,000 | 399 k | 251 ± 5 | 0.210 | 0.35 |
| rainfall (fitted on Binford's groups) | 6,000 | 721 k | 137 ± 3 | 0.119 | 0.22 |

**Verdict: not adopted.** The split size does not transfer between
continents:
- **North America:** about 1,900 people per language (FORGE's population
  over 211 languages).
- **Australia:** about 1,300 people per language.

Australia's languages were smaller communities, and FORGE beats rainfall
as the density cap.

Across layers 1 and 1b the richness pattern stays at R² 0.21–0.28, below
Gavin et al.'s 0.56. Part of the gap is the target. Glottolog gives one
point per language, while Gavin et al. counted mapped language areas per
cell, which is a less noisy measure of richness.

**The next design** follows Nettle's ecological-risk hypothesis:
communities are larger where lean seasons are long, because people need
wider networks to share risk. The split size would rise with FORGE's
scarcity days. It would be fitted on North America (count and richness),
then tested blind on Australia.

## Layer 1c: split size rising with lean seasons (Nettle), not adopted

**Plan:** `calibration/language_areas_20261101/plan_1c.json`, frozen before
the run. **Output:** `output/language_areas_20261101/layer1c.json` and
`layer1c.png`.

The split size is N0 × exp(c × (scarcity − 200) / 100), where scarcity is
the group's population-weighted FORGE scarcity days. N0 and c were fitted
on North America: among settings within ±15 % of the 211 languages, the one
with the highest richness R². The search chose N0 = 3,000 and c = 1.0
(184 languages, R² 0.22).

Applied blind to Australia it gives **204 languages (369) and R² 0.17**.
Not adopted.

The North American grid shows why. The richness pattern is matched best by
small groups (R² 0.33 at N0 1,000, c 1), but those give 2.5 times too many
languages. The count needs groups of about 3,000. With Glottolog's
one-point-per-language target, the model cannot match both, and the
lean-season term does not change that. Median lean-season days are 266 in
North America and 227 in Australia, so the term makes Australian groups
larger relative to North America, the wrong direction for Australia's
smaller languages.

**Where layer 1 stands after three frozen tests:**
- **Counts:** right to within a factor of 1.5–1.8.
- **Richness pattern:** R² 0.17–0.28 against Glottolog points. A plain
  density correlation scores 0.25.
- **Density cap:** FORGE works better than rainfall.

None reaches the adoption bar. Two ways forward:
1. **A truer target.** Mapped language territories, not centroid points,
   are what Gavin et al. scored, but no openly licensed polygon set covers
   both continents.
2. **Illustration.** Use layer 1 on the maps to show plausible forager
   language territories, labelled with this Earth performance.

The decision belongs to the map's owner.

## Layer 2: how farming spreads, the European Neolithic test (plain distance wins)

**Plan:** `calibration/language_areas_20261101/plan_2.json`, frozen after
the site table was parsed and before any distance or date was compared.
**Script:** `scripts/farming_spread_earth.py`. **Output:**
`output/language_areas_20261101/layer2/` (`summary.json`,
`layer2_farming.png`).

**The data** are the dated early-farming sites of Pinhasi, Fort &
Ammerman (2005, *PLoS Biology* 3: e410), Supporting Information 1:
- 726 sites of the Near East and Europe with a calibrated date;
- one site (Yarim Tepe I) has coordinates outside the climate window
  (56.8° E for a site in Iraq) and is left out of every model;
- the paper's 37 candidate origins.

**Four models,** each a straight line, date = a − b × distance:
- **M0:** great-circle distance.
- **M1:** the paper's own shortest-path distance.
- **M2:** travel time over terrain (Tobler's hiking function), with sea
  crossings at κ times the flat-land time.
- **M3:** M2, slowed where wheat and barley do badly. The slowdown is
  max(s, 0.05)^β, where s comes from the map's crop rules
  (`scripts/land_people.py`) run on WorldClim's present climate.

The origin, κ and β are fitted on six of seven regional blocks; the
seventh is predicted.

| | M0 distance | M1 paper path | M2 terrain + sea | M3 + crops |
|---|---:|---:|---:|---:|
| **held-out error, years** | **950** | 1,009 | 987 | 1,121 |
| held-out correlation | **0.76** | 0.74 | 0.74 | 0.65 |
| Near East & Anatolia | 1,712 | 1,788 | 1,753 | 2,152 |
| Southeast Europe | 744 | **686** | 765 | 773 |
| Italy | 477 | 553 | 469 | **465** |
| Iberia & France | **766** | 898 | 851 | 923 |
| Central Europe | **769** | 786 | 771 | 774 |
| Britain & Ireland | 514 | 563 | 537 | **512** |
| Denmark & Sweden | **913** | 1,089 | 1,057 | 1,018 |

**Verdict: plain distance.** M3 beats M2 in only 3 of 7 blocks; M2 beats
M0 in only 1. By the frozen rule, layer 2 spreads farming by distance from
its hearths. The crop rules decide only where farming can take root
(s ≥ 0.05), not how fast it gets there.

**The distance model reproduces the paper.** On all sites:
- correlation 0.83 (the paper reports about 0.83);
- speed 1.0 km per year (the paper: 0.6–1.3);
- sea crossings: every fit chooses κ = 1, so the sea is as easy as flat
  land. That matches the fast maritime Cardial spread along the western
  Mediterranean.

The fitted crop exponent was β = 0.5, the Fisher-wave textbook value, in
four of the seven folds. It made no difference.

**What the errors show** (the right panel of the figure):
- **Near East:** farming is earlier than any wave predicts, by about
  1,100 years on average. The core's millennia of pre-pottery Neolithic
  are local development, not spread.
- **Iberia and France:** about 500 years earlier than predicted. This is
  the Cardial maritime leapfrog.
- **Denmark and Sweden:** about 900 years later than predicted. This is
  the well-known stall at the northern edge of the loess.

The crop rules cannot explain the stall. On present climate, wheat and
barley do well in Denmark and southern Sweden. The usual explanation is
people, not climate: the dense, settled Ertebølle fishers held out for
about a thousand years (Zvelebil's availability model).

That points to a FORGE-based follow-up: a wave slowed where foragers are
dense. It was suggested by these residuals, so it cannot be tested on
these sites. It needs an independent spread, such as Yayoi rice into
Jōmon Japan, which stopped short of Hokkaido.

**Limits:**
- present climate, not the early Holocene;
- one spread (west Eurasian wheat and barley);
- the Near East block is extrapolation for every model.

## Layer 2b: where farming starts (not predicted; hearths are the owner's choice)

**Plan:** `calibration/language_areas_20261101/plan_2b.json`, frozen
before any global FORGE run. **Script:** `scripts/farming_hearths_earth.py`.
**Output:** `output/language_areas_20261101/layer2b/` (`summary.json`,
`layer2b_hearths.png`).

**Setup:**
- FORGE configuration D ran on 14,820 one-degree land cells of WorldClim's
  present climate.
- Four indices were tested:
  - **B1:** productivity;
  - **B2:** forager density;
  - **B3:** plant-fed forager density;
  - **H:** Testart's storing plant foragers, plant-fed density × the
    share of the year that is lean.
- Each index is averaged over a 500 km disc around each of Diamond's nine
  homelands of domestication. That mean is compared with 2,000 random land
  discs more than 1,000 km from any homeland.

| homeland (percentile among random discs) | B1 NPP | B2 density | B3 plant-fed | H storing |
|---|---:|---:|---:|---:|
| Fertile Crescent | 55 | 57 | 65 | 66 |
| China | 86 | 85 | 85 | **93** |
| New Guinea highlands | **98** | **98** | 92 | 83 |
| Sahel | 39 | 36 | 45 | 47 |
| tropical West Africa | **89** | **89** | 86 | 75 |
| Ethiopia | **80** | 78 | 77 | 72 |
| eastern United States | **86** | 84 | 80 | 72 |
| Mesoamerica | 85 | 85 | **95** | 94 |
| Andes and Amazonia | **86** | **86** | 77 | 74 |
| **AUC** | **0.78** | 0.78 | 0.78 | 0.75 |

**Verdict: not predicted.** No index reaches 0.80, and H falls below the
plain baselines. By the frozen rule, the fantasy map's farming hearths
are the owner's choice, or farming arrives from beyond the map's edge.

**What it shows:**
- **The homelands are productive land.** Productivity alone places them
  about as well as any FORGE measure: about 78 % of the time a homeland
  outranks a random place.
- **The Fertile Crescent and the Sahel score poorly on present climate.**
  Both were wetter in the early Holocene, which is a limit of the test.
- **Storing plant foragers rank China and Mesoamerica higher, but the
  tropics lower.** New Guinea, West Africa and Amazonia had no long lean
  season.
- **H's strongest false hearths are suggestive.** They include the
  Deccan and Gujarat (19.5° N 74.5° E) and South Sudan. Both are regions
  later argued to be further centres of domestication (Indian millets and
  pulses; sorghum), though neither is on Diamond's list. The others are
  in Hungary, Zambia, Guinea, northern Australia and Madagascar.
- **Productivity's maxima are rainforests:** Borneo, the Solomons and the
  Amazon.

Climate sets where farming *can* go (layer 2's crop rules). It does not
pick out where farming *began*: that took particular wild plants, and on
these tests history.

## Layer 2c: language density from terrain and land-quality variation (adopted)

**Plan:** `calibration/language_areas_20261101/plan_2c.json`, frozen before
the run. **Script:** `scripts/language_density_earth.py`. **Output:**
`output/language_areas_20261101/layer2c/summary.json`.

**The question:** on land where farming can take root, what sets how many
languages a region holds? Two lines of work suggest an answer:
- **Nichols (1992):** open plains are *spread zones*, with few languages,
  each repeatedly replaced. Rugged country is a *residual zone*, where
  languages accumulate.
- **Michalopoulos (2012):** variation in land quality and elevation
  predicts ethnolinguistic diversity.

**Setup:**
- **Crops:** the map's crop rules ran on WorldClim for the whole world.
- **Blocks:** 2,733 two-degree blocks of crop-capable land, holding 6,533
  Glottolog languages.
- **Target:** log(1 + languages per block).
- **Test:** each Glottolog macroarea is predicted from the other five.

| | climate (C0) | + ruggedness | + ruggedness, land variation, land quality (C1) |
|---|---:|---:|---:|
| **held-out R²** | 0.28 | 0.33 | **0.34** |
| Africa (RMSE) | **0.90** | 0.91 | 0.93 |
| Eurasia | 0.59 | 0.58 | **0.57** |
| Papunesia | 1.39 | 1.29 | **1.24** |
| North America | 0.56 | 0.53 | **0.52** |
| South America | 0.92 | 0.86 | **0.84** |
| Australia | 0.58 | 0.58 | **0.56** |

**Adopted.** C1 adds 0.056 to the held-out R² (the bar is 0.05) and is
better in 5 of 6 macroareas; only Africa is worse.

The fitted signs agree with Nichols and Michalopoulos. Each coefficient is
per standard deviation of its predictor:

| predictor | coefficient |
|---|---:|
| warmth | +0.38 |
| elevation variation | +0.14 |
| land-quality variation | +0.13 |
| rain | +0.20 |

Warmth stays the strongest term: this is the tropical diversity gradient.

## On the fantasy map: languages grown from the land, then the polities (preview)

**Script:** `scripts/language_map_preview.py atlases/earth_fit`. **Output:**
`output/language_areas_20261101/fantasy/` (`fantasy_languages.png`,
`fantasy_languages.json`, `fantasy_languages.npz`).

**How the map is built:**
- **Farmland (94 % of the land):** C1, refitted on all Earth blocks,
  predicts language density from the map's own climate (corrected), its
  elevation and its crop rules.
- **Where no crop roots:** FORGE density divided by 3,000 people per
  language. This is layer 1b's split size and is only illustrative.
- **Territories:** each is one random draw. Seeds are placed at that
  density, and each land cell joins the seed it reaches first on foot.
- **Edges:** 20 more draws give the chance of a language edge at each
  place.
- **Polities:** the drawn de jure claims enter only at the end.

**What comes out:**
- **About 130 languages.** 125 are on farmland, and 24 lie on unclaimed
  land, mostly the north.
- **Xšāça, the empire,** covers 1.13 million km² of land and holds about
  48 languages. Its largest language covers 6 % of it, which is about 42
  effectively equal languages. It is multicultural by geography alone,
  before any history.
- **The kingdoms** hold 2–8 languages each: Anušiya Cities about 8, the
  Tribes of the Neck and Kasos about 6, Yu'ež Tokar about 5.
- **The small principalities** hold one or two. Seltar, the 1st Prince
  and Olśkan are close to one language each.
- **Polity borders barely follow likely language edges.** The edge share
  is 0.23 along inland polity borders, against 0.19 over all land. The map
  is low and open: its median elevation is 39 m. So the grown language
  edges have few natural lines to follow, and the drawn borders cut
  across language country rather than enclosing it.

**What this does not yet include:**
- **Language families.** These need the hearths, which are the owner's
  choice.
- **Spread-zone replacement on the open plains.** A large farming or
  herding dispersal would erase the residual pattern there.
- **The polities' own languages of rule.**

## Layer 2d: can the map alone say where farming began? (asked by the owner)

**Plan:** `calibration/language_areas_20261101/plan_2d.json`, frozen before
the run. **Script:** `scripts/farming_hearths_map.py atlases/earth_fit`.
**Output:** `output/language_areas_20261101/layer2d/` (`hearths_map.json`,
`hearths_map.png`).

**Method:**
- **Base rate:** Earth has nine homelands of domestication on 135
  million km² of land, or 0.067 per million km².
- **Productivity weight:** layer 2b's best predictor, productivity
  averaged within 500 km, weights each place by its Earth tercile. The top
  third of Earth's random discs holds 7 of the 9 homelands, a likelihood of
  ×2.1; the middle third ×0.7; the lowest ×0.14.
- **Applied to the map:** the same weights on the map's own Earth-corrected
  productivity.

**Result:**
- **Expected independent hearths on the map: 0.42.** The map has 3.3
  million km² of land, about one fortieth of Earth's, and 85 % of it is in
  Earth's top productivity third.
- **So there is about a two-in-three chance (66 %) that farming arrived
  from beyond the map** rather than starting on it.
- **The map cannot say where a hearth would be.** Nearly all its land
  ranks alike, and productivity is only a weak guide (AUC 0.78). The most
  productive places on large landmasses, at least 1,500 km apart, are:
  1. the wet west coast (35.8° N);
  2. the north edge (48.6° N);
  3. the south coast (29.7° N).

  These are ties more than predictions.

**If farming came from beyond, which side?** This is information, not a
tested rule:
- **Land beyond each edge** (the off-map neighbourhood fitted with the
  climate): south 72 %, east 68 %, north 52 %, southeast 45 %, west 33 %,
  northeast almost none.
- **Latitude:** Earth's homelands lie between 6° S and 37° N, and the map
  spans 28–49° N. Only its southern third is in that belt.

Both point to the **south or southeast** as the natural entry, as Europe
got farming from the Near East to its southeast. The choice stays with
the owner.

## In the atlases

The preview is in all three atlases, and in their hosted copies, as a new
**Languages** topic (`scripts/add_language_layers.py`). It is labelled
illustrative and has three layers:
- **Language density;**
- **Language territories,** one draw;
- **Likely language boundaries,** drawn against the de jure borders.

Each fit uses its own climate: the Earth-corrected one for the Earth fit,
the simulated one for the free and Whittaker fits. The expected counts
are 130, 181 and 144 languages. Language families are not drawn, because
the hearths are the owner's choice.
