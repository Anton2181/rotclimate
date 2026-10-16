# Overnight result and next controlled check

15 October 2026. The user completed the overnight run. Assistant work is saved
evidence verification, pressure-level reference analysis, scalar clock probes,
four frozen-state single-step checks and manufactured tests. No regional
seasonal integration, calibration or atlas export was started by the assistant.

## Result

The run finished its useful queue after **6 hours 9 minutes**, within the
nine-hour allowance. It completed 215 cases comprising 944 repeated-forcing
years. Three additional cases stopped. All 215 completed cases settle, but none
meets the original eligibility rules. Therefore the declared protocol skipped
30/15 km refinement. The atlas remains unchanged.

The saved-state review and evidence hashes are in
[`output/v10_overnight_review/review.md`](../output/v10_overnight_review/review.md)
and [`review.json`](../output/v10_overnight_review/review.json).
Reproduce without simulation using:

```sh
.venv/bin/python scripts/review_v10_overnight.py --write
```

The eight shortlisted settings received 60 km checks in both regions on three
artificial weather seeds; 47 of 48 completed. California still receives roughly
twice the reference rain on average, with insufficient coverage and excessive
peaks. Iberia's regional totals are closer but hide dry gaps and misplaced rain.
All 47 have greater monthly rainfall MAE than predicting zero rainfall. That
is an information-free error baseline, not an acceptable model, but it shows
that a lower search score alone is not evidence of useful spatial rainfall skill.

Water and declared approximate-static-energy budgets close: maximum annual
residuals among completed cases are about 6.5e-12 mm and 3.7e-5 J/m². Numerical
conservation and repeated-year settling are not the limiting acceptance tests.

## A correction to the thermal diagnosis

Every original case fails the upper-temperature departure screen. However,
those departures measure distance from imposed targets made by adding local
surface-temperature anomalies to an offshore vertical profile. They are not
errors against local pressure-level air temperature.

Sampling the existing coarse NOAA pressure-level data at the actual local model
pressures gives a different picture. For the reference-informed shallow control
at 120 km, upper p95 absolute error changes from 17.63 to 8.56°C in California
and 13.61 to 5.45°C in Iberia. All 47 shortlisted 60 km cases have upper errors
under 10°C in that separate comparison. Lower-layer errors remain, and these
coarse reference estimates have terrain and climatological-period limitations.

This does **not** change historical acceptance or make the rainfall pass.
It establishes that the spatial thermal target and its guard need testing
together. Do not tighten relaxation toward those old targets merely to make
the model pass them. The signed cooling relative to an imposed target identified
in the earlier research plan cannot by itself establish an equally large error
against actual free-air climatology.

## The three stops were scheduling defects

Scalar-clock probes reproduce every stop without evolving water or energy.
The old integrator rejects any timestep below .01 seconds, including a legal
millisecond remainder before a three-hour forcing boundary. Actual CFL limits
at these stops are 1,350–3,600 seconds. All three corrected scalar clocks finish
their years within the existing step-count cap. Their physical cases have not
been rerun and remain recorded as failed in the frozen batch.

The new isolated helper `experiments/v10_time.py` permits positive boundary
fragments while enforcing forward progress and the actual CFL bound. It never
discards the remainder or snaps a climate state forward without integration.
The original model/runner remain unchanged.

## Next user-run command: two cases, no sweep

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_upper_air.py --run
```

Allow approximately **10–20 minutes**, based on comparable saved runs; the
extra diagnostics can increase cost. A one-hour cap and monthly checkpoints
permit resuming with the same command if needed.

Reuse completed setting 120, seed 41, 60 km baselines in both regions. Run two
new cases, changing only the **upper two temperature targets** to spatial
pressure-level air from the already cached reference. Lower targets, geometry,
dry mass, circulation, humidity multiplier and storm events remain fixed.
Upper boundary humidity saturation caps respond consistently to the changed
temperature. Initialization matches the old protocol; repeat three to six
years to test settling rather than warm-starting from a fitted final state.

New instrumentation records rain by layer and monthly signed temperature
changes from horizontal transport, vertical exchange, thermal relaxation,
evaporation and condensation. The contributions are cumulative and can be
large and cancelling; their sum is checked against the actual temperature
change. Dividing by month length gives mean K/day contributions. These are
process accounting, not independent causal effects of deleting a process.

Results go to `output/v10_upper_air_check/`, with frozen source/input/baseline
fingerprints, yearly fields, monthly resume points, process ledgers and a
comparison report. Default without `--run` prints the read-only plan. No new
data download, parameter search, background automation or atlas update occurs.
Temperature remains observation-informed forcing; rainfall observations remain
scoring-only. This is a mechanism check, not a newly untouched validation set.

If corrected targets materially improve rain placement, test that mechanism
with broader transfer evidence before fantasy integration. If rainfall remains
poor, the new ledgers distinguish persistent horizontal/orographic cooling from
vertical exchange and relaxation, guiding a cloud/fallout or circulation test.
Changing the old acceptance thresholds is not the proposed fix.

## Verification

Thirty focused tests pass, covering the frozen overnight machinery and the new
target/clock/diagnostic experiment. New tests establish equivalence to the old
step when targets are unchanged, water/static-energy and signed-temperature
closure, upper-only target replacement, checkpoint resume, legal clock fragments,
two-case resume/provenance protection and read-only defaults.

Four independent single-step probes use actual saved baseline states and
January/July forcing in both regions. Maximum residuals are 2.53e-16 mm water,
5.48e-9 J/m² static energy and 1.59e-13°C temperature accounting. Their protocol
and source fingerprint are saved in
[`upper_air_preflight.json`](../output/v10_overnight_review/upper_air_preflight.json).
No new regional seasonal case was launched. The frozen overnight source hash
still matches its completed manifest.
