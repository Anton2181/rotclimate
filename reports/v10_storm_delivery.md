# Coordinate result and a controlled wind/storm-delivery test

15 October 2026. All four user-run coordinate cases are complete and their
source, configuration, input and annual evidence hashes match. Sixteen saved
cycles took 10.00 minutes; each case settles in four cycles. None passes the
declared rainfall screens. The atlas is unchanged.

## What the coordinate comparison found

| Region / path | Monthly rain MAE, mm | Annual rain, mm | Rain / reference | Wet-reference coverage | Highest-layer rain, mm/year |
|---|---:|---:|---:|---:|---:|
| California sigma | 64.26 | 683.96 | 1.70 | 50.9% | 299.75 |
| California hybrid | 30.26 | 171.67 | 0.43 | 52.0% | 0.00 |
| Iberia sigma | 37.71 | 195.40 | 0.46 | 59.0% | 77.31 |
| Iberia hybrid | 32.84 | 90.79 | 0.21 | 58.6% | 0.00 |

Reference mean annual rain is 401.80 mm in California and 424.17 mm in Iberia.
The hybrid path removes almost all rain in the upper two layers. Its lower MAE
is useful evidence about the mountain-rain mechanism, but it also leaves both
regions far too dry. Median hybrid annual rain is only 1.38 and 0.98 mm; regional
means hide very large dry gaps. Coverage here means the fraction of land with
reference rain >=50 mm/year receiving at least 1 mm/year, a deliberately weak
minimum-wetting screen rather than a measure of good local rainfall.

The coordinate experiment changed physical paths and implied velocities; it
was not a coordinate-invariance comparison. Both variants also share the
all-layer local pressure-temperature targets and revised reference heights.
Do not attribute every change relative to the earlier upper-air-only experiment
to the hybrid grid alone.

Budgets remain sound: the largest saved annual water residual is about
5.3e-12 mm and the static-energy residual about 2.6e-5 J/m². The dominant
problem is rainfall distribution and forcing, rather than failed convergence
or leakage in these ledgers. Saved-only analysis is in
[diagnosis.md](../output/v10_coordinate_diagnosis/diagnosis.md) and
[diagnosis.json](../output/v10_coordinate_diagnosis/diagnosis.json). Reproduce:

```sh
.venv/bin/python scripts/diagnose_v10_coordinates.py --write
```

## Why change the flux construction before tuning storms

The old forcing prescribes layer air fluxes using reference sea-level layer
masses. Retaining those fluxes in thinner hybrid layers increases their implied
wind speeds. The new experimental module interprets the forcing as nominal
face velocities, multiplies by actual face dry mass, and removes column mass
divergence with a weighted potential projection. The correction applies the
same velocity increment to each layer at a face, preserving their face shear.
Diagnosed exchange between layers then closes each layer's mass balance.

With total face mass M, raw flux F and potential phi, the corrected flux is
F_k - m_k grad(phi), solving -div(M grad(phi)) = -div(sum(F_k)). Exterior
potential is zero on the open boundary, half a cell from the adjacent center.
This permits boundary velocity adjustment. Water and energy entering or leaving
those boundaries remain explicit in their ledgers. Dry masses and geometry
stay fixed. This is a prescribed-circulation approximation with stationary mass,
not a prognostic momentum, surface-pressure or radiation system.

There is also a diagnostic correction to the earlier wind discussion. The
reported 54–56 m/s peaks used averaged face flux divided by **cell** mass. That
can differ substantially from averaging face velocities F_face/m_face near
steep mass gradients. With the same face-velocity convention on both flows:

| Region | Old hybrid middle-layer maximum | New projected maximum | Maximum background projection adjustment |
|---|---:|---:|---:|
| California | 27.90 m/s | 9.71 m/s | 0.89 m/s |
| Iberia | 13.37 m/s | 6.44 m/s | 0.72 m/s |

These are maxima across twelve no-storm monthly snapshots and scored land.
The manifest retains both diagnostic conventions. Do not describe the numerical
change as a measured real-world wind improvement. Against local coarse
pressure-level reference winds, new layerwise p95 vector errors remain
6.23–9.24 m/s in California and 5.51–10.64 m/s in Iberia. Applying a monthly
offshore mean profile throughout a region is still a substantial limitation.
Storm-time projection adjustments are recorded separately during the new runs.

