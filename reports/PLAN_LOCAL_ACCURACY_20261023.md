# Plan: per-location temperature and rainfall accuracy

Goal: make the simulated monthly temperature and rainfall at each place
closer to observed climate, measured on real Earth geography, and carry
every adopted improvement into the fantasy-map atlases. This plan is worked
through as a perpetual loop: measure, pick the largest error, test one
physical hypothesis under a frozen gate, adopt or reject, record, repeat.

## 1. Where the error is now

Baseline: the published Earth physics (r29, `atlases/earth_fit/params.json`)
on the 19 development regions at 56 km, against WorldClim 2.1 monthly normals
(`scripts/benchmark_local.py`, output `output/local_20261023/baseline_56km/`).
Regions have equal weight; these regions have been used in development, so
the numbers measure progress, not independent accuracy.

| | Temperature | Rainfall |
|---|---|---|
| Monthly error per cell | 2.23 °C (MAE) | 31.4 mm (MAE) |
| Annual mean / total per cell | 1.58 °C MAE; 70 % of cells within 2 °C | log RMSE 0.452; 37.5 % of cells within 25 % (equal-region) |
| Local pattern | anomaly correlation 0.95 | wet/dry rank correlation 0.51 |
| Frozen rainfall loss | — | 0.442 |

Splitting the squared monthly error per region:

| Share of squared error | Region-wide offset | Local pattern | Seasonal shape |
|---|---|---|---|
| Temperature | 31 % | 15 % | **55 %** |
| Rainfall (log monthly) | 20 % | 32 % | **49 %** |

The seasonal shape is the largest part for both.

- **Temperature peaks too late in mid-latitudes.** The first annual harmonic
  peaks late by 37 days in New Zealand, 35 in western Europe, 20 in the
  Pacific Northwest, 15 in eastern Europe, 13 in Chile and the Cape.
  Springs are too cold (western Europe −4 to −5 °C March to July) and autumns
  too warm. Air over land follows the slow sea instead of warming with the
  spring sun.
- **Seasonal swings are wrong in size:** 13–19 % too large in dry interiors
  (Levant, Mexico, Central Asia, East China), 12–20 % too small in Iberia,
  western Europe and east and south-west Australia.
- **Rainfall seasons:** too flat in monsoon climates (the seasonal contrast
  is 0.28 of observed in Japan, 0.41 in Mexico, 0.59 in Manchuria), and up to
  twice too peaked in California, New Zealand and western Europe.
- **Rainfall location:** places are ranked badly in Japan (−0.07), eastern
  Europe (0.19), the SE US (0.20), Central Asia (0.26) and Mexico (0.29).
- **Region-wide offsets:** Chile +3.3 °C, Manchuria +2.6, Pacific NW −2.1,
  Iberia and eastern Europe −1.8; east Australia twice too wet; New Zealand
  and Japan too dry.

A learned statistical correction was tested and is not the main route yet.
A ridge regression of observed monthly values on model output and geography,
validated by leaving each region out, lowers monthly temperature error
2.23 → 2.00 °C (all of it seasonal shape). But annual-mean error rises
1.58 → 1.73 °C and rainfall gets worse (31.4 → 32.5 mm; log RMSE 0.452 →
0.486). With 19 regions each region's offset is its own. Physics that fixes
the seasonal cycle is the robust route; a correction is revisited only with
many more regions.

## 2. Selection gate (frozen before results)

`calibration/local_accuracy_20261023/policy.json`. For a candidate against
the current reference, same regions, same resolution:

- Score S = 0.5 × (temperature monthly MAE / reference) + 0.5 × (rainfall
  loss / reference), equal-region means; 1.000 = reference.
- Adopt only if S improves by at least 0.5 % over all 19 regions, S does not
  worsen in any of the three groups (training 8, former holdout 5,
  mid-latitude 6), and neither component worsens by more than 1 % overall.
- Every adopted candidate also gets a paired 28 km check on 4 regions (no
  worsening of S beyond 1 %).
- Each adopted milestone is checked once on sealed regions: Norway and
  south-east Africa (already reserved), plus the new sealed set below. Sealed
  results are reported, never tuned on.

## 3. Work tracks, in priority order

1. **Seasonal timing of temperature** (largest single error). Hypotheses:
   land air warming with the spring sun under maritime flow, faster than the
   sea it came from; the sea's own seasonal phase (shallow summer mixed
   layer, deep winter one); a too-long circulation lag. Diagnose with
   station traces (air, land equilibrium, sea, winds) before building.
2. **Seasonal size of temperature:** dry interiors swing too much and wet or
   maritime ones too little. Hypotheses: cloud and soil moisture damping of the
   land's summer heating and winter cooling, land heat capacity tied to soil
   water.
3. **Rainfall seasons:** monsoon summers too flat (the convergence import
   e17 is weak at its adopted 0.15), dry summers too dry in Mediterranean and
   oceanic climates (the humidity-spread e22 and the weather-uplift option
   `orographic_gust_ms` are the candidates).
4. **Rainfall location within regions:** orographic and coastal structure;
   rain shadows (a ridge-aware form that keeps the rain on the windward side).
5. **Region-wide offsets:** cold-current coasts (Chile), the Siberian High
   (Manchuria), oceanic coasts (Pacific NW, New Zealand), east Australia's
   double rain.
6. **A wider Earth sample.** Add about 12 predeclared regions (more climate
   types at the map's latitudes) and seal 4 more alongside Norway and
   south-east Africa. More regions make every selection less noisy and are a
   precondition for any learned correction.
7. **Finer-scale detail for the atlas:** downscale model fields to the
   atlas's terrain (seasonal lapse already applied to temperature; add an
   orographic rainfall factor) and verify against WorldClim at ~14 km.
8. **Learned correction, deferred:** only the seasonal shape of
   temperature, only with 40+ regions, always as a separate, labelled layer.

## 4. Loop mechanics

- Each iteration: one hypothesis, diagnosis first, then the cheapest test
  (6-region pilot, then 19 regions), gate, write-up in
  `reports/ITERATION_LOCAL_<date>.md`, commit and push.
- Reference changes rebuild the Earth-fit atlas once per adopted milestone,
  with the repository's existing build and browser checks.
- Rejected mechanisms stay in code only if they are off by default and
  documented; dead ends are removed.
- Population research runs as a side track (see
  `research_notes/population_density_research_20261023.md` when written).
