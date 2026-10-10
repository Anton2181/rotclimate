# How the simulator works

The map tells us the shape of the land, four unlabelled height tiers, rivers
and roughly what the climate should be. Everything else is unknown: where on
the planet the map sits, the axial tilt, which way the planet spins, how high
the tiers are, and what lies beyond each edge. The simulator turns those
unknowns into numbers (`rotclimate/config.py`). The calibrator then searches
for the combination whose simulated climate best reproduces the painted zones.

```
 map layers ─► geography.py ─► model grid (land, elevation, latitude, padding)
                                         │
 tilt, orbit ─► astronomy.py ─► ebm.py (planet-wide seasonal energy balance)
                                         │  zonal sea / continental temperatures
                                         ▼
                                 model.py: 73 five-day weeks
          winds ◄── thermal lows/highs ◄── air temperature ◄── sea-surface temps
            │                                    ▲
            └──► moisture transport ─► rain/snow ┘ (evaporation, recycling)
                                         │
                       koppen.py ◄───────┘──► score.py ◄── painted target
                                                  │
                                         calibrate.py (CMA-ES)
```

## 1. Geography (`geography.py`)

* **Scale.** The image is 2000 × 926 px, drawn on pointy-top hexes with
  15-mile sides (30 mi corner to corner, 26 mi across the flats, ~585 sq mi).
  Measured from your hex lines (`scripts/prepare_sources.py`: 4,284 hex
  centres, columns 22.72 px apart, rows 19.68 px, a perfectly regular grid)
  that is 1.143 mi per pixel, so the map is 2,286.8 mi east–west by
  1,058.2 mi north–south (1 px ≈ 1.84 km) and spans about **15.3° of
  latitude**. (Rounds 1–11 used 2,200.5 × 1,018.5 mi,
  i.e. hexes 25 mi across the flats: 4% smaller.)
* **Elevation.** Each tier is a band between two unknown heights (the
  `tier_tops` parameters). Inside a band, the height ramps smoothly from the
  lower to the upper boundary using distance transforms. Coastal plains start
  near sea level, interior basins sit higher, and ridge crests are highest.
* **Beyond the map.** The grid is padded by about 1,100 km on every side and
  filled with *plausible, procedurally generated* surroundings:
  1. **Continuation.** Whatever touches an edge (open sea, a coast, the
     northern mountain range, the southern landmass) carries on outward. Its
     profile is blurred more with distance and meanders, then fades out over
     `beyond_continuity_km`.
  2. **Fractal geography.** Farther out, seeded multi-scale noise makes
     coastlines, islands, inland seas and low hills (`beyond_relief_m`). Each
     side has one number, its **land fraction** (`beyond_north_land` etc.;
     0 = open ocean, 1 = solid continent). Corners blend their two sides.
  3. **Ensemble.** A single random coastline is fiction, so the calibrator
     scores every candidate on 3 differently seeded surroundings and averages.
     What it learns is *how much land* lies in each direction, not a specific
     shape. `output/world_context.png` shows one realisation.

  (Rounds 0–2 used a cruder `blocks` style: each side was ocean, solid land or
  the edge row stretched outward.)
* **Target.** Only the six flat paint colours are read. Label text is refilled
  from the surrounding paint and enclosed gaps are filled. The single green
  colour is split into *swampy* (west of x = 1150 px) and *tree* (east).

## 2. Sunlight and the planet-wide energy balance (`astronomy.py`, `ebm.py`)

Daily-mean top-of-atmosphere sunlight is computed for any tilt and
eccentricity. A **seasonal energy-balance model** covering the whole planet
(90 equal-area latitude bands, each with a land column and a sea mixed layer,
poleward heat diffusion and ice/snow albedo feedback) turns that into:

* the zonal **sea-surface temperature** for every latitude and day, and
* the **deep-continental temperature**: what land far from any sea would reach.

Its constants were tuned so that, with Earth's tilt, it gives Earth-like
numbers between 30° and 60° (e.g. at 40°: continental air 0 → 29 °C, sea
surface 10 → 21 °C). The land peaks about 4 weeks after the solstice and the
sea about 11 weeks after. Changing the tilt therefore changes the seasons
physically, not by fiat.

## 3. The 2-D map model (`model.py`)

For each of the 73 five-day weeks:

1. **Sea surface.** Zonal SST, plus boundary currents within a few hundred km
   of coasts. On a prograde planet the west coasts of continents get cold
   currents in the subtropics (like California) and warm ones poleward of about
   45° (like Norway). Retrograde spin swaps the sides. Enclosed seas take on
   part of the land's seasonal swing.
2. **Winds.** A three-cell circulation (trades, westerlies, polar easterlies)
   whose belts (ITCZ, subtropical high, storm track) migrate with a one-month
   lag behind the sun. Retrograde spin flips the east–west components. On top
   of that is a **thermal wind**: hot land in summer forms a low (monsoon
   inflow) and cold land in winter forms a high. Pressure is taken from the
   smoothed temperature anomaly, the wind is turned by Coriolis (the sign
   depends on spin) with friction letting it cross isobars, and it slows over
   mountains.
