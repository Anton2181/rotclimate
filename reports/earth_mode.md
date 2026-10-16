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

(56 km cells; d lower is better)

| Physics | CA | Iberia | SE US | Levant | C Asia | E China | Chile* | Cape* | SW Aus* | mean |
|---|---|---|---|---|---|---|---|---|---|---|
| fantasy-fitted (live atlas anchor) | 4.13 | 3.43 | 2.75 | 3.59 | 3.09 | 3.85 | 4.55 | 4.11 | 3.25 | 3.64 |
| fitted on CA + Iberia only (stopped early) | 1.78 | 1.74 | 4.46 | 1.97 | 2.46 | 6.21 | 3.12 | 2.15 | 2.65 | 2.95 |

\* held out of every fit.

The fantasy-fitted physics is ~2× too wet and 3–4 °C too cold in both
Mediterranean regions and keeps almost no Cs (0–6 %); it fits the humid
south-east US well (Köppen 87 %). Fitting California and Iberia alone fixes
them (Köppen 39–52 %, Cs kept 33–45 %, coastal winter rain 290–370 mm) and
transfers to the held-out southern Mediterranean coasts, but turns the humid
south-east US and east China 5–7 °C too hot and too dry. So the physics must
be fitted on all zone types at once.

## 4. What calibration could not fix: new physics (e1)

City climographs showed three structural errors that no parameter setting of
the V9 model removed:

1. **No real summer drought.** Rain-rate suppression under the subtropical
   highs cannot dry a supply-limited column: the water piles up until it rains
   anyway (San Francisco 45 mm in August, observed ~1 mm).
2. **Rainy season 1–1½ months early** (San Francisco 85 mm in September,
   observed ~5 mm), because the circulation was fixed to lag the sun by 30 days.
3. **Spring on land a month early** (April in east China 8–9 °C too warm,
   Memphis +6 °C, summer peaking in June).

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

## 5. Next

Section 3 is completed with the six-region fit (`calibration/earth_r2`) and
its held-out scores, then the Earth-fitted physics goes onto the fantasy map
with only the world's unknowns free (`calibrate.py --physics world`), judged by
the handoff's promotion guards.
