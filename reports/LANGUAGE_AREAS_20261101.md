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
