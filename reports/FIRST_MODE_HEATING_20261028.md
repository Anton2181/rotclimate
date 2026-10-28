# Accounted latent heating to an explicit first vertical mode

The new `rotclimate/baroclinic_heating.py` derives forcing and gravity-wave speed
for a constant-stability hydrostatic Boussinesq atmosphere with rigid lids.
This is a physically specified reduced vertical model, not a compressible
Earth atmosphere or a validated regional rainfall forecast. The phase-change
step and dry circulation are connected in a forward demonstration; their full
nonlinear moist/energy feedback is not yet solved.

## Vertical structure and normalization

For height z from0 toH, uniform reference density and constant buoyancy frequency
N, use m=pi/H and vertical profiles

    velocity(z) = -Uamp cos(m z)
    pressure(z) = -Phiamp cos(m z)
    buoyancy(z) = m Phiamp sin(m z)
    vertical_velocity(z) = div(Uamp) sin(m z)/m

Hydrostatic balance, continuity and the linear buoyancy equation yield

    d(Phiamp)/dt + c² div(Uamp) + rT Phiamp = Qamp
    c = N/m = N H/pi

For explicitly accounted layer heat Hlayer W/m² and layer dry mass Mlayer,
heating per mass is h=Hlayer/Mlayer and buoyancy source is g*h/(cp*Tref).
Project it onto sin(pi*z/H):

    Bdot1 = 2 integral_0^1 buoyancy_source(s) sin(pi*s) ds
    Qamp = Bdot1/m

The integral is exact for piecewise constant layer-specific heating. The
constant reference density makes layer mass fractions equal height fractions.
Reference pressure is linear with height, using the same dp/g dilute mass
approximation as the box demonstration. These are stated Boussinesq assumptions,
not a realistic compressible height-pressure relation or solved background
potential-temperature profile. Fixed N supplies a maintained stable reference;
it is not diagnosed from the two coarse box temperatures.

For lower fraction a and upper fraction1-a, the cosine layer-average winds
satisfy the existing regional embedding with

    S = sin(pi*a)/(pi*a*(1-a))
    Usolver = S Uamp; Phisolver = S Phiamp; Qsolver = S Qamp
    Ulower = -(1-a) Usolver; Uupper = a Usolver

This preserves exact column dry mass and matches direct continuous vertical
averages. It also avoids guessing a heating multiplier from regional rain gains.

## Mode energy and unresolved heat

The continuous reference-mass kinetic plus available potential energy is
`(Uamp² + (Phiamp/c)²)/4`. Therefore multiply the regional solver's energy/work
identity by `1/(2*S²)` to obtain the continuous first-mode budget. Its physical
buoyancy work equals the independent integral of buoyancy times its source
weighted by1/N². Coarse two-layer mean kinetic energy alone omits within-layer
velocity variance and must not be equated to the continuous mode's energy.

The projection retains net column heat separately and reports the fraction of
buoyancy-forcing squared norm captured by the first sine mode. The remaining
mean/higher-mode heat is not silently removed from the phase/enthalpy ledger.
Captured forcing norm is not a fraction of total heat, nor a rainfall accuracy
measure. The available-energy work is also not the full thermodynamic heat
input: mean internal energy and the maintained reference stratification are
outside this single-mode circulation. A complete atmospheric first-law budget
would require prognostic heat transport, radiation, potential/gravitational
energy and the other vertical modes.

## Forward demonstration

`scripts/demo_latent_circulation.py` uses the same upper moist pulse over two
lower humidity states. A synthetic3400m ridge sets surface pressure through
101325*exp(-height/8000m); top pressure is100hPa and a=0.25. Mass is dp/g,
with lower/upper box representative pressure at the interval midpoint. Initial
box temperatures are298K/250K. Upper RH varies from0.75 to1.60; lower RH is
0.25 or0.98. The phase step conserves water and its stated dilute enthalpy.
Condensation and cooling are accumulated over an explicitly chosen one-day
forcing interval. This interval belongs to the manufactured pulse and is not
a measured cloud lifetime or a fitted Earth parameter.

Actual phase heat divided by that interval is projected with H=15km,
N=0.01/s, Tref=275K, giving c=47.75m/s. Momentum/thermal damping are fixed5/20days.
The regional operator then gives a steady *linear response* to this source.
Closed boundaries isolate the local response; there is no imposed incoming
observed humidity or wind. Five-day drag and a one-day pulse do not imply the
atmosphere reaches the steady response within that day. This is not a transient
coupled integration. Moisture is not then re-transported and re-condensed.

The comparison demonstrates why atmospheric condensation and ground rain must
be stored separately: dry lower air can reevaporate all falling water while
upper heating and lower cooling still force a circulation response. Humid
lower air passes more rain to the ground and has less evaporative cooling.
No observed rainfall, humidity or winds enter these manufactured sources.

## Verification and next experiment

Eleven vertical-mode tests check the analytic uniform-heating sine coefficient,
derived wave speed, exact layer-average winds, direct continuous buoyancy work
and energy integrals, heating cancellation and unresolved forcing, and invalid
inputs. Together with22 phase/thickness tests there are33 new checks. Receipts
bind source hashes, raw fields, phase water/enthalpy, actual heat projection,
and independent first-mode energy work. The regional and native-face tracer
kernels from earlier milestones remain unchanged.

This adds two isolated regional linear responses and zero Earth climate runs.
Cumulative Earth counts remain1934 attempts /1929 strict passes /four historical
failures /one historical interruption. No Earth rainfall improvement or climate
adoption is claimed. Next requirements include a prognostic moist-column energy
and transport closure, compressible/terrain vertical modes, background circulation
and actual incoming states, with fixed Earth-like priors before a bounded coupled
Earth comparison. Single-mode linear uniqueness does not establish a global
minimum of the full nonlinear calibration objective.
