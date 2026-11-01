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

**Result:** (pending)
