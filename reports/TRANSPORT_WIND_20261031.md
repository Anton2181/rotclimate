# Transport wind, dry ground and the seas: r40's remaining regional errors, 31 October 2026

Follow-up to `reports/PHYSICS_GAPS_20261030.md` (§10, e57) and
`reports/SUMMER_RAIN_20261030.md` (§9, e61), which both ended on the same
proposal: give the model a separate transport wind (the ~850 hPa flow, little
slowed by the ground) beside the surface wind that carries heat. All runs are
the 31 development regions at 56 km against r40
(`output/transport_wind_20261031/`; r40 reproduces bit for bit with every
new switch off).

## 1. Separate land friction for the heat and the water winds (e62, opt-in)

`heat_land_friction` slows the zonal belts over land (land share smoothed
over 300 km, as e57) only in the wind the temperature solver and the
land-fetch memory use; `water_land_friction` only in the wind that carries
water, lifts it over terrain and makes convergence. e57 is both at once.

| 31 regions against r40 | T MAE | rain loss | S | training | former holdout | mid-latitude | dev12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| heat 0.3 | −0.26 % | +0.27 % | 1.0001 | 1.004 | 0.998 | 0.993 | 1.002 |
| heat 0.5 | +0.14 % | +0.50 % | 1.0032 | 1.010 | 1.000 | 0.992 | 1.006 |
| heat 0.7 | +1.31 % | +0.79 % | 1.0105 | 1.021 | 1.006 | 0.998 | 1.013 |
| water 0.3 | −0.07 % | +0.25 % | 1.0009 | 1.009 | 0.993 | 0.996 | 1.002 |
| water 0.5 | −0.14 % | +1.06 % | 1.0046 | 1.019 | 0.988 | 1.001 | 1.005 |
| heat 0.3 + water 0.3 | −0.38 % | +0.41 % | 1.0002 | 1.013 | 0.990 | 0.986 | 1.003 |

The split does not resolve e57's conflict. Heat friction is a seasonal-range
knob: it mends the regions whose range is too small (US Midwest −4.2 °C →
−3.2 at 0.5, T MAE 1.60 → 1.35; western Europe, Great Basin, East Australia)
and spoils those whose range is already too large (Anatolia +4.0 → +4.8,
the Levant +2.3 → +3.0, Central Asia +1.0 → +2.3, Korea). Water friction
dries the winter-wet west (western Europe 924 → 807 mm against 875, Great
Basin 484 → 445 against 337, California 488 → 449 against 392) and starves
the same interiors (Anatolia 371 → 331 against 560, the Levant 269 → 241
against 394, Central Asia 186 → 149 against 228). The interiors want the
strong westerlies in both winds, so the conflict is not heat against water.

## 2. What the interiors lack is a warm winter sea

The attribution runs of the physics report (observed fields in place of the
model's, r39) separate the two: observed winds make Anatolia and the Levant
worse; the observed sea surface fixes them (Anatolia rain 358 → 602 mm
against 560, T MAE 1.87 → 1.42 °C, seasonal range error +4.2 → +2.5; the
Levant 261 → 434 mm against 394, range +2.4 → +1.2).
`scripts/compare_sea_surface.py` (new) sets r40's monthly sea surface beside
WOA18 over each region's seas, split into enclosed seas (the model's own
enclosure share above one half) and open sea
(`output/sea_20261031/sst_r40_{4,coasts}.json`). Seasonal mean bias, °C
(southern regions in season order):

| seas | winter | spring | summer | autumn | annual range, model / WOA18 |
|---|---:|---:|---:|---:|---:|
| Mediterranean by Anatolia, the Levant (enclosed) | −6.0 | −2.5 | −2.7 | −4.5 | 13–16 / 10–13 |
| off Iberia, Morocco (open) | −5.5 | −5.2 | −2.9 | −3.5 | 9 / 5–6 |
| NE Atlantic by Britain, western Europe (open) | −3.2 | −2.9 | +0.8 | +0.8 | 12–13 / 7 |
| NE Pacific by California, Pacific NW (open) | −1.7 | −1.4 | +2.2 | +1.3 | 9–11 / 4–6 |
| SW Australia, Cape, NZ, Patagonia (open) | −5.5 | −5.3 | −2.5 | −2.3 | 8–11 / 4–6 |
| Yellow Sea, Bohai, inner East China Sea (enclosed) | +2.2 | +6.1 | +1.9 | +0.5 | 11–18 / 18–21 |
| Kuroshio off Japan (open) | −0.1 | +0.2 | −1.9 | −1.2 | 9 / 12 |
| Gulf of Mexico, off the SE US (open) | −0.1 | −0.4 | −1.7 | −0.4 | 7 / 8–10 |

