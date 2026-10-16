# Mechanism test: episodic lifting and moisture timing

## Completed result — 15 October 2026

All twelve cases settle in four cycles (48 cycles; 31.03 saved integration
minutes). Both discretization controls pass with only 0.0017 / 0.0025 mm
annual-cell-change p95. All input/config/evidence hashes, recomputed summaries,
annual physical/thermal ledgers and actual monthly incoming-water controls
verify. Maximum monthly dose error is 1.77e-11 mm.

Coastal winter rain improves 26.0 → 70.2 mm in California (534.8 observed),
16.3 → 35.5 mm in Iberia (439.2 observed), comparing the original steady
control with the fixed lift16/linked-moisture case. Only 8.7% / 4.6% of the
original coastal deficit is closed; 91.3% / 98.5% of reference Mediterranean
cells remain arid. No atlas publication.

Lifting alone adds 40.95 / 18.20 mm coastal winter rain; linked rather than
shifted moisture at lift16 adds just 1.16 / 1.44 mm. The timing sign is not
uniformly positive at lift1. About 79.5% / 84.1% of added land rain forms in
the middle three layers. This supports a lifting mechanism without selecting
an observed storm strength or validating a new climate.

Boundary input is fixed, but ocean evaporation and recycling rise. The
full-domain atmospheric rain increase is +29.46 / +17.40 mm, with about
98.2% / 97.6% of total vapor input still exported. Budget differences are
not source fractions of the extra coastal rain.

See the [complete verified review](../output/v10_event_review/review.md),
[updated Köppen comparison](../output/v10_event_review/koppen_comparison.png)
and [next small diagnostic replay](v10_delivery_replay.md). The next command
replays four single saved years without warm-up, with exact physical
reproduction required, to distinguish dry ascent, local delivery and thermal
relaxation before another physics change. The original protocol follows.

## Original prepared handoff

15 October 2026. **The separate implementation and short preflight are complete.**
The user runs every seasonal simulation or calibration. Frozen parent source
files, completed outputs, acceptance evidence and the fantasy atlas are unchanged.

