# Lower-air-cell dynamic resolution results

Six of nine declared 24-hour controls complete. All six four-part first-cell
cases finish at 900/450 seconds. All three sixteen-part cases reject a step
because convection does not converge at the original 64-sweep limit. Every
failure and partial state is retained. These are not successful daily climate
runs and their partial rain must not be compared as 24-hour totals.

| Region | First-cell parts | Step s | Outcome | Accepted steps | Land rain mm | Land net evap mm | Land surface change K |
|---|---:|---:|---|---:|---:|---:|---:|
| north india | 4 | 900 | completed | 96 | 0.749 | 6.113 | -3.48 |
| north india | 4 | 450 | completed | 192 | 0.732 | 6.096 | -3.47 |
| north india | 16 | 900 | failed | 19 | 0.000 | 1.798 | -1.44 |
| mexico | 4 | 900 | completed | 96 | 1.722 | 4.135 | -2.00 |
| mexico | 4 | 450 | completed | 192 | 1.710 | 4.120 | -1.99 |
| mexico | 16 | 900 | failed | 18 | 0.001 | 1.075 | -0.75 |
| pacific nw | 4 | 900 | completed | 96 | 0.438 | 5.297 | -3.67 |
| pacific nw | 4 | 450 | completed | 192 | 0.439 | 5.292 | -3.66 |
| pacific nw | 16 | 900 | failed | 39 | 0.000 | 2.906 | -2.37 |

Nine attempts were frozen in `42c6bcd8` before outcomes. No pressure lid, Earth
parameter, opacity, exchange coefficient, relaxation or numerical tolerance was
retuned. The static transfer preserves initial gas/surface/kinetic energy,
total water and integrated momentum. Target-pressure conversion rain and actual
liquid enthalpy return before time zero and are excluded from run rain.

The first air cell reference height changes from roughly 750 m to 175 m or
43 m. Source cells are reconstructed as constant subcells, so this changes
resolved initial stability as well as exchange geometry. It does not infer an
unobserved near-surface lapse profile or promise a balanced atmosphere.

## Four-part timestep sensitivity

| Region | 450 minus 900 s land mean rain mm | Land spatial rain RMS mm | Surface T RMS K |
|---|---:|---:|---:|
| north india | -0.0168 | 0.1660 | 0.0659 |
| mexico | -0.0115 | 0.2998 | 0.0558 |
| pacific nw | 0.0014 | 0.0750 | 0.0176 |

Regional mean changes are smaller than local spatial differences. These two
timesteps do not establish local convergence or monthly rainfall skill. The
sixteen-part grid has no completed 24-hour run or finer timestep control.

All nine saved final/partial energy and water budgets independently pass against
recorded supplies. Maximum energy relative error is 3.429e-15;
water relative error is 3.383e-16.
Failed weather states remain at the last accepted step; the rejected step is
not accepted, replaced or counted as climate progress. All raw histories,
source hashes, frozen plans and saved states are available in the atlas.

The next diagnostic replays the next rejected India step once with passive
convection-input capture. That is a new actual integration attempt, expected to
reject again, and will be counted as a failure if it does. Five fixed static
closure solves then test work caps 64/128/256/512/1024 on exactly that captured
input without changing tolerance, relaxation, thermodynamics or dynamics.
Their literal plan is `calibration/convection_limit_replay_20261029/plan.json`.
No replay outcome is known in this report. No larger cap is dynamically adopted.

The observer receives copies only. Two new tests and a 22-test focused suite
verify complete coupled trajectories and certificates remain byte-identical
even when a callback mutates its snapshots; nonconverged targets and controls
are preserved. Existing original solver code bodies and globals stay unchanged.

Prototype record through this grid study: 102 starts /95 completions /seven
retained numerical failures. Legacy 1934/1929 and normal Earth r39 maps stay
unchanged. No recalibration, monthly accuracy improvement or physical adoption.
