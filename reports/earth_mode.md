# Earth mode: can the production model simulate real climates?

16 October 2026. Work after the 13–16 October handoff, with the goal the user
set: make the simulator reproduce real climates — California and Iberia first,
then real-world equivalents of every painted zone.

## 1. Review of the handoff (what was kept, what was not)

**Kept in full — production numerics (V9).** Converged moisture iterations with
a local equation check (`moisture_residual_tol`), optional strict linear solves,
bounded temperature retries, the `exponential` transport option, the moisture
budget diagnostics, `eddy_seasonality` and the `zonefit` objective. These are
sound and well tested (604 tests passed at the merge, 609 now). One finding
here strengthens them: on real geography the old fixed two damped Picard
half-steps are badly unconverged — California's mean rain is 938 mm with them
and 748 mm converged. Every calibration made with the old numerics fitted that
numerical error as if it were physics.

**Kept as frozen evidence, not developed further — the V10 layered prototype.**
Its water accounting is rigorous, but its skill on the two Earth regions is
very poor: coastal winter (Oct–Mar) rain is 57–93 mm in California and 33–61 mm
in Iberia against its own references of 535 and 439 mm, and 78–97 % of the
target Mediterranean cells turn arid
([its review](../output/v10_regional_transport_review/review.md)). Its
last experiment stopped at 6/8 cases for diagnosis. The production model
already does far better on the same coasts (section 3), so the effort went
there.

**The gap the handoff left.** The production model had never been run on real
geography. Its physics constants were fitted together with the world's
unknowns (latitude, tilt, spin, terrain heights, the land beyond the map), so a
wrong constant could hide behind a wrong unknown. On Earth every unknown is
known, so the physics can be tested on its own.

## 2. Earth mode

`rotclimate/earth.py` builds the model grid from WorldClim 2.1 (5′ terrain and
1970–2000 monthly normals) on an azimuthal-equidistant projection around each
region (exact distances, north up), with 1,100 km of real surroundings, and
runs the unchanged production model with Earth's tilt, spin, orbit and
calendar. Observed "painted zones" come from the zone rules applied to the
observed climate, so every fantasy score has an Earth counterpart.

| Region | Stands in for | Observed Köppen (top) |
|---|---|---|
| california | Mediterranean, hot-dry, cold-dry, cold-wet mountains | Csa/Csb, BSk, BWh, Dsb |
| iberia | Mediterranean, hot-dry (Sahara edge), warm-wet (France) | Csa, BSk, BWh, Cfb |
| southeast_us | warm-wet, "tree", swamp (S Florida) | Cfa 95 % |
| levant | Mediterranean, cold-dry steppe, hot desert, cold-wet highlands | BWh, Csa, Dsb, BSk |
| central_asia | cold-dry | BWk 47 %, BSk 30 % |
| east_china | warm-wet, "tree" (monsoon) | Cfa 61 %, Cwa 27 % |
| chile, cape, sw_australia (held out) | southern Mediterranean coasts | Csb, BSk, BWh, Csa |

Southern regions are run as their north–south mirror image with the months
shifted by half a year (the reflection and the opposite Coriolis turning cancel,
so it is the same physics on a northern map; perihelion moves with them).

Scores (`earth.compare`): the **climate distance** d (RMS monthly temperature
error / 2.5 °C + RMS monthly √rain error / 2, averaged over land cells: 0 =
identical), temperature bias, rain totals and seasonality, coastal winter rain,
Köppen agreement, the share of observed Cs kept as Cs or lost to arid, zone
agreement, and climographs for 4–8 well-known cities per region.

## 3. Results so far

Climate distance d on each region (56 km cells; lower is better). The two
reference rows are built from the observations themselves: every land cell
given its region's mean climate (no skill), and every cell given the mean
observed climate of its 2° latitude band corrected to its height (a perfect
zonal model with no coast-to-interior structure).

