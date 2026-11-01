# Why r41's deserts are too cold — 1 November 2026

**Finding.** r41's hot deserts and dry subtropics run 2.5–5 °C too cold.
Their summers are too mild. Three causes were ruled out:
- the model's too-high desert rain;
- the dryness of the ground;
- any setting of the existing levers.

The missing piece is the compression warming of air sinking along the
Hadley cell's descending branch. A new opt-in term (e71) supplies it, gated
so that it reaches the ground only inland and not under a coastal marine
layer. With it, the 31 development regions improve (S 0.982, temperature
error −3.3 %) and so does the retired desert set (0.935). Two groups still
worsen: the holdout (1.010) and the mid-latitudes (1.005).

A frozen refit (`calibration/desert_refit_20261101/plan.json`) is
balancing it against the land offset, the cold-air pool and the wet-ground
sunshine term. It will be judged on sealed set c, which has never been run.

## The error

r41's temperatures in these regions:

| region | annual bias | seasonal-range error | worst months | model / observed rain |
|---|---:|---:|---|---:|
| Algerian Sahara | −2.6 °C | −5.5 °C | Jun–Sep −4.6 to −5.8 | 176 / 26 mm |
| Najd | −5.0 °C | −4.5 °C | all year, Jul–Aug −7.1 to −7.7 | 364 / 124 mm |
| Sahel | −3.1 °C | −1.6 °C | Apr–Jun −3.3 to −4.9 | 581 / 521 mm |
| Deccan | −3.0 °C | −1.2 °C | dry season Jan–May −4.4 to −5.4 | 799 / 1,129 mm |
| north India | −2.8 °C | | all year −1.2 to −3.5 | |
| Iran | −3.1 °C | | Jun–Nov −3.4 to −4.3 | |

The first four are retired sealed set b, now development data. North India
and Iran are development regions.

In Najd the model rains 25–39 mm in every month; the observed summer gets
2–4 mm. The Sahara gets a monsoon that reaches too far north: 34–41 mm a
month in July–August against 1–5.

An earlier version of the r41 report called the deserts "warmer-wrong".
That was a mistake, now corrected: r41 made them slightly colder.

## What was tried (r41 + each change; dev31 and both retired sealed sets)

| change | dev31 S | holdout | mid-lat. | retired a | retired b (deserts) |
|---|---:|---:|---:|---:|---:|
| gated dry heating 2.7 K (e54b/c/d) | 0.9903 | 1.0005 | 1.0028 | 0.995 | 0.985 |
| gated dry heating 4.5 K | 0.9897 | 1.0010 | 1.0055 | 0.994 | 0.979 |
| … + annual-dryness gate 0.5 (e54e, new) | 0.9979 | 0.9996 | 1.0021 | 0.998 | 0.995 |
| sinking along the whole descending branch (e70, new) | 0.9995 | 1.0016 | 1.0004 | 1.005 | 0.990 |
| … + subsidence 0.5 | 1.0593 | 1.0971 | 1.0952 | 1.074 | 0.972 |
| compression warming 2 K (e71, new) | 1.0039 | 1.0840 | 1.0104 | 1.002 | **0.939** |
| … 3 K, fading over 10° to the Hadley edge (e71b) | 0.9929 | 1.0447 | 1.0041 | 1.001 | **0.932** |
| … + wet ground excluded (e71c) | 0.9937 | 1.0339 | 1.0032 | 0.995 | 0.959 |
| … 3 K, inland air only, chi0 0.5 (e71d) | 0.9851 | 1.0115 | 1.0037 | 0.994 | 0.938 |
| **… 4 K, chi0 0.7 (screen c7)** | **0.9816** | 1.0100 | 1.0050 | 0.996 | **0.935** |

What the screens show:
- **Desert rain is not the cause.** Cutting it with sinking along the whole
  branch (e70) barely changes desert temperatures. Stronger sinking ruins
  mid-latitude rain.
- **Dry heating stays small.** It is limited by the damp soil the rain floor
  leaves behind. It also warms East Asia through the dry interior upwind of
  Manchuria, so the annual-dryness gate removes the benefit and the damage
  in proportion.
- **Compression warming is the first lever that moves the deserts.** At c7
  the Sahara goes 2.77 → 2.42 °C, Najd 4.96 → 4.46, Sahel 3.12 → 2.42 and
  Deccan 3.06 → 2.72. North India improves to 0.87, Iran to 0.91, Texas to
  0.92 and Morocco to 0.94.
- **Only some places need it.** Ungated, it over-warms the southern
  mid-latitude coasts (SW Australia, Victoria, Chile, South Brazil). The
  coastal gate (air that has crossed land) removes most of that. What is
  left is East Asia: East China, the North China Plain and Manchuria, about
  1.04 each.

## New opt-in switches (all off; r41 reproduces bit for bit)

