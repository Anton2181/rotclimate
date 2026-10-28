# Native-face multilevel moisture and shared-grid adiabatic audit

`rotclimate/multilevel_transport.py` generalizes conservative donor scalar
transport from two fixed boxes to any positive set of fixed dry-air layers.
It retains actual staggered horizontal mass fluxes and diagnoses every vertical
interface dry flux from cumulative horizontal mass divergence. Top/surface dry
flux is zero; an unbalanced dry column is rejected, not repaired by a source.

A positive scalar rate supports either an explicit steady reaction or backward
Euler with rate1/dt and source old/dt plus physical supply. The timestep term
is not condensation, rain or heat dissipation. At interior horizontal and
vertical faces, actual donor mixing ratio is amount/layer dry mass. Incoming
lateral flow uses specified layer mixing ratio; outgoing carries local donor.
There is no fixed humidity partition, convergence import or saturation reset.

The sparse M-matrix conserves all internal tracer transfers and preserves
nonnegative amounts. Every solve independently recomputes actual face fluxes,
per-layer/column budgets and dry-column closure. Roundoff at the top is exposed
rather than exported as fictitious dry air. Nine new tests check exact agreement
with the old two-level kernel, constant mixing-ratio equilibria over stratified
mass/overturning, independent multi-interface upward/downward donors, analytic
horizontal recurrences, closed budgets and invalid equations/dry mass flow.
Existing199 focused tests and older scientific kernels remain unchanged.

## Resolving the adiabatic mismatch

The new `audit_multilevel_adiabatic.py` compares a donor thermodynamic derivative
on the shared vertical cells with the hydrostatic eigenmode's adiabatic response.
Actual one-second implicit matrix solutions independently recover the same
semidiscrete response. This is a manufactured consistency audit, not a fitted
correction or observation-based skill score.

With uniform reference density, constant N and linear dry reference temperature,
mode response ratios are exactly cos²(pi/(2n)):0.990393 at16levels,0.997592
at32,0.999398 at64 and0.999849 at128. Vertical symmetry cancels the directional
bias in the first mode. These ratios should not be generalized to a real
stratified density profile.

Using the stable hydrostatic reference density and temperature, the first-mode
ratios are1.03124/0.95317 (ascent/descent) at16levels,1.01764/0.97845 at32,
1.00932/0.98970 at64 and1.00478/0.99497 at128. The donor-background one-sided
error is first order here and decreases with resolution. There is no stability
clipping or wave-speed multiplier. The previous unequal two-box/smooth-mode
audit had much larger0.51231/0.26370 responses. Resolving vertical structure
provides a demonstrated path toward shared thermodynamic/momentum states.
It does not yet prove nonlinear moist feedback or exact mechanical energy.

## Resolved moisture demonstration

`scripts/demo_multilevel_transport.py` builds32 vertical cells in the same
15km,N0.01/s hydrostatic reference. A dry thermal anomaly generates a mode
wind for6hours using the shared pressure/buoyancy/wind solver. Its exact
staggered winds, multiplied by the resolved vertical mode, then remain fixed
for24hours of conservative moisture transport. A smooth positive initial dry
mixing ratio declines with height; no external water or loss is supplied.
Eight3-hour backward-Euler steps preserve total vapor while redistributing it
vertically/horizontally. These are two sequential manufactured problems, not
a bidirectionally coupled moist atmosphere. No observed wind or humidity is
used. No phase step is performed; supersaturation, if any, is not reset and
no rain is diagnosed.

Raw layer masses, face winds, initial/final vapor, actual flux budgets and the
vertical-resolution audit are archived. The demonstration checks the intended
shared vertical geometry without interpreting passive moisture as rainfall.
The reference is anelastic with fixed heights/density and reflecting walls;
it is not compressible terrain physics or a predicted radiative climate.

Next: a consistent multilevel thermodynamic/phase state and pressure feedback,
with energy work and external reservoirs accounted. Avoid adding separate
adiabatic cooling twice, silently treating the old two-box thermodynamics as
these new interfaces, or calling a scalar sink precipitation. A bounded Earth
pilot still needs fixed Earth-like priors, mean location/month rain loss with
regional tradeoffs allowed, temperature/physical guards and excluded checks.
Earthr39/main atlas fields and Earth counters1934/1929/4historicalfailures/
1historicalinterruption remain unchanged. No new rainfall skill or global
optimum is claimed by this numerical refinement.
