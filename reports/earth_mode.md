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

## 5. Next

The six-region fit with all of the above (`calibration/earth_r4`) and its
held-out scores complete section 3. Then the Earth-fitted physics goes onto
the fantasy map with only the world's unknowns free
(`calibrate.py --physics world`), judged by the handoff's promotion guards.
