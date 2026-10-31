# Transport wind, dry ground and the seas: r40's remaining regional errors, 31 October 2026

**Outcome.** Nothing adopted; r40 stays. Splitting the land friction
between the heat and water winds (e62) does not help by itself; the
interiors it was meant for lack a warm winter sea instead (r40's
Mediterranean is ~6 °C too cold in January). Dry-ground heating gated to
warm ground (e54c) with small frictions passed the 31-region gate (S 0.9879,
every group better; North India's temperature error 3.40 → 2.99 °C, Iran's 3.28 → 2.81) and the 28 km check (0.9893),
then failed the fresh sealed six (1.0405: the Kazakh steppe and Hokkaido).

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

## 5. Frozen refit of the frictions, dry heating and the inland seas (not adopted)

Plan `calibration/transport_refit_20261031/plan.json`, frozen and committed
before any result: from the combined screen (S 0.9900), eight levers — heat
and water land friction, dry heating and its coastal gate, cold-high storm
damping, inland-sea strength, lag and winter overturning — 72 candidates
scored as the gate scores against r40.

No candidate cleared every group. The lowest cost (candidate 68, 0.9992):
heat friction 0.05, water friction 0.11, dry heating 0.49 with coastal gate
0.61, cold_high_storms 0.45, inland-sea lag 2 days, warming 3.81, winter
overturning 0.44. Validation (`output/transport_wind_20261031/refit/`):

| check | result |
|---|---|
| 31 regions, policy v2 | S 0.9930 (T −0.8 %, rain loss −0.6 %); training 0.996, mid-latitude 0.988, dev12 0.990, **former holdout 1.0031: fails** |
| paired 28 km | S 0.9950 (passes) |
| fresh sealed six | not run (the development gate failed); still unseen |

The holdout's loss is Chile (1.010) and SW Australia (1.008), whose summers
dry heating warms, and Japan (1.004), which the stronger cold-high damping
warms while it fixes Manchuria's and Korea's rain (Manchuria 0.950, Korea
rain ×0.94, temperature ×1.04). The search moved away from dry heating,
because at full strength it warmed North China's and Manchuria's dry
winters, and kept the frictions small. r40 stays.

## 6. Dry heating only on warm ground (e54c, opt-in)

Dry ground warms the air through the day's sensible heat; a low winter sun
and long clear nights cancel it, which is why the dry winter plains of North
China and Manchuria are cold. `dry_heating_warm_c` lets e54 act fully where
the land equilibrium is 8 K above this temperature and not at all below it.

| 31 regions against r40 | T MAE | rain loss | S | training | former holdout | mid-latitude | dev12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| dry heating 3.0, coastal gate 0.6 | −1.83 % | +0.69 % | 0.9943 | 0.993 | 1.035 | 1.026 | 0.972 |
| … on warm ground (12 °C) | −2.06 % | +0.30 % | 0.9912 | 0.996 | 1.023 | 1.013 | 0.971 |
| refit candidate 68 | −0.78 % | −0.62 % | 0.9930 | 0.996 | 1.003 | 0.988 | 0.990 |
| … + dry heating 1.5 on warm ground (12 °C) | −1.66 % | −0.63 % | 0.9885 | 0.993 | 1.009 | 0.990 | 0.980 |
| … + coastal gate 0.78 | −1.55 % | −0.71 % | 0.9887 | 0.993 | 1.004 | 0.990 | 0.981 |
| … dry heating 2.0 at 15 °C, gate 0.78, cold_high_storms 0.3 | −1.67 % | −0.61 % | 0.9886 | 0.994 | 1.003 | 0.993 | 0.980 |

The gate halves dry heating's cost in East Asia (Manchuria 1.20 → 1.12,
North China Plain 1.17 → 1.10 at strength 3.0) and keeps most of North
India's gain (0.85 → 0.88). On the refit's best candidate it brings S to
0.9885–0.9887 with every group better except the former holdout, now
0.3–0.4 % worse (Chile, SW Australia).

## 7. Second frozen refit: passes development and 28 km, fails the fresh sealed six (not adopted)

Plan `calibration/dry_heat_refit_20261031/plan.json`, frozen and committed
before any result: from the last screen above, seven levers (dry heating,
both its gates, cold-high damping, the two land frictions, winter
overturning), 56 candidates against r40. 37 of them cleared every group.
The lowest cost (candidate 38): dry heating 2.66 above a 15.7 °C
equilibrium, coastal gate 0.83, cold_high_storms 0.29, heat friction 0.16,
water friction 0.13, deep-sea winter overturning 0.80.

| check (`output/transport_wind_20261031/dry_heat_refit/`) | result |
|---|---|
| 31 regions, policy v2 | **S 0.9879, passes**: T 1.807 → 1.773 °C (−1.9 %), rain loss 0.4329 → 0.4306 (−0.5 %); training 0.996, former holdout 0.999, mid-latitude 0.993, dev12 0.979 |
| paired 28 km | **S 0.9893, passes** |
| fresh sealed six (first use) | **S 1.0405, worse: not adopted** |

