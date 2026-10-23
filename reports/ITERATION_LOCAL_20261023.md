# Local accuracy iterations — 23 October 2026

Plan: [PLAN_LOCAL_ACCURACY_20261023.md](PLAN_LOCAL_ACCURACY_20261023.md). Gate:
`calibration/local_accuracy_20261023/policy.json` (score S = half monthly
temperature error, half rainfall loss, each relative to r29; adopt only if S
improves by 0.5 % over all 19 regions and in no group gets worse).

## Iteration 1: seasonal timing of temperature

The largest temperature error is the seasonal shape (55 % of squared monthly
error). Fitting the first annual harmonic per cell, the model's seasons peak
late in mid-latitudes: by 37 days in New Zealand, 35 in western Europe, 20
in the Pacific Northwest, 15 in eastern Europe, 13 in Chile and the Cape.
Western Europe's spring is 4–5 °C too cold.

Tried, all rejected by the gate (`output/local_20261023/`):

| Candidate | S all | S training | S holdout | S mid-latitude | Temperature | Rainfall loss |
|---|---|---|---|---|---|---|
| land heat capacity 0.7 (existing setting) | 0.9944 | 1.0223 | 1.0010 | 0.9625 | −1.4 % | +0.3 % |
| land–air coupling 0.65 days (existing) | 1.0112 | 1.0103 | 1.0256 | 1.0036 | +0.3 % | +2.0 % |
| e28 maritime land centre 1 + coupling 0.65 d | 1.0044 | 1.0390 | 0.9971 | 0.9765 | −0.3 % | +1.2 % |
| e28 0.5 + coupling 0.65 d | 0.9994 | 1.0206 | 0.9856 | 0.9881 | −1.6 % | +1.4 % |

- **e28** (`maritime_mean`, new, off by default) centres a maritime land's seasonal swing on
  the nearby sea's annual mean instead of the latitude's continental one
  (Siberia and Canada at 49° N). It shifts means (Chile 3.48 → 2.89 °C monthly error)
  but does not move the timing, and it cools California and Iberia toward
  their cold coastal water.
- A lower land heat capacity speeds maritime seasons but swings the dry
  interiors harder, and they already swing 13–19 % too much.

## Iteration 2: the sea is the hidden part of the error

A trace at Brest shows the model's sea at 3.3 °C in winter and 19.7 in
summer, against 10.4–16.7 in the World Ocean Atlas 2018. The latitude-mean
energy-balance ocean is ~5 °C too cold at 49° N in winter, the global sea
offset is −2.2 °C, and the enclosed-sea term pulls coastal water toward the
frozen latitude-mean land.

**Observed sea in place of the model's** (`sst_source="observed"`, WOA18
monthly SST via `scripts/build_woa_sst.py` and `earth.observed_sst`; a
diagnostic, Earth only):

| | r29 (model sea) | Observed sea |
|---|---|---|
| Monthly temperature error | 2.230 °C | 2.237 °C |
| Annual-mean temperature error | 1.58 °C | 1.47 °C |
| Rainfall loss | 0.442 | 0.499 (+12.8 %) |

Seasonal swings collapse in maritime regions with the real sea (western
Europe −6.8 °C too small, SW Australia −6.4, Iberia −5.9, New Zealand −5.4),
and rain rises over warmer real winter seas. The model's over-swinging sea
has been compensating too-weak land–air coupling, and the atmosphere
settings were tuned around both errors. They have to be fixed together: the
sea against observed sea temperature (Stage B), then the atmosphere with
that sea (Stage A).

**Stage B, the sea fitted directly** (`scripts/fit_sst.py`). The model's sea
surface is computed exactly as in a run, without the winds' upwelling, at
every ocean cell of the 19 region grids and compared with WOA18. Eight
settings: the sea offset, the cold and subpolar currents, enclosed-sea
warming, lake coupling, winter mixing (e19), ocean heat transport (e27)
and a new `ocean_heat_capacity` (mixed-layer depth; 1 = ~26 m).

| Sea-surface monthly error | Fitting regions | Unseen regions |
|---|---|---|
| r29 settings | 3.06 °C (19) | |
| fitted on fold A (10 regions) | 2.76 → 2.02 | fold B: 3.39 → 2.38 |
| fitted on fold B (9 regions) | 3.39 → 2.17 | fold A: 2.76 → 2.17 |
| fitted on all 19 | 3.06 → 2.14 | |

The fit transfers between folds, as expected from thousands of ocean cells
against eight settings. Settings (all 19): offset −0.74 °C (was −2.19), cold
currents 2.6 (6.3), subpolar currents 7.4 (10), winter mixing 1.0 (0), mixed
layer 1.87× (~49 m), ocean transport 0.17 (0), enclosure 6.6, lakes 0.69
(`calibration/sst_20261023/`). Most regions' seas swung 1.5–2.7 times too
much over the year; the Black Sea, the Mediterranean and western Europe
were 3–5 °C too cold.

With the fitted sea and the old atmosphere the land benchmark gets worse
(S 1.060; temperature +3.6 %, rainfall loss +8.3 %), as with the observed
sea: annual biases shrink in 12 of 19 regions, but maritime seasonal swings
become 3.5–5.3 °C too small, and Mediterranean winters 45–84 % too wet over
the warmer winter sea. **Stage A** refits eight atmosphere settings with
the fitted sea held fixed (`scripts/fit_local.py`; land–air coupling in
sun and in darkness via the new `land_radiative_days`, coupling exponent,
continentality, land offset and amplitude, sea-air humidity, rain
threshold). It is fitted on fold A and judged on the unseen fold B against
the gate; results below when complete.

## Population side track

Research: [population_density_research_20261023.md](../research_notes/population_density_research_20261023.md).

**HYDE 3.3 comparison harness** (`scripts/hyde_compare.py`; HYDE 3.3 portal
rasters, population count per 5′ cell). HYDE before 1500 is itself
modern-country totals spread by suitability weights, so this is a
consistency check, not validation. The Earth food-capacity run
(`output/land_people/earth/earth.npz`, 0–56° N, 12° W–125° E) against HYDE,
1° land blocks:

| | Rank correlation | People to move | log10 density error |
|---|---|---|---|
| Capacity, 0 CE | 0.506 | 58.4 % | 0.458 |
| Capacity, 200 CE | 0.529 | 58.0 % | 0.453 |
| Uniform over land, 200 CE | 0.070 | 65.5 % | 0.528 |

![Capacity against HYDE](../output/population_hyde/capacity_vs_hyde_ce200.png)

Capacity totals 2.58 billion against HYDE's 204 million in the window, as a
potential should. The pattern differences are systematic:

- **Capacity far above HYDE** in tropical Africa, Siberia's forest and
  Borneo: farmable in principle, thinly settled in fact (forest clearance,
  disease, frontier).
- **Capacity far below HYDE** in the Sahara margins, Arabia, Iran, the
  Central Asian deserts, Mongolia and Tibet: there is no herding population
  in the model.
- By latitude, capacity puts 45 % of people at 0–20° N (HYDE 17 %) and
  25 % at 20–35° N (HYDE 54 %).

Next population steps:

- A pastoral capacity from grassland productivity.
- An occupation discount for forest and disease frontiers.
- The Han AD 2 census as an independent target. The prefecture records
  (Zheng & Wu 2026, CC BY 4.0) carry no coordinates, so this needs their
  563 MB shapefile.
