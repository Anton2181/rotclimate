# Northern steppe: why the painted cold-dry zone is wet — 15 November 2026

Owner instruction: when settlement work is blocked, return to the climate model, the northern steppes first.

## 1. The failure on the current atlas (r44 physics, earth_fit world)

Painted zone 2 ("Cold and dry", north-centre, latitude 40–46°), land cells of the published atlas:

| Climate | Median rain | Median annual mean | Rain / Köppen dry threshold | Share below 1 (steppe or desert) |
|---|---|---|---|---|
| raw | 821 mm | 15.0 °C | 2.28 | 0 % |
| corrected | 832 mm | 14.5 °C | 2.32 | 0 % |

The rule needs a ratio below 1. The zone's year (corrected, median, local months from early winter):

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| °C | 0.6 | 1.1 | 3.4 | 9.3 | 15.6 | 22.6 | 30.7 | 31.7 | 25.2 | 17.4 | 11.2 | 4.5 |
| mm | 95 | 89 | 91 | 79 | 58 | 33 | 8 | 10 | 52 | 87 | 102 | 102 |

That is a Mediterranean year (Csa), not a steppe: wet winters from the storm track and a hot, dry summer. Rain falls from
west to east across the zone: about 1,150 mm on the west edge, 630 mm in the east. The summer is dry everywhere; the
excess is the cold-half-year rain (380–540 mm in five winter months, against roughly 100 mm on Earth's cold steppes).

## 2. Is it the physics? The Earth test says no

r44 on Earth's steppe analogues (`scripts/benchmark_local.py`, 56 km cells, WorldClim 1970–2000; lowland cells):

| Region | Simulated annual | Observed | Winter (simulated vs observed) |
|---|---|---|---|
| Caspian lee (central_asia, 50–58° E, 38–46° N) | 167 mm | 128 mm | about right; spring peak too strong |
| Turan lowland (60–70° E) | 160 mm | 147 mm | about right |
| Kazakh steppe | 239 mm | 307 mm | **too dry**: 1–3 mm a month against 13–20 |
| Middle Volga | 351 mm | 481 mm | **too dry**: 4–6 mm a month against 25–35 |
| Interior Anatolia (31–36° E, 38–41° N) | 345 mm | 436 mm | right; summer too dry |

The model makes deserts and steppes where Earth has them, including in the lee of an inland sea, and where it errs on cold
steppes it errs dry, not wet. A physics change that dried the fantasy zone would make these Earth regions worse. The cause is
the world, not the physics.

## 3. The world: what feeds the zone

The planet spins backwards (`retrograde`), so the mid-latitude winds blow from the east: the zone is a "west coast" in Earth
terms. The world refit set the land beyond the map's north-east edge to a share of 0.009, i.e. open ocean directly upwind of
the zone, with inland seas on both of its flanks, and a 33.5° tilt that strengthens the winter storm track.

(Probe results follow in §4.)
Winds over the zone (atlas, median by local month from early winter): easterly 11–12 m/s from the 1st to the 3rd month and
in the 12th, weakening to calm in mid-summer. The winter rain therefore comes from the east, across about 1,300 km of the
map's own (wet) land and then the fitted ocean beyond the north-east edge. Water within 200 km of the zone is only 3–4 %,
within 400 km 7–17 %: the zone is not coastal. It is wet because the whole northern continent is wet and the zone sits only
one or two thousand kilometres downwind of open ocean, where Earth's cold steppes (Kazakhstan, the Volga) lie 3,000–5,000 km
downwind, or in a rain shadow (Patagonia, the Great Plains, Anatolia).

## 4. Can a world knob fix it? Probes (32× coarse grid, every other gene as fitted)

`scripts/probe_steppe_world.py`; logs in `output/northern_steppe_20261115/`. Aridity = median rain over the dry threshold
in the painted zone (coarse start 2.95; the full-resolution atlas 2.3).

| Probe | Cold-dry aridity | Zone-fit | Side effects |
|---|---|---|---|
| start | 2.95 | 0.176 | — |
| north-east beyond: land 0.5 | 2.08 | 0.124 | Mediterranean 0.49 → 0.15 |
| north-east beyond: land 0.9 | 1.90 | 0.079 | Mediterranean → 0.03, warm-wet → 0 |
| north and north-east land 0.9 | 2.10 | 0.077 | same |
| north-east 0.9, no gap to the north | 1.90 | 0.079 | same |
| east 0.95 + north-east 0.9 | 2.12 | 0.061 | same, worse |
| tilt 23.4° (Earth) | 2.65 | 0.148 | cold-wet 0.87 → 0.58 |
| tilt 40° | 2.83 | 0.136 | |
| map 4° further south | 2.33 | 0.163 | the best single trade, still 2.3× |
| map 4° further north | 2.96 | 0.116 | |
| Earth's spin direction | 2.80 | 0.139 | cold-wet 0.30 |
| north turned 30° either way | 2.23–2.84 | 0.138–0.155 | |

No world knob brings the zone near the threshold (best 1.9×, at the cost of every warm painted zone). The world refit was
right to leave the north-east beyond the map as ocean: the Mediterranean and warm-wet zones need that moisture.

## 5. Conclusion and options for the owner

* **The model is not the cause.** The same physics makes steppes and deserts in the right places on Earth, and errs dry on cold
  steppes. Drying the physics to paint this zone would break the Earth validation. No change is made.
* **The map's geography cannot hold a cold steppe there** with the wet continent and ocean upwind. Two things on Earth make a
  steppe this close to the sea, and both are map edits (owner decisions, not model changes):
  1. a mountain barrier upwind, i.e. on the zone's **east** side under this planet's reversed winds (as the Andes make the
     Patagonian steppe 300–600 km from the Pacific); or
  2. a far larger continent upwind (3,000+ km of land to the east), which the map's frame does not contain.
* Otherwise the painted zone reads, honestly, as a **cold-winter Mediterranean** (Csa with near-freezing winters, like inland
  northern Iran or eastern Anatolia's wetter margins), and the zone painting could be changed to that.

## 6. Earth issue found on the way

On Earth the cold steppes' **winters are too dry** in r44: Kazakh steppe 1–3 mm a month against 13–20 observed; middle Volga
4–6 mm against 25–35 (annual 239 vs 307 mm and 351 vs 481 mm). The handoff already lists "winter overflow of
supersaturated columns" as next physics; this confirms where it matters. It is a real Earth error and the next physics target,
with the knowledge that fixing it would make the fantasy steppe wetter, not drier.

## 7. A second Earth defect: rain shadows are too weak

The ridge question in §5 led to a check of r44's rain shadows on Earth (56 km cells, lowland medians of annual totals):

| Pair | Windward sim / obs | Lee sim / obs | Lee/windward sim | obs |
|---|---|---|---|---|
| Washington coast vs Columbia Basin | 1,193 / 1,637 mm | 561 / 276 mm | 0.47 | 0.17 |
| California coast/valley vs Nevada | 757 / 617 mm | 394 / 192 mm | 0.52 | 0.31 |
| Galicia/north Portugal vs Ebro valley | 896 / 1,376 mm | 579 / 430 mm | 0.65 | 0.31 |

The windward sides are too dry and the lee sides up to twice too wet: the model's mountains take too little water out of the
air. A 3,000 m test ridge on the steppe's upwind side moved its aridity only from 2.95 to 2.70 on the coarse grid, consistent
with this. The rain-shadow work is declared in `calibration/rain_shadow_20261115/` (screen, then amendment 1 to the dev49 gate).

## 8. Rain-shadow attempts (all development, none adopted)

Plan `calibration/rain_shadow_20261115/` (declared screen, then amendments 1–4, each written before its gate ran). Gate:
policy v3, 49 development regions, S49 must fall at least 0.5 % (S ≤ 0.995).

| Step | Change | Result |
|---|---|---|
| Screen | one knob at a time on three windward/lee pairs | no knob cuts the contrast error 25 % (best orographic ×6: −18 %) — failed as declared |
| A1 | e3 crest cap (eddy_rainout 1), alone and with lee drying 2.4 or orographic 6 | S49 1.021 / 1.029 / 1.023 — fail |
| A2 | new e74: the cap only where ground stands above its surroundings | S49 1.019 / 1.018 — fail |
| — | **bug found**: e3's six edge-padded Gaussian steps differ from one kernel by up to 5 % of the field on regional grids, so every earlier e3 result (including the r42 factorial's crest-rainout profiles) carried an edge artefact | e74b pads once; reproduces r44 when the cap does not bind |
| A3 | e3 with the padded operator, with and without the relief gate | S49 1.020 / 1.018 — fail: the cap deletes the clipped water, drying the ranges themselves (central Asia above 1,500 m: 243 → 83 mm, observed 374) |
| screen | e74c: the clipped water rains where it is clipped | too much rain at cap = saturation; no effect at weaker caps |
| A4 | e4 (eddies mix humidity above the ground) at 4 and 6 km | S49 1.048 / 1.022 — fail: mountains dried (central Asia 243 → 57 mm), lowlands wetted |

Every existing lever dries the lee by drying the mountains as well, while on Earth the windward slopes and ranges are
themselves too dry. A real fix has to move water from lee to windward: rain on the upslope side out of the low-level flow
before it crosses (accounted orographic rainout along the mean wind), not a cap or a height-weighting of the eddy mixing. That
is new physics, recorded as the next rain-shadow step. The opt-in switches e74, e74b and e74c stay in the code, default off.

## 9. Cold-interior winters (development screen, no gate)

Winter (three coldest observed months) rain, r44 against WorldClim, cells with a coldest month below −10 °C: Kazakh steppe
3 mm against 51, middle Volga 16 against 93, Hokkaido 28/82, Nova Scotia 115/250; but the East Asian winter-monsoon side is
too wet (North China Plain 73/11, Korea 158/37, Tibet 49/6). The dry bias is the Eurasian interior's, fed on Earth by Atlantic
and Mediterranean storms 3,000+ km inland. Screen (`scripts/winter_interior_screen.sh`, output/northern_steppe_20261115/winter_screen):

| Change | Kazakh winter (obs 51) | Volga (93) | Manchuria (14) | Mean loss of 8 cold regions (r44 0.354) |
|---|---|---|---|---|
| cold_high_storms 0 (r44 0.13) | 8 | 37 | 100 | 0.363 |
| cold_high_storms 0.3 | 2 | 11 | 17 | 0.354 |
| edge_continental_drying 0 | 4 | 17 | 35 | 0.340 (Mongolia better, Kazakh worse) |
| far_fetch 0 | 2 | 10 | 26 | 0.354 |
| storm_seasonality 0.4 | 3 | 18 | 33 | 0.378 |

Only trades: the storm suppression under cold highs that keeps Manchuria dry starves the Kazakh and Volga winters. A fix needs
storms steered around the high (moisture reaching the high's western flank), not weaker or stronger suppression. Recorded as
an open physics item. It does not bear on the fantasy steppe, whose winter is mild (coldest month 0.6 °C).

## 10. New physics e75: an upwind barrier on eddy water (development, not adopted)

Budget diagnosis first (`scripts/rain_shadow_budget.py`, California, r44): Nevada's lee rain, 1.08 mm/day against about 0.53
observed, is fed by eddy exchange 0.80, local evaporation 0.65 and mean-wind advection 0.33, less column drying 0.68. The e3
cap failed because it also clipped inside the lee's own ranges.

**e75** (`eddy_barrier_km`, `eddy_barrier_dz_km`, `eddy_barrier_crest`; default off, r44 byte-identical): the eddy water reaching
a cell is capped at saturation at the highest ground within a set distance upwind along the eddy-scale mean wind, wherever
that barrier stands above the cell. Crest and windward cells are never capped. Plan `calibration/rain_shadow_20261115/plan_e75.json`.

| Step | Result |
|---|---|
| Screen, barrier from cell-mean heights (150/300 km) | contrast error −6 to −8 %: fail (56 km cells flatten the ranges) |
| Amendment 1: barrier from crest heights, C05 / C10 | −23 % / −20 %: fail the 25 % bar; three-region rain loss −10 % / −16 %; Nevada 168 mm (obs 192) |
| Amendment 2 (disclosed departure): C05 and C10 to the dev49 gate | S49 1.015 / 1.037: **fail**; fine28 0.978 pass |
| Frozen refit of C05 with storm track, recycling, RH threshold, rain time (14 evaluations) | best S49 **1.012**: fail |

What it shows: e75 fixes the westerly lee basins (Great Basin −32 %, California −21 %, Canadian prairies −16 %, Manchuria −15 %)
and brings US Midwest winters to the observed level. But several regions' annual totals were already too low (US Midwest
summers 65 mm against 93; the Alps and central Asia too dry overall), so taking the excess lee water away costs more there
than it gains. r44's fit uses lee over-wetting to offset summer and inland deficits; e75 can only pass together with a fix
for those deficits (the summer rain-making gap in `reports/SUMMER_RAIN_20261030.md`). e75 stays in the code, default off.

## 11. Summer rain-making alongside e75 (development, not adopted)

e75 failed because summer and inland totals are already too low. Two declared mechanisms for the summer deficit
(`calibration/rain_shadow_20261115/plan_e76.json`), both opt-in, default off:

| Candidate | S49 (gate ≤ 0.995) | Helps | Hurts |
|---|---|---|---|
| J1 e76: convection onset 18 °C instead of 22 | 1.014 | US Midwest −18 %, Japan −19 % (Midwest summer 65 → 82 mm, obs 93) | East Australia +43 %, Tripolitania +38 %, East China +14 % |
| J2 / J3: e76 at 18 / 15 °C with e75 C05 | 1.026 / 1.045 | | |
| K1 / K2 e77: summer showers scaled by the storm index | 1.000 / 1.002 | US Midwest −11 %, Japan −9 % | Manchuria, Victoria, East Australia +8–9 % |

e77 is the cleaner mechanism (neutral, where e76 is harmful), but nothing passes, so the e75 combination was not run (declared
rule). The pattern across sections 8–11: r44 sits in a balance where errors offset each other region by region, and every
single mechanism (rain shadows, summer convection) improves its target regions while unsettling that balance elsewhere.
The way forward is a joint refit of e75 + e77 with the rain-making parameters, on the scale of the earlier multistart
campaigns, declared in advance and checked on sealed set i, not more one-mechanism gates.
