# Northern steppe as the sole target — 16 November 2026

The isolated experiment is complete. Open the [map and parameter viewer](../output/northern_steppe_only_20261116/presentation/index.html),
[temperature/rain/Köppen comparison](../output/northern_steppe_only_20261116/presentation/climate_comparison.png),
[seasonal chart](../output/northern_steppe_only_20261116/presentation/target_seasonal_cycle.png)
or [exact world/planet parameter table](../output/northern_steppe_only_20261116/presentation/parameters.csv).

Fitting only the northern painted cold-dry region can make it much colder and
drier. The selected world has **44.94° tilt, 0.843 Earth radii, 96.51% of Earth
starlight and a nearly reversed map north direction**. However, the target
becomes predominantly **cold desert**, and every other painted zone loses fit.
This is a bounded exploratory result, not a uniquely inferred planet or an
adopted climate.

## Exact target and search

The user explicitly requested this isolated climate experiment in parallel with
settlement work, superseding the earlier climate-parking preference for this
experiment. The [plan](../calibration/northern_steppe_only_20261116/plan.json)
was committed in `9abf33e5c` before the search; the exact numerical bounds,
baseline and source identities were frozen in `protocol.json` before fitting.
The runner/protocol were subsequently preserved in `dae38cbf1`.

The sole target is the existing painted **class 2, cold_dry**, in the map's
north-centre, documented in [the preceding diagnosis](NORTHERN_STEPPE_20261115.md).
It is not an Earth analogue or all dry zones. The actual mask is
`grid.inmap & grid.land & (grid.target == 2)`: one connected component, 498 land
cells at ds16. Its existing fuzzy rule is:

```
mean over the sole mask of
sigmoid((18 − annual mean temperature)/1.2)
× sigmoid(−ln(max(rain / Köppen dry threshold, 0.001))/0.18)
```

No other painted class, global accuracy, spill/precision/F1 term or realism
penalty contributes to selection. Other-zone metrics are reported only after
selection. Global physics still couples places: excluding other zones from the
objective does not remove them from heat, wind or moisture calculations.

The bounded CMA-ES search evaluated the unchanged starting world plus eight
generations of twelve candidates: **97 evaluations**, seed 20261116, normalized
sigma 0.18, four workers, no racing, ds64/layout 1. All 97 numerical checks
passed. The best completed point was evaluation 96, with sole-target score
0.992132 versus 0.002501 for the coarse baseline. The run stopped on its fixed
budget, not demonstrated convergence or a global optimum.

Nineteen existing world/planet knobs were free. Terrain tiers, v22 terrain,
painted source maps, shared r44 physical recipe and strict saved solver settings
were fixed. The explicitly free world knobs include cross-equatorial transport
and the EBM latitude/land response scale; they are not fixed in this experiment.
The inherited far-pole-land sentinel −1 stays fixed outside the search space.
The existing perihelion-phase and EBM land-scale bounds were declared in advance.
No Earth reserved pool or new climate-physics fit was used.

## What the fitted planet/world looks like

| Quantity | Published parameter baseline | Steppe-only candidate |
| --- | ---: | ---: |
| Axial tilt | 33.5047° | **44.9411°** |
| Planet radius | 1.000 Earth | **0.843026 Earth**, about 5,371 km |
| Starlight | 1.000 Earth | **0.965126 Earth** |
| Orbital eccentricity | 0.016700 | **0.007933** |
| Perihelion after winter solstice | 13.000 days | **27.935 days** |
| Added greenhouse forcing | 0 W/m² | **−0.11345 W/m²** |
| Spin direction | Retrograde | **Retrograde** |
| Map-centre latitude | 38.5148° N | **39.8340° N** |
| North bearing from map top | −8.8137° | **167.9663°** |
| Cross-equatorial transport coefficient | 1.100 | **0.348525** |
| EBM land-response scale | 1.000 | **1.160153** |

North rotates by about **176.8°**, so the drawn northern region is no longer
geographically north of the map centre. Its latitude range moves from
40.34–46.46° N to **30.16–37.75° N**. This is an allowed world configuration,
not a result with geography/orientation held fixed.

