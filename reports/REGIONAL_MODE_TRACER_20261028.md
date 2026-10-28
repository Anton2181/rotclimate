# Native-face water transport for the regional dry mode

`rotclimate/regional_mode_tracer.py` supplies a conservative passive tracer
bridge for the new staggered regional circulation. It does not change the
Earth climate model, rainfall law, humidity observations, atlas climates or
calibration counts. Nine tests pass; combined with the periodic and regional
dry operators, 35 tests pass. The existing cell-wind reservoir solver remains
unchanged: averaging the new face winds into its input would alter the solved
mass flux and continuity, so this foundation retains native faces directly.

## Actual donor equations

For constant lower dry mass fraction a and positive total dry-column mass M,
layer masses are aM and (1-a)M. Given dry mode U, the lower dry face flux is
`-a(1-a) Mface U`; the upper flux is its exact floating-point opposite. Internal
face mass is the neighboring-cell arithmetic mean. The lower vertical outflux
is `Fup=a(1-a) M div(M U)/M`, including exterior fluxes. Its donor mixing ratio
is lower W/(aM) when Fup is positive, upper W/((1-a)M) when negative.

Each layer's steady water equation is

    source = removal_rate * W + div(horizontal donor water flux)
             + signed vertical donor water flux

Interior and exterior horizontal flows use upwind *mixing ratio*, not water
amount. Incoming external air carries independently supplied layer humidity;
outgoing air carries local humidity. These choices preserve uniform mixing
ratio over varying column mass. Each vertical water transfer appears once
with opposite signs in the two layers. It cannot create or remove column
water, and there is no prescribed upper/lower humidity ratio.

The supplied removal rate is strictly positive in this prototype. Together
with donor transport it gives a nonsingular M-matrix even in stagnant cells:
the positive removal dominates the transport matrix's otherwise conservative
column sums. Nonnegative supplies and exterior humidity produce nonnegative
water. There is no post-solve clipping, resaturation, iterative humidity reset,
or import term derived from observed rain. Every solve checks both the sparse
matrix equation and the independently recomputed actual face equation.

If M is kg/m², W is kg/m² (equivalently mm liquid water), source is kg/m²/s and
mixing ratio is kg/kg. The demo uses M=10000 kg/m² times the prior synthetic
relative-mass pattern; this is a fixed demonstration scale. Rates and integrated
budgets sum equal-area cells; multiplication by dx² gives actual kg/s. The
reported per-cell sums must not be misread as already integrated kg/s.

## Validation and demonstration

Tests recover independent source/removal boxes, two analytic opposing-flow
upwind recurrences, uniform humidity with variable mass and passive boundaries,
a manufactured nonuniform humidity field with both upward and downward donor
exchange, independent boundary/layer/column water budgets, rejection of stale
circulation geometry and invalid supplies/removal. No test asserts rainfall
accuracy. Test-time errors during implementation are not Earth integrations.

The demonstration `scripts/demo_regional_mode_tracer.py` reads the committed
regional mode receipt, verifies its frozen source/image hashes, and transports
water using its exact solved faces. It compares closed and passive boundaries
under the same prescribed lower water supply (2 mm/day), 10-day removal and
external lower/upper mixing ratios 0.009/0.0025 kg/kg. Upper water is solved
independently; dry upward/downward exchange uses actual donor humidity. The
removed water is a tracer sink, **not predicted precipitation**. There is no
condensation or latent-energy feedback. The receipt contains all fluxes and
independent water-budget checks. It adds two passive tracer solves and zero
Earth integrations. Cumulative Earth counts remain 1934 attempts / 1929 strict
passes / four historical failures / one historical interruption.

## Before an Earth rainfall pilot

This foundation needs physically budgeted atmospheric heating, background
circulation and incoming lateral states, terrain metric/blocking treatment,
a physical moisture source/condensation/latent-feedback coupling, and declared
Earth-like mode/damping priors. The dry mode is a linear steady approximation,
not a complete primitive-equation atmosphere. Its passive normal impedance
is not a transparent rotating-wave boundary. Do not interpret the manufactured
water maps or sink as a new Earth climate or an improvement in rainfall skill.
The next bounded coupled test must use actual location/month rainfall error,
allow regional tradeoffs, and retain temperature/conservation guards. Its
nonlinear calibration can have local minima even though each isolated linear
circulation/tracer solve is unique. Neither uniqueness here nor these test
passes establishes a global climate optimum.
