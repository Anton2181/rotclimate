# What invented surroundings cost, measured on Earth (1 November 2026)

The invented map knows nothing beyond its edges; the model generates the
1,100 km around it (`rotclimate.geography._procedural_offmap`: each side's
land share, fitted on the map; fractal coastlines; edge features continued
and faded over `beyond_continuity_km`; low noise hills; climate averaged over
three random layouts). `scripts/offmap_earth_test.py` measures the method on
Earth: each region's scored window keeps its real land and terrain, the
surroundings are the real world or generated with the real side shares (so
only the method is tested), both in map mode (the Earth-only derived fields
set to None, the world beyond the grid real in every run). Physics r40, 56 km;
`output/offmap_earth_20261101/offmap.json`.

| method | T cost vs real surroundings (RMS, °C) | rain cost (log RMS) | T error vs WorldClim | one layout's T cost |
|---|---:|---:|---:|---:|
| real surroundings | — | — | 2.05 | — |
| M0 the atlas's (continuation 688 km, 3 layouts) | 0.84 | 0.220 | 2.05 | 0.97 |
| M2 continent-scale noise (1,500, 3,000 km) | 1.73 | 0.467 | 2.75 | 1.91 |
| **M3 continuation 300 km (3 layouts)** | **0.79** | **0.206** | **2.03** | 0.98 |

By region (T cost, °C, M0 / M3): British Isles 0.77 / 0.74, Iberia 0.51 /
0.58, East China 0.26 / 0.24, Japan 2.07 / 2.11, Central Asia 0.39 / 0.37,
California 1.06 / 0.71.

* Against the observations the generated surroundings cost nothing on
  average (2.05 °C either way): the model's physics errors dominate; against
  the real surroundings' own climate they cost ~0.8 °C and ~20 % of rain.
* **Continent-scale coherence is worse**, not better: large random blobs
  put whole continents in the wrong place.
* **A shorter continuation (300 km) is a little better** than the 688 km the
  map's world fit chose (−6 % in temperature, −6 % in rain; better in four of
  six regions, most in California). The fit's long continuation extends the
  map's own edge features (its coasts and ranges) too far.
* Averaging three layouts takes ~13 % off one layout's cost; the cost is
  mostly systematic, not layout noise.
* Japan is the outlier (2.1 °C): side shares cannot place the cold Asian
  continent close upwind of it. A side-share method misses an asymmetric
  neighbour; the map's own side shares carry what the painting implies.

For the planet refit of the invented map: `beyond_continuity_km` is fixed at
300 km from this test instead of being fitted, continent-scale noise is not
used, and three or more layouts are averaged.
