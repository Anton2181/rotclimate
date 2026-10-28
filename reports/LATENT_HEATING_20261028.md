# Conservative phase change and physically accounted heating

The isolated regional circulation needs an actual atmospheric heating rate.
The existing empirical surface-temperature corrections do not define one.
`rotclimate/phase_adjustment.py` now supplies a conservative liquid-only
saturation adjustment and falling-rain step, while `heating_projection.py`
accounts for heat input in physical units and its dry hydrostatic thickness
tendency. Both are development foundations; the Earth climate implementation,
rainfall law, saved parameters and published climates remain unchanged.

## Water and dilute enthalpy

With dry mass Md kg/m², vapor W kg/m² and incoming liquid L kg/m², the state
uses fixed pressure, constant cp=1004 J/(kg K), Lv=2.5e6 J/kg and the existing
Bolton liquid saturation formula. The saturation mixing ratio is per **dry**
mass, r=epsilon es/(p-es), rather than specific humidity q per total gas mass.
The conservative equilibrium solves for vapor change x:

    Tnew = Told - Lv*x/(cp*Md)
    Wnew = Wold + x
    Lnew = Lold - x
    Wnew = Md*rsat(Tnew,p) if liquid remains

All available liquid evaporates if the resulting air remains undersaturated.
The saturation residual is strictly increasing in x; bracketed bisection gives
a unique equilibrium. Condensation warms air and raises its saturation capacity,
so the amount condensed differs from clipping water at its old temperature.
Evaporation cools air and lowers capacity, so rain cannot evaporate beyond the
cooling-adjusted saturation state. No post-solve humidity reset is needed.

Every solve checks actual water and the **specified dilute enthalpy**
`cp*Md*T + Lv*W`. This is deliberately not a complete moist-energy equation:
water-vapor/liquid heat capacity, ice, liquid precipitation enthalpy and
precipitation gravitational work are omitted. The saturation formula is liquid
only, including supercooled water. No ice forecast is claimed. Input temperatures
are180–330K and pressures10–110kPa, with supported equilibrium150–370K;
initial vapor/dry mixing ratios above0.2 are rejected. Near-boiling states are
unsupported. Representative layer pressures approximate well-mixed boxes,
not a resolved vertical cloud or a convective instability closure.

## Falling rain and heating location

In the two-layer step, upper supersaturation condenses and warms the upper
layer. All upper condensate then falls into the lower layer, where it can
evaporate and cool that layer. Lower supersaturation can also condense.
Surviving liquid reaches the ground; there is no cloud storage or finite fall
time. Column vapor loss equals ground rain. Summed sensible heat equals
Lv times net ground rain in this simplified enthalpy convention.

The vertical distribution still matters: **zero ground rain can coexist with
upper latent heating and equal lower cooling** when all falling water
reevaporates. Inferring atmospheric heating from ground rain alone would miss
this dipole. Condensation, reevaporation and ground rain are stored separately.

## Heat ledger and hydrostatic thickness

For descending pressure interfaces, the diagnostic layer dry mass is dp/g
(the dilute pressure-mass approximation). Explicit layer heat H in W/m² gives
`Tdot=H/(cp*Md)`. Piecewise uniform temperature then gives the dry fixed-pressure
thickness tendency

    Qthickness = Rd sum[ln(pbottom/ptop) * Tdot]

Its units are m²/s³. The net column heat sum(H) is retained separately. Zero
net column heat can produce a nonzero thickness tendency because heating at
different levels has different log-pressure weight. This is a hydrostatic
diagnostic, **not yet a vertical eigenmode projection**, and does not prove
that the regional dry solver's chosen wave speed/vertical mode matches it.
Virtual-temperature changes, moving pressure boundaries and terrain metrics
are excluded. A mechanical mode projection must be derived separately before
calling this coupled atmospheric physics. Do not simply equate thickness
forcing to a validated first-mode forcing.

## Checks and scope

Twenty-two tests cover an independent scalar Brent root, dry/specific humidity
conversion, water and actual enthalpy budgets, full and partial reevaporation,
both layers condensing, latent warming's effect on saturation, analytic
hydrostatic heat cases, vertical heating dipoles, independent continuous
pressure integration under refinement and invalid input rejection. All earlier
regional circulation/tracer sources remain untouched.

Zero regional Earth integrations are added. Cumulative counts stay1934 attempts,
1929 strict passes, four historical failures and one historical interruption.
No rainfall improvement or climate adoption is claimed. The next work is a
proper vertical-mode projection with known stratification and a physically
accounted column-to-circulation demonstration. Full atmospheric energy transport,
radiation, terrain, moisture sources and lateral states are still prerequisites
for a bounded Earth rainfall trial.
