# Active work — six native dry terrain controls complete; monthly rain still running

User:continue, do not stop after pushes; keep served .bat atlases current.
Latest pushed3b414516: closed dry core + static work publication + literal six controls.
Detached rainfall batch PID17717 still running. Log output/regional_rainfall_recovery_2_20261029.log.
Mexico wet/dry aboutday38/37 as of18:52UTC. Do not relaunch any workers.
Original session roots were killed twice; detached process survives tool resets.
All remaining literal month cases still run. No pooled primaryscore until6done.

Current native dry publication staged, QA PASS:65studies/158figures, fresh portable
1318files/534links, Windowscheckout, browser themes/mobile/keyboard/hash/errors,
682old sources +monthly+newdry source manifests unchanged, ZIP bytecomparisons.
Six synthetic-state/native-geometry6h controls ALLCOMPLETE at900/450s. Actual saved
hourly and final energy independently checked, extended full-state agreement.
Max final gasenthalpy+KE residual1.59e-4J/m² summedcells, no heat correction.
Timestep finalmassweighted temperatureRMS1.86–2.24e-5K. NO rainfall skill claimed.
New plots posted. No vapor/nonlinear momentum/open boundaries/surface/radiation.
These add6syntheticgeometryintegrations, zero Earth-climate-initialized starts.
67 related terrain/pressure/remapping/rainfall tests PASS.
Finish current native publication commit/push then continue.

Uncommitted next building block terrain_momentum_transport.py +6tests PASS.
Energy-skew reconstructed velocity transport, second-order manufacturedvortex
acceleration convergence; NOT enabled in dry time integrator or rain forecasts.
Needs actual implicit velocity+temperature coupling and trajectory qualification.
Do not silently switch frozen terrain_dry.py (its6h protocol hashes it).

Potential next operational improvement: detached final rainfall publisher that
waits for all originalattempts, scores fullmonths, updatesatlas+QA+commit+push.
Keep original monthly source/objective/masks frozen. Commit only explicit own
artifact paths (git commit --only) to avoid unrelated user staged changes.
Current analyzer/publisher already support completecases/pending/failedstates.

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