3. **Air temperature.** Air masses are carried by the wind and relax toward the
   local surface temperature (sea or land). The relaxation is fast over land
   and slower over sea. Downwind of an ocean you get maritime climates; downwind
   of a continent you get continental ones. Storm eddies also exchange heat with
   the surrounding ~450 km (physics v3). Wet ground keeps summers cooler
   (physics v8): where recent rain matches the potential evaporation, part of
   the land's summer warmth goes into evaporating water instead of heating the
   air, which is why humid summers on Earth rarely pass 30 °C. Winters are
   untouched. The result is cooled with height (lapse rate) at full map
   resolution.
4. **Moisture and rain.** Precipitable water evaporates from the sea toward 80%
   of saturation, is carried by the wind and by storm eddies, and is
   re-evaporated from wet land. Rain-out depends on the column relative
   humidity, boosted by:
   * wind convergence (ITCZ, monsoon lows),
   * the **storm track**, which sits about 13° poleward of the subtropical high
     and is stronger in winter (this is what makes Mediterranean climates rain
     in winter),
   * **forced ascent** where the wind blows uphill (orographic rain), and
   * saturation at altitude (rain shadows follow automatically).

   It is suppressed under the **subtropical high**. That subsidence is stronger
   on one side of each ocean basin (dry west coasts on Earth), and the side
   flips with retrograde spin. It can also be stronger in summer than in winter
   (physics v7), since monsoon heating next door drives the summer sinking
   (Rodwell & Hoskins 2001).
5. **Snow.** Snow accumulates when below about 0 °C and melts by degree-days.

Each week's transport equations
(`u·∇φ − K∇²φ + λφ = S`) are solved to steady state with an upwind,
over-relaxed Gauss–Seidel "fast sweeping" solver (`solver.py`, Numba). Each
solve is warm-started from the previous week.

## 4. Köppen classification (`koppen.py`)

This uses the standard Köppen–Geiger rules of Peel et al. (2007) and Beck et
al. (2018), with a C/D boundary at 0 °C, applied to 12 equal "Earth months" so
the thresholds keep their usual meaning. Charts use the local calendar.

## 5. Scoring against the painted map (`score.py`)

Each painted zone becomes a fuzzy rule on climate statistics:

| zone | rule (soft thresholds) |
|---|---|
| Cold and wet | coldest month below ~1 °C, humid (precipitation ≥ 1.8× the Köppen dryness threshold) |
| Cold and dry | coldest month below ~1 °C, semi-arid or arid (below 1.3× threshold) |
| Warm and wet | coldest month above ~1 °C, warmest above ~20 °C, humid, no summer drought |
| Mediterranean | warmest month above ~22 °C, coldest above ~0 °C, dry summer and wet winter, not desert |
| Hot and wet, swampy | warmest month above ~25 °C, coldest above ~4 °C, **hot year (mean annual above ~21 °C)**, very wet (≥ 2.0×), **on flat ground** (slope under ~1.5 ‰ over ~15 km): waterlogged. Where this rule is met the place counts as swamp, since every swamp also meets the warm-wet and forest rules |
| Tree | coldest month above ~2 °C, humid enough for forest (≥ 1.6×) |
| Hot and dry | mean annual temperature above ~17 °C, arid or semi-arid (< 1×) |

A zone's score is the average membership over its land cells. Two objectives
are used:

* **mean**: the plain mean over zones (rounds 1–2);
* **balanced**: half mean, half soft-minimum over zones (no zone can be
  sacrificed), minus penalties for implausible rainfall;
* **f1** (rounds 12–15): as balanced, on each zone's F1, which also counts how
  much of a zone's rule spills into areas painted as something else;
* **f1r** (round 16 on): as f1, plus a penalty when humid summers are hotter
  than Earth's. On Earth (WorldClim lowland, 20–50°) only 2.8% of the land
  whose warmest month brings 80 mm or more of rain passes 30 °C; the penalty
  starts at twice that share.

The swamp's heat rule comes from your legend ("Hot and wet" against "Warm and
wet") and from the map itself: among places meeting the rest of the swamp rule,
mean annual temperature separates painted swamp from the other zones almost
perfectly (AUC 0.96), while drainage measures from the wetland literature
(height above the nearest river, wetness index, upstream area) do not, because
the four flat height tiers leave them no relief to read. About 21 °C keeps it
within Earth's range: Miami, Tampa and Guangzhou are inside, Houston on the
edge, New Orleans just below.

An independent check that is never optimised compares the density of your
hand-drawn **rivers** with the model's runoff.

## 6. The calendar (`calendar.py`)

The calendar has 10 months of 35 days (seven five-day weeks each) plus 15 holy
days, which makes 365 days. That is 73 weeks, exactly one model step each.
With the winter solstice on Titian Marigold 23, every month name matches the
astronomy and the thermal lag:

| month | days | season | what happens |
|---|---|---|---|
| Titian Marigold | 1–35 | early winter | winter solstice on the 23rd |
| Scarlet Violet | 36–70 | middle winter | coldest weeks |
| Peony Blossom | 71–105 | late winter / early spring | |
| Iris Rose | 106–140 | middle spring | spring equinox on the 9th |
| Verdant Camellia | 141–175 | late spring | |
| Amber Zinnia | 176–210 | early summer | summer solstice on the 30th |
| Crimson Lantana | 211–245 | middle summer | hottest weeks |
| Saffron Lotus | 246–280 | late summer / early fall | |
| Lilac Crocus | 281–315 | middle fall | autumn equinox on the 16th–17th |
| Silver Chrysanth | 316–350 | late fall | |
| Holy Days | 351–365 | turn of the year | |
