# Upper-air result: investigate atmospheric paths above terrain

15 October 2026. The user completed both upper-air target cases. All source,
input, configuration and completed-year evidence fingerprints were checked.
Assistant work is saved-field analysis, manufactured dry transport tests, eight
single-step input probes and fast tests. No new regional seasonal simulation,
calibration or atlas export was started.

## Completed result

Both cases settle after four repeated years. Their eight saved cycles took
8.07 minutes. Water, approximate static-energy and signed-temperature ledgers
close. Correcting the upper-air targets improves the thermal comparison, but
does not repair rainfall:

| Region | Monthly rain MAE, before → after | Mean annual rain / reference | Highest-layer rain share | Wettest 5% of land's share of total rain |
|---|---:|---:|---:|---:|
| California | 71.12 → 75.48 mm | 2.14 | 46.4% | 59.6% |
| Iberia | 40.90 → 41.42 mm | 0.78 | 39.4% | 60.1% |

Median annual rain is just 2.8 mm in California and 5.1 mm in Iberia, versus
reference medians of 294 and 384.5 mm. Aggregate regional totals hide large dry
gaps and concentrated peaks. Coverage is unchanged at 54.6% and 65.3% under the
declared non-arid-reference coverage metric. Neither case qualifies; the atlas
stays unchanged.

Saved analysis is in
[`output/v10_upper_air_diagnosis/diagnosis.md`](../output/v10_upper_air_diagnosis/diagnosis.md)
and [`diagnosis.json`](../output/v10_upper_air_diagnosis/diagnosis.json).
Reproduce without seasonal simulation:

```sh
.venv/bin/python scripts/diagnose_v10_upper_air.py --write
```

## What the thermal diagnostics say

In the highest layer, annual scored-land mean horizontal transport contributes
−0.873 K/day in California and −0.313 K/day in Iberia. Mean vertical exchange
contributes +0.086 and +0.026 K/day. Condensation and relaxation provide
opposing heat contributions. These are cumulative signed process contributions
divided by year length, not net temperature changes or causal experiments.
Local vertical cooling can be hidden by a positive regional mean.

Nevertheless, simply suppressing vertical terrain exchange cannot address the
dominant negative mean term in that layer. In the existing geometry, every
representative layer height includes the full ground elevation. Prescribed
horizontal flow along those surfaces can carry upper air uphill even when
coordinate-vertical exchange is zero. This is a question about the prescribed
physical path, not an objection to terrain-following coordinates themselves.

An isolated dry hill test makes the assumption visible. With uniform initial
temperature, no vapor, no rain physics, no relaxation and no vertical exchange,
the current path produces up to 0.083°C upper-layer cooling in one 60-second
step. A hybrid path whose upper pressure surface is level has only roundoff
temperature change. Flat-terrain controls are unchanged in both cases. The test
does not predict a sustained daily cooling rate or a regional rainfall gain,
and the two paths are not equivalent physical velocity fields.

