# Six fixed Earth-input pressure-column smoke integrations

The coupled pressure/convection prototype completed all six declared runs
using archived simulated states for India, Mexico and the Pacific Northwest.
This tests state transfer and numerical admissibility on Earth geography.
It is not a recalibration, weather forecast or monthly rainfall skill test.

The outcome identifies a setup blocker: 99.5–100% of new rain falls in the
outermost grid cells, and temperature adjustments somewhere in the partial
column reach 7.5–12.9 K over six hours. The closed, initially unbalanced setup
is unsuitable for rainfall fitting despite its excellent conservation budgets.

## Declaration and inputs

The literal plan and transfer code were committed before integration in
`01c7e8c`. The source archive hashes, physics code, days, grid, timescale and
both timesteps are frozen in `calibration/pressure_input_pilot_20261029/plan.json`.
No replacement regions or parameter changes followed the outcomes.

Inputs come from the earlier experimental hydro-control archives, not an
independent observational analysis. The selected scored model days are 197.1
for India and Pacific Northwest and 226.3 for Mexico. The exact scored-index
mapping selects records 21/21/23, avoiding a same-day spinup occurrence.
Only simulated temperature and two water reservoirs, calendar and geographic
geometry are read. Observed rain/temperature and archived/reference winds or
humidity are not input fields.

Every fourth original 56 km cell is point-sampled onto a 224 km grid. This is
not conservative horizontal aggregation or a native observation footprint.
The 6-cell pressure grid spans 101325–38000 Pa, with its first cell containing
25% of reference dry mass and the remaining five the upper 75%.

## Declared thermodynamic transfer

Terrain is flattened because the new prototype has fixed pressure bounds.
One fixed 6 K/km lapse reduces the archived simulated near-surface temperature
to a sea-level reference; the same lapse defines the hydrostatic vertical
temperature profile, with an explicit 200 K isothermal cap. Unsupported states
are rejected rather than clipped. This is a counterfactual flattened regional
input, not a claim to simulate terrain precipitation or the original surface
temperature at all elevations.

Lower and upper archived vapor integrals are preserved exactly. Saturation-
capacity weights distribute water within each corresponding pressure
reservoir, equivalent to uniform relative humidity within that reservoir.
This reconstructs unresolved vertical structure; it does not recover a measured
humidity profile. The original archive does not supply a thermodynamic energy
state directly comparable with this new pressure coordinate. The energy
budget therefore starts at the newly declared raw temperature/water profile.

One initial enthalpy phase adjustment makes that profile admissible. Its rain
and actual liquid enthalpy are returned separately. They are excluded from
the subsequently accumulated run rain. Both the conversion budget and the
full raw-initial-to-final gas/kinetic/rain budget are independently verified.

## Six-hour integrations and results

All cases use Earth latitude-dependent Coriolis, five-day momentum drag and
one declared one-hour convection relaxation. They start at rest, unbalanced
with the regional temperature gradients. Horizontal walls and pressure lids
are closed. There is no sustained radiation, evaporation, lateral moisture
inflow or surface forcing. Each region runs six hours at 1800 and 900 seconds,
for 108 total timesteps. No observed climate scores are computed.

| Region | Initial conversion rain mm | New six-hour rain mm | Peak level wind m/s | Rain in outer cells |
| --- | ---: | ---: | ---: | ---: |
| India | 0.002690 | 0.000414 | 21.56 | 100.0% |
| Mexico | 0.005909 | 0.000474 | 19.97 | 100.0% |
| Pacific Northwest | 0.028486 | 0.008408 | 29.65 | 99.5% |

These are unweighted means over each sampled model grid, from the 900-second
cases. Initial conversion is not added to run rain. All new rain is tiny in
the regional mean; local values and boundary concentration are in the raw
fields and geographic maps.

The 1800-versus-900-second temperature RMS differences are 0.055/0.044/0.063 K
for India/Mexico/Pacific Northwest. Rain-field RMS differences are
0.00129/0.00223/0.00327 mm. Relative mean-rain differences are 27.0/23.8/2.2%:
the large tropical percentages involve absolute mean differences around
0.0001 mm. Two timesteps do not establish convergence of climate rainfall.

Actual whole-run energy and water errors remain below 6.3e-16 relative,
including initial conversion where appropriate. No solver or physical-domain
failure occurred. This is a conservation/admissibility result, not acceptance
of the boundary-dominated precipitation or startup temperature response.

## Counts, tests and next experiment

There are six new Earth-initialized smoke integrations. They are recorded
separately from the legacy 1934 benchmark attempts / 1929 strict passes / four
historical failures / one interruption. No new legacy strict passes, calibration
attempts or independent validation results are claimed. Earthr39 and normal
world/biome/population datasets remain unchanged.

Seven new tests verify scored-calendar selection instead of spinup, exact
lower/upper water transfer, actual conversion energy and rain, the dry
hydrostatic limit, one fixed elevation lapse, empty reservoirs and invalid
inputs. The full focused suite passes 300 tests. Publication independently
reconstructs archived input selection, declared profiles, vapor transfer,
conversion, actual final gas/face-kinetic/rain budgets, saturation and timestep
differences. Input/final fields and startup rain remain available separately.

The next useful comparison must address regional boundary conditions and
initial dynamical balance before fitting rainfall parameters. Sustained thermal
and moisture forcing is also needed for a climate integration. The strong
edge-rain signature should remain an explicit diagnostic; simply adding a
rain coefficient or stronger damping would not establish a correct regional
water/energy supply. A longer or finer run alone does not repair missing
boundary physics.

Inherited dry/dilute, liquid-only, partial-pressure-column and convection
assumptions remain. Terrain, water loading/gas-volume/potential, ice, nonlinear
momentum advection, barotropic dynamics and prognostic surface pressure are
not represented. These limitations and the initial reconstruction constrain
what an eventual regional forcing experiment can demonstrate. No measured
rainfall-accuracy improvement is claimed here.