| Physics | CA | Iberia | SE US | Levant | C Asia | E China | Chile* | Cape* | SW Aus* | mean |
|---|---|---|---|---|---|---|---|---|---|---|
| reference: region mean | 2.91 | 2.74 | 1.69 | 3.26 | 2.79 | 1.95 | 3.14 | 1.23 | 1.36 | 2.34 |
| reference: latitude band + height | 1.78 | 1.12 | 1.01 | 1.30 | 1.27 | 1.26 | 2.22 | 1.07 | 0.79 | 1.31 |
| fantasy-fitted (live atlas anchor) | 4.13 | 3.43 | 2.75 | 3.59 | 3.09 | 3.85 | 4.55 | 4.11 | 3.25 | 3.64 |
| r1b: fitted on CA + Iberia only | 1.78 | 1.74 | 4.46 | 1.97 | 2.46 | 6.21 | 3.12 | 2.15 | 2.65 | 2.95 |
| r2: six regions, free circulation | 2.56 | 2.66 | 1.79 | 2.23 | 1.93 | 3.21 | 2.85 | 2.60 | 1.65 | 2.39 |
| **r4: six regions, Earth circulation, all e1 physics** | **1.86** | 2.19 | 1.76 | **1.83** | **1.48** | 3.50 | 3.52 | 2.01 | 1.85 | **2.22** |

\* held out of every fit.

- The **fantasy-fitted physics** is worse than "the regional mean everywhere"
  in every region but the south-east US: ~2× too wet and 3–4 °C too cold in
  the Mediterranean regions, almost no Cs kept (0–6 %).
- **Fitting California and Iberia alone** fixes them (Köppen 39–52 %, Cs kept
  33–45 %) and transfers to the held-out southern Mediterranean coasts, but
  turns the humid south-east US and east China 5–7 °C too hot and too dry.
- **Fitting all six regions with the circulation free** finds a compensating
  error: it moves the subtropical high to 37.7°N all year (Earth's: ~30–33°N,
  migrating ~5° with the seasons). California and Iberia then sit under the
  high all winter with weak easterly winds instead of the westerlies, so no
  mild ocean air reaches the west coasts, and the Mediterranean regions are
  sacrificed (Köppen 14–17 %) for the humid ones (south-east US 96 %).

On Earth the circulation is observed, so later fits bound it to Earth's range
(high 28–34°N shifting 3–8°, westerlies 4–12 m/s, trades 4–9 m/s, ITCZ 2–8°N
± 6–14°): the climate must come out right for the right reasons. With those
bounds (r3) the Mediterranean regions keep 78–90 % of their Cs.

**The current Earth fit (r4,** `calibration/earth/earth_e1_r4.json`**: 46
physics constants, 960 evaluations, ~2 h on four cores)** brings the training
mean from 3.47 (fantasy physics) to 2.10:

| Region | d (refs) | T bias | Rain sim/obs | Köppen exact | Cs kept / → arid |
|---|---|---|---|---|---|
| California | 1.86 (2.91 / 1.78) | −1.2 °C | 468 / 392 mm | 29 % | 92 % / 0 % |
| Iberia | 2.19 (2.74 / 1.12) | −1.7 °C | 499 / 392 mm | 22 % | 73 % / 4 % |
| SE US | 1.76 (1.69 / 1.01) | +0.4 °C | 1045 / 1229 mm | 97 % | – |
| Levant | 1.83 (3.26 / 1.30) | −0.8 °C | 324 / 394 mm | 42 % | 50 % / 26 % |
| Central Asia | 1.48 (2.79 / 1.27) | +0.2 °C | 233 / 228 mm | 34 % | – (cold-dry zone 88 %) |
| East China | 3.50 (1.95 / 1.26) | +3.2 °C | 912 / 1281 mm | 62 % | – |
| Chile* | 3.52 (3.14 / 2.22) | +4.2 °C | 485 / 489 mm | 8 % | 100 % / 0 % |
| Cape* | 2.01 (1.23 / 1.07) | +1.0 °C | 595 / 324 mm | 3 % | 100 % / 0 % |
| SW Australia* | 1.85 (1.36 / 0.79) | +1.4 °C | 438 / 358 mm | 22 % | 77 % / 23 % |

What this means: the model now produces Mediterranean climates where Earth
has them — wet winters and dry summers on the west coasts, with almost no Cs
turned into desert (the V10 prototype turned 78–97 % arid) — and humid
subtropics on the east coasts, steppe and desert in the interior, from the
same physics. It does not yet beat the "perfect zonal model" reference in
most regions: the coast-to-interior detail is right in kind but not yet in
amount (exact Köppen agreement is 22–42 % in the Mediterranean regions, with
most misses between neighbouring classes such as Csa/Csb or BSk/BWk).

Known limits, documented rather than tuned around:

- **East China** stays 3–6 °C too warm from autumn to spring. Its winters come
  from Siberian air (the East Asian winter monsoon), Earth's most extreme
  continental anomaly; the model's land temperature is the latitude mean
  (11 °C in January at 30°N, against 4 °C observed in Wuhan). A test coupling
  coastal seas to the overlying air did not help and was removed.
