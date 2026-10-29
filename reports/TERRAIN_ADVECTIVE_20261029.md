# Nonlinear terrain momentum controls

Same centered-enthalpy model body, momentum transport explicitly off/on, matched synthetic states and one shared preparation projection. Native closed dry trajectories, not rainfall or climate initialization. All failed partials retained.

Six declared trajectories were attempted, using the actual regional height grids and a synthetic common dry reference plus1K bottom-layer perturbation. Both branches use the same prepared4m/s synthetic vortex; one shared mass projection reports its signed kinetic change without heat compensation. 6 completed. The independent publication starts zero additional integrations.

| Region | Transport | Status | Steps | Actual final energy residual J/m² sum |
|---|---:|---|---:|---:|
| north_india | off | completed | 24 | 1.2003351e-05 |
| north_india | on | completed | 24 | 1.8137507e-05 |
| mexico | off | completed | 24 | 9.3327835e-06 |
| mexico | on | completed | 24 | 1.006946e-05 |
| pacific_nw | off | completed | 24 | 5.30947e-06 |
| pacific_nw | on | completed | 24 | 4.2654574e-06 |

Both branches share the same model code and a centered native enthalpy equation. The scalar state is the dry-mass-weighted layer-mean temperature. Its analytic reference mean is integrated in pressure; anomalies reconstruct the same hydrostatic profile used by pressure and compression. Momentum uses implicit midpoint pressure and energy-skew Coriolis forces with a saddle constraint for fixed column mass. Actual layer continuity generates vertical transfer; implicit upwind native enthalpy transport is conservative. Both native velocity and temperature are iterated under the declared tolerances; unsuccessful steps fail and retain the last accepted state.

The reference column-potential gradient is a barotropic constraint gradient. Absorbing it into the constraint gauge avoids tiny-rest-force cancellation without changing admissible motion or adding heat. A dedicated test verifies that it does zero work on constrained winds. The inherited refined saddle solver retains its8-epsilon acceptance limit.

Every available hourly state has its energy reconstructed and hash recorded; initial and final/partial field hashes also match the driver receipts. Its actual energy change is independently reconstructed from temperatures, dry masses and native port speeds. Extended-precision full-state enthalpy differences agree with stable actual-state differences. Per-step runtime certificates and all six outcomes are downloadable. No residual is redistributed to repair heat or kinetic energy. The scalar heat solve is centered about a constant reference before flux/time terms are combined; its explicit reference-flux divergence preserves the original affine equation and avoids loss of small changes against the large background. Tests check equivalence to the uncentered equation. This does not use the observed energy error as a correction.

Transport-on versus off differences at the declared900s step (mass-weighted temperature RMS K; native port velocity RMS m/s):
- north_india: T RMS 0.01112481K, max 0.1183422K; velocity RMS 0.07001291m/s, max 1.373346m/s.
- mexico: T RMS 0.005611263K, max 0.06397451K; velocity RMS 0.0449233m/s, max 0.8873766m/s.
- pacific_nw: T RMS 0.005359481K, max 0.05404035K; velocity RMS 0.05028613m/s, max 1.358472m/s.

A small energy residual does not demonstrate trajectory spatial or time-step convergence, correct Earth winds, or accurate rain. These are six synthetic dry subsystem integrations, not six new climate-initialized Earth trials. The partial380-hPa pressure top, closed boundaries, staircase geometry, absent vapor/phase physics and surface/radiative forcing limit interpretation. No baseline replacement or normal-atlas field changes.
