# Arable land from slope (block D, step D1) — 8 November 2026

Plan: `calibration/geography_control_20261107/plan_D1.json` (D1, D1b). Code: `scripts/arable_slope_d1.py`,
`scripts/arable_slope_earth.py`, `harvest/export.py` (`geometry`), `scripts/land_people_earth.py --arable slope`.

## Why

Now that the eroded height map carries the drawn rivers in Earth-fitted valleys (`reports/RIVERS_TERRAIN_20261108.md`),
farming should follow the terrain. Until now, the share of a cell that can be ploughed was one constant per drawn tier
(0.85 / 0.75 / 0.45 / 0.08). The constants came from the GAEZ slope classes (Fischer et al. 2012), weighted by typical
landform slopes. Valley floors and steep valley sides in the same tier were therefore treated alike, and a flat high
plateau counted as almost unploughable.

## D1: the rule, fitted on Earth at the map's own scale

* **Kept rule.** GAEZ's slope classes: land under 8 % slope is fully arable, 8–16 % 0.6, 16–30 % 0.3, steeper 0.05.
* **Earth target.** That rule applied to every 90 m pixel of Copernicus GLO-90. Each ~1.85 km cell takes the mean of its
  pixels.
* **Predictor.** The slope S the map itself resolves: the ~1.85 km block-mean surface, in degrees.
* **Fitted curve.** a(S) = 0.018 + 0.982 / (1 + (S / 2.75°)^1.29), on 12 development tiles (1° each).
* **Rejected variant.** A separate lowland and upland ceiling gained 0.001, below the frozen 0.01, so it was not adopted.

| | Tier constants | a(S) |
|---|---|---|
| Development tiles, tile-mean RMSE | 0.240 | 0.119 |
| Blind tiles (12, never used), RMSE | 0.308 | 0.184 |
| Blind tiles where a(S) is better | | 12 of 12 |
| Blind bias | | +0.036 (gate ±0.05) |

Weak spot: finely dissected hill country whose 1.85 km slope is moderate, such as the Shanxi loess (+0.19) and the Fujian
hills (+0.20). There the curve over-states arable land.

On the map, height map v2.1 gives these mean arable shares per tier:

| Tier | a(S) | Old constant |
|---|---|---|
| 1 | 0.85 | 0.85 |
| 2 | 0.58 | 0.75 |
| 3 | 0.44 | 0.45 |
| 4 | 0.30 | 0.08 |

* Tier-1 valley floors come out at 0.91.
* The land-weighted mean is almost unchanged, 0.744 → 0.739, so farming moves into valleys and plains rather than growing
  or shrinking.
* Atlases without an eroded terrain file (free, Whittaker) keep the tier constants.

## D1b: one calibrated chain on Earth

The same rule now drives the Earth harness: ETOPO 2022 slopes at 60″, a(S), averaged over each 5′ cell.

### FALLOW refit

* `FALLOW` sets the share of single-cropped fields sown each year. It had been fitted so the North China Plain's AD 2 census
  (80.7 per km²) sits at capacity.
* It is refitted the same way: 0.68 → 0.599. The plain's flat land is about 0.99 arable, not 0.85.

### No-harm checks (frozen gates)

| Check | Before | After | Gate |
|---|---|---|---|
| 10 unfitted historical regions, RMS of ln(historical / capacity) | 1.701 | 1.648 (8 of 10 closer) | worse by ≤ 0.05 |
| Earth control development pools, v2.1 rules, balanced accuracy: Rome AD 150 | 0.8488 | 0.8486 | lose ≤ 0.01 |
| Earth control development pools, v2.1 rules, balanced accuracy: Han AD 2 | 0.6637 | 0.6630 | lose ≤ 0.01 |

The control check rebuilt the whole Earth chain in a separate worktree: harness, window people, food fields, staffing chain
and territory. A baseline worktree reproduced 0.8488 and 0.6637.

* Both gates pass, so D1 is adopted on the map and on Earth.
* A first slope run was not consistent: it took the window people from a harness computed before the `FALLOW` refit. It was
  re-run; the numbers above are from the consistent run (`output/arable_slope_d1/d1b_checks.json`).
* Older Earth intermediates stay as they were when their tests ran: the spent blind pools and the settlement-model harness.

## Release

* **Drivers:** `scripts/release_d1_arable.sh` (Earth-fit base from the height map v2.1 checkpoint, plus the free and
  Whittaker food chain refreshed in place) and `scripts/release_d1_arable_addons.sh` (promotion and add-ons).
* **Climate:** unchanged.
* **Changed:** the arable share, `FALLOW`, and everything downstream of them (farming, population, settlement, institutions,
  control).
