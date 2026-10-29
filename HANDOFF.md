# Active work — full primary rainfall verdict; final450s control still running

User: keep developing/commit/push milestones, do not pause after pushes. No agents.
Workspace /workspace/rotclimate, branchwork, Python .venv/bin/python.
Set OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1. CPUquota2.
Push git -c http.version=HTTP/1.1 push origin HEAD:refs/heads/claude/friendly-turing-43ygeu.

## Current milestone and active jobs

Latest pushed71ec5389: coupled nonlinear dry terrain model +frozen pairedcontrols.
Current staged:all6paired nonlinearcontrols passed, atlaspublication andmonthly
waterdiagnostics,5complete-raincase snapshot,2nd automaticfinalpublication plan.
Finish commit/push then STARTfinalpublisher2 DETACHED as below. Neverduplicate
rainfallcontrollerPID17717. It is alreadyrunning finalMexico450control.

As of20:11UTC all6 primary900s monthcases areCOMPLETE/qualified. Main fullprimary
MAE3.52574765 vsr39 2.74930244:28.24%WORSE. r39 staysaccepted. Alltargets/masks/
objective frozen; regionaltradeoffs allowed. No recalibration/adoption.
Indiawet/dryMAE7.25423/8.09228 vsr39 5.95452.
Mexicowet1.86076 (~11%gain),dry3.02336 vsr39 2.08827.
PNWwet.26994,dry.65392 vsr39 .20511. PNWdrymean.02670vsobserved.68062.
Source output/regional_rainfall_analysis_primary_20261029/analysis.json.

RemainingMexico wet450 numericalcontrol aroundday39/45 at20:08UTC; expectedsoon.
Log output/regional_rainfall_recovery_2_20261029.log, controllerPID17717 DETACHED.
Threelegacy+sixprimary=9finished originalcases; onecontrolactive. Keep all7
prototype attempts even though thisconfiguration cannotwin. No earlystopping.
Counts116Earth-climateinitializedprototype starts/107complete/8oldfailures/1active;
finalif450passes116/108/8. Legacy1937attempts/1932strictpasses/4oldfailures/1oldinterruption.
New native dry controls12syntheticgeometryintegrations/12complete, countedseparately.
They addzero Earth-climateinitialized starts. Tests/staticaudits notbenchmarkruns.

## Automatic final publication — REARMED plan2, launch AFTERcommit

Finalizer1 PID19901 was intentionallyterminatedwhilewaiting before newownedatlas
edits. Preserveoldplan. New literal calibration/rainfall_final_publication_2_20261029/plan.json
captureslatest reporter/analyzer/frontend/source/asset hashes. Oncecommitted:
Popen .venv/bin/python scripts/finalize_rainfall_benchmark.py --plan
calibration/rainfall_final_publication_2_20261029/plan.json, start_new_session=True,
stdinDEVNULL, stdoutappend output/regional_rainfall_finalizer_20261029.log,
singlethreadenvironment. VerifyPID/statuswaiting. Do notattachlongjobs toexec
sessions (two environmentresets killed foregroundworkers; detachedonespersist).

Status output/regional_rainfall_results_final_20261029/automation_status.json
(localignored). It waits all10originalattempts (3legacy+7prototype), validatesall
frozen sources, scoresfullvalidmonths, updatesatlas+putsactualrainfallstudyfirst,
Windowscheckout/portable/browserQA+ZIPbytechecks, gitcommit--only explicit own
artifactpaths, pushauthorizedoriginbranch. No adoption/recalibration. Failed
cases retained andpooledscore withheldifinvalid.8htimeout. Unit testproves it
never includes unrelatedstageduserwork; outsideartifactpaths rejected.

