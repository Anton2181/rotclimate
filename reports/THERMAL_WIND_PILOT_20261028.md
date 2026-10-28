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

## Completed outcome: failed rainfall criterion

All12 integrations completed and passed strict numerical checks and the80m/s
branch-speed guard. The six controls reproduced all original climate fields
and the extra PNW native archive exactly. All599 frozen sources/inputs were
verified. Independent analysis reconstructs396 solved seasonal steps and the
actual thermal shear from saved ground temperature, elevation and seasonal
lapse; numerical pressure quadrature agrees within8.81e-12m/s. The cumulative
counter is1898 attempts,1893 strict passes,4 old failures and1 old interruption.
No new scientific failure, failed numerical run or hidden restart occurred.

| Ocean | Region | Paired rainfall-loss ratio | Temperature monthly MAE change C |
|---|---|---:|---:|
| Legacy | India |1.973| −0.092 |
| Legacy | Mexico |0.914| −0.199 |
| Legacy | PNW |1.530| +0.100 |
| Hydrostatic half | India |2.075| −0.157 |
| Hydrostatic half | Mexico |0.794| −0.204 |
| Hydrostatic half | PNW |1.697| +0.122 |

Mean paired rainfall loss increases47.2%and52.2%, respectively, versus the
predeclared target of at least5%reduction. Mean temperature MAE changes by
−0.064C and−0.080C. Both ocean settings fail the rain criterion. No adoption,
shortlist, broad recalibration or independent validation follows. The opt-in
code remains available for controlled research; the default and published
world/Earth/biome/population data remain unchanged.

The hydrostatic-half annual rain changes from319to32mm in India,935to333mm
in Mexico and1036to436mm at PNW. India's JJA rain changes216→13mm versus515mm
observed; horizontal advective supply falls212→25mm and upward internal water
transfer288→16mm. Local surface evaporation falls146→11mm through feedbacks.
PNW DJF rain changes416→217mm versus340mm observed, while advective supply
falls312→16mm. These steady balances identify responses, not independent
recoverable causal shares. Upper return flow strongly changes together with
the common projection and mean circulation; the test does not isolate those
as separate causes.

The matched925–300hPa vector RMSE improves5.44→4.39m/s on India's11lowland
footprints and4.94→3.35m/s on Mexico's one land cell, but worsens2.24→2.61m/s
on PNW's3ocean cells. The native mean improvement cannot establish correct
vertical structure: India JJA700hPa modeled east/north becomes−6.63/+5.44m/s
against+0.43/−1.98reference, and PNW DJF700hPa becomes+19.76/−6.18against
+8.29/+3.08. Sparse masks and two-box pressure representation remain limits.

## Exploratory thermal-structure audit after the outcome

This audit was added AFTER outcomes, has zero climate integrations, modifies no
acceptance rule, and supplies no observed forcing or fitted physical parameter.
It uses already cached height fields: g*(Z_top−Z_bottom)/(Rd*ln(p_bottom/p_top))
is the hypsometric layer-mean virtual temperature. Compare it with the candidate
wind-temperature profile using identical925hPa-valid native pixels, Gregorian
months and true areas. Model virtual temperature uses the first-order1+0.61q
correction from actual independent layer water. This is model-assisted reanalysis
and an inferred virtual temperature, not direct independent air observations.

The candidate's virtual-temperature biases in925–700hPa are−4.77K (India),
−3.90K (Mexico),−3.64K (PNW ocean);700–300hPa biases are−2.94,−2.34,−3.18K.
A mean bias alone does not establish the horizontal gradients controlling wind.
Therefore an explicitly exploratory spatial plane also estimates gradients on
India's11native land footprints. Require at least4cells and full rank; Mexico
and PNW do not receive a spatial plane estimate. The fitted gradients are
DIAGNOSTICS, never model inputs or calibrated coefficients.

Three summer monthly gradient estimates averaged equally give:

| India JJA layer | Candidate east/north K per1000km | Reference east/north K per1000km |
|---|---:|---:|
|925–700hPa| +1.44 / +2.05 | −2.13 / +2.19 |
|700–300hPa| +1.27 / +2.08 | +0.58 / −0.54 |

The reference's meridional thermal gradient reverses sign aloft, whereas this
single uniform-lapse pattern cannot provide that vertical change in gradient
direction. The observation is regional and sparse; it does not prove a globally
valid replacement. It supports separating near-surface land/ocean anomalies
from a broader free-atmosphere temperature field and testing their vertical
structure before another coupled shear test. A possible later mechanism is
boundary-layer anomalies that weaken with height over a modeled zonal thermal
background. Do not turn this finding into a fitted regional attenuation factor
or an unplanned search through shear amplitudes. The pressure-gradient response
and mean-flow projection also need separate checks. After two well-tested
physical hypotheses fail, revisit the circulation/energy architecture.

Five plots and complete monthly, seasonal, native, shear and exploratory
thermal data are published in the launcher-served research companion. The
normal atlases retain their adopted climates. Numerical guards pass; the
physical hypothesis still fails its rainfall test, and that failure stays visible.
