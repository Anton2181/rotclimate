# Initial momentum balance — 29 October 2026

Momentum-only initialization is insufficient. The formal steady solutions for
the frozen thermal fields reach 207–250 m/s and produce large instantaneous
thermal tendencies. No proposed wind is adopted or integrated.

The declaration was committed in `d4d2195` before results. Thirty static states
cover three regions, closed/prescribed-flow boundaries and five candidates:
archived simulated initial wind; three regularized corrections (1/6/24 hours);
and formal steady drag/Coriolis balance. They add **zero** Earth integrations.

## Objective and fixed physics

In mass-weighted face velocities, minimize

`||A x + b||² + ||x − x_ref||² / tau²`.

`A` is the actual unchanged Coriolis/drag matrix; `b` contains the actual thermal
pressure gradient and prescribed-boundary rotation contribution. `tau` controls
the allowed initialization correction and is not a new atmospheric parameter.
The normal matrix `I + tau² AᵀA` is positive definite, so this diagnostic has a
unique global minimum. This statement does **not** establish a global optimum
for the nonlinear climate calibration problem.

Temperature, vapor, Earth rotation, drag and prescribed exterior velocities
remain fixed. The solution retains zero depth-mass-mean flow and does not clip
winds or use observed fields. A steady frozen-temperature momentum solution
is not a steady thermal/moist solution.

## Prescribed-flow cases

| Region | Candidate | Peak wind m/s | Initial max acceleration m/s² | Instantaneous thermal RMS K/day |
|---|---|---:|---:|---:|
| North India | archived seed | 5.9 | .00396 | 1.27 |
| North India | 1 h correction | 6.1 | .00391 | 1.44 |
| North India | 6 h correction | 29.3 | .00302 | 13.49 |
| North India | 24 h correction | 91.4 | .00141 | 58.49 |
| North India | formal steady | 226.1 | roundoff | 378.56 |
| Mexico | archived seed | 6.6 | .00378 | 1.27 |
| Mexico | 1 h correction | 6.6 | .00368 | 1.34 |
| Mexico | 6 h correction | 34.0 | .00226 | 9.42 |
| Mexico | 24 h correction | 97.2 | .00108 | 39.78 |
| Mexico | formal steady | 248.8 | roundoff | 373.87 |
| Pacific Northwest | archived seed | 7.2 | .00435 | 2.16 |
| Pacific Northwest | 1 h correction | 7.2 | .00398 | 2.33 |
| Pacific Northwest | 6 h correction | 34.4 | .00172 | 15.21 |
| Pacific Northwest | 24 h correction | 86.0 | .00066 | 43.22 |
| Pacific Northwest | formal steady | 207.3 | roundoff | 197.72 |

Thermal rates evaluate the instantaneous actual donor enthalpy/vapor,
compression and drag heating, before liquid phase and convection. They are
**not forecasts** of temperature changes after a day. Kinetic energy changes
are recorded as proposed initialization changes; no conservation claim is made
for replacing the initial state. Ten analytic tests check the independent dense
quadratic optimum, physical face constraints, tradeoff limits and regional
initial energy/water tendency identities.

## Next physics step

The current pressure prototype removes all vertically averaged wind. Fixed
pressure lids require zero **column divergence**, which is less restrictive
than setting the entire vertically averaged velocity to zero. Retaining a
divergence-free mean flow could preserve more of the archived circulation and
moisture transport. This has not yet been implemented or tested, and it is not
known to cure the startup thermal imbalance. A conservative pressure projection
should keep the mean flow without adding dry mass or pressure-work energy.

Joint temperature/wind initialization may still be necessary. ECMWF's
[gravity-wave control documentation](https://www.ecmwf.int/sites/default/files/elibrary/2021/81269-ifs-documentation-cy47r3-part-ii-data-assimilation_1.pdf)
describes normal-mode and digital-filter approaches; neither is implemented here.

There remain eighteen separate Earth-input smoke integrations, unchanged legacy
1934 attempts /1929 strict passes /four historical failures /one interruption,
and no new monthly skill, recalibration or adoption. Earth r39 and all normal
atlas climate/biome/population fields remain unchanged.
