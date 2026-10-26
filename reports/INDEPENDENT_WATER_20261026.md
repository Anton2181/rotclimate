# Independent seasonal layer water — 26 October 2026

The seasonal model now has an opt-in pair of independent steady moisture
reservoirs. The lower and upper dry-air masses remain25%/75% of the same
hydrostatic column. Horizontal donor transport and diagnosed vertical donor
exchange preserve uniform specific humidity; vertical exchange cancels in the
column ledger. Optional symmetric mixing has a declared0 or5day timescale.
Sea and land evaporation enter the lower layer. Sea exchange responds to actual
lower humidity. Both layers rain, dry and undergo the existing conservative
linear storm exchange. The old fixed humidity ratio no longer determines water.

The first Earth comparison keeps calibrated absolute column saturation and sea
water unchanged. A normalized hydrostatic moist profile only partitions the
capacity and boundary supply; it never resets the solved humidity. This
separates vertical humidity dynamics from the already rejected absolute
pressure-capacity replacement. There is no independent vertical temperature,
latent-heat feedback, time-storage equation or new momentum model.

Every seasonal/primer step must pass the actual nonlinear equation separately
for each layer and for their sum, including the updated evaporation switch.
The linear block solver checks the independent sparse equation and borders,
and recovers the same equation with a sparse solve when necessary. Actual donor
water fractions also feed the total face ledger and diagnostic vapor winds.
The old default branch remains available as an exact numerical control.

The frozen plan is `calibration/independent_water_20261026/plan.json`:35actual
coupled Earth runs,21exact historical controls then14candidate runs over7reused
development regions. There are exactly2eligible candidates, no/5day mixing.
Neither planetary parameters, shared winds nor accuracy thresholds are tuned.
Numerical damping is0.1for the new nonlinear systems and0.05for archived
transport/pressure controls; the residual tolerance is unchanged.

In addition to all existing temperature/rain/ocean/circulation/mass/branch-speed
requirements, a candidate must preserve observed native ocean humidity over
Iberia. Its monthly925–300hPa partial-water MAE and upper700–300/lower925–700
mean specific-humidity-ratio MAE may each worsen at most2% relative to the
paired common-mass fixed-profile control. Integrate model piecewise-uniform
layer specific humidity over exactly these pressure intervals, aggregate to
original native footprints, and use the same true areas/calendar weights.
Exclude footprints containing any model terrain above925hPa. The observed
profile never forces the model. Full dry-column ratios are not equated with
observed partial ratios. Reanalysis is model-assisted, coarse and1981–2010,
whereas rainfall reference is WorldClim1970–2000; these remain reused development
constraints, not independent global validation.

All layer/column certificates remain mandatory in the full31/ocean/fine/
established stages. Ocean checks repeat the humidity safeguard at56km; before
adoption an additional paired28km Iberia humidity comparison must pass the same
limits. The at-most2qualifiers can add at most3such solves, with one shared
fine-grid control. Fantasy/world qualification remains separate.

Initial verification:11coupled/core tests cover analytic two-box evaporation,
vertical mixing and drying, exact equilibrium on terrain/counterflow/storms,
spatial donor fractions, no-Numba fallback, unsupported settings, strict coupled
layer/column/vapor ledgers and independence from the old humidity ratio.
Independent pressure-overlap and area/month-weighted humidity guard tests also
pass. Actual Earth outcomes will be recorded after the frozen comparison.

Status: plan declared before new Earth candidate scores; no adoption.
