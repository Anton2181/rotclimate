# rotclimate: a climate simulator for a hand-drawn world

A physically based seasonal climate model for a 2200 × 1018 mile hand-drawn
map. The model reads the map's layers (coast, height tiers, rivers, place
names) and runs a year of weather in 73 five-day weeks on the local calendar.
A calibrator then searches for what the map doesn't say — latitude, axial
tilt, spin direction, how high the tiers are, and what lies beyond the edges —
until the simulated climate reproduces the painted target zones.

<!-- RESULTS -->

## Quick start

```bash
pip install -r requirements.txt
python -m rotclimate render --params calibration/best_params.json   # all maps + gifs -> output/
python -m rotclimate score  --params calibration/best_params.json   # just the target score
python -m rotclimate calibrate --physics v3 --objective balanced --seeds 1,2,3 \
       --start calibration/best_params.json --out calibration/my_run --evals 600
python -m rotclimate.experiments tilt --params calibration/best_params.json --out output/tilt_sweep.gif
```

A full-resolution render (7 km cells, 73 weeks) takes about 3–5 minutes on 4
cores. The coarse grid used for calibration (28 km) takes about 1 s per
simulated year.

## Repository layout

| path | what |
|---|---|
| `data/source/` | your five map layers (elevation, rivers, target climate, roads, labels) |
| `data/places.csv` | place names with their pixel positions (transcribed from the labels layer) |
| `rotclimate/geography.py` | layers → model grid, tier elevations, target masks, procedural surroundings |
| `rotclimate/astronomy.py`, `ebm.py` | sunlight for any tilt; planet-wide seasonal energy balance |
| `rotclimate/model.py`, `solver.py` | the 2-D seasonal model (winds, temperature, moisture, rain, snow) |
| `rotclimate/koppen.py`, `score.py` | Köppen–Geiger classes; fuzzy scoring against the painted zones |
| `rotclimate/calibrate.py` | CMA-ES search over ~45 unknowns |
| `rotclimate/render.py`, `experiments.py` | maps, GIFs, climographs, sweeps |
| `calibration/` | best parameters, iteration snapshots |
| `docs/MODEL.md` | how the physics works |
| `docs/ITERATIONS.md` | the improvement log |
| `output/` | rendered maps and GIFs |
