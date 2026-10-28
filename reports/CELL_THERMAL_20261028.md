# Shared-cell dry thermal dynamics and a resolved phase pulse

The new cell thermal formulation evolves pressure, buoyancy and horizontal
velocity at every vertical level, with no selected vertical mode. It puts dry
buoyancy at the same cell locations as resolved temperature and moisture. Its
hydrostatic pressure and adiabatic thermal update have an exact discrete work
identity on unequal cells. A conservative liquid-phase pulse now supplies a
checked virtual-buoyancy source to this dry dynamical system.

This is a linear dry dynamical test with one prescribed phase-derived source,
not a bidirectionally coupled moist atmosphere or a rainfall skill improvement.
The cell-centered grid also exposes a pressure-invisible computational thermal
mode; that limitation is retained and quantified.

## Hydrostatic pressure and the thermal adjoint

Let M be diagonal dry cell mass, E=M/N² the diagonal thermal available-energy
weight, and C linear interpolation of cell buoyancy to interior interfaces.
Actual cell widths supply C on an uneven grid. Hydrostatic pressure is

    diff(phi)/diff(zcenter) = C*b
    phi = H*b, with sum(M*phi)=0

Closed-lid continuity uses actual horizontal mass divergence:

    rho_face*w_face = -cumsum(M*divU)

Integration by parts gives

    (M*divU)^T * H*b = (rho_face*w_face*diff(zcenter))^T * C*b

The adiabatic cell tendency follows from the exact energy adjoint:

    b_t = -E^-1 * H^T * M*divU + Qb

Equivalently, it is -N²/M times C^T acting on rho_face*w_face*diff(zcenter).
On a uniform grid this is -N² times the mean of the two adjacent face vertical
velocities, with zero velocities at the rigid lids. Density/distance weights
are required on unequal cells; independently choosing a midpoint average there
would break the pressure/thermal work identity.

The horizontal momentum equations use the actual gradient of H*b and a skew
Coriolis interpolation on the closed Cartesian C-grid. Variables are scaled
by sqrt(M/totalM) for velocity and sqrt(E/totalM) for buoyancy. The pressure and
thermal blocks are transposes with opposite signs. Crank-Nicolson then obeys

    Etotal_new - Etotal_old = dt*(midpoint thermal-source work - damping)

where Etotal is dry kinetic plus quadratic thermal available energy per
reference mass. The solver neither projects away a solved flow nor resets
temperature. Closed-lid mass-mean velocity is checked with explicit relative
and absolute roundoff tolerances, and its actual maximum is reported.
The velocity state is restricted to zero depth-mass-mean baroclinic flow.
Divergence-free barotropic winds, which can also satisfy rigid-lid continuity,
are excluded; this is a stronger restriction than closed lids alone.

This is a fixed-reference, linear anelastic available-energy law. It is not
the full nonlinear gas/rain static-energy law, and the two cannot simply be
added as if they were independent conserved reservoirs.

## Internal modes and a visible computational mode

The mass-symmetric matrix sqrt(M)*H*E^-1*H^T*sqrt(M) has n-1 positive c²
eigenvalues and a zero barotropic pressure mode. Its pressure modes are
mass-normalized; cell buoyancy modes follow from E^-1*H^T*M*F/c². On a uniform
grid of n cells and width dz, the independent dispersion relation is

    c_k = N*dz / [2*tan(k*pi/(2*n))],  k=1,...,n-1

The implementation computes the singular values/vectors of
sqrt(M)*H/sqrt(E) directly instead of forming its squared normal matrix. A
128-level check exposed loss of hydrostatic-mode accuracy in the latter
calculation. The direct singular-value formulation avoids squaring the
condition number and passes the independent full spectrum and hydrostatic
identities through 256 levels.

The cell-to-face interpolation also has a one-dimensional thermal nullspace:
cell buoyancy proportional to alternating signed cell width gives C*b=0.
It can retain thermal available energy while producing no pressure gradient.
This is a computational feature of the Lorenz grid, not a novel physical
equilibrium. It is not clipped, smoothed or silently discarded. Energy is
partitioned into pressure-active and pressure-invisible thermal components;
the latter remains stationary under adiabatic evolution and responds to its
actual source projection. Tests explicitly excite it.

