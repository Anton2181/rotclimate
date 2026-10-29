# Partial-column parcel stability and the moist-convection gate

The repeated conditional moist run has substantial positive parcel buoyancy
within the represented pressure column. Stable and dry controls have none.
This supplies a physical instability diagnostic for the next convection
treatment; it does not validate the strong horizontal-wind response, fit any
coefficients, or constitute complete atmospheric CAPE/CIN.

## Parcel thermodynamics

The diagnostic starts at the lowest selected model cell, after initial local
phase adjustment. The example column covers roughly 965 to 399 hPa. It does
not invent a surface parcel or extrapolate beyond the model top.

Unsaturated ascent retains mixing ratio r and obeys

    dT/dlog(p) = Rd*T/(cp_d + cp_v*r)

Saturated ascent removes liquid at its actual temperature. Using the same
gas/liquid enthalpies as the phase kernel gives

    dhgas + hliquid*drain = Rd*T*dlog(p)
    dT/dlog(p) = [Rd*T - L(T)*drsat/dlog(p)] /
                 [cp_d + cp_v*rsat + L(T)*drsat/dT]
    L(T) = Lv0 + (cp_v-cp_l)*(T-T0)

The liquid saturation curve and its actual derivatives are used consistently.
This is a dry/dilute pressure-coordinate parcel, matching the primary coupled
model assumptions. Water loading, retained condensate, entrainment and ice are
absent. A separate optional virtual-temperature sensitivity is saved rather
than silently changing the primary diagnostic's density law.

The dry lifting-condensation point is bracketed before integrating. The exact
unsaturated solution reaches that event; RK4 then integrates only the smooth
saturated branch. Independent adaptive verification exposed an initial
implementation error as large as 0.16 K when a combined dry/moist derivative
was switched inside an RK stage, including roundoff at saturated sources.
The event split fixes that error; independent DOP853 paths now agree within
8 microkelvin across all audited states.

## Buoyancy integration and resolution

The primary dry/dilute buoyancy is g*(Tparcel-Tenvironment)/Tenvironment.
Hydrostatic dz=-Rd*Tenvironment/g*dlog(p) makes the positive and negative
energy integrals Rd*integral(Tparcel-Tenvironment)*d(-log(p)), with each sign
handled separately. Piecewise-linear sign crossings are split at their actual
zero instead of integrating a clipped endpoint trapezoid.

Between model levels the environment is reconstructed with log-temperature
and linear vapor in log pressure. Internal sampling resolves unsaturated
ascent, condensation and sign changes. Sampling only the ten coarse level
endpoints had missed the conditional flank's shallow negative-buoyancy layer
entirely. A regression test explicitly covers that case. Changing the assumed
environment between levels remains a source of diagnostic uncertainty.

Pressure-step comparisons use maximum log-pressure steps 0.04/0.02/0.01/0.005.
The finest values are summarized below. They are partial-column positive and
negative integrals, not a conventional complete-column CAPE/CIN calculation.
The negative integral includes any negative segment in the supplied column,
not only inhibition below the first level of free convection.

| State | Mean positive J/kg | Maximum positive J/kg | Mean negative J/kg |
| --- | ---: | ---: | ---: |
| Conditional, initial phase-adjusted | 1644.32 | 2156.80 | 5.58 |
| Conditional, after six hours | 804.90 | 1197.35 | 19.68 |
| Saturated-stable, initial | 0 | 0 | 1475.24 |
| Saturated-stable, after six hours | 0 | 0 | 1601.30 |
| Dry control, initial | 0 | 0 | 3097.61 |

The conditional case retains available parcel energy after the coupled run.
Positive energy of this magnitude can support strong motion; a 41.8 m/s wind
is not mathematically impossible on energetic grounds. The acceptance issue
is the omitted convection/nonlinear dynamics and unvalidated transfer of this
instability into resolved motion, not an arbitrary wind cap.

## Verification and next physical experiment

Nine new tests check the exact dry adiabatic path, the actual saturated gas/
exported-liquid enthalpy differential, a neutral dry environment, the exact
isothermal negative-energy limit, the expected stable/conditional/dry ordering,
analytical sign crossing, shallow inhibition between coarse levels, cloud-base
event convergence and invalid or supersaturated source rejection. The full
focused suite passes 282 tests.

Publication independently repeats the ODE with adaptive DOP853, reconstructs
the declared environment, integrates positive/negative linear segments and
locates condensation pressure using scalar bracketed roots. Raw pressure
paths, temperatures, mixing ratios, buoyancy and energy integrals are included
in the portable research atlas. No new coupled integrations are required;
the audit reuses the stable/conditional/dry manufactured runs.

The next useful closure test is conservative adjustment or convective transport
of unstable near-saturated layers, with actual water and enthalpy budgets and
the same stable/dry controls. It should account for a physical redistribution
of heat/water and activation conditions, rather than remove buoyancy or cap
winds without a reservoir. Residual instability and parameterization limits
must remain visible before a bounded Earth comparison.

No Earth integrations, model adoption or rainfall accuracy gains are claimed.
Earthr39 and normal world/biome/population atlas datasets remain unchanged.
Counters remain 1934 attempts / 1929 strict passes / four historical failures /
one historical interruption.
