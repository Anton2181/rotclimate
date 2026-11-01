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
