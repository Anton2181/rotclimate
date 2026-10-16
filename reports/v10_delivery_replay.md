# Coastal moisture and condensation diagnostics

15 October 2026. The completed event experiment verifies all twelve cases,
48 cycles and both held-boundary controls. Stronger convergence improves
coastal winter rain, but the predeclared linked-moisture case closes only
8.7% of California's and 4.6% of Iberia's original deficit. Most incoming
vapor still leaves the regional atmosphere. The fantasy atlas is unchanged.

## Next user-run command

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_delivery.py --run
```

**Four single-year diagnostic replays, approximately 5–15 minutes.** There is
a **45-minute invocation cap**, monthly checkpoints and same-command resume.
No new warm-up, parameter search, data download or atlas export is included.
The assistant did not launch a real annual replay.

Replay the saved final year of the original-lift/steady-moisture control and
the lift16/linked-moisture case in each region. Start from each saved
preceding-year state. All physical states, monthly rain/temperature/reference
arrays, physical budgets and original process diagnostics must match the
completed year **exactly**; elapsed wall time is excluded. A mismatch stops
the run and preserves the output for diagnosis.

The prepared identity and twelve independent <=60-second operator checks
are saved in [`output/v10_delivery_preflight/manifest.json`](../output/v10_delivery_preflight/manifest.json).
Code identity is `c251f51d2cb99b8177b4f4eda6df1486749ae7a9b882dce0f71f4d1d2c22f761`.
Default invocation without `--run` or `--preflight` prints a plan only.

## What is collected

- Gross vapor imports/exports, evaporation, recycling, rain, roundoff and
  atmospheric storage change for the full domain, scored land, coast and
  interior. Internal regional transfers can recirculate; they are not new
  external sources or molecular ancestry tags.
- Relative humidity after transport, after prescribed thermal relaxation,
  and immediately before condensation, with actual timestep/cell weights.
- Joint recipient humidity and upward dry-air exchange at every interface,
  retaining both time weights and rain formed in the recipient layer.
- Actual layer rainfall, signed thermal-process changes, gross internal
  upward vapor and independent latent-coupled condensation opportunities
  before/after thermal relaxation.

The detailed joint bins are retained, rather than only threshold summaries.
The summary's illustrative moist/rising threshold is RH >=0.9 and upward
exchange >=0.01 Pa/s. At the fixed 607.95 hPa interface, g times upward dry
mass flux has the opposite sign to omega; the recipient is the 454 hPa
representative layer. On the lower hybrid interfaces this is an exchange
scale, not a directly observed pressure velocity. No threshold is an observed
storm definition or a statistical independence claim.

**Condensation opportunities are diagnostic snapshots on the realized
trajectory.** They are not the precipitation of an alternative operator
order or climate. Summing them can count the same vapor repeatedly if the
physical trajectory does not condense it at that stage. Do not add a removed
opportunity total to actual rain or use it as a predicted attainable gain.
The replay measures a possible mechanism; changed physics would require
its own consistent experiment.

## Interpretation before another physics change

If rising coastal air is already very dry after transport, inspect which
boundaries and layers supply it, the local column moisture convergence and
missing event-linked thermodynamic structure. A fixed whole-domain boundary
influx does not guarantee adequate wet inflow at the coast.

If transport creates condensation opportunities that thermal relaxation
removes, inspect the prescribed heating and splitting/order sensitivity.
This is a hypothesis test, not permission to turn off heating or count every
instantaneous opportunity as additional annual rain.

If humidity and ascent overlap but precipitation remains misplaced, examine
vertical transport, cloud conversion/fallout and precipitation evaporation.
The current immediate-rainout model cannot establish realistic cloud/ice
physics; passive diagnostics do not repair that limitation.

Read the complete joint histograms, monthly masks and local water budgets
together. An instantaneous regional rain source cannot be identified from
a single mean RH, and atmospheric budget differences are not source tags.
Do not start another storm-amplitude, timing or seed sweep from a lower
average error alone. Real submonthly reference data and a separate fantasy
forcing bridge remain necessary before atlas promotion.

## Verification

**100 focused tests pass.** New checks verify gross regional transfers
against flux divergence on disconnected masks, humidity/ascent bins,
stage reconstruction without state mutation, rain weights without a second
dt factor, exact manufactured physical-year replay, binary diagnostic
restart, corrupted evidence, stale preflight and the global time cap.
Previous event, split, thermal, source, weather and Köppen checks remain.

Twelve independent actual-input probes leave every physical output array
unchanged. Maximum reconstruction errors are 1.97e-13°C for stage temperature,
zero for upper-layer water, 9.41e-17 mm for evaporation, 5.79e-17 mm for a
local column water ledger and 1.73e-18 mm for gross boundary flow. These are
short operator checks, not a claim that the four real annual replays have
already reproduced; that is what the user-run command verifies.

Diagnostic output goes to `output/v10_delivery_replay/`. Each checkpoint
stores physical and diagnostic arrays in the same hashed binary file with
an atomic metadata pointer, preventing a restart from combining different
physical and diagnostic months. Completed results include summaries,
immutable source-year identities and exact-reproduction checks.

See the [completed event review](../output/v10_event_review/review.md),
[new Köppen maps](../output/v10_event_review/koppen_comparison.png) and
[coastal/interior monthly rain](../output/v10_event_review/rainfall_comparison.png).
