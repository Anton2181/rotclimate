# Transient thermal-state, pressure and momentum feedback

`rotclimate/hydrostatic_wave.py` evolves one normalized vertical eigenmode from
the energy-paired anelastic grid. This closes thermal-state/pressure/momentum
feedback within a specified **linear dry** reference atmosphere. It does not
attach an incompatible pressure law to the prior two-box moist transport,
claim a fully coupled moist atmosphere, or change Earth rainfall forecasts.

## State and operators

An initial virtual-potential-temperature buoyancy field determines hydrostatic
reduced pressure by D*phi=b. Its pressure-mode amplitude is projected with the
vertical mass norm. Keeping one mode explicitly reports initially excluded
available energy; it does not silently call a truncated profile complete.
Pressure levels and buoyancy interfaces are always reconstructed from that
same evolving amplitude, so their hydrostatic relation holds at every step.

The horizontal grid is a closed Cartesian staggered grid. Normal exterior
velocities are exactly zero. For internal east/south velocities u/v and pressure
amplitude Phi, the state equations are

    du/dt + r u + R v + Gx Phi = 0
    dv/dt + r v - R^T u + Gy Phi = 0
    dPhi/dt - c²(Gx^T u+Gy^T v) + rT Phi = Q

c comes from the vertical eigenproblem, not an independently fitted wind
parameter. The vertical mode has mean(M F²)=1, so per-reference-mass energy is
one half of the horizontal mean of u²+v²+(Phi/c)², using actual internal face
quadrature. R and -R^T ensure Coriolis does no work even with varying f.
Pressure work and adiabatic buoyancy work cancel. Vertical mass velocity is
diagnosed from the actual mode-weighted horizontal divergences and closed lids.

Crank-Nicolson uses midpoint state for pressure, Coriolis, heating work and
damping. Every step checks actual momentum/buoyancy residuals and

    Enew-Eold = dt*(midpoint heating work - midpoint damping)

With zero damping/source it conserves quadratic modal kinetic+available energy.
This is not a full moist thermodynamic/first-law budget. Initial available
energy can become kinetic energy: a prescribed wind or steady thermal-response
solve is no longer needed to generate the motion in this reduced model.

Interface buoyancy heating is projected with the same vertical energy weight.
The norm of source retained in the selected mode and the excluded norm are
reported. These are squared forcing norms, not fractions of total heat input.
No second adiabatic tendency is added to the separate moist-static-energy code;
these two representations still need a common vertical prognostic discretization
before they can be composed.

## Tests and full-day example

Eleven new tests cover independent closed-box discrete standing-wave dispersion
including the exact Crank-Nicolson phase, analytic relaxation and uniform heating,
thermal anomalies generating wind, actual hydrostatic reconstruction, energy
under varying rotation, independent vertical heating work with excluded modes,
and invalid states/timesteps. Together with14 new vertical-state tests these
are25 new checks on top of the preceding174 focused tests.

The demonstration initializes a small temperature anomaly on interfaces of the
stable hydrostatic reference: theta_surface300K,ps101325Pa,N0.01/s,depth15km,
64 vertical cells. Actual ideal-gas reference density enters the mode. Pressure
and winds are initialized from the resulting buoyancy; the initial wind is zero.
The horizontal domain is4800 by4000km on100km cells with Earth rotation varying
with northing about30°N. One run is undamped; another uses fixed5-day momentum
and20-day buoyancy damping. Neither has imposed heating or lateral inflow.
A24-hour timestep-refinement comparison uses60/30/15/7.5-minute steps.
The walls reflect internal waves; this is not transparent regional circulation.

## Remaining climate work

This proves state feedback and discrete dry modal energy in a linear anelastic
approximation. It does not predict convection, rain, clouds, ice or radiation,
and does not evolve compressible density or terrain. Temperature is diagnosed
from virtual-potential buoyancy about a maintained stable reference. The prior
moist two-box representation cannot supply this grid's interface state without
a separately consistent discretization; the measured51%/26% one-sided coupling
audit is why it was not simply wired in.

The next Earth-oriented step needs shared vertical thermodynamic and momentum
states, conservative moisture/phase/source accounting on that grid, realistic
incoming states and radiative/thermal reservoirs. Only then declare a bounded
Earth comparison with fixed Earth-like priors, regional rainfall tradeoffs and
temperature/physical guards. Existing Earthr39 and normal atlas fields stay
unchanged. No new Earth integrations, rainfall gain or global optimum are
claimed. Counters remain1934 attempts /1929 strict passes /four historical
failures /one historical interruption.
