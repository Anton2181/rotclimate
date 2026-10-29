# Terrain-following geometry: first building block

The current regional prototype moves air over a flat lower boundary at a fixed bottom pressure. Archived ground temperatures were referred to sea level to keep that construction explicit. It has no resolved mountain lifting or terrain-following dry column mass. This is a structural limitation, separate from parameter calibration.

A new independent geometry module integrates the dry hydrostatic reference

`T(z) = T0 − lapse*z`, `dp/dz = −p*g/(Rd*T)`.

The isothermal limit is continuous. Its analytic pressure-to-geopotential inverse returns `g*z`. Hybrid interfaces use `p = ptop + sigma*(ps − ptop)`; sigma decreases from one at the ground to zero at the fixed pressure top. Every layer has positive dry mass and each column sums to `(ps − ptop)/g`. A ground surface that intersects the declared top is rejected rather than clipped.

The static audit uses all three existing regional source height/temperature fields, the declared source lapse, and the same sea-level and top pressures as the flat prototype. It does not use observed surface pressure, run weather, or tune Earth parameters.

| Fixed scoring footprints | Mean source height | Reference surface pressure | Flat-column mass excess / flat model mass |
|---|---:|---:|---:|
| India | 760 m | 938.2 hPa | 11.85% |
| Mexico | 1237 m | 882.5 hPa | 20.65% |
| Pacific Northwest | 1036 m | 899.7 hPa | 17.94% |

Means use the predeclared projection-area weights. The mass percentages are relative to the **partial flat model column from its fixed bottom to 380 hPa**, not to the full observed atmosphere. The dry reference is a geometry diagnostic, not a measured pressure error. Individual Indian mountain cells reach a much larger difference; the common-mask score is not changed or masked further.

Fifteen new tests pass, including standard-atmosphere pressures, the hydrostatic differential equation, inverse geopotential across several lapse rates, the continuous isothermal limit, independently summed column masses, and rejection of underground/invalid grids. The related pressure/remapping/rainfall stack passes 34 tests. The full static audit checks the inverse and column mass at every cell. It starts zero climate integrations.

This geometry is **not plugged into the current weather core**. That needs compatible variable-mass continuity, horizontal and vertical transport, pressure gradients that preserve a resting hydrostatic atmosphere over mountains, impermeable lower-boundary kinematics and a matching pressure-work/energy budget. Simply inserting variable masses or an extra elevation force would be incorrect. The next implementation gate is the resting-atmosphere pressure-gradient and work test, followed by transport and complete Earth controls. Missing nonlinear momentum remains another separate limitation.

The current month-long rainfall forecasts, their literal sources, initial conditions, time steps, masks and primary objective remain unchanged. No new rain accuracy, physics adoption, recalibration or normal-atlas climate change is claimed.

The next geometry primitive is implemented separately in `terrain_apertures.py`: neighboring columns connect through their shared pressure intervals, including cross-level overlaps; no port is invented below the neighboring terrain. Seven additional tests verify the flat-grid limit, an exactly specified step mountain, aperture bounds, left/right symmetry, a single cross-level transfer and cancellation of arbitrary paired interior mass fluxes. A static audit repeats the aperture and cancellation checks for all three actual regional grids, with separately identified synthetic velocities. It starts zero climate integrations and is not a circulation solution. Compatible vertical fluxes, pressure constraints, momentum and energy work remain to be implemented.

The common-pressure hydrostatic-gradient diagnostic now passes all three native terrain grids: the maximum rest acceleration is1.30e-16m/s², while the declared1K bottom-layer thermal perturbation generates nonzero force. Seven new tests include independently integrated pressure profiles, flat/steep terrain, reversed neighbors and very thin pressure intervals. The common analytic reference is removed before differencing, preventing large terrain terms from producing spurious rest winds.

The pressure-work component also passes its next static gate. Native level-pair fluxes are projected to close each fixed dry column; vertical pressure motion is reconstructed from their actual pressure subintervals, including neighboring interfaces. Independent eight-point integration of Rd*T*omega/p supplies layer compression/expansion powers. All nine declared synthetic controls pass across the three source terrains and three seeds: maximum absolute summed pressure/compression residual9.20e-12W/m², maximum normalized error1.33e-12. The initial projection's signed kinetic change is separately reported; no residual is redistributed as heat. Seven more tests exercise conservation, projection, linearity and rejection of unclosed flows. The combined terrain/pressure/remap/rainfall stack passes55 tests.

These ports form a staircase in pressure coordinates. The controls are static, closed-domain diagnostics, with synthetic velocities/anomalies rather than observed or forecast winds. They still do not integrate momentum, transport temperature/vapor, resolve a smooth terrain metric, or supply regional boundary work. Their climate integration count is zero. A pressure-work-compatible time step with native transport remains the next gate before any Earth trial.