While it waits: newsource-only physics outsidefrozensources isfine. Do notalter
protected atlasHTML/rainfallresultdata/report/organizer orSCRIPTS inplanwithout
stoppingonlyknownwaitingfinalizer,re-armingnewliteralplanandstartingdetachedagain.
Do notstopcontroller17717 or editfrozenprediction/scoremodules. Current reporter
adds a purelymathematical nonnegative-losslowerbound, neverpartial-monthscores.

## Published/current atlas

Newest regional-rainfall-results; newterrain-advective studysecond.
66studies/160figures. Windows799byteassets, portable1323files/541links, browser
keyboard/hash/themes/mobile/errorsPASS. Allold682sourcehashes +monthly+newNplan
hashes unchanged. CurrentHTML/JSON/PNG/NPZ/report bytes comparedagainstZIP.
Latest publicationdirs:
output/terrain_advective_publication_20261029
output/regional_rainfall_results_pnw_wet_20261029 (5cases snapshot; finalizerupdatesall7).
Rawfullprimary6case analysis separately retained,actualscorepostedto user.
Normalworldatlasrelease r38 andqualifiedEarthr39 unchanged. No badcandidateadoption.
All newfigures posted. Coastlines darkwithwhitehalo.

## Mechanisms completed and next physics

terrain_hydrostatics.py: actualdryhydrostaticheight-pressure/inversegeopotential,
variablecolumnmasshybridpressure interfaces; rejectundergroundtop, noclip.
terrain_apertures.py: exactcommonpressurelevelpair openings, blockedbelowground,
conservativeincidence. Flatlimit/stepmountain/reversal/globalmass tests.
terrain_pressure_gradient.py: shared-reference subtraction/commonpressureforce;
zero hydrostaticrest overterrain, nonzerothermalresponse, independentquadchecks.
terrain_pressure_work.py: actual nativeflux continuity reconstructsverticalomega;
independentphysicalcompression cancelspressurework.9staticcontrols pass,max9.2e-12W/m²sum.
terrain_transport.py: positiveimplicitupwindheat/watertransport,norenormalization.
terrain_dry.py: coupledclosed dry pressure/Coriolis/enthalpy,qualifiedsix6h900/450s
syntheticcontrols. Source/planfrozen. Norealmomentumadvectioninthisreferencecore.
terrain_momentum_transport.py: energy-skew projectedcentralnativevelocitytransport,
manufacturedvortexaccelerationconvergessecondorder. Momentumtransposeworkzero.
terrain_advective.py: nonlinearvelocity ANDtemperature midpointcoupling, explicit
advect_momentum off/on inSAMEmodelbody. Centeredenthalpy equation includesactual
native referenceflux divergence; equivalenttooriginal equation, noenergy-error
feedback/clipping/renormalization. Fixesuniform-backgroundroundoff. Constraint
pressure gauge absorbsreferencecolumnpotential, zeroworkonadmissiblewind.
Inherited8epssaddlethreshold andenergybudgetthresholds unchanged.

Paired plan calibration/terrain_advective_20261029/plan.json; driver
scripts/run_terrain_advective_controls.py. ALL6native6hcasesPASS, sourcecoldref,
4m/svortex+1Kbottom-easthernanomaly, one shared explicit initialmassprojection,
signedKEchange recordedwithoutheat. Off/on initialarrays byteidentical. Independent
hourly/finalfieldenergychecks incl extendedprecisionfullenthalpy. Noheatcorrection.
WindRMSdifferences.045–.070m/s,max.887–1.373m/s; T RMS.0054–.0111K,max.054–.118K.
Actual on/offwindmaps/energycurves posted,reportTERRAIN_ADVECTIVE_20261029.md.
82 relatedselected terrain/pressure/remap/rainfall/Git-safetytestsPASS.
These are drysynthetic-native-geometry consistencytests, NOTclimate/rainfallsuccess.
No vapor/phasephysics, openregionalboundaries, surface/radiation, smoothterrain
metric orEarthadoption. Nextcandidate needsmoisture+boundarycoupling; do notfudge
Earthplanetparameters or addobservedwind/humiditynudging. Currentfrozenwetmonthly
core isdifferent andstillflat. r39 hasparameterizedupslope rain.

