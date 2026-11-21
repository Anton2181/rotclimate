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
