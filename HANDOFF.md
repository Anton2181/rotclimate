# Active work — four complete rainfall months; final publisher being armed

User says keep developing/commit/push after milestones, do not stop after pushes.
No agents. /workspace/rotclimate branchwork; single-thread .venv Python.
Latest pushed584dea80: six dry terrain trajectory publication + nonlinear
momentum operator (not enabled). Current staged milestone: complete Mexico
tradeoff and automated final monthly publication. Finish commit/push then start
finalizer DETACHED, and verify waiting status. Do not duplicate model workers.

## Long-running actual rainfall batch

Detached controller PID17717, log output/regional_rainfall_recovery_2_20261029.log.
Four primary months complete (Indiawet/dry + Mexicowet/dry). Remaining Mexico
wet450 numerical check and PNWwet900 active; PNWdry900 queued.
Mexico wet MAE1.8608 vsr39 2.0883 (~11% gain), mean1.2252vsobserved3.0234.
Mexico dry mean0/MAE3.0234. India wet/dryMAE7.2542/8.0923 vsr39 5.9545.
No primary pooledscore untilall6complete/qualified. No best-initializationpick.
BothIndiabranches worse; Mexico improvement onlywet, drycollapse unresolved.

Current four-month publication output/regional_rainfall_results_mexico_20261029.
QA PASS Windowscheckout/portable/browser,65studies/158figures, sources and ZIPbytes
checked. Plots posted. Newest openingstudyregional-rainfall-results. Normal atlas
climate fields unchanged; Earthbaseliner39, worldatlasr38 remain qualified.
Counters currently115prototype starts/105complete/8retainedfailures/2active.
Pending notfailures. Final ifall7complete116/108/8. Legacy1937/1932 unchanged.
Synthetic dry subsystem controls6/6 separately counted, zero new Earth-climate
initialized runs from those controls/static audits/tests.

## Final publisher automation

Script scripts/finalize_rainfall_benchmark.py tested:2tests prove artifact-only
commits leave unrelated staged user work untouched and reject non-artifactpaths.
New calibration/rainfall_final_publication_20261029/plan.json ARMED but mustbe
committed before launch. Sources/guarded atlas inputs hashed before finaloutcomes.
Then subprocess.Popen .venv/bin/python scripts/finalize_rainfall_benchmark.py
--plan calibration/rainfall_final_publication_20261029/plan.json
start_new_session=True, stdinDEVNULL, outputlog output/regional_rainfall_finalizer_20261029.log.
Use singlethread environment. Do not leave longjobs attachedtoexec sessions.

Automation waits forall10declared attempts (3r39 alreadydone +7candidatecases),
validates frozen sources, scores onlycompletequalifiedmonths, updatesatlas,
puts rainfallstudyfirst, runsWindows/portable/browserchecks+ZIPbytecomparison,
commitsONLY explicit ownartifactpaths withgitcommit--only, pushes sameauthorized
origin branchclaude/friendly-turing-43ygeu. It never adoptsphysics/recalibrates.
Final status output/regional_rainfall_results_final_20261029/automation_status.json
(local/ignored). Eight-hourtimeout. Guard rejects source/atlas/branch changes.

IMPORTANT while watcherwaits: source-only newphysics outsidefrozen inputs isfine.
Changing guarded HTML/resultdata/report/organizer requires re-arming finalizer
against updatedfiles (preserve oldplan, stop onlyknownwatcherPID, newplanpath).
Otherwise it will safely refuse to overwrite concurrentatlaschanges. Do not
modify oldprediction/score sources while existing casesrun. Watcher can handle
retainedfailed finalcases, withholding pooledscore; no substituted trajectories.

## Physical mechanisms completed this round

New variable-mass terrain geometry +commonpressureport intersections +hydrostatic
rest pressuregradient +continuity-based compression power. All9declaredstatic
work controls pass; max pressure/compressionwork residual9.20e-12W/m²summedcells.
New native upwind heat/watertracer transport withpositive/constant/conservedtests.
New TerrainDryModel couples heattransport, midpointpressure/Coriolis andcolumn
constraint;8epssaddlelimit unchanged. Referencecolumnpotential absorbedinpressure
gauge; testedzero work onadmissiblewind, noheatcorrection.

