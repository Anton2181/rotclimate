# Warm-season inflow: e102 tropical sea + heat-low inflow (22 Nov 2026) — FAIL at fine28, parked

Stage A (dev49 vs r50): X1 sst_tropical 3 -> 1.0029 (retired a 0.981, b 0.966; training 1.016);
X2 + trade_heat_low 1.0, monsoon_pressure_hpa 1.5 -> 1.0055.
Stage B (plan_B.json, 39 evaluations): best S49 0.9925 (T -1.0 %, P -0.5 %) — PASSES the dev gate.
Best: sst_tropical 2.06 (fade 25 -> 31.25 deg), trade_heat_low 0.50, monsoon_pressure_hpa 2.94, ocean_rh 0.755,
convective_rain 0.614, subsidence_warming 5.40, monsoon_descent 0.0408, precip_tau_days 9.67 (stageB_best.json).
fine28 (fresh paired r50 run, 4 regions at 28 km): S28 1.0112 (T +0.9 %, P +1.4 %) > 1.01 — FAIL.
California rain log RMSE 0.481 -> 0.514 (513 -> 528 mm, obs 414), Japan T MAE 1.78 -> 1.85; W Europe and
New Zealand unchanged. Per policy v3 not adopted; r50 stays; sealed set q NOT opened.
fine28 has now been seen for this line: a follow-up must not be tuned on it. The dev49 gain is real (training,
holdout and retired sets improve), and California's extra rain (its southern seas sit inside the 25-31 deg fade)
is the named cost. A follow-up would need a reason independent of fine28 (e.g. stop the warming at the
eastern-boundary upwelling coasts, where WOA is cold) and its own declaration.

## Follow-up check: is California's cost the upwelling sea? No.
WOA18 annual sea bias, r50 -> e102 best (compare_sea_surface.py): California open +0.4 -> +0.4 (unchanged: it lies
poleward of the 31 deg fade), Chile -0.5 -> -0.3, Morocco -3.8 -> -3.7, Benguela (namibia_kalahari) +0.9 -> +1.7
(too warm), Bengal -3.3 -> -1.5, Mexico -5.2 -> -3.3. The tropical warming does what it should where it acts, and
over-warms the Benguela upwelling; but California's extra rain at 28 km comes from the shared rain/inflow settings
the refit moved, not from its sea. No upwelling follow-up is declared on that basis; the line stays parked.

## e102b probe (withhold the warming from cold-current seas): rejected on WOA alone, code reverted
WOA18 annual bias e102 -> e102b: Benguela +1.7 -> +1.1, but Mexico open -3.3 -> -4.9 (the model's cold-current
mask covers Mexico's Pacific coast, which WOA has warm), Bengal -1.5 -> -1.7. Net worse; not scored.
