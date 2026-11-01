# The invented world with planet levers, on r41 physics — 1 November 2026

**Result:** not published. The atlas keeps r41 with the published world's
geometry.

- **Frozen search:** no world passes the plan's coarse screen.
- **Amended review:** two finalists reached the native check and both fail
  it on the painted hot-dry zone (the southern desert).
- **Audit:** never run. Its nine layouts stay unseen.

The best finalist would raise strict agreement on the painted map from
32.6 % to 37.3 %, but it gives up the desert. No planet lever separates the
two.

## Plan

`calibration/map_world_r41_planet/plan.json`, frozen before any run.
`scripts/world_campaign_r41.py`.

**Held fixed:**
- r41's shared physics.
- Earth's gravity, day length and year length.
- Planet radius, map scale and retrograde spin.
- The off-map continuation, fixed at 300 km. On Earth this beat the fitted
  688 km (`reports/OFFMAP_EARTH_20261101.md`).

**Free:**
- The r40 world genes: latitude, orientation, the four terrain tiers and the
  surrounding land.
- The legal planet levers:
  - tilt, 8–45°;
  - eccentricity, 0–0.06;
  - perihelion phase, the whole year;
  - starlight, 0.96–1.04 × Earth's;
  - greenhouse forcing, −2 to +8 W m⁻²;
  - land by latitude, Earth's pattern × 0.4–1.8.

**Search:** CMA-ES with 241 candidates at downsample 32. Each candidate is
scored on the mean climate of five layouts.

**Objective:** the zone objective minus a penalty for every point outside
the coarse screen, measured against the matched r41 atlas (the control).
r40's search had found gains that only traded one painted zone for another;
this objective searches inside the screen instead.

## Search

The control scores 0.1835 (strict agreement 37.3 %, hot-dry recall 0.246,
Mediterranean dry share 5.2 %).

The fixed 300 km continuation alone moves the map far outside the screen.
At the start, cold-wet recall is 1.0 (control 0.63), warm-wet 0.30 (0.43)
and tree 0 (0.09), and the penalty is 0.50. The search walks back from
there.

The 25 candidates with the smallest penalties agree on a planet:

| lever | median | range |
|---|---:|---:|
| greenhouse forcing | +2.2 W m⁻² | +1.1 to +3.8 |
| land by latitude | × 1.33 | 1.01–1.49 |
| tilt | 31.1° | 27.6–34.9 (the published world: 33.5) |
| eccentricity | 0.017 | 0.005–0.030 |
| starlight | 0.998 | 0.992–1.010 |
| latitude of the map centre | 37.2° | 35.7–39.2 (38.5) |
| land beyond the north edge | 0.94 | 0.63–1.00 (0.52) |

The search prefers a warmer greenhouse, more land on the planet, more land
to the north, and a map about 1° further south. Perihelion phase stays
unconstrained.

No candidate gets a zero penalty. The best raw candidates:

| eval | zone objective | breach | cold wet | warm wet | Med. | tree | hot dry | Med. dry |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| control | 0.1835 | | 0.630 | 0.429 | 0.766 | 0.088 | 0.246 | 5.2 % |
| 167 | **0.1912** | tree, hot dry | 0.796 | 0.451 | 0.880 | 0.035 | 0.185 | 2.6 % |
| 176 | 0.1886 | tree, hot dry | 0.685 | 0.445 | 0.807 | 0.070 | 0.154 | 2.1 % |
| 213 | 0.1881 | tree | 0.778 | 0.423 | 0.766 | 0.035 | 0.277 | 4.7 % |

By the plan's rule nothing advanced (`output/r41_world_planet/review.json`).

## Amendment

`calibration/map_world_r41_planet/amendment_cell_screen.json` was declared
after the review and before any native or audit run.

At downsample 32 the painted zones hold few land cells: tree 57, hot dry 65,
cold wet 54. A recall loss of 0.03 there is one or two cells. The amendment
widens each zone's coarse allowance to two binomial standard errors (tree
0.075, hot dry 0.107). Everything after the screen stays exactly as frozen:
- the native downsample-8 check, with about 1,000 tree cells and 1,100
  hot-dry cells, and every zone limited to a recall loss of 0.02;
- the nine-layout audit, on layouts no campaign has run.

Eval 213 motivated the amendment. That is why the unseen native check and
audit remain the deciding tests. The finalists are 167 and 176, ordered by
raw zone objective.

## Native check (downsample 8, layouts 1–3, against the r41 atlas)

| | r41 atlas | 167 | 176 |
|---|---:|---:|---:|
| zone objective | 0.1771 | **0.1853** | 0.1801 |
| strict agreement | 32.6 % | **37.3 %** | 34.1 % |
| cold wet | 0.595 | 0.657 | **0.509 ✗** |
| warm wet | 0.351 | 0.369 | 0.349 |
| Mediterranean | 0.681 | 0.865 | 0.797 |
| tree | 0.071 | 0.062 | 0.100 |
| hot dry | 0.246 | **0.176 ✗** | **0.138 ✗** |
| Mediterranean dry / Cs share | 11.4 % / 73.9 % | 6.3 % / 88.3 % | 5.0 % / 89.3 % |

Both finalists fail (`output/r41_world_planet_amended/review.json`). The
audit did not run, so its layouts remain prospective.

## Why the desert goes

Inside the painted hot-dry zone (1,020 native cells), r41 gives:
- median annual rain 739 mm;
- median annual mean 18.1 °C;
- Köppen classes: 61 % Cfa (humid subtropical), 25 % BSh (hot steppe),
  10 % Csa.

So the painted desert is mostly humid subtropical in the model already.

Candidate 167 warms the zone by 1.6 °C (84 % of cells now reach an annual
mean of 18 °C, against 54 %). It also moves the rain into winter: Csa rises
to 32 % and BSh falls to 18 %. The levers that win the cold-wet north and
the Mediterranean (more greenhouse, more land, more northern land, the map
further south) turn the south Mediterranean, not dry.

This is the geometric limit reported in October
(`reports/WORLD_KNOBS_20261023.md`): on the painted map the hot-dry south
and the cold-wet north are closer together than Earth's climate belts
allow, and the planet levers trade one against the other.

## What it leaves

The r41 atlas keeps the published geometry.

Candidate 167 is recorded (`calibration/map_world_r41_planet/finalists/`)
as a choice for the map's owner: much better strict agreement, Mediterranean
and cold-wet zones, against a 0.07 loss of hot-dry recall. The rule does not
allow it, so it is not taken.

A next attempt would have to protect the desert in the search itself:
- run at downsample 16 (about 280 hot-dry cells instead of 65);
- allow no hot-dry loss.

The cost is roughly four times the compute. Moving the desert's rain
needs the subtropical high to reach the map's south, and that is shared
physics, not a world lever.
