# Coupled dry terrain subsystem controls

Actual six-hour closed dry integrations on native regional terrain, using synthetic reference/anomaly/zero wind rather than climate initialization. No vapor/rain, open boundaries, nonlinear momentum, surface forcing, calibration or atlas climate adoption. Every declared failed partial retained.

Six declared trajectories were attempted, using the actual regional height grids and a synthetic common dry reference plus1K bottom-layer perturbation. All initial winds are zero. 6 completed. The independent publication starts zero additional integrations.

| Region | Step s | Status | Steps | Actual final energy residual J/m² sum |
|---|---:|---|---:|---:|
| north_india | 900 | completed | 24 | -4.1664095e-05 |
| north_india | 450 | completed | 48 | -0.00010210242 |
| mexico | 900 | completed | 24 | -7.5657463e-05 |
| mexico | 450 | completed | 48 | -0.00015833314 |
| pacific_nw | 900 | completed | 24 | -4.0696459e-05 |
| pacific_nw | 450 | completed | 48 | -0.00010107393 |

The scalar state is the dry-mass-weighted layer-mean temperature. Its analytic reference mean is integrated in pressure; anomalies reconstruct the same hydrostatic profile used by pressure and compression. Momentum uses implicit midpoint pressure and energy-skew Coriolis forces with a saddle constraint for fixed column mass. Actual layer continuity generates vertical transfer; implicit upwind native enthalpy transport is conservative. Nonlinear temperature coupling is iterated under the declared tolerance; unsuccessful steps fail and retain the last accepted state.

The reference column-potential gradient is a barotropic constraint gradient. Absorbing it into the constraint gauge avoids tiny-rest-force cancellation without changing admissible motion or adding heat. A dedicated test verifies that it does zero work on constrained winds. The inherited refined saddle solver retains its8-epsilon acceptance limit.

Every available hourly state and final/partial field is hash-checked. Its actual energy change is independently reconstructed from temperatures, dry masses and native port speeds. Extended-precision full-state enthalpy differences agree with stable actual-state differences. Per-step runtime certificates and all six outcomes are downloadable. No residual is redistributed to repair heat or kinetic energy.

Timestep sensitivity in final temperature (mass-weighted RMS K;900s versus450s):
- north_india: 2.239469e-05; maximum 0.0001796206.
- mexico: 1.860289e-05; maximum 0.0003407155.
- pacific_nw: 2.095517e-05; maximum 0.000176722.

A small energy residual does not demonstrate spatial or time-step convergence, correct Earth winds, or accurate rain. These are six synthetic dry subsystem integrations, not six new climate-initialized Earth trials. The partial380-hPa pressure top, closed boundaries, staircase geometry, absent nonlinear momentum, vapor/phase physics and surface/radiative forcing limit interpretation. No baseline replacement or normal-atlas field changes.