| switch | name | what it does |
|---|---|---|
| e70 | `subsidence_branch`, `subsidence_branch_gap` | the rain-damping sinking extends from ITCZ + gap to the Hadley edge |
| e54e | `dry_heating_arid` | dry heating only where the soil's one-year mean is dry |
| e71 | `subsidence_warming` | land warming across the descending branch, × (1 + summer factor) |
| e71b | `subsidence_warming_taper` | the warming fades over the last degrees to the edge |
| e71c | `subsidence_warming_wet` | wet ground loses it (rain means rising air) |
| e71d | `subsidence_warming_chi0` | only air that has crossed land carries it down |

## Refit

**Plan:** `calibration/desert_refit_20261101/plan.json`, frozen before the
search.

**Search:** starts at screen c7, 80 candidates. Knobs:
- the warming and its four gates;
- the land offset, the cold-air pool and `wet_sun`.

**Guards:** both retired sealed sets.

**Validation:** fresh paired dev31 under policy v2, then the paired 28 km
check, then sealed set c once.

**Result: not adopted.**

| check | result |
|---|---|
| search | 80 candidates; best is candidate 39, cost 0.9927 |
| fresh paired dev31, policy v2 | **S 0.9826**, every group passes; temperature 1.761 → 1.711 °C (−2.8 %), rain loss −0.7 % |
| retired desert set b | 0.959 (during the search) |
| retired set a | 1.005 (during the search) |
| paired 28 km | **0.9964**, passes |
| sealed set c, run once | **1.0159**, worse |

Candidate 39's settings:
- e71 3.8 K;
- taper 1.4°;
- chi0 0.89 (strongly inland air only);
- wet gate 0.12;
- branch gap 10.9°;
- land offset −1.25 (r41: −0.98);
- `continental_mean` 6.72;
- `wet_sun` 0.69.

Sealed set c by region (r41 → candidate):

| region | S | temperature MAE | annual bias |
|---|---:|---:|---:|
| Tibet | **1.103** | 2.41 → 2.87 | +1.6 → +2.3 |
| middle Volga | 1.051 | 1.80 → 1.96 | −1.1 → −1.5 |
| northern BC coast | 1.032 | 3.24 → 3.44 | −2.9 → −3.1 |
| Tripolitania | 1.009 | 1.71 → 1.79 | −0.6 → −0.7 |
| Ethiopian highlands | 0.972 | 1.83 → 1.74 | +0.1 → −0.1 |
| Nova Scotia | 0.952 | 2.57 → 2.23 | +2.6 → +2.2 |

Two lessons:

1. **A high plateau in summer is not sinking air.** Tibet lies inside the
   branch in summer and its air counts as inland, so e71 warmed a plateau
   already too warm. A summer plateau is an elevated heat source under
   rising air.
2. **The search paid for e71's spillover with a lower global land offset.**
   That cooled continental and coastal mid-latitudes (Volga, the BC coast)
   and the coastal desert edge (Tripolitania, which the inland gate
   excludes from the warming).

The next design needs three changes:
- no compression warming under summer ascent: high plateaus and the
  monsoon (task P6);
- no global offset as compensation;
- the coastal gate softened for the desert edge.

Sealed set c is now development data
(`calibration/sealed_20261101c/declaration.json`). A fresh set d is
declared for the next adoption.

## Second design: gates instead of a global offset

Two new opt-in gates follow the sealed-set failure:
- **e71e** `subsidence_warming_rain`: no warming under raining (rising) air,
  × exp(−smoothed rain / this).
- **e71f** `subsidence_warming_top_m`: none above this height, full
  1,000 m below it.

The land offset stays at r41's value. Screens: e71 4 K, taper 10°,
chi0 0.7, top 2,500 m; columns as before plus the now-retired sealed set c.

| rain gate | dev31 S | holdout | mid-lat. | dev12 | retired a | retired b | retired c |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 mm/day (g1) | 0.9853 | 1.0051 | 1.0050 | 0.972 | 0.994 | 0.955 | 1.004 |
| 1 mm/day (g2) | 0.9875 | 1.0047 | 1.0047 | 0.976 | 0.994 | 0.960 | 1.004 |
| 1 mm/day, chi0 0.5 (g3) | 0.9876 | 1.0076 | 1.0047 | 0.976 | 0.993 | 0.956 | 1.004 |

Sealed set c's damage is gone: Volga and the BC coast are unchanged, and
Tibet moves only 2.41 → 2.51 °C. What remains:
- **Manchuria (1.033–1.037):** mostly rain, 646 → 668 mm against 582
  observed, downstream of the warmed interior.
- **SW Australia, Victoria and Chile:** 0.1–0.3 °C each.

The second refit, `calibration/desert_refit2_20261101/plan.json` (frozen
before its search), starts at g1. Knobs:
- the warming and its gates;
- the branch gap;
- `wet_sun`;
- the rain-out time `precip_tau_days`.

It has no land offset and no cold-air pool. All three retired sealed sets
are guards. It will be validated on sealed set d
(`calibration/sealed_20261101d`, never run).

## The desert rain floor (P5): dry air brought down by the branch

`scripts/trace_desert_rain.py` traces the rain step at the centre cells of
Najd and the Algerian Sahara (r41).

