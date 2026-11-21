# Monsoon peak — what was ruled out (21 Nov 2026)

1. Resolution (calibration/monsoon_resolution_20261121): 56/28/14 km peak ratios Mexico 0.28/0.27/0.25, Texas 0.29/0.27/0.27,
   Sahel 0.61/0.63/0.60 -> PHYSICS.
2. Moisture supply (e91 warm-sea inflow, declared screen A): FAIL. Best target mean 0.981 (gain 0.5; Mexico 0.940, Bengal 0.944)
   but Sahel 1.046 and Najd guard 1.108 (false summer rain). Supply helps Bengal/Mexico a little, harms the arid margins.
3. Sea temperature (diagnostic, sst_source observed / WOA18): Mexico July column 30.4 -> 32.4 mm, rain 0.78 -> 0.83 mm/day;
   January wetter (worse). The model's cool seas are not the main cause.
4. Probe (scripts/monsoon_probe.py): Mexico July column 30-32 mm at RH 0.60-0.62 with July temperature right (+0.2 C) yet rain
   ~0.8 mm/day (obs ~3); January RH 0.88-0.95 rains 1.6-2.3 mm/day (obs ~0.75). Rain follows column RH, not heating:
   the model rains readily from cold saturated winter columns and hardly from hot, moderately humid summer columns.

Conclusion: the remaining lever is the rain-production law itself (convection triggered by surface heating / instability at
moderate column humidity, and less rain from cold stable columns). Two-level transport (the plan's next step) targets rain
shadows, not this. e88 heated-slope convection already failed its screen. Not pursued further without an owner decision.

5. Rain-production law (e92 heating-dependent convective threshold over land; calibration/monsoon_convection_20261121): FAIL.
   Threshold drop 0.05/0.10/0.15: Mexico 0.993/0.983/0.971, Bengal 0.992/0.980/0.961, but Sahel 1.025/1.062/1.112 and Najd
   1.021/1.061/1.146; the target mean never improves (1.002-1.007). Climate PARKED at r49 per the declared plan.

Common pattern of e88, e90, e91, e92: every term that lets hot land rain more also rains on the arid margins (Sahel pre-monsoon,
Najd), faster than it helps the monsoon cores. What separates them on Earth is the dry, warm layer aloft over the desert
margins (Saharan/Arabian air layer) that caps convection; e84 instability_cap tried this alone and failed. A future attempt would
need that discriminator and a monsoon-side term together, declared as one experiment, with sealed set o still unopened.