## Next user-run batch

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_storm_delivery.py --run
```

Ten fixed 60 km cases, five per region. The two completed hybrid baselines are
read from saved evidence. All new cases use the projected flow; the first two
anchor cases change only flux construction and projection relative to those
baselines. Hybrid geometry, thermodynamic/rain closure, temperature targets,
terrain drag and storm strength/radius remain fixed.

| Control | Humidity multiplier | Nominal storms per 30 days | Purpose |
|---|---:|---:|---|
| anchor | 0.8 | 1 | Isolate the flux/projection change against the completed hybrid baseline |
| mean_only | 1.0 | 0 | Reference humidity with no transient storms |
| rare_storms | 1.0 | 1 | Separate humidity from the projected anchor; compare storms against mean_only |
| winter_storms | 1.0 | 4 | Test more winter-biased moisture delivery |
| frequent_storms | 1.0 | 8 | Diagnose whether storm count can remove dry gaps without excessive peaks |

The seasonal rate envelope is unchanged, with events possible in summer as
well as winter. Seed 41 gives 0/11/44/97 events in the four storm-count controls
in each region. The rate-one catalogue exactly matches the old experiment.
Rates four/eight add events from a separate rate-seven master catalogue, with
fixed uniform marks selecting a nested subset. They retain correct marginal
Poisson rates and common events across the controls. Humidity changes do not
change the weather. This avoids confusing changed storm locations with a
humidity or frequency response.

Expect roughly **20–45 minutes**, extrapolating from the completed sixteen-cycle
run; active storms and the extra flow solve may change the timing. There is a
**90-minute invocation cap**, three to six repeated cycles per case, monthly
checkpoints, and resume with the same command. An unsettled or numerical failure
stops for diagnosis. The command without `--run` prints the plan and writes
nothing. No optimization, new download or atlas publication is included.

Results go in `output/v10_storm_delivery/`: immutable manifest of inputs, source,
runtime, wind audit and weather hashes; monthly/annual checkpoints; completed
field hashes; layer rainfall and signed thermal ledgers; maximum projection
adjustments, budgets, summary and run log. Temperature is still informed by
observations, so even a rainfall success cannot directly update the fantasy map.

## Decisions after the batch

1. Compare the two anchors against the completed hybrid cases before interpreting
   storm controls. Record whether changing air residence times and vertical
   exchange alters rainfall and thermal departures.
2. Compare rare_storms with anchor for humidity, and zero/one/four/eight storms
   at reference humidity for transient delivery. Assess wet gaps, spatial
   concentration and seasonality as well as regional means and monthly MAE.
3. A provisional pass requires the existing settling, budget and rain/thermal
   screens: lower/upper temperature departure <=5/10°C, rain/reference
   0.5–1.75, coverage >=80%, p99 rain <=4 times reference. It is development
   evidence. Also require useful monthly skill against zero rain and inspect
   geography before selecting another expensive run. No eligibility rule is
   retroactively changed in the old evidence.
4. If adequate rain appears only by making peaks worse, or most land remains
   dry even with frequent storms, stop frequency tuning. Diagnose spatial mean
   circulation and correlated frontal heat/moisture delivery next. The large
   residual local wind errors make that a stronger avenue than another broad
   parameter sweep. Source-water tracers can separate boundary delivery from
   local evaporation if attribution remains unclear.
5. If both regions improve coherently, check independent weather seeds and
   grid sensitivity before a larger search. Then construct observation-free
   planetary forcing for the fantasy model and reapply the user's Mediterranean,
   cold-dry and hot-dry protections across the declared worlds. The current
   validated V9 atlas remains the display source until that bridge is tested.

## Verification before handoff

55 focused tests pass, covering projection recovery with open half-cell
boundaries, idempotence/shear, exact constant-tracer transport, positivity,
water/static-energy/temperature closure, flat sea-level agreement with frozen
forcing, paired weather/catalogue rates, checkpoint resume and read-only defaults.
The report change also passes the two runner tests independently.

Twenty-eight independent actual-input single-step probes cover January, July
and an active strongest-storm center when events exist. They do not advance a
season or feed one probe into another. Maximum residuals are 6.98e-16 mm water,
1.29e-8 J/m² energy, 2.03e-13°C signed temperature accounting and 1.45e-15
kg/m²/s column mass divergence. Protocol, wind audit and probes are saved in
[storm_preflight.json](../output/v10_coordinate_diagnosis/storm_preflight.json).
The assistant started no regional seasonal run or calibration. Original
production, overnight, upper-air and coordinate source fingerprints are retained.