Potentialthroughputnextstep: compression_power repeatedlyrebuildsstaticpressure
subintervalquadgeometry. Since omega linearinportspeed andT=Tref+layeranomaly,
power=C0@U +deltaT*(C1@U), sparseoperators canprecomputegeometry/referencequadrature.
Keepoldfrozenfunction, addcachebackend withunchangedadvancecode via isolated
bind_dependencies perinstance, validate inplacemutation, compareall9savedstatic
workcases andpairedwholetrajectories BEFOREusing. Couldspeed futurecalibration.
Notimplementedyet. Do notmodifyfrozenoldmodules toclaimsameexperiment.

## Rainfall protocol and diagnosis

Fixed224-kmcentered footprints, projection-areaweights,>=80%validland, interior
cells24/23/12.31GregorianJulIndia/PNW,AugMexico after14-dayprelude. Prelude not
assumedtoerase soilmemory. Primarymean6independentlyscoredwet/dry900sMAEs; no
bestinitialstatepick oraveragedpredictionsbeforescoring. Mexico450excludedprimary.
Simulated fixedmonthly lateralreservoirs, not independentglobalforecast/annual
orheldoutvalidation. Qualifiedr39 rawannualGregorianoverlapreaggregation; archive
float32monthlyT/P reproducedexactly by3newcontrols, alreadycounted, donotrerun.

Complete-monthwaterbudget diagnostics nowin analyzer, reporter andatlas. Derived
from savedrain/vapor/soil underfixedmasks: E=P-dsoil; import=dvapor+dsoil;
P=E+import-dvapor. Inferredidentities, notobservedE ororigintracers.
WetIndia E1.4334,I−.8096,P.8613; wetMexicoE1.8961,I−.8975,P1.2252;
wetPNWE.7591,I−.3274,P.5086mm/day. Allwet casesexportwater anddepletesoil.
DryIndia/Mexicorainzero,PNWtiny. Sourceinitializationandmoisturedeliveryaremajor
issues; thisdoesnotuniquelyprovecause, bistability oroptimizerlocalminima.
Fourcasealgebraiclowerbound3.37177vsbaseline2.74930 retainedin
output/regional_rainfall_lower_bound_20261029.json; noearlystopping. Fullactual
6primaryscoreabove nowconfirmsfailure. Normalclimate/biome/populationfieldsunchanged.

## QA / provenance / recovery

Stageassets BEFOREcheck_atlas_checkout.py. Force-add ignoredrawNPZ. Completeall
page/report/datawritersBEFOREpackage_fit_atlases.py; thenportablechecker andZIP
bytecomparisons. Reports explicitlylisted inpackager. Organizer --report,not--out.
Browserchecker canstartlocalserverinoneshellprocess,terminatefinally. RetainQAJSON,
ignorelogs/ZIP/screenshots. Full682sourcefreeze inoutput/divergent_thermal_20261028/protocol.json.

EnvironmentkilledIndiawetday29/dryday30; recoveryexact-nextdaychecks10fields byte
exact,3replaysegmentsretained (wetrepeatedafterCLIglobalfix), bothmonthsdone.
Second interruption Mexicowetday3/dryday2; twofurtherexactnextdaychecks, bothdone.
Fourprocessinterruptions/fivequalificationreplaysegments separatelyrecorded;
recoveryaddszeronewEarthinitializations. Originalper-step prefixhistories weren't
flushed; originaldailyfields/ledgersretained, neverfabricated. Recovery2preserves
firstreceipt. All remainingliteralcases runwithtwo workers. Stale oldprogress/
profileoutputdirectories retaineduntracked, notuserchanges tocleanaway.
Historicalhandoff reports/handoffs/BEFORE_REGIONAL_RAINFALL_BENCHMARK_20261029.md.