- **Chile's coast** is 8 °C too warm in its summer: a strip one or two 56 km
  cells wide against the Andes, whose cold marine layer is below the model's
  resolution, in a hemisphere that is more oceanic than the mirrored northern
  land temperature assumes. Weakening the storm-eddy heat mixing (to stop
  Argentine air leaking over the Andes) did not help.
- **Holdout transfer is mixed:** all three southern Mediterranean regions keep
  their Cs (77–100 %, none turned arid), but their overall climate distance is
  worse than with the earlier unconstrained fit, mostly from summer heat.

## 4. What calibration could not fix: new physics (e1)

City climographs and monthly bias profiles showed structural errors that no
parameter setting removed:

1. **No real summer drought.** Rain-rate suppression under the subtropical
   highs cannot dry a supply-limited column: the water piles up until it rains
   anyway (San Francisco 45 mm in August, observed ~1 mm).
2. **Rainy season 1–1½ months early** (San Francisco 85 mm in September,
   observed ~5 mm): the circulation was fixed to lag the sun by 30 days.
3. **Spring on land a month early** (April in east China 8–9 °C too warm,
   Memphis +6 °C, summer peaking in June).
4. **No west-coast/east-coast asymmetry.** Every land cell relaxes to the same
   latitude-mean "continental" temperature however much land its air has
   crossed: west coasts stayed 2–4 °C too cold, east coasts 1–4 °C too warm.
5. **Cold seas all year or never.** The fits pinned the global sea-surface
   offset at −4 °C plus 5.5 °C cold currents: right for the summer upwelling off
   California and Iberia, far too cold for their winter coasts.
6. **Elevated deserts ~6 °C too cool in summer** (Reno, Las Vegas, the
   Meseta) at the fixed 6 K/km lapse rate; WorldClim's own along-terrain lapse
   rates are 3–5.5 K/km.

New parameters, each defaulting to the old behaviour (round 19's strict fit
gives bit-identical temperature, rain and water fields with the handoff's
`model.py`; only the source fingerprints change):

