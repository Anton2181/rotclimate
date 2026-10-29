# Active work — fine-grid results verified; launch committed rainfall benchmark next

User explicitly continues after pushes, repeated latestmessage. No agents. Keep
meaningful frequent commentary and post figures. Latest ETA question answered:
first full fine-grid day ~7minutes; fullbatch45–90min. Batch nowfinished6/6.
All six independent saved water/energy budgetsPASS, maxE<3e-15/W<1.5e-16.
Prototype109starts/101completions/eightretainedfailures. Legacy1934/1929unchanged.
Oldthreefailedinitialstatearraysandacceptedscalarprefixesexactlyreproduce.
Fine21level900/450landP India.619/.632, Mexico1.751/1.715, PNW.427/.427mm/day.
SpatialstepRMS.204/.559/.148mm. Maxactualclosurework432; no newaccuracyclaim.
Bothfiguresposted. Currentstagedpublicationupdatesatlas60studies/149images,
770Windowsbyteassets,1288ZIPfiles. Allbrowser/launcher/682source/bytechecksPASS.
Commit/pushcurrentpublicationnow,thenimmediatelylaunchmonthbenchmarkbelow.

BenchmarkSETUPalreadyCOMMITTEDandPUSHEDf48a02a7. No benchmarkintegrationsyet.
Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python
scripts/run_regional_rainfall_benchmark.py --plan
calibration/regional_rainfall_benchmark_20261029/plan.json --out
output/regional_rainfall_benchmark_20261029 > output/regional_rainfall_benchmark_20261029.log 2>&1`.
It validates currentcapreceipt, snapshots prior109/101/8, runs3legacycontrols
then7prototype45daycaseswith2workers. Sourceprotocolsallcurrentlyhashvalid.
Do notstopafterpublicationpush. Scoring/publisherimplementationstillnext;
metric/calendar/masksarealreadyfrozen. Monitorindividualcase.dailycheckpoints.

## Workspace and authorization

`/workspace/rotclimate`, branch `work`. Python `.venv/bin/python`.
Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` for models/tests. CPU quota2 cores.
Push: `git -c http.version=HTTP/1.1 push origin HEAD:refs/heads/claude/friendly-turing-43ygeu`.
Last pushedf48a02a7: fixed monthly rainfall benchmark setup. Current fine-grid publication ready.
No approval required for this authorized local development/commit/push work.
No AGENTS.md found. Cloud runtime skill read earlier; no secrets accessed.

## Active integration — do not edit its frozen dependencies

Session34000 runs `scripts/convection_cap_pilot.py --plan
calibration/convection_cap_20261029/plan.json --out output/convection_cap_20261029`,
stdout `output/convection_cap_20261029.log`. Six24h integrations:21levels, lowest
old cell split16 ways,3regions each900/450s, fixed1024-sweep work limit.

India900/450 and Mexico900/450 now COMPLETE. PNW900 underway (last live624/864 total
planned calls). Live progress every24 calls at `coupled_timings_live.json`;
root `progress.json` updates per region group. Final `verification.json` and
`coupled_timings.json` appear after all six. Case folders:
`{region}_split16_cap1024/{region}/forced/{900,450}.{json,npz}` plus `initial.npz`.
Every call records target sweeps, convergence and wall time, including failures.

Before active batch:103 prototype starts/95 completions/eight retained numerical
failures (includes one expected repeated rejection). If all6 finish:109/101/8.
Read actual final counts. Legacy1934 attempts/1929 strict passes/four historical
failures/one historical interruption unchanged by these prototype studies.
Never replace failed cases or loosen tolerance after outcomes.

India fine900 land rain.61927mm, fine450 .63161mm; land spatial timestep RMS.20403mm,
skinT RMS.05457K. Initial fine43m reference height versus previous175m/750m cells.
India actual fine budgets <2.5e-15E/<8e-17W. Max observed closure sweeps432 so far.
Small regional mean differences are not local convergence or measured accuracy.

NEXT: publish all six outcomes and independent final/partial energy/water checks,
compare21level900/450 with old9level and6level archives, keep old64-cap failures.
Use `publish_lower_cell_resolution.stats`/`comparison` helpers; new publisher needed
(e.g.publish_convection_cap.py). Include all call timings and sweep distributions.
Update atlas/report, full launcher/browser/portable/source/byte QA, commit/push,
then CONTINUE into already prepared monthly benchmark below.

## Prepared monthly rainfall benchmark — no integrations yet

New code/plans currently being committed as setup milestone:
- `rotclimate/rainfall_validation.py`,4 tests;31 focused tests pass.
- `scripts/rainfall_month_pilot.py`: nine-level/four-part grid, fixed1024 numerical
  cap, fourteen-day prelude + complete July/August month, daily checkpoints.
  Rebuilds wet/dry surface correctly then returns common conversion rain/H once.
  It binds the frozen extended daily driver. Original driver's receipt is preserved
  as `inherited_driver_receipt.json`; final receipt corrects calendar metadata.
- `scripts/r39_rainfall_control.py`: canonical r39, strict checks, exact archived
  float32 monthly reproduction required; retains raw25-step climate for Gregorian
  reaggregation. Custom region definitions come from old archived protocol.
