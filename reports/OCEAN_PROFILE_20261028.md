# Hydrostatic ocean humidity and rainfall — 28 October 2026

A new fixed coupled pilot follows the completed joint calibration, whose
32newsettings did not beat the retained wind setting, and the independently
verified marine RH process test. It changes an ocean boundary law behind an
opt-in flag. No climate or atlas replacement is authorized by this declaration.

## Literal paired design

Use the retained wind-study global01 rain setting: storm exchange3.5/day,
rain timescale15.532421910244794days, activationRH0.8098909563459455,
legacy full subsidence/monsoon drying. Test background wind4.5and3.5m/s.
At each wind run the same three ocean target modes:

| Mode | Hydrostatic ocean flag | RH taper | Ocean target |
|---|---|---:|---|
| Legacy |false|0|existing empirical total and existing layer-supply shape|
| Hydrostatic uniform |true|0|absolute pressure-integrated uniform-RH column|
| Hydrostatic half |true|0.5|pressure-integrated column with half-strength RH taper|

The uniform physical control separates the absolute total-water law from the
additional RH shape and water reduction in the half-taper target. Total water
is never renormalized. Hold the actual calibrated surface-RH coefficient
0.7547460305996778 fixed (warm increment0). The reference process study used
literatureRH0.77 and an observed925hPa anchor; this climate pilot uses actual
modeled SST and terrain pressure, not those observed air/humidity profiles.

The same selected environmental6K/km thermal profile and dry layer masses
supply target total and lower/upper fractions. Ocean exchange and external
regional boundary reservoirs receive that target. Actual lower/upper interior
water remains independently solved by conservative transport and rainfall;
no humidity reset, new latent-energy equation or new planetary setting occurs.
Land rain capacity and all nondeclared actual parameters stay unchanged.

Four historical exact controls precede six fixed profiles, each on the same
seven reused regions: **70maximum actual new Earth integrations**. The fresh
legacy4.5profile must additionally reproduce the old retained wind setting's
full main NPZ fieldsets/arrays and native companion. This extra matched epoch
check is an actual rerun, counted once among the six profiles.

## Explicit source epoch and safeguards

Core opt-in implementation commit76adf7e changes exactly config, model,
column_thermodynamics and joint parameter classification. The plan binds the
SHA256 and committed Git bytes before(30a925f) and after(76adf7e) for those
four files. Every other historical source and input remains exact. Historical
protocols and outcomes are not rewritten. The new fixedpilotrunner freezes
current sources and preserves the source transition separately.

Both pre-edit strict toy legacy/independent simulations reproduce T/P/W/days/
layer_water bit-exact after the edit; all91focused core checks pass. Another
26focused epoch/kernel/objective checks pass, including rejection of changed
observations, invented old code bytes, wrong running versions and missing
seasonal ocean certificates. All old environmental6native saturation arrays
reproduce exactly under the new default thermal code; the original marine RH
reference support is retained as reference evidence, not a claimed climate
response. No real-Earth integration ran before this declaration commit.

Each primer and scored step must certify actual ocean mode/taper, temperature
profile/lapse, grid cell count, surfaceRHbounds and target-water positivity,
alongside existing strict layer/column/transport/branch residuals. Physical
surface RH, including any warm increment, must lie in(0,1]. Sea-free grids
record no applicable target extrema. Failed candidate evidence is retained;
if the legacy source-epoch control fails, the campaign stops. The original
recorder's failed record is preserved inside any parameter-materialized failure
row, with no numerical rerun or altered error.

## Prediction policy

The equal-region mean objective, regret weights, normalization floors and
research shortlist are inherited unchanged. No individual prediction-error
veto prunes these fixed experiments. Any finalist still needs separately
frozen broader Earth, ocean, resolution, established-region and world checks;
no automatic adoption. There are no local proposals or adaptive extensions.
The two-hour ceiling and per-profile source checks remain mandatory.

The pilot is a low-resolution25step/year screen on reused regions, not new
independent validation or a global optimum. The profile uses liquid saturation,
a prescribed200Kfloor, water integration down to100hPa and fixed dry-layer
fractions. It is not the complete1967radiative-convective model. Reference
gains cannot predict the coupled rainfall, temperature or wind response.
Publish every candidate, numerical failure, regional damage and native metric.

