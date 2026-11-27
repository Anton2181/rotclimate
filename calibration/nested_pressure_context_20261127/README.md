# Prospective fixed native-parent pressure-context pilot

One different structural hypothesis following the failed zero-exterior study.
The native model supplies an explicit finite exterior thermal field. It is not
assumed to predict the true atmosphere or to be a whole-planet solution.

Exactly14 coupled integrations, committed before preflight/integrations:
1. Two default-off native children (Somalia, North India) must reproduce ALL
   saved current-source97 baseline cell arrays byte-for-byte.
2. Six native parents on56km grids with4012km padding, unchanged r58 physics,
   original numerical criteria, calendar, primer and Earth conditioning.
   Retain the ACTUAL final pressure-input temperature anomaly at each model
   day, including the last inner temperature coupling. All six parents are
   frozen before any nested child. No accuracy-based parent selection.
3. Six nested children with original1100km padding and original full inputs,
   masks, moisture boundaries, SST, physics parameters and numerics. On EACH
   pressure call replace the parent's anomaly in the ENTIRE child padded
   rectangle with that child's current anomaly. Apply the ORIGINAL pressure
   Gaussians and coefficients on the composite parent grid, crop the pressure,
   and use original signed momentum/friction. Updated last_pres feeds all
   existing pressure couplings. No blend coefficient or observed T forcing.

Regions: Sahara/Somalia targets; North India, Algerian Sahara, Najd and
California guards. Seven operator/alignment tests passed, including actual
wide-FFT kernel contributions and exact same-parent sampling across two nested
window sizes. The six parent/child input pairs share geography/observations
exactly at a52-cell offset. Raw input preparation ran ZERO climate integrations.

Prospective screen: Sahara rain-loss ratio<=.90; Somalia July GEOGRAPHIC
surface-vector RMSE ratio<=.90 versus the default-off run; every region's
temperature MAE and rainfall-loss ratios<=1.01. Fixed NCEP sigma.995 surface
winds,1991–2020,2.5degree reference is diagnostic ONLY, not forcing. Use same
WorldClim-scored cells and full projection Jacobian (metric and rotation).
Passing only permits broader exposed development under the existing policy,
not adoption. Failure closes THIS fixed nested alternative, with no selected
padding, blend/amplitude rescue or gate relaxation. Report all parent and
child outcomes. No accuracy early stopping. Numerical/identity failure stops
and is preserved; no scientific retry or tolerance change.

Physical limits: one-way frozen seasonal parent, no feedback to exterior;
parent still has nearest continuation at its outer edge. A2051km broad kernel
has a long reach relative to the parent halo. Native parent weather, original
spinup and Earth-only conditioning can be biased. Large peripheral planar
projection distortion remains. Composite joins can have real discontinuities;
no interface taper is fitted. This isolates exterior thermal context at fixed
child moisture inputs; it does not prove domain convergence or global truth.

No production89-source changes. Same231 regular private source/helper/cache
files, pinned sources/inputs/libraries and four thread variables1, one nice10
worker using literal venv Python. Protocols explicitly identify each arm and
all six frozen parent archives. Preserve attempts, all raw T/P scores, full last
pressure-call anomaly/pressure fields and actual scored monthly winds.
Independent review uses direct scipy Gaussian convolution (original truncate4)
to reconstruct pressure; maximum discrepancy<=1e-7 Pa accounts for the original
FFT's9-decimal kernel-sigma rounding and arithmetic. This is an operator
reconstruction precision bound, NOT a changed solver or accuracy tolerance.
Raw float32 scores use existing propagated rounding bounds.

W18/W18c remain permanently closed. AA unopened; no fine28, world fit,
parameter adoption or atlas change. The shared-solar-cap candidate stays closed.
The spherical whole-planet filter remains a separate reference prototype; this
finite nested pilot does not claim to have supplied its missing global field.