Six6hsyntheticreference+1K thermalperturbation controls (3terrainregions,900/450s)
ALLCOMPLETE. Independenthourly/finalstateenergychecked. Max finalactualgasenthalpy
+KE residual1.59e-4J/m²sumcells, dtRMS1.86–2.24e-5K. These are notrain/climateskill.
Sourcecode+plans+rawfields inGit. Reports/TERRAIN_DRY_20261029.md andatlasstudy.

terrain_momentum_transport.py is the next component: energy-skew centraltransport
of reconstructednativevelocities usingadjoint interpolation.6testsPASS incl2nd
order nonlinearvortexaccelerationconvergence, terrainKEwork, signreversal/zeroflow.
NOT enabled in qualifieddryintegrator orrainforecasts. Need explicitnewsubclass/
backend withimplicitvelocity+temperaturecoupling andnative trajectorycontrols;
do not edit frozen terrain_dry.py/transport/work/gradient modules (literalplans
hash them). Reuse untouched physics as reference. Full moisture/phase/open
boundaries, surface/radiation andnonlinear vector momentum qualification remain.
Total related selected terrain/pressure/remap/rainfall+Git safetytests75PASS.

## Actual rainfall result (fixed footprints,31-day July after14-day prelude)

India wet: mean.86133mm/day, MAE7.25423. Dry: mean0, MAE8.09228.
Observed mean8.09228; r39 mean2.40797, MAE5.95452. BOTH prototypes worse thanr39.
Both complete45days and saved daily/final independent E/W budgets pass.
No pooled six-case score until all6 primary months are complete/qualified.
Mexico450 is a numerical control, excluded primary mean. No physics adoption.
Other reference MAE:MexicoAugust2.08827,PNWJuly.20511mm/day.
These are reused summer regional development cases, not annual/global skill.
World atlas release remainsr38; qualified Earth baseline remainsr39.

Frozen benchmark plan calibration/regional_rainfall_benchmark_20261029/plan.json.
Same224-km centered common footprints with projection-area weights and>=80%
valid land, interior masks24/23/12 cells. Same masks allprofiles. Mean of6
independently scored region/initialization MAEs; regional tradeoffs allowed.
No best initial-state selection or averaged wet/dry predictions before scoring.
Sources/calendar/timesteps1024cap/.01Kneutral/3600srelaxation unchanged.

## Process interruption/recovery — IMPORTANT

Tool-session/environment resets killed foreground process groups TWICE.
First:India wetday29/dryday30. Recovery41f77a71 pushed; both India trajectories
continued and completed. Original daily fields/ledgers preserved; original
per-step histories were not flushed and are unavailable, never fabricated.
Three one-day replay segments retained (wet repeated after CLI-global fix).
All10 next-day fields byte exact on both branches.
Second interruption:Mexico wetday3/dryday2. New literal recovery declaration
calibration/regional_rainfall_recovery_2_20261029/plan.json. Two detached one-day
Mexico replays complete, all10 saved fields byte exact. Total replaysegments5,
processinterruptions4. These are separate from Earth-initialized trajectory counts.
Original controller and first recovery driver/sources remain frozen.

AFTER committing declaration, launch remaining controller DETACHED (not an exec
session that stays running): subprocess.Popen([...],start_new_session=True,
stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=singlethread).
Command .venv/bin/python scripts/continue_rainfall_batch_recovery.py
--recovery-plan calibration/regional_rainfall_recovery_2_20261029/plan.json
--out output/regional_rainfall_benchmark_20261029.
Log output/regional_rainfall_recovery_2_20261029.log.
New recovery keeps recovery_batch.json and writes recovery_batch_2.json.
Do not launch duplicate workers; checkps and latest checkpoints first.
Every remaining literal case runs, bothMexico900, Mexicowet450,PNWwet/dry900.
No completed India orlegacy control reruns. Two workers, CPUquota2.

