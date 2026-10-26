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

Status: complete; no candidate qualified and no adoption.

## Completed actual Earth comparison

Source `fd458cf`; all35/35actual coupled runs passed strict numerics, with21
exact controls. The supervisor completed in390.3seconds. Both new closures
failed the fixed scientific protections; no full31/ocean/fine/established gates
ran. No climate, population, farming or trade packet is replaced.

| Eligible closure | Combined error / r39 | Rain loss / r39 | Temperature MAE / r39 | Qualified |
|---|---:|---:|---:|---|
| No extra mixing |1.17546|1.35486|0.99607|No|
|5day symmetric mixing|1.28217|1.52319|1.04114|No|

Both improve North India's rain loss and Iran's rain loss, but regional
protections reject wetter Iberia, Japan, Mexico and Pacific Northwest. The
five-day closure also fails eastern Australia and the aggregate temperature
limit. Annual rainfall alone is not the selection metric:

| Region | Observed mm/year | r39 | Independent, no mixing | Independent,5day mixing |
|---|---:|---:|---:|---:|
|North India|760.83|256.26|280.63|316.19|
|Iran plateau|232.39|365.10|225.71|316.50|
|Iberia|391.83|444.93|821.67|1041.12|

North India's monthly rainfall MAE improves from50.01mm to44.45/43.54mm, but
its monsoon remains far too weak. The fixed comparison map shows the second
predeclared candidate, five-day mixing, regardless of its score.

The new physical safeguard matters. Over the same20Iberian ocean footprints
(1,218,866km²), observed925–300hPa water averages12.577mm and partial upper/lower
q ratio0.24263. The fixed-profile control gives11.682mm/0.25372, with local
monthly PW MAE1.34593mm and partial-ratio MAE0.01587. No mixing gives12.253mm/
0.27449: PW MAE1.31162mm improves slightly, but shape MAE0.04919 is3.10times
control. Five-day mixing gives13.052mm/0.33097, PW MAE1.44450mm and shape
MAE0.08967,5.65times control. Both fail the separate vertical-shape guard;
five-day mixing also fails the PW guard. Closer total water cannot compensate
for an unrealistic distribution.

Each candidate covers231primer/scored steps across7regions. Every actual
layer and column residual is below0.01, with no sparse recovery needed. Whole
column upper/lower q ranges across individual interior cells are0.064–0.876
without extra mixing and0.076–0.897with five-day mixing; these are not the
observed partial-pressure ratios. North India native land partial q ratio is
about0.490without mixing versus0.251in reference, another diagnostic warning
beyond the predeclared ocean guard. Reporting this does not add a post-result
candidate or change qualification thresholds.

The prototype is now a tested, opt-in seasonal implementation, but it is not an
accuracy upgrade. Its broad upper reservoir transfers rising vapor without
explicit parcel cooling/condensation on the way up. A separately declared
parcel-ascent experiment can test that missing process before another Earth
fit; no empirical upper-humidity reset is justified by these outcomes.

Figures/data are published in the launcher-linked Climate accuracy companion
as a new collapsible study: all trial scores, fixed rainfall maps, actual
native humidity curves and error protections, and full layer certificates.
The series now contains812actual Earth attempts,808passes and4preserved earlier
failures. Manufactured systems, reference audits and backend timings add no
Earth integrations. Science Earthr39 and fantasy Earthr38 remain in place.