The surrounding-world land fractions also change: north-east 0.0089→0.4616,
east 0.6789→0.7781, west 0.3349→0.8079, north 0.5186→0.5894, south
0.7229→0.9699 and south-east 0.4543→0.2854. Continuation scale changes
687.7→453.4 km and off-map relief 176.0→358.6 m. These are model surroundings
parameters, not reconstructed observations. The full nineteen-row CSV retains
all exact values and bounds.

Tilt is within 0.06° of its 45° upper bound. A single small search with a nearly
saturated fuzzy target cannot identify every planetary parameter independently.
Earth day length, 365-day year, gravity, map scale and calendar remain fixed.
The radius uses the model's existing first-order world scaling with those
quantities fixed, rather than an independently validated planetary structure.

## Finer comparison, with no reselection

The selected candidate and unchanged baseline parameters were each run at
**ds16, surroundings layouts 1/2/3**, with all six strict numerical checks
passing. Results below score the mean climate fields, not the arithmetic mean
of three scores. No replacement winner was chosen after this check.

| Northern target metric | Baseline rerun | Steppe-only candidate |
| --- | ---: | ---: |
| Cold-dry fuzzy membership | 0.01779 | **0.96221** |
| Median annual rainfall | 878.5 mm | **88.5 mm** |
| Median annual temperature | 14.53°C | **10.18°C** |
| Median coldest month | +1.29°C | **−14.52°C** |
| Median hottest month | 33.01°C | **34.50°C** |
| Median rain / dry threshold | 2.577 | **0.2885** |
| Cold steppe, BSk | 0% | **16.87%** |
| Cold desert, BWk | 0% | **80.92%** |
| BSk or BWk | 0% | **97.79%** |

Candidate per-layout scores are 0.9784, 0.9546 and 0.8672; the world surroundings
still matter. This ds16 sensitivity is not native ds8 qualification. The baseline
uses unchanged published parameters at the same new resolution/layout ensemble,
so its rainfall is not claimed to equal the archived native-resolution map.

The current **cold-dry rule accepts desert** and only requires a cool annual
mean, rather than a specified grassland biome or winter temperature. The fit
does produce cold winters, but its very dry interior is mostly BWk, not the
grassland steppe implied by the informal region name. That distinction matters
more than its high fuzzy score. The summer remains hot; the major temperature
change is much colder winters and a wider seasonal range.

As requested, other zones exert no counterweight. Their mean memberships change
from 0.664→0.0239 (cold-wet), 0.358→0.0000063 (warm-wet), 0.597→0.0000236
(Mediterranean), 0.314→0.0000071 (forest/tree), with swamp and hot-dry also near
zero. These are disclosed consequences, not failed constraints added after fitting.

## Independent checks and reproduction

The [numerical review](../output/northern_steppe_only_20261116/review.json) passes
all 97 candidate parameter vectors, bounds, locked coefficients and winner
selection. It independently constructs monthly overlap weights, annual/dryness
statistics, fuzzy membership and BSk/BWk fractions from saved temperatures and
rainfall for all six final runs and both mean climates. Fresh coarse baseline
and winner simulations reproduce their scores. Adversarial changes to every
non-target monthly field leave the sole objective exactly unchanged.

Source/protocol and protected published-asset hashes pass. The presentation
review checks all nineteen exact parameter rows, image/source identities and
local links; maps were visually inspected. A Chromium desktop/mobile check
loads all four images and the nineteen-row table and retrieves the CSV.
The main atlas, published climate, settlement model and production defaults
are unchanged by this experiment.

```sh
# A fresh search directory is required for a new run; existing state resumes:
.venv/bin/python scripts/northern_steppe_only.py --resume
# To reproduce only the declared six final physical runs:
.venv/bin/python scripts/northern_steppe_only.py --compare-only
.venv/bin/python scripts/review_northern_steppe_only.py
.venv/bin/python scripts/render_northern_steppe_only.py
.venv/bin/python scripts/review_northern_steppe_presentation.py
```

Outputs are isolated under `output/northern_steppe_only_20261116/`: all attempted
scores/parameter vectors, exact best parameters, search stop, numerical receipts,
final climate preview and maps. Raw daily members/checkpoint are ignored and
reproducible. Wall-clock timings and completion order in the search log are
execution records, not deterministic scientific predictions.

A useful next experiment would retain the sole region but require **cold steppe
rather than cold desert**, and compare free versus fixed north orientation. That
would answer a different question and needs a new declaration; these results
must stay intact rather than changing the objective retrospectively.