- **Najd:** rain and evaporation are both about 1 mm/day in most months, a
  recycling loop. It runs under a column at relative humidity 0.48–0.76,
  with background ascent of 0.75 and almost no summer damping from sinking
  air (damping factor 0.97). The model's subsidence band lies north of 23° N
  in summer.
- **Sahara:** the same loop, in July–August. Rain is 1.0–1.2 mm/day against
  evaporation of 0.6–1.2. Monsoon moisture raises the column's relative
  humidity to 0.55–0.59.

Screens (r41 plus each change), scored as before:

| change | dev31 S | rain loss | holdout | mid-lat. | retired a | retired b (deserts) | retired c |
|---|---:|---:|---:|---:|---:|---:|---:|
| subsidence drying 0.1/day across the band and branch (e70) | 1.1964 (set a) | +36 % | | | 1.196 | 0.931 | 1.070 |
| **e70b: branch-core drying 0.1/day** | 1.0037 | +1.1 % | 1.042 | 1.012 | 1.017 | 0.930 | 0.981 |
| e70b 0.2/day | 1.0270 | +5.3 % | 1.088 | 1.027 | 1.030 | 0.907 | 0.970 |
| e70b 0.2 + e71 gated | 1.0087 | +4.6 % | 1.092 | 1.030 | 1.016 | **0.848** | 0.974 |
| **e70b 0.2 + rain gate 1 mm/day (e70c)** | **0.9986** | −0.03 % | 1.030 | 1.004 | 1.038 | 0.927 | 0.998 |

What these runs show:
- **Drying through the band dries the mid-latitudes.** The band sits at
  34–40° in summer, so drying it ruins mid-latitude rain.
- **Drying only the branch core works on the deserts.** It cuts their rain:
  Najd 364 → 221 mm (0.1/day) and → 164 mm with the warming (observed 124);
  the Sahara 176 → 116 and → 91 mm (observed 26).
- **The rain gate spares the monsoons.** It switches the drying off under
  rising, raining air, and East China and the North China Plain are spared.
- **What remains is downstream.** South Brazil 1.11, SW Australia 1.075,
  the Levant 1.08, Central Asia 1.06 and Anatolia 1.05 now lose rain. They
  sit downstream of the dried deserts, and their moisture crosses the dried
  column.

Desert refit #2 (gated e71, without drying) ran 63 of its 80 candidates
before the 1.9-hour time limit; its best cost is 1.0026 (candidate 32).
Mid-latitude 1.0018 and holdout 1.001 block it, both through Manchuria and
the southern coasts. The remaining 17 candidates are queued; the frozen
plan allows them.

## Desert refits #2 and #3: the same answer twice (not adopted)

Both frozen searches ran to their 80 candidates. Refit #3 was resumed
twice after container restarts, which its plan allows.

| | refit #2 (gated e71) | refit #3 (e70b core drying + e70c rain gate + gated e71) |
|---|---:|---:|
| best candidate | 32 | 79 |
| dev31 S | 0.9938 | 0.9938 |
| training / dev12 | 0.993 / 0.989 | 0.997 / 0.987 |
| **holdout** | **1.0010** | **1.0002** |
| **mid-latitude** | **1.0018** | **1.0020** |
| retired sealed b (deserts) | 0.977 | **0.958** |
| retired sealed a / c | 0.995 / 1.002 | 0.995 / 1.002 |
| cost | 1.0026 | 1.0020 |

In refit #3, 37 of the 80 candidates pass the overall bar (S ≤ 0.995),
but none keeps every policy group from worsening.

**Verdict:** the frozen gate fails any group above 1. The validation
re-run is deterministic and would fail the same way, so neither candidate
was validated. Sealed set d stays unseen and r41 stays.

**What blocks both searches.** These are the per-region changes for
refit #3's best candidate against r41, on the monthly temperature error
and the rain loss:

| region | temperature error | rain loss |
|---|---:|---:|
| Manchuria | 2.13 → 2.15 °C (+1.3 %) | 0.276 → 0.286 (+3.8 %) |
| SW Australia | 0.66 → 0.67 °C (+2.3 %) | 0.522 → 0.528 |
| Japan | 1.84 → 1.85 °C | slightly better |

The rest of both groups move by less than 0.5 %.

**What it shows:**
- **The desert physics works.** Retired set b, the deserts, improves by
  4 %, and dev31 by 0.6 %.
- **Manchuria is not warmed directly.** Candidate 79's branch edge reaches
  27.6° in winter, 33.6° on the annual mean and 39.6° in summer, while
  Manchuria lies at 44.6°. So e71 never touches it. Its loss arrives
  indirectly: the warmed and dried belt to the south reaches it through
  eddy mixing (850 km) and moisture transport.
- **Cutting the warming off at the branch edge would not help.**

**The headroom has to come from Manchuria's own errors:**
- an annual warm bias of +1.9 °C, reaching +2 to +4 °C from September to
  January;
- winter rain at 1.6–3 times the observed.

The rest of East Asia has the same error: winters too wet in Japan,
Korea and the North China Plain, and springs too dry and warm. The dry,
cold winter monsoon is missing. That is P6. Once it is fixed, the desert
refit can be re-run against sealed set d, which is still unseen.