The original staggered-interface vertical-state formulation remains available
unchanged. Sharing thermal cell locations has this numerical cost; the null
mode and its effect on phase/transport must be considered before choosing a
production moist grid. A small null fraction in one smooth test is not proof
of a general bound or a reason to ignore cell-scale heating.

## Controlled phase-pulse experiment

The demonstration uses 16 vertical cells over a shallow 8 km column and a
12-by-16 horizontal grid at 100 km spacing. The reference has Ts=300 K,
ps=101325 Pa, lapse=6 K/km and an explicit 200 K cap. Reference N² is derived
from that structure. Dry cell masses are dp/g. Earth rotation corresponds
to 30 degrees north. The reference is held fixed; the walls reflect waves.

A manufactured relative-humidity pulse ranges from 0.8 to a slightly
supersaturated core. One resolved liquid-only phase adjustment includes actual
vapor/liquid heat capacities, rain evaporation, fall potential work and ground
rain enthalpy. In this case all falling liquid reevaporates before ground,
so ground rain is zero. The maximum temperature adjustment is about 0.715 K.

The actual temperature and vapor change supplies

    delta_b = g*[Tv_after - Tv_before]/T_reference
    Tv = T*(1+r/epsilon)/(1+r),  r=vapor/dry_mass

That delta_b is imposed as a constant source for one hour, followed by five
hours of unforced dry dynamics from initially zero wind and zero perturbation
buoyancy. It is a prescribed source from a resolved phase calculation, not
ongoing water transport, repeated condensation or interactive moist feedback.
The moist-static-energy transport step is not composed here, so a second
adiabatic cooling is not added to an existing expansion-cooling tendency.

Four timestep sequences of 20/10/5/2.5 minutes make 270 dry dynamic steps.
The finest run reaches maximum absolute east and south level velocities of
0.678 and 0.682 m/s. Its final kinetic plus thermal available energy is
0.00694267 m²/s²; 0.00006166 m²/s², about 0.89%, is in the pressure-invisible
thermal mode. Source-free energy remains constant to numerical roundoff.

| Timestep | RMS pressure difference m²/s² | RMS east velocity difference m/s | RMS south velocity difference m/s |
| --- | ---: | ---: | ---: |
| 20 min | 0.075845 | 0.0017969 | 0.0018187 |
| 10 min | 0.019369 | 0.0004542 | 0.0004596 |
| 5 min | 0.003936 | 0.0000922 | 0.0000933 |

These are final differences against the 2.5-minute run, not Earth errors.
The phase water/static-energy ledger and dry linear source/work ledger are
checked separately. The publisher reconstructs the source from actual phase
fields and verifies final dry energy against an independently computed inner
product of that source with the saved time-integrated midpoint buoyancy.
It also reconstructs hydrostatic pressure, interface continuity, mass mean
and the null amplitude from raw cell fields. This tests the represented source
work; it does not establish a complete nonlinear moist mechanical energy law.

## Verification and remaining climate work

Eleven new column tests cover six independent uniform-grid dispersion cases,
actual uneven-grid pressure/thermal work, hydrostatic reconstruction, exact
uniform-grid adiabatic averaging, visible computational-mode energy, null
invariance, and invalid mass/stability inputs. Six new dynamical tests cover
closed-box horizontal/vertical dispersion including exact numerical phase,
energy with varying Coriolis force, actual source work with damping, stationary
computational heating, uniform horizontal heating without spurious wind, and
invalid mass/timestep constraints. Together with the prior 232 focused tests,
249 pass. These include 128/256-level regressions for the mode-conditioning
issue. Additional vertical phase-heating refinement is still required; the
large-scale dry wave speed converges faster than the nonlinear phase pulse.

Before a useful Earth rainfall trial, the prognostic moisture/phase state and
this thermal state need a common thermodynamic update, reference-maintenance
and pressure/kinetic-work accounting, and suitable incoming/radiative states.
The pressure-invisible cell mode needs an explicit grid/design decision;
filtering its energy away would require a recorded dissipative reservoir.
The present liquid-only phase remains warm/supercooled and omits snow/ice,
cloud storage, finite fall time and precipitation kinetic energy. The dynamics
omits nonlinear momentum advection, compressible density, radiation and terrain.

No Earth integrations or calibration claims accompany this milestone.
Earthr39 and normal world/biome/population fields remain unchanged. Counters
remain 1934 attempts / 1929 strict passes / four historical failures / one
historical interruption. This work addresses a physical discretization gap;
it is not evidence for a global calibration optimum.