| sealed region | S | T MAE r40 → candidate | seasonal range error | rain, mm (obs) |
|---|---:|---|---|---|
| Kazakh steppe | 1.162 | 2.15 → 2.54 °C | +3.6 → +5.3 | 194 → 171 (295) |
| Hokkaido | 1.065 | 3.02 → 3.31 | +6.0 → +7.1 | 977 → 998 (1,091) |
| Canadian prairies | 1.000 | 2.74 → 2.73 | −5.0 → −4.2 | 419 → 401 (406) |
| southern Italy | 0.997 | 1.62 → 1.60 | +4.2 → +4.2 | 719 → 745 (789) |
| north Queensland | 1.000 | 1.11 → 1.09 | +0.1 → +0.1 | 1,957 → 1,980 (874) |
| Namib and Kalahari | 0.965 | 1.33 → 1.18 | +0.5 → +0.7 | 118 → 111 (237) |

The two climates the 31 development regions lack, a cold steppe and a cold
winter-monsoon coast, are where it fails: their seasonal ranges, already
too large, grow. The heat friction makes their air more continental in
winter (the steppe −0.3 to −0.5 °C) and dry heating warms the steppe's
summer (+0.9 to +1.3 °C in June–August), which r40 already runs 1.5–2.2 °C
too warm. On the development set the same levers mended the Midwest's
too-small range and North India's, Iran's and Morocco's cold. The sealed
set has done its job: dry heating needs to know a desert from a steppe
(the steppe's summer heat is already there through the continental land
column), and more continental heat in general is not supported.

r40 stays. The fresh sealed six have now been seen by one candidate
(`calibration/sealed_20261031/declaration.json`); because this result points
at a mechanism (dry heating on cold steppes), a later design that uses it
should come with a fresh sealed set.

## 8. What this leaves

* Opt-in switches added, all off in r40 (bit-identical): e62
  `heat_land_friction` / `water_land_friction`, e63 `inland_sea_lag_days`,
  e54c `dry_heating_warm_c`.
* North India and Iran remain the worst regions. A dry-heating design that
  does not warm cold steppes could gate on the equilibrium's annual mean or
  on the latitude (subtropical dry season) rather than on the month's
  warmth; it must be designed without further looks at the sealed regions'
  numbers beyond this report.
* The sea surface is the deeper error behind Anatolia, the Levant, the
  Mediterranean coasts and part of North India (§2–3). It is entangled with
  the land settings and needs the land-side structural change already noted
  in HANDOFF.md (land surface layer or two-tile coast).

## Reproduce

```sh
python -I scripts/benchmark_local.py --fit calibration/local_accuracy_20261023/r40_params.json --regions dev31 --set '{"heat_land_friction": 0.3}' --out output/transport_wind_20261031/hf03
python -I scripts/compare_sea_surface.py --params calibration/local_accuracy_20261023/r40_params.json --regions anatolia levant central_asia iberia --out output/sea_20261031/sst_r40_4.json
python -I scripts/gate_calibrate.py --plan calibration/transport_refit_20261031/plan.json --out calibration/transport_refit_20261031/search
python -I scripts/gate_calibrate.py --plan calibration/dry_heat_refit_20261031/plan.json --out calibration/dry_heat_refit_20261031/search
OUT=output/transport_wind_20261031/dry_heat_refit REF_NAME=r40 REF_FIT=calibration/local_accuracy_20261023/r40_params.json BEST=calibration/dry_heat_refit_20261031/search/best_params.json SEALED_SPEC=calibration/sealed_20261031/regions.json bash scripts/validate_monsoon_refit.sh
```

## 9. Dry heating only in warm climates (e54d) and what the sealed failure taught

The first 31-October sealed set, run once in §7, is development data from
now on; a fresh set b (Algerian Sahara, Sahel, Najd, Mongolia, Bengal,
Deccan; `calibration/sealed_20261031b/`) was declared before any run of the
design below. `dry_heating_mean_c` (e54d) lets dry heating act only where the
cell's annual-mean land equilibrium (with its continental adjustments) is
warm: full 8 K above the threshold, none below. Screens on the first refit's
best candidate (`output/dry_heat_v2_20261031/`), scored against r40 on dev31
and on the retired sealed set:

| variant | dev31 S | T | rain loss | mid-latitude | retired set S | Kazakh steppe | Hokkaido |
|---|---:|---:|---:|---:|---:|---:|---:|
| first refit's best (§7) | 0.9879 | −1.9 % | −0.5 % | 0.993 | 1.0405 | 1.162 | 1.065 |
| without heat friction | 0.9880 | −1.7 % | −0.7 % | 0.998 | 1.0352 | 1.146 | 1.070 |
| … + e54d at 12 °C | 0.9852 | −2.3 % | −0.7 % | 0.995 | 1.0319 | 1.124 | 1.083 |
| … with r40's storm damping | — | | | | 1.0098 | 1.073 | 0.998 |
| … without water friction | — | | | | 1.0150 | 1.044 | 1.088 |
| **v1: no frictions, r40's damping, e54d 12 °C** | 0.9881 | −2.3 % | −0.1 % | 1.010 | **0.9936** | 0.994 | 1.004 |

The cold-high storm damping (0.29 in the first refit) made Hokkaido more
continental, the water-wind land friction starved the Kazakh steppe of
westerly water, and gated dry heating harms neither. v1 fixes the retired set
but fails the mid-latitude group (Manchuria 1.048, eastern Europe 1.029),
which wanted the stronger damping. A frozen refit
(`calibration/dry_heat_v2_refit_20261031/plan.json`) balances dry heating,
its three gates, the storm damping, the winter overturning and the rain time
scale with the retired set as an extra guarded group
(`scripts/gate_calibrate.py` now takes `extra_groups`), to be validated on
sealed set b.
