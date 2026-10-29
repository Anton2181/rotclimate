# Full finer-grid controls with a fixed larger solver allowance

All six 24-hour controls complete. The previous three fine-grid convergence
failures are resolved in this batch by increasing maximum solver work from
64 to 1024 sweeps. Stopping tolerance remains 0.01 K; relaxation, thermodynamics,
planetary parameters and initial fields stay unchanged. The old failures remain
retained. No physical model is adopted and no observed accuracy gain is claimed.

| Region | Step s | Land rain mm | Land net evap mm | Land surface change K | Max target sweeps |
|---|---:|---:|---:|---:|---:|
| north india | 900 | 0.619 | 6.039 | -3.337 | 432 |
| north india | 450 | 0.632 | 6.013 | -3.311 | 425 |
| mexico | 900 | 1.751 | 4.285 | -2.065 | 251 |
| mexico | 450 | 1.715 | 4.254 | -2.032 | 336 |
| pacific nw | 900 | 0.427 | 5.067 | -3.332 | 273 |
| pacific nw | 450 | 0.427 | 5.031 | -3.298 | 304 |

The 21-level first-cell reference height is about 42–43 m, compared with
170–175 m on the nine-level grid and about 750 m originally. Piecewise-constant
refinement preserves integrals but changes resolved initial stability and flux
geometry; it does not infer the unknown near-surface lapse profile.

Initial arrays exactly reproduce each original fine-grid case. Their recorded
accepted scalar histories also reproduce exactly through the original failed
step (19, 18 and 39 steps respectively). The full weather fields at those prefix
times were not separately saved by this protocol; no claim is made to have
compared unavailable snapshots.

| Region | Fine 450 minus 900 s mean land rain mm | Spatial land rain RMS mm | Surface T RMS K |
|---|---:|---:|---:|
| north india | 0.0123 | 0.2040 | 0.0546 |
| mexico | -0.0360 | 0.5587 | 0.0768 |
| pacific nw | -0.0003 | 0.1485 | 0.0343 |

A small regional mean difference does not establish local convergence. Mexico
has a 0.559-mm spatial timestep difference, larger than the corresponding
nine-level 0.300-mm difference. Refinement alone is not demonstrated accuracy.

All 864 coupled calls are retained with times and target sweep counts.
Their observed summed coupled-call time is 2999.6 seconds;
this is not a repeated-timing confidence interval. Every successful target
meets the original stability tolerance. Actual work reaches 432 sweeps, so a
256-sweep cap inferred from the single captured target would have been too small.

Maximum saved-state energy relative error is 2.854e-15;
water relative error is 1.426e-16. These are independent
reconstructions against actual recorded supplies. All initial/final and old
failed arrays, protocols, source hashes and scalar/timing histories are retained.

The next observed-rainfall benchmark is already frozen in
`calibration/regional_rainfall_benchmark_20261029`. It uses the completed
nine-level grid for fixed complete calendar months, both wet and dry starts,
and common area-weighted WorldClim footprints. Three r39 raw-climate controls
must reproduce the archived qualified model before Gregorian reaggregation.
Refinement work therefore does not indefinitely postpone the accuracy comparison.

This six-run study brings the prototype record to 109 starts /101 completions /
eight retained numerical failures, including the earlier expected replay rejection.
It adds zero legacy benchmark attempts. No recalibration, monthly rainfall skill
or physical adoption occurs. Normal atlas climate/biome/population fields remain
unchanged. The forthcoming benchmark has separate legacy/prototype counters.