The seas on the eastern sides of the oceans (west coasts of continents) are
4–7 °C too cold in winter with seasonal ranges about twice WOA18's; East
Asia's shelf seas warm 5–7 °C too early in spring with ranges too small.
This is the known cold-sea balance: a sea fitted to WOA18 makes the land
fail (`reports/CITY_RAIN_20261024.md`: S 1.17), a joint sea-and-land search
found no candidate, and r38's warm-sea search (`reports/STABLE_LAND_20261025.md`)
bought its land gain with a slightly worse sea. The land settings are fitted
around the cold sea; correcting it needs a structural change on the land
side, which this report does not attempt.

## 3. North India: a dry, sheltered plain on a latitude's mean land column

North India is r40's worst region (T MAE 3.40 °C, annual bias −2.9, rain
373 against 761 mm); its Indo-Gangetic plain (258 cells below 300 m, 27.5° N)
is 3.7 °C too cold, 4.3 in winter and 4.7 before the monsoon, while the
Himalayan and Tibetan cells beside it are within 0.5 °C. Iran's low and
middle ground is 2.7–4.1 °C too cold in every season. Halving the eddy heat
exchange moves North India by only 0.2 °C and a quarter of the heat
diffusion by nothing, so mixing across the Himalaya is not the cause. A trace
of the plain's cells (monthly means, °C):

| | Jan | Mar | May | Jul | Sep | Nov |
|---|---:|---:|---:|---:|---:|---:|
| observed (WorldClim) | 15.0 | 23.5 | 33.2 | 30.9 | 29.2 | 21.0 |
| model air | 10.9 | 18.7 | 28.7 | 29.2 | 26.0 | 16.9 |
| land equilibrium | 13.3 | 20.3 | 29.9 | 30.5 | 27.2 | 19.0 |
| zonal land column at 27.5° N | 13.1 | 20.5 | 30.7 | 34.1 | 30.0 | 19.0 |
| zonal sea at 27.5° N (with r40's offset) | 19.2 | 18.1 | 20.0 | 23.2 | 24.4 | 22.4 |

The equilibrium is the latitude's mean land column, 2–3 °C colder than the
dry, sunny, sheltered plain in the dry season, and the air sits another
1.3–2.4 °C below it, cooled by a sea that is ~5 °C colder than the Arabian
Sea and the Bay of Bengal in winter. Dry-ground heating (e54, sunshine on dry
soil heats the boundary layer, gated off on coasts by the advected land
share) addresses the first part.

| 31 regions against r40 | T MAE | rain loss | S | training | former holdout | mid-latitude | dev12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| dry heating 3.0, coast gate 0.6 | −1.83 % | +0.69 % | 0.9943 | 0.993 | 1.035 | 1.026 | 0.972 |
| + heat friction 0.3 | −2.56 % | +1.00 % | 0.9922 | 0.995 | 1.030 | 1.016 | 0.972 |
| + water friction 0.2, cold_high_storms 0.3 | −2.42 % | +0.42 % | **0.9900** | 1.001 | 1.026 | 0.999 | 0.972 |

North India (region score 0.85), Morocco (0.88), Iran (0.92) and the US
Midwest (0.90) improve most; Manchuria, the North China Plain, Korea and
East China worsen (dry heating warms springs that are already 2–4 °C too
warm), and so do the cold-current Mediterranean coasts, SW Australia and
Chile (already 1.7 °C too warm).

## 4. Inland seas with a lag (e63, opt-in)

East Asia's spring warmth follows its shelf seas, and those warm early
because an enclosed sea takes a share of the land's equilibrium at once.
`inland_sea_lag_days` lets enclosed seas and lakes follow it with a memory
(a 30–50 m mixed layer of their own). At 45 days the April–May bias of the
Yellow Sea and the Bohai falls by 2–3 °C (Korea's enclosed sea +6.2 → +3.8
in April) but winter and autumn rise by as much (+1.6 → +3.3 in January,
+0.3 → +3.1 in November): those seas need a larger seasonal swing, not only
a later one (`output/sea_20261031/sst_lag45_eastasia.json`). Left to the
refit, with the inland-sea strength and winter overturning.

## 5. Frozen refit (running)

Plan `calibration/transport_refit_20261031/plan.json`, frozen and committed
before any result: from the combined screen (S 0.9900), eight levers — heat
and water land friction, dry heating and its coastal gate, cold-high storm
damping, inland-sea strength, lag and winter overturning — 72 candidates
scored as the gate scores against r40. Validation: fresh paired dev31 runs
under policy v2, the paired 28 km check, then the fresh sealed six declared
on 31 October (never run) once.
