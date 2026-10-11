# rotclimate: a climate simulator for a hand-drawn world

A physically based seasonal climate model for a 2287 × 1058 mile hand-drawn
map (pointy-top hexes with 15-mile sides). The model reads the map's layers (coast, height tiers, rivers, place
names) and runs a year of weather in 73 five-day weeks on the local calendar.
A calibrator then searches for what the map doesn't say — latitude, axial
tilt, spin direction, how high the tiers are, and what lies beyond the edges —
until the simulated climate reproduces the painted target zones.

## Results

**Interactive atlas:** https://claude.ai/artifact/BMvofWDzswrdCgSBkHnNRf (private until you share it).
Zoomable map layers (Köppen, your zones, the simulated climate in your zones, match accuracy,
temperatures, precipitation). Click any place for its climograph in the local calendar and its
closest real cities. Search a town on the map, or a real city to see outlined where on the map
feels like it (the magnifier button shows or hides the search box). The copy button puts the
current view (zoom, outlines, names and all) on the clipboard as an image. Your settlement markers
(`data/source/settlements.png`, lossless) are drawn as vector pixel art, every pixel an exact square,
so they stay sharp at any zoom; the "Towns and names" toggle shows them with the place names.

In the simple-zones map, land that fits none of your seven zones is named for what it is:
*Mountain* (cold highland: above ~2,200 m or summers below 15 °C), *Grassland* (a semi-dry margin
between the wet and dry zones) or *Transitional* (humid, but between two zones' rules).

![The calibrated climate in your simple zones](output/simulated_zones.png)

![Köppen map](output/koppen.png)

### What the world must be like (best calibration, round 17)

| unknown | best fit |
|---|---|
| spin | **Earth-like**, narrowly, on the fit score (see below) |
| latitude | 29.4°N to 44.7°N (centre 37.1°N) |
| axial tilt | 17.0° (Earth 23.4°) |
| height tiers | lowland ≤ 51 m, hills ≤ 251 m, upland ≤ 564 m, peaks to 2,697 m |
| land beyond the map | north-west 98%, north-east 64%, west 35%, east 34%, south-west 25%, south-east 61% |

**Spin: the verdict has flipped, and it is close.** Until round 15 reversed spin led
(0.427 against 0.421). A literature review (`reports/Climate simulator improvement literature.md`)
then turned up two things. First, the score alone could not separate the spins: re-scored on
surroundings the search never saw, the gap shrank to 0.004 with an uncertainty range that
included zero. Second, reversed spin was getting its fit partly from **summers no wet place on
Earth has**. On Earth, where the warmest month brings 80 mm of rain or more, the lowland passes
30 °C on only 2.8% of the land; the reversed-spin world did so on about half of it (swamp 32.6 °C,
against 28–29 °C on the Gulf Coast). The model now lets wet ground spend summer sunshine on
evaporation (physics v8), the score penalises humid summers hotter than Earth's, the swamp rule
needs a hot year as your legend says, and both spins search the same physically set box.

Each spin was then recalibrated on equal terms and its three best candidates re-scored on 60
fresh surrounding worlds, with a ±0.01 "tie" band declared in advance:

| | reversed spin | Earth-like spin |
|---|---|---|
| round 16 (fit score on 60 fresh worlds) | 0.394 | **0.422** |
| round 17, sea and land offsets held within ±2 °C | 0.390 | **0.417** |
| round 17 gap (95% range) | | −0.040 to −0.013 |
| round 17 painted land in its own zone | **51.1%** (ahead on 46 of 60 worlds) | 47.7% |
| warm-wet west coast (F1) | **0.56** | 0.51 |
| swamp / forest (F1) | 0.32 / 0.39 | **0.40 / 0.48** |
| world it needs | 26.7–42.0°N, tilt 20.8° | 29.4–44.7°N, tilt 17.0° |

By the test fixed in advance (the fit score on fresh worlds) **Earth-like spin wins**, and the
atlas now shows that world. But the two spins fail differently. Reversed spin gets more of your
painted land right and is the only one that makes the big west coast warm and wet, while it
sacrifices part of the swamp and the hot-dry south-east. Earth-like spin matches every zone a
little, but gives the west coast the dry summers Earth gives every west coast at 30–45°
(California, the Mediterranean), so the painted warm-wet coast reads as Mediterranean. The
reversed-spin pattern (a mirror-image North America) is the one a full Earth-system model gives
for a retrograde Earth (Mikolajewicz et al. 2018); the fit score prefers the Earth-like
compromise. Both parameter sets are kept: `calibration/round17_earthlike.json` (published) and
`calibration/round17_retrograde.json`. (A southern-hemisphere map with south at the top would
behave like the reversed spin.)

### Match with the painted zones (14 km render, round 17, Earth-like spin)

Each zone is judged two ways. **Coverage**: how well the painted area meets the zone's climate
rule (0–1). **Precision**: how much of the rule's area lies inside its own painted zone, rather
than spilling into areas painted as something else (ridges above 1,500 m don't count as spill;
a broader zone may hold inside a narrower one it contains, as forest inside swamp). **F1**
balances the two. *Correct* is the share of painted land whose single best-fitting zone is its own
(a place meeting the swamp rule counts as swamp).

The swamp rule asks for a hot, very wet climate **on flat ground** with a **hot year** (mean
annual above ~21 °C): your painted swamp gets the same rain as the warm-wet coast but is about
five times flatter (median slope 0.7 vs 3.4 ‰), and waterlogged lowland is what makes a swamp
(Everglades, Pantanal, Gulf Coast bayous). Heat is what the legend's "Hot and wet" adds to
"Warm and wet"; drainage measures from the wetland literature can't tell the two apart on four
flat height tiers.

| zone | coverage | precision | F1 | correct |
|---|---|---|---|---|
| Cold and wet | 0.37 | 0.24 | 0.29 | 44% |
| Cold and dry | 0.48 | 0.74 | 0.58 | 75% |
| Warm and wet | 0.42 | 0.66 | 0.51 | 0% |
| Mediterranean | 0.67 | 0.38 | 0.48 | 93% |
| Hot and wet, swampy | 0.45 | 0.46 | 0.45 | 47% |
| Tree (forested) | 0.83 | 0.31 | 0.45 | 40% |
| Hot and dry | 0.39 | 0.52 | 0.45 | 38% |
| **overall** | **0.51** | | **0.43** (objective) | **51%** |

(it00, the Earth-like first guess: coverage 0.17 and 9% correct.)

Where it still falls short:
* **The warm-wet west coast** is humid enough (precision 0.66) but its summers are dry, so the
  Mediterranean rule fits it better everywhere: with Earth's spin a west coast at these
  latitudes sits under the summer subtropical high. Reversed spin fixes this coast and loses
  elsewhere (see above).
* **Mediterranean and forest** climates spill beyond their painted bands (precision 0.38 and
  0.31), and **cold-and-wet** climate reaches into hills painted as other zones.
* Humid summers are now Earth-like in most places (9% of the wet-summer lowland passes 30 °C,
  against 2.8% on Earth and about 50% before).

The maps are simulated on 14 km cells, the same grid rounds 11–17 were calibrated on. Since the
time-step fix (see `docs/ITERATIONS.md`), the calibration's 25 steps a year and the maps' 73 give
the same climate. All map layers are drawn at 3× resolution with full-detail terrain.

### Maps and GIFs (`output/`)

`simulated_zones.png` · `koppen.png` · `comparison.png` · `world_context.png` · `temperature_*.png` ·
`precipitation_annual.png` · `atlas_temperature.png` · `atlas_precipitation.png` ·
`climographs.png` (with "feels like" cities) · `insolation.png` · `year_temperature.gif` ·
`year_precipitation.gif` · `spin_flip.gif` · `tilt_sweep.gif` · `surroundings.gif` · `improvement.gif`

![A year of temperature and wind](output/year_temperature.gif)

**Real-world analogues ("feels like").** The reference set is every city of 50,000+ people and
every national capital (GeoNames; suburbs within 15 km folded into the bigger city): 8,468
cities. Each has monthly normals from WorldClim 2.1 (1970–2000), corrected to the city's own
elevation. Another 472 official WMO weather stations cover remote places no city does
(mountains, islands, polar and desert outposts). Checked against the official WMO station
normals for 1,262 cities with a station within 10 km, the monthly temperatures differ by a median
of 0.54 °C (90% under 1.24 °C) and annual rainfall agrees to within ±20% for 80% of them.

Both the map place and each real place are reduced to 12 months aligned on the winter solstice
(southern-hemisphere places shift half a year). Then

    d = RMS(monthly temperature difference) / 2.5 °C + RMS(difference of √monthly rain) / 2
    match % = 100 · e^(−d/2)

so 100% is identical, and every 2.5 °C off in a typical month (or rain off by 2 √mm, e.g. 100 vs
144 mm) multiplies it by 0.61. The temperature term compares **daily highs and lows**, not just
means: RMS(ΔT)² = mean over months of (Δhigh² + Δlow²)/2 = Δmean² + Δswing²/4, so a day/night swing
4 °C wider counts like a month 2 °C warmer.

**Day/night swings.** The climate model works in daily means, so the map's day/night range is
learned from Earth: WorldClim monthly mean daily highs minus lows at 100,000 land cells, as a
function of what the model does compute (monthly and annual rain, monthly temperature and its
seasonal departure, annual temperature range, elevation, distance from the sea, latitude), by
nearest-neighbour regression (`rotclimate/diurnal.py`). Tested on whole continents it never saw,
it explains about half the variation, with a typical error of 1.8 °C in the range (about ±0.9 °C on
highs and lows): deserts and continental interiors swing 14–18 °C, rainy coasts 5–8 °C. The real
places' highs and lows come from WorldClim (cities) and the WMO normals (stations), which agree to a
median of 0.0 °C. In the atlas the climograph's band is the average daily low to high. The square root makes 10 vs 40 mm count about as much as 100 vs
160 mm. A result list never shows two places within 100 km of each other, and each match shows
its typical monthly temperature and rain difference in plain units.
Place names come from your hex-grid list (`data/hex-names.csv`), placed by `scripts/hex_places.py`.

## Quick start

```bash
pip install -r requirements.txt
scripts/make_all.sh calibration/best_params.json          # every map, GIF, chart + atlas data
python -m rotclimate render --params calibration/best_params.json --out output
python -m rotclimate score  --params calibration/best_params.json
python -m rotclimate calibrate --physics v4 --objective balanced --seeds 1,2 \
       --start calibration/best_params.json --out calibration/my_run --evals 600
python -m rotclimate.experiments tilt --params calibration/best_params.json --out output/tilt_sweep.gif
python scripts/fetch_wmo_normals.py      # official WMO station normals (needs worldweather.wmo.int)
python -I scripts/build_reference.py .   # city reference set; first download into data/cache/:
python -I scripts/build_dtr_model.py .   # day/night range model (data/dtr_knn.npz)
#   geonames/  cities15000.zip, admin1CodesASCII.txt, countryInfo.txt  (download.geonames.org/export/dump/)
#   worldclim/ wc2.1_5m_{tavg,tmin,tmax,prec,elev}.zip                   (geodata.ucdavis.edu/climate/worldclim/2_1/base/)
python -m pytest -q                      # fast checks (calendar, Köppen, solver, hydrology, end-to-end)
```

To view the interactive atlas locally, run `python -m http.server -d atlas` and open
http://localhost:8000.

A full-resolution render (7 km cells, 73 weeks) takes a few minutes on 4 cores.
The 28 km grid used for calibration simulates a year in about 1 s.

## Repository layout

| path | what |
|---|---|
| `data/source/` | your five map layers (elevation, rivers, target climate, roads, labels) |
| `data/places.csv` | place names with their pixel positions (transcribed from the labels layer) |
| `data/real_cities_worldclim.csv` | 8,468 real cities with monthly normals, the "feels like" reference (`scripts/build_reference.py`) |
| `data/dtr_knn.npz` | Earth-trained day/night range model (`scripts/build_dtr_model.py`) |
| `data/real_cities_wmo.csv` | official WMO station normals: remote reference places and the cross-check (`scripts/fetch_wmo_normals.py`) |
| `rotclimate/geography.py` | layers → model grid, tier elevations, target masks, procedural surroundings |
| `rotclimate/astronomy.py`, `ebm.py` | sunlight for any tilt; planet-wide seasonal energy balance |
| `rotclimate/model.py`, `solver.py` | the 2-D seasonal model (winds, temperature, moisture, rain, snow) |
| `rotclimate/koppen.py`, `score.py` | Köppen–Geiger classes; fuzzy scoring against the painted zones; river check |
| `rotclimate/analogs.py` | real-world "feels like" matching on solstice-aligned seasons |
| `rotclimate/hydrology.py` | runoff, priority-flood drainage, river discharge (validated against your drawn rivers) |
| `tests/` | fast automated checks |
| `rotclimate/calibrate.py` | CMA-ES search over ~45 unknowns |
| `rotclimate/render.py`, `experiments.py`, `atlas.py` | maps, GIFs, climographs, sweeps, atlas data |
| `atlas/index.html` | the interactive atlas page |
| `calibration/` | best parameters, every round's best, iteration snapshots |
| `docs/MODEL.md` | how the physics works |
| `docs/ITERATIONS.md` | the improvement log |
| `output/` | rendered maps and GIFs |
