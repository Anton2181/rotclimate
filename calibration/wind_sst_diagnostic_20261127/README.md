# Literal observed-SST correction and fixed wind × SST diagnostic

The existing heat-only damping addback belongs to a MODELED sea. It formerly
added modeled seasonal anomalies to the moisture/convection/e91 temperature
even after observed SST had set the heat target. The source correction limits
that addback to sst_source=model; modeled-SST arithmetic remains unchanged.
An actual coupled prescribed-temperature regression fails before and passes
after; it verifies saved surface/heat target/moisture temperature, read-only
inputs and complete physical/budget byte equality when the now-irrelevant flag
is toggled under observed SST. A modeled-SST test preserves its intended heat/
moisture temperature difference. Combined58 source tests plus6 WOA reference
checks pass; raw pre-fix failure preserved. No solver criterion changes.

Commit plan/source before preparation/integration. Exactly12 fixed regional
runs: six modeled-SST controls (three regions with modeled wind, then observed
wind) FIRST; then the six observed-SST arms in same wind order. Parent6 controls
are the completed Ekman-corrected source captures. All shared physical monthly/
raw/budget fields must reproduce byte-exact. Same56km cells,1100km pad, exact
coordinates/observations/actual case identities, r58 coefficients and original
0.01 moisture criteria. Only wind_source and sst_source change across arms.
All225 regular private source/cache files pinned; one worker,nice10,all4thread
vars1,literalvenvPython. Preserve and STOP on failure/interruption, no automatic
retry, numerical changes or post-result budget extension. No score-selection
screen or climate adoption. Full attempts/params/certificates/fields retained.

Use scripts/run_wind_sst_diagnostic.py to prepare, then --run. Preparation
validates all12 public raw WOA source hashes against its monthly1degree cache,
axes/units/finite coverage, copies that complete normalized reference into the
packet, and retains full projected NCEP wind/WOA SST inputs per padded grid.
Actual inputs are read-only and hashed before/after. Observed sea inputs must
be above the sea-ice threshold on all modeled sea cells before any run, allowing
literal heat target validation without ice physics. Diagnostics include ALL
modeled sea cells as well as unchanged scored land. Save and check actual
pre-ice surface SST, heat-equilibrium target and moisture SST against temporal
interpolation, plus actual wind samples; independent review rederives WOA
sampling and validates complete cached sea masks. The extra recorder changes
no physical return value. Controls demonstrate diagnostic passivity.

Report every arm/regional T MAE, existing per-cell rain loss and both components,
worst annual spatial errors, source accounts, interaction and figure. Regional
means alone previously hid Nepal errors, so do not treat better totals as skill.
Both SST uses change together; related heat, advection, sources, drying, uplift
and recycling respond, not independent additive causal fractions. WOA all-
decade SST and NCEP1991–2020 surface winds differ in period/resolution and do
not specify a matched observed3D atmosphere. Neither is a fictional-world law.
W18c CLOSED,AAUNOPENED,r58retained,atlasr51unchanged. Establish current-source
paired references before future calibration/map use; do not rewrite old ones.
