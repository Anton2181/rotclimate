# Repeated pressure-coordinate moist feedback and convection controls

The new reduced model repeatedly evolves gas enthalpy, vapor, liquid phase,
hydrostatic pressure and horizontal velocity. It replaces the prescribed
phase-heating pulse with two-way feedback at every timestep. Energy exchange
closes within its declared dry/dilute pressure-coordinate assumptions.

It is not ready for Earth adoption: a conditionally unstable moist column
develops 41.8 m/s peak winds after six hours without a convection closure or
nonlinear momentum transport. Saturated-stable and dry controls remain bounded.
That stress result is retained rather than removed by tuning.

## Pressure and compression appear once

Descending pressure edges define fixed dry reference masses M=dp/g and
geometric-mean pressure centers. Hydrostatic geopotential is a trapezoidal
temperature integral in log pressure:

    diff(Phi) = Rd*diff(-log(p_center))*mean_adjacent(T)
    Phi = A*T, with sum(M*Phi)=0

The pressure gauge and velocity subspace exclude depth-mean barotropic motion.
This is stronger than rigid pressure lids alone. Actual dry continuity gives
the upward mass flux F=-cumsum(M*divU), with pressure velocity omega=-g*F.
The compression power on thermal cells is

    Qcompression = -T * [C^T * (Rd*diff(-log(p_center))*F)]

where C averages adjacent cell temperatures. Its sum cancels the actual
momentum pressure work exactly. Under pressure-grid refinement it recovers
Rd*T*omega/p times pressure-cell mass. Seven coordinate tests independently
verify isothermal and log-linear exact integrals, work on unequal pressure
grids, the analytical compression quadrature and invalid lids/order.

Only this compression term supplies adiabatic temperature change. The scalar
transport carries gas enthalpy and vapor, not fixed-height gas-plus-gz moist
static energy. Adding the earlier dry buoyancy cooling would count expansion
twice; adding the fixed-height rain-potential terms would mix different budgets.

## Actual coupled timestep

Momentum uses Crank-Nicolson pressure/Coriolis/drag with midpoint temperature.
Gas enthalpy and vapor use the existing conservative native-face backward-
Euler donor transport at midpoint velocity. Actual compression power, external
heating and vapor-source enthalpy enter the thermal source. Drag work returns
as local heat allocated from actual interior face velocities. Liquid phase
passes rain through all pressure cells and exports actual liquid enthalpy.

Temperature, pressure and transport are solved by fixed-point iteration.
Every iterate starts from the same old gas/water state, so iteration does not
reinject evaporation or repeatedly remove rain from an already updated state.
Nonconvergence raises an error; it is not accepted as a timestep. Actual
temperature, midpoint momentum/hydrostatic residuals, transport face budgets,
water and energy exchange are reported.

Within this reduced coordinate, the closed/source budget is

    gas enthalpy + kinetic energy + exported rain enthalpy
      = initial gas/kinetic energy + actual external energy

Vapor plus ground rain separately balances initial water and actual injection.
Positive-reference gas enthalpy adds a constant cp_d*M*T0; this cancels under
fixed dry-mass continuity. The finite-grid donor scheme supplies numerical
mixing; energy conservation does not prove an accurate entropy/convection law.

## Deliberate limits of the new coordinate

The hydrostatic and compression laws are dry/dilute. Fixed dp/g reference mass
does not evolve with water loading; vapor gas-volume feedback is omitted.
Phase uses dry/vapor/liquid heat capacities and actual rain sensible enthalpy,
but omits water gravitational potential, falling-rain work, stored cloud liquid,
precipitation kinetic energy and ice. It is an enthalpy-only phase approximation,
not the previously checked fixed-height fall-work kernel. The models remain
separate; no missing term is hidden in a fitted heating factor.

Closed pressure bounds, zero depth-mean flow and reflecting horizontal walls
are laboratory constraints. Prognostic surface pressure, nonlinear momentum
advection, radiation and terrain are absent. These limits matter for Earth
climate, especially a growing moist-convective response.

## Stable, conditional and dry controls

Both moist cases use ten pressure cells from 101325 to 38000 Pa, an 8-by-10
horizontal grid at 100 km spacing, Earth Coriolis at 30 degrees north and a
five-day momentum drag. They begin motionless, with the same manufactured
relative-humidity pattern spanning 0.88 to a supersaturated core.

Temperature is proportional to p^a. The saturated-stable case has a=0.08,
equivalent to a 2.73 K/km dry hydrostatic environmental lapse. The conditional
case has a=0.18, about 6.15 K/km: dry-stable but capable of moist instability.
The differing temperatures also imply differing water capacities. These are
mechanism controls, not otherwise identical Earth weather realizations.

Each case runs six hours at 600/300/150/75-second timesteps. A separate dry
control starts from the conditional case's initial phase-adjusted temperature,
removes latent feedback and runs at 150 seconds. There are 1224 total repeated
steps across eight moist runs and one dry control.

| Case | Finest peak level velocity | Mean six-hour rain |
| --- | ---: | ---: |
| Saturated-stable moist | 2.44 m/s | 1.053 mm |
| Conditional moist stress | 41.80 m/s | 5.179 mm |
| Dry, phase-adjusted initial temperature | 1.17 m/s | no water |

The conditional isolated initial phase produces only 0.152 mm mean rain.
Further rain develops through repeated circulation/transport/phase feedback.
The stable run remains bounded while the conditional case strongly amplifies.
The dry control argues against a universal dry numerical blowup, but does not
by itself validate the moist-convective stress response.

Both moist cases converge under timestep refinement. Conditional rain RMS
differences against 75 seconds fall from 1.422 to 0.596 to 0.196 mm for
600/300/150 seconds; temperature RMS falls from 0.275 to 0.124 to 0.041 K.
The stable equivalents are 0.01461/0.00567/0.00184 mm and
0.02500/0.00962/0.00302 K. Convergence retains the stress response rather than
eliminating it, so timestep error alone is not an adequate explanation.

## Verification and the next gate

Seven new coupled-model tests check motionless dry equilibrium, thermal-state
wind generation, actual dry and moist long-run energy/water/rain balances,
source enthalpy, returned drag heat, the enthalpy-only phase limit, iteration
semantics and rejection of failed coupling. Together with seven coordinate
tests and the prior 259 checks, the focused suite passes 273 tests.

Publication independently reconstructs final gas enthalpy, actual face kinetic
energy, rain enthalpy, water, saturation, depth-mean constraints and numerical
refinement from saved raw fields. Long-run energy and water errors are below
2.1e-14 relative. Histories retain per-step fixed-point and actual pressure/
compression-work residuals. Those budgets are necessary, not a physical
acceptance certificate for convection.

The next integration gate is a parcel-stability diagnostic and a physically
declared treatment of unresolved convection, tested against these same stable,
conditional and dry cases. It must preserve energy/water and should not tune
away the stress response with region-specific stability or wind coefficients.
Only then is a bounded regional Earth comparison useful before broader fitting.
No global-optimum proof or unanimous regional score improvement is required
for that experiment; physical and temperature guards still apply.

No Earth integrations or accuracy gains are claimed. Earthr39 and all normal
world/biome/population fields remain unchanged. Counters remain 1934 attempts /
1929 strict passes / four historical failures / one historical interruption.
