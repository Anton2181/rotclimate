# Coupled hydrostatic thermal-wind mechanism test — declaration

The transport diagnosis found large lower/upper wind errors that the ocean
humidity change barely affected. This experiment tests one replacement wind
closure, with no fitting, observed wind forcing or planet changes. The earlier
isolated operator is now coupled behind `moisture_thermal_layer_winds=False`.
The default T/P/W/layer-water/days reproduce the pre-edit toy climate exactly.
56 focused tests pass, including independent pressure quadrature, terrain-only
invariance, manufactured transport and strict coupled layer-water ledgers.

## Temperature coordinate and physical approximations

The modeled common-height Tsl field is interpreted as a common101325Pa thermal
reference A, smoothed at the existing500km synoptic scale. It is not a raw
terrain-cooled surface temperature or an observed temperature field. The new
wind profile is T(p)=max(A(p/101325)^kappa,200K), with kappa=Rd*Gamma/g and the
fixed environmental Gamma=6K/km used by this pilot. This common-pressure
reference is an approximation to the existing common-height thermal state,
not a new solved vertical temperature/energy field. The fixed dry-pressure
mass geometry and temperature profile remain diagnostic approximations.

Take grad_p(T) at FIXED pressure before integrating between the local layer
pressure centroids0.875ps and0.375ps. The analytic integral accounts for the
200K floor. Taking a gradient of the moving-bound temperature mean would add
false terrain-driven shear; a uniform common reference over varying surface
pressure must produce exactly zero shear, which is independently tested.

The desired lower wind retains its existing1km thermal-height contribution.
The desired upper wind adds the hydrostatic/geostrophic pressure shear.
Project the dry-mass mean and apply a common correction to both branches,
preserving their difference and exact dry continuity. Orbit, gravity, rotation,
Rd, dry masses, all numerical settings, rain laws, ocean settings, storm
exchange and drying coefficients remain fixed. The existing smooth10degree
Coriolis regularization remains; this is not equatorial momentum dynamics.

The inherited provisional fixed-q water weights for pre-solve rain/drying
inputs remain unchanged as a law. The actual reservoir solve still replaces
them with independently solved lower/upper water fractions. Shear construction
and the dry projection themselves use no humidity ratio. Internal water donor
exchange remains explicit and conservative. These choices isolate the wind
mechanism while retaining existing empirical feedbacks and fixed observed
cloud/remote-monsoon backgrounds. The setup remains a conditional regional
model, not a fully independent global physical forecast.

## Twelve literal integrations, fixed before outcomes

North India, Mexico and PNW × legacy/hydrostatic-half ocean settings × old/new
wind closure =12 integrations. Run six exact historical controls first, then
six new cases. Every original control climate array and extra native PNW field
must match the old ocean pilot exactly. Actual parameters may differ only by
the newly explicit default-off flag. Four-file Git source transition2dd22be to
7439e98 binds config/model/joint/thermal_layer_winds; every other parent source
and cached input is unchanged. New runner, analysis helper, tests and literal
plan are frozen and committed before integrations. Preserve all failures.

The new wind closure must keep strict solver/water/dry-mass checks and all33
primer/scored step certificates, the exact declared thermal geometry/constants,
and branch speeds below80m/s without velocity clipping. A material process
win requires mean paired regional rainfall-loss ratio<=0.95 and mean monthly
temperature MAE increase<=0.25C. Use existing location/month-sensitive rainfall
loss, equal regional weights. Expose every regional regression; no individual
rain-score veto. Native vector/humidity changes are separate diagnostics and
cannot substitute for rainfall gains. Tests cover these acceptance rules.

Either ocean setting may support the mechanism; report both. No automatic
adoption, independent validation claim or parameter shortlist follows from
this development-region test. A promising mechanism needs excluded-region,
finer-grid and transfer tests. After two well-tested physical hypotheses fail,
reassess circulation/water architecture instead of extending parameter boxes.

Counter before:1886 attempts,1881 strict passes,4 old failures and1 interruption.
A completed12-run experiment brings actual attempts to1898. Toy/manufactured
checks are not Earth benchmark integrations.