## Run the prepared experiment

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run
```

Twelve fixed cases, estimated **45–75 minutes**, with a **two-hour invocation
cap**, monthly restart files and same-command resume. Cached data only; no
NOAA access, parameter search or atlas export. The default without `--run`
prints a plan without preparing or integrating anything.

The first two cases check the new held-boundary-water discretization against
the completed controls. If either is unsettled or materially different, the
batch saves it and stops **before** the mechanism cases. The remaining ten
cases separate lifting strength and moisture timing in both regions.

The six settings per region are the cross product of:

- Original or strengthened **convergence-only fluctuation**; the full monthly
  mean dry circulation, storm rotation and seed-41 catalogue are unchanged.
- Steady moisture, event-linked moisture at each boundary cell, or a half-month
  shift of the same nominal local pulses.

Every case receives the same **gross incoming vapor per month**. The engine
checks the integrated amount at every month boundary. Ocean evaporation,
land recycling, humidity means/variances, heat transport, export and diagnosed
flow work can still change. “Aligned” refers to the boundary storm-convergence
signal; advection can delay its effect at the coast. This is not an observed
complete warm/cold front or a pure isolation of covariance.

The strengthened setting uses **16 times the tiny original convergence
fluctuation**, not 16 times all winds or the storm count. A forcing-only
design audit tested fixed doses 1/4/16/32/64 before any new seasonal result.
The declared design requirement was at least 10% more coastal winter
positive-only ascent in both regions. Sixteen is the smallest listed dose
meeting it: **+12.2% California / +16.2% Iberia**. Four changes this measure by
only 1.0% / 1.5%, so the initial fourfold preflight was archived rather than
spending a climate run on it. This is experimental contrast selection, not
calibration to rainfall or observed storm statistics. The geographic coastal
mask includes land within 150 km, including the model rim; rainfall evaluation
uses the original stricter shared mask.

Prepared tables and checks are in
[`output/v10_event_preflight_lift16/`](../output/v10_event_preflight_lift16/review.md).
The weaker preflight, its
[source snapshot identity](../output/v10_event_preflight/source_snapshot/identity.json)
and [forcing-only dose audit](../output/v10_event_preflight/lifting_power_audit.json)
are preserved separately. Source/input/calendar/evidence hashes prevent
silently changing an active run.

## Implementation and verification

`experiments/v10_event_forcing.py` keeps a separate static copy of the
pressure-based physical step, changing its interface to accept explicit
prepared boundary humidity. It retains conservative water transport,
dry-theta transport, instantaneous liquid-water rainout, latent heating,
soil/evaporation, prescribed thermal relaxation and explicit flow-work
accounting. No momentum/radiation/cloud-ice model is newly claimed.

At each three-hour forcing tick, derive the convergence-only storm flow by
subtracting the same circulation with zero storm convergence. Compute its
exact per-face monthly mean. Add 15 times its fluctuation about that mean
to the original full flow. Column continuity remains balanced at every tick.

At each boundary cell, the positive convergence-only ascent at 607.95 hPa
sets a bounded 0.6–1.4 nominal moisture pulse with a monthly mean of one.
The timing control shifts that local sequence by half the month's ticks.
Use the original profile at the tick midpoint, with a saturation cap safe
over the whole interval, then solve a capped monotone normalization for the
same total monthly gross incoming vapor as the original-amplitude steady
table. Actual capped/normalized humidity distributions are saved and not
claimed identical. No observed rainfall enters table construction.

Two tiny manufactured checks pass: an unsaturated constant-temperature
moisture front translates exactly without rain; saturated pressure transfer
matches an independent latent-heating/saturation root to 2.1e-14 mm.
These do not validate a resolved thermal front or cloud fallout.

**90 focused tests pass**, including forcing invariants, local pulse shifts,
cap feasibility, exact physical-step regression, dose checks, serialization,
restart, stale-input rejection, completed-case corruption, the initial-control
stop and the global time cap. The original split/source/thermal/weather/map
checks remain included. No real seasonal simulation was started by the assistant.

The regional preflight constructs the full forcing calendars without state
integration. It also runs **48 independent <=60-second probes**, including
36 new forcing/step checks and 12 exact original-step regressions. Water,
energy, theta, thermal accounting and gross incoming coefficients are checked.
Full-year mean dry circulation and monthly gross dose agree to rounding
precision; exact numerical bounds are recorded in the prepared manifest.

The initial held-boundary controls have predeclared tolerances: monthly rain
change p95 <=1 mm, annual p95 <=5 mm, MAE change <=0.1 mm, annual mean and
coastal winter changes <=max(1 mm, 2% of the old control). These guard a
discretization change; they are not Earth climate accuracy criteria.

Results go to `output/v10_event_forcing/`, including immutable protocol,
case identities, annual/monthly fields, gross-input controls, thermal/layer
and flow-work diagnostics, coast/interior seasonal responses and fixed-surface
temperature Köppen statistics. Unsettled six-cycle mechanism cases remain
labelled; physical/provenance/dose failures stop. No automated winner or
fantasy publication is included.

The original scientific design and outstanding limitations follow.

## What the completed experiments establish

The five-layer test improves a profile integral and some rainfall errors,
without restoring coastal winter wetting. The California uniform MAE gain
comes entirely from reducing errors where the original case was already
too wet; the dry-cell contribution worsens. Mediterranean-to-arid errors
increase. Upper humidity assumptions dominate the additional highest-layer
rain; fixed column concentration is not fixed gross moisture influx.

The [forcing-only audit](../output/v10_split_review/storm_ascent.md) samples
the actual three-hour forcing clock. At the fixed 607.95 hPa interface,
coastal November–April upward-positive signed mass exchange is:

| Engine background | California | Iberia |
|---|---:|---:|
| Uniform monthly flow, no storms | +0.07853 Pa/s | +0.01694 Pa/s |
| Spatial monthly flow, no storms | -0.03683 Pa/s | -0.03257 Pa/s |
| Same storm perturbation, signed increment | +0.00045 Pa/s | +0.00109 Pa/s |

Negative means descent. Storms reverse spatial-background descent in only
2.08% / 1.94% of coastal cell/tick pairs. Equal storm perturbations can have
very different effects on positive-only ascent when one background is
descending. These are engine-implied motions, not observed omega or a
calibration target. Projection, terrain and coarse vertical winds remain
part of this circulation hypothesis.

The synthetic storms explicitly alter circulation, without associated
incoming moisture/temperature anomalies. Internally transported model
humidity can still develop covariance. The independent
[ERA5 Mediterranean moisture-budget study](https://wcd.copernicus.org/articles/6/245/2025/)
supports testing submonthly eddy transport against the monthly mean; it
does not supply a California forcing amplitude or validate this model.

## First implementation should answer a mechanism question

Can brief coherent lifting and moist inflow produce coastal winter rain
**at controlled actual boundary import**, while maintaining a dry interior?
Do not turn the spatial monthly mean into a permanent ascending/wet flow.
Do not start another storm-seed search or assume larger convergence is
observationally justified.

Begin with manufactured unsaturated/saturated front and pressure-transfer
checks. Separate physical rain from numerical mixing, and show that the
existing pressure-based dry law and water/thermal balances survive. These
are tiny tests, not regional integrations. Resolve failures before preparing
the user-run batch.

Then prepare a small paired sensitivity experiment, using both regions and
the same seed-41 event catalogue. The frozen five-layer dry-upper control
can provide a common structural anchor; it remains a humidity assumption,
not an observed atmosphere. If a mechanism succeeds, repeat it with the
retained-RH upper case before interpretation.

Two factors should be separate:

1. **Intermittent lifting.** Compare the existing event anomaly with a fixed
   larger anomaly about its monthly mean. Subtract the exact discrete
   monthly anomaly mean on every dry-air face. Preserve each month's mean
   circulation, stationary column continuity and the unchanged event count.
   A declared amplitude such as four times the fluctuation is a mechanism
   dose, not a fitted or observed storm strength. Diagnose altered velocity
   variance, implied ascent and prescribed-flow work explicitly.
2. **Moisture timing.** Compare a predeclared bounded event-linked incoming
   moisture pattern with a within-month shifted timing control. Separate
   timing from mean water dose. Do not yet claim that this moisture-only
   sensitivity represents a complete front with observed warm/cold sectors.

Both factors require precomputed forcing and a separate fingerprinted engine
or forcing interface. Do not monkey-patch a completed model or alter its
evidence to add diagnostics. Reproduce an unchanged anchor exactly before
new seasonal cases. No observed rainfall may enter forcing construction.

## The supply control must be real

Match **gross incoming vapor flux integrated over each month and all open
faces**, using incoming face dry mass flux times the applied mixing ratio.
The previous mass-weighted column match is insufficient. Apply local
saturation caps before checking the match; infeasible matches must stop
before a seasonal simulation. Save the forcing table and its hash.

Do not claim that concentration means, humidity variance, its full
distribution and gross influx are all fixed unless preflight verifies
each one. A timing shift plus saturation caps or a scalar normalization
can change the other quantities. If a pure timing control cannot meet
the declared constraints, revise the design and its interpretation first.

Matching boundary import also does not fix ocean evaporation, land recycling,
export or heat transport. Save those responses and atmospheric storage
separately; use source tags only if their generalized implementation has
passed conservative-transport checks. The imposed circulation work remains
an exchange with unsolved momentum, not a new closed-energy GCM.

## Decisions before another calibration

Report the full coastal/interior winter/summer response, rain formation by
layer, gross input/export, temperature departures, numerical settling and
same-surface-temperature Köppen response. A lower MAE that increases coastal
drought is not an eligible Mediterranean fix. Do not pool settling cycles,
cells or the two regions as independent weather replicates.

If lifting alone helps, investigate ascent structure and event statistics.
If aligned moisture helps against the shifted control at matched gross
import, investigate covariance and boundary sectors. If neither improves
coastal rain, inspect finite cloud conversion/fallout, precipitation
evaporation, vertical transport and dynamical forcing before any larger
parameter search. Success in this synthetic test is only mechanism evidence.

The six-hourly reference audit remains paused after NOAA HTTP 429. It cannot
be replaced by cached monthly means, daily means called six-hourly weather,
or unverified large downloads. Observed event statistics and mass/pressure
consistency are necessary before proposing a realistic forcing prescription.
Fantasy transfer then needs its own geography/circulation bridge and the
user's existing Mediterranean, cold-dry and hot-dry protections.
