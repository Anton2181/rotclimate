# rotclimate: a climate simulator for a hand-drawn world

A physically based seasonal climate model for a 2200 × 1018 mile hand-drawn
map. The model reads the map's layers (coast, height tiers, rivers, place
names) and runs a year of weather in 73 five-day weeks on the local calendar.
A calibrator then searches for what the map doesn't say — latitude, axial
tilt, spin direction, how high the tiers are, and what lies beyond the edges —
until the simulated climate reproduces the painted target zones.

## Results

**Interactive atlas:** https://claude.ai/artifact/BMvofWDzswrdCgSBkHnNRf (private until you share it).
Zoomable map layers (Köppen, your zones, the simulated climate in your zones, match accuracy,
temperatures, precipitation). Click any place for its climograph in the local calendar and its
closest real cities. Search a town on the map, or a real city to see outlined where on the map
feels like it.

![The calibrated climate in your simple zones](output/simulated_zones.png)

![Köppen map](output/koppen.png)

### What the world must be like (best calibration, round 7)

| unknown | best fit |
|---|---|
| spin | **retrograde (opposite to Earth)** |
| latitude | 24.7°N to 39.5°N (centre 32.1°N) |
| axial tilt | 32.6° (Earth 23.4°) |
| height tiers | lowland ≤ 277 m, hills ≤ 709 m, upland ≤ 2497 m, peaks to 4984 m |
| land beyond the map | north 77%, south 99%, west 3%, east 11% |

The strongest result is the spin. With Earth-like spin, no calibration in any round could make
the south-east hot and dry. A final fairness run with identical physics and budget confirms it:
best balanced score 0.336 for Earth-like spin against 0.493 for retrograde, with hot-and-dry at 0.09. Reversed spin turns the continent into a mirror-image North America:
the west coast and south coast play the humid south-east US, the east plays California, the
south-east plays the dry south-west, and the north-west plays New England. (A southern-hemisphere
map with south at the top would behave the same way.)

### Match with the painted zones (14 km render)

Overall 0.51; **54% of painted land falls in its own zone's rule**
(it00, the Earth-like first guess: 0.17 and 9%).

| zone | agreement (0–1) |
|---|---|
| Cold and wet | 0.61 |
| Cold and dry | 0.48 |
| Warm and wet | 0.50 |
| Mediterranean | 0.46 |
| Hot and wet, swampy | 0.28 |
| Tree (forested) | 0.65 |
| Hot and dry | 0.56 |

The swampy south coast is the zone the model does not reproduce: it comes out warm-and-wet
instead. The maps are simulated on 14 km cells. Calibration ran on 21–28 km cells and the score
holds down to 14 km, but finer grids drift (7 km: 0.47), because cold-dry and hot-dry sit on
climate thresholds that react to newly resolved terrain. All map layers are still drawn at 3×
resolution with full-detail terrain. See `docs/ITERATIONS.md`.

### Maps and GIFs (`output/`)

`simulated_zones.png` · `koppen.png` · `comparison.png` · `world_context.png` · `temperature_*.png` ·
`precipitation_annual.png` · `atlas_temperature.png` · `atlas_precipitation.png` ·
`climographs.png` (with "feels like" cities) · `insolation.png` · `year_temperature.gif` ·
`year_precipitation.gif` · `spin_flip.gif` · `tilt_sweep.gif` · `surroundings.gif` · `improvement.gif`

![A year of temperature and wind](output/year_temperature.gif)

Real-world analogues use official WMO climate normals for 2,106 cities
(`data/real_cities_wmo.csv`), plus approximate values for 42 well-known cities WMO lacks.
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
python scripts/fetch_wmo_normals.py      # official city normals for the analogues (needs worldweather.wmo.int)
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
| `data/real_cities_approx.csv` | approximate climate normals of ~130 real cities, used for the "feels like" analogues |
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