| Parameter | Physics |
|---|---|
| `subsidence_drying` | Under the highs, dry air sinking from aloft replaces moist low-level air: the column dries without raining (Pierrehumbert's advection–condensation picture). |
| `sverdrup` | Sverdrup balance βv = f ∂w/∂z: low-level flow toward the pole rises, toward the equator sinks (dry summers on west coasts, monsoon rain on east coasts; Rodwell & Hoskins 2001, Seager et al. 2019). |
| `circulation_lag_days` | How far the highs, storm track and ITCZ lag the sun (was a fixed 30 days). |
| `subsidence_width` | Latitude width of the highs' sinking (was a fixed 6°). |
| `storm_seasonality` | Summer weakening of the storm track (was a fixed 0.3). |
| `land_heat_capacity` | Heat capacity of the energy-balance land column: how far land seasons lag the sun. |
| `continentality` | Land fraction carried along the model's own winds (4-day memory, one extra linear solve per step) scales the land seasons: sea air milder, continental air harsher. With Earth-like westerlies it reads 0.40 over California and 0.61 over Iberia in January, 0.95–0.99 over the south-east US and east China. |
| `upwelling` | Wind along a coast drives surface water 90° to its right (Ekman; left with reversed spin); where that is offshore, cold water wells up. From the coastline and the model's winds: +1.8 to +2.3 m/s offshore transport off California, Iberia and Chile in July, none in January. |
| `lapse_rate` (Earth fit only) | Fitted on Earth where heights are known; held fixed on the map, where it would trade off against the unknown terrain heights. |

All of them are computed from the model's own winds, temperatures and
coastline, never from geographic labels, so they apply unchanged to the
fantasy map with either spin and any orientation.

## 4b. Physics e2 and e3 on Earth

**e2 rain closure on Earth (r5,** `calibration/earth/earth_e2_r5.json`**):**
fitting only the five e2 genes around r4 gives a training mean of 2.077
(r4 2.104) and holdouts Chile 3.60, Cape 2.02, SW Australia 1.82
(nine-region mean 2.210 against 2.22). Earth keeps the background ascent
(0.996) and little convective rain (0.13), unlike the free map fit.

**Diagnosis that led to e3.** Summer temperature errors on the r5 fit
(`output/earth_benchmark/e3_hand_56km/t_error_before_after.png`): the
Chilean coast was 12-14 °C too hot (La Serena 32 °C against 18 °C, the air
over the sea off it 32 °C) and San Diego 8 °C too hot. Causes found:

1. the trade easterlies blow desert air offshore at 30° in summer, and air
   over the sea relaxed to the sea surface in 3 days;
2. the inland-sea warming measured land within 400 km, so every straight
   coast counted as half an inland sea and its waters warmed by up to 5 °C;
3. the planet-wide EBM used 30 % land at every latitude (Earth: 5 % at 40°S,
   48 % at 40°N);
4. storm-eddy moisture mixing was one 900 km Gaussian jump, carrying Pacific
   moisture straight through the Sierra Nevada (Reno 416 mm a year against 241).

**e3 options (default off; a default run is bit-identical):**
`ebm_land="earth"` (WorldClim land fraction by latitude, mirrored for the
southern regions; land-sea exchange scaled by the band's ocean share),
`sea_enclosure="rays"` (share of 16 compass directions closed by land within
1,000 km), `ocean_tau_stable` (air warmer than the sea cools to it in hours),
`subtropical_high` + scale/width/seasonality (pressure ~ ocean basin × band
around the Hadley edge; equatorward, onshore flow on west coasts),
`eddy_heat` (eddy heat vs moisture exchange) and `eddy_rainout` (the eddy
moisture mixing in six capped steps that cannot carry more than the crest's
saturation across a ridge). A lee-descent rain factor was tried and removed
(Reno 416 -> 409 mm).

By hand on r5 they work where aimed: Chile's summer error +7.9 -> +4.9 °C,
East China's winter +3.9 -> +2.9 °C; the rain-out alone takes California
1.78 -> 1.67 and Köppen agreement up in California, Central Asia, Iberia and
the Levant. Refitted (first stage: the e3 genes and the constants they trade
against, 240 evaluations each):

| Fit | Training mean (6) | California | Iberia | E China | Chile | Cape | SW Australia | Nine-region mean |
|---|---|---|---|---|---|---|---|---|
| r5 (e2) | 2.077 | **1.78** | **2.09** | 3.45 | 3.60 | **2.02** | 1.82 | 2.210 |
| r6, e3 with Earth's land profile | 2.105 | 2.05 | 2.26 | **3.12** | **3.18** | 2.15 | 1.94 | 2.211 |
| r6b, e3 with uniform land | 2.077 | 1.89 | 2.19 | 3.27 | 3.48 | 2.04 | **1.79** | **2.197** |

The fits keep the stable marine air (1.3 days) but switch the subtropical
highs (0.23) and the rain-out (0.05-0.13) nearly off: the highs' onshore flow
pushes marine air through the smoothed Coast Ranges into the Central Valley
(Sacramento's summer 17 °C against 25 °C), and the rain-out starves Central
Asia's winter rain. Earth's land profile helps the southern hemisphere and
East China but costs California and Iberia. Net: e3 is worth ~0.6 % on the
nine-region mean and nothing on California and Iberia, so r5 stays the Earth
reference; the options remain for the map and for finer grids, where coastal
ranges are resolved.

### 4c. Pressure-driven winds (e5) become the Earth reference

A sea-level pressure diagnosed from the temperature anomaly (CLIMBER-style:
~2 hPa/K on a planetary scale, plus an optional boundary-layer term) drives
the surface wind through the friction-Coriolis balance, replacing the
thermal-wind approximation. A first fit (r8, sigma 0.2 in 28 settings) never
beat its starting point: its typical candidate scored 3.1 against a start of
2.13. A scan of the two pressure strengths around r5 (`scripts/earth_scan.py`,
`calibration/earth_scan_slp.json`) showed the large-scale term helping
(2.061 at 2.0) and the local term hurting at every strength, so r9 started
there with small steps (sigma 0.06, 241 evaluations):

| Fit | Training (6) | Chile | Cape | SW Australia | 9-region mean |
|---|---|---|---|---|---|
| r5 (e2) | 2.077 | 3.60 | 2.02 | 1.82 | 2.210 |
| **r9 (e5, pressure winds)** | **2.038** | **3.45** | 2.02 | **1.76** | **2.162** |

r9 (`calibration/earth/earth_e5_r9.json`: large-scale pressure 1.65, local
0.12, planetary scale 1,870 km, drag 3.5e-5 over sea and 8.9e-5 over land) is
better on training and on the held-out regions and is the new Earth
reference. East China's winter stays ~3 °C too warm: the pressure field has
no cold-season continental high strong enough to push polar air south.

On the map the pressure winds cannot simply be switched on: with the free
fit's other settings (tuned to the thermal wind) the map warms by 2.6 °C on
average and dries, and the zone score falls from 0.527 to about -0.03 at any
strength from 0.2 to 3 (`calibration/map_scan_slp*.json`). The map is being
refitted with them (`--physics e3b5`: the free fit's settings plus the
pressure-wind ones). After 400 evaluations at downsample 32 (sigma 0.12,
from the free fit with r9's pressure settings) the best zone score was 0.369,
flat from evaluation 145 on, against 0.505 for the free fit with the thermal
wind at the same resolution (`calibration/earth/free_e5_ds32_best.json`).
The map prefers the thermal wind, so the free fit keeps it: pressure winds
are the Earth physics, not the map's.

**Correction (17 October): the map does not reject the pressure winds, only
Earth's settings of them.** The free fit's thermal wind works at a small scale
(its temperature field smoothed over 366 km, with a 51° cross-isobar angle):
sea breezes and heat lows. The refit above started from r9's large-scale
pressure (1.65 hPa/K over 1,870 km, local term 0.12 hPa/K over 100 km) and
never found that scale. At downsample 32 on the free fit D2 (`scripts/map_scan.py`):

| D2 with | zonefit | strict |
|---|---|---|
| its thermal wind (reference) | 0.514 | 59.1 % |
| pressure winds at its own scale, 2 hPa/K over 366 km | 0.519 | 59.3 % |
| the same with r9's friction (8.9e-5 land, 3.5e-5 sea) | 0.518 | 59.5 % |
| **r9's large-scale term + a local term of 2 hPa/K over 366 km** | **0.517** | 59.1 % |
| r9's large-scale term at half strength + the same local term | 0.486 | 56.2 % |
| 2 hPa/K over 500 km | 0.479 | 57.1 % |

So one set of wind equations serves both worlds: Earth's planetary-scale
pressure plus a strong boundary-layer term at ~370 km. On Earth that local
term costs a little before refitting (training mean 2.038 → 2.070 at 1 hPa/K,
2.169 at 2 hPa/K; East China improves to 3.20 and 3.09); the two fits
below settle how strong it should be.

**The two fits (17-18 October).** On the map, a refit of every gene around
D2 with the unified winds (481 candidates, sigma 0.08) found nothing above
its start: D2 sits on a sharp peak that broad steps in ~80 dimensions only
fall off. Searching the seven pressure-wind genes alone works: 0.530 at
downsample 32 (241 candidates; D2 with its thermal wind 0.505 under the same
numerics), then 0.539 at downsample 16 (121 candidates; D2 0.527). The map's
planetary-scale term lands on Earth's own values without being told them:

| Fit | large-scale hPa/K, km | local hPa/K, km | friction land / sea (1/s) |
|---|---|---|---|
| Earth r9 | 1.65, 1,870 | 0.12, 100 | 8.9e-5 / 3.5e-5 |
| Earth r10 (local term free, started at the map's) | 1.15, 2,110 | 1.42, 329 | 3.8e-5 / 3.2e-5 |
| Map, pressure genes at downsample 16 | **1.77, 1,893** | 1.85, 323 | **9.9e-5** / 2.7e-5 |

Earth keeps a strong local term when it starts with one (r10, 241
evaluations from r9 with the map's local term) but scores worse than r9:
training 2.086 against 2.038, nine-region mean 2.203 against 2.162 (Chile
improves 3.45 → 3.22, south-west Australia worsens 1.76 → 2.07). So the
wind equations and their planetary-scale setting are shared; what differs
is how much small-scale (~330 km) thermal circulation each world wants,
and the map wants roughly what Earth tolerates at a 2 % cost. r9 stays
the Earth reference (`calibration/earth/earth_e5_r10.json` keeps r10).
At full detail (downsample 8, the same moisture iterations for both) the
pressure-wind map scores **0.529 against D2's 0.520**, strict agreement 59.1 %
for both: the cold-dry north 53 → 59 % recall, "tree" 55 → 59 %, swamp 45 → 47 %,
against cold-wet 76 → 71 % and the Mediterranean 67 → 64 % (Cs 78 → 77 %, dry
11 → 12 %). It is the new free fit (`calibration/earth/free_e5p_ds16.json`)
and the free-fit atlas is rebuilt from it: the map now runs on Earth's wind
equations and Earth's planetary-scale pressure, with a stronger local term.

### 4d. East China, taken apart (17 October)

East China is the worst training region under r9 (3.39 against 1.46-2.09
for the other five). Its distance splits into a temperature part of 1.51 and
a rain part of 1.89, and most of the rain part is timing: with the right
annual total it would still be 1.61. The model gives 65-100 mm in every month
against 29 mm in December and 199 mm in June: no monsoon. Temperature is too
warm from October to May (+3.3 to +5.7 °C, worst in March and April) and
slightly cool in July and August.

Taking January apart at 30°N, 114°E (Wuhan's cell): the land's own target
temperature is 10.1 °C against 4.5 °C observed, and neither transport nor
eddies change it (9.6 °C solved), because the winds come from the west
(+2.9, −1.4 m/s) instead of from the cold north. The north itself is too mild:
Mongolia is 5-7 °C too warm in January, so the continental high the pressure
winds build is too weak to beat the prescribed westerly belt (~4 m/s at
30°N in winter).

With the westerlies nearly removed and a stronger, sharper high
(`westerly_speed` 1, `slp_large` 4, `slp_scale_km` 1,200), January winds turn
northerly (~3 m/s), January's bias falls to +1.4 °C, the monsoon appears
(January 35 mm against 34, July 176 against 171) and East China's distance
drops to 2.95. The same settings make Florida's winter 8-10 °C too cold and
Iberia's summer 5-7 °C too cool (south-east US 1.72 → 2.69, Iberia 2.09 →
2.57): the model's continental highs cannot tell Eurasia from North America.

On WorldClim, the land share upwind to the west, with a memory of
1,000-2,000 km, and latitude explain 85 % of the variance of the annual
temperature range over land (latitude alone 60 %); Wuhan's westward land
share is 1.00 and Atlanta's 0.80, and the fit predicts their ranges within
2 °C. The model's continentality term already measures this along its own
winds with a ~1,700 km memory, but its domains reach only 1,100 km beyond the
scored region and treated air entering at the edge as having crossed only
the edge cell. Physics e6 (`far_fetch`) gives the edge the real world's
westward land share instead. On r9 unrefitted it moves the training mean from
2.038 to 2.119 and leaves East China unchanged; a domain twice as large
(2,200 km) moves East China only from 3.39 to 3.35; Earth's land profile in
the energy balance takes it to 3.20 but costs California and the Levant, as
in r6. Spring stays 5-6 °C too warm at 30°N whatever the winds (the land
target in early April is 23 °C against 17 °C observed), as it is, less
strongly, in the south-east US (+3.2 °C in April): humid east coasts warm
too early. East China stays the open problem; e6 remains an option (off by
default) for later fits.

**Refitted, e6 is the new Earth reference (r11, 18 October).** With
`far_fetch` = 1 and the pressure winds and their partners refitted from r9
(241 evaluations, sigma 0.06, `calibration/earth/earth_e6_r11.json`):

| Fit | Training (6) | E China | Chile | Cape | SW Australia | Nine-region mean |
|---|---|---|---|---|---|---|
| r9 (e5) | 2.038 | 3.39 | 3.45 | 2.02 | 1.76 | 2.162 |
| **r11 (e5 + e6)** | **2.016** | **2.97** | **3.37** | **1.89** | **1.55** | **2.102** |

East China's distance falls by 0.42 (January bias +2.3 °C against +3.0) and
all three held-out southern regions improve, so the edge fetch is a real
gain, not a training artefact; the fit raised the planetary-scale pressure
(1.99 hPa/K over 1,780 km against 1.65) and the land's seasonal amplitude
(0.86 against 0.72) while lowering the continentality factor (0.84 against
1.19): with true upwind land at the edge, less amplification is needed
inside. On the map the option has no effect (the map's surroundings are its
own procedural edge), so the map fit is unchanged.

## 5. On the fantasy map

Physics fitted on California and Iberia alone, dropped onto the live atlas's
world unchanged, dried the map out (strict agreement 12.7 %, painted
Mediterranean 88 % dry; the anchor scores 50.2 % and 11.2 % at the same
downsample-16 screening resolution): the anchor's world genes (reversed spin,
34°N, 21° tilt) were fitted together with the fantasy physics. So the world's
unknowns are refitted with the Earth physics held fixed, once per spin
direction (181 evaluations each, downsample 16, `zonefit`;
`calibration/earth/world_e1_retro.json`, `world_e1_pro.json`):

![map comparison](../output/earth_on_map/world_e1_compare.png)

| Same screening resolution (downsample 16) | zonefit | strict | Med recall | Med Cs / dry | cold-dry | hot-dry | swamp | tree | cold-wet | warm-wet |
|---|---|---|---|---|---|---|---|---|---|---|
| live atlas (fantasy physics, reversed spin) | 0.411 | 50.1 % | 36 % | 39 % / 11 % | 72 % | 61 % | 11 % | 52 % | 78 % | 55 % |
| Earth physics, reversed spin (35.5°N, tilt 28.9°) | 0.186 | 32.8 % | **66 %** | **70 % / 8 %** | 0 % | 20 % | 0 % | 1 % | 86 % | 34 % |
| Earth physics, Earth spin (32.7°N, tilt 31.7°, north 29° W of up) | 0.209 | 28.6 % | 33 % | 43 % / 9 % | 1 % | 56 % | 0 % | 81 % | 79 % | 14 % |

With physics that works on Earth and reversed spin, the painted Mediterranean
band comes out *better* than in the live atlas — two thirds of it labelled
Mediterranean, 70 % Cs and only 8 % dry, the user's main concern — but the
painted cold-dry north turns into cold forest (500–1,000 mm of rain where
cold-dry needs a few hundred), the swamp and "tree" zones vanish and the
hot-dry south is too wet. With Earth's spin the west coast becomes
Mediterranean instead of the painted warm-wet, which is why the map favours
reversed spin under either physics. The live atlas's higher overall agreement
relies partly on physics that is wrong on Earth (section 3).

A joint fit (`scripts/joint_calibrate.py`) then fitted physics and world
together to the map, the physics penalised as soon as its mean Earth climate
distance rose above 2.25: best zonefit 0.202 at Earth distance 2.23
(`calibration/earth/joint_e1_retro.json`, the Earth-physics atlas). A free fit
of the same physics with no Earth constraint reached 0.458 in stages
(`free_e2new_retro.json`) and 0.499 with every world and physics setting free
at once (`free_e2_all_retro.json`, the free-fit atlas: per-setting CMA-ES step
sizes, 0.1-0.5 x sigma for the world's orientation, latitude, tilt, tiers and
beyond-the-edge land; at downsample 8 strict 57.1 %, painted Mediterranean
82 % Cs and 0 % dry, cold-dry 60 %, hot-dry 43 %, swamp 35 %;
`output/earth_on_map/free_all_compare.png`).

### 5.1 What makes the painted cold-dry north dry?

`scripts/physics_attribution.py` swaps one group of the free fit's physics
constants at a time into the joint (Earth-realistic) fit, world unchanged
(downsample 16; `output/earth_on_map/attribution_joint_vs_free.json`):

| Swapped from the free fit | zonefit | strict | cold-dry | Mediterranean | hot-dry |
|---|---|---|---|---|---|
| nothing (joint fit) | 0.202 | 33.1 % | 0 % | 62 % | 18 % |
| circulation | 0.158 | 22.6 % | 0 % | 23 % | 0 % |
| temperature | 0.099 | 20.8 % | 2 % | 40 % | 26 % |
| moisture supply | 0.195 | 30.9 % | 1 % | 69 % | 22 % |
| rain (incl. e2 closure) | 0.171 | 32.5 % | 0 % | **90 %** | 38 % |
| sinking air | 0.174 | 30.1 % | 0 % | 42 % | 2 % |
| **storm eddies** | **0.219** | 32.3 % | **55 %** | 48 % | 26 % |

Only the storm-eddy group makes the cold-dry zone: the free fit mixes
moisture by eddies over a 423 km scale (the Earth fits: ~900 km) and weakens
them more in summer (seasonality 0.7 vs 0.22). A scan of the eddy settings on
the joint fit, scored on the map and on all nine Earth regions
(`scripts/eddy_scan.py`, `output/earth_on_map/eddy_scan.json`):

| eddy scale / seasonality | zonefit | strict | cold-dry | Mediterranean | Earth d (9 regions) | C Asia | SE US |
|---|---|---|---|---|---|---|---|
| 896 km / 0.22 (joint fit) | 0.201 | 33.1 % | 0 % | 62 % | 2.336 | 1.66 | 2.01 |
| 896 km / 0.70 | 0.206 | 37.4 % | 0 % | **78 %** | 2.427 | 1.74 | 2.04 |
| 750 km / 0.45 | 0.207 | 34.2 % | 1 % | 68 % | 2.389 | 1.79 | 2.09 |
| 650 km / 0.55 | 0.211 | 33.8 % | 2 % | 68 % | 2.419 | 1.88 | 2.17 |
| 550 km / 0.70 | 0.214 | 31.9 % | 7 % | 65 % | 2.459 | 1.98 | 2.29 |
| 423 km / 0.22 | 0.217 | 30.3 % | **53 %** | 40 % | 2.501 | 2.16 | 2.64 |

The cold-dry zone switches on only below ~550 km, and every step there costs
Earth realism: shorter eddy mixing starves continental interiors (Central Asia
61 mm a year against 228 observed at 423 km) and the Gulf coast. On Earth a
dry interior at 40–45° needs either a long overland fetch or mountains
upwind (Manabe & Broccoli 1990); the painted north has neither at the map's
scale, so Earth-like physics keeps it forested. Stronger summer weakening of
the eddies alone is cheaper (Earth d +0.09) and lifts the Mediterranean
match from 62 % to 78 %.

### 5.2 Is the free fit stuck in a local optimum?

A restart campaign (`scripts/campaign.py`, `calibration/campaign/plan.json`)
ran independent CMA-ES fits from deliberately different starting worlds at
downsample 32, which ranks candidates like downsample 16 (Spearman 0.97 over
16 logged candidates, 0.95 over the better half) at a fifth of the cost.

Large steps do not work in 72 dimensions: with sigma 0.3 every candidate was
effectively random (the map orientation alone, with ±108° jumps, explains most
of the loss; Spearman −0.51 between score and orientation distance), and even
sigma 0.2 found nothing in 361 evaluations. So each start got a proper local
fit instead (sigma 0.08, orientation ±14° per step, 481 evaluations):

| Start | Best zonefit (downsample 32) |
|---|---|
| current free fit (reference) | **0.499** |
| live atlas world with its own (v9-era) physics | 0.448 |
| current fit with Earth's spin | 0.332 |
| random world 0 (31.8°N, tilt 17°, retro) | 0.375 |
| random world 2 (28.6°N, tilt 16°, retro; ended 33.2°N, 16.5°, −19°) | 0.446 |
| random world 3 (38.3°N, tilt 23°, Earth spin) | 0.266 |
| random world 1 | stopped at 81 of 481 (0.323) |

No other basin came within 0.05 of the current fit in the same budget; the
reversed spin is preferred again (both Earth-spin starts end lowest). The
current free fit is not a lucky local optimum among those tried, though the
two runners-up (the live atlas world and random world 2) had far fewer
evaluations behind them.

Polishing the runner-up changed that. Random world 2, refined at downsample
32 (0.505 there) and then at 16 (193 evaluations, 0.527), scores **0.520 at
downsample 8 against 0.497 for the previous free fit** (strict agreement
59.1% against 57.4%). It is now the free-fit atlas: reversed spin, 32.9°N,
15.8° tilt, true north 7.4° anticlockwise of the map's top edge
(`calibration/earth/free_d2_polish_ds16.json`). It trades some Mediterranean
purity (78% Cs, 11% dry, against 82% and under 1%) for better cold-wet,
warm-wet and swamp recall.

## 6. Tried and removed (no measurable effect)

- **Coastal seas following the air over them** (shallow shelf seas chilled by
  offshore continental air): East China stayed +4.1 °C; its warm winters come
  from the land temperature itself, not the coastal sea.
- **A trapped marine layer** (low coastal land pulled toward the nearest sea's
  temperature when warmer, below a 0.8–1 km inversion, fading over 50 km):
  Valparaíso's summer moved 30.2 → 29.7 °C against 19.2 observed. At 56 km
  the coastal cells' temperature is set by the storm-eddy heat mixing (fitted
  to a ~900 km scale), which averages the coast with the hot interior.
- **A crest squeeze** (air fast enough to climb a ridge, h_eff = min(h, U/N),
  saturates at the crest: Smith & Barstad's dividing streamline, to make rain
  shadows): the lee dried a little (Reno 441 → 347 mm, observed 241) but all
  high ground got wetter (Fresno 802 → 1,110 mm against 382, Tashkent 290 →
  898 against 474); the mean distance over California, Central Asia, the
  Levant and Iberia rose from 1.84 to 1.93–2.11 even with the orographic
  boost cut to a half or a quarter.
- **Seasonal land coupling** (e2, `land_coupling_insolation`) is kept as an
  option but barely moved East China (Wuhan January 10 °C vs 4 °C observed):
  the air arriving there is itself 4 °C too warm, with no Siberian High in a
  latitude-mean land temperature.

The e2 rain closure (exponential convective rain, no background ascent,
sub-cloud evaporation) is what helps: Miami 936 → 1,548 mm (observed 1,395)
in a hand test, and the free map fit chose it (no background ascent).
