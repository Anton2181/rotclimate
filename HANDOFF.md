# Active work — monthly workers recovered; water-supply atlas milestone ready

41f77a71 pushed exact checkpoint recovery; controller RUNNING session83618.
India wet/dry around day37/38 of45 as of18:03UTC; two workers, no duplicate launch.
Controller log output/regional_rainfall_recovery_20261029.log. After India ends it
runs every queued Mexico/PNW case from the original frozen plan; legacy controls
are reused, not rerun. Recovery segments2/replay segments3 are separately recorded.
Zero new Earth initializations by replay/recovery. Original prefix daily fields
retained; per-step prefix histories unavailable. Both branches next-day states
reproduce all10 fields byte exactly; frozen model sources unchanged.

Water-supply atlas publication READY and QA passed (62studies/153figures,
778 Windows byte assets,1298 ZIPfiles/509links; browser, launcher,682source checks).
Finish its commit/push, then CONTINUE. Partial India days15–30 scored-area water
identity: wet rain1.043,evap1.662,netimport−.911,vaporchange−.292mm/day; dry allrain/
evapzero and netimport/vaporchange−.079. These are mechanism diagnostics, NOT
incomplete-month candidate accuracy scores. No model adoption/calibration.

New complete-month publisher scripts/publish_regional_rainfall_results.py is
implemented but not run (wait for at least one full45-day candidate receipt).
Then publish all complete cases; never omit worse branches or average available
regions into a pooled primary. Add organizer entry regional-rainfall-results and
packager report REGIONAL_RAINFALL_RESULTS_20261029.md only when results exist.
Analyzer requires complete receipts and all45 daily budgets, final fields exact.

New independent geometry module rotclimate/terrain_hydrostatics.py and15tests PASS.
Not wired into frozen models. Hydrostatic pressure/analytic geopotential and
variable dry-mass hybrid interfaces for future terrain-following atmosphere.
Next: static terrain-mass audit using all3 prepared Earth source elevations;
conserve source hashes, no dynamics, no claiming this changes current climate.
Missing terrain and nonlinear momentum remain potential causes, not proven.

## Workspace and authorization

`/workspace/rotclimate`, branch `work`. Python `.venv/bin/python`.
Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` for models/tests. CPU quota2 cores.
Push: `git -c http.version=HTTP/1.1 push origin HEAD:refs/heads/claude/friendly-turing-43ygeu`.
Last pushedf48a02a7: fixed monthly rainfall benchmark setup. Current fine-grid publication ready.
No approval required for this authorized local development/commit/push work.
No AGENTS.md found. Cloud runtime skill read earlier; no secrets accessed.

## Completed fine-grid controls

bceb3239 pushed all six completed21-level900/450s controls and updated atlas.
Prototype109starts/101completions/eightretainedfailures through that study.
AllfinalbudgetsPASS, oldinitialarrays/scalaracceptedprefixesexact. Maxwork432.
LandPfine900/450 India.619/.632,Mex1.751/1.715,PNW.427/.427mm24h.
SpatialsteprainRMS.204/.559/.148mm; notlocalconvergence orobservedaccuracy.
Old64-cap failures retained. See reports/CONVECTION_CAP_20261029.md.

## ACTIVE monthly rainfall benchmark — session98295

Setup COMMITTED/PUSHEDf48a02a7; controller nowRUNNING. All3legacy r39 controls
passed strict checks and reproduced archivedfloat32monthlyT/P EXACTLY. Legacy
record now1937/1932 (3added, no reruns by publication). First2prototypecases
Indiawet/dry900currently~23/24 of45days, past14-dayprelude intoevaluationmonth.
Do notmarkactivecasesasfailures. No newprototypefullmonthscoreyet.

Code already committed:
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
Scoring IMPLEMENTED scripts/analyze_regional_rainfall.py, newuncommittedfile
beingcommittedwithbaselinepublication. It validates all sourcehashes, rawreceipts,
all45dailyandfinal/partialbudgets, fixedmasks/calendar; pooledscorewithhelduntil
all6primarymonthscompleteandall3referencesqualified. No forecast/dynamicscalls.
Run --out output/regional_rainfall_benchmark_20261029 --dest output/regional_rainfall_analysis_20261029.
Fullmonthresultfigures/publisher stillneedsimplementation while jobsrun;
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

Current baselinepublicationstaged:61studies/150figures, newestregional-rainfall-reference.
773Windowsbyteassets,1292portablefiles/500links; browser/launcher/sourcechecksPASS.
Baseline3referencecontrols/rawannualfilesstaged; no activeprototypefilesstaged.
Finishthisbaselinepublicationcommit/push,thenKEEPWORKINGonthescorer/reporting.
ReferenceMAEIndia5.9545,Mex2.0883,PNW.20511mm/dayatselectedJul/Augfootprints.
Observed/r39meanrates8.092/2.408,3.023/1.591,.681/.838; notannual/globalskill.
Allthreeinputidentitiesandoldmonthlyfloat32outputsverifiedexact.
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