Status: complete; source `bd27f58`, opt-in core `76adf7e`. All70actual runs pass strict numerics; no validation shortlist or adoption.

## Scope of inherited Earth background inputs

The new ocean target does not read the observed925hPa air/humidity profiles
used in the reference comparison. The frozen plan's forcing sentence refers
to that new boundary treatment; it must not be read as a claim that the whole
regional Earth model is independent of observed climate backgrounds.

Existing Earth grids carry a WorldClim-derived latitude/month cloud reference
(from rain, temperature and vapor pressure) and a WorldClim-rain-derived
remote monsoon-descent field. The retained cloud_longwave coefficient0.25
and monsoon_descent0.015443602894513648 can use these prescribed backgrounds.
They are held unchanged and included in actual case identities across all
controls/candidates. Observed SST is loaded for evaluation, while the declared
SST source remains model. These conditional regional tests therefore cannot
establish fully independent global physical forecasting skill. Replacing such
backgrounds is a separate future physical-model question, not an input change
inside this pilot. The original frozen declaration remains untouched.

## Completed coupled results

| Trial | Wind m/s | Ocean mode | Objective | Mean rain/r39 | Mean T/r39 | Worst combined/r39 |
|---|---:|---|---:|---:|---:|---:|
| global01 | 4.5 | legacy | 1.12568 | 1.06867 | 1.03585 | 1.27665 |
| global02 | 4.5 | hydrostatic_uniform | 1.18881 | 1.18705 | 1.07573 | 1.52247 |
| global03 | 4.5 | hydrostatic_half | 1.10958 | 1.07424 | 1.04880 | 1.38032 |
| global04 | 3.5 | legacy | 1.11455 | 1.04473 | 1.04379 | 1.27922 |
| global05 | 3.5 | hydrostatic_uniform | 1.16462 | 1.14064 | 1.08268 | 1.52428 |
| global06 | 3.5 | hydrostatic_half | 1.09941 | 1.04983 | 1.05696 | 1.38304 |

At both winds, half taper improves the penalized objective versus legacy,
but worsens mean rainfall and temperature errors at the same wind. Best
objective global06 (half3.5) is1.09941 versus legacy3.5(global04)1.11455;
mean rainfall1.04983 versus1.04473, and meanT1.05696 versus1.04379.
This is a native-atmospheric diagnostic gain, not a rainfall breakthrough.
Native squared normalized regret falls1.33243→0.83180; that is an objective
component, not a claim that every native error or raw MAE falls37.6%.

Half3.5 increases North India from278to319mm/year (761observed), and reduces
PNW1050to1036mm/year (897observed). Mexico remains the largest regional
combined regression. Hydrostatic uniform worsens the overall objective at
both winds. Native/process improvements therefore do not establish better
coupled precipitation skill or authorize adoption.

The lower legacy wind itself improves mean rain error1.06867→1.04473 versus
the previous4.5setting, while remaining4.5%above r39 on this seven-region
screen. Best mean climate/mean rain selects global04; best objective/native
selects global06. Sensitivity winners include global03/global04/global06.
No candidate reaches the unchanged shortlist. All seven-region results are
reused development evidence, not independent new global forecasting skill.

Independent verification checks the source transition, refreshed thermal and
retained RH references, every actual input/parameter and step certificate,
28historical main controls/four native companions, and the additional seven
matched legacy climate packets/one native companion. All matched packets are
exact. Every scalar objective and fixed trial decision reproduces. Series
counters: **1879actual attempts /1875passes /four preserved historical
failures**. This round adds70passes, no numerical failure. No broader/full/
fine/established/world stage ran; normal atlas climates/headlines stay unchanged.

## Development decision after this round

The user asked for a strategy review because rainfall gains have plateaued.
Pause further broad coefficient sweeps. Next diagnose North India's dry
monsoon, Mexico's seasonal timing/wet bias and PNW's coastal wet bias using
common seasonal water budgets and native wind/humidity constraints. Prioritize
explicit low/upper wind and donor-water exchange evidence before choosing a
new transport/vertical-flow correction. Monthly means cannot recover exact
instantaneous vapor fluxes, and native humidity/rain footprints must be aligned
before inferring precipitation efficiency. Treat each physical hypothesis as
a small falsifiable test with rainfall as a separate primary outcome.