- `scripts/preflight_regional_rainfall.py`: all10 inputs prepare,0 integrations;
  exact r39 identities; identical initial atmosphere across water/timestep scenarios.
- `scripts/run_regional_rainfall_benchmark.py`: validates committed literal global
  plan, waits for current cap batch final receipt, freezes actual prior counters,
  runs3 legacy controls then7 prototype cases with2 separate worker processes.

Literal global plan `calibration/regional_rainfall_benchmark_20261029/plan.json`;
all child plans, reference-footprint NPZs and preflights same directory.
Three legacy r39 cases add3 legacy attempts (strict passes only if reproduced),
zero prototype starts. Seven prototype month cases add7 starts:3regions wet/dry900s,
plus Mexico wet450s as numerical sensitivity (excluded from primary objective).
Do not double-count. Controller records actual case receipts, failures and counters.

Primary: area-weighted MAE mm/day for each region/initialization, mean of six losses;
never average wet/dry predictions before scoring or select best initialization.
Common centered224km footprints over56km r39/reference data, projection-area weights,
>=80% valid reference land area, interior model-land centers. Eligible24/23/12 cells.
Same mask for every profile. Gregorian JulyIndia/PNW and AugustMexico,31 evaluation
physical days after14 prelude (not assumed adequate to erase memory).
No pooled score if any primary case incomplete/budget-invalid or r39 fails reproduction.
Report source initial-state uncertainty, numerical sensitivity, geographic attributions
and liquid-below-freezing diagnostics. Reused development cases, not global validation.

Before launching benchmark ensure all setup is COMMITTED and all source hashes match.
Then `run_regional_rainfall_benchmark.py --plan .../plan.json --out
output/regional_rainfall_benchmark_20261029` with root log same path+.log.
Rainfall scoring/publisher still needs implementation while month jobs run;
metrics, calendar, masks and objective are already explicit in frozen plan.
R39 raw climate needs `scripts.earth_calendar.monthly_stats` (Gregorian), not old
saved equal-month totals. Reference arrays are WorldClim2.1, used for scoring only.
Month predictions are fixed simulated lateral-boundary tests, not independent forecasts.

## Existing scientific results and frozen modules

- `phase_backend.py` binds copied namespaces with identical frozen function bodies.
  Fast liquid root qualified in six Earth controls, maxT difference1.42e-11K,
  rain3.57e-11mm, measured complete-call time reduction15–28%.
- `shared_transport_backend.py`: exact CSC factor reuse within one advance only;
 1152→576 factorizations/day, all six control final fields byte-identical.
 Atomic key/factor installation protects singular-factor retry.374-test stack passed.
- `surface_coupling.py`/`column_forcing.py`: finite water/heat, actual vapor and
 rain enthalpy, conservative grey radiation/neutral exchange, no runoff or ice.
- Fourteen-day wet/dry all6 complete,84 daily ledgers verified. Late land Pwet/dry
 India1.993/.450, Mexico1.599/.388, PNW1.096/.004mm/day; soil memory persists.
- `pressure_remap.py`: exact pressure overlaps; refinement conserves E/W/momentum/KE;
 coarsening exposes lost KE separately.8 new tests,86 focused passed.
- Original fine-grid64-cap pilot:6 four-part runs complete;3 sixteen-part failures
 after19/18/39 steps. All failed states retained, final/partial budgets pass.
- `convection_observer.py` receives copies only;2 tests/22 focused pass, full synthetic
 trajectories and certificates byte-identical even if callback mutates snapshots.
- ReplayIndia next rejected step reproduces exactly. Five STATIC caps64/128 fail,
 256/512/1024 converge at176 with byte-identical targets. These static solves are
 NOT Earth integrations. Replay itself is a new failed attempt already counted.

No new monthly rainfall skill, recalibration or physical-model adoption yet.
Qualified Earth physics r39 remains benchmark; fantasy/world atlas release stillr38
per existing summary, not r39. Normal free/Earth/Whittaker/biome/population fields unchanged.
Unknown terrain, partial380hPa top, liquid-only physics, neutral deep-cell exchange,
fixed lateral reservoirs and absent nonlinear momentum remain limitations.
Initialization memory is not proof of bistability or optimizer local minima.

## Atlas and QA

Current pushed research atlas59 studies/147figures, newest convection-limit.
766 Windows byte assets,1282 portable files. `.bat` launcher browser checks pass.
Raw source freeze:682 hashes from output/divergent_thermal_20261028/protocol.json;
verify unchanged. Also check each current literal protocol's source hashes.
Stage assets before Windows checkout QA. Force-add ignored raw NPZ outputs.
Tools: organize_climate_accuracy.py, check_atlas_checkout.py,
package_fit_atlases.py, check_portable_atlases.py, check_climate_accuracy_browser.py.
Add new report paths to packager explicitly. Newest STUDIES entry first.
Browser: start serve_atlases and checker in same exec Python process; terminate finally.
Compare current HTML/JSON/PNG/NPZ/report bytes against ZIP, retain QA JSON receipts.
Use dark coast with white halo. Avoid claiming numerical speed or conservation is skill.

Historical detailed handoff archived at
reports/handoffs/BEFORE_REGIONAL_RAINFALL_BENCHMARK_20261029.md (also in Git history).
Untracked old progress snapshots and synthetic profile output are retained; not model changes.
