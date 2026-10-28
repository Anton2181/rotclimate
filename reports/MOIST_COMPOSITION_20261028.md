# Composed moist transport, phase change and falling-water work

Two new isolated kernels close the fixed-wind gas-static-energy/ground-rain
budget: `falling_water_energy.py` and `regional_moist_step.py`. They compose
native-face backward-Euler vapor/static-energy transport with nonlinear phase
adjustment. This is prognostic moist thermodynamics under fixed winds, not
an Earth climate integration or a completed momentum/radiative feedback.

## Falling water must release potential energy

Transport includes g(Md+Wv)z. The earlier phase model conserves gas/rain enthalpy
but omits falling-water potential work. Combining those equations directly
would silently lose g*Cu*(zupper-zlower)+g*P*zlower, where Cu is upper
condensation and P surviving ground rain. An independent test exhibits over
100kJ/m² lost from this omission.

The new phase step assumes instantaneous terminal fall and uniform drag per
fall distance. Condensate falling from upper centroid zu to lower centroid zl
deposits fraction (zu-zinterface)/(zu-zl) of that work in the upper box, with
the rest below. Surviving rain descends from zl to ground0 and heats the lower
box. All gravitational release becomes local gas/liquid-mixture heat; there
is no stored precipitation kinetic energy, surface impact reservoir or ice.
This is an explicit reduced fall/dissipation model, not a resolved drop model.

Dissipation feeds back inside the saturation root: upper heating changes Cu,
and lower heating changes evaporation and survival. It is not appended after
phase equilibrium. For vapor change x and a linear heat contribution A-beta*x,

    Tnew = T0 + [Hinitial + A - Lv0*Wold - (Lv0+beta)*x] /
                [cp_d Md + cp_v(Wold+x) + cp_l(Lold-x)]

Upper beta is its share of g*(zu-zl); lower beta=g*zl and A includes incoming
rain's remaining released potential and descent allowance. Bounds preserve
water/temperature. Incoming rain carries its actual upper-temperature liquid
enthalpy. Ground rain leaves at the lower temperature; ground height is0.
The resulting whole-column identity is

    initial gas enthalpy + vapor/dry potential
      = final gas enthalpy + vapor/dry potential + ground rain enthalpy

Water also balances with ground rain. The static-energy reference used during
transport differs by constant dry cp*Md*T0; fixed dry masses make this harmless.

## First-order operator composition

`advance_moist` first transports vapor and static energy using identical exact
dry face fluxes, then performs phase/fall equilibrium. It records every
external heat/vapor supply, boundary export and ground rain amount/enthalpy.
Actual composed energy and water changes are checked each step. No independent
c²divU temperature cooling is added; transport already supplies hydrostatic
adiabatic work. The splitting and backward Euler are first order.

Ten new tests check rain drag work, lost energy without it, complete
reevaporation, drag warming's effect on condensation, the zero-height limit,
invalid geometry and actual composed budgets with/without physical sources.
The preceding164 focused tests remain unchanged.

## Repeated-step demonstration

The saved humid-pulse native winds and phase-adjusted T/W are reused. Geometry
now matches the maintained15km uniform-density mode: lower quarter centroid
1875m, interface3750m, upper centroid9375m. Thus three quarters of upper-to-lower
fall work is deposited above the interface and one quarter below. No free
regional heating multiplier or observed rain forcing is introduced.

Closed, unforced24-hour integrations use6/3/1.5/0.75-hour steps, with phase
adjustment at every step. Temperature/vapor and cumulative ground rain are
prognostic. Each run conserves initial static energy as final atmospheric
static energy plus accumulated rain enthalpy, and initial vapor as final
vapor plus accumulated rain. Time-refinement differences are against the
0.75-hour run, not an exact forecast or Earth validation.

This supplies rain in the manufactured fixed-wind problem, not an improvement
in Earth rainfall accuracy. Fixed-pressure liquid-only boxes, instantaneous
terminal fall, fixed heights and prescribed winds remain strong approximations.
No pressure-mode momentum feedback, predicted radiation, cloud storage, ice,
compressible moving-coordinate work or wind kinetic-energy budget is solved.
A closed atmospheric momentum/thermodynamic feedback must still derive mode
pressure from the evolving thermal state consistently before any Earth pilot.
Earthr39 and all normal atlas climates remain unchanged. Earth counters stay
1934 attempts /1929 strict passes /four historical failures /one interruption.