Counters before active monthly cases:prototype109starts/101completions/8failures.
With India complete and Mexico initialized:113starts/103completions/8failures,
2active. Pending not failures. Final if all7complete:116/108/8.
Legacy1937attempts/1932strictpasses/4historicalfailures/1historicalinterruption.
New month benchmark reproduced3r39 controls exactly; already counted. No repeat
legacy or prototype integrations from analyses/publications/static geometry.
Recovery/replay segments separately reported, no new Earth initializations.

## Useful tools

scripts/analyze_regional_rainfall.py --out output/regional_rainfall_benchmark_20261029
--dest output/regional_rainfall_analysis_20261029. Validates all sources/receipts,
all45 daily andfinal/partial E/W budgets; complete-month scores only. r39 rawannual
Gregorian overlap reaggregation, not old equal-month totals. Prefix histories can
be absent; retained daily ledgers and continuation cumulativehistory reconstruct.

scripts/publish_regional_rainfall_results.py --source output/regional_rainfall_benchmark_20261029
--out output/regional_rainfall_results_20261029. All available complete cases,
explicit pending, extra450case in table/JSON, primaryscore withheld until6done.
Creates atlas data/maps/report. Rerun after further complete cases, retain earlier
publication snapshot BEFORE overwriting. No new dynamics. Source states/forcing
are simulated fixed monthly lateral reservoirs, not observed-wind nudging.

scripts/monitor_monthly_rainfall.py --source ... --out output/monthly_rainfall_progress_20261029
makes unique timestamped daily traces and verifies every saved state ledger.
scripts/diagnose_monthly_water.py maps shared available postprelude wet/dry days.
India days15–30:wetP1.043,E1.662,netimport−.911,vaporchange−.292mm/day;
dryP/E0,import/vaporchange−.079. Conserved-store identities, not origintracers.
This points to moisture delivery/circulation and soil supply; not a uniquecause.

## New physical geometry building blocks (not adopted into forecasts)

rotclimate/terrain_hydrostatics.py: dry hydrostatic ps(height), inverse reference
geopotential, positive variable-mass hybrid interfaces.15tests pass.
rotclimate/terrain_apertures.py: all shared-pressure level-pair horizontal ports;
blocks below-neighbor-ground flow; conservative mass-divergence incidence.
7tests pass:flatlimit/stepmountain/portbounds/reversal/globalcancellation/singleport.
Related pressure/remap/rainfall stack41tests passed.
Static audits output/terrain_geometry_20261029 andoutput/terrain_apertures_20261029,
zero weather integrations. Fixed scored-area flat-column mass excess /flatpartial
column:India11.85%,Mexico20.65%,PNW17.94%. These are reference geometry differences,
not observed pressure errors. Same source heights/lapse/seaPs and380hPatop.

NEXT IMPLEMENTATION GATE: hydrostatic resting atmosphere over terrain must have
zero horizontal pressure force, with pressure work compatible with energy and
mass transport. Need vertical exchange/columnconstraint/native momentum as well.
Do not insert variable masses or elevation forcing into frozen flat operators.
Nonlinear momentum and actual orographic lifting remain absent. Old r39 has
parameterized upslope rain; flat experimental core does not replace it yet.
Initialization sensitivity is not proof of bistability or optimizer local minima.

## Publication QA

Stage atlas assets BEFORE checkout QA. Force-add ignored raw NPZ outputs.
organize_climate_accuracy.py --report FILE (not--out).
check_atlas_checkout.py --out FILE; package_fit_atlases.py --out ZIP;
check_portable_atlases.py ZIP --out FILE; browser checker via local8768server.
Keep page/report/data writers finished BEFORE packaging (previous concurrent
report edit caused a retained checksumfailure; serial rerun passed).
Compare currentnew HTML/JSON/PNG/NPZ/reports with ZIP bytes. RetainQAJSON,
ignorelogs/ZIP/screenshots. Darkcoasts withwhitehalo.
Reports explicitly listed in package_fit_atlases.py. Newest STUDIES entry first.
Full682sourcefreeze output/divergent_thermal_20261028/protocol.json unchanged.
Historical handoff reports/handoffs/BEFORE_REGIONAL_RAINFALL_BENCHMARK_20261029.md.
