# Predicting where people lived: what the Earth tests say

This report covers the population side track of 23 October 2026. The
research behind it is in
[population_density_research_20261023.md](../research_notes/population_density_research_20261023.md),
and the step-by-step log in
[ITERATION_LOCAL_20261023.md](ITERATION_LOCAL_20261023.md).

The atlases' settlement model (`harvest.models.settlement_fields`) turns
climate into low-input food capacity: crops, herding, clearance, river
access and malaria. That capacity is then occupied at a uniform share. The
question here: how well does that predict where people actually lived
around 1–200 CE, and what is missing?

## Tests

| Test | What it is | Independent? |
|---|---|---|
| HYDE 3.3, 0 and 200 CE, 1° blocks | Historians' country totals spread by HYDE's own suitability weights | Partly. Country totals carry history; the pattern within a country is a model like ours. |
| Han census, AD 2 | 98 commanderies with recorded populations (Zheng & Wu 2026) | Yes: a real count inside one state |
| Roman towns, AD 150 | 1,243 towns with urban features (Hanson 2016, OxREP), 2° blocks | Yes, and never used to choose any setting |
| 11 historical regions | Rome, Han, Parthia, from published estimates | Only the ranking is used |

All scores are rank correlations of density, with tied ranks averaged, plus
the share of people that would have to move to turn one map into the other.

## Results

| Model | HYDE 200 CE | Han AD 2 | Roman towns AD 150 |
|---|---|---|---|
| uniform over land | 0.03 | −0.18 | −0.10 |
| crops only | 0.53 | 0.10 | |
| settlement base (crops, herding, clearance, rivers, malaria) | 0.575 (56 % to move) | 0.29 (56 %) | 0.19 |
| × old cores, straight-line distance, L 800 km | 0.744 (42 %) | 0.82 (45 %) | 0.53 |
| × old cores, travel cost, L 800 km | 0.746 (44 %) | **0.84 (39 %)** | **0.62** |
| HYDE 3.3 itself | | 0.72 (46 %) | 0.64 |

The settings were fixed on Han and HYDE before the Roman towns were opened:

- **Cores:** the four river-valley cradles (Uruk, Memphis, Harappa,
  Zhengzhou) plus Rome.
- **Core term:** exp(−D / L), where D is the distance to the nearest core.
- **Travel cost:** each km costs 2× in forest, plus 1 per km of relief;
  the sea costs the same as land.

![Old cores against HYDE 200 CE](../output/population_cores/cores_vs_hyde.png)

![Han commanderies and Roman towns](../output/population_cores/han_roman.png)

## What this means

1. **Environment sets the ceiling; history sets the share filled.** Inside a
   single state, low-input capacity barely ranks places: 0.29 for Han China,
   0.19 for Roman towns. The share of capacity actually occupied falls with
   distance from the oldest farmed and governed land:
   - about 5× capacity within 300 km of the Central Plain;
   - about 0.17× at 1,300–1,800 km;
   - in Rome's empire, Egypt and Syria at about 1× capacity, Gaul and
     Iberia at about 0.15×.
2. **The core is the old heartland, not the capital.** Adding Chang'an as a
   core lowers the Han score from 0.83 to 0.74. Rome helps because it was
   Italy's heartland.
3. **One scale works across empires:** L ≈ 600–800 km.
4. **Forests and mountains slow the frontier, and the sea does not.**
   - Slow forests halve the remaining overfill of the Han south.
   - Making the sea slow hurts, because Mediterranean shipping tied the
     provinces together.
5. **A history-free rule only half works.** Taking the strongest
   concentrations of irrigable river land in dry climates as cores finds real
   early states on Earth: Mesopotamia, the Nile, the Indus, the Yellow River
   at Taosi, Meroë, Jenné-Jeno, Varanasi. It lifts HYDE (0.575 → 0.67) and
   Han (→ 0.73), but not Rome (0.19 → 0.20). Its western cores lie east of
   the Roman heartland.
6. **What still fails:**
   - the Han south (Hunan and Jiangxi about 4–9× too full);
   - the Mesopotamian alluvium, which was in decline;
   - Siberia's forest;
   - southern India, which is too empty: far from any listed core but dense
     in HYDE.

## On the fantasy map

- The automatic rule's first core falls in the province the campaign calls
  *The Heartlands*, and the second in Old Arǧos.
- **Sheet settlement levels** (2,227 hexes): rank 0.298 for the settlement
  base, 0.334 with five rule cores.
- **The campaign's 151 settlements** follow the settlement base (0.40)
  better than any cored version (0.27–0.31). They were spread over
  farmland rather than crowded into a heartland.

A core term would therefore change the campaign's own picture. It belongs
in the atlas as an option with cores the campaign chooses, such as each
nation's heartland, not as a silent default.

## Measures beyond HYDE, and where they stand

| Measure | Use here | Status |
|---|---|---|
| HYDE 3.3 (population, cropland, pasture) | Consistency test | Done |
| Han AD 2 census polygons (Zheng & Wu 2026) | Independent count inside a state | Done |
| Hanson 2016 Roman towns (OxREP) | Independent test of town density | Done |
| Reba et al. 2016 / Modelski city sizes | Rank-size test of the largest cities | Not yet |
| ORBIS (Roman travel costs) | Check of the travel-cost core distance | Not yet; the cost ratios are noted in the research note |
| GAEZ / Caloric Suitability Index | Alternative capacity input | Research note only |

## Reproduce

```sh
python3 -I scripts/population_cores.py --earth output/land_people/earth/earth.npz \
    --hyde data/cache/hyde33/popc_ce_0.tif data/cache/hyde33/popc_ce_200.tif \
    --shp data/cache/han_ad2/shp/ResearchArea --out output/population_cores/scan.json      # add --travel for travel cost
python3 -I scripts/roman_cities_check.py --xlsx data/cache/hanson2016/cities.xlsx \
    --earth output/land_people/earth/earth.npz --hyde data/cache/hyde33/popc_ce_200.tif \
    --out output/population_roman/ad150.json
python3 -I scripts/plot_population_cores.py --earth output/land_people/earth/earth.npz \
    --hyde data/cache/hyde33/popc_ce_200.tif --shp data/cache/han_ad2/shp/ResearchArea \
    --xlsx data/cache/hanson2016/cities.xlsx --out output/population_cores
```

The data caches under `data/cache/` are untrusted downloads, kept out of
git. Read them only with `python3 -I`.