[Schär et al. (2002)](https://iacweb.ethz.ch/doc/publications/2002_ScharEtAl_VertCoord.pdf)
show why terrain-coordinate advection needs consistent horizontal and vertical
terms and discuss terrain signatures decaying with height. Our prototype
prescribes rather than solves that circulation, so the immediate hypothesis is
overly constrained upper-air paths. Separately, hybrid pressure coordinates are
an established design in atmospheric models; [ECMWF's numerical
overview](https://www.ecmwf.int/sites/default/files/elibrary/2004/10021-overview-numerics-ecmwf-atmospheric-forecast-model.pdf)
describes terrain-following lower levels and pressure levels aloft. Neither
source validates this simplified four-layer rainfall model.

## Next user-run command

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_coordinates.py --run
```

Four new cases at 60 km: reference-aligned sigma and hybrid hypotheses in both
regions. Same fixed setting 120 and weather seed 41; no parameter optimization.
Allow approximately **20–40 minutes** from comparable saved timings. A one-hour
invocation cap and monthly checkpoints support resuming with the same command.
The default without `--run` prints the plan and writes nothing.

Both hypotheses use the same all-layer pressure-level temperature reference and
pressure-consistent mean geopotential heights. Fixed surface pressure is inferred
by inverting the annual reference height profile at the model terrain; this is
a derived annual approximation, not an independently observed or prognostic
surface-pressure field. Near sea level it extrapolates the lowest available
reference height interval. The coarse pressure-level product and native/model
terrain mismatch remain limitations, particularly near the ground.

The sigma control has interfaces [1, .9, .75, .6, 0] times local surface
pressure. The hybrid upper interface is fixed at 0.6×101325 Pa = 607.95 hPa;
three lower layers divide the remaining below-interface column in fractions
.25/.375/.375. Both grids coincide at the reference sea-level pressure, and
both contain the same total local dry mass. All input columns have positive
layer masses and representative heights above ground. No altitude, temperature
or humidity value is silently clipped to make a case pass.

All-layer temperature, reference-aligned pressure and geopotential are common
changes relative to the completed upper-only experiment. The new sigma control
is necessary to distinguish those changes from the hybrid path hypothesis.
Within the new pair, the pressure geometry, sampled representative air and the
physical velocities implied by identical face fluxes differ. It is explicitly
**not a coordinate-invariance test** or a solved momentum model.

Wind consistency must accompany any apparent rain improvement. For example,
the hybrid California no-storm speeds reach 54–56 m/s in its thin middle layers,
versus about 13 m/s in the new sigma control. The hybrid upper speed is lower.
These are diagnostic model speeds, not claims of realistic local wind. The
runner records maxima, p95 speeds and departure from prescribed offshore
vectors in its manifest and report. Rain/thermal eligibility alone cannot
validate this circulation or authorize an atlas export.

Results will be saved in `output/v10_coordinate_check/`: frozen manifest,
explicit coordinate/reference input arrays with hashes, monthly resume points,
yearly fields, budgets, rain by layer, signed thermal ledgers, state and report.
Completed cases resume only with matching source/input/evidence fingerprints;
an unsettled or failed case stops for diagnosis. Historical evidence remains
unchanged.

## Decision after the comparison

If the hybrid path removes most excessive high-level mountain rain, develop a
more realistic mass-consistent circulation and vertical discretization before
calibration. A better score accompanied by excessive middle-layer winds is a
mechanism lead, not a validated model. If high-level peaks persist, inspect
reference humidity, pressure quadrature and rain-out efficiency using the saved
ledgers. If peaks diminish while coastal dry gaps remain, examine frontal
moisture delivery next. Do not add a long cloud fall time merely to spread rain
across the map.

The same concern can affect a future fantasy atmosphere, where mountains should
shape low-level lifting and rain shadows without a prescribed full-height
terrain imprint in every upper-air path. This Earth comparison still uses
reference-informed temperature/winds and cannot directly supply a fantasy atlas.
The user's Mediterranean and dry-zone protections remain unchanged.

## Verification before launch

43 focused tests pass. New checks cover matching sea-level grids, positive and
conserved column mass, ordered pressures, rejection of intersecting ground,
hydrostatic reference inversion, dry-ridge/flat controls, equivalence to the
frozen step when geometry/targets match, hybrid water/static-energy/temperature
closure, CFL enforcement, exact checkpoint resume, array fingerprints, bounded
four-case resume and read-only defaults.

Eight independent January/July single-step checks cover all four actual input
cases. Maximum residuals are 4.29e-16 mm water, 1.61e-8 J/m² static energy and
1.93e-13°C signed temperature accounting. Prepared protocol and results are
saved in
[`coordinate_preflight.json`](../output/v10_upper_air_diagnosis/coordinate_preflight.json).
No regional seasonal case was launched. All existing frozen source identities
still match their completed evidence.
