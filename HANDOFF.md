**OWNER RULE (27 Nov 2026): "It's about earth accuracy first and foremost, always."** Painted-zone agreement on the
invented world never outweighs Earth accuracy; the r58 atlas stands despite the Mediterranean loss (strict 0.35->0.22).

# r58 ATLAS LIVE (27 Nov 2026 20:28 UTC): release complete, browser checks pass (smoke + 8 suites), reports/RELEASE_R58_20261127.md
World physics r58w (r58 + e116z zonal edge PW; Earth screen 1.0098 vs r58), world geometry = r51 world (W6 search
found nothing better), fit objective zonefit_rivers. Corrections retrained for r58w (calibration/earth_correction_r58_20261127).
Corrected r58w on dev31: T 1.509 / rain 0.438 vs corrected r51 1.489 / 0.415; plain r58 corrections give 1.511 / 0.432,
so the edge rule is not the cause. K1 (corrections on all 97 regions) REJECTED by the per-region rule
(calibration/correction_wide_20261127). r51 vs r58 on 97 regions: r51 13.8 % worse (calibration/r51_vs_r58_20261127); atlas stands.
Claude copy REPUBLISHED 28 Nov (owner: "The atlas isn't updated still"): https://claude.ai/artifact/XypoZqva951RWZm4ni6FiP
v23-26, 219 files in 4 publishes (.gz files need contentType application/wasm); hosted hashes match output/artifact_pack/earth_fit.

# Southern wind belts FIXED/QUALIFIED; current97 reference explicitly compatible

Main source005827e44 adds guarded SHwesterly/polar belts. Eleven previously
failing symmetry checks nowpass; combined39testsPASS,20pre-edit NHgoldens EXACT
on mixed grids. Both prospectively declared native sourcechecks complete2/2 with
original strictnumerics, worker22293 exited. OrdinarySom1100 ALLsavedTP/obs/
coords+monthlywind bytes EXACT, branchinactive. Wide nativeSom4012 branchactive
14/25steps up to2051cells; rain3587.62→3579.78, TMAE1.364457→1.363049,
maxmonthlyΔT.01439C/ΔP3.4885mm/Δwind.06862m/s. Smallsourceeffects, notbroadskill.
Full findings calibration/southern_zonal_belts_fix_20261127/findings.md.

USE output/southern_zonal_belts_fix_20261127/qualification.json for CURRENT89
engineering source + EXPLICIT compatibility to original97reference. Rawpaired
controls remain output/climate_reference_20261127/ref58/r58_PART; originalQ and
allprotocolsourcehashes remain historical, neverrelabelled. reference_scope.json:
actualcaseIDs ALL97 exact; guardFALSE on ALL97FULLgrids forEVERY s∈[-1,1],
includingprimer (threshold−27.562666,minactualgrid−10.489706). Exact model.py
comparison: onlyguardedblock added; other88sourcehashes unchanged. Thus existing
r58reference physics is unchanged. ZEROnew97integrations;39tests+2sourcechecks
qualifyfix. Futureplans mustPIN newQ/compatibilityproof AND rawcontrolprotocols,
notblindlyassert oldQ.modelhashes equalnewsource. Scope appliesr58Earthparams,
notarbitrarynewparams/worldgeography.

Raw before/after/regression XML/logs;13regressions+NHgolden;scope/2attempts/
protocols/certs/TP/windraws/review/inspectedsource_changes.png/agent_review/Q
allpreserved. Fix isunfitted anddoesNOTcompleteSH/globalthermodynamics. New
coupled native sourcechecks DO NOT rerun/rescueanynestedchild. Among6large
parents onlySomreachesnewbelts; Sahara/Algeria failures cannotbeexcused bygap.

NEXT climatepriority: precipitation conversion/stability. The native-parent
pressure pilot is CLOSED/UNAPPLIED1d74c8fec: SomJulywinderror−22.6% but
rain+53.8%; Sahara215→779,Algeria14.6→360 severewetting; NIhelps. All14numerics
passed. Changingpressureexterior alone isn'tfix, no more boundary/blend/padding
rescue. Read interpretation_note.md: childdata/formulas/locations stayedfixed;
actual SST/moisture boundarytargets CANrespondcoupled, neverclampedvalues.
Oldwind×observedSSTjoint stillrain2590vs457 withPWnearref; bothbase+expconv
active,overflow0. Warm-instability0closedforNIharm; offline sharedcapnotconvincing.
Before newverticalhypothesis reread r39 environmental6/6.5K/km failures (numerics
passed, accuracy/humidityfailed). Need defensible vertical stability/moisture
discriminator, notnew geographicmask/globaldrying/amplitude rescue. Existing
NCEPpressure-level reference machinery mayhelp; no nextstudy declaredyet.
Do notsilently treat prescribedobservedPW/descent as standalone-worldskill.

Current readableprioritynote calibration/climate_priorities_20261127/README.md.
Noactiveworkers. GoalACTIVE, W18/W18c permanentlyCLOSED,AAUNOPENED,
retainedr58params, atlasr51unchanged, nofine/worldfit/PR.

# Southern zonal-belt source correction APPLIED:39 tests pass, two checks declared

Rootmodel.py now adds ONLY guarded SHwesterly/polar belts, opposite seasonal
strength/meridional sign; existing friction/spin/maprotation retained. Prior
source lacks these belts: new mechanism tests11FAIL/1PASS before;13PASSafter.
Combined39regressionsPASS. Twenty PRE-EDIT Northern Hemisphere golden profiles
on mixed grids match every u/v/phi byte after source change.
tests/test_southern_zonal_belts.py; tests/fixtures/southern_zonal_belts_northern.npz;
raw before/after/regressions XML/logs +before_source.json/before_tests.py preserved
output/southern_zonal_belts_fix_20261127. Source fix is AFTER14-run worker exited,
never altered/retried its source or outcomes. It is NOT full global circulation.

Strong r58reference compatibility proof COMPLETE:
scripts/check_southern_belts_reference_scope.py -> reference_scope.json.
Actual caseIDs ALL97 exact; new guarded branch FALSE on ALL97 FULL grids for
EVERY s∈[-1,1], includingprimer. Onlymodel.pyinsertedguardedblock changed,88
other sources exact. Threshold−27.562666deg. Original refs/certs/protocols keep
old hashes; this is explicit inactive-branch compatibility, NOT97new integrations.
Only wideSomalia parent among6 can activate (2054potentialcells); Sahara/NI/
Algeria/Najd/Calif parent domains remain inactive, so this is no desert rescue.

Prospective calibration/southern_zonal_belts_fix_20261127/{plan,regions,README}
pins exactlyTWO sourcechecks: nativeSoma1100 ALLsavedcells+monthlywinds exact to
current97/off; nativeSoma4012 originalnumerics/inputs/scorebounds and branchactive,
reportallchanges, noaccuracyselection. Nativeparent control from CLOSEDnested
study, NOT a nested rerun. r58params fixed; private231; originaltolerances;
nice10/all4threads1/literalvenvPython. scripts/run_southern_belts_source_checks.py
prepare then --run aftercommit; reviewer sameprefix. NONEstarted yet. No retries.

Qualification pendingthese2coupledchecks: don'tlabelold97protocols newsource.
After pass, write ENGINEERING sourcequalification plus explicit compatibility
link, notnewclimateadoption. Broad current97 accuracy staysr58; atlasr51unchanged.
All14native-parent study completed/closed/rejected1d74c8fec (Somwind−22.6% but
rain+53.8%; Sahara/Algeria severewetting). Broaderpressure and convection/thermal
issues remain. W18/W18cCLOSED,AAUNOPENED,goalACTIVE.

# Native-parent pressure context COMPLETE:14 pass numerics, candidate rejected

Prospective10a12a43d, output/nested_pressure_context_20261127 complete14/14,
worker21818 exited. Off2 all saved baseline cell arrays EXACT; all native6
parents frozen before nested6. Actual full pressure-input/output frames,
scored T/P/winds/protocols/attempts/certs preserved. DirectGaussian max1.304e-8Pa
within declared1e-7Pa precision. Root89 source unchanged at completion.

CLOSED/UNAPPLIED: Soma July surface-vector RMSE10.562→8.179m/s (−22.6%, target
passes), but rain3548→5558mm, loss+53.8%. StillwestwardJuly(−4.834,+2.894).
Sahara215→779(loss2.708x),Algeria14.6→360(loss10.096x),Najd99→177,Calif491→523
all rain protections fail; NI547→602/Terror−6.1% useful local gain only.
No blending/padding/amplitude rescue, no broader extension/adoption.
Native larger Sahara parent7.16mm vsnested779 and Algeria parent.54vsnested360
prove large-domain rain change NOTpressurecontext alone. Kernel unknown weight
79→8.2% geometric only. Frozen offline pressure response also archived; no new
integrations/selection. Findings calibration/nested_pressure_context_20261127/
findings.md; raw review+inspected nested_response.png+agent_review complete.

NEXT concrete source gap reproduced: zonal_wind has SHtrades but NO SHwesterly/
polar belts (45N7m/s vs45S0;75N−3vs75S0 in symmetric equinox). Regression
tests/test_southern_zonal_belts.py currently11FAIL/1PASS, raw pre-fix before.xml/
before.log output/southern_zonal_belts_fix_20261127. Not committed failing tests
yet; source itself UNMODIFIED. Prepare symmetric SHbelts with opposite-season
strength, flipped meridional signs, unchanged NH bytes; don't alter other
hemispheric physics or claim full global circulation. Add outer guard for cells
south of SHHadleyedge. r58 edge33.590636/shift6.027970, radius1 => branch can
only affect lat<-27.562666 for ANY season. Ordinary97 child domains likely all
above that: prove actual case IDs/latitudes, don't rerun97 unnecessarily.
Wide Somalia parent reaches SHmidlatitudes; needs fresh native source check.
Correction is separate from rejected nested study; DO NOT rerun nested arms
under revised source or reopen it. Current97 old-source qualification remains
valid until source changes; then disclose compatibility/new source epoch.
Goal ACTIVE, AAUNOPENED,W18/W18cCLOSED,r58retained,atlasr51 unchanged.

# Native finite-parent pressure-context pilot DECLARED:14 integrations, unrun

New calibration/nested_pressure_context_20261127/{plan.json,regions.json,README.md}.
Input-only preparation complete: six1100/4012km56km pairs share full overlap
geography/observations EXACT at52-cell offset;231 private regular files pinned;
ZERO climate integrations. Input inventory output/nested_pressure_context_20261127/
input_inventory.json. scripts/prepare_nested_pressure_context_inputs.py generated
three missing parent caches; no old tree changed.

experiments/nested_pressure_context.py SEVEN known-answer tests PASS: analytic
outside heat-low contribution/local feedback/constant/native continuation,
actual wideFFT kernel, exact unchanged-parent sampling across two window sizes,
bad-alignment rejection. New runner run_nested_pressure_context.py and independent
review_nested_pressure_context.py compiled. Root89production unchanged.
No actual global parent is claimed: this is native finite planar parent context,
distinct from the separate spherical operator reference.

Exactly14: Somalia/NIndia default-off repeats must match ALL saved control cell
arrays byte exact; six native4012km parents (Sahara,Somalia,NI,Algeria,Najd,Calif),
THEN six1100km nested children. All6 parents frozen, none selected by accuracy.
Capture actual last pressure-input anomalies for each native day; child replaces
ENTIRE local padded rectangle with own CURRENT anomaly on EACH pressure call,
original pressure Gaussians/coefs on composite parent, crop, original momentum/
last_pres couplings. Child moisture inputs/boundaries/SST/parameters unchanged.
One-way/outer nearest/projection/long broad kernel/Earth conditioning remain
explicit limitations, no global climate or convergence-to-truth claim.

Prospective screen: Sahara rainloss<=.90; Somalia July geographic sigma995
surface-vector RMSE<=.90 vs default-off; ALL6T/Ploss ratios<=1.01. Original
numerics/no automatic retry, no accuracy early stopping. Failure closes fixed
alternative/no pad/blend/amplitude rescue. Pass only broader development,
NOT adoption. Raw parent/child climate+pressure inputs/winds archived, original
directGaussian reconstruction<=1e-7Pa operator precision bound (NOT solvertol).
Commit plan BEFORE preflight; then nice10/all4threads1/literalvenvPython prepare
and --run. No worker started yet. No fine/AA/W18c reopen; r58/atlasr51 unchanged.
Solar-bound/pressure0/instability0 alternatives stay CLOSED; current97 qualified.

# Solar-bound wetness experiment COMPLETE: full97 rejection; next global context

Committed prospective study9a21d3c1e; output/wet_energy_budget_20261127 now
complete99 original strict certificates (2 default-off controls +97 candidates).
Both off controls reproduce ALL saved arrays byte exact. Root89/r58/atlasr51
unchanged; same229-file private source off/on, all97 actual inputs/masks/obs paired.
No scientific retry, numerical/gate change, fine28 or AA. Worker20921 exited.

Fixed shared solar cap CLOSED/UNAPPLIED. Full97 S1.004161, 90% upper1.014629
(FAIL); T mean1.629671→1.633926 C (+.261%), rainloss.461644→.464281 (+.571%).
Means meet1% limits but continentalS1.042208/highland1.025579 FAIL1.02 guards.
Unmodified gate_v3 CLI agrees exactly with raw independent review (expected
accuracy exit1, not numerical failure); gate_inputs summary copies have manifest.
VolgaT−27.2%,Prairies−21.9%,BritishIsles−24.9%,NIndia−2.4%; BUT Ungava+29.1%,
Ontario/Hudson+34.5%,multiple rain harms. No capacity/bound/amplitude rescue.
Full findings calibration/wet_energy_budget_20261127/findings.md; all raw97
T/P and stepwise energy captures,2off arrays/protocols/certs/attempts/review,
inspected thermal_response.png and root agent_review preserved in output.
Effective EBM-column capacity assumption remains unproven; not closed energy.

NEXT structural direction started: experiments/spherical_pressure_context.py,
tests/test_spherical_pressure_context.py FIVE PASS (output/spherical_pressure_
context_20261127/tests.xml/log/prototype_review.json). Small dense whole-sphere
geodesic/area-weighted two-scale pressure reference, <=2048cells, zero climate
integrations and no production import. Constant/periodic/hemisphere/global-area/
off-crop influence tests; one l=1 harmonic max error.007559→.002134→.000546 on
8x16→16x32→32x64 with2500km kernel. Not full3D/all-scale/transport certification.
No actual global parent thermal field or momentum solved, no skill/adoption.
Need specify parent physics and nested-domain/scalable/reference agreement
BEFORE declaring coupled evaluations; don't pass off static EBM landmask as truth.
Protocol/limits calibration/spherical_pressure_context_20261127/README.md.

Readable main issues/progress/next choices:
calibration/climate_priorities_20261127/README.md. Major issues: wet cooling/
thermal dipole, missing off-domain pressure context, active tropical rain triggers,
under-rained interiors, Earth-only conditioning for world transfer. Old r39
environmental6/6.5 K/km profiles passed numerics but failed accuracy/humidity;
don't reinvent as an untested new model. Pressure0/globalinstability0 remain
closed. Current97reference remains qualified. W18/W18c permanentlyCLOSED,
AAUNOPENED, retainedr58, atlasr51 unchanged, no active workers, goal ACTIVE.
User asked if actual progress: candid yes to fixes/local gains, no new broadly
validated atlas; do not claim a rejected experiment improved retained climate.

# Shared wetness solar-bound hypothesis DECLARED:99 integrations, unrun

calibration/wet_energy_budget_20261127/{plan.json,regions.json,README.md};
experiments/wet_energy_budget.py;4 dimensional/allocation tests PASS;
scripts/run_wet_energy_budget.py + review_wet_energy_budget.py compiled.
One unfitted physical hypothesis: TWO positive wetness-cooling terms share
absorbed ice-free EBM-land daily TOA sunlight bound, using existing EBM column
capacity * actual regional relaxation coefficient for W/m2/K. Explicit NEW
effective-column assumption, NOT a closed surface/latent heat budget.
Dry-soil warming preserved; exact actual lambda/delta_sun identities asserted.

Production89/r58/atlasr51 unchanged. Private229 files: default-off model branch
plus helper, hashed sources and explicit off/on protocol. Exactly99: Middle
Volga/Ungava default-off ALL saved arrays byte exact, then fixed candidate ALL97
current-qualified development regions. No accuracy early stopping/selection,
no fitted amplitude, no per-region1% gate: existing policy-v6 dev6 (bootstrap
90%upperS<1, meanT/P<=1% worse, regimeS<=1.02). Individual harms still reported.
Failure closes THIS fixed candidate; no amplitude rescue. No adoption/fine/AA.
Original solver criteria, no automatic retry, preserve failures/interruption.
Commit before prepare then --run, nice10/all4threads1/literalvenvPython.
No worker started yet; all97 input identities preflight required.
W18/W18cCLOSED,AAUNOPENED,current97reference qualified and immutable.

# Pressure-exterior physical pilot COMPLETE: target improves, guard failures

All6 nativecoupled candidates pass originalnumerics, current97-control case/
input/params/obs/masks pairing and independentrawscorebounds. Privatepressure
filters nearest→constant0exterior ONLY; root89productionfiles/profileunchanged.
Saharatarget215.04→78.73mm,loss−54.51%,T2.364→2.267. Soma3548→3003,loss−15.16%.
BUT NIndia547→321loss+47.37%,Algeria14.6→5.15loss+24.43%,CaliforniaT+2.26%/
rainloss+1.006% allfail original1%guards. Najdloss−.12%. CandidateCLOSED/
UNAPPLIED,noblendstrengthrescue. No gate/source/defaultGaussian change.

SaharaJulywindstillwrongdirection(+1.917,+2.194) vsobs(−1.423,−4.325); control
(+1.473,+2.439). Soma retainswestwardJuly(−7.030,+1.583). BettertargetPdoesnot
provewindfix. Sourcepressure/turning/drying feedbacksallcoupled; missingoutside
context NOTrecoveredbyzeroor nearestclosure.3kernel/momentumtestsPASS.
Full findings calibration/pressure_zonal_exterior_20261127/findings.md;6rawcases/
T/P/winds/certs/protocols/summaries/review/inspectedfigure/agentreview outputsame.
PID20342exited; noactiveworkers. Current97qual remainsvalid/root89hashesmatch.

CURRENT calibrationreference output/climate_reference_20261127/qualification.json
and ref58/r58_PART, complete97passed,3recentnativeTP/obs32repeatsexact.
MeanTMAE1.629671C,rainloss.461644(exposeddevelopment,notindependentvalidation).
Committed0e35e8c35. Oldclimate_runtime_20261126 qualifications historical.
Offline sharedconvectivecap prototype5tests/0coupledruns notconvincingNIndia
protection, do notpresentitascandidatefix. Globalinstability0closedtoo.

NEXT options: usefullcurrent97pool. Mainrainoutliersinclude under-rained
Namibia19vs237/inlandAustralia17vs240 aswellasover-rainedSom/Sahara; avoid
broad drying. ExistingRHspread e22 waspreviouslytried(oldr24/26 docs earth_mode
~786/904), gaveunwanteddesertshowers/fittednearlyoff; don'tre-inventitblindly.
Distinct untestedthermallead from calibration/inversion_20261125/findings.md:
wet_cooling scaleswith regional temperature-aboveannualmean, notavailable
seasonalenergy, and overcoolswesterncontinental summers/latephase. Consider
physicallyspecifiedenergy/seasonalforcing formulation withbroadguards, not
globalcoolingknob orspentW18c ocean rescue. No nextstudydeclaredyet.
W18cCLOSED,AAUNOPENED,r58retained,atlasr51unchanged. NoPR.

# Pressure zonal-exterior pilot DECLARED:6 native candidates, unrun

calibration/pressure_zonal_exterior_20261127/{plan.json,regions.json,README.md};
experiments/pressure_zonal_exterior.py;3known-answer testsPASS; runner/reviewer
run_pressure_zonal_exterior.py/review_pressure_zonal_exterior.py. Only broad/
local pressureTanom Gaussians nearest→constant0 exterior. Root89productionfiles
unchanged; hashed private classmethod override; coefficients/otherfilters/
momentum/numerics fixed. Last_pres couplings respond. Unknown exterior hypothesis,
not globalpressuretruth; uniformfinitewarm patch getsedgegradients explicitly.
No observedforcing.

Exactly6:Saharatarget,Somalia,NIndia,Algeria,Najd,California. Reuse6qualified
current97controls. TargetPloss<=.90; all6T/Ploss ratios<=1.01; failclosesfixed
alternative/no blendrescue. Passonlybroaderexposedwork,notadoption. Commitfirst,
prepare/--run,nice10/4threadvars1/private228regularfiles. Restore experiment
pressure/run methods onfailure; actualwind recorded/geographicreview. None
started. Current97complete/pushed0e35e8c35. W18cCLOSED,AAUNOPENED,
instability0closed,r58retained,atlasr51unchanged.

# Current-source97-region reference COMPLETE and qualified

All97 original strict numericalcertificates PASS; inputs/caseIDs/obs/masks/
coords/terrain exact.3recentnativeSomalia/Sahara/NIndia T/P/obs32repeatbytes
exact. Newepoch current89physicalfiles+134cache+5helper/spec=228privatefiles;
no params/source/numericalchange duringrun. PID19885exited. Sourcequalified
output/climate_reference_20261127/qualification.json;8standard r58_PART folders
under ref58/, rawcases/cells/protocols/summaries; independentreview and inspected
error_summary.png. Full findings calibration/current_climate_reference_20261127/
findings.md. This is now current97baseline, NOT oldclimate_runtime_20261126.

Mean TMAE1.629671C, meanrainloss.461644(dimensionless; exposeddevelopmentpool,
notindependentglobalskill). Worst rain:Soma3548vs457(loss3.655),Sahara215vs2
(1.686),Namibia19vs237(1.080),inlandAustralia17vs240(1.043),Bolivia662vs2356
(.958). WorstT:Okhotsk3.45,NIndia3.21,Nigeria3.05,Ungava2.97,prairies2.88.
24historicalTParrays changed,73exact;maxscorechanges.0357C/.0270rainloss.
Oldsourcequalifications immutable/historical; currentreference ready forfuture
pairedwork. No fit,fine28,AA,W18ccontinuation,candidate,adoption oratlaschange.

Offline shared-convection-cap prototype only: experiments/shared_convective_cap_
prototype.py,5puretestsPASS, output/shared_convection_cap_20261127/offline_review.json,
calibration/shared_convection_cap_20261127/README.md.0coupledruns,noproductionimport.
FrozenstateNI raincut~109mm/yrvs~119fromfailedglobalinstability0, so notconvincing
monsoonprotection yet; do notpromise/runcampaignjustbecausealgebralimitswork.

NEXT bounded physicallead: thermal-pressure exterior assumption. Current big/
localpressureTanomalyfilters use nearest extension; finitewindows continueedge
anomalies outward at2050km scale. Propose separatelydeclared constantZEROANOMALY
(zonalexterior) for pressurefiltersONLY, fixedparams/grids. Targetsahara circulation,
guardSomalia/NIndia andothernativecases; no observedforcing/defaultgausschanges.
Not provenphysicsfix; offdomain anomalies unknown, padding/frozenflow audits
notcausalproof. No such candidatecode/plan/run yet. Keepinstability0closed,
W18cCLOSED,AAUNOPENED,r58retained,atlasr51unchanged. Noactiveworkers.

# Current-source97-region reference DECLARED; none started

calibration/current_climate_reference_20261127/{plan.json,regions.json,README.md}.
New scripts/run_current_climate_reference.py and review_current_climate_reference.py.
Exactly97 coarse r58 baseline runs in8 historical EXPOSED dev parts, no fine/AA.
Sameparams/actualcaseIDs/obs/masks/grids/numerics. Current89 source files and
134cache+5helpers=228regularprivatefiles.3recentnativegoldens must byte-exact
T/P/obs32. Old qualifications remainhistorical,actual physicaldeltas reported.
No candidate/profile/atlas change. Commit first, prepare then --run atnice10,
all4threadvars1, literalvenv. All97 actualinputs verifiedbeforeintegrating.
Anyfailed/interrupted scientificattemptstops,noautoretries/tolerancechanges.
Raw standard8partprotocols/cases/cells/summaries +independent rawarrayreview.
No worker startedyet. W18cCLOSED,AAUNOPENED,r58retained,atlasr51unchanged.

# Physical instability0 test COMPLETE: Somalia improves33.5%, India guard fails

Four new physical candidates,4 reused exact/current89-source controls. All
originalnumerics/local0.01 equations pass; pairedactualparams differONLYin
instability3.27995→0. Explicitexpconv/cap/RHheatgate/storm/slope/transportfixed.
Somalia nativeP3547.92→2359.41,loss3.6549→2.4290(−33.54%),TMAEimproves1.1%.
Sahara215→197loss−6.36%,Talsoimproves. NorthIndia547→465loss+11.15%, fails
original<=1%guard. JointobservedSom2590→2006loss−23.52%(reportonly).
Fixedzero candidate CLOSED/UNAPPLIED, no amplitude rescue/guardrelaxation.

Somalia stillfalsewetsummer and5.16× observedrain; PW44.38→46.01vs35.42obs.
Marineexchangechange−928mm explainsmuchofrain−1189,coupledfeedbacknotisolated
closureeffect. No acceptedclimateimprovement/atlas yet. Full findings calibration/
instability_consolidation_20261127/findings.md;4raw/certs/review/inspectedfigure/
agentreview outputparallel. PID19474exited; noactiveworkers. Userquestion about
progress answeredcandidly, concretephysicsresult reportedinclfailedmonsoon guard.

NEXT required infrastructure: current-source97-region reference understrict
existingprotocol,source/input/librarymanifest. No such newrefdeclared/started.
Find latest ref58/readiness/protocol scripts; reuse immutable exposed97case
specs, avoidsealedAA and spentW18c fine. Oldqualifications historical. Main
physicslead structuralstability/triggering in legacybase+expconv, NOT simple
waterremoval orglobalzero boost. Avoid arbitrarycoast/regionmask/amplitude
rescue of failedcandidate. Need freshglobalreference forbroadercandidatework.
Optionalheat_record.surface_c diagnosticbug describedbelow remainsunfixed;
currentanalysesused actualtracedTeq so unaffected. W18cCLOSED,AAUNOPENED,
r58retained,atlasr51unchanged. No PR.

# Physical candidate DECLARED: instability0, four new runs, none started

calibration/instability_consolidation_20261127/{plan.json,README.md}, new
run_instability_consolidation.py/review_instability_consolidation.py. Existing
instability parameter0 removes inheritedbulk warmboost, explicitexpconv/cap/RH
heat gate and transport unchanged. No main source/retained profile edits.
Exactly4 fresh candidates:nativeSomalia/Sahara/NIndia +jointobservedSomalia.
Reuse4 frozencontrols from six just-completed exact rainclosure replays;
all89sources225privatefiles/cache/case/params match, onlyinstabilitychanges.
New prospective control-reuse rule saves identical re-integrations.

Declaredscreen nativeSomlossratio<=.90 and allnativeT/P-loss ratios<=1.01;
jointSom reportonly. Fail closesfixedzero candidate,noamplituderescue. Pass
only permits broaderexposeddevelopment,noadoption. Commitfirst/prepare/--run,
nice10/threadvars1/literalvenvPython. Originalnumerics unchanged; anyfailure
stops,noautoretry. Alloldworkersfinished,no newworker yet. W18cCLOSED,
AAUNOPENED,r58retained,atlasr51unchanged,current97reference stillabsent.

# Rain closure capture COMPLETE: both base and exponential terms too large

All6 exactendpointreplays pass originalnumerics, sharedparentphysical/budget/
SST fields byteexact. ActualsolvewrappercopiesW/Ws/A/instability/fullclosure;
independentreconstruction≤1.1e-14mm/day.4helpertestsPASS. PID19223exited.
Somalia annualbase2300.80+exp1247.13,overflow0. Jointobserved1481.43+1109.00,
overflow0. Julybaselinebase10.27/exp4.65mm/day; joint4.90/4.36; obs~.84total.
Julyinstability3.056/2.236, effectiveRHthreshold.321/.366. Both inherited
warmboost and explicit exponentialconvection active; algebra doesn't prove
causal duplication. Full findings calibration/rain_closure_capture_20261127/
findings.md;raw6/fulltrace/closureinputs/review/inspectedfigure outputparallel.

NEXT actualphysics test:fixed instability0 removes inheritedbulktemperature
boost but keeps explicitconvection/cap/threshold andtransport. Prospectively
fourcandidate runs:nativeSomalia/Sahara/NIndia plusjointobservedSomalia.
Reuse alreadyexact/current89source controls (do not re-integrate identical
controls without need). Fullsource/cache/input/case/params pairing required,
only instabilitychanges;declareguardcriteria before execution. No candidate
plan/runyet. Userfrustratedwithdiagnostics:deliverthis physicaltest next.
W18cCLOSED,AAUNOPENED,r58retained,atlasr51unchanged. Noactiveworkers.

# Rain-closure endpoint capture DECLARED:6 exact replays, none started

calibration/rain_closure_capture_20261127/{plan.json,README.md}, scripts/
trace_rain_closure.py,review_rain_closure.py,rain_closure_components.py.
Four known-answer helper tests pass. No source/params/numerics change.
Exactly6:3baseline +3jointobserved endpoints of completedwind×SST study;
all parentphysical/raw/budget fields must exact. Private solvewrapper copies
actual W/Ws/A/instability/fullclosure, returns original untouched result, restored
on exception. Savefullscoredtrace; separate reviewerreconstructs base/expconv/
overflowactualrain, weightedmonthly/July contributions, figure. No condensate/
spread in declaredlegacybranch.225regularprivatefiles,nice10/threadvars1.
Commitfirst,preparethen--run; anyfailure/interruptionstops,noautoretries.
Prior12wind×SSTpacket complete/pushed d232c4f7d. No active worker yet.

User asks whether any actualprogress: candidly answered no materiallybetter
validatedatlas yet; priority now actualphysics intervention after this bounded
closureidentitycheck. JointSomPW only+4.9% butrain5.66×,JulWless thanobs butrain
11.1×. Do notkeep widening observational-forcing diagnostics without testing
an identified physical mechanism. W18cCLOSED,AAUNOPENED,r58/atlasr51unchanged.

# Observed SST fix +12 wind×SST runs COMPLETE; rain conversion is next lead

Commitad42ff244 declared source/plan before prep/integration. Observed-SST
mode now bypasses modeled damping addback, actual coupled test reproduced
oldfailure;58source+6WOA testsPASS.12regionalruns all original numericsPASS,
6 modeled-SST controls exact all shared monthly/raw/budget fields to parent.
All observed SST actual heatTeq/preice/moisture exact on EVERY modeled sea
cell; actualwind exact; source/reference/read-only arrays verified. PID17957
exited. Full findings calibration/wind_sst_diagnostic_20261127/findings.md.
All12raw packets/forcing/WOA+PW references/reviews/inspected2figures output/
wind_sst_diagnostic_20261127; sourcequal output/observed_sst_fix_20261127.

SomaliaPbaseline3548→3356withSSTalone; observedwind4163→2590withSST, versus457
observed. SSTchangeswindresponse+615→−766,interaction−1381mm/year. Sahara
jointP2.42vs2.07, butSSTaloneworsens. NIndia modelwindP547→653lossimproves,
joint877vs761 butmountainerrorspersist: Nepal4219vs519mm/year atonecell.

NEW keydiagnostic: jointSomaliaPW37.15vsNCEP35.42mm(+4.9%), butrain5.66×.
JulyPW32.90<36.43reference, rain281.93>25.43mm/month. Rain/mean-water proxy
5.40×(descriptive,notmicrophysicalefficiency/isolatedcausality). Supports
rainconversion/stability audit, not simplyremovingmoisture. PW1991–2020units/
axes/scales/raw+cacheverified; boundaryPW alreadyused =>NOTindependentvalidation.
Raw has5993negatives(min−2.307), existingbuilderclips0, cacheexactlymatches;
no datachanged. Initialnonnegativeassertassumptionfailed/read-only documented.
Somalia/Sahara0clipped-corner influence; NIndia4.55% cellmonths involved.

NEXT declare6 exact endpoint rain-closure captures: retainedbaseline vsjoint
observedwind/SST,3regions. Capture actual solvedW/Ws/dynamics/instability and
closureconv/r0/cap/evap/T/fT; reconstruct base/expconv/overflow components at
actual solved state, no physical changes. Fullparentphysical/budgetexact +
originalstrictnumerics. No nextplan/integration yet;12-run packet immutable.
Separate optional heat_record.surface_c mislabels postaddbackmoistureSST as
heatsurface in modelheat-onlymode; currentstudy usedactualTeq/preice instead,
so unaffected. Verify/fix recorderbeforefuture sensibleheatfluxaudit.
W18c CLOSED,AAUNOPENED,r58retained,atlasr51unchanged. No current97pairedref,
no active scientificworker. Do not reopen failedcap/deletion/globalturn lines.

# Observed-SST damping guard FIXED/TESTED;12 wind×SST runs DECLARED

Main model.py anomaly addback now only when sst_source=model. Previously obs
heat target was literal SST but moisture/convection/e91 got obs+modeled anomaly.
Actual coupled test reproduces1fail/1pass before, bothpass after; flags toggled
under observed SST now allphysical/budget bytes exact. Modeled SST retains old
heat-only behavior.58combined source tests+6WOA checksPASS. Rawlogs/XML under
output/observed_sst_fix_20261127. No regional integration started yet.

Prospective calibration/wind_sst_diagnostic_20261127/{plan.json,README.md,patch}.
New run_wind_sst_diagnostic.py/review_wind_sst_diagnostic.py. Fixed12 integrations:
6 modeled-SST controls reproduce current Ekman6captures byteexact FIRST, then
6 observed-SST arms, bothwindtypes×Somalia/Sahara/NIndia,56km/1100km. All coefficients
and original numerics fixed.225regular privatefiles,oneworker nice10/threadvars1.
Commit first, prepare then --run. Any failure/interruption stops preserved,
no automatic retries. No selection/adoption. Preparation validates full WOA
raw12hashes/cache and archives normalized ref/full forcing packets. Obs sea
inputs above ice threshold required. Actual SST preice/heatTeq/moisture checked
on EVERY modeled sea cell, actual wind exact; allinputs read-only unchanged.

W18c CLOSED,AAUNOPENED,r58retained,atlasr51unchanged. Prior sourcequals historical;
modeled-SST physical arithmetic unchanged but needs these exact regressions.
No current97pairedreference yet. All earlier workers finished; no new worker.

# Coastal Ekman hemisphere fix COMPLETE:56 tests +6 regional checks

Main source now uses signed latitude AND spin for coastal Ekman direction,
zero contribution at exactequator, legacyNH arithmetic byteexact. Known-answer
actual SST snapshots reproduce6fail/4pass before and10pass after; further
NHbyte/rotation check and combined56 focused testsPASS/no failures/skips.
All6 prospectively declared regional integrations pass original numerics/local
0.01 equations;4NH-only Sahara/NIndia arms exact all monthly/raw/budget fields.
Same actualparams/inputs/obs/coords/calendar; observed actualwind still exact.

Somalia crosses−8.67..+13.49deg,138southern coastal sources. Modelwindrain
3556.41→3547.92(−8.49),loss−0.233%,TMAE+0.000190C; observedwindrain
4097.36→4162.73(+65.36),loss+1.531%,TMAE+0.01599C. Mechanically correct
source retained, NO global accuracy claim or fit. Allfindings/raw6/figure/
review/agentreview/qualification output+calibration/ekman_hemisphere_fix_20261127.
PID17445 exited. This turn24regionalruns(6+12+6),allpassed,no scientificretry.
Current89source hashes in qualification.json; prior sourcequals historical.
No current-source97pairedref yet; needed before calibration/map use.

NEXT concrete issue (unfixed, no newexperiment yet): sst_source observed with
sst_damping_heat_only true still adds a MODELED undamped seasonal anomaly to
SST AFTER literal observed sea set T_eq. Moisture/convection/e91 use obs+anomaly,
so the old mode is not a clean observedSST diagnostic. Verify/fix this diagnostic
interaction with actual heat+moisturesea known-answer checks, preserving modeled
SST arithmetic, BEFORE any wind×SST physical comparison. Do not silently run
old attribution script. MainSomali physics remains coastalSST/boundary/source
coupling and rainconversion; Sahara pressureflow and NIndia spatialorographic
errors separate. Source deletion/globalturn/cap notadopted. W18c CLOSED,
AA UNOPENED,r58retained,atlasr51unchanged. No scientific jobs active.

# Signed-hemisphere upwelling FIX TESTED; six regional checks DECLARED

Main model.py now calls winds.ekman_turn: right for positivef, left for negativef,
including latitude AND spin; zero at exactequator. Existing empirical magnitude,
weights, smoothing unchanged. No tuned knob. Production SST known-answer tests
reproduce6fail/4pass before patch; all10 nowpass, plus NHbyte/rotationcheck.
Combined56 focused testsPASS/no skip. Logs/XML output/ekman_hemisphere_fix_20261127.
These10 tests stop before heat/moisture solves, not10climate integrations.

Prospective calibration/ekman_hemisphere_fix_20261127/plan.json+README+patch.
New runner/reviewer scripts: run_ekman_hemisphere_regression.py and
review_ekman_hemisphere_regression.py. Exactly6 declared regional integrations
(3 exposed regions×2wind arms), sameparams/grids/obs/strictnumerics.4NH-only
Sahara/NIndia cases require all fields/traces/budgets byteexact; Somalia crosses
equator, actualcoupledchanges allowed/reported. New225regularprivatefiles.
Commit first, prepare then --run atnice10/threadvars1/literalvenv. No workers
active yet. Previous17070/16724 confirmedexited BEFORE source edits.

This is a correctness/newsourceepoch, not globalaccuracy claim. Prior89source
qualifications now historical; never rewrite. W18c CLOSED,AAUNOPENED,r58retained,
atlasr51unchanged. Current-source97regionreference still needed beforefitting.
At declaration18 priorregionalruns complete this turn,6new unstarted.

# Wind × marine-relaxation ablation COMPLETE; deletion not adopted

All12 declared runs pass original numerics;6 controls reproduce both prior
wind arms byte-exact (all shared physical/raw/budget fields); forced actual
wind verified;6 inflow_gain0 arms have zero marine term. No scientific retry,
source/SST/other coefficient/tolerance changes. PID17070 exited. Full findings
calibration/wind_marine_ablation_20261127/findings.md; outputs raw12 packets,
forcing,review,inspected figure,agent_review. Preserve immutable.

Somalia modelwindP3556→3593 whene91off (rainloss+1.0%); observedwind4097→3423
(loss−16.1%), still vs457observed. Windresponse flips+541→−170mm/year when
marine source off,−711interaction. Removing1663source only cuts674rain due
advection+817/storm+139compensation. NIndiaoff loss+16.5%model/+4.2%observed.
Sahara215→202model/12.31→0.85observed. Deleting e91 is NOT a general fix,
not adopted or tuned. No additive causal shares/global closure inferred.

Separate next source audit: coastal upwelling rotation at model.py~1625 uses
spin but omits sign(latitude). Prograde southern westcoast equatorward wind
should turnLEFT; current code turnsRIGHT. Existing NHtest hardcodes formula
and misses this. Verify with analytic hemisphere/spin/rotation cases, then
fix and prospectively declare changed-source regressions. No patch/test or
source change yet. Check all old workers exited before source edits. No proof
this is mainSomali error. SSTfuture diagnostic must address heat-only damping
anomaly addback rather than assume literal observed SST throughout moisture.

W18c CLOSED, AA UNOPENED, r58 retained, atlasr51 unchanged. Fresh current-source
paired reference still required before calibration/map. All jobs finished.

# Wind × marine-relaxation ablation DECLARED;12 runs not started

New prospective calibration/wind_marine_ablation_20261127/plan.json +README,
new scripts/run_wind_marine_ablation.py and review_wind_marine_ablation.py.
Exactly12 fixed integrations on same3 regions/56km/1100km:6 byte-exact controls
replicate BOTH completed modeled/observed wind arms, then6 inflow_gain0
ablations under both wind types. Other coefficients/SST/numerics unchanged;
main physical source unchanged. Removing e91 removes moistening AND drying.
No selection gate/adoption; quantify coupled wind×source interaction.

Commit plan first, prepare then --run with4 thread vars1 and nice10, literal
.venv/bin/python. New225 regular private files, full read-only projected wind
packets.6 controls exact all shared raw/monthly/budget fields; forced actual
winds exact prescribed; marine-off field must be zero. Original0.01 numerical
criteria remain. Any failure/interruption stops preserved, no auto retries.
All completed parent packets immutable. W18c CLOSED, AA UNOPENED, r58 retained,
atlasr51 unchanged. No worker started yet. Parent6 wind study complete/pushed
737ffac12; full findings and spatial failures documented below.

# Six surface-wind diagnostic runs COMPLETE: compensation defeats Somalia correction

Plan/source/scripts committed4bae4a240 before preparation/integration. All6
original numerical certificates pass,3 controls byte-exact monthly/raw/budget,
3 observed-wind actual heat+moisture samples byte-exact to read-only projected
reference interpolation. No source/SST/other coefficient/tolerance changes.
Worker16724 exited. Full findings calibration/surface_wind_diagnostic_20261127/
findings.md; output contains full forcing,6 captures/certs, independent review,
spatial_rain_review.json, inspected wind_response.png, agent_review.json.

SomaliaP3556→4097 vs457 observed, TMAE1.298→1.515, rainloss+14.71%.
Convergence import1592→259 but marine relaxation−12.68→1662.56mm/year;
source compensation offsets wind correction. SaharaP215→12.31 vs2.07,
rainloss−91.63%, T improves. NIndiaP547→748 vs761, T improves, but BOTH
per-cell rain loss components worsen(total+35.80%): several Nepal cells
3246–3889mm vs366–772obs. Mean seasonal/annual curves hide redistribution;
do not substitute a regional-mean metric. No observed forcing adoption.

Next proposed: separate prospective fixed wind×e91 marine-relaxation ablation
on same3 regions; declare own budget and exact controls before any new runs.
Completed6-run packet immutable. Ablation inflow_gain0 tests source interaction,
not a selected moisture law. Prior rejected cap stays unapplied; no strength
tuning or W18c rescue. No next study started yet. W18c CLOSED, AA UNOPENED,
r58 retained, atlasr51 unchanged; fresh current-source paired reference still
required for future calibration. No active scientific worker to restart.

# Six surface-wind diagnostic runs DECLARED, not yet started

Prospective plan: calibration/surface_wind_diagnostic_20261127/plan.json and
README.md. New runner scripts/run_surface_wind_diagnostic.py prepares225
regular private source/cache files and3 full projected surface-forcing packets,
then --run executes exactly6 integrations: all3 unchanged model-wind controls
FIRST, then3 observed-wind interventions on Somalia/Sahara/NIndia at56km,
1100km pad and identical scored footprints. No physical source edits, SST or
other coefficient/numerical changes. Existing wind_source observed changes
heat and moisture velocities together. Controls must reproduce archived fields,
raw traces/winds and every local source account exactly. Actual observed solver
winds must equal read-only projected reference monthly interpolation exactly.

Commit plan before preparing or integrating. All4 thread vars1, nice10, literal
.venv/bin/python (do not resolve its symlink). One worker, fixed budget6; any
failed/interrupted scientific attempt is preserved and stops, no auto retries.
Full forcing/coordinates/Jacobian saved and hashed before integrations. Existing
inverse-Jacobian metric/rotation verified, source surface sigma0.995 not850hPa.
15 combined geometry/calendar/reference tests pass. Independent array reviewer
scripts/review_surface_wind_diagnostic.py produces regional T/P/source contrasts
and figure. Observed forcing is only an Earth diagnostic, not an adoptable
fictional-world solution. No selection gate on outcomes. W18c CLOSED, AA
UNOPENED, r58 retained, atlas r51 unchanged. Fresh current-source reference
still required before future calibration. No scientific worker active yet.

# Circulation components COMPLETE: four exact captures and geographic review

All4 fixed replays passed unchanged numerical certificates and byte-exact
archived scored physical fields/traces/budgets. PID16192 now zombie; do not
restart. Full findings: calibration/circulation_components_20261127/findings.md.
Observed winds/pressure NEVER entered a solver in this completed diagnostic.

July physical geographic east/north vectors:
- Somalia1100 model(-6.808,+1.512) vsNCEP(+2.498,+6.332). Belt(-7.115,+2.525),
  pressure(+0.307,-1.012). Crossing eligibility100%, pressure gateonly1.34%max.
- Somalia4012 model(-4.018,+3.296), gate33.09%max; still wrong eastward sign.
  Better wind does not fix rain (3556vs3589mm/year; earlier source compensation).
- Sahara model(+1.473,+2.439) vsobs(-1.423,-4.325): pressure part reverses its
  weak belt flow. Local crossingmask0 despite pressure gate67.32%max.
- NIndia model(+4.394,+3.450) vsobs(+1.080,+1.211), pressure gate98.33%max.
No universal extra turning/pressure strength is justified across these regimes.

Use output/circulation_components_20261127/geographic_review.json and
geographic_wind_components.png as final comparison. Original grid-frame
review/figure preserved; supplement uses existing tested projection Jacobian
including metric factors (no climate rerun). Actual pressure momentum and
belt+pressure+drag sums reconstruct raw samples; heat/moisture winds equal.
NCEP is SURFACE sigma0.995,1991-2020,2.5deg,not850hPa; pressure slopes are
production-grid diagnostics and full/zonal-anomaly SLP are not model thermal
pressure targets. Do not interpret regridded cells as independent observations.
All figures viewed/readable. Test filename collision was fixed before runs:
original tests/test_circulation_reference.py restored byte-exact, new5checks
in tests/test_surface_wind_reference.py; both files'12 tests pass together.

Next justified experiment: prospectively declare6 model-vs-observed-SURFACE-
wind runs (three exact baseline controls + three observed-wind diagnostics)
on same Somalia/Sahara/NIndia footprint, unchanged SST/coefficients/tolerances.
Project input geographic velocity into model grid with existing Jacobian,
verify actual raw solver wind against temporal interpolation, retain coupled
T/P/source changes. This tests whether correcting winds helps rain; it is
not an adoptable fictional-world law. No such six-run forcing experiment
has been declared or started yet. Keep W18c closed,AAunopened,atlasr51;
no background scientific workers currently active.

# Next circulation diagnostic declared: four unchanged exact captures

UNRUN at this commit: calibration/circulation_components_20261127/plan.json,
README.md. Four fixed baseline diagnostic replays (Somalia1100/4012km,
Sahara1100,NIndia1100,all56km) with pure instance wrappers around zonal_wind
and pressure_wind. Current root model/source/params/tolerances unchanged.
Capture actual prior pressure input, current pressure, returned wind parts,
drag and crossing/gate inputs. Require exact physical monthly fields/traces/
budgets and original strict numerical certs. No scientific retries.

Restored/validated public NOAA PSL NCEP/NCAR sigma0.995 surface wind+SLP,
1991-2020,global2.5deg. Raw files/metadata/normalized packet are in
output/circulation_reference_20261127/. Verified scale/units/grid/period and
converted SLP millibars toPa. downloads host timed out; fileServer worked,
one429 recovered with delay. Data retrieval only, no climate integration.
JulySomalia eastwardwind +2.498m/s observed vsr58-6.809, largepad-4.019.
This is surface, NOT850hPa; fullSLP differs from thermal anomaly. Five pure
reference/momentum tests pass. Observations will NOT enter any solver/model.

Commit plan before preparing/running scripts/trace_circulation_components.py
(all4 thread vars1,nice10). Fresh225 private files, singleton source/attempt
guards. --run executes exactly4; review_circulation_components.py auto-checks
Pa/m momentum, actual belt+pressure+drag wind sums and unchanged physical
fields, then compares surface reference and renders wind_components.png.
Inspect actual figure/findings. No new wind law, forcing, parameters, gate,
fine/AA data, W18c rescue or atlas/adoption. None started at this commit.

# No-water inflow guard COMPLETE:30 tests +7 matched regional regressions pass

Main source now enables e91 warm-sea inflow only if the existing modeled sea
mask has a water cell. All-land EDT's false outside-grid source can no longer
cause marine moistening/drying. This is NOT the rejected cap law and changes
no water-body classification. Pre-fix regression reproduced positive fake
marine reach;30 focused tests pass, including4 actual coupled homogeneous
runs byte-identical to gain0 controls, zero marine term, mixed geometry check.

The prospectively committed seven regional regressions also finished, PID15551
now zombie. All original numerical criteria pass; all actual case identities,
params, observations/coordinates unchanged. Somalia/Sahara/NIndia mixed-control
T/P fields byte-exact atfloat32. Of4 all-land domains in97 cached cases,
Kazakh is also exact; r_12n_22e,r_40n_94e,s2_7n_23e change slightly: maximum
annual rain difference~0.093mm/year, T-MAE change~0.000502C, rain-loss increase
~0.30%. Do not claim an accuracy improvement or unchanged97 source scores.

Full findings/reproducible review: calibration/no_sea_inflow_guard_20261127/
findings.md, review_regions.py. Actual source-epoch qualification and all7
raw scored arrays/certs/protocol/summary are under output/no_sea_inflow_guard_20261127/.
This explicitly changed-source golden regression is NOT a new97-region paired
reference/global climate qualification. Old protocols remain immutable.
Before next calibration/atlas, establish current source/protocol references.

All experiments/jobs are FINISHED; no scientific worker to restart. Rejected
cap pilot stays unapplied, W18/W18c permanently closed, AA UNOPENED. R58 params
retained; atlasr51 not rebuilt. Next main physics lead: circulation/coupled
transport behind Somali excess, with desert/monsoon protections; don't tune
cap strengths or reinstate the rejected global turning floor. No new circulation
experiment started yet. Source absence fix is generic correctness, not the cause
of the three studied mixed-grid Earth's large rainfall errors.

# No-water inflow guard: tests passed, seven regional regressions declared

Current working/source change: ClimateModel only builds/enables warm-sea
inflow if the existing modeled sea mask has any cell. This fixes fake EDT
sea indices on all-land grids and is NOT the rejected cap law. Pre-fix test
reproduced positive marine reach without any real modeled sea.30 focused tests
PASS (four coupled homogeneous toy runs byte-identical to gain0 controls,
zero marine exchange, mixed real-source geometry plus existing27 tests).

Static scan of all97 existing full coarse cached domains finds FOUR all-land
cases: kazakh_steppe,r_12n_22e,r_40n_94e,s2_7n_23e. This can change their physical
climates, so do not describe it as bookkeeping or claim unchanged97 scores.
No water-body classification change. All other mixed cases keep the same code
arithmetic; root r58 params unchanged, no atlas/climate adoption.

calibration/no_sea_inflow_guard_20261127/plan.json and README declare7 new
56km/1100km regional regression integrations: those4 + Somalia/Sahara/NIndia
mixed controls, compared with the preserved fresh-current-runtime r58 golden
fields under an explicitly changed source. Require unchanged case identities,
observations/coordinates, strict numerical certs, byte-exact float32 mixed
controls; report affected improvements/degradations without fitting. No fine/
AA data, retries or new97-region paired qualification. None started at commit.
Run the documented benchmark ONCE, inspect receipts/any surviving processes
before recovery, then publish actual outcome and new source-epoch scope.

# Cap pilot COMPLETE: numerical pass, prospective screen FAIL; keep unapplied

Private marine_target_cap_20261127 finished all6 fixed runs/reviewer, PID15167
now zombie. No retries/numerical changes. All3 legacy controls byte-exact incl
physical monthly fields/traces/budgets. Source/targets/rates/equations checked.
Full findings: calibration/marine_target_cap_20261127/findings.md. Actual figure
cap_response.png viewed/readable; review.json retains failed screen and18 raw hashes.

Somalia rain3556.41->3556.91mm/year, rain loss+0.0137%; cap binds0% at its
scored cells despite90% positive marine-rate samples. Sahara215.04->210.34,
loss-1.6395%, but scored marine rate0 despite lower target. NIndia547.42->538.96,
rain loss+1.4691% exceeds1% protection; active target actually binds~31.94% of
its positive-rate samples. Marine source falls32.49mm/year there, partly offset
by advection/storm response. All capped residuals <unchanged0.01 (NIndia0.009974).

Declared local screen FAILS: noSomali1% gain and NIndia protection fails.
Do NOT apply cap to main, tune strengths or reinterpret the screen. The cap is
an unapplied private patch, not a new adopted climate or full validation. All
current private packets are finished/immutable. Root main source is still the
applied marine-export diagnostic epoch at d5a86827e; r58/atlasr51 retained,
AA unopened, W18c permanently closed. No background scientific jobs remain.

Next justified work: circulation/coupled transport behind Somali excess, rather
than a receiving-land humidity ceiling (not active at scored Somali cells).
Separate minor correctness issue: legacy inflow computes nearest-sea EDT even
on all-land grids; no real sea means no marine relaxation/drying. Address with
a narrow source-presence guard and actual coupled toy tests, not the rejected
cap or a claim of fixing these mixed-grid Earth errors.

# Next physical pilot declared: private marine-equilibrium target cap

UNRUN at this commit: calibration/marine_target_cap_20261127/plan.json,
README.md, marine_target.py and unapplied marine_target_cap.patch. Six fixed
integrations:3 exact legacy r58 controls then3 Boolean cap cases (Somalia,
Sahara,NIndia), all56km/1100km. Main physical source stays at the applied
diagnostic fix; no cap code or parameter added to main. Seven helper tests pass.

New law caps receiving-land RH target by nearest-sea MODELED EQUILIBRIUM
column water (not actual source vapor or conservative transport). Existing
gate formulas/parameters unchanged; realized rates can respond. All-land has
no marine exchange/drying; sea targets unchanged. Require control physical
fields, traces and budgets byte-exact to completed archives, original strict
certificates/local residual0.01. Any failure stops, no auto retry/solver changes.

Prospective local screen: Somalia rain loss at least1% better and all3 regions'
T/rain-loss ratios <=1.01. Eligibility for further EXPOSED evaluation only,
not a global qualification. Do not fit a cap strength after a failed screen.
No fine/AA observations used; W18c stays permanently closed, r58/atlasr51 retained.

Commit this fixed plan before scripts/prepare_marine_target_cap.py, then run
scripts/run_marine_target_cap.py readiness and --run with all4 thread vars1,
nice10 (see README). Fresh226 regular private source/helper/cache files;
singleton lock and per-case hash/attempt guards. Independent reviewer runs
after6 pass, producing cap_response.png; inspect actual figure/write findings.
No such physical integrations have started at this commit. Do not confuse
the completed earlier six budget captures with this new six-case physical pilot.

# W18c permanently CLOSED; main marine diagnostic fix APPLIED and tested

W18c w1_005 FAILED the original fine28 gate: S28=1.0347252704 >1.01,
T+1.749%, rain loss+5.196%. All8 paired fine numerical certificates passed;
rain loss worsens in all4 regions. Dev6 had passed, but that does not rescue
fine failure. SupervisorPID14224 exited/zombie. AA remains UNOPENED, empty
seen_by. Retainr58 and atlasr51. DO NOT reopen W18/W18c, select another point,
refit against fine, alter gates or run sealedAA for this finalist.

Complete closure and independent fine-array reconstruction:
calibration/ppe_20261123/W18c_records/closure.md, final_campaign_status.json,
gate_fine.json, fine_array_review.json, review_fine_gate.py. Fine NPZ arrays
are float32 after scoring; explicit propagated ULP bound~1.54e-6 on S28
is far too small to affect failure. No integrations or gate reruns for review.
All49 original development results, frozen params and GP closure are retained.

After confirming both workers/supervisors exited and base hashes matched,
applied the prepared marine-export-only patch to main model.py/transport.py.
All89 main model hashes exactly match previously validated private patched
source; no physical parameter/solver changes. Promoted6 functional checks
into tests/test_marine_budget_exports.py (excluded private import guard).
27 focused main tests PASS, no failures/errors/skips. Applied source epoch:
output/marine_budget_export_applied_20261127/qualification.json; findings under
calibration/marine_budget_export_applied_20261127/. Signed marine exchange
now enters exported local/flux accounts; independent-reservoir E already
includes it, so its extra component stays0. Physical outputs remain unchanged
in paired toys and six exact archived scored regional captures.

IMPORTANT: this is a NEW DIAGNOSTIC SOURCE EPOCH. Old qualifications/protocols
are immutable historical source-pinned records, not current paired refs.
Do not restart W18c or claim a new97-region qualification. Any next benchmark
needs new source/protocol records. Main diagnostic fix does not adopt a new
climate or rebuild an atlas. Completed private padding/capture packets stay
unchanged, and all old waiting queues stay retired.

Next distinct physical lead: current marine relaxation uses a fraction of
receiving LAND saturation water; warm/onshore/distance gates use nearest sea.
Test a marine-equilibrium source-water cap prospectively with exact legacy
controls and Sahara/NIndia protections, holding those gates fixed. No such
new physical integrations have started. This is not a rescue/ocean refit of
W18c and must not use its fine outcomes to choose parameters. All six budget
captures are DONE; their full findings/figure were independently/visually reviewed.

# W18c dev6 PASS; fine validation LIVE; six-capture study complete

Resumed supervisor PID14224 is LIVE (verify actual /proc state), uses the
inherited singleton lock /tmp/rotclimate_W18c_campaign.lock. Recovery source
fix committed/pushed d4b4e69d7 before resume. See validation_recovery_launch.json
under calibration/ppe_20261123/W18c_records. Frozen finalist is still w1_005,
all49 initial scientific evaluations preserved, no extra wave evaluated.

Original dev6 PASSES: S97 0.9842206108, existing90% bootstrap interval
[0.9701247546,0.9983828892], T-1.936%, rain loss-1.220%, worst regime1.01796884.
Fine28 is underway on unchanged physical source/runtime qualification. AA
remains UNOPENED at this checkpoint and can only open if original fine gate
passes. Actual live status/output takes precedence over this snapshot. Do not
repeat gate/benchmark calls independently or tune against these outcomes.
No adoption/atlas rebuild yet; keep main physical source FROZEN through gates.

All49 results plus finalist metadata/parameter bytes, GP closure prediction,
design/emulator and dev6 gate are preserved in W18c_records. Predicted remaining
gain0.0029349<0.005, so the original policy stopped search after initial wave.
Status-writing repair changed no selection, numerical setting or gate.

All SIX private diagnostic captures FINISHED and independent review PASSES.
WorkerPID12025 now zombie; do not restart. Full findings:
calibration/padding_budget_capture_20261127/findings.md. Agent visually inspected
term_changes.png; review/figure/table/provenance/agent_review.json preserve all
terms, equations and exact raw fields. All local residuals pass unchanged0.01.
Somalia import-665.79 is offset mainly by marine+398.59 and advection+302.81;
Sahara marine0, but drying+260.05/storm+185.59 offset part of import-462.35;
NIndia import-164.98/storm-165.64 partly offset by advection+198.66/marine+62.74.
These are coupled local equation changes, not causal/source tags/global fluxes.

Source-based next physical hypothesis in findings: current warm-sea relaxation
targets a fraction of RECEIVING LAND saturation water, while nearest-sea SST
gates its rate. An upstream marine-water limit is a different closure to test
prospectively with desert/monsoon controls, not an established fix or license
to reduce a coefficient. Do not launch a new physical search before completing
the present validation and recording its result. The tested main diagnostic
export patch is still UNAPPLIED until finalist validation/supervisor exit.

# W18c finalist frozen; pre-validation supervisor recovery

W18c finished ALL49 initial evaluations, no numerical failures. The existing
GP rule closes further search: predicted gain0.0029349234 <0.005. w1_005 is
FROZEN finalist (objective0.9842206108, params hash4db0b828...0356b).
Original PID6609 exited/zombie before validation: state(..., **candidate)
supplied plan_sha256 twice to dict(), raising TypeError. No dev6 gate report,
fine candidate run or sealed-AA pair existed; AA declaration verified UNOPENED
with empty seen_by. This is a supervisor serialization error, not a scientific
gate failure or permission to reopen a failed campaign.

validation_supervisor_recovery.json and validation_supervisor_before_recovery.py
under calibration/ppe_20261123/W18c_records preserve old source/status/finalist
and zero-gate evidence. The fix only accepts identical repeated status metadata
and rejects conflicts; two regression tests pass. Original physical/shared-input
readiness passes unchanged. Resume the same finalist through existing once-only
dev6/fine/single-AA rules; no new points, refit, candidate choice or policy change.
DO NOT apply main diagnostic patch yet: finalist validation requires the original
physical source. Record actual resumed PID before assuming a process is live.

All SIX private budget captures also FINISHED, PID12025 now zombie. Independent
review passed, every saved physical state/trace dtype/shape/byte exact and all
complete local equations within unchanged residual0.01. review.json and plotted
term_changes.png are present; figure was viewed/readable, full findings pending
publication. No more physical replays are needed for this six-case protocol.

# Six private budget captures LIVE alongside W18c

New worker PID12025, detached nice10, command scripts/padding_budget_capture.py
--run. Check actual /proc state, output/padding_budget_capture_20261127/status.json
(real per-step progress/timestamp), run.log and per-case attempt/result receipts
before any action. Do not restart a live worker. The first3 original-size
controls passed with byte-exact saved physical states/traces and strict local
equation residuals (scaled max Somalia0.001696, Sahara0.003952, NIndia0.009488,
unchanged limit0.01). Somalia4012km also passed (scaled max0.00001758).
Sahara4012km now underway at last check. Remaining endpoints
then independent reviewer run automatically; scientific findings still pending.

The prospective six-case plan/producer/reviewer was committed and pushed as
b88a0c032 BEFORE preparation or any integration. Preparation verified225 regular
private files and unchanged main source/inputs.6 guard/accounting tests passed.
Only the already tested marine diagnostic-export patch differs in private source;
no physical parameter/source changes, calibration/gate changes or new targets.

PRELIMINARY actual Somali local equation1100->4012: import-665.79mm/year,
marine exchange+398.59, advection+302.81, diffusion+7.10, storm exchange-7.85,
surfaceE-2.52, drying+0.41, residual-0.02; rain+32.78. Four of six replays
complete, full independent study review pending. This splits the earlier
unpartitioned remainder without changing physical outputs; it does not isolate
causality or measure a boundary flux. Raw hashes and partial-readout scope are
in output/padding_budget_capture_20261127/somalia_endpoint_preliminary.json.

Operational launch recovery is preserved: first launch PID12006 exited BEFORE
ANY physical import/attempt/integration because the launcher dereferenced the
venv interpreter symlink to system Python. Library guard rejected it. No model
code/tolerance/plan change. recovery_0001.json records zero attempts and verified
correct venv libraries; launch_0002.json is the active correct Python launch.
Old launch.json is preserved as the failed first launch, NOT the live PID.

Freeze new producer/reviewer/plan/private copy until completion. DO NOT apply
the pending patch to main while W18c OR this six-capture worker is running:
its per-case source guards also require unchanged main source. Do not edit
the completed padding source/cache snapshots. An attempted replay without a
passed receipt requires recorded recovery; no automatic scientific retry.

Main W18c remains live PID6609, now28 completed development records and same
leader w1_005 S97/objective0.9842206108. Full gates remain outstanding; sealed
AA not opened by any follow-up. Adoptedr58, atlasr51. No new map/adoption.
New plot_review.py waits for completed six-case review before producing the
signed-source change figure; then inspect it and write/commit actual findings.

# Next fixed diagnostic: six private exact replays declared, not yet started

calibration/padding_budget_capture_20261127/plan.json and README.md declare
six ADDITIONAL diagnostic integrations (Somalia/Sahara/NIndia,1100/4012km,
all1100 controls first). This follows the completed9-case study, not a retry,
new padding choice or extension of its budget. No integration at this commit.

scripts/padding_budget_capture.py prepares fresh225 regular private files,
then --run uses the validated marine-export-only patch from the older private
fixture. Only model.py/transport.py hashes differ from r58; main W18c source,
shared inputs and completed padding packet stay unchanged. One worker nice10,
OMP/BLAS threads1. Require byte-exact saved physical monthly fields, raw
gain/sink/W/P traces and calendar plus original strict numerical certificate
and complete local-equation residual within unchanged0.01+export rounding.
Six tests pass (failure/interruption/no-retry, dtype/signed-zero equality,
marine sign, cancellation-resistant residual scaling and fixed plan budget).

Commit prospective plan before preparation/run (CLI enforces git HEAD bytes).
Prepare then run as documented with all4 thread vars1 and nice10. Singleton
lock/protocol prevent duplication/drift; failed or dangling attempts require
recorded recovery, no automatic retry. Status includes per-step timestamps.
After6 pass, scripts/review_padding_budget.py independently validates raw
references and complete equation, producing term integrals/endpoint changes.
Actual findings still need agent review. No main patch application, candidate
selection/gate changes, new fine/sealed use, climate adoption or atlas rebuild.

# Completed padding study: all9 passed and independently reviewed

Private padding has FINISHED. PID10059 is a zombie, PID10060 exited; do not
restart the completed producer/driver or the retired original waiting queue.
output/padding_sensitivity_parallel_20261127/review.json validates all9 cases,
all9 pairwise comparisons and36 raw files. All3 controls exactly reproduce
current-runtime r58. Agent visually inspected padding_changes.png and recorded
agent_review.json. Full findings and reproducible supplementary partial-source
accounting: calibration/padding_sensitivity_parallel_20261127/findings.md,
analyze_completed.py; output completed_accounting.json.

Annual rain1100/2220/4012km (same scored cells/observations):
- Somalia3556/3832/3589 vs457 observed; larger domains do not fix it.
- Sahara215/13.3/7.2 vs2.07 observed; strong improvement but still excess.
- North India547/429/470 vs761 observed; both expanded cases worsen rain loss,
  although largest-domain T MAE improves3.206->3.029C.
No pooled score, best padding, source change, climate adoption or atlas rebuild.
Do NOT deploy larger padding as the solution or translate frozen-wind proxy
changes into rainfall. Somalia1100->4012 import falls665.79mm/year while rain
rises32.78; unpartitioned remainder rises700.67. This remainder combines
unrecorded advection/diffusion/storm/marine exchange and equation residual,
not a measured boundary flux or isolated causal component/closure certificate.

W18c remains LIVE PID6609 on unchanged frozen source/inputs. Last26 complete
development evaluations, same leader w1_005 S97/objective0.9842206108. Read
actual campaign_status.json before action. Full gates outstanding; source
readiness passed again. Adoptedr58, atlasr51. Pending marine diagnostic patch
still UNAPPLIED to main; do not edit active sources/helpers/caches. Useful
next independent work is a separately declared bounded private diagnostic
capture with corrected export and exact archived physical reproduction, so
the compensating terms can be split. No such new captures started here.

# Latest review: remote branches checked; Earth conditioning scope recorded

Fetched ALL remote heads (the clone's default refspec fetched only the active
branch). friendly-turing-43ygeu is the newest; wonderful-mayer-uqbwtb is Nov16
and project-continuation-a484h1 is Nov12. Active branch was already current.

W18c now24 completed development records, w1_023 underway, same provisional
leader w1_005. Frozen-source/input readiness passed again. Full gates pending;
no adoption, no atlas rebuild, no extra validation targets opened by this audit.

Private padding remains LIVE PID10059/10060, now8/9 cases numerically passed.
Both Somalia and Sahara4012km completed; North India4012km is computing.
Do not restart either driver. Independent review launches automatically after
the last case; inspect its figure and write full findings before interpreting
the completed study. All controls exact; no tolerances/retries/design changed.
Somalia rain at4012km3589.19mm/year remains far above457.36 observed, despite
import falling to925.86 from1591.65 at1100km. Sahara215.04->13.33->7.22mm/year
across pads, observed2.07. These pending-full-review results do not isolate a
single mechanism and do not select a deployment padding.

NEW read-only scope audit: calibration/earth_conditioning_20261127/findings.md,
audit_source.py and source_audit.json. r58 Earth boundary uses observed NCEP
PW; monsoon descent is derived from observed global WorldClim rainfall. SST
and global observed cloud-reference branches are inactive in r58. The existing
r58 adoption explicitly documents Earth-only boundary conditioning; atlasr51
uses the zero edge_obs_pw default. A selected-file static AST scan finds only
a diagnostic-shape target read in model.py, not a complete dynamic dependency
proof. No integrations or current-source changes. Treat Earth scores as
conditional regional skill; validate replacement forcings before world transfer.
Two identical source-audit executions passed and preserve this source epoch.

# Active goal: W18c and prospectively amended private padding study LIVE

Current processes (always recheck actual /proc state after reconnect):
- W18c PID6609 remains live on original frozen physics/shared inputs. Last
  22 initial candidates complete, w1_021 underway; leader still w1_005,
  S97/objective0.9842206108, worst regime1.01796884. No full gate/adoption.
- Private padding driver PID10059, worker PID10060, both nice10. New packet:
  output/padding_sensitivity_parallel_20261127/. Check driver_status.json,
  integrating.log, driver_failure.json and per-case receipts before any restart.

IMPORTANT scheduling amendment: the old waiting queue PID8757 was stopped
BEFORE ANY padding integration (old study had0 attempts/results). It is now a
zombie/retired, not active. Original plans/preparation/protocol remain intact.
output/padding_sensitivity_20261126/superseded_before_run.json blocks old
execution, so there is ONE nine-attempt budget, not two. Do not restart the
old queue or original padding plan. Prospective replacement was committed in
eeb97f316 before the first run; see calibration/padding_sensitivity_parallel_20261127/README.md.

Why changed: private code/cache isolation permits useful physical evidence
while the longer W18c campaign computes. Scientific design is IDENTICAL:
r58 source/parameters,3regions,same scored cells/observations,pads1100/2220/4012,
same exact controls, tolerances, failure policy and max9 attempts. Only timing,
namespace and reuse of6 prepared private cache files changed.59 tests pass;
225 private regular files/source hashes and unchanged main inputs verified.
W18c source/design/selection/budget/proposals/gates/sealed use are UNCHANGED.
Pending marine-budget main-source patch remains UNAPPLIED while W18c runs.

All3 1100km controls passed, bit-exact float32 archive reproduction incl
Somali/Saharan E/W/u/v. All3 2220km cases also passed; the3 large4012km
cases remain pending at last check. Read actual receipts.
The driver automatically runs the independent reviewer after its fixed study;
no automatic source application/adoption/publication. Do not modify current
runner/reviewer/plan/private sources while active, or retry failed/interrupted
attempts without the declared recorded recovery review.

PRELIMINARY Somalia1100->2220 (full9-case review still required): rain
3556.41->3831.87mm/year, convergence import1591.65->1386.39, surfaceE change
-13.85, drying change+1.55mm/year. The unpartitioned equation remainder rises
~493.01mm/year. It combines advection/diffusion/storm/marine exchange and
residual, NOT a measured boundary flux or one-process attribution. Monthly
state changes RMS T0.20568C, rain38.08564mm/month. Exact cells/observations,
calendar and independently reconstructed raw traces were checked. This is
evidence against treating the earlier fixed-field filter proxy as a rainfall
prediction, not an adopted fix or a reason to change the declared experiment.
Preliminary JSON packets preserve raw hashes and scope; finish ALL cases.

NEXT: monitor both live jobs. After padding completes, inspect the actual
figure, verify independent review and publish complete findings/failures.
Let W18c finish under its original rules, review its finalist/gates, then apply
and retest the ready diagnostic export patch as a new epoch. r58 remains
adopted, atlasr51. Do not regenerate regional leader reports unless it changes.

# Earlier active-goal state follows

# Active goal: W18c live; automatic fixed-padding follow-up queued

Check BOTH live processes before restarting anything:
- W18c: PID 6609, scripts/run_w18c_campaign.py. Last 19 initial candidates
  complete, w1_018 underway; consult live campaign_status.json.
- Follow-up queue: PID 8757, scripts/run_climate_followups.py. Its heartbeat
  is output/climate_followups_20261127/status.json, stdout queue.log.
  It was verified alive, waiting, holding its singleton lock; no padding
  attempts existed at launch/readiness. Both are detached processes, but
  always recheck after any executor disconnect; zombie PIDs are not live.

The queue will AUTOMATICALLY run the already declared nine-case private r58
padding study after W18c is terminal AND its supervisor/benchmark workers
exit, then run review_padding_sensitivity.py. Do not manually launch a
duplicate padding study. This diagnostic can run while the W18c finalist
awaits agent review: it uses its own original r58 copy, exposed cases and
unchanged budget, and cannot change candidate selection or sealed outcomes.

17 queue tests pass: live/nonterminal guards, orphan-worker waiting,
zombie filtering, interrupted-attempt pauses, command-failure/no-output
stops, dependency drift and check-only mode. Frozen dependencies are in
output/climate_followups_20261127/protocol.json. Do not modify those runner,
reviewer or plan files while queued/running. The queue never applies the
core patch, adopts physics or commits/pushes results. Its finished state
still needs figure inspection, scientific findings and finalist review.

If the queue pauses for recovery, preserve its failure state and record the
agent's investigation before resuming; no automatic scientific retries. If
it dies while a padding child is alive, restart only the queue after checking
the existing child; it will wait rather than duplicate it. A dangling padding
attempt without a result still requires the declared recovery review.

Leader unchanged at 19 completed points: w1_005, S97/objective0.9842206108,
worst regime1.01796884. Full gates remain outstanding; r58 is adopted,
atlas r51, sealed AA unopened at this checkpoint. Do not regenerate the
13-record regional report unless the leader or stage changes.

# Earlier active-goal state follows

# Active goal: W18c live; provisional-leader regional tradeoffs reviewed

Check live PID 6609 (`run_w18c_campaign.py`) and campaign_status.json. Last
verified: 16 of 49 initial records complete, w1_015 running. The old PID 1877
is a zombie. Do not duplicate the run, apply the pending core patch or start
the padding study while W18c remains active.

Read calibration/ppe_20261123/W18c_records/progress_0013.md and the inspected
figure output/ppe_20261127/W18c_progress_0013/development_progress.png. This
is a fixed 13-record snapshot, not a current gate result. The leader remains
w1_005: S97=0.9842206 (T MAE -1.936%, rain loss -1.220%), worst regime
S=1.0179688. No finalist or full validation pass has been declared.

The leader improves 52 regions and worsens 45. Nigeria s2_5n_7e and Somalia
s_2n_43e account for about 59.8% of its net score gain. Somali T MAE rises
1.298->1.645 C while rain loss falls 3.663->3.188. Western Europe worsens in
both components: T 1.252->1.409 C, rain loss 0.322->0.373. North India and
Kalahari are slightly worse in combination; NW Australia's gain is small.
Arid T MAE worsens 3.51% while rain loss improves 3.79%; temperate rain loss
worsens 3.90% while T MAE improves 3.15%. The headline does not resolve these
issues. Do not predict the fine result or invent a retrospective local veto.

Regional contributions use global reference denominators and sum exactly to
S97-1; they are not mean individual ratios, causal shares or global-area skill.
Independent checks cover 13 objectives and 194 regional components, a common
reference epoch, the append-only live prefix, all 97 regions and seven regimes.
Zero new integrations; the bootstrap gate has not run. Existing selection,
search budget, proposal sequence and gates are unchanged. Update this report
only when the leader changes or a stage finishes, not every goal turn.

Next: finish W18c and review its frozen finalist under the original gates.
Then apply/retest the ready marine-budget diagnostic patch as a new source
epoch, and run the prepared nine-case padding study on its original r58
snapshot. r58 remains adopted, atlas r51, AA unopened. Both follow-ups are
ready; see the immediately preceding handoff below.

The post-run padding reviewer is now implemented and ready:
`.venv/bin/python -I scripts/review_padding_sensitivity.py`.
It currently refuses because the physical study has not run. Fifteen tests
pass for seasonal cancellation, instantaneous rate/water covariance, calendar
and footprint matching, failed-case gaps, and direct archival control arrays.
It verifies source/file/certificate hashes, reconstructs monthly P/W from raw
traces, compares all three padding pairs per region, and reports signed,
absolute, RMS and maximum changes without an aggregate or preferred padding.
Readiness receipt: output/padding_sensitivity_20261126/reviewer_readiness.json.
No padding attempts exist. After actual runs, inspect its figure and write
findings; software readiness does not constitute physical validation.

# Earlier active-goal state follows

# Active goal: W18c live; tested marine-budget correction READY, UNAPPLIED

CHECK current live PID6609/run_w18c_campaign.py and
output/ppe_20261127/W18c/campaign_status.json. Last13 completed, w1_012 running.
Old PID1877 is a ZOMBIE after executor disconnect, NOT a live run. At23:35UTC
resumed original supervisor detached with inherited lock after verifying11
completed records+31 certified partial regions. NO duplicate/candidate/budget
change. Receipt calibration/ppe_20261123/W18c_records/executor_resume.json.
Leader remains w1_005,S97/objective.9842206108,worstregime1.01796884. No
finalist/gate/adoption claim. r58 adopted, atlasr51, AA unopened.

NEW READY FIX: READ calibration/marine_budget_export_patch_20261126/findings.md
and marine_budget.patch. Patch only model.py +transport.py export accounting;
MAIN PHYSICAL SOURCE IS STILL UNCHANGED. Single-column land humidity
relaxation is solved already but missing from exported local/flux ledgers.
Add signed marine_exchange beyond surfaceE. Reservoir E ALREADY includes it,
so its additional component is0 (not a claim physicalexchangeis0). PreserveE
and every physical field; no solver/rain/temperature/parameter change.

Private validation COMPLETE:3fixedtoy configurations,9paired-validation runs,
plus4coupledtoy runs in fixed existing regression suites; NO Earth regions.
430560 byte-exact physical scalar comparisons including reservoirlayerwater;
28 tests pass(no skips/failures), incl genuine positive/negative source solves
and ocean_sink1/.4 +signedreportcomponent. Fluxledger .032438->.001593 passes
existing.01; maxscaledlocal.009580/.008147/.001560. Reservoir residual/cert
unchanged; old failures retained. Qualified evidence output/marine_budget_export_patch_20261126/.
Private baseline/ and patched/ are ignored; never edit/reuse their results
under another source. Additional marine_export_checks.py deliberately has a
nondefault filename for private-only checks; original testfilename rename
preserved identicalbytes and is recorded in unit_test_source.json.

NEXT: whileW18cactive, DON'T APPLY PATCH or start prepared padding integrations.
After terminal+supervisor exit: review W18c finalist/gates before any adoption;
apply/retest diagnosticpatch as a new source/protocol epoch, preserving old
qualifications. Promote6functional checks (private-contextguard staysprivate).
Then activate prepared9-run padding study on its ORIGINAL pinned r58 snapshot;
main diagnosticpatch does not modify that snapshot. No refitting boundarymode
or reinterpreting historical flux failures. If executor drops again, exclude
zombies, verify saved regional receipts, then resume pending work only with
the /tmp/rotclimate_W18c_campaign.lock advisory lock and detached session.

# Earlier active-goal state follows

# Active goal: W18c resumed; isolated padding experiment READY, not started

Executor disconnected: old PID1877 is a ZOMBIE, not a running campaign.
Verified11 complete rows +31 saved partial regions; resumed at23:35UTC on
26Nov with detached PID6609 and inherited advisory lock
/tmp/rotclimate_W18c_campaign.lock. Receipt W18c_records/executor_resume.json.
No live workers existed before resuming. Do not mistake stale PIDs/status
for live progress; inspect /proc state, excluding Z. Existing certified
regional packets are reused by the original supervisor; budget unchanged.

CHECK PID6609/run_w18c_campaign.py and live
output/ppe_20261127/W18c/campaign_status.json BEFORE restarting anything.
Last11 completed, twelfth w1_010 resumed. Frozen physical source/shared caches
unchanged. No new adoption; r58 current, atlasr51, AA unopened. Provisional
leader NOW w1_005: S97/objective0.9842206108 (~1.58% lower average dev loss),
worstregime1.01796884 within1.02. Earlier handoff's base/regime failure is
superseded by this new leader; no finalist/full dev6/fine/sealed pass claimed.

READ calibration/padding_sensitivity_20261126/README.md and plan.json.
Nine fixed future integration attempts: Somalia s_2n_43e, Sahara u_21n_21e,
NorthIndia, pads1100/2220/4012km. Integer-cell offsets0/20/52 retain identical
56km scored cells; round2200/4000 would shift sampling. r58 frozen regardless
of future adoption. No parameter changes, new targets or candidate selection.

PREPARATION COMPLETE under output/padding_sensitivity_20261126/. Private
model/ copies89physicalsources+128cachefiles+2helpers=219regularisolatedfiles;
NEVER edit this pinned snapshot. All9staticfootprints generated. Independent
45612exactstaticchecks, coords1e-10deg, masks24/25/494cells, actual --run CLI
refuses activeW18c.17unittests pass. Zero climate integrations/attempts.
Do not mistake preparation_review.json for physical climate validation.

RUN ONLY AFTER W18c terminal AND supervisor exited (runner enforces both):
nice -n 10 .venv/bin/python -u -I scripts/padding_sensitivity.py --run
All3 exact1100controls first, then fixed6expanded cases. No retries or changed
tolerances; started receipt without result requires recorded recovery review.
Runfile validates fullprivateinputs, actualcaseIDs, strictnumerics andcontrols.
Then independently review tracedgain/sink/W/P and monthlyT/P/E/W/u/v. No
sealing/adoption/atlas. NPZ files are globally ignored; publish explicit
footprint/fields files with targeted git add -f, NEVER force-add model/.

IMPORTANT historical counterevidence: calibration/map_edge_20261124/README.md
already found broad r52 domain sensitivity but Somalia nearly unchanged;
largerpadding worsened pooled scores and did not stabilize at3300. r53
edge-humidity variants also rejected (edge_moisture_20261124/findings.md).
Currentr58 test adds exactmatchedcells+instantaneousrates, not a new claim
that largerdomains fix Somalia. Do not change deployment calibrationmargin or
introduce observed lateralhumidity as a substitute. Previous epoch scores stay
separate. Next: monitor/finishW18c and reviewfinalist; activate prepared study
only when allowed. Core marine-budget export patch remains deferred; an
unapplied patch can be developed separately without editing frozen snapshots.

# Earlier active-goal state follows

# Active goal: W18c running; convergence boundary dependence identified

CHECK live PID1877/run_w18c_campaign.py, log/tmp/rotclimate_w18c_campaign.log
and output/ppe_20261127/W18c/campaign_status.json BEFORE doing anything.
Last8completed, w1_007 running. Do not duplicate process, edit physical source
or shared inputs/caches. Fixed campaign continues; no finalist/adoption yet.
r58 adopted, atlasr51, AA unopened. Best checkpoint still fails regime cap.

READ calibration/convergence_boundary_audit_20261126/findings.md. Zero new
climate integrations. Actual2000km Gaussian sigma vs1100km regional padding;
45x45cellsat56km. Nominal4sigma radius143cells/~8008km. ~77.8% nominalkernel
weight uses exterior continuation (production reflect). NOT77.8% falsewater.
FrozenMONTHLY convergenceproxyreflect/nearest/zeroexteriordiv,1/day:
Somali control .097399/.044400/.025019; turning .039645/.031009/.010534;
Sahara .055877/.022974/.013334. Other extensions are stress assumptions,
NOT known outside winds or selected fixes. Actualgain not reconstructed.
IndependentmanualGaussian/boundarykernel matrices +manualdivergence verify
2628filtervalues,7884scalars; maxfilterdiff2.55e-21/s;876uniquecellmonths;
figure inspected, allsourcesunchanged. Scientific support for boundary
SENSITIVITY, no observed rainfall causality or physical improvement claim.

NEXT after W18c freeze resolved: separately declare bounded padding-sensitivity
climate experiment, same r58 physics/scoredcells/56km, Somalia+Sahara+exposed
wetmonsoon protection(NorthIndia), fixedpaddingbudget, freshstrictcontrols,
traceactualgain/W. Largerpadding also changes other operators, not isolated
causality. No boundarymode/fluxscale chosen by matching Somali rain. No
wholesale flux restart (historical accuracy/numeric failures already retained).
Core marine-budget export patch remains deferred until W18c closes.

# Earlier active-goal state follows

# Active goal: W18c running; convergence-import audit complete

CHECK live run_w18c_campaign.py PID1877 and campaign_status.json; do not restart
or change core source/shared inputs. Last check7 completed, w1_006 running.
Adoptedr58, atlasr51, AA unopened; development best still fails regime cap.

READ calibration/convergence_import_audit_20261126/findings.md. Zero new climate
runs.3650 exactfloat32 import/drying reconstructions; independent1825cellsteps,
16425scalars,396monthlychecks; inspected seasonal figure, pinned provenance.
Somali baseline import+1591.645mm/yr, positive ALLsteps/cells; advection net
+1585.343,drying-194.164. Gain.0512-.1765/day,mean.0974. Co-occurrence is NOT
doublecount proof: production concentration advection omits -Wdiv(u). Turning
reduces import to605.435 but changes other terms too. Sahara import787.724
and drying-1378.396. Historical r39/r43 flux switches already failed accuracy
or numerical guards; no point restarting them wholesale. Source branch that
subtracts monsoon-heating velocities is INACTIVE here (monsoon_heating0).

NEW focused lead: flux_scale_km2000, Gaussian4sigma support8000km vs1100km
regionalpadding,45x45gridat56km. Support mismatch alone is NOT measured bias.
NEXT committed calibration/convergence_boundary_audit_20261126/plan.json:
zero-integration measurement of nominal exterior kernel mass plus fixed
reflect/nearest/zero-divergence extension sensitivity on saved monthly winds.
Manual convolution checks, no reconstructing actual instantaneous gain from
monthly fields, no choosing a boundary rule based on observed rain. Any real
padding/physical experiment needs separate bounded plan and W18c source freeze.

# Earlier active-goal state follows

# Active goal: W18c running; marine-access audit complete

Latest remote branch checked/pulled: claude/friendly-turing-43ygeu. No newer
remote branch found. CHECK live PID1877 / run_w18c_campaign.py and
output/ppe_20261127/W18c/campaign_status.json BEFORE any restart. Source and
shared inputs remain FROZEN. Never duplicate the running campaign.

READ calibration/marine_gate_audit_20261126/findings.md. Zero new climate runs;
876 saved cell-months,1752 independent scalar paths,4380 scalar field checks,
8 synthetic tests, exact production geometry, inspected figure and provenance.
Somali baseline ALL288 monthly paths reach sea at BOTH resolutions; turning
265/266 reach sea,23/22 land through horizon, no positive monthly gate on those
land paths. Little support for false marine access explaining Somali rain.
Sahara185/186 paths EXIT domain: UNKNOWN, not nonmarine.14 land-horizon paths
have positive gate but actual captured marine exchange is ZERO throughout
Sahara. All3 domains contain real sea and all scored nearest indices valid;
generic all-land EDT risk is NOT the actual cause here. Monthly wind proxy
is not instantaneous transport; retain measured temporal gate aliasing.
Marine source/sink annual totals: Somali control+230.832/-243.515, turning
+451.036/-26.549, Sahara0/0 mm/yr. No climate improvement/adoption claimed.

Latest checkpoint6 completed dev candidates, seventh w1_005 underway; live
process may advance. Base still best development objective0.9857234, S97
0.9826256 (~1.74% lower mean loss), BUT worst-regimeS1.020310 exceeds1.02
cap. Do NOT describe as passing/adoptable. No finalist selected. Fixed49+
up to16+16 budget then development/fine/sealed rules remain. r58 adopted,
atlasr51, AA unopened. Snapshot is for recovery; never overwrite live results.

NEXT: audit positive-only convergence import algebra/signs and overlap with
advection/column drying using saved traces first. Existing Somali local terms
~+1592mm/yr import and+1585advection do not by themselves prove double count.
Declare any further integrations separately; physical changes and core budget
export fix wait until W18c closes. No marine gate redesign justified yet.

# Earlier active-goal state follows

# Active goal: W18c running; marine-budget bookkeeping defect identified

CHECK existing PID1877 / run_w18c_campaign.py process and live
output/ppe_20261127/W18c/campaign_status.json before restarting. Log is
/tmp/rotclimate_w18c_campaign.log. Do NOT modify physical source/shared inputs
while it runs.49+up to16+16 fixed budget, finalist by dev only, then fine/AA.
Adopted climate remains r58; atlas r51. AA unopened at this checkpoint.

READ calibration/somalia_transport_trace_20261126/findings.md.
Original THREE instrumented replays exactly preserved fields, but exported
local-budget tests failed; KEEP those original failures. Separately declared
THREE corrective replays (six total) captured actual solve_moisture arguments.
DEFECT: e91 land marine-humidity relaxation is included by solver but omitted
from exported E/local budget. It can source OR sink. Original comparison also
used surfaceE denominator instead of actual net source (incl drying/import).
External corrected diagnostic passes0.01 unchanged: maxscaled .001696 Somali
control, .001273 turning, .003952 Sahara. Actual climate arrays ALL EXACT.
Marine net annual -12.683/+424.487/0mm respectively; seasonal cancellation
large. Core export patch DEFERRED until W18c closes (source inventory frozen).
7targetedtests pass incl positive/sink regression of real moisture solver;
180independentmonthly integral checks; figure inspected. No climate adoption.

In ALL traced cells/steps of these3cases surface and transport u/v EXACTLY
MATCH. No hidden friction/wind-split cause here. Somali control local terms:
advection+1585, convergenceimport+1592, landE+853, eddy-372, drying-194mm/yr.
Turning drops advection/convergence by~861/~986 but marine input offsets~437
and eddy removal weakens. Local equation is stationary CONCENTRATION form,
NOT a conservative boundary-flux/global budget or observed causal attribution.

NEXT independent cheap diagnostic: audit e91's nearest-sea onshore gate vs
upwind marine access using EXISTING saved wind/land-sea fields; no new climate
integrations needed initially. This is a hypothesis, not proven geometric bug.
Positive-only convergence import also deserves checking. Do not adopt a
regional floor (already worsens Sahara). Any physical change waits for W18c
closure and a separate full-gate plan. Keep all historical source/score
mismatches explicit; no reopening sealed data or population evidence work.

# Earlier active-goal state follows

# Active climate goal: W18c running; Somali factorial diagnostic complete

CHECK existing run_w18c_campaign.py process and
output/ppe_20261127/W18c/campaign_status.json BEFORE restarting anything.
Main log /tmp/rotclimate_w18c_campaign.log. Current process launched PID1877
(session39071), no need to duplicate it. Process may move candidates while
this handoff is read. Do NOT edit physical source/shared caches during it.

W18c first point w1_base completed all97 regions; fresh paired development
S97 .9826256 (T -1.9054%, rain loss -1.5695%). This is a development result,
NOT a finalist/adoption/fine pass. Full49(+up to16+16) fixed budget/gates remain.
No new climate release; adopted r58, local atlas r51. Sealed AA still unopened.

READ calibration/somalia_mechanism_20261126/findings.md and reviewed output.
Eight predeclared integrations, two exact reference controls,672monthlyscalar
checks,8strict certificates; inspected figure. No parameter fit or adoption.
Somali observed457.4mm/yr, control3556.4; land-source-off3155.4; globalminimum
turning2439.6; both1850.0 (still4xobs). Sahara obs2.07, control215.0; source-off
72.6; turning357.3; both196.6. Turning response larger in Somalia but worsens
Sahara. Keep global floor OFF. In this model land_recycling scales represented
landE, so source-off has E=0 and also changes soil P-E: not pure recycling with
surface evaporation held fixed. Responses are not measured causal shares or
an audited atmospheric water-budget decomposition. Both effects interact.

NEXT useful independent work while W18c computes: use existing model trace
hooks to inspect moisture_u/v, condensation drivers and forcing on the same
exposed regions. Surface wind alone cannot establish the transport wind.
Declare a bounded diagnostic before any new integrations; do not expand this
completed eight-run budget or open any new targets. Pressure-gradient/remote
heat-low forcing is the focused structural lead; original r52 diagnosis had
remote Arabia/India lows outside the regional map. Any real structural change
must wait until W18c is closed and use full gates, with desert controls.

# Earlier active-goal setup follows

# Active climate goal: fresh r58 paired reference qualified; W18c ready to run

Owner goal: identify and fix the main outstanding climate issues; continue
trying major/minor mechanisms as warranted. Commit/push remain authorized.
No atlas rebuild for each improvement. Latest adopted climate stays r58.

READ calibration/ppe_20261123/W18c_runtime_amendment.json BEFORE any search.
Original W18c plan unchanged:49 initial + at most16+16, fixed seed/ranges,
close if predicted gain<.005, dev6 then fine28 ONCE then sealed AA ONCE.
This is W18's one continuation, not another retry. No AA opening before gates.

This restored workspace lost the derived inputs/reference runs. Public WC4
archives match historical hashes; NCEP PW+WOA/SST/depth/frozen sea restored.
All97 r58 runs have strict numeric certificates. California repeat arrays
are EXACT. But historical194 scores NOT exact: mean abs Tdelta .003602C,
mean rain-loss delta .002568; maxima .05917C/.07053. Precise cause unresolved;
old derived grids unavailable. r46 Alps also differs. Preserve FAILED exact
replay output/ppe_20261126/ref58/restoration_review.json; do not relabel pass.
Fresh paired reference separately qualified in
output/climate_runtime_20261126/qualification.json. All NEW candidates compare
only to these fresh r58 runs; policy adoption gates have NOT been relaxed.
Boundary obs_pw + chi_pole_ice were absent from case identity: FIXED,29tests
pass; supervisor six budget/sealed/resume tests also pass. No physical model
change. Restoration tools + references committed for reproducibility.

Fresh inventory output/climate_runtime_20261126/error_inventory.csv/json:
Somalia rain7.78x, Sahara u_21n_21e104x (small observed denominator), Kalahari
.08x, NW Australia .07x; north India/Najd cold ~2.7C; southern maritime cold;
regional spring timing errors have opposite signs. Rank actual loss/burden,
not rain ratios alone. Phase omitted for weak observed seasonal cycles.

NEXT command .venv/bin/python -u scripts/run_w18c_campaign.py
Supervised/resumable journal: output/ppe_20261127/W18c/campaign_status.json;
main log /tmp/rotclimate_w18c_campaign.log if launched by this goal turn.
Check existing process/status BEFORE starting it again. Finalist picked ONLY
on development objective; all-gates pass returns READY FOR REVIEW, no automatic
adoption. If fail, preserve failures; no second W18 continuation. Then address
Somali circulation/boundary and false desert rain, with a new structural plan.
Do not edit rotclimate code/shared caches while this campaign is running.

# Historical handoff and owner decisions below

# OWNER 22 Nov 2026: "you don't have to rebuild after each tiny model improvement, I'd rather conserve tokens and focus on

**Rivers / height map outcome (27 Nov 2026): v2.2 STAYS (natural physics).** Owner decisions: rivers follow unchanging physics; the height map is calibrated; undrawn rivers compared to drawn river systems in their region (relative rule); where the painted tiers genuinely drain into large undrawn rivers (329 cases vs drawn systems within 300 km, 40 over 10,000 km2, largest ~88,000 km2) the owner ACCEPTS them. Regional tilts toward drawn rivers within the tier bands (scripts/terrain_tilt.py, alpha 2-10 m/km) did not remove them and broke the tier gates; capped-tree terrains (scripts/terrain_capped.py) only met the cap by overriding physics or with artefacts. Kept: rotclimate/routing draws every drawn river in full (factual rivers already pass the strict check); routing always follows the height map. Thin < thick: 3 of 11 confluences still fail under v2.2's natural drainage. output/terrain_erosion_20261107/map_height_v23.* are NOT adopted prototypes. Records calibration/rivers_cap_20261126/.

**OWNER (26 Nov 2026): rivers follow unchanging real physics (steepest descent / Priority-Flood on the height map); the HEIGHT MAP is what is calibrated.** No stored drainage tree may override the routing; every river rule and gate is evaluated on the drainage recomputed from the height map. scripts/terrain_capped.py's capped tree is only a target the height map is shaped to (divides as ridges, channels falling to their outlets), within the tier rules.

**OWNER (26 Nov 2026): never assume a rule is display-only; the owner cares about the factual model.** Rivers: every drawn river must exist in full in the model's hydrology (v2.2 passes the strict check); no undrawn channel may have a catchment larger than the smallest drawn river (measured per river); within each river system a thin drawn river carries less catchment than the thick stem it joins. Enforced in the terrain / drainage (height map v2.3, scripts/terrain_capped.py), tier rules as before. Display change (rotclimate/routing.segments always draws drawn rivers) is only a consequence.

**r58 ADOPTED (26 Nov 2026).** r57 + e116 observed lateral column water at map edges (Earth calibration boundary; the atlas keeps land_edge_rh) + e75 eddy barrier (storm moisture capped behind high ground), refit W17 then the one allowed continuation W17c (storm-track rain). Why: the r57 error inventory (calibration/inventory_20261126) put the largest coherent error in interior rain deficits (Canadian Shield, Congo, Amazon, Bolivia, Kalahari, NW Australia 6-50 %% of observed); W16 (e116 alone) failed the regime cap in the highlands, W17 failed dev6 on the upper bound (0.9851 [0.966, 1.004]). Gates vs r57: dev6 S97 0.9710 [0.9486, 0.9922], T +0.6 %%, P -6.4 %%, regimes tropical_wet 0.870, highland 0.909, continental 0.914, tropical_dry 0.960, temperate 1.007, mediterranean 1.008, arid 1.014; fine28 0.9972; sealed Z (opened once, coastal boxes) S 0.931 [0.846, 0.995] T -5.8 %% P -8.0 %% PASS. Params calibration/local_accuracy_20261023/r58_params.json, r58_adoption.json, W17_records, W17c_records. Reference runs output/ppe_20261126/ref58/r58_<part>. Sealed Z SPENT; no unopened set remains. Atlas NOT rebuilt (remains r51). Open: Somalia rain (no Somali jet), Southern Ocean ~4 C cold (ocean_transport 0), spring timing (east coasts warm, snowy interiors cold), hot dry land cold.

**After r57 (26 Nov 2026): parked probes.** Sealed Z declared (12 regions, coastal boxes, LAND_MIN 0.55). East-coast spring (Japan, Korea, Hokkaido, Nova Scotia +2.5 to +5.6 C): e136 (less sea damping off east coasts) + e137 (sea-breeze cooling toward a colder nearby sea) cool summer, not spring, because the model's spring sea is not colder than the land; code removed (calibration/phase_20261125/notes.md). Interior spring cold (Volga, Kazakh, prairies, BC -3.5 to -4.6 C in April): e138 radiation snowmelt neutral (S97 0.9999-1.0000; calibration/snowmelt_20261126). Both spring errors are regional with opposite signs.

**r57 ADOPTED (25 Nov 2026).** r56 + e91 warm-sea onshore inflow (inflow_gain 1.92, inflow_sst 26.5, inflow_km 567) + e134b plateau heating 3.52 (cell) with land_edge_rh 0.505, subsidence_branch_drying 0.370, monsoon_descent 0.0609, onset_gap_deg 3.87 (W15 refit, finalist w2_004 by dev objective). Gates vs r56: dev6 S97 0.9786 [0.9655, 0.9904], T -0.5 %, P -3.8 %, regimes tropical_wet 0.936, highland 0.933, tropical_dry 0.958, temperate 0.979, continental 0.989, mediterranean 1.004, arid 1.010; fine28 1.0015; sealed Y (opened once) S 0.9944 [0.973, 1.015] PASS. W15 note: an accidental extra propose ran 16 wave-3 points without their own 0.005 check; the finalist is a wave-2 point (W15_records/note.md). Params calibration/local_accuracy_20261023/r57_params.json, r57_adoption.json. Reference runs output/ppe_20261125/ref57/r57_<part> (screen_v6 with ref57 r57). Sealed Y SPENT; new set Z declared UNOPENED (calibration/sealed_20261126Z, 12 regions incl. coastal boxes, LAND_MIN 0.55; run as part sealed_Z vs r57). Atlas NOT rebuilt (remains r51). Open leads: east-coast spring land_eq 4-6 C hot (Japan, Nova Scotia; calibration/phase_20261125/notes.md), Sahara/Sahel moisture reach.

**e134b plateau heating = candidate component (25 Nov 2026).** plateau_heating 4 + plateau_heating_cell true (seasonal elevated heat source on broad extratropical plateaus) S97 0.9971 [0.991, 1.001] vs r56, highland 0.952, Tibet 0.81; one-region gain, so not refit alone: stack with the next win. calibration/plateau_20261125/findings.md. Interior rain line CLOSED (onset gap makes the Sahara wetter; its rain is large-scale saturation of transported water).

**Hot-tail / interior-rain probes under r56 PARKED (25 Nov 2026).** land_budget now has LB_MAX_ELEV and an observed_sl row (the old budget compared sea-level air with obs at elevation). e132 cloud_radiation (clear-sky sunshine) neutral-to-worse (calibration/cloudsw_20261125). Root blocker: deep tropical interiors get 36-53 % of observed rain (too clear, too warm), so any warming of clear dry land heats them too. Edge humidity fixes (e81 edge_inner, land_edge_rh, new e133/e133b edge_itcz_rh: land-edge inflow moistened near the model ITCZ) fix Congo/Amazon (0.55-0.9) but wet the Sahara/Sahel x1.5-3.5 through their southern edges; best S97 1.012. Needs a cap on the northward reach of monsoon moisture over hot land first. calibration/interior_20261125/findings.md.

**r56 ADOPTED (25 Nov 2026).** r55 + e131 maritime_mean 3.0 with maritime_mean_clip (lifts maritime land's annual mean toward the sea's: BC coast 0.844, British Isles 0.949, Pacific NW 0.940, Volga 0.957 vs r55). W14 refit (8 knobs incl. e129 pole_frozen_sea) found nothing better than its base; emulator best 0.9892 predicted < 0.005 gain so no wave 2. Gates: dev6 S97 0.9936 [0.9878, 0.9979], worst regime highland 1.002; fine28 1.0002; sealed X (opened once) S 0.9946 [0.980, 1.009] PASS. Params calibration/local_accuracy_20261023/r56_params.json, r56_adoption.json, W14_records/. Reference runs output/ppe_20261125/ref56/r56_<part> (screen_v6 with ref56 r56). Sealed X SPENT; new set Y declared UNOPENED (calibration/sealed_20261125Y, 12 regions, run as part sealed_Y vs r56). Atlas NOT rebuilt (remains r51).

**East-west continental dipole PARKED (25 Nov 2026, after r55).** r55's largest errors: eastern Canada / Okhotsk interiors too warm (+2-6 C, winter-autumn), western Canada / Volga / Kazakh / Krasnoyarsk / BC too cold (spring -3 to -7 C). Six levers screened vs r55 (e128 snow inversion, W12 refit closed after wave 1, land coupling, e129 winter-frozen sea in pole_land, e130 seasonal cold pools REJECTED, land_radiative_days 4): none beat r55; each trades east against west. All new options default off. Sealed X (calibration/sealed_20261125X, 13 boxes) UNOPENED for the next candidate vs r55. Most specific remaining lead: the west runs late (British Isles +20 d, BC +12, E Europe +8; phase_lag.py), i.e. task C4 maritime lag. calibration/inversion_20261125/findings.md. e129 needs data/cache/earth/frozen_sea_1deg.npz (scripts/make_frozen_sea.py from the WOA SST cache).

**r55 ADOPTED (25 Nov 2026).** W11 refit on es3 (e127 sea ice gated by sea air, band snow albedo replaced by cell snowpack) finalist w2_001 (dev objective only): dev6 S97 0.9889 [0.980, 0.996], T -2.0 %, P -0.2 %, every regime <= 1.000 (continental 0.972, tropical_wet 1.000); fine28 S28 0.997; sealed W13 (opened once) S 0.9953 [0.979, 1.013]: PASS. Params calibration/local_accuracy_20261023/r55_params.json, record r55_adoption.json, W11_records/. Reference runs output/ppe_20261125/ref55/r55_<part> (use these as the paired reference now; screen_v6 with ref55 r55). W13 SPENT. Atlas NOT rebuilt (remains r51). NEXT: new sealed set needed before the next adoption (mid-latitude 300 km boxes exhausted; consider southern/maritime/tropical boxes at 200 km); structural leads: Ungava summer land_eq too hot, BC/NE Pacific sea too warm in summer, maritime seasonal range.

**Sea ice e127/e127b + sealed W13 (25 Nov 2026).** New sealed set calibration/sealed_20261125W13 (13 x 200 km
NH mid-latitude boxes; 300 km boxes exhausted) declared UNOPENED for the next candidate against r54. e127 sea ice
(air over a freezing sea relaxes to min(land eq, 0 C)) gated by the air over the sea (e127b sea_ice_air_c -5):
S97 0.9940 [0.9836, 1.0000] vs r54, continental 0.973, all others 1.000 (Ungava 5.20 -> 3.53 C); carry into the
next candidate. Next lead: band snow albedo (ebm_land_ice) delaying maritime springs (screen_eli.log).
HAZARD: never copy the WOA cache into data/cache/earth while a screen runs: cases pick up WOA sea depth and the
paired-geography check fails (ig5m60 lost once). calibration/seaice_20261125/findings.md.

**r54 ADOPTED (25 Nov 2026).** plan_W10 closed after wave 1 (49 runs, emulator LOO 0.0006, predicted best
~0.976 vs observed 0.9780: < 0.005). Finalist = base point ho40r8 (mw70l25 + sst_damping 0.4 full at 55 deg,
e126 sst_damping_heat_only, land_radiative_days 8). dev6 S97 0.9780 [0.965, 0.990], T -3.2 %, P -1.2 %, regimes
<= 1.005 (temperate 1.002, mediterranean 1.005); fine28 S28 0.998 (W Europe 1.85 -> 1.65 C); sealed V18 (opened
once, declared first) S 0.951 [0.921, 0.976], T -4.2 %, P -5.6 %: PASS. Records
calibration/local_accuracy_20261023/r54_adoption.json, r54_params.json; reference runs output/ppe_20261124/ref54
(r54_<part>, incl. fine28). V18 SPENT. Atlas NOT rebuilt (remains r51). NEXT: (1) a new sealed set must be
declared before the next candidate (mid-latitude boxes exhausted; consider a coarser or re-padded mid-latitude
set); (2) maritime seasonal range is narrower under r54 (28 km W Europe range error -1.69 -> -2.68 C, NZ -1.24 ->
-2.94) while phase improves: next structural target; (3) boreal autumn warmth.

**Maritime lag diagnosed; plan_W10 (now closed -> r54) (24 Nov 2026).** e125 (maritime continentality slope) and land
coupling alone leave the westerly-coast lag (+19..+33 d) in place. Stage breakdown (land_budget.py, new sst tap):
coastal air ~95 % sea air in winter, and the regional sea ~2x over-seasonal and 4-6 C cold in winter; the two
compensate (observed SST makes British winters +4 C). 97-region screen on mw70l25: sd40 0.9829, sd40r8 0.9797,
ho40r8 0.9780 [0.965, 0.990] (sst_damping 0.4 to 55 deg, e126 sst_damping_heat_only = moisture keeps the
undamped sea, a compensation for rain fitted to the cold sea; land_radiative_days 8). plan_W10 declared on
ho40r8 (8 knobs incl. land_amplitude, continentality for the fine28 range failure mode), finalist by dev only.
calibration/range_20261124/findings.md.

**PPE plan_W9 CLOSED, no adoption (24 Nov 2026).** Base mw70l25 (e124), 8 knobs incl. land_offset and the
maritime shift, 49 runs, emulator LOO rmse 0.0003, predicted optimum 0.9787 vs observed 0.9808 (< 0.005 gain),
closed after wave 1. Finalist chosen on dev only: w1_011 (land_offset -1.97, maritime_mean 0.88 from 20 deg,
lw_ref_rh 0.82): S97 0.9808 [0.964, 0.998], T -2.6 %, P -1.3 %, worst regime mediterranean 1.015: PASSES dev6.
FAILS fine28 once: S28 1.0173, T +2.4 %. V18 still UNOPENED. Diagnosis: the fine loss is the seasonal RANGE
(California range error -0.57 -> -1.09 C, NZ -1.24 -> -1.55), and r53 already under-swings every maritime
mid-latitude region (W Europe -1.69, Japan -1.33, dev British Isles/Patagonia/Alps -1.0..-1.4) and lags it
(+20-43 d). Next: e125, a separate maritime-side continentality slope (continentality_maritime, default 1 = off),
screening in calibration/range_20261124. Records calibration/ppe_20261123/W9_records.

**e123 maritime finalist FAILS fine28 (24 Nov 2026).** W8 finalist + maritime_mean 0.7 with e123 mid-latitude
gate (maritime_mean_lat 25): S97 0.9809 [0.967, 0.994], every regime <= 1.009, T -2.5 %: PASSES dev6. fine28
1.0165: California and NZ (cold-current coasts) cooled and over-damped. V18 UNOPENED. e124 one-sided shift
(maritime_mean_warm_only): S97 0.9819 [0.970, 0.994], worst regime 1.005, fine28 1.01007 = FAIL by 0.00007; the
residual is the W7/W8 global land cooling hurting California/NZ. calibration/maritime_20261124/findings.md.

**PPE plan_W8 CLOSED, no adoption; W7/W8 lineage SPENT (24 Nov 2026).** W8 = the one allowed continuation of W7:
W7 neighbourhood + e122 (continental_depth faded over high ground, gate 1,000 m), 7 knobs, 49 runs, emulator
LOO rmse 0.0003, predicted optimum 0.9848 vs observed 0.9858 (within noise), closed after wave 1. Finalist
w1_023: S97 0.9858 [0.974, 0.998], T -1.8 %, P -1.0 %, worst regime mediterranean 1.014: PASSES dev6. FAILS
fine28: S28 1.0115 (> 1.01), T +2.8 %; all four fine regions (California, W Europe, Japan, NZ) cooler and
worse except Japan. V18 still UNOPENED. The tropical gain comes with a global land cooling (land_offset ~-1.6)
that the maritime mid-latitudes pay for; the next refit needs a structural fix for maritime mid-latitude land
(late phase +20-43 d, cold) rather than more tuning. Records calibration/ppe_20261123/W8_records.

**PPE plan_W7 CLOSED, no adoption yet (24 Nov 2026).** 65 runs; emulator LOO rmse 0.0011, predicted optimum
0.9866 vs observed best 0.9872 (inside noise), so closed after wave 1. Finalist w1_049 (lw_ref_rh 0.90,
cloud_longwave 0.257, dry_heating 1.48, land_offset -1.59 [at bound], wet_sun 2.43, subsidence_warming 6.77,
dry_coupling 1.78, continentality 0.42): S97 0.9872 [0.972, 1.002], T -1.4 %, P -1.2 %, worst regime temperate
1.017. FAILS dev6 (upper bound 1.002 >= 1). Wins: wet tropics cooled (tropical_wet 0.918). Losses: every
cold-biased region cools further (Alps, BC coast, Sahel, prairies). Params output/ppe_20261124/W7/w1_049_params.json.
Diagnosis (calibration/land_lag_20261124): annual-harmonic phase lags +20-43 d in maritime temperate (NZ,
British Isles, Patagonia, W Europe, S Chile), ~+5-10 d continental, -5 to -8 d arid; boreal Canada/Siberia
autumn-winter 5-9 C too warm. Observed SST does not remove the maritime lag. land_heat_capacity 0.4 cuts inland
lag ~10 d and 6-region T MAE 2.01 -> 1.68, but on 97 regions land_heat_capacity 0.7/0.5/0.35 gives S97
0.994/1.024/1.058 (with amplitude compensation 0.996/1.027) and e121 land_phase_days (+-20, 40) 1.02-1.10: PARKED.
calibration/land_lag_20261124/findings.md. e120 lw_ref_rh stays the W7 base.

**Boreal screen (24 Nov 2026): noise.** continental_depth 0.5 S97 0.9877 (continental 0.982, highland 1.046),
0.75 1.0017; snow_albedo 0.32 0.9874. calibration/boreal_20261124/findings.md.

**POLICY v6 IN FORCE (24 Nov 2026, owner: "update the policy").** calibration/local_accuracy_20261023/policy_v6.json.
Dev pool 97 = v5's 61 + spent S18 + spent U18; adopt if S97 90 % upper bound < 1, T/P <= +1 %, every regime
(regimes_v2.json, observed-climate Koppen tags) point S <= 1.02, fine28 <= 1.01, ONE sealed V18 run (sealed5).
Tools: scripts/gate_v3.py dev6, scripts/screen_v6.py (prints per-regime S). r53 refs: output/ppe_20261124/ref53
(r53_sealed_S18 run 24 Nov; r53_sealed_U18 -> e110_l25 candidate).

**B6 PARKED (24 Nov 2026): southern-tropics onset.** e118 (wind gate) fails; e119 (poleward desert, + e117 max) best 0.998, noise. The e93 convection cap (Saharan dry layer) delays the southern
Amazon's spring rain 1-2 months (the +3-5 C). Gate off: Amazon/Brazil 0.72-0.79 but Sahel/Sahara/E Australia
1.56-1.72 (S61 1.033). e117 (cap x dry-land air share) is circular, no gain. Needs a non-soil discriminator
(static geography or the subsidence field). calibration/onset_20261124/findings.md.

**Deep-root store PARKED (24 Nov 2026).** e114 at low thresholds (p0 500-700): S61 1.0007-1.0087, noise or
worse; cools cold mid-latitude wet lands. Southern Amazon wet season starts ~2 months late and ends 1 early (real
Sep-Oct 0-8 mm vs 84-139 obs): the +3-5 C pre-onset heat is a rain-onset error. calibration/root_store_20261124.

**PPE plan_W6 CLOSED, no adoption (24 Nov 2026).** Observed lateral column water (e116 edge_obs_pw, NCEP PW) +
physics refit, 8 knobs, 81 runs. Finalist w2_004 S61 0.9940 [0.983, 1.004] (T +1.0 %, P -2.2 %) FAILS dev5 (upper
bound >= 1). The fit keeps only 0.36 of the observed edge; arid T still 2.5 % worse. The southern-tropics warm bias
is internal (land-surface energy balance), not edge moisture. r53 stays; sealed V18 still UNOPENED; edge_obs_pw
default 0. Records calibration/ppe_20261123/W6_records.

**Interior moisture PARKED (24 Nov 2026).** Southern-tropics warm bias = rain deficit (S Amazon 750 vs 1,900 mm;
column water half observed): their sea is beyond the map, water enters at land_edge_rh 0.5. More edge moisture
helps the Amazon/Congo (0.75-0.88) but floods steppes/deserts; e115 (zero-gradient edge on warm wet ground only)
nets 0.9985 [0.992, 1.004] - noise. e114 (root depth) no effect. Owner decision proposed: observed lateral
humidity for Earth regional cases. calibration/edge_moisture_20261124/.

**B5 hot-land bias PARKED (24 Nov 2026).** Northern dry tropics/subtropics too cold (-1 to -2.6 C), southern
short-dry-season tropics too warm (+1.3 C mean, 5-20 S). Dry heating (+ e113 cold-sea exemption, + arid gate)
stays within 1.0006-1.019 of r53: no adoption. Lead: a deep-root forest water store. calibration/hot_bias_20261124.

**PPE plan_W5 CLOSED, no adoption (24 Nov 2026).** e112 (mirror itcz_mean for southern Earth regions) + 6 ITCZ
knobs: base 1.109, best of 65 1.0245, emulator (LOO 0.002) predicts nothing below 1.34 with penalties. One land
ITCZ can't serve both the Sahel and the southern tropics. e112 default off. Sealed V18 DECLARED, UNOPENED
(calibration/sealed_20261124V18; all 18 boxes within 23 deg of the equator). Records ppe_20261123/W5_records.

**Lead B4b (24 Nov 2026): itcz_mean is not mirrored for southern Earth regions** - the rains end 1-2 months late
there (Zambia April). Ocean-only flip fixes the tail but weakens the wet peak; needs a joint refit of the land ITCZ
range (PPE). calibration/itcz_mirror_20261124/findings.md. r53 at pad 2200 (13 regions): neutral (Congo rain loss
0.28 -> 0.32, Namibia 1.01 -> 1.04), calibration/e110_20261124/r53_pad2200.txt.

**r53 ADOPTED (24 Nov 2026, policy v5, NO atlas rebuild): calibration/local_accuracy_20261023/r53_params.json** =
r52 + e110 (subsidence_branch_gate_winter 1.0, subsidence_branch_gate_lat 25). Cause (B4): the e70c rain gate
(no dry descent where it rained) locked false dry-season rain on winter-hemisphere tropical land (Zambia 50-106
mm/mo vs obs 2-11). dev5 S61 0.9836 [0.9686, 0.9965] T 0.0 % P -3.3 % S49 0.9957; fine28 0.99997; sealed U18 (now
SPENT) S 0.9873 [0.968, 1.002] T +0.9 % P -3.4 %. Regimes: tropical_dry 0.943, rest ~1.00. Records
calibration/e110_20261124/, r53_adoption.json. Reference runs for r53 on the v5 pool = candidate_* in
output/ppe_20261124/screen/e110_l25 (ignored output). No unopened sealed set remains: declare a new one before
the next finalist. Somalia stays wrong (onshore trades; heat lows off its regional map, see east_africa findings).

**PPE plan_W4 CLOSED, no adoption (24 Nov 2026).** e52c (land_stable_barrier_*: extra stable-layer cooling where an
upwind crest within ~800 km rises above the cell) + 8 neighbours, 81 evaluations. Best = declared base r52+e52c 0.3:
S 0.9978 [0.9940, 1.0015], fails v5 upper-bound gate; wave 2 best 0.9991. e52c cuts pad-2200 error 4.5-7.7 % (fixes
the prairie warm drift A1 found) but is flat at pad 1100. Code kept, off by default. Adopting it needs a scoring-domain
change (pad-2200 gated set) = owner decision. Records calibration/ppe_20261123/W4_records/. r52 stays; U18 UNOPENED.
Next: plan B2-B5.

**Plan 20261124 approved; A1 + A2 DONE (24 Nov 2026).** A2: frozen observed-climate regimes for 79 regions
(calibration/regimes_20261124, scripts/regimes.py score): r52's gain over r51 was all tropical-dry (0.947) and arid
(0.972); highland 1.014, mediterranean 1.006. A1 (calibration/map_edge_20261124): doubling the map pad changes r52's
scores by ~12 % (prairies T_mae 2.6 -> 4.7 -> 5.3 C at pad 1100/2200/3300; not converged): westerly marine heat crosses
the Rockies too freely once the Pacific is on the map. The atlas uses the same 1,100 km pad (not a whole world), so
calibration stays at pad 1,100; A4 dropped; pad 2,200 on 12 regions becomes a robustness diagnostic for B1. Next: B1.

**East Africa / Somalia rain diagnosed, e109 PARKED (24 Nov 2026).** Southern Somalia (S18) rains 3,800 mm/yr
against 460: the e55 Somali-jet turning is gated on a poleward pressure fall that the 2,500 km region map cannot
see (heat lows off the map). e109 monsoon_westerly_floor (default 0) fixes the wind partly but S61 1.025 / 1.004
(floor 1 / 0.5): Sahara, Sahel, east China lose. See calibration/east_africa_20261124/findings.md. Next: soil-moisture
limit on tropical land evaporation (Somalia E ~70 mm/month all year).

**PPE plan_W3 CLOSED, no adoption (23 Nov 2026).** 81 evaluations over dry heating (e54), terrain-blocked eddy mixing
(e100c) and five rebalancing knobs around r52. Best w2_013 S61 0.9986, within noise; best points switch dry heating
nearly off. Regional gains in the dry subtropics and South Asia are cancelled by Namibia, Chile and the Central Asian
basins. Records: calibration/ppe_20261123/W3_records/. r52 stays; U18 UNOPENED. Next lead: southern-tropical land rain
onset and strength (Congo s_0s_28e).
# developing instead of rebuilding". The 'every adopted climate gets a full rebuild' standing instruction is RETIRED.
# Adopt climates on the gates as before, but do NOT rebuild the atlas unless the owner asks. r51 rebuild (already running
# when this was said) is finished lean: commit atlas + short report, no extra packaging work.

# r51 ATLAS LIVE (22 Nov 2026): rebuild done, browser checks pass, reports/RELEASE_R51_20261122.md. No Claude copy (owner).
# C1 NEXT: sealed set s declared UNOPENED (calibration/sealed_20261122s). e105 rain-cloud shading (rain_shading, _mm) and
# e105b (rain_shading_wet_pow, wet-all-year gate) in code, default off; screens vs r51 with scripts/screen_v4.py in
# output/cloud_shade_20261122 (ref = refit_T3 j37 runs). e105 alone: 1.5 K S55 0.997 / S49 1.008; 3 K S55 1.003 / S49
# 1.021 (Amazon +1.6 -> +0.15 C but Sahel/Burkina/N India/Bengal colder). joint_refit.py has objective_mode 'v4'.

# C1 22 Nov late: e105/e105b (rain shading) and e106 (land ITCZ mean) PARKED, default off; findings in
# calibration/cloud_shade_20261122/findings.md. Sealed s still UNOPENED. Leads: (1) southern-tropical land rains arrive ~2
# months late and half-strength (S Amazon, S Congo) - moisture supply/onset, not the belt latitude; (2) Najd/Sahel/Deccan
# 4-6 C too cold in their hottest months even under full subsidence warming - check the land equilibrium there;
# (3) Kenya-Tanzania coast rains all year (~200 mm/month in the dry season, obs ~10).

# SOUTH ASIA (24 Nov): Ganges plain 3.5 C too cold all year under r52. e108 heat barrier, e100b/e100c relative eddy
# terrain weighting tried (default off), best e100c S61 0.9994 = neutral -> PARKED. See calibration/south_asia_20261124/
# findings.md. Next lead there: the local column's pre-monsoon cold (Apr -2.7 C on the plain, Deccan -3 C Jan-May).

# PPE plan_W2 (around r52, wider taper/cap_land, W1 runs imported) CLOSED: best 0.9990 -> r52 is the optimum of the 16
# knobs; next gains need structure (calibration/ppe_20261123/W2_records/verdict.md). Sealed U18 (calibration/
# sealed_20261124U18) declared and UNOPENED for the next adoption.

# r52 ADOPTED (23 Nov 2026, policy v5, NO atlas rebuild - owner rule): calibration/local_accuracy_20261023/r52_params.json,
# r52_adoption.json. PPE W1 (scripts/ppe.py, 145 runs: Sobol 97 + 3 emulator waves of 16; emulator LOO rmse ~0.001) finalist
# w4_000: S61 0.9886 (90 % CI 0.979-0.998, T -1.4 %, P -0.9 %), S49 0.9998, fine28 0.997, sealed S18 0.958 (T -5.4 %,
# P -3.0 %) -> S18 SPENT. Changes: subsidence warming stronger (6.2) and on land starts closer to ITCZ (gap_land 1.39,
# floor 8.2 deg), taper 20, wet_sun 2.0, dry_coupling 2.0, cap_land 5.0. Records calibration/ppe_20261123/.
# Leads: taper (20) and cap_land (5.0) sit on their box edges -> next PPE should widen them; S49 0.9998 is at the guard,
# so mid-latitude regions are flat (Canadian prairies, Tibet worse by ~3 %); Congo s_0s_28e rain worse. Atlas still r51.
# A NEW sealed set is needed before the next adoption.

# POLICY v5 IN FORCE (23 Nov, owner approved): calibration/local_accuracy_20261023/policy_v5.json. Dev pool 61 (dev49 + t +
# spent r); adopt if 90 % bootstrap upper bound of S61 < 1 (gate_v3.py dev5), T/P <= +1 %, S49 <= 1, fine28 <= 1.01, ONE run on
# the 18-region sealed set calibration/sealed_20261123S18 (s + s2 + s3, unopened; gate_v3.py sealed5: S <= 1, 90 % lower < 1).
# Evidence: calibration/methodology_20261123/score_uncertainty.md. Calibration now by scripts/ppe.py (PPE + GP emulators):
# plan calibration/ppe_20261123/plan_W1.json (16 knobs around r51, wave 1 = 97 points, then emulator waves of 16).
# plan_U3 (e107 coordinate refit) is judged under v5 and may not use S18 unless it passes dev5.

# AUTONOMOUS WORK PLAN — owner approved 21 Nov 2026 ("write it down as a list of tasks for you to follow autonomously and keep
# going"; paste every map/graphic into the chat). Work in order; each Earth test declared before scoring; adopt only on pass.
* T1 Finish the r50 atlas rebuild: select_world_r50.py + r50 corrections -> scripts/release_r50.sh -> browser checks ->
  package -> Claude copy -> reports/RELEASE_R50_20261121.md, HANDOFF, push.
* T2 Mexico monsoon circulation (biggest known climate error): new sealed set q first; summer trades over land (trade_land)
  so Gulf air reaches Mexico; screen -> refit -> policy_v3 vs r50; if adopted, full rebuild again (standing instruction).
  Also re-check equatorial interiors (too dry) and rain shadows.
* T3 River runoff AMOUNT vs GRUN (timing already validated; amount ~0.4 of observed): blind checkerboard test.
* T4 Grazing capacity (uncalibrated clip(T/15)*P/(P+50)) vs GLW livestock density and MODIS NPP on non-crop land.
* T5 Travel costs (forest/relief/water, hand-set) vs Stanford ORBIS Roman route times; blind route split.
* T6 Crop yields vs FAO GAEZ low-input rainfed yields; blind split.
* Not planned: malaria population penalty (needs the dropped population-history line).
* Owner 21 Nov: "I don't care about keeping data sets blind" -> fit on ALL Earth data, keep only cross-validation; sealed sets
  no longer required for settlement/population work. Population total is NOT supplied: food capacity x occupation ratio
  (median 0.32 of 10 AD 1-200 regions, data/settlement_reference_regions.json; ratios span 0.03-1.0) x lore heartland weight.
  Queue after T7 (suggested order, owner may reorder):
  - T8 Occupation ratio as a fitted field (state age / distance to old cores, malaria, herding) on all Earth regions: ~100 Han
    commanderies (Zheng & Wu), the 10 reference regions, HYDE 200, Domesday. Replaces the single median.
  - T9 Nomads: N1 nomadic/seminomadic probability from Ethnographic Atlas EA030 (data/cache/dplace_ea; ~110 mobile of ~700 in
    window) vs growing season, aridity, rain reliability, winter cold, with herd animal EA040; N2 nomad density from GPP-tested
    forage vs historical steppe estimates, own term in the population ledger; N3 seasonal circuits from monthly forage vs
    documented migration lengths; N4 steppe confederations in the control map vs Cliopatria nomad polities.
  - T10 Town sizes/primacy fitted on all city data (Hanson, Buringh, Mesopotamia, Valley of Mexico, Reba/Modelski).
  - T11 Villages (Domesday + Roman rural Britain); T12 control map refit on all pools; T13 grazing allowance refit.
  - Trade stays untested (no target data).
* PROGRESS 21 Nov 16:20 UTC:
  - T2: PARKED. e95 (summer western flanks of the ocean highs) and e96 (no westerly turning in the plateau-anchored band) both
    FAILED their screens; Mexico is unresponsive to wind fixes. Set q unopened. calibration/monsoon_circulation_20261121/findings.md
  - T3: ADOPTED. Budyko-Fu w 2.6 annual runoff, blind log error 0.872->0.657; reports/RUNOFF_AMOUNT_20261121.md.
  - T4: ADOPTED. Forage phenology span 20 C, rain half-saturation 100 mm, 1-month rain memory; blind r 0.837->0.890;
    reports/FORAGE_SEASON_20261121.md.
  - T5: DROPPED. ORBIS land times are its authors' fixed mode speeds, not observations; calibration/travel_orbis_20261121.
  - T6: current VALIDATED, no change (G1 fails; blind wheat 0.76). Open finding: wheat and barley grow in the hot humid tropics.
    reports/CROP_YIELD_GAEZ_20261121.md
  - T1: DONE 21 Nov 18:50 UTC. r50 atlas promoted, browser checks pass, Claude copy v19; reports/RELEASE_R50_20261121.md.
  - T7: DONE 21 Nov ~21:30 UTC. Fu runoff + GPP grazing seasons + r5 town-size fit, full rebuild; browser checks pass;
    reports/RELEASE_R50_T7_20261121.md. Claude copy v21, all 84 layers x 2 climates load. Next: T8.
  - T8: DONE, level KEPT by owner. Occupation field M1 (1.42 exp(-D/811 km)) beats the single ratio in CV (0.813 vs 1.050)
    and confirms the 800 km heartland shape, but applied with the 7 lore cores it gives 125 M; owner chose to keep 50 M.
    calibration/occupation_field_20261121/findings.md. Next: T9 nomads.
  - T9 N1: ADOPTED. Pastoral nomads = logistic of the herding share (OOF AUC 0.92, 632 EA societies); new layer
    land_nomads (scripts/nomads_layer.py, in the release after herding). Map max ~0.30: no Earth-like nomad belts.
    N2-N4 deferred (little nomad land). calibration/nomads_20261121/findings_n1.md. Claude copy v22. Next: T10.
  - Side project (two targets: painted Med zone Cs + cold-dry nomads), STOPPED by owner before the ds8 check.
    Search (241 evals, ds32): med_cs 0.75 -> 1.00, cold-dry nomads 2.8% -> 2.3% (max any world 4.4%).
    Not adopted. calibration/two_target_20261121/, scripts/two_target_world.py.
  - C1 climate (owner: iterate on the climate model autonomously): sea-profile line PARKED. WOA shows r50's regional sea
    ~3 C too cold and 2-5x too seasonal; EBM refit (S49 1.281), e98 sea-only damping (1.097 -> refit 1.082) and e98b
    joint rain+sea refit (1.024) all FAIL; the search pulls the sea back to r50. Kalahari dry-margin diagnosis parked.
    calibration/sea_profile_20261122/findings.md, calibration/dry_margins_20261122/findings.md. Sealed q unopened.
    Then (22 Nov, all FAIL, r50 stays, sealed q unopened): gated dry heating re-test on r50 (best S49 0.9989,
    calibration/dry_heat_r50_20261122); e98c sea swing damping alone (0.9979; T -1.1 % but coastal rain +0.7 %).
    BC coast winter (-7 C, worst T region) diagnosed: not the sea (open sea too warm), continental offshore winter air;
    e100 terrain-weighted eddy heat STOP (S49 1.078: East Asia +1.3-1.8 C); e101 directional damming probe ~0 (reverted).
    Remaining large errors sit in the latitude-mean land equilibrium itself (BC winter, North India/Deccan/Najd all year,
    East Asia warm): calibration/maritime_winter_20261122/findings.md.
    e102 tropical-only sea warming + heat-low inflow (calibration/warm_season_inflow_20261122): dev49 PASS 0.9925
    (T -1.0 %, P -0.5 %) but fine28 FAIL 1.0112 (California wetter, Japan T): not adopted, sealed q unopened.
    Closest candidate of the campaign; e102 code kept (default off).
    plan_C (e102, global rain settings frozen): dev49 0.9916, fine28 1.0064, then sealed set q 1.065 FAIL (eastern
    Brazil hotter and +330 mm wetter on +1400 already; Air +26 mm on +415): NOT adopted; sealed set q SPENT. A fresh
    sealed set is needed for the next finalist. dev49 lacks tropical South America: consider adding it when drawing.
    New sealed set r drawn (calibration/sealed_20261122r, UNOPENED) and open tropical set t (calibration/
    tropical_check_20261122t; r50 tropics 1.2-1.9 C too warm, Maranhao coast 5165 mm vs 1991, Amazon interior starved).
    plan_T1 global convection refit FAIL 0.9987 (tropics trade against dev49). Cause found: the e93 chi gate treats
    wet-forest air as desert air aloft. e103 (gate on dry-land chi, default off): S_t 0.916 at dev49 1.0008; refit
    plan_T2 best dev49 0.9992 FAIL -> parked. dev49 cannot credit a tropical-only fix: OWNER DECISION whether set t
    should join the dev objective (policy v4). Maranhao coastal deluge (20-24 mm/day Nov-Apr) still open.

# CLIMATE r50 ADOPTED on Earth (21 Nov 2026) — reports/CLIMATE_R50_20261121.md  [current best]
* e93 (heated-land convection threshold, gated by belt and desert air) + e94 (monsoon descent caps convection). vs r49: dev49
  0.9854, fine28 1.001, sealed set p 0.922. Sets o and p SPENT (o failed e93 alone). Atlas still on r49 -> rebuild next
  (owner standing instruction: latest Earth calibration in full). Open: Mexico circulation (trade_land, belt at 30 N).

# FULL REBUILD ON r49 — owner (20 Nov, away): "do the full rebuild ... handle it yourself ... keep going until you're done"
* OWNER OVERRIDE (20 Nov): "Use the latest model in full, even if the zone agreement falls. Earth calibration is the most
  important" + "Are you also checking the planetary parameters ... How about the offmap land? Be comprehensive".
  -> The zone-agreement decision rule below is VOID. The atlas is rebuilt on FULL r49 physics. Painted-zone agreement is
  reported, never a gate.
* Plan (21 Nov):
  W3 world refit on full r49 (calibration/map_world_r49_planet/plan.json; scripts/world_campaign_r49.py search; log
  output/rebuild_r49_20261120/w3.log): world genes + planet levers + off-map land, guarded zonefit, 241 evals, ds32.
  Selection per plan (native ds8 check vs the r49 start). The physics stays r49 regardless.
  Earth corrections retrained for r49 (scripts/retrain_earth_corrections.sh -> calibration/earth_correction_r49_20261121).
  Then base build -> corrected climate -> harvest (malaria rule) -> population -> all add-ons -> settlement chain
  (release 3/4, provisional r5) -> browser checks -> Claude copy.
* [DONE 21 Nov] W3 world refit on full r49: 241 evals, best zero-penalty coarse zonefit 0.212 (start 0.168). Native ds8 check
  (scripts/select_world_r49.py; calibration/map_world_r49/selection.json): refitted world (eval 231) zonefit 0.206 vs start 0.169,
  strict agreement 35.9 % vs 29.0 % (r44 atlas 32.4 %) -> SELECTED (calibration/map_world_r49/params.json; checkpoint
  output/r49_world/candidate_001.pkl, ignored). Changes: tilt 33.5 -> 24.7, solar 1.000 -> 1.039, greenhouse -0.5 W/m2,
  eccentricity 0.017 -> 0.009, lat_center 38.5 -> 41.3, north bearing -8.8 -> -3.7, ebm_land_scale 0.82, off-map land up on all
  sides (NE 0.01 -> 0.61, W 0.33 -> 0.64, S 0.72 -> 0.98), off-map relief 176 -> 51 m.
* [DONE 21 Nov] Earth corrections retrained for r49 (calibration/earth_correction_r49_20261121, force-added): cluster-CV
  temperature 1.494 C (r44 1.506), rain loss 0.4238 (r44 0.4318).
* [DONE] per-polity herding statistics use the adopted growing-season rule (polity/herding.py); forest-in-travel on in the driver.
* [DONE 21 Nov] ATLAS REBUILT ON r49 AND PUBLISHED — reports/RELEASE_R49_20261121.md. Base (scripts/release_r49.sh) ->
  add-ons -> settlement release 4 on r49 (calibration/settlement_chain/release4_r49.json; publish_release4.sh; release4_reach_chain.sh;
  admin/hierarchy on release-4 towns via run_on_release3 + scripts/move_release3_admin.py) -> pages (refresh_atlas_pages.py then
  scripts/enable_release3_page.py) -> accuracy (publish_current_earth_r49.py) -> hub. Browser: smoke + 8 release checks pass.
  Claude copy v15 (https://claude.ai/artifact/XypoZqva951RWZm4ni6FiP): 219 files, 191 MB; 84 layers x 2 climates checked.
  Headlines: people 51.4 M corrected (r44 54.0), towns 984/1,017 (r44 1,034/1,053), strict zone agreement 35.9 % (r44 32.4).
  Fixes: forest-in-travel added to scripts/prepare_settlement_feedback.py and scripts/settlement_fantasy_inputs.py.
* [DONE 21 Nov, owner "OK do that"] (a) presence/mobility now uses forest in travel (layer rebuilt); (b) scripts/release_r49.sh is
  ONE command for the whole rebuild (base -> add-ons -> settlement release 4 chain, staged reach, reach variants, release-3 admin,
  pages, accuracy, hub). In-place files are backed up/restored (no git checkout). Every step ran individually on 21 Nov, but the
  consolidated script has NOT been run end-to-end yet; for a new physics release copy it, change PHYS/WORLD/CK/CAL/REPORT/NOTE.
* [DONE 21 Nov] Monsoon peak investigation — calibration/monsoon_inflow_20261121/findings.md. Resolution ruled out (14 km no
  better), e91 warm-sea inflow FAILED its screen (Najd/Sahel guards), observed SST barely helps. Remaining lever: the rain-production
  law (heating-driven convection at moderate RH; less rain from cold saturated columns). e91 code stays (default off). Owner
  decision before more climate physics; sealed set o still UNOPENED.
* [DONE 21 Nov, owner "Let's try"] e92 heating-dependent convective threshold over land: screen FAIL (Najd 1.02-1.15, Sahel
  1.03-1.11 while Mexico/Bengal gain <= 4 %). CLIMATE PARKED AT r49 (declared rule). e91/e92 code stays, default off.
  Pattern and the only remaining idea: findings.md item 5. Sealed set o still UNOPENED.
* [RUNNING, owner "Keep trying, keep going until we get it"] e93 = e92's land threshold drop gated by the e86 belt ramp and the
  desert-air share chi (calibration/monsoon_convection_20261121/plan_e93.json). Screen D PASS at heat 0.3 (target 0.948; Sahel
  0.873, Bengal 0.926, Najd 0.993). Stage B joint refit running: refit_e93.json -> output/monsoon_convection_20261121/refit
  (reference r49 = output/monsoon_convection_20261121/ref symlinks). Then policy_v3 gates; sealed set o ONCE.
* [DONE 21 Nov] e93 refit best j24 (heat 0.31, chi0 0.675, convective_rh 0.708, convective_rain 0.537, onset_gap 4.125):
  dev49 PASS (S 0.9914, T +0.07 %, P -1.8 %), fine28 PASS (1.003), SEALED SET o FAIL (S 1.040, P +8.8 %): Oman/Dhofar box
  (17N 53E) 4.20 -> 5.18 — r49 already rains a false monsoon there (245-259 mm Jul-Aug, obs 6-10); e93 doubles it. NOT ADOPTED;
  set o SPENT. Lesson: sea air off a COLD upwelling sea (Somali jet, Oman) is stable; e93's gates (belt, desert air) miss it.
  Next: draw sealed set p first, then e94 = e93 + source-sea temperature gate (and/or fix the false Oman monsoon itself).
* Next lead (Mexico barely moves under e93): scripts/monsoon_trace.py shows Mexico's air counted as land-crossed (chi 0.63-0.86)
  under monsoon WESTERLIES all summer: trade_land = 1.0 removes summer trades over big land masses (no Gulf of Mexico easterly
  supply) and the plateau-anchored belt (e85) puts Mexico on the westerly side. A circulation fix, separate experiment. WOA18 SST cache rebuilt (data/cache/earth/woa18_sst_1deg.npz).
* [OPEN] Provisional r5 NOT carried over: frozen r44 cohort (plan says no climate update; prepare_urban_candidate_control.py and
  successors pin the r44 publication). Absent from the r49 atlas and Claude copy; kept in git history + GPT site. Rebuilding on
  r49 = new cohort declaration + removing r44 identity pins in ~12 scripts (owner decision whether worth it).
* [OPEN] Superseded experiment layers not recomputed (absent). Presence/mobility built without forest-in-travel (no hook).
* Superseded text below (kept for history):
* CORRECTION FIRST: earlier map checks of r46-r49 merged only SPACES['e3'] physics (dropped e85-e87 and the r45/r46 additions).
  Full-physics check (earth_physics_on_map.py --since r44): r49 strict 31.0 % vs r44 32.4 % (warm wet 22 vs 34). The owner's
  rebuild decision rested on the wrong +2.6.
* DECISION RULE (fixed before the zone fit result): the release procedure refits the map world to the painted zones
  (build_atlas_variant --fit-objective zonefit). r49 (or r47/r48 if better on the full map check) replaces r44 on the atlas
  ONLY IF its zone-fitted strict agreement >= 32.4 %. Otherwise the atlas stays on r44 and the rebuild still carries the
  malaria rule, forest-in-travel and herding stats on r44.
* RESULT (full physics, existing fitted world, ds8): r47 31.7 %, r48 31.2 %, r49 31.0 % — all below r44's 32.4 % -> the
  ATLAS STAYS ON r44 (rule + r46 precedent). Amendment to the rule's wording: build_atlas_variant's --fit-objective only
  labels the score; no zone fit is part of a release (r42-r44 kept the fitted world); a world refit is a separate campaign
  (r41's W2 found none) and was not started unasked.
* Rebuild continues on r44: malaria rule (harvest -> population -> every add-on), forest-in-travel C2, herding stats.
  Working in place (local atlas under git; revert = git checkout atlases/); hosted copy updated only at the end.
* [IN PROGRESS, WIP COMMITS] malaria v2 switched on (harvest/export.py + data/malaria_model.json active); harvest/population
  re-exported raw + corrected (corrected via stage_atlas + fingerprint patch); forest + herding layers re-added; land_malaria_v2
  retired (main malaria layer is now the validated rule). Add-on driver scripts/release_r44_malaria.sh running
  (output/rebuild_r49_20261120/stages_done). UNTIL IT FINISHES the atlas's harvest-bound add-ons (21 manifests) may be hidden.
  Next: settlement chain (release 3/4) build from the top, downstream reach/trade/control, provisional r5, browser checks,
  Claude copy. Superseded experiment layers (release2, dispatch, seeded dispatch, feedback, network visits x2, year-complete,
  food-checked visits) stay bound to the old harvest -> hidden by the page; recompute on request.

# CLIMATE r49 ADOPTED on Earth (20 Nov 2026) — reports/CLIMATE_R49_20261120.md  [current best]
* e87 itcz_plateau_m fitted 1,750 m (Mexican plateau/Rockies now anchor). vs r48: dev49 0.9875 (S31 0.984), fine28 1.0038,
  sealed n 0.978. Sets l, m, n SPENT; draw a new one first (scripts/make_sealed_set.py, band 15-60).
* Map (ds8) strict zone agreement: r44 32.4, r47 34.9, r48 35.1, r49 35.0 -> r49 = atlas rebuild candidate (OWNER decision).
* Open: Mexican monsoon (Jul-Aug 20-28 mm vs 92-95), Sahel Jul-Aug peak, T +0.6 % in dev.
* Monsoon-peak sensitivity screen (calibration/monsoon_peak_20261120): NO existing knob qualifies (best Mexico -3 %).
* e88 heated-slope convection, e89 (= e40 ocean_rh_warm re-enabled), e90 wet-soil feedback: ALL FAIL their screens
  (calibration/monsoon_physics_20261120; code default off). Per the owner's sequence, climate work STOPS at r49.
  Mexico moves <= 2 % under every change: likely structural (56 km grid vs the Sierra Madre / Gulf of California corridor).
  Sealed set o declared and UNOPENED (still usable). r49 = atlas rebuild candidate.

# CLIMATE r48 ADOPTED on Earth (20 Nov 2026) — reports/CLIMATE_R48_20261120.md
* e86 onset suppression (rotclimate: onset_suppression/onset_gap_deg; default off). vs r47: dev49 0.9921, fine28 1.0013,
  sealed m 0.975 (Oman better, NW Australia rain 1.22 worse). Sets l and m SPENT. Params calibration/local_accuracy_20261023/r48_params.json.
* Map (ds8): strict painted-zone agreement r48 35.1 % (r47 34.9, r44 32.4); r48 = rebuild candidate (OWNER decision).
* Remaining: Sahel Jul-Aug peak too weak; N Australia monsoon margin too wet; original 31 regions ~0.5 % worse in both steps.
  A new sealed set is needed before the next candidate (band 15-60 has 701 free boxes; scripts/make_sealed_set.py).

# CLIMATE r47 ADOPTED on Earth (20 Nov 2026) — reports/CLIMATE_R47_20261120.md
* dev49 0.9876, fine28 1.0016, sealed l 0.931 vs r46 (set l now SPENT). Params calibration/local_accuracy_20261023/r47_params.json.
* On the map (ds8): strict painted-zone agreement 34.9 % vs r44 32.4 % (+2.5); Med recall 60->72 %, Med dry 5.3->8.5 %.
  -> rebuild case exists (full cascade incl. new world checkpoint + corrections retrain); OWNER DECISION.
* Next physics: Sahel timing (e86: dry air aloft / pre-onset convection suppression); needs a NEW sealed set first.
# (history) CLIMATE — e85 plateau-anchored ITCZ (20 Nov 2026)
* Restored: .venv, WorldClim 5' incl. vapr; r46 Alps rerun reproduces the recorded finalist exactly (only runtime differs).
* Diagnosis (r46, dev): Sahel rain peaks May-Jun (obs Jul-Aug); JJAS 243 mm at 15-20 N in Najd (obs 26); false summer rain
  20-25 N Algeria-Sahara; land ITCZ reaches 6.7 + 15.8 = 22.5 N everywhere (right for India via Tibet, wrong for Africa).
* e85 (rotclimate/config.py itcz_plateau_*, model.py; default off): summer excursion += gain x plateau anchor (plateau directly
  poleward, Gaussian 10 deg in longitude). Plan calibration/itcz_plateau_20261120/plan.json (reference = r46 itself).
* Screen (7 dev regions vs r46): s8_g12 mean 0.924 (Algeria T0.56 P0.66, Najd T0.78 P0.93, India/Tibet/Ethiopia ~1.0);
  Sahel timing NOT fixed (model rain fires before the belt: needs a dry-air-aloft / pre-onset suppression mechanism next).
* Refit running: scripts/joint_refit.py calibration/itcz_plateau_20261120/refit.json -> output/itcz_plateau_20261120/refit
  (log refit.log; 40 evaluations of dev49 vs r46). Then fine28 (gate_v3 fine) and sealed l once if dev passes.

# Rebuild without r46 — 20 Nov 2026 (owner: skip r46, rebuild, then back to climate)
* Malaria: validated field published as its own layer land_malaria_v2 ("Malaria (Earth-validated)", raw + corrected); Claude copy
  v11. Population NOT switched: all add-ons are bound to the harvest fingerprint (switch = full cascade; effect 1.5 % of people,
  totals +0.8/+0.3 % with the burden-preserving penalty 0.161). Rule ready in harvest/malaria_v2.py, data/malaria_model.json
  (active_in_export false); wire into harvest/export.py at the next full cascade (editing export.py alone changes the fingerprint).
* PRE-EXISTING: harvest fingerprint inputs changed since the last export (e.g. scripts/land_people.py), so ANY future harvest
  export orphans the add-ons -> the next harvest export must be a full cascade rebuild (harvest -> all add-ons -> settlements).
* Deferred to that cascade (tiny effects): forest-in-travel C2 (ROTCLIMATE_FOREST_TRAVEL; <1 % of contested land) and the
  per-polity herding stats (polity/fields.py -> new herding share).
* NEXT: climate (owner). Open problems: land rain belt to ~22.5 N in Africa (Sahel rains early, false summer rain Najd/Sahara),
  equatorial interiors too dry, Bengal, rain shadows; four refits around r46 stalled; sealed set l unopened.

# Runoff test — 20 Nov 2026: current model VALIDATED, no change (reports/RUNOFF_GRUN_20261120.md)
* GRUN 1970-2000 vs polity/seasons.py runoff: blind seasonal shape 0.80 (V passes), flood-month F1 0.68; best alternative
  (Droogers-Allen PET) +0.007 -> not adopted. Runoff amount ~0.4 of observed (map uses relative flows only).
* NEXT (owner decision): the bundled rebuild — malaria thermal-months rule + forest-in-travel C2 + herding stats [+ r46?],
  with HYDE/Han population re-checks before publishing. Remaining list items: travel times vs journeys (low odds), crop yields.

# Malaria test — 20 Nov 2026: rule ADOPTED on Earth, map rebuild pending owner (reports/MALARIA_GENETICS_20261120.md)
* Targets: MAP sickle-cell (HbS, Piel 2013) and G6PDd (Howes 2012) allele frequencies, 1-degree blocks, 10-degree checkerboard.
* Current field (Mordecai thermal x rain gate 0-80 mm, annual mean): blind HbS 0.11 (V fails). Adopted rule: share of months
  with thermal suitability >= 0.25, no rain gate: HbS 0.55, G6PD 0.55 (G1, G2 pass); better in Africa and outside.
* NOT yet on the map: malaria feeds health -> population -> towns -> everything. Proposed bundled rebuild (owner decision):
  malaria rule + r46 climate? + forest-in-travel C2 + herding stats, with HYDE/Han population re-checks before publishing.
* Note: polity.earth.earth_people uses the older MARA index (z['malaria']); the map uses Mordecai. Data: data/cache/map_genetics.

# Herders test — 20 Nov 2026: NOT adopted (reports/HERDERS_20261120.md)
* Ethnographic Atlas (D-PLACE) 546 societies in the Earth window; blind Spearman 0.12, grazing x5 no better (G1, G2 fail).
  Dev diagnostic: shorter growing season 0.52 / lower NPP 0.59 rank herding far better; humid-hot (tsetse) lowers herding.
* [ADOPTED v2] herding share = 0.207 + 0.331 x clip((240 - LGP)/210): dev 0.54, BLIND Africa S of equator (145) Spearman 0.42 vs
  old -0.06; G1+G2 pass. New atlas layer land_herding ("Herders and farmers", raw+corrected; scripts/herders_layer.py).
  Grazing allowance/food/population unchanged; per-polity herding stats switch at the next reach rebuild (polity/fields.py).
  EA pools spent: all 546 north + 145 south. Earth south run: output/land_people/earth_south (window -36,0,8,52).
* Container rebuilt 20 Nov: .venv recreated from requirements.txt (+pandas); WorldClim 5', Natural Earth rivers (geojson
  converted from the shapefile) and D-PLACE EA re-downloaded; Earth run rebuilt (regional totals within 1.5 % of tracked).

# Fixable / improvable parts — proposed 20 Nov 2026 (owner: drop the population-history line, keep improving the model)
Ranked by feasibility x visible value; each needs a declared Earth test before adoption.
1. Herders / pastoral capacity (uncalibrated): test pastoral capacity and herding share against the Ethnographic Atlas
   (D-PLACE, open, ~1,300 geolocated societies; dependence on animal husbandry) plus modern livestock density (GLW) on
   non-crop land. Affects steppe/dry-interior lifeways, population, pasture layers.
2. Malaria suitability (thermal traits sourced, moisture gate + density penalty uncalibrated): test against pre-control
   endemicity maps (Lysenko & Semashko 1968 as digitised by the Malaria Atlas Project; verify availability first).
3. Runoff / hydrology (no discharge calibration): compare model water balance on Earth windows with GRUN observation-based
   runoff (open, Zenodo); feeds irrigation, rivers, floods, mud season.
4. Already-verified changes not yet on the atlas: r46 climate (owner skipped the rebuild), forest-in-travel C2. Bundle into
   one rebuild only if the owner wants it (large cascade, modest visible change).
5. Lower feasibility: travel times vs real journey records (small, scattered data); crop yields (historical wheat failed;
   Woburn reserved, needs weather matching).
Already Earth-tested, leave: languages (Glottolog), foraging (Binford), towns/placement, supply share, control v2.1, sailing
season, terrain, forest level/pattern.

# Two hosted copies, one branch — 20 November 2026 (Claude session)
* Owner: one branch only, "use the most up to date one" -> claude/friendly-turing-43ygeu (squashed snapshot + GPT-session
  work). claude/wonderful-mayer-uqbwtb is FROZEN (its content is inside this branch's root snapshot; history kept there only).
* Owner wants a Claude copy and a GPT copy of the atlas. Claude copy (full atlas incl. provisional r5 viewer at provisional/):
  https://claude.ai/artifact/XypoZqva951RWZm4ni6FiP v8 (packaged with scripts/package_atlas_artifact.py; 295 files, 244 MB of
  256 MB cap; only the 25 changed files uploaded; browser-checked 83 layers x 2 climates + provisional page). GPT copy:
  https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site (hosts the provisional comparison viewer only).
  atlases/artifact_links.json lists both. Republish the Claude copy after any atlas change (diff packs, upload changed files).
* Container note: .venv is missing after the rebuild; packaging needs only system python3.
* Science status: see the owner question "is this worth pursuing?" (answered in chat 20 Nov): recommendation = stop open-ended
  evidence hunts (plough/reaping/warehouse/handling closed negative); at most ONE bounded, pre-declared test with a kill rule.

# Buffered geographic transfer completed; small signal, unreliable totals

READ reports/GEOGRAPHIC_EXTENT_TRANSFER_20261117.md and qualification.
Plan e7cec7875 committed before groups/fits. Fixed17E/38N quadrants, shared
centre grouping, strict>120km PROJECTED-grid exclusion in outer/inner training.
8outer means/24inner means;32independentmask checks,8heldout perturbations,
200independent score cells,6fresh exports byteexact; figure visually inspected.
Outer groups SW69/SE112/NW383/NE100; sourceSE includes1AD200-incompatible row.
No supportgate failure; no boundary/buffer/feature tuning. Inputs/archivefixed.

M0/H broad CRPS .619987/.606658 (+2.15%); strict .611964/.593771 (+2.97%).
H wins4/4broad groups but3/4strict: NEstrict17rows loses12.38% vsM0.
Generated-total/reference-area H1.3265broad/1.3799strict; baseline also high.
Do NOT call modest individual-score skill reliable regional totals, dated
AD200 population validation, or calibration of historical household resources.
Previous grain600/300/potential all lose to H; no feature/hour adoption.
R5 atlas/climate/defaults unchanged. All plough/reapingtarget screens CLOSED.

NEXT numerical question (proposal, NOT a frozen protocol): predictive dispersion.
Current sigma=inner residual RMS; normal draws and clipping alter area totals.
Declare separately BEFORE fits: calibrate dispersion on inner-heldout CITY-AREA
scores symmetrically forM0/H, preserve same buffered outertest, no outer-total
fitting, new hour/grain/geographic tuning, all-datafit or automaticatlasadoption.
Keep the NEfailure and regionaltotals visible. This does NOT unlock historical
agricultural capacity: actual matched work-time evidence is still absent.
Dated extent/population evidence remains required for historical validation.
Reserved pools/workbook/climate closed. Commit/push/continue remain authorized.

# Historical handoff: grain experiment completed

# Conditional grain/city-area comparison completed; grain feature rejected

READ reports/CONDITIONAL_GRAIN_EXTENT_20261117.md and its qualification.
Declaration53edba13a preceded new features/fits. Twenty outer mean fits,
5,010 independent score cells,20held-out perturbation checks, all1315centre
disks independently reconstructed;9fresh exports byteexact, figures inspected.
M0 broad/strict CRPS .597820/.582518; simple reference H .580108/.558584;
potential grain .592324/.588896;600h .592722/.591992;300h .589611/.585539.
Grain loses to H on both pooled/equalprovince comparisons; retain regional
mixed results (grain beats M0 in3/4strictfolds despite pooled strict loss).
300/600features correlate .997334; prediction difference RMS .025265log.
No actual hours/draft/density inferred; no historical agricultural calibration.
Reference people ALL used as work proxy; NO area-derived resident subtraction.
Gross grain is not exportable/diet population. H and M0 archives exact.
Published r5/climate/parameters unchanged. Reaping target CLOSED; no more search.

NEXT: declare a contiguous geographical transfer test of ONLY M0 and simpleH,
with shared-centre grouping and120km grid-plane exclusion buffer. Freeze exact
quadrants/inner fitting before outcome scores. Current provincehash folds are
not contiguous, so this is a real robustness question, not a grain rescue.
Do not infer historical work capacities or population from this test. Existing
extent phases remain undated. Reserved pools/workbook/climate closed.
Commit/push and continue beyond intermediate pushes remain authorized.

# Historical handoff: grain experiment entry

# Reaping screen closed; conditional grain/extent experiment declared

READ reports/REAPING_CONTRACT_TARGET_20261117.md. Its qualification passes;
three searches/two bodies exhausted, zero paired area/work-time targets.
P.Sarap.51/TM17068 (12 April125) contracts130 arourai and13 reapers; no job
work duration. One-day unpaid clause is not the whole-job duration. Howes2023
quotes54 arourai/6per-worker/5/6artaba but cites this different primary text;
keep mismatch unresolved. No fit/rate/atlas change. Do not continue this search.

NEXT: calibration/roman_benchmark_20261117/conditional_grain_extent.json.
Distinct CONDITIONAL CITY-AREA development estimand, not empirical calibration
of hours/draft/density. Commit declaration BEFORE constructing new grain features.
Use fixed Earth window, all known sites/hinterlands, exact reference density as
workforce proxy without area-derived city subtraction. Compare M0, simple lnH,
potential gross grain, fixed600h and300h gross grain with matched outer folds.
New alpha/beta fits only; no hour search or hierarchy tuning. Existing hierarchy
is frozen reference. Work assumptions unmeasured; gross output not exportable.
Retain dated-extent/survey/population gaps and negative results. Reproduce M0/H,
independent scalar production/OLS/CRPS, leakage control, fresh export, figures.
Reserved pools/workbook/climate closed. No atlas adoption. Commit/push/continue.

# Historical handoff: previous target

# First calibration candidate closed; two planned stages remain

User asks "Go on. How many steps until calibration?" Current truthful answer:
unit check complete;2PLANNED work packages remain (matched evidence+baseline,
thenfit/evaluation). This is NOT a promise of2turns/commits or an ETA. Baseline
and firstestimand proposed, no qualified observation yet; no empirical fit done.
Avoid another generic source-unit/engineering task as a surrogate for the data.

READ reports/COMPANION_ACCOUNT_TARGET_20261117.md and preceding entry report.
Completed output/companion_account_target_20261117/qualification.json:
passed_companion_identity_scope_and_explicit_no_fit_closure.
ONE additional primarybody+metadata under explicitpostscreenamendment, no new
search. SBXX14452=TM32187, NOT adjacentTM14882. Initialmetadataadjacencyprobe
returnedwrongcitation and was rejected; no unrelatededition opened or used.
Currentpinnedrepo0adcd9651ec240726a5b62028cd5c153bf45ffd0:
DDbDP/32/32187.xml,HGV_meta_EpiDoc/HGV33/32187.xml. Historicalcitationpath
sameparent0eec6593... independentlyidentifiesTM32187; old/currentbodyagree;
3officialGitblob identities exact, CC-BY3DukeDDbDP/HGV attribution retained.

Actualcompanion is BEGINNING OF PERSON LIST, only2survivinglines ofnames/gaps,
noarea/duration/operatorroles. Namesnot2workers, line/gapcountsnotworkquantities.
HGVdate lowprecision226–275AD; do NOT inherit versodate20June259. Reciprocity
metadata identifiesversoSBXX14453. No papyrusimage/independentcriticalGreek
collation, no fittedquantity. Heroninoscandidate CLOSED withzeroeligiblepairs.
Earlierinitialscreen/readinesssnapshotpreserved; currentclosureexplicitnofit.

NEXT data-only package2 alternative under
calibration/roman_benchmark_20261117/documented_task_target.json:
one RomanEgyptian reaping-contract/performance sourcefamily, max3searches/
2sourcebodies. Findactualsame-eventarea+operation+crew/exposure/timeunit.
PrefernearAD200; exactdatescope; contractedminimum != observedrealizedrate.
No datum from wages/deadline/names alone. If eligibleconstraint appears, declare
newestimandbeforefit (reaping data CANNOT calibrate plough/draftcapacity). If
none, finiteclosure; no bibliographyloop. No optimizer/newatlasmodel until
baseline/target/estimand/evaluationgate passes. No sourceunit/scheduler sidequest.
Reserved pools/workbook/climate stayclosed. Commit/push andcontinueauthorized.

# Historical handoff: initial calibration entry

# Calibration baseline/estimand recorded; target observation still missing

READ reports/AGRICULTURAL_CALIBRATION_ENTRY_20261117.md.
output/agricultural_calibration_entry_20261117/qualification.json passed source/
baseline identity checks, but readiness explicitly FALSE: no eligible paired
area/operator-day observation. Unitcheck complete, package2baseline/evidence
in progress, package3fit/evaluation notstarted. TWO planned workpackages remain;
no defensible fixed number of source discoveries/turns or ETA while data absent.

Concrete reference: existing candidate/corrected/central/600h activity packet;
no field changed. First proposed estimand: ploughoperator days per worked area
for a defined package, baseline3days/iugerum=12days/ha under assumed.25ha.
Not a new fit or universalvariety rate. Operator/draft STOCKS/annual worker
allowance/density/marketedshare remain separate; don't fit them all to one outcome.

Bounded Heroninos screen used3queries;2actual bodies read (Rathbone2005pp261-269
plusSBXX14453 edition+same-recordmetadata). ArchiveDB methods502/503 unavailable,
notread/qualified. Author's archive249-268AD is later than200; preserve transfer
limit. Articlep266 cites cross-unit plough servicecost recordSBXX14453.
OfficialPapyri website botcheck; publicpapyrigitconnector recovered corpus:
repo papyri/idp.data currentcommit0adcd9651ec240726a5b62028cd5c153bf45ffd0,
DDbDP/14/14883.xml,HGV_meta_EpiDoc/HGV15/14883.xml. OldDDB_EpiDoc_XMLpath
migratedJuly2026; priorparent0eec6593ebfb2c0e2e9ae0c1a7988fb83538e9a7.
All4sourcefiles officialGitblob identities exact; current/historicaledition
bodies structurallyidentical butheadersdifferent. CC-BY3 attribution retained.
SBXX14453=TM14883 catalogue0259-06-20. Letterrequeststeamreturn/payment, NO
matched workedarea/operatoror teamduration. Numerals6/26 areDATES, deadline30
notobservedjobduration. Modernheader1907/1997 publicationdates NOT papyrusdates.
No scan/independentcriticalGreekcollation; no targetrate extracted.

NEXT calibration/roman_benchmark_20261117/companion_account_target.json:
ONE named primary companionSBXX14452, directlyidentifiedinHGV14883 asrecto.
Explicitpost-screen amendment allows this extra ONE body+metadata, no more
searches/sourcefamilies; initialtwo-body result is preserved. Record unopened.
Inspect/extract ONLY if explicit area+definedoperation+crew/duration align; else
closecandidatewithno-fit. Do not restart generic sourceunit/scheduler work.
Unifiedmilestonescalibration_entry.json stays governing; no newmodel/atlas/climate.
Commit/push andcontinueauthorized; oldNEXTlinesbelowhistorical.

# Historical handoff: unit crosswalk

# Unit crosswalk complete; calibration-entry package is next — 17 November 2026

User: "Go on. How many steps until calibration?" Answered as THREE work
packages from that question:1units,2one baseline/freeparameter/matchedtarget,
3fit+comparison. Package1 NOW COMPLETE;2/3 remain. This is NOT a guaranteed
number of turns or promise that absent empirical observations will materialize.
Do not count source checks,62 engineeringtests or the old chosen95%-grain fit
as independent empirical resource calibration. City-area model already fitted;
new agricultural operator/draft/workavailability targets remain unqualified.

READ reports/CEREAL_SEED_AREA_LINK_20261117.md.
output/cereal_seed_area_link_20261117/qualification.json passed:
11 paragraph identities/two arithmetic conversions and conditional unit links;
fresh exports byteexact, source same original ColumellaII English witness.
2.9.1/5 wheat4or5modii/iugerum matches2.12.1;2.9.14/15 namedhexastichum barley
5modii/iugerum matches2.12.2. Distichum/Galatian barley2.9.16 uses6modii, not
directly matched; no6/5 task rescaling, no universalbarley claim. Daylength8h
and approximate.25ha conversions remain scenarios. Coefficients/atlas unchanged.

NEXT UNIFIED PLAN calibration/roman_benchmark_20261117/calibration_entry.json.
Package2: choose one concrete calibration baseline/estimand and match eligible
area+operation/crewtime or animalservice observations. Fixed hourly allowances,
operatorfractions/draftstocks remain scenario inputs unless observed targets
qualify. Max3 searches/2original scholarly/method bodies on one farm-account
family; exact dates/support/inclusion, no eligibility from snippets or transferring
another Roman date into exactAD200. If none qualifies, explicit no-fit readiness
decision; do not manufacture a historical fit or restart generic task audits.
Package3 runs ONLY after target/baseline/comparison gate. Reserved pools/workbook
and climate stay deferred; no warehouse/modernhandling return. Commit/push and
continue authorized. Older NEXT lines below are historical, not parallel queues.

# Historical handoff: plough-only completion adapter

# Plough-only completion adapter implemented and checked — 17 November 2026

READ reports/PLOUGH_COMPLETION_ADAPTER_20261117.md and preceding Roman resource
contract. New harvest/plough_resources.py reuses unchanged harvest.labour:
plan_plough_package requires ONE explicit physical origin, per-ha total human,
qualified operator subset and draft-team service, net capacities and boolean
window. No Roman coefficients, animal supplies, operator fractions or dates
defaulted. Rejects missing/zero team requirement and operator>totalhuman.
Zero available team service is valid and completes zero. Human/operator/team
must coexist in same period; operator column is SUBSET, not extra people.
Result: completed plough-PACKAGE hectares, used/rawunused hours only. No grain,
annualcropcompletion or populationoutput. Pass/fieldquality/animalfeed/otherduties
remain outside; explicit net capacities are caller inputs, not inferred.

Completed output/plough_completion_adapter_20261117/qualification.json:
passed_supplied_plough_resource_adapter_not_full_farm_or_atlas_feasibility.
62 tests pass across new tests/test_plough_resources.py and oldtest_farm_labour.py;
9 manufactured controls independently bounded by sum of per-period minimum
capacities, fresh CSV/JSON/result byteexact. Tests cover subset/draft/human limits,
disjoint windows, netotherduties, calendar shift, unitrescaling, fractionalarea
and invalidinputs. No atlas/crop/climate/food/route/worldpopulation rerun.
The original scheduler and all prior science/publication identities stay fixed.

NEXT FROZEN calibration/roman_benchmark_20261117/cereal_seed_area_link.json.
Same cached ColumellaII English witness, sections2.9 and2.12 ONLY: crosswalk
cereal sowing volumes per iugerum to task-count seed quantities. Keep crop/soil/
method qualifiers; state which prior area interpretation is supported. No silent
rate correction, new sourcefamily, operator/animalallocation, food/map/default
or climate change. OriginalHTML cached/ignored under plough_resource_contract
source/ with exact historicalsha. No new scan/Latin equivalence claimed.
Do not infer Earth seasonal feasibility just because the adapter works.
Commit/push and continue remain authorized; no background jobs at completion.

# Historical handoff: Roman plough resource contract

# Roman plough resource contract complete — 17 November 2026

READ reports/PLOUGH_RESOURCE_CONTRACT_20261117.md.
Completed output/plough_resource_contract_20261117/qualification.json:
passed_one_witness_plough_resource_scope_no_capacity_adoption.
One LacusCurtius English bookII witness (site says Loeb1941); fetchedHTMLsha
c3be3fab... EXACTLY matches original farm-task source.20 paragraphs in2.4/2.12,
10 located claims; independent streaming paragraph/digest/quantity checks pass;
fresh exports byteexact. Wholebook fetched but only two chapters analyzed.
No new Latin/scan collation, resource-rate adoption, model run or atlas change.

Findings: named ploughmen's days are operator work, a subset of total human
work.2.12.7 conditional tree-free200iugera example has2yokes,2ploughmen,6common
labourers; not a universal operator/draft fraction.2.4.8 fourday package bundles
multiple passes plus ridging/sowing (don't charge sowing twice). Soil/moisture/
terrain/quality qualify work; no numeric global workability threshold.2.12 crop
list gives seedvolume, not independent area certification for all crops here.
Previous seed-area conversions remain assumptions; no silent source repair.
Actual operator pool, teams, feed/endurance/otherduties and windows stay missing.

NEXT FROZEN calibration/roman_benchmark_20261117/plough_completion_adapter.json.
Existing harvest.labour already supports simultaneous resources. Add small
single-origin plough-package adapter: explicit per-ha human/operator/team hours,
explicit NET capacities/window, operator capacity<=same total human capacity.
No default Roman rates or capacities, no team-free shortcut. Completion reports
plough-package hectares only, not grain, annualcropcompletion or supportedpeople.
Manufactured analytical tests for coincident/disjoint resources, subset/draft
binding, invalid/missing inputs and unit/scope behavior. No Earth scenario.
Commit/push and continue authorized; climate later, warehouse detour superseded.

# Historical handoff: cereal operation demand preparation

# Cereal operation demand preparation complete — 17 November 2026

READ reports/CEREAL_OPERATION_DEMANDS_20261117.md (and preceding crop packet report).
Completed output/cereal_operation_demands_20261117/qualification.json:
passed_fixed_normative_task_demands_not_dated_resource_schedule.
64 task/case summaries on16 SAME physical activity cases;15365984defined
origin/task demands,69664032materialized task values independently checked;
four missing-prescription/crop/worker/unit controls pass; fresh exports byteexact.
No new model solve, scenarios, workers, dates or liveatlas changes.

Barley normative plough96, harrow32, firsthoe48, reap32 hours/retained ha,
using existing Columella2.12 transcription and assumed8h/0.25ha conversions.
Absent barley second-hoeing/weeding prescriptions stay UNKNOWN(NaN), notzero.
No-crop demand and worker-day denominators with zero workers stay undefined.
Reader in scripts/cereal_operation_demands.py materializes from tracked base
activity packets; no duplicate binaries or market-share workforces.

Plough46.15% of listedwork versus reaping15.38%. Max full8h-worker-day equivalents
at600h: plough34.62,harrow11.54,firsthoe17.31,reap11.54;300h halves these.
These are conditional thresholds IF all effective workers devote time to task,
NOT available dates, actual Roman day lengths, feasible calendars or draftteams.
Correctedcentral600h normative plough4.3504B,harr1.4501B,hoe2.1752B,reap1.4501Bhours.
Canonical-minus-normative signed residuals stay separate:annual−194.938h,reap+10.911h;
no adjustments, clamping or extra availability. Reaping subset notdoublecharged.

NEXT FROZEN calibration/roman_benchmark_20261117/plough_resource_contract.json:
one bounded Columella bookII source witness, sections2.12 task counts and2.4
ploughingmethod. Establish meaning of plough-day (human/crew/yoke), soil,
implement/pass conditions and missing paired human/draft quantities. No new
source family, numerical search, invented universal dates or resourceallocation.
Largest task first; no warehouse/modernhandling or climate detour.
Keep all-barley and density alternatives explicit. Current work committed/pushed;
continue authorized; no background jobs.

# Historical handoff: per-origin cereal activities

# Per-origin cereal activities recovered — 17 November 2026

READ reports/CEREAL_ACTIVITY_PACKET_20261117.md.
FIGURES output/cereal_activity_packet_20261117/annual_limits.png and
retained_cereal_area.png (two native-grid four-panel maps, visually inspected).
Completed qualification.json: passed_fixed_cereal_origin_area_work_packet_not_seasonal_qualification.
Two TRACKED NPZ climate packets (~54.3MB total), load_packet()/activity() reader
in scripts/cereal_activity_packet.py. Shared crops/rates/areas, eight rural vectors,
16 retained-fraction arrays.32 marketed-share scenarios alias16 physical cases;
never duplicate their hectares/workers by summing share alternatives.
Stable row*1000+col IDs for all241889 majority-land cells in both climates,
including crop0 with undefined(NaN) physical cereal area/yield and preserved meals.

All416 original scalar food/work controls EXACT,16 literal unchanged field_support
replays. Independent scalar min/divide and crop/area/energy/reader checks pass
3870224origin-case rows/104496048materialized values;224 summary values checked.
Fresh allscientific exports (including NPZs) byteexact. No climate/crop/route/
placement calls, new scenario, parameter or live r5 atlas change.

Main findings: EVERY productive origin selects BARLEY under least-listed-work
objective (raw238796/corrected241391; crop0 raw3093/corrected498; wheat0both).
Not an observed crop mix or complete diet. ALL work-limited origins bind annual
allowance; zero reaping/both/zero-worker-limited origins in these16 cases. Relative
utilization classification has no absolute tiny-budget floor.30day*8h reaping
allowance is240h/worker vs <=92.31h required at600h annual barley allowance.
Correctedcandidate600h central retains45.3164Mha/52.335%; low53.3966Mha/61.6667%.
Area weights differ from calorie weights. Rawcentral44.6033Mha/51.8771%.

Precision: frozen source rates float32 promoted exactly; retain signed differences
from normative per-ha hours. Maxrelative listed-hour residual5.895e-8; corrected
central600h signed sum−194.938h (NOT a credit/work pool). Reviewer caught an extra
rounding from multiplying stored float32 cell area by100; recovery promotes FIRST.
Original cell snapshot and every old food/work result unchanged. Packet source
potential reconstructs EXACTLY; no rate replacement/clamping.

NEXT FROZEN calibration/roman_benchmark_20261117/cereal_operation_demands.json.
Decompose normative operations on same retained hectares (Columella2.12 counts),
keep rounded-work residual separate, compute required h/worker and full8h-worker
day equivalents (conditional thresholds, not observed days/calendar). Focus on
plough/harrow/hoe rather than unbinding reaping. Missing windows/draft/processing
remain explicit; no invented calendar, workers, crop mix, scenarios, warehouse
or climate development. Commit/push and continue remain authorized.

# Historical handoff: annual agricultural budget trace

# Annual agricultural budget trace complete — 17 November 2026

READ reports/ANNUAL_AGRICULTURAL_BUDGET_20261117.md and
output/annual_agricultural_budget_20261117/budget.csv / recipe.json.
Completed qualification.json: passed_scalar_annual_agricultural_trace_not_complete_farm_economy.
32 existing candidate/control cases;288 ledger identities checked; separate
reviewer checks928 scalar/string exports with complementary identities; fresh
budget/recipe/result byte exact. AST checks field-support defaults/land constants.
No new model run, parameter, source family or atlas change.

Key definitions: workers=.4*rural;600/300h means240/120 listed hours per rural
person; reaping allowance96h/person in same annual budget. Wheat336/48 and
barley208/32 listed/reaping hours per cropped hectare use normative Columella
days and assumed8h/0.25ha conversions. Potential area uses land fraction,
arable and.6 farmed*.6 sown=.36 of arable; sowing share inherits HanAD2 fit,
not Roman observation. Work-efficient single wheat/barley activity differs from
the broader population crop portfolio. Existing land/population denominator
1.1M kcal/person-year versus cereal ration912500kcal: different scope; neither
certifies complete draft/feed/processing/storage occupation in this flow model.
Aggregate retained crop hectares remain unavailable without cell crop identities.

Corrected central600h production128.674M ration-years of240.092M potential
(53.59%retained); rural actual retention40.086M, positive surplus88.588M,
marketed29.871M, townconsumed11.532M, transport grain-equivalent cost10.540M,
leftatorigins6.022M, unusedtownexcess1.777M. Ruraldeficit28182 remains explicit.
Foregoneunderworklimits111.418M is NOT historically recoverable output.

NEXT FROZEN: calibration/roman_benchmark_20261117/cereal_activity_packet.json.
Recover per-origin cereal identities, potential/retained cropped area, net yield,
work/resource units, rural need and surplus from existing fixed archives. Exact
replay of existing field arithmetic permitted ONLY as control of all32 current
cases; no new scenario/fit/climate/crop/route/placement solve. Inspect where limits
bind. Preserve majority-land versus land-fraction masks, source IDs and packet
precision. Complete human/draft/processing tasks remain unqualified; do not invent
non-reaping windows or repurpose unused listed work into warehouse staff.
Both density scenarios stay explicit; climate remains deferred.
All current work committed/pushed; continue authorized. No background jobs.

# Historical handoff: Karanis density feasibility

# Karanis density feasibility screen complete — 17 November 2026

READ reports/KARANIS_DENSITY_FEASIBILITY_20261117.md.
Completed output/karanis_density_feasibility_20261117/qualification.json:
bounded source provenance/scope passed; ZERO matched AD200 density observations.
Exactly3 targeted searches/3 source bodies: Yiftach2020 pp243-247 (especially
p246 n36), Motta etal2024 doi10.15184/aqy.2024.69, KelseyMuseum site history.
Source HTML/text/web-extracted chapter caches ignored under source/; URL/hash/
retrieval route records tracked. Direct Academia HTML is preview/AI material;
actual printed chapter text was read through separate web extraction, NOT that
preview. No facsimile identity or direct papyrus interpretation claimed.

Specific missing link: tax-collection units not located on excavated plans;
taxpayers not complete inhabitants; census examples cross dates; lettered
excavation levels do not define town-wide simultaneous occupation. BGU I97 and
BGU II577 (201/2) are CITED LEADS ONLY, not records opened this session. No town
population / whole-mound area division, new density, model run or atlas change.

NEXT: calibration/roman_benchmark_20261117/annual_agricultural_budget.json.
Use existing supply diagnostics + pinned work/production code and already read
Columella evidence to trace people→workers→listed hours→crop-area/work→production
→rural retention→marketed surplus→delivered ration equivalents in compatible units.
Quantify work-limited production without calling it historically recoverable.
Identify largest missing agricultural definition before seasonal work. No new
source pool, simulation, fit, warehouse detour or climate development here.
Both density alternatives stay explicit. Commit/push and continue authorized.

# Historical handoff: annual assumption priorities

# Annual assumption priorities complete — 17 November 2026

READ reports/ANNUAL_ASSUMPTION_IMPACT_20261117.md and
output/annual_assumption_impact_20261117/assumption_impacts.png.
Completed qualification.json: passed_existing_annual_matched_sensitivity_not_empirical_uncertainty.
Only existing November16 supply/hierarchy outputs were reduced:32 cases,
48 strictly one-input contrasts,16 unavailable combinations,60 ranking rows.
Separate exhaustive scalar/Cartesian-pair reviewer passes; all five scientific
exports fresh-byte-exact;18 figure values checked and visual inspected. No new
food/work/freight/climate model run or published atlas change.

Candidate corrected maxima: density changes town residents7.795M (5.520→13.315M)
and grain coverage56.521pp; marketed share50.315pp; listed field allowance50.239pp.
Hours most affect rural shortfall (226663 ration-years) and short towns (239).
All outcome-specific factor orders agree across raw/corrected and old controls.
Ranges are scenario choices, NOT empirical uncertainty; near-tied extraction/hour
effects do not establish a historical ordering. Density also redistributes rural
people/workers/production endogenously; it is not a frozen-supply comparison.

Priorities: matched inhabited-area/population evidence; complete agricultural
work/output budget; marketed fraction with production/retention denominator.
Unvaried crop/yield/workforce/freight inputs remain UNRANKED, not small effects.
Earlier housing-phase audit was AD150, not a new AD200 population qualification.
Keep conditional city-area skill and weak regional spatial result separate.

NEXT DECLARED: calibration/roman_benchmark_20261117/karanis_density_feasibility.json.
One finite Karanis evidence feasibility screen, max3 searches/3 original bodies:
approximately AD200 occupied residential area matched to household/person data.
Do not assume census declarations enumerate the whole settlement, excavated
area equals occupied area, or village density transfers to large cities.
No new fit/default/atlas change; reserved pools/workbook stay closed; climate later.
Commit/push and continue remain authorized. Earlier NEXT entries superseded.

# Historical handoff: regional source contract and spatial diagnostic

# Regional source contract and spatial diagnostic complete — 17 November 2026

Owner asked to continue the approved AD200 realism programme. This continuation
screened exactly three source families, qualified a limited new regional
observation contract, and ran the declared SAME-SUPPORT spatial baseline check.
It continued across source-preparation commits/pushes; no atlas/model adoption.

READ reports/ROMAN_REGIONAL_SOURCES_20261117.md and
reports/LEVANT_SPATIAL_DIAGNOSTIC_20261117.md.
FIGURES: output/roman_regional_sources_20261117/source_support.png and
output/levant_spatial_diagnostic_20261117/spatial_comparison.png.
Both output directories have completed qualification.json receipts.

Source screen: Rural Britain remains excavation/report-selected, not a census.
Potenza official methods acknowledge second/third-century fine-ware dating
problems; no matching machine-readable support qualified here. Selected third
candidate: Titolo & Palmisano2025 South Levant, doi10.5334/joad.158, CC-BY4.0,
pinned GitHub a3537c67cc736fb929291c50a4928a0cd7136dd9. Raw files local/ignored
under output/roman_regional_sources_20261117/source/, URLs/hashes/Git blobs pinned.
Current GPKG canonical; CSV discrepancies retained, not repaired. Actual current
files:14273 phase rows/5557 SiteIDs, versus older paper counts14142/5542.

Frozen phase/type/quality/identity/support rules yield565 unique habitation-site
IDs (Late Roman70–324AD, Settlement/Fortified Settlement, LocQualA) in EIGHT
exact-primary-source survey envelopes. Ten identical phase duplicates collapsed,
six outside-own-polygon sites and200 unmatched-source sites retained as exclusions;
one mislabelled Late Roman324–638 row excluded, never corrected.69 valid polygons,
8 named and61 unattributed. Geometry/attributes agree; no phase-specific area or
population inferred. Most SizeQualC; noA/B. Paper documents unequal detection.
Source input reviewer checks all14273rows,69areas,571 scalar polygon memberships
and3955 observation values. Fresh seven exports + result receipt byte exact.

Diagnostic result: fixed legacy/refreshed population-pattern fields are IDENTICAL
on this support and slightly WORSE than within-source uniform-land opportunity.
Equal-source mean log gain−0.03949845 nats/site; pooled gain−0.06024747;
equal-source presence/background AUC0.47701196 vsuniform0.5. Two sources improve
likelihood, six worsen; all retained. Zertal-Bar2019 is strongest negative case,
not a new tuning target. Do not relabel this as an absolute population error.

565 observations all on-grid/on-land, but only55 distinct9km model cells and
93source/cell pairs. Source totals are conditioned separately, not compared as
regional census density. Uniform observation opportunity and proportional
population-to-site intensity are explicit UNQUALIFIED assumptions. Source phase
presence is not simultaneousAD200 occupancy. No p-value/new blind/geographic
validation claim. This tests fixed occupation-density covariates, not the urban
town generator against farms. Current hierarchy area-skill result remains separate.

Original centre-H and whole-window population recipe controls exact before new
scores. Four focused scorer tests pass (optional GIS group); independent closed-
form grid assignment, cell intersections and scalar probability/likelihood/AUC
checks cover565assignments,93pairs and120scorevalues. GEOS/canonical density
recipe reused, not independently rederived. Fresh five exports + receipt exact.
Optional dependencies: requirements-roman-benchmark.txt (Shapely2.1.2, pyproj).
No new climate/food/work/route solve, population allocation, hierarchy fit or
published atlas change. Live r5 stays https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site

NEXT FROZEN: calibration/roman_benchmark_20261117/annual_assumption_impact.json.
Use ONLY already reviewed candidate supply/hierarchy packets to rank major
annual assumptions with MATCHED one-input contrasts: density at fixed extraction/
work/climate; extraction at fixed density/work/climate; listed field-work hours
at fixed other inputs. Missing matched cases unavailable. Raw/corrected climate
separate scenarios. Differences are scenario sensitivity, not empirical uncertainty.
Keep source evidence class/AD200 relevance and missing complete occupation/diet
explicit. Return ranked priorities and one period-evidence target; no new food
runs, rate sweeps, hierarchy tuning, warehouse/truck research or default adoption.

User's wider approved programme: strengthen period observations and simple
baselines, annual economy, influential uncertainties, high-impact seasonality,
then matching atlas cohorts. Climate remains deferred. All earlier warehouse
NEXT targets below are superseded. Commit/push and continue remain authorized.
No jobs running at completion.

# Historical handoff: first Roman conditional-size benchmark

# Roman benchmark comparison complete — dated regional observations next

17 November 2026. Owner-approved realism plan is now the active programme.
This continuation built the first direct evidence/baseline/current-model
comparison and continued across intermediate commits/pushes. All warehouse and
handling NEXT instructions below remain superseded; no truck/handling research.

READ: reports/ROMAN_BENCHMARK_20261117.md.
MAPS: output/roman_benchmark_20261117/roman_comparison.png,
egypt_comparison.png, evidence_coverage.png.
QUALIFICATION: output/roman_benchmark_20261117/qualification.json, status
passed_conditional_Roman_size_baseline_benchmark_not_dated_demographic_validation.

Result: current refreshed-H hierarchy family has modest added size skill versus
same-training M0. Compatible AD200 targets663: CRPS improves4.40%, median log-area
MAE5.55%; strict152:7.54%/9.43%. Province wins32/51 and25/40; equal-province
CRPS improvements2.01%/4.71%. Mean total area ratio is1.118 current vs1.016 M0
on compatible targets. Egypt strict11 remains badly underpredicted: current
mean generated area39.76% of reference, all medians low. Do not tune a new
Egypt correction or declare full realism from a relative score improvement.

Same original664 training records, four province-hash outer folds (not spatial
blocks), no hierarchy refit. Exact original five-seed control, then predeclared
256 seeds1000..1255 for both alternatives. Four simple baseline fits only.
All339968 area draws and2688 aggregate cells independently checked; pairwise
CRPS agrees within2.67e-15; max area difference7.39e-13ha. Fresh six exports +
result receipt byte exact. All5312 plot values and six panels checked; all sites
inside map frames.1108 CURRENT protected identities, including live r5, unchanged.

Evidence gates: catalogue city epochAD150; AD200 compatibility uses old open-end
convention. Of663 compatible model records only6 have an explicit end date.
Areas table has NO phase date. Zero dated extent phases, independent survey
footprints or observed city populations are newly certified.51 provinces have
coverage counts; availability is not completeness. Known locations/capital
labels supplied. This is a conditional exposed-source development benchmark,
not AD200 demographic validation, missing-town prediction or new blind test.

NEXT FROZEN: calibration/roman_benchmark_20261117/dated_regional_evidence.json.
Inspect metadata/methods for at most THREE scholarly regional survey/census
sources appropriate toAD100–300. Need independently documented footprint,
phase/site type/detection limits, and area or population definition. Select on
support/provenance, not model outcomes. Qualify one regional observation
contract before comparing simple spatial/fixed-budget population baselines on
identical support. Preserve unknowns; do not treat excavated-site catalogues as
complete surveys or household samples as provincial censuses. Reserved Buringh
pools and site-survey workbook stay closed unless a later explicit scope changes.

Programme after that: period-constrained annual economy, influential uncertainty
ranges, high-impact seasonality, then matching settlement/supply/reach/trade
atlas cohorts. Climate fixed for now. Published r5 remains unchanged and LIVE:
https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site

Recipes: prepare_roman_benchmark.py, review_roman_benchmark_preparation.py,
run_roman_benchmark.py, review_roman_benchmark.py, render_roman_benchmark.py,
seal_roman_benchmark.py under scripts/. Large derived NPZ and fresh/ local/ignored,
pinned and reproducible. Completed stages refuse overwrite. No jobs running
at completion; commit/push and continuing across pushes remain authorized.

# Historical handoff: benchmark declaration

# ACTIVE: AD200 Earth benchmark — approved realism plan, 17 November 2026

Owner approved the six-stage realism plan. Start with evidence, a simple baseline
and the current settlement model on the SAME Roman regions. This supersedes
all older warehouse/handling NEXT targets, including Roman handling research.
No more mechanism work before assessing added predictive value.

Frozen declaration: calibration/roman_benchmark_20261117/plan.json.
First deliverable: conditional settlement-area benchmark using existing pinned
Roman catalogue, explicit AD200 occupation/date and extent-basis audit, M0 versus
training-isolated current hierarchy family, common regional maps and all-province
scores. Areas are undated extents; city occupation is not an extent phase. Do not
claim AD200 demographic validation, survey completeness or location forecasting.
Same four province-hash folds; no new blind claim. Exact five-seed control before
256 fixed evaluation draws; no hierarchy refit or new source pool.

Then move to genuinely dated population/settlement observations and simple spatial
baselines, annual economy, influential uncertainties, seasonal constraints and
matching atlas chain. Climate stays fixed. Period-specific evidence and unknowns
remain explicit; modern truck rates remain discontinued.

Preserve current published r5 atlas and all historical scientific receipts.
Commit/push intermediate stages and continue; do not pause after each push.

# Historical handoff: superseded handling-evidence queue

# Owner steering: AD 200 evidence only for handling calibration — 17 November 2026

The owner challenged the modern truck-handling study: "we're doing 200 AD why
are we reading about trucks". That research direction is DISCONTINUED. None of
its numbers entered any model. Do not resume the modern observation target in
older handoff entries or promote modern warehouse guidance to Roman work rates.

ACTIVE NEXT: calibration/urban_diagnosis_20261117/roman_handling_evidence.json.
Seek dated Roman-period documentary evidence (prefer AD100–300, centred on200)
for grain handling operations/loads/work organisation and any matched quantity,
crew and time denominator. Keep dates/sites, evidence class and temporal transfer
explicit. Wages/storage volume/shipping duration are not handler productivity.
Missing period rates stay unknown; no modern truck/conveyor substitute.

Completed and pushed this continuation: ALL-original Earth handling quantities
and exact independent review (2170town rows,52080monthly quantities,15896ordered
shipments), then one FAO guidance screen with no empirical rate qualified.
Reports: HANDLING_EXPOSURE_20261117.md and HANDLING_RATE_SCREEN_20261117.md.
The latter is historical conceptual guidance, not AD200 calibration evidence.
Modern observation PDF was read but no extraction/qualification/integration was
completed; disposition at output/urban_handling_observation_20261117/disposition.json.

Current live provisional r5 atlas and all original model inputs remain unchanged:
https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site
No new food/work/stock/graph solver, handling coefficients or staff assignment.
Commit/push and continue authorized; climate/steppe remain deferred.

# Historical handoff: superseded modern evidence direction

# Handling quantities and FAO evidence screen complete — observational paper next

17 November 2026. Live r5 atlas remains unchanged:
https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site

Two stages completed this continuation, continuing across pushes:
1. ALL original Earth handling quantities: 2,170 town rows, 52,080 exact monthly
quantities, 15,896 ordered shipments, 1,363 year wraps; fixed requests and zero
movements retained. Six outputs + result receipt fresh byte-exact. Rates/work
hours unknown. Report reports/HANDLING_EXPOSURE_20261117.md; qualification
output/urban_handling_exposure_20261117/qualification.json.
2. Bounded 3-query/6-record/ONE-body source screen: first matching direct FAO
Storage in bags chapter. Ten independent literal/section checks. Guidance on
manual/equipment work, inspections and storage geometry supplies no measured
crew/quantity/time denominator. No empirical rate qualified or adopted.
Report reports/HANDLING_RATE_SCREEN_20261117.md; qualification
output/urban_handling_rate_screen_20261117/qualification.json.
Raw source HTML/receipt local/ignored; exact digests in qualification.

NEXT FROZEN: calibration/urban_diagnosis_20261117/handling_observation_primary.json.
Read the ONE direct-journal original observation paper (Industrial Health45(1),
p165, West Godavari grain handlers, J-STAGE PDF URL in declaration). Full body
not yet opened at this handoff stage. Verify operation/material/crew/time,
measurement/sample and uncertainty. Search snippets are not qualified facts.
No automatic truck-time/person-hours conversion or modern-to-ancient/fantasy
transfer. No food/work/stock/graph/warehouse solve, staff/coefficient adoption or
atlas/default changes. Climate/steppe and reserved sources remain deferred.

Guard: 3,378 historical checks use five exact archived original publication
exceptions after r5, while 1,197 CURRENT identities remain fixed. Never overwrite
live r5 files or falsify old receipts. Commit/push and continue are authorized.

# Historical handoff: handling exposure audit

# Original handling exposure complete — bounded rate-evidence screen next, 17 November 2026

The published provisional-r5 atlas remains LIVE and unchanged:
https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site

Completed after the release: all original Earth monthly central/low town handling
quantities. See reports/HANDLING_EXPOSURE_20261117.md and
output/urban_handling_exposure_20261117/qualification.json.
All 2,170 town rows retained, including zero flows; 52,080 monthly quantities and
15,896 ordered shipments independently reconstructed exactly, including 1,363
December-to-January records. Fixed requests/geometry unchanged. Separate qin/qout
annual/peak values, monthly vectors, CSVs and 2x2 inspection map retained.
Rates and work hours remain UNKNOWN; no rural-slack staffing, warehouse mapping,
food/stock/work/graph solver or new Earth scenario. Fresh six outputs + receipt
byte exact. This is the ORIGINAL EARTH cohort, not fantasy r5 towns.

Publication-aware guard: 3,378 historical identity checks; five changed r5 live
paths resolve to their exact archived original hashes. Separately 1,197 CURRENT
identities stay pinned, including the live r5 atlas. Never restore old public
files over the new atlas or falsify old qualification receipts.

NEXT FROZEN: calibration/urban_diagnosis_20261117/handling_rate_evidence_screen.json.
Bounded search: at most 3 initial queries, 6 candidate records, ONE direct primary
manual/report body selected for operation/provenance before numeric outcomes.
Need explicit manual grain loading/unloading/stacking operation, material/crew/
time; distinguish observed human work from prescribed/design/equipment rates.
Modern-to-ancient/fantasy transfer and mass-to-net-edible-kcal conversion remain
unknown. No rates/staff/model adoption or new food run. Continue across pushes.

# Historical handoff: provisional settlement atlas r5 publication

# Provisional settlement atlas r5 published — 17 November 2026

LIVE: https://rotclimate-settlement-atlas-r5.stripedapple4.chatgpt.site
Deployment succeeded; owner-private Site. All 24 desktop/mobile scenarios passed.
Deployment/source IDs and hosted file hashes: output/settlement_provisional_release5_20261117/deployment.json.

The owner accepted a bounded provisional atlas release after asking for the next
map. This supersedes the old warehouse diagnostic NEXT below. Do not resume
open-ended source research before completing publication. Commit/push and keep
working across pushes are explicitly authorized.

Frozen scope: calibration/settlement_provisional_release5_20261117.json.
Report: reports/SETTLEMENT_PROVISIONAL_RELEASE5_20261117.md.
New full-atlas Settlements default: provisional_central. New synchronized
comparison: atlases/earth_fit/provisional/index.html. Four options per climate
cover central/low settlements and each cohort's annual grain. Existing R4 maps
are retained and labelled; reach/trade/administration are NOT recomputed.
Historical adopt=false and scientific gate=false remain unchanged.

Independent Earth/candidate/five-seed/supply reviews reran before publication.
Fresh candidate: all 13 files exact. Fresh supply: rederived freight network,
four released files and full unrounded control receipt exact; all ten scientific
exports exact. New presentation reviewer checks 8,348 added town grain values,
all earlier viewer values and 1,178 pinned inputs with archived publication
exceptions. Reviewer timing-only Earth receipt was separately saved and original
receipt restored. No science source changed. Replays are local/ignored and
pinned; old historical producers need original publication baseline to rerun.

Publication scripts: scripts/publish_settlement_provisional.py,
scripts/review_settlement_provisional.py,
scripts/check_provisional_atlas_browser.cjs. Receipts and archived baseline:
output/settlement_provisional_release5_20261117/.

Hosted comparison Site registered as appgprj_6afc259a53e4819199e8facba394edf3,
checkout /workspace/sites/rotclimate-provisional-atlas. Preserve this identity;
do not create another Site. Owner-only audience confirmed. Deployment succeeded with saved version
appgprj_6afc259a53e4819199e8facba394edf3~appgver_8d75782aa4948191a1993ec9be19dbda.
Site source commit a9a3db0f103e5ba766bd99a051f15c87a6a8eb78; atlas source
commit 19c004496. Both repositories pushed. No jobs remain at completion. Sites source helpers
were absent from this runtime; portable static Git/tar fallback keeps credentials
only on stdin/in memory. No token is stored in this repository or Site checkout.

Scientific limits remain explicit: exposed Earth development pool, failed older
southern Mesopotamia blind test, no new blind qualification; seed sensitivity is
not calibrated uncertainty. Annual grain/work is not seasonal continuous food,
warehouse/handling staff or complete diets. Climate r44 and northern-steppe
side quest remain deferred. NEXT science: the historical rate-free handling
exposure plan below can resume; do not treat it as a blocker for this published
provisional map or silently promote the candidate to full scientific adoption.

# Historical handoff: Original work-budget inspection map complete — 17 November 2026

Latest figure: output/urban_original_work_map_20261117/original_work_budgets.png.
Report: reports/ORIGINAL_WORK_BUDGET_MAP_20261117.md. Qualification:
output/urban_original_work_map_20261117/qualification.json, status
passed_original_partial_work_map_all_source_values_and_display_limits.
No jobs running at completion. This continuation completed the archived evidence
review, primary calendar witness, six-expression printed concordance and map,
continuing across commits/pushes. All 1103 protected identities remain unchanged.

The four-panel map uses ONLY original B600 central/low physical-source budgets.
Independent review checks all 112,756 values, masks, 81 km² cell area and plotting
formulas. Original unspent fractions are 14.2439% / 16.1581%; annual constraints
bind at 45,935 / 44,726 positive-workforce sources. Each case has 56,378 sources,
53,265 positive workforce and 3,113 undefined utilization cells. Same 0–100%
use and .01–10000 h/km² positive log scales. Exact zero unspent is separately gray.
All clipping counts retained: negative unused 1610/1459, percent 4027/3837,
positive under-floor 1569/1471, over-ceiling 364/428. Tiny positive residuals can
show in the lowest color; they are not meaningful spare staff. Raw budgets and
original work tolerance unchanged. Derived local_plot_values.npz (~2 MB) is
LOCAL/IGNORED, pinned and reproducible. Compact PNG/summary/receipts tracked.

No new food/work/climate/graph/phenology/population solver ran. The map is partial
listed cereal work, not warehouse staffing or an updated settlement atlas.
84.62% of listed task hours lack monthly placement in these original archives.
No population/default change or empirical task-rate/capacity/access adoption.

NEXT FROZEN: calibration/urban_diagnosis_20261117/warehouse_handling_exposure.json.
Use ONLY original monthly central/low arrivals and inter_exported plus matching
prepared model nodes/geometry/fixed resident requests. Include all original towns,
including zeros; no selection/raw city tables/new cohorts. Build a RATE-FREE
incoming/outgoing handling basis qin/qout, preserving original bins/year wrap.
Required hours remain symbolic qin*h_in+qout*h_out with rates UNKNOWN, not set to1
or derived from rural unspent time. Exact direct+inter_received=arrivals and
ordered shipment reconstruction of exported/received first. Annual/peak exposure
and ratios per fixed resident REQUEST where positive; undefined ratios unknown.
No actual warehouse mapping, staff assignment, task-budget/handling converter,
food/stock/route solver, new Earth scenario or numeric rate sweep. One paired
inspection figure/compact receipts if useful. Continue after push per user intent.

Source findings completed this continuation:
- Archived work evidence audit:22 exact interface/report statements,10 archived
  normative task counts. Old Columella2/FAO raw caches missing. One old cereal-map
  receipt pins earlier land_people.py; exact old whole-recipe identity NOT
  requalified, mismatch retained. Existing farm LP/monthly staff mechanisms can
  be reused with explicit inputs; scenario windows/loads/rates are not observations.
- Columella11.2:101 paragraphs,39 located claims,90 independent literal checks.
  Declared Chicago EnglishXI404; both language links commented/not_online. Frozen
  adapter uses publisher-linked LatinLibrary site witness. Its exact critical
  edition remains unverified; English is our paraphrase. Source dates unconverted.
- Same chapter concordance:6 selected online paragraphs EXACT across LatinLibrary/
  Wiki revision134877, but printed p433/scan439 OMITS bis in11.2.46. Digital text
  includes it. Other5 targets agree in substance with spelling/numeral variants.
  Titlepage5+six scans visually inspected. Printed title says Gesner recension,
  volume2, Biponti1787; Wiki index says Pseudo-Gesner/Pseudo-1787, flags UNEXPLAINED.
  No whole-edition equivalence or independent textual descent proven. Variant
  UNRECONCILED; old source packet/model coefficients remain unchanged. Primary
  calendar records two attributed solstices, straw30-day interval, original
  modii/opera and fibrae markers without modern date/area/stage conversion.

Raw source HTML/images/OCR remain local/ignored under each source packet/source/;
restore recorded URLs/digests before fresh replay. Qualified producers/outputs
refuse overwrite. Reserved Buringh size/climate pools and site-survey workbook
unopened; climate/steppe deferred. Prior entries below are historical instructions.

# Previous six-expression concordance completion — 17 November 2026

# Six-expression concordance complete; original work diagnostic map next — 17 November 2026

Latest report reports/COLUMELLA_CONCORDANCE_20261117.md and qualification
output/urban_columella_concordance_20261117/qualification.json. Exactly6already-
exposed11.2locations3/6/9/26/46/94 compared. LatinLibrary andWiki revision134877
paragraphsEXACT atallsix. Separatelyviewedtitlepage5andsixscannedpages proveone
SUBSTANTIVEvariant:§46digitalliranturiugeraduoBISoperauna,printedpage433(scan439)
liranturjugeraduooperauna,NO bis. Bothretained,notreconciled orselectedasmodelrate.
Other5targetexpressionsagreeinsubstance (quatuor/quattuor,sarit/sarrit spelling,
spelled/Romannumeralsretained). No modern date/bin conversions oroldpacket edits.
Independent reviewandall1103protected identities PASS;zero solver/modelinputcalls.

Printedtitle: ScriptoresreirusticaeveteresLatini,erecensioneJo.Matth.Gesneri,
vol2Columellam,Biponti,ExTypographiaSocietatis,1787. Actualtitleimageinspected.
WikiindexcallsPseudo-Gesner/Pseudo-1787;Commons/IAdescribe1787. Metadataflags
UNEXPLAINED,wholecriticaledition/digital-scan equivalenceNOTestablished. Identical
onlineparagraphsNOTindependentdescentproof. Wiki-link scan isimportant:don'ttreat
online transcriptionasproofitfaithfullyreproduces everyprintedword. Mainfirst
LatinLibrarysourceeditionremainsunverified. Publicconcordance/visualreceiptssmall;
rawWikiHTML/metadata,titleandselectedscanJPEG/OCRLOCAL/IGNOREDsource/. Source
readingsremainprescriptions,notmeasuredtaskrate/fulloccupation/handleridentity.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_work_diagnostic_map.json:
read-onlyoriginalB600central/low diagnosticfigure,exactly4panels (annual listed
crop-workutilization%,unspentlistedallowance hours/km²;tworeadingscolumns).
Originalcomponentwork+calendar sourceIDs+preparedgeometry/cellareaonly;verify
qualifiedbytes/sourceorder/ruralalignment. MapatPHYSICALSOURCEcells,nocities/
ports/warehouseassignment. Same0–100%scaleandfixedpositive log.01–10000h/km²;
zeroseparate,no-workforceutilizationundefined. Recordplot-onlyroundoff/scaleclipping,
neverchangesourcebudgets/tolerances. Summary2rows+localplotarrays/digests;independent
allsourcevalue/mask/formulachecks andold14.24%/16.16%unusedfraction. NoLP/work/
food/stock/graph/climate/phenology/populationcall/newEarthcase orstaffadoption.
Labelpartiallistedcerealscenario;unspentallowanceisNOTlogisticsstaff. Continueafter
push:makeconstraintsvisiblewithoutanothernumericvariant/mainatlasrelease.

Thiscontinuationalsocompleted22-rowarchivedevidenceaudit+oneLatinprimarycalendar
(101paras,39claims,90literalchecks).EnglishXIunavailable404;frozenLatinadapter
used. Two oldfarmrawcachesmissing;oneoldcerealmapbuilderidentitydriftretained.
Nooldscienceoutputs changed. ReservedBuringhpools/site-surveyworkbookunopened;
climate/steppe deferred;noactualpopulation/atlas/defaultchange. Priorentrieshistory.

# Previous primary calendar completion — 17 November 2026

# Primary calendar witness complete; six-expression concordance next — 17 November 2026

Latest report reports/COLUMELLA_CALENDAR_20261117.md. Qualification:
output/urban_columella_calendar_20261117/qualification.json,
passed_faithful_Latin_calendar_witness_with_edition_and_calendar_transfer_limits.
Columella De re rustica11.2:101paragraphs,39located task/calendar claims,90
independent literalanchor/date/numberchecks. Complete sourcecoverage/digests.
All1103 protected identities exact;zero solver/newEarthfood/staff/modelinput calls.

Source access resolution:declaredLacusCurtius EnglishbookXI404. Publisherindex
showsBOTH XI Latin/English anchors commentedout/not_online. Committed adapter
6d4a94708 authorizes SAMEchapter via publisher-linked LatinLibrary publictext,
notan unavailabletranslation/scan. Exposure BEFORE eachbody. CanonicalURL:
https://www.thelatinlibrary.com/columella/columella.rr11.shtml ,body80263bytes,
sha2566df5bdd11e459bb9efa5a8822ba642bbc63bbf31f11156bb5dc1086263e2bc7c.
Catalogue/book/chapterII1–101boundariesverified. Publishergeneralassertion says
Lundstrom,butdirectbookpage givesnoeditionmetadata. ExactcriticaleditionNOT
independentlyestablished. Qualification isfaithfulSITEWITNESS/limits. OurEnglish
isparaphrase,notattributedtranslation. Rawfullbook/index/catalogue/failureHTML/
privateparagraphJSON LOCAL/IGNOREDsource/. OtherchaptersI/III incidentally
retrieved/partlyvisible,notextracted. RestoreURL/digestbeforefreshreplay.

Findings:weather/soil/regional/developmentconditionaltasks,competingweeding/hay/
threshing/straw/animalfeeding/day/nightwork. No fullmeasured monthlyoccupation,
warehousehandlingrate,staffaffiliation oroperationalcapacity/rights. §54thirtydays
isCUTSTRAW handling,notgrainwarehouseresidence. §47solstice deadline explicitfor
vinework,notrecastasfloorprepdeadline. §94TWOsolsticemarkers XVI Kal.Ian.(Hipparchus)
andVIIII Kal.Ian.(Chaldean),bothretained/unconverted. §9quattuorfibrarum notmapped
tomodernstage;§26modiostresunaopera notconvertedtoarea;§46liranturiugeraduobis
operauna clauseunresolved/unrepaired. §82earlierworknormexplicitlyquestioned.
Sourceoperæ/horae areNOTassumed8modernhours. NoGregorian/modelbin conversion.

NEXT FROZEN calibration/urban_diagnosis_20261117/columella_calendar_concordance.json:
ONE separatelyidentified public-domain witness ofSAME11.2. BeginWikisource
De_Re_Rustica_(Gesner)/Liber_XI +linkedscan/index/titlepagemetadata. Verifyeditor/
edition/year/chaptercorrespondenceBEFOREcomparison. Exactly6alreadyexposed
locations:3(halfmonth/15days),6(semestrium),9(fibrae),26(modii/opera),46(lira/bis/
opera),94(twoattributedsolstices). Preserveorthography/numerals/editionsandunknown
meaning;no silentoldpacket/modelcorrection. No widertextmining,newcohort,sourcefit,
calendarconversion orsolvers. Allsamechapterwitnessesdevelopment,notindependent
historicalvalidation. Continueafterpush;userwantsongoingwork.

Also completedthiscontinuation:22-rowarchived evidence/interfaceaudit,10archived
taskcounts,2missingoldsourcecachesretained. Oneoldcereal-mapreceipt pins earlier
land_people.py;exactoldwhole-recipeidentityNOTrequalified,currentmodelsunchanged.
Existing farmLP/monthlystaffinterfaces reusable butwindows/loads/handlingrates
remainassumptions. No oldsourcecachehash replaced. Reserved Buringh pools/site-
surveyworkbook unopened;climate/steppe deferred;population/atlasunchanged.
Previousentriesbelow arehistorical instructions forcompletedstages.

# Previous archived evidence audit completion — 17 November 2026

# Archived work evidence audit complete; primary calendar next — 17 November 2026

Latest report reports/WORK_EVIDENCE_SCOPE_20261117.md. Qualification
output/urban_work_evidence_20261117/qualification.json,passed_faithful_work_evidence_audit_with_primary_cache_and_old_recipe_identity_limits.
22 exact archived/source-interface rows,10prescribed-as-archived taskcounts;
all1103 protected identities unchanged. Zero newsource bodies/solver calls.

Reusable farm-operation LP and monthly staff mechanisms already exist. Demo
windows,collectorloads/handlingtimes,workday/area andavailability remain supplied
scenarios. Columella2.12 counts concern listed tasks tothreshingfloor,notcomplete
occupation. No fullEarth baseline monthlyschedule orwarehouse handlingintensity
qualified. Two oldrawcaches absent (Columella2 andFAO);metadatahashes preserved,
notreplaced orfreshlyverified. Farm/requiredwork/monthlywork codeidentity matches.
Oldcereal-map receipt instead pins earlier scripts/land_people.py:
recordedb344faae07f411b125fb09f5838f6d9d893fa6bf4017ab62cd0707bd0025d1ae,
currentb2c46780c9504f00233afc742c444f8f513431d01bb6b72ce2d55894a6f52bc8.
Exactold whole-maprecipe NOT requalified;old_receipt_status.json retainsboth.
Nooldsource/outputchanged,nomaprerun. Quote-gate andoldidentity-gate failures
retained;newqualification isfaithful reportingoflimits,notoldmapreplayapproval.

NEXT FROZEN calibration/urban_diagnosis_20261117/columella_calendar_source.json:
ONEprimary agriculturalcalendar,Columella De re rustica11.2. Beforefetch,write
exposure receipt. StartpublicLacusCurtius Chicago bookXI11*.html#2,verifyedition,
title/book/chapter/paragraphboundaries andeditorialcontext BEFOREtranscription.
SamechapterLatinallowedforidentity/taskcalendarcrosscheck. RawbookHTMLlocal/
ignored,analyticalchapter2only;recordincidentalbookretrievalanddevelopmentexposure.
Ledgercereal landprep,sowing,harrowing/hoeing/weeding,reaping/threshing/processing/
storage wherepresent,explicitcompetingduties/geographiclimits;paratextseparate.
Roman/astronomicaldates remainSOURCEIDENTIFIERS,notGregorian/modelbins. Missing
hours,completeoccupation,handlers/materialunitsremainunknown. NoEarthcase,
sourcefit,LP/work/stock/food/graph/weather/phenology/demographiccalls oradoption.
Do not fetcholdmissingcaches aspartofthisnewcalendarcollection. Continueafterpush.

Climate/steppe deferred;reserved Buringh pools/site-surveyworkbook unopened.
Oldqualifiedproducers/packets frozen;nextstagefaithful sourcequalification isnot
calibratedwindow/workrate adoption. Priorentriesbelow arehistory.

# Previous grain/work bridge completion — 17 November 2026

# Grain/work bridge complete; existing evidence and scheduler audit next — 17 November 2026

Latest report: reports/WAREHOUSE_GRAIN_WORK_COUPLING_20261117.md.
Qualification: output/urban_warehouse_coupling_20261117/qualification.json,
passed_three_manufactured_paid_grain_and_shared_work_coupling_controls.
No jobs at completion. This continuation worked across five completed stages
and their pushes; four new isolated modules pass93 tests (34nohold,21roles,
24taskbudget,14handlingclaims). All1103 protected identities remain exact.

Completed this continuation:
- NoHoldLedger:8declared manufactured cases +exactly2original baseline arrival
  reductions,all8arrays EXACT,1,250,180records INCLUDING zeros. Nofood/stocksolve.
- Shared physical store acrosscommercial/town roles:7manufactured scenarios,
  7direct aggregate controls,ALL15FoodYear fields EXACT;one capacity/stock.
  Adapter13canonicalyears,reference13,reviewer7;all0annual-map advances.
- Original B600work-readiness:10contracts,4schemas,112756scalar rows;14.24%/
  16.16%unspent listedallowance isNOTstaff;84.62%listedwork lacksmonthlytiming.
  Relative reapinglimitneverbinds (max38.46%);absolute nearcounts tinyfloorartifacts
  retained withdiagnostics. Zero oldmodelcalls.
- TaskBudget:stateful oneannual/monthlyphysicalworkforce acrossbaseline+roles;
  8declared outcomes3accept/5reject,independent scalarchecks. Missing complete
  baseline fails;duplicateIDs/overruns/cross-workforceborrowing cannotfundtasks.
- handling_claims:EXACTLY3couplings fromfrozen priority_ab/ba receipts;zero role/
  sharedstore/food/stocksolverreruns. Positive DELIVERED arrivals unload once;
  actual PAID withdrawals create work,notrequests. Units/rates/crewexplicit.

Latest coupling:one manufactured crew annual11h/monthly10h/baseline6hbin0;
toyrates unloading.01h/deliveredkcal,commercial.2/town.5h/paidkcal. Same15grain:
AB13+2pays→4.8additional/10.8totalh PASS;BA11+4→5.4/11.4h annualFAIL;
ABincompletebaselineFAIL. No priority orrateadoption. Tasks5/6/5 (16total),
independentlyderived with exact decimalFractions. Initial reviewer fixed-count
assertion andfollowupmetadata assumed5allcases;bothfailures retained,corrected
againstsourcecells. Producer/converter/grain/stock notchanged orreexecuted for
those fixes. Producer3converters,3noholdmaterializations+3revalidations;reviewer
0newconverter/checker calls. All originalgrainoutputs/capacities unchanged.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_work_evidence_scope.json:
read-only existingevidence/scheduler audit beforefurther variants. Inspect existing
research_notes/farm_labour_20261103.json,harvest/labour.py,harvest/work_maps.py,
polity/monthly_work.py andtheir reports/protocols,newworkcontracts. Distinguish
Columella's prescriptive listedtasks frommanufactured windows/collectorloads/
handlingtimes. Existing LP/montlystaffmechanisms maybereusable,buttheir scenario
coefficients areNOTempirical inputs. Make task/timing observed/prescribed/assumed/
unknown ledger,interface reusemap,andONEconcrete primaryevidence target/declaration
ifjustified. No newsourcebody,cohort,LP/work/food/stock/graph/weather/phenologysolve,
rate/prioritysweep,staffassignment,newEarthcase orfit inthisscope. Afterfinitebridge,
prioritize missingevidence ratherthanmoretoyvariants. Userrequestedongoingwork.

Earth attachment stillneeds complete non-reaping baseline timing,handler
sourceaffiliation/travel,task/material/handling evidence,operationalcapacity and
rights. Currentengineeringpass doesNOTqualifythese. No actualwarehouse/staff,
population,land,recruitment oratlas/default changes. Reserved Buringh size/climate
pools andsite-surveyworkbook unopened;climate/steppe deferred. Completed packets
andproducers frozen;isolated OUT required forreplay. Priorentries arehistorical.

# Previous shared task-budget completion — 17 November 2026

# Shared task budgets complete; three-case grain/work bridge next — 17 November 2026

Latest report: reports/WAREHOUSE_TASK_BUDGET_20261117.md. Qualification:
output/urban_warehouse_tasks_20261117/qualification.json. The new isolated
polity/task_budget.py passes24 tests. Eight finite manufactured outcomes match
independent scalar checks:3accepted/5rejected,reviewer0checker calls. One physical
workforce's annual/monthly budget persists across role reservations;failed batches
claim no IDs/hours. Baseline task IDs cannot be debited again. Complete baseline
schedule and consistent annual use required;no reaping-only monthly substitute.
All1103 protected identities exact;zero old work/food/stock/graph/weather solves.

This continuation has completed nohold34tests+2exactbaseline arrival controls,
sharedroles21tests+7manufactured/7exactaggregate stockcontrols,read-only original
work-readiness audit,and taskbudget24tests+8outcomes.79new module tests total.
No Earthwarehouse/staffcase oractualpopulation/atlas/default change. Capacity,
rights,handlingrates,physicalstaffaffiliation/fullmonthlybaseline still unqualified.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_grain_work_coupling_controls.json:
exactly3 manufactured claim conversions from EXISTING priority_ab/priority_ba
shared-role receipts. No inventory/role/food solver rerun. Supplied toy unloading
rate.01h/deliveredkcal,commercial.2h/paidkcal,town.5h/paidkcal;onecrew annual11h,
monthly10h,baseline6h inbin0. AB has4.8additional/10.8total→accept;BA has5.4/11.4
→annualreject despite SAME15grain total;ABwith incompletebaseline→reject.
Generate named tasks once from actual delivered arrivals/paid withdrawals,never
requests;explicit IDs/bin/role/workforce,then reserve TaskBudget once. Independent
receipt/task/hour review. No newgrain dispatch,priorities,staff/ratesadoption,
newEarthcase orfit. Afterthisfinitebridge,prioritize missingevidence inputsover
more numerical variants. Continue afterpush,peruser's ongoingwork instruction.

Work-readiness limitation:14.24%/16.16% unspent listed cereal allowance isnot
logisticsstaff;84.62% oflistedwork hasno monthlytiming. Reaping maxutil38.46%,
zero relativebinding;absolute-near counts are minute tolerance-floor artifacts.
Raw counts/diagnostics retained. Reserved Buringh pools/site-survey workbook
unopened;climate/steppe deferred. Prior entries below are historical.

# Previous work-readiness completion — 17 November 2026

# Physical-work readiness complete; shared task budgets next — 17 November 2026

Latest report reports/WAREHOUSE_WORK_READINESS_20261117.md and qualification
output/urban_warehouse_work_20261117/qualification.json. Read-only originalB600
central/low audit complete:10 source contracts,4schemas,112756scalar source rows,
exact original source/rural alignment. Zero component_work/food/stock/graph/
Dijkstra/weather/crop/population solves. All1103 protected identities exact.

Original listed cereal-work allowance unused14.2439%central/16.1581%low. This is
NOT logisticsstaff. Annualworkused includesreaping;84.6154%oflistedwork hasNO
monthlyplacement inarchives. Reaping-only peakarrays cannotserve ascomplete
monthlyoccupation. No handler affiliation,task/material unit rate ortravelinput.
Absolute-near reapingcounts4761/4759 are tinyworkforce/tolerancefloor artifacts
(allowances<2e-8hours,total<9e-7). Relativebindingreapingcount0,maxutil38.461539%.
Originalcounts plusindependent limit_diagnostics.json retained;no budget/tolerance
changed. Rawunusedmin-5.82e-11hoursroundoff retained at oldworktolerance.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json:
implement isolated shared task-budget constraint checker with explicit complete
manufactured baseline monthlyschedule,consistent annualuse,one physical workforce
budget and supplied taskhours/month/role. Exactly8declared cases:3accept,5reject
(annual-only,monthly-only,double-rolecapacity,cross-workforceborrowing,incomplete
schedule). No logisticsrate derived orstaffrecruited;reject unknownmonthlybaseline
ratherthanfillzero. Samephysicalbudget mustnot be copiedperrole;validate unique
workforce/task IDs andexisting1e-8worktolerance. Independentscalarchecks;zero old
work/food/stock/graphsolves. Passing checker doesNOTsupply missingEarth schedule.

Thiscontinuation alreadycompleted nohold34tests+2exactoriginalarrivalreplays and
sharedroles21tests+7manufactured/7exactaggregateinventorycontrols beforethisaudit,
continuingpastpushes. Continuefinite task-budget step aftercommitting audit.
No Earthwarehousecase,physicalstaffassignment,newfit,actualpopulation oratlas
change. Reserved Buringh pools/site-surveyworkbook unopened;climate/steppe deferred.
Old producers/packets frozen;priorentries below arehistorical next-step records.

# Previous shared-role completion — 17 November 2026

# Shared roles complete; read-only physical-work readiness next — 17 November 2026

Latest report reports/WAREHOUSE_SHARED_ROLES_20261117.md and qualification
output/urban_warehouse_roles_20261117/qualification.json. New isolated adapter
polity/warehouse_roles.py passes21 tests. Seven finite manufactured scenarios
and seven direct aggregate shared-store reductions pass ALL15FoodYear fields
EXACT. Independent canonical replay/physical monthly ledger and priority checks
pass seven cases,zero adapter calls. Periodic tolerance ratio0,maxgrainresidual
1.42e-14kcal. All1103 protected identities exact. No jobs at stage completion.

Funded no-hold receipts revalidated/unique;explicit store assignment must match
physical paid endpoint. Repeat arrivals from same physical origin/store coalesced.
One capacity/stock perunique store,one distinct supplied node perstore;multiple
buildings inonegrid unsupported. Role requests share one inventory,then actual
withdrawals allocated by explicit fixed priority. No role duplicates capacity.
Cap5 priorityAB pays[13,2],BA[11,4],same15total andidenticalaggregateinventory.
Dry secondstore gets0;zero deliveredgrain gets0;zerocap carries0. Stored5%loss
andyearwrap included. Honest kernel counts:adapter7→13canonicalyears;reference
7→13years;reviewer7years. All0annualmap advances. Pytest counted separately.
These are7manufactured scenarios,0newEarthcases,0actualwarehouse mappings.
Upstream rural/work funding,handlingstaff,capacity/rights NOT certified.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_work_readiness.json:
read-only source/schema and aggregate audit of ORIGINAL B600central/low component
work + monthly source/rural ordering. Check workers=.4*rural,annual600h allowance,
harvest-bin min(annual,workers*30*8),listedannualuse,reaping-onlymonthlypeakuse,
unusedlistedallowance andbinding counts at existing tolerance. No component_work,
food/stock/graph/weather/crop/population solver calls. Unspent cereal allowance
is NOT available port labor or complete monthly work. Identify missing task/unit,
time andstaffaffiliation input contracts before any futurehandling calculation.
No newlogistics coefficient,recruitment,physicaldays,newEarthcase orfit.

Continue thisaudit afterpush;user requested ongoingwork acrosscommits. No-hold
stage also completed thiscontinuation (34tests,8manufactured cases,2exactbaseline
arrival reductions/8arrays,1,250,180records includingzeros,0food/stock solves).
All old producers/packets frozen. Reserved Buringh size/climate pools andsite-survey
workbook unopened;climate/steppe deferred;actual population/atlas unchanged.
Previous entries are history;do not rerun their completed next-stage instructions.

# Previous no-hold accounting completion — 17 November 2026

# No-hold accounting complete; shared-role integration next — 17 November 2026

Latest report reports/WAREHOUSE_NO_HOLD_20261117.md and qualification
output/urban_warehouse_no_hold_20261117/qualification.json. New isolated
polity/no_hold.py passes34 tests. Eight declared manufactured cases and exactly
two original baseline accounting reductions completed and independently checked.
All8 original direct/inter_received/inter_exported/arrivals arrays EXACT.
1,250,180 consignment records INCLUDING zeros (625315 central,624865 low),
not that many positive shipments or new routes. Producer8+26 ledger calls,
reviewer0 new-ledger calls. Zero food/stock solves,graphs,Dijkstra,new Earthcases.
No jobs at stage completion; all1103 protected identities exact.

Consignment IDs unique within/across calls; invalid batches claim no IDs.
Original sent/delivered charge and one-bin arrival preserved,including year wrap.
Explicit event charges annotate one movement,not new funding or time. No physical
capacity/rights inferred. Charge allocation residual0 in both legacy controls;
aggregate floating totals residual central-.00390625/low+.001953125kcal retained
at original grain tolerance,not adjusted. Funding itself still needs upstream
protected-rural/work evidence; new IDs cannot authenticate external grain.
Independent scalar arrival accumulation and exact Fraction manufactured checks.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json:
connect funded receipts once to one physical inventory/capacity across explicit
commercial/town roles,with supplied fixed withdrawal priority. Exactly7 finite
manufactured scenarios and7 direct aggregate reductions,ALL15FoodYear fields
exact;count canonical year/map calls for each phase separately. Reject duplicate
funding,endpoint/store mismatch,invalid roles/mappings/priority/material/permission.
Role paid sums to store departures at original grain tolerance. No cross-store
borrowing or capacity/stock multiplication. Independent original-tolerance
inventory replay from recorded initial stock,zero new-role-adapter reviewer calls.
No Earth cases or realstore mapping/work/rights/capacity adoption. Climate later.

Reserved Buringh size/climate pools and site-survey workbook unopened. No fit,
actual people/staff/land/recruitment or atlas/default changes. Completed producers
and packets frozen;isolated OUT and matching test receipts required for replay.
Previous entries below are history. Continue integration after committing thisstage.

# Previous original-route provenance completion — 17 November 2026

# Original route provenance complete; no-hold contract next — 17 November 2026

Latest report: reports/WAREHOUSE_ROUTE_PROVENANCE_20261117.md. Inspection figure:
output/urban_warehouse_routes_20261117/original_routes.png. Qualification:
output/urban_warehouse_routes_20261117/qualification.json, status
passed_sixteen_original_route_certificates_with_exact_archived_costs_and_owners.
No jobs running at completion. This continuation completed shared warehouse,
read-only readiness and route recovery, continuing across their pushes.

Sixteen funded original routes selected and committed BEFORE graph calls in
cd604ca5e, with no outcome substitutions. Exact original captured world restored
using original grid/biome/road/strait/sea recipe; no weather reader, wind fallback
or raw city table. Four canonical legacy graphs, eight Dijkstra calls, zero
new full all-pairs tables. Full source owners/distances EXACT at archived dtype
for both readings/all quarters; eight selected forward intertown costs EXACT.
Independent review: 16 rankings/chains, 1148 directed edge occurrences; max
cost-sum error 1.14e-13 at existing path tolerance. Reviewer zero canonical graph
or Dijkstra calls, four independent CSR assemblies from saved raw records.
All 1103 protected identities unchanged. Zero food/stock solves or new cases.

Six distinct chains among 16 records. Largest source leg is 215876→215276,
9 road-km, same all quarters/readings. Intertown sender 141127 (western North
Africa), central destination 105258 (central Italy); low Q0 destination 111271,
otherwise same central route. Costs central 267.59/224.50/152.47/177.61 road-km.
These are funded sent-quantity selections, not largest delivered grain or a
representative atlas sample. Selected edges have no summed parallel records;
that does NOT prove full graph equivalence to the alternative freight connector.
Model port/river-landing memberships and auxiliary mappings retained explicitly;
not authenticated buildings, storage, rights, unique old paths or physical days.

Compact node/edge certificates and inspected map are tracked. Full raw legacy
CSR/predecessor caches (~130 MB) remain local/ignored under output packet/local,
pinned in results/qualification. Completed producers refuse overwrite. Initial
selector was interrupted before output for repeated archive decompression; fixed
to load once, incident retained, zero graph/food calls in interrupted attempt.
No route reconstruction failure or identity mismatch occurred.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_no_hold_contract.json:
implement isolated consignment/event accounting with one funding/whole-leg charge
and original endpoint arrival bin, including year wrap. Intermediate events cannot
multiply retention or add an automatic bin. Explicit charge allocation must
conserve the original charge; exact endpoint grain remains authoritative. Declare
finite manufactured conservation/timing/rejection controls before execution,
then EXACTLY TWO original baseline arrival-accounting reductions (central/low),
no food/stock solve. Require exact original direct/intertown arrival arrays and
operation order. Duplicate funding, invalid IDs/amounts/holds fail. No Dijkstra,
new routes, parameter sweep, actual warehouse mapping or food scenario. Positive
hold, physical capacity/rights/handling work and cross-role capacity deduplication
require later declarations. A consignment event is not warehouse evidence.

Climate/steppe deferred; reserved Buringh size/climate l and site-survey workbook
unopened. No new fit, actual population/staff or atlas/default adoption. Prior
entries below are history; do not execute their completed next-stage instructions.

# Previous readiness completion — 17 November 2026

# Shared-store readiness complete; bounded route recovery next — 17 November 2026

Latest report: reports/SHARED_STORE_READINESS_20261117.md. Qualification:
output/urban_shared_store_readiness_20261117/qualification.json, status
passed_read_only_shared_store_coupling_contract_and_schema_audit. Fifteen exact
interface quotes and six archive schemas checked independently; all 1103
protected identities unchanged. Zero graph rebuilds, Dijkstra, food calls or
new Earth food scenarios. No jobs running at completion.

Saved costs/owners do not retain chosen paths or warehouse identities. Of
56,378 origins, 4,050 change recipient across quarters (3,458 central/3,457 low
actually export). Quarter-varying owner IDs cannot identify fixed stores.
Transport snapshot omits road, biome and cell size; original road is available,
but restore all inputs from the exact old 1981–2010 recipe. Do not use the
1991–2020 fallback. Legacy CSR sums parallel records; the isolated freight
connector selects alternatives, so substituting it would change the graph.

Two accounting contracts remain before insertion: multiplying subleg retention
adds ab/L² relative to the current whole-leg rule; an extra ordinary leg adds
a bin even with zero storage hold. No-hold pass-through must conserve original
charged grain and arrival timing. Road-km cost is not physical travel days.
Physical store capacity, rights, role overlap and handling work remain unknown.
The completed shared ledger (19 tests/four exact reductions) is engineering,
not historical qualification of a warehouse attachment.

NEXT FROZEN calibration/urban_diagnosis_20261117/warehouse_route_provenance_controls.json:
freeze at most 16 original positive route selections BEFORE graph calls, one
source and one intertown leg per quarter/reading, ranked by recorded funded
quantity with physical-ID ties. Rebuild only the four original legacy graphs;
verify full original reverse source owners/distances exactly and selected
forward intertown costs exactly before interpreting paths. Retain directed
node/edge chains, auxiliary/port provenance and mode/parallel ambiguities.
Do not infer an unrecorded unique path, physical duration or warehouse site.
If restoration/identity fails, preserve the failure and stop dependent route
interpretation; no tuning. No new all-pairs table, dispatch, stock solve,
capacity/rights adoption, food scenario, fitting, population or atlas changes.

Climate/steppe deferred; reserved Buringh size/climate l and site-survey workbook
unopened. Existing completed producers and outputs are frozen; isolated OUT
required for fresh replay. Previous entries below are historical instructions.

# Previous shared warehouse completion — 17 November 2026

# Shared warehouse complete; route-coupling readiness next — 17 November 2026

Latest report reports/SHARED_WAREHOUSE_20261117.md and qualification
output/urban_shared_warehouse_20261117/qualification.json.19tests pass for new
isolated polity/shared_warehouse.py.5manufactured scenarios+EXACTLY4legacy
export-store reductions (central/low×5%/0loss,90day cap) completed and reviewed.
ALL15FoodYear fields AND departures EXACT for eachcontrol,225512origin-store
rows. No newEarthmeal scenario or actualport assignment. No jobs running.

One unique physicalID/capacity perstore;explicitorigin partition and withdrawals;
matching netmaterial/pool labels;boolean scenario pooling permission required
for multiple origins. Unknown/negative/nonfinitecapacity,deposits withoutstore,
duplicateIDs and incompatiblepools rejected. No automaticquota/capacity resizing.
Zero capacity can pay immediatefundedwithdrawal butcarry0;zero deposits cannot
fund inheritedfood. Signed/unsigned integerpartitions supported. Rights/history
NOT inferred;deposits require upstream protected-rural/work certificate outside
the primitive. No routing,owner allocation,people/work or default changes.

Independent grouping+original-tolerance stock/physicalledger review PASS9groups;
maxinventory ratio.546307,compensatedwholegrainresidual0. Count kernel calls
honestly:producer5manufactured adapters→7canonical_year;4legacy adapters→6years,
0canonicalannualmap_advances. Reviewer0sharedadaptercalls,5canonicalyears+
102annualmap_advances. Pytest separate. Completedreceipts pin thiscall scope.
1103protected identities unchanged;oldfoodadapters/outputs remain frozen.

NEXT FROZEN calibration/urban_diagnosis_20261117/shared_store_coupling_readiness.json:
read-only source/schema contract audit before any sharedwarehouse network.
Inspect existing prepared/monthly key shapes and code:protected deposits,
physical ID/capacity,seasonal source→store allocation,chosen-path/predecessor/
port provenance,paid cost/retention/travel timing,rights,potentialcommercial/town
capacity overlap,handlingwork and upstream food/work/people. No Dijkstra,food,
climate or phenologycalls,route rebuild,mapping/clustering,source measurements,
parameter variants or demographics. Existing source scan suggests prepared
captures deliberately omit predecessors (assertnotpredecessors) and retain only
endpointcost/owner matrices;confirm in the declared audit before concluding.
Do not infer ports from endpoints/nearestcoast or quarterowner asphysicalID.

Continue thisaudit after committing/pushing theprimitive. If paths missing,
declare tightly bounded original-route reconstruction controls;do not invent an
Earthwarehouse network. Current-Ostia source arithmetic/commodity/geometry/
duration/rights remain unqualified for numeric adoption. Rawsourcecache local.
Reserved Buringh size/climate l andsite-surveyworkbook unopened;climate/steppe
deferred;atlas/population unchanged. Full diet/work,rights and independent
transfer gates persist. All completed producers refuseoverwrite;isolated OUT
and pinnedtestreceipt needed for fresh replay. Previous entries are history.

# Previous completed primary Ostia source — 17 November 2026

Latest report reports/URBAN_OSTIA_STORAGE_20261117.md and qualification
output/urban_ostia_storage_20261117/qualification.json. This turn continued past
methods95993e93c and explicit-contract364e6d11f pushes into ONEprimary source.
Boetto/Bukowiecki/Monteix/Rousse2016,Les Grandi Horrea d'Ostie,CEFR522,pp177–226,
chapterDOI10.4000/books.efr.32815. Publisher fullHTML+HALauthor-deposit mirror
identity checked;81paragraphs/50printedpages,61numeric source claims,18context
rows,7capacity estimate rows,81numeric token checks/10Decimal column diagnostics.
No jobs running. Zero newfood/climate/phenology runs,network attachments,fit,
actualpopulation/staff or atlas/default changes. All1103protected identities exact.

Important retained NEGATIVES:contents not positively identified;wheat is AUTHOR
CONVENTION. First Severan phase selected,not allphases pooled. Pile/sack heights,
geometry,upperstorey and preservation months include hypotheses/modernanalogies.
Destination Rome versus priorityOstia remains unresolved. Model days/rights not
inferred. Neither new geometric netenergy nor operational capacity qualified.

Source TABLEp217 has unaligned columns under its own8.76L/modius convention:
Nord349m3vs30772modii implies269.56272m3,difference79.43728m3.
Central-sack753m3vs83904modii implies734.99904m3,difference18.00096m3.
Printed formula,n114,p217adds length-cubed prism term to length-squared term;
confirmed inpublisherHTML/PDFimage,not OCR-only. Original table/formula left
UNRECONCILED and NOT adopted/corrected. Positive qualification means faithful
transcription/limits,not approval of numeric capacity. No automatic density,
height,edibleyield or operational-load imputation. Source740kg/m3is a proposed
author convention,not a measured input to our model. No source→city/pool crossing.

Provenance:publisher meta citation_doi contains BOOK32730;citation modal verifies
CHAPTER32815. Booktitlepage522/publisher177–226 override secondary552/322and178
variants. PublicHTMLordinaryfetch succeeded;someweb/HALrequests hadbotprotection,
no challengebypass. Mirror carries HAL01441802titlecover;only PDFpages7–56
(printed177–226)used. Extra frontmatter/bibliography/index not a newcohort.
Initial page-header-parity gate failure retained before any source-data outputs.
All chapter/incidentally visible comparison examples are DEVELOPMENT exposure;
Portus/Vienne/external examples not extracted as additional sites. Initial
before-reading exposure.json remains unchanged. Raw HTML/PDF/text in source/
LOCAL/IGNORED;public facts/locators/digests/negativechecks tracked. Restore via
source_identity.json access URIs/digests before replay;web wrappers may change.
Qualified extract/review/seal refuseoverwrite,use isolated OUT;old stages frozen.

NEXT FROZEN calibration/urban_diagnosis_20261117/shared_warehouse_primitive.json:
generic isolated ledger for several permitted origins funding ONEunique store,
with one explicit capacity and explicit monthly withdrawals. Unique storeIDs,
oneorigin→onestore partition,homogeneous netpool and explicitpooling permission;
reject duplicates,unknownnumeric capacity,unassigned positive deposits,invalid
values. Groupdeposits once,reuse qualified loss0/.05inventory/originaltolerance,
retain actualwithdrawals/spoil/overflow/stockΔ. Never auto-size capacity/quotas
or infer ownership. Manufactured sharing/partition/no-freegrain controls first,
then EXACTLY4existing export-store reduction replays:central/low×5%/0loss at90d
from output/urban_storage_loss_20261117,ALL15FoodYear fields exact. Count adapter/
canonical calls honestly;replays are controls,NOT newEarthfoodscenarios.
No realport mapping,sourcecapacity choice,newcitymeal run or routing/rights
integration yet. Source evidence motivates a separate storeidentity,not an
ancient globalcapacity or forced collective right. Buringh sizes/climate l and
site-survey workbook unopened;climate/steppe deferred. Full diet/work/resources,
rights and independent transfer gates remain before adoption. Previous entries
below are historical;all three tasks above are COMPLETE.

# Previous completed explicit capacity contract — 17 November 2026

Latest report reports/URBAN_STORAGE_CONTRACT_20261117.md and qualification
output/urban_storage_contract_20261117/qualification.json. Continued AFTER
pushing methods95993e93c. New isolated polity/storage_capacity.py has23passing
tests,7manufactured examples,5invalid-input receipts and18independent Decimal
checks. Six baseline model store-class totals EXACT to existing table;no stock
reruns,capacity changes,site observations,food/climate/phenology runs or adoption.
All1103protected identities unchanged. No jobs running.

Quantity records carry explicit unit,evidence kind,source/locator,known value
or unknown. Single commodity allocated to usable space;gross/mixed unallocated
space rejected. Density must match commodity/state;already-net material must
be explicitly net_edible and cannot receive repeated deductions. Known floor
mass limit rejects excess fill;unknown support/preservation/phase/access stays
visible. Outputs are GEOMETRIC volume/mass/netenergy,never automatic operational
or historical capacity. Module always leaves operational_capacity_kcal unset
and empirically_qualifiedFalse,even if an input is labelledobservation.

Compatible positive explicit365day annualflow only for geometric dayequivalents;
missing/zero/incompatible flow leaves days undefined. No density/depth/yield/
energy/load defaults. Example numeric inputs are MANUFACTURED scenarios,not
Salido/Gentry ancient measurements. Existing rural365d/commercial365dofbaseline
market/town90d budgets remain scenarios;grid coordinates do not supply physical
facility location or operational evidence. Frozen food producers untouched.

NEXT FROZEN calibration/urban_diagnosis_20261117/ostia_store_source_qualification.json:
ONEcomplex/primary chapter,Boetto,Bukowiecki,Monteix,Rousse2016,Les Grandi Horrea
d'Ostie,in Marin/Virlouvet,Entrepôts et trafics annonaires en Méditerranée,
CollectionEFR522,pp177–226. Citation exposed in Salido;body NOT read yet.
Register DEVELOPMENT exposure beforebody,authenticate lawful full source bytes/
title/authors/year/pages/license and retain identity/access failures. Extract all
explicit relevant function/location/phase/commodity/access/geometry/material/
support/preservation/duration/flow statements for thiscomplex,with exact locators.
Separate measurement,reconstruction,author estimate,secondaryclaim,our derivation
and unknown;never sum incompatible phases or use gross mixed space as grain.
No plan digitization or inferred unprinted dimensions;no imputed height/density/
yield/load/rights/duration. No dividing by modeled market or city/network
attachment. Conditional/indeterminate geometry is valid. Zero newfoodfits.
Reserved Buringh size/climate l pools AND site-survey workbook unopened.

Proceed after committing/pushing this contract. Primary evidence now precedes
any numeric capacity/dispatch variant or finite-occupancy integration. Full
diet/resources/work,rights and independent transfer remain separate adoption
gates. Climate/steppe deferred;atlas/population unchanged. Previous entries below
retain historical states. Qualified stages refuseoverwrite;use isolated OUT
for fresh audit/review/seal replay,do not edit frozen code and reuse outputs.

# Previous completed archaeological methods review — 17 November 2026

Latest report reports/URBAN_STORAGE_METHODS_20261117.md and qualification
output/urban_storage_methods_20261117/qualification.json. Full Salido2018 source
read under the prior committed declaration;16-page publisher PDF retained with
CC BY4.0 attribution,DOI10.5209/GERI.60294. SHA256a4374b2b23e7cbfea88b3abe2ebb26fd71515a6ea2adb82bedf09c31d4608424.
Uncookied URL initially looped;locale cookie/session handling resolved access.
No secondary substitution.12method fields including all9§7factors;24anchors
match fresh layout/raw extraction,printed88–90 visually checked. No food jobs.

Decision:source supports distinguishing volume/material/function/phase and
turnover,NOT replacing90/365day or5%coefficients. Gross footprint is not cereal-
allocated usable volume;species,state,husk/container,working/ventilation space,
floor support and safe fill matter. §7.5harvest turnover/owner behavior is AUTHOR
INTERPRETATION,not a measured universal quota. §7.9residence neednot1year.
Functions change bybuilding phase;germination is not an annual decay coefficient.
Reported Gentry density/competingheight estimates were NOT adopted/verified.

Fullarticle/examples/figures are DEVELOPMENT exposure now. No numerical site,
height/density/capacity dataset extracted;raw text/PDF preserve source only.
No cited primary source opened/verified;VanOyen/Rickman bodies still unread.
All1103protected parent identities unchanged. No new food cases/climate/
phenology,fit,actual population/staff or atlas/default changes.

NEXT FROZEN calibration/urban_diagnosis_20261117/storage_capacity_contract.json:
isolated tested physical-store/unit contract,disconnected from food producers.
Explicit store identity,function/location/phase,access and input provenance.
Single allocated commodity;usable area×effectivefill→volume×matching-state
density→mass×net-edibleyield×edibleenergy/kg. OURbookkeeping,not Salido'slaw.
No defaults for geometry/material/load/edible conversion. Unknown inputs remain
unknown;gross/mixed allocations/state mismatch/double deductions must not pass.
Geometric energy≠operational capacity;floor support/preservation/duration and
rights/location still need evidence. Compatible positive explicitflow only for
day equivalents;zero/unknown flow leaves undefineddays. Arithmetic never
automatically qualifies empirical evidence. Meaningful synthetic/Decimal
controls;optional read-only labeling of six baseline store-class budgets,zero
stock reruns/capacity changes/source measurement extraction. Continue AFTER
committing/pushing this source stage. All prior sources/producers stay frozen.

Broader evidence→interface→food/work/finite-occupancy integration queue remains.
Complete diet/resources/work,rights and independent transfer before adoption.
Climate/steppe deferred,Buringh sizes/climate l unopened. Previous entries below
retain historical states;the first methods-body task is now COMPLETE.

# Previous completed storage source scoping — 17 November 2026

Latest: reports/URBAN_STORAGE_SOURCES_20261117.md and
output/urban_storage_source_scope_20261117/qualification.json. This read-only
stage followed the completed fixed-quota control (778c6ff0e, sealed34b8f02f5).
Nine exact existing contracts and three bibliographic leads are recorded.
No new food cases/kernel calls, phenology scores, archaeological measurement
extraction, fitting, population change or atlas/default adoption. No jobs running.
All1103protected identities and parent qualifications remain unchanged.

The plan now moves from numerical variants to evidence at the storage/dispatch
interface. Reserve algebra and modern FAO store sizing do not identify ancient
capacity/loss. An older consultation log already separates harvest receipts,
dispatch schedules and buffer capacity. Existing freight costs are not fleet
capacity or travel time; physical availability is not entitlement.

Bibliographic leads,all DEVELOPMENT exposure:
- Salido Domínguez2018,Gerión36(1)79-94,DOI10.5209/GERI.60294. Publisher
  metadata/abstract read;full article NOT read. Open methods critique is NEXT.
- Astrid Van Oyen2020,Control(Flow):Warehouses in the Ports of Ostia and Portus,
  DOI10.1017/9781108850216.006. Cambridge metadata/summary read;chapter body
  NOT read/access not assumed. Lead for commodity/turnover/institution distinctions.
- Rickman1971,Roman Granaries and Store Buildings. AGRIS/NationalAgricultural
  Library catalogue checked;monograph NOT read. Primary-source trail only.
output/*scope*/exposure.json records both searches and incidental quantitative
snippet visibility,including excluded unopened military-granary hit. No numeric
snippet was transcribed/used;do not call these leads an unseen evaluation pool.

NEXT FROZEN calibration/urban_diagnosis_20261117/storage_capacity_method_qualification.json:
obtain lawful full Salido2018 article from journal,verify bytes/DOI/page locators,
then read ONE source's capacity methods/limits. Distinguish observations,author
estimates,modern analogies,our bookkeeping and unknowns:usable floor area,
fill/stack geometry,grain form/packaging,bulk density,working space,function,
ownership/dating and losses ONLY where stated. No site-level dimension/capacity/
population/yield table or fit. Record incidental example exposure as development.
Do not treat unread VanOyen/Rickman bodies or cited papers as authenticated facts.
Any symbolic volume→energy relation is our unit contract,not an ancient law.
Days of modeled market flow need separately justified denominator and location.
Decide whether the physical-origin commercial-store interface itself requires
institution/location distinctions before calibrating its coefficient.

Broader queue: storage/dispatch source qualification → defensible interface →
explicitly declared physical food/work/finite-occupancy integration. Full diet,
resources/work,rights and independent transfer remain separate adoption gates.
No further numerical sweeps until justified by evidence. Climate remains later;
steppe archived,Buringh sizes/climate l unopened. Main atlas/population unchanged.

Quota result remains:four70array controls exact;two0loss/90d fixed-quota cases
40.258773%central/46.087820%low. Eighteen previous local losers improve and one
returns to equality vs5%control;no newlosers vs5%. Fixed quota still feeds
6474/3569fewer mealPY than0%OWNquota. Initial seal's overly strict improvement
assertion was preserved/corrected;scientific arrays unchanged,final seal passes.
Do not select a rule from totals or use logistics uncertainty for climate fitting.
All scoped source outputs frozen;scope/seal refuse overwrite,use isolated OUT
for fresh local replay. Previous entries below retain historical states.

# Previous completed fixed-quota control — 17 November 2026

Latest report reports/URBAN_FIXED_DISPATCH_20261117.md and qualification
output/urban_fixed_dispatch_20261117/qualification.json. FOUR existing own-quota
controls replay ALL70food arrays EXACT BEFORE exactly2new0loss/90day cases.
Originalbaseline annualmarket/12 now fixes the quota as well as commercial
capacityreference. Allwork/grain/firstbest dates/requests/ruralpeople/shares/
actual1981-2010routes remain fixed. No jobs running;no atlas/default adoption.

City meals central/low at90days:
5%ownquota40.006758/45.810563%;0%ownquota40.336113/46.175795%;
0%FIXEDquota40.258773/46.087820%. ALL11central/8low previous local losses
versus5%control disappear,with NO newlosers versus5%. This isolates quota
feedback in those declines,not general monotonicity or historical dispatch.
Versus0%OWNquota,fixed quota feeds6474.384/3569.347FEWERmealPY,
gains175/193cities but harms399/604. Do not confuse those comparisons or pick
the rule with a preferred aggregate/local outcome. Fullmeal cells217/131.
Paid departures fall39158.618/17624.162grainPY versus0%ownquota;commercial
spill rises bysameamount. Ruralinventories/marketedgrain EXACT to0%owncases.
Zero-reference origins keep0capacity AND0quota. All-rural/all-citymealsfalse.

10newadaptertestsPASS;qualified0lossendpointmethod/originaltolerances reused.
Separate stock-map/route/ledger review112756source-cases/8inventorygroups/
3683shipments;trace differences and compensatedgrainresidual0.1103protected
parent identities exact.6510cityrecords/2170completechannelrows/19previous
loserrows/72month/30region rows,3maps and compacttownpacket tracked.
Large cases/*/fields.npz local/ignored. Frozen producer/review/render/seal
refuseoverwrite;fresh replay needs consistent runtime OUT and pinnedinputs.

NEXT FROZEN calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json:
move from parameter variations to STORAGE/DISPATCH EVIDENCE. First read-only
inventory of exposed reports/citedreferences;separate reservealgebra/scenario
assumptions/modern context from ancient institutions. Manifest of exactquotes
and cannot-infer interfaces:ruralretention,commercial staging,townstorage,
seasonaldispatch. Footprint!=usablevolume!=ediblestock!=capacity!=throughput;
annualmarket itself is model-dependent. Sourceclasses/ownership/dating matter.
Public bibliographic discovery allowed only as LEADS ifneeded;no quantitative
observation extraction/crossing before a later source/measurement declaration
and exposure registration. No newfoodcases or capacity/dispatchfit. Existing
sources currently supply no qualified ancient365/90day or5%coefficient.

Broader priority:finish evidence qualification at this interface,then address
physical food/work and finite occupancy together. Complete diet/resources,
rights and independent transfer remain separate gates before adopting a new
atlas. Testedcapacity effect47.8–52.5pp dwarfs quotaaggregateeffect<.1pp;
don't compensate for logistics uncertainty using climate fitting. Climate/
steppe deferred;Buringh sizes/climate l unopened. Continue source scoping
after pushing this completed control. Old entries below are history.

# Previous completed storage-throughput audit — 17 November 2026

Latest report reports/URBAN_STORAGE_THROUGHPUT_20261117.md and qualification
output/urban_storage_throughput_20261117/qualification.json. Completed AFTER
pushing factoriale217f9709;zero newfood scenarios/kernel calls/observations.
451024saved source-case ledgers plus ALL19local-loss cities/228months reviewed.
No jobs running. Parent frozen outputs/code and1103protected identities exact.

Main result:98.5090%central/98.4578%low of0loss marketed grain comes from
ONE-positive-marketed-pulse origins withALL12routesopen. For these,annual
departures=min(ownannualmarket,ownannualmarket/12+FIXEDcommercialcapacity)
holds atoriginal tolerance;exact cohort counts44895central/44888low.
Identity covers99.2974/99.2770%of90d departures.
It explains why small commercial stores plus stipulated uniform dispatch
spill grain before later quotas;NOThistorical capacity calibration,optimal
dispatch or a food forecast under another policy. Do not apply identity to
multiple pulses,blocked routes or5%loss.

5%central market30.444MgrainPY fixed,departures29.447→9.901M at365→90days;
commercial overflow.294→20.477M. Low market13.203M,departures12.765→4.292M,
overflow.132→8.882M. Distinguish source grain from arrivals/meals/people.
ALL11central/8low losing cities at0loss/90d have more annualDIRECT arrivals;
8/6have less intertown receipts,remaining3/2have unchanged intertown receipts
but additional overflow and lower arrivals in some later bins. No local
protected-exporter flag flips. Combined city losses−276.520/−107.883mealPY;
all monthly/annual channels retained. Maxtrace ratio6.37e-6oforiginaltol,
bound ratio3.70e-6,citymealΔledgerres<=1.37e-12PY. No missing grain invented.

Tracked11.8MBsource_accounting.npz retains ALL451024source-case vectors;
redundant60MBsources.csv remains local/ignored. Small summary/city/month
tables tracked. Qualified audit/review/seal refuseoverwrite;redirect OUT
consistently in fresh process for read-only replay. Don't edit frozen code
and reuse outputs. All previous food cases remain baseline/sensitivity only.

NEXT FROZEN calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json:
exactly2new0loss/90day cases,central/low. Keep commercial capacity references
and ALLphysical inputs;hold monthly dispatch quota at ORIGINALbaseline
annualmarket/12 instead of each0loss scenario's ownannualmarket/12. Isolate
quota feedback,not choose bestfeedingpolicy. New isolated adapter must first
reproduce ALL70arrays for BOTH5%/90and0%/90own-quota controls at eachdensity
(4controls),then run2newcases. Reuse qualified0lossendpointmethod/tolerances.
Zero-reference origins retain0capacity AND0quota,even if newlyeligible.
Independent fullinventories/routes/grainledgers;compare allcity/month/region
and previous19losses plus newlosers,departures/spill/unused/transit separate.
No new365d case,parameter search/sharefit/data/phenology/demography/default
adoption. Original prototype remains reference;historical/rights/fullwork/
diet/independent-transfer gaps unresolved. Climate/steppe archived,Buringh
sizes/climate l unopened. Previous entries below retain historical states.

# Previous completed storage/loss factorial — 17 November 2026

Latest report reports/URBAN_STORAGE_LOSS_20261117.md and qualification
output/urban_storage_loss_20261117/qualification.json. Six declared new cases
reviewed; both original controls replay ALL70food arrays EXACT. No food jobs
running. Original B600h grain,first-best calendars,population/work/requests,
shares and actual1981-2010 routes unchanged. No atlas/default adoption.

City meal coverage central/low:
5%loss/365d baseline92.457845/93.575793%;5%/90d40.006758/45.810563%;
0%/365d93.892804/94.803867%;0%/90d40.336113/46.175795%.
Commercial capacities use ORIGINAL baseline marketed energy and stay absolute
across loss levels. Rural365d/town90d capacities fixed. All-rural/all-city
mealsfalse. These are fixed-request meal equivalents,NOT occupancy forecasts
or historical granary estimates. Shorter stores cost52.451/47.765pp at5%loss;
zero-loss gain1.435/1.228pp at365d but only.329/.365pp at90d. Interaction
−1.105605/−.862842pp. Zero loss at90d HARMS11central/8low city cells despite
improving aggregate meals. Do not assume local monotonicity.

Important preserved numerical control:generic zero-loss bisection selected
avoidable inherited reserves in495/1000synthetic noninteger balanced cases.
Frozen original kernel untouched. New isolated polity/earth_storage_loss.py
uses supported food_year at0loss and zero-loss map endpoints T(0)/T(cap),
preferring smallest lower endpoint if it repeats at ORIGINAL1e-10criterion.
Method declared/committed BEFORE Earth cases;19testsPASS. Five-percent branch
unchanged. Separate stock-map/ledger review:338268source-cases,24inventory
groups,23137intertown shipments;maxoriginal tolerance ratio.576484,fullgrain
residual<=1.72e-8PY.1103protected parent identities unchanged. Zero-reference
origins keep0commercialcap;15/17newly protected such sources cannot carry
stock but can immediately dispatch harvest-month quota.

Tracked maps(central/low,factors,monthly),8680city/96month/40region rows,
2170city/24month/10region factor rows and compact town_model.npz. Large
cases/*/fields.npz remain local/ignored. Scientific sources/output identities
frozen;qualified producers/review/render/seal refuseoverwrite,redirect OUT in
fresh process for replay. Do not modify them then reuse numerical caches.

NEXT FROZEN calibration/urban_diagnosis_20261117/storage_throughput_audit.json:
read-only saved original+sixcase commercial ledgers and ALL19local city-loss
channels. Independently verify marketed=departures+spoilage+overflow+stockΔ.
For zero-loss ONE-positive-marketed-pulse,ALL12route-open origins only,
test departure=min(annualmarket,annualmarket/12+fixedcapacity);report how much
of the mass/cohort this covers,do not apply to multiharvest/blocked routes.
Trace direct/intertown/overflow/spoilage/stocks and protection flips for all
11+8losing cities. Zero new food cases/data/parameter search;no policy change.
Proceed with this audit after committing/pushing factorial,do not stop there.

Climate/steppe sidequest archived. Buringh sizes/climate l unopened;no new
evidence/phenology rescoring,share fit,demographic iteration or main atlas
adoption. Old entries below retain historical state.

# Previous evidence/buffer audit — 16 November 2026

Latest report reports/URBAN_EVIDENCE_BUFFERS_20261116.md and
output/urban_evidence_buffers_20261116/qualification.json. Completed AFTER
pushing exact-energy timing stageeba2c96f3. READ-ONLY:6source/interface contracts,
6baseline peak vectors reconstructed EXACT,0food-kernel reruns,0raw Sacks
record reads,0new geographic intersections,0phenology re-scoring. No jobs running.

Evidence bridge:modern calendars constrain duration/context,not ancient dates.
Old cereal clock predicts physiological maturity GIVEN sowing;heat-only28.56d
conditional evaluation error vs51.99threshold,trainedchilling68.06d/2nonmaturity
failures. Its negative adoption and already-scored status remain;not a new
evaluation. FAO56 supplied-stage rows do not identify ancient Nile barley dates.
Reserve algebra gives no universal200ADcapacity/loss. No automatic calendar/
phenology substitution,share fit or atlas/default adoption from these facts.

Baseline store capacity / SAME-TIME peak / SUM of individual peaks (MgrainPY):
centralrural53.029/35.592/52.757,export30.444/18.484/27.944,town2.064/.800/.801;
lowrural57.343/38.462/57.022,export13.203/8.048/12.119,town1.000/.508/.509.
These are grain-energy scenario quantities,not people or observed granaries.
Never conflate/add class peak statistics as a system simultaneous peak.
Commercial median peak=11/12capacity. ALL45453central/45442low actually
exporting origins exceed hypothetical90/365annual-market capacity at their
RECORDED peaks,associated with100%of existing departures. This is potential
binding,NOT100%lost exports/meals;no changed-capacity path has been run.

NEXT FROZEN seasonal_transfer_storage_loss_factorial.json:
originalFIRST-BEST calendars and B600h fixed requests/work/grain/shares/routes.
2x2loss{.05,0} × commercialcapacity{365,90}days of ORIGINALBASELINE annual
marketed energy;existing.05/365is control,only3newcombos×2densities=6newcases.
Referencecapacity saved separately for central/low and fixed ACROSS loss levels;
do NOT resize stores to each new case's marketed energy. Baseline-zero-capacity
origins keep0even ifzero loss makes them newly export-eligible. Rural365d and
town90d capacities unchanged. Recompute overflow/eligibility undereachloss;
dispatch RULE remains own-case marketed annual/12 withsame routeavailability.

New isolated parameterized adapter MUST reproduce ALL70original monthly food
arrays EXACT before interpretation;don't edit frozen models/caches. Zero loss
makes old analytic1/(1-decay)invalid:require supported original-tolerance
periodic method and explicit smallest repeating-stock/zero-loss controls;
nofree inherited food/no tolerance relaxation. Independent stock/routes/grain
ledger for all6newcases. No assumed monotonic city gain or selecting best
default. No storage/loss counterfactual has been run yet.

Current timing result remains:67.581%potential has exact date ambiguity;
two recipes change global meals<=.018604pp but individual cities<=12.7824pp,
and do NOT bound outcomes. Original monthlycentral92.4578%/low93.5758%still
reference;actual occupancy/demography unchanged,all-rural/all-city mealsfalse.
All old sources/numeric/atlas identities protected;no new evidence/validation,
climate run or reserved pools. Buringh sizes/climate l unopened,sidequest archived.

Audit scripts audit_urban_evidence_buffers.py then seal_urban_evidence_buffers.py;
completed audit refuses overwrite,use isolated OUT for fresh read-only replay.
Science code/results from earlier stages remain frozen. Prior entries below
are history.

# Previous completed exact-energy calendar sensitivity — 16 November 2026

Latest report reports/URBAN_CALENDAR_SENSITIVITY_20261116.md and output
output/urban_calendar_sensitivity_20261116/qualification.json. Catalogue,
2original monthly controls and4timing cases independently reviewed. Original
full-precision maxima/first masks and saved energies exact;both original
monthly cases replay ALL70food arrays exactly. No jobs running.

Exact ties on35156/53550positive source components;67.5810%of annual grain
potential affected. All455positive basin components have multiple equal-energy
boundaries avoiding saved high-flow growing bins. No isclose/yield tolerance,
changed grain/crops or invented observed dates. Earliest/latest use original
length/start order within the selected boundary. One shared B600h workforce;
grain,annual work,requests,rural people,shares,stores/routes all unchanged.

City MEAL coverage first→earliest/latest:
central92.457845→92.471846/92.460095%;
low93.575793→93.572850/93.557190%.
Largest aggregate change0.018604percentage points;individual city shifts up
to12.7824points. Changes in meal-equivalent person-years:
central+1172earliest/+188latest;low−119/−755. Full-meal city counts:
central1046→1044/1048,low967→956/967. Actual city requests/occupancy NOT changed.
Original central is BELOW both alternatives;original low ABOVE both:
earliest/latest are NOT network outcome bounds or confidence intervals.
No variant adopted. Local gains/losses can cancel in the aggregate.

Six new exact-window testsPASS(parent7food/12work test identities unchanged).
Independent catalogue/tie-eligibility/work grouping and225512source-cases,
16inventory groups/31728shipments PASS original1e-10stock tolerance(maxratio
0.57741);grain residual<=1.72e-8person-years.4340city difference rows,72monthly/
30regional rows,3figures,compactcatalogue/windows.npz andtownpacket tracked.
Large cases/*/fields.npz ignored. All original controls/1103protected identities
unchanged,adoptFalse;no demography/new validation/mainatlas/default change.

NEXT FROZEN seasonal_transfer_evidence_buffer_audit.json: read-only bridge audit
of ALREADY EXPOSED reports/plans/implementation contracts plus ORIGINAL monthly
stock paths. No raw Sacks records,new source queries,country intersections,
phenology re-scoring,new food scenarios or parameter fitting. Existing docs:
modern calendars are duration/context constraints,not ancient dates;the isolated
clock is conditional on supplied sowing and its trained chilling candidate
FAILED adoption;FAO56 examples do not supply an ancient Nile calendar;reserve
algebra gives no universal historical capacity/loss. Keep negative results.

Also reconstruct baseline individual stock peaks exactly;report class capacity,
SIMULTANEOUS peak and SUM OF INDIVIDUAL peaks separately. For export stocks,
count potential binding at hypothetical90/365annual-market threshold,including
actually exporting origins/departure weight. This is only a saved-path diagnostic,
not a forecast under changed capacity. Then declare a bounded next experiment
or evidence strategy. Calendar stability across TWOrecipes does not qualify
all timing assignments or isolate buffer causality. No buffer query made yet.

Science producers frozen;no source edits and cache reuse. Report has replay
commands;completed outputs refuse overwrite,use isolated OUT. Buringh sizes/
climate l unopened,climate sidequest archived. Prior entries below are history.

# Previous completed fixed-request monthly pilot — 16 November 2026

Latest report reports/URBAN_EARTH_MONTHLY_20261116.md;output
output/urban_earth_monthly_20261116/qualification.json,meal_maps.png,
monthly_accounting.png,town_model.npz,towns.csv/months.csv/regions.csv.
Continued AFTER pushing the paired-work stage449824936. Original6annual
controls and recomputed B600h source work/annual city allocations stay EXACT.
New fixed-request monthly pilot complete for central/low;independent reviewPASS.
No research jobs running.

600h physical-work B annual support→MONTHLY MEAL coverage:
central95.0773→92.4578%,low95.6076→93.5758%.
Egyptcentral81.6122→76.6582%,low85.2320→80.9950%.
Urban unmet631378central/260644lowperson-years;monthly rural unmet218953/
259521person-years(vs annual209624/249148). Both all-rural/all-city mealsFALSE.
Full-meal city cells1071→1046central,1018→967low. Local redistribution:
6central city cells gain meal-equivalent supply/32lose;40lowgain/77lose.
Fixed requests,locations,production and population unchanged. This is NOT
revised occupancy,actual supported residents,staff or a demographic fixedpoint.

One fixed physical rural population/workforce;factorized uniform global urban
withdrawal(no people matrix),rural reconstruction error<=3.64e-12people.
Original two component pulses preserved,including41different base/basin dates.
365d rural/export stores,90d town stores,5%stockloss,protected overflow-only
source/town exports,unchanged4actual1981–2010snapshots held3bins,1bin leg delay.
Unused/unmarketed grain,all stock/freight losses and cyclic transit explicit.
No demographic allocator/CoupledNetwork invoked. Protected fantasy helper
functions reused unchanged;new isolated polity/earth_fixed_food.py adapter.

Independent canonical-bisection check on ALL8inventory groups PASS original
1e-10relative inventory tolerance(maxfraction0.57649);source/town eligibility
flags match. Independent15896monthlyshipment rows and all source arrivals
(EXACT),grainledger residual<=1.72e-8person-years.112756physical source-cases,
2170city rows/26040city-months;7new adapter testsPASS(parent12work testsPASS).
All prior1103protected sources/assets unchanged;shares not fitted,adoptFalse.
Food repeatability is not population feasibility or observed seasonal validation.

NEXT FROZEN seasonal_transfer_calendar_sensitivity.json: original crop engine
may have equally productive windows with different maturity dates. Reproduce
original full-precision max/first-best masks exactly,then enumerate EXACT-energy
ties using original inputs/dtypes/parameters. Basin ties must avoid saved
flow>1growing bins. No energy-tolerance broadening or invented observed dates.
Two declared timing alternatives:earliest/latest eligible calendar-year boundary
per component;not network-optimal recipes/probabilities/global outcome bounds.
Check B600h grain/work unchanged at each timing choice,then four fixed-request
food cases(2densities×2timings)with SAME frozen food adapter,stores/routes/shares.
Canonical inventory/physical ledger independent review before interpretation.
No new calendar catalogue or alternative food run has been made yet.

Completed new science producers frozen;don't edit them and reuse outputs.
Large cases/*/fields.npz ignored,compacttown packet tracked. Producer refuses
completed-case overwrite;use isolated OUT for fresh runs;see report commands.
No main atlas/default adoption,new evidence pool or climate fitting. Buringh
sizes/climate l unopened;sidequest archived. Previous entries below are history.

# Previous completed annual component-work comparison — 16 November 2026

Latest completed stage: reports/URBAN_COMPONENT_WORK_20261116.md and
output/urban_component_work_20261116/qualification.json. All6original annual
result cases replay BYTE EXACT via unchanged Greek/low runners and verified
cached1981–2010 routes. Original population/city/crop/work arrays recomputed
bit-exact before B. No new Dijkstra run or transport physics validation.

Physical component work B uses original positive base/basin crop activities,
areas0.36nonbasin/0.95basin,ONE0.4rural workforce per physical source and shared
annual/per-harvest reaping budgets. One common retention scales all components.
Same potential,crop calendars,city requests,global recruitment/population,actual
routes,270haul limit and existing central/low marketed shares. No share fit.
Both600h primary and300h stress PASS independent scalar-work/sorted-flow review.

Annual city request supported,A→B:
600hcentral95.1267→95.0773%,low95.6390→95.6076%;
300hcentral64.2613→63.3162%,low68.3038→67.7091%.
Central600hgrain−18914person-years,citysupport−4140people across4city cells;
300hgrain−353122person-years,citysupport−79112people across10cells.
Egyptcentral600h81.7406→81.6122%,300h47.6285→42.9360%;
low300h55.6504→50.4651%. Actual occupancy/requested populations NOT changed.
Central600hruralshortfall207112→209624person-years;300h590957→617382.
All material grain changes on basin sources;nonbasinmax3.14e-12person-years.
No material city support gains. All reaping peaks slack:annual work binds;
maxreapingbudget38.46%at600h/19.23%at300h under partial listed task counts.

12 meaningful tests PASS. Independent225512source-cases,8town allocations,
5963shipment rows,1820basin CSV rows;maxsource residual2.10e-12person-years,
maxtown residual2.92e-10people.4340city comparison rows/40regional rows,
3figures,compacttown packets tracked. Larger source case NPZ ignored.
All protected prior identities/mainatlas/defaults unchanged,adoptFalse.
This is ANNUAL fixed-request grain support,NOT seasonal meals/new settlement
occupancy,complete work/diet or new empirical validation. No jobs running.

NEXT FROZEN seasonal_transfer_fixed_request_pilot.json: B600h as work scenario,
its reviewed exact ANNUAL control,central/low fixed original requests and shares.
Uniform global withdrawal stays factorized (no huge people matrix); preserve
exact rural arrays. Two component harvest pulses/one physical worker/grain
ledger;365d rural/export and90d town stores,5%loss,original4snapshot routes
held3bins,onebin perleg delay,protected overflow-only exports. Explicit stock/
freight loss/unused grain. Independent repeating inventory/meal/route audit.
Report fixed-request monthly shortfalls,NOT demographic feedback/actual city
caps/coupled fixedpoints/maximum populations or staff. No share fitting.

All new science producers are frozen after these outputs;no editing and cache
reuse. Scripts urban_component_work.py --control greek/low (separate processes),
--hours600,review600,then --hours300,review300,render/seal;see report. Completed
outputs refuse overwrite;use isolated OUT for fresh replay. Prior entries below
are history. Buringh sizes/climate l unopened;climate sidequest archived.

# Previous completed calendar recovery — 16 November 2026

Latest report: reports/URBAN_EARTH_CALENDARS_20261116.md. Output
output/urban_earth_calendars_20261116/{qualification,results,review,presentation}.json,
calendars.npz,monthly_energy.csv,timing.png. Continued AFTER pushing the annual
audit. Original crop engine timing recovered on56378active sources/54324unique
5' pixels;53265positive and3113zero production sources retained. All108648
wheat/barley energies reproduce the original float32 saves BITEXACT; basin
float64 capacity BITEXACT. Independent reviewer re-read36derived monthly fields,
re-enumerated windows WITHOUT crop_yield,and reproduced all energies/masks.
Original calendar source and annual/fantasy controls unchanged. No jobs running.

All455basin sources use barley (no ties/crop mismatch),harvest boundaryApril;
no selected basin growing window intersects saved catchment high-flow bins.
This is model consistency,NOT observed flood/harvest validation.285cells have
both positive base/basin components;41have DIFFERENT harvest boundaries.
Those41contain7.2748%of basin energy/0.2291%of world potential. Keep both
harvest pulses with ONE physical population/workforce/land/grain ledger.

NEW FOUND DEPENDENCY: annual blended-yield work charges0.36of arable area,
while basin energy represents0.95cropping on its fraction. Separate physical
task areas imply1.066–2.573times the old task area on285both-positive cells,
median1.721;at full potential the extra listed barley tasks are126Mhours.
READ-ONLY diagnostic: no work/grain/food totals or shares changed. Current
timing figure assigns EXISTING annual-work-limited grain to recovered dates;
it is NOT a seasonal food/dispatch/store calculation. All gates/adoptFalse.

NEXT FROZEN seasonal_transfer_component_work.json: paired annual diagnostic
A=exact original mixed-work control,B=explicit physical component areas/tasks,
ONE shared0.4rural workforce,600h annual and30days×8h per harvest bin;sum
reaping requests on shared boundaries and limit all component activities with
one common retention. Positive components only;zero-energy sources explicit.
Keep actual population/city requests/grain potential/routes unchanged. Compare
at EXISTING central/low shares and270haul limit;no share refit/optimization.
Only after independent review declare a seasonal food pilot/factorized global
recruitment adapter. Don't edit the protected fantasy module or hide distinct
dates/copied workers to fit its one-boundary/sparse-recruitment interface.
Climate sidequest archived;reserved pools/Buringh sizes/climate l unopened.

All calendar science/producer files frozen now;do not change a producer and
reuse its output.9.5MBprepared weather ignored;1.6MBcalendar packet tracked.
Producer refuses to overwrite completed results;use isolated OUT for a fresh
replay and redirect review/render to it. See report. Prior entries are history.

# Previous completed annual input/control audit — 16 November 2026

Latest completed stage: reports/URBAN_SEASONAL_TRANSFER_20261116.md and
output/urban_seasonal_transfer_20261116/results.json. Six annual Earth cases
reproduce their COMPLETE archived result JSON BYTE FOR BYTE: four Greek-wall
variants plus central/low density readings. Qualified artifacts live under
output/urban_seasonal_transfer_20261116/wind_1981/. Independent review passes
all source population/crop/work/demand checks and all100 primary flow settings
(300 aggregate checks,max difference2.22e-16). No seasonal Earth simulation,
share refit,new validation claim or atlas/default change. No jobs running.

Found and resolved a transport INPUT identity problem: original ignored wind
cache absent; existing fallback URLs serve1991–2020,while annual protocol
specifies1981–2010. Wrong-period Greek primary e95=.3455135751 vs archived
.3371937035. Preserve first full failed4case run and independent200setting
review in TOP-LEVEL output/urban_seasonal_transfer_20261116/{greek,readiness}.
The old1981-labelled sea calibration is an inadequate identity check:
fallback actually matches all108 old sea diagnostic scalars; that alone did
NOT qualify the annual supply inputs. Native1991 arrays equal fallback exactly;
native1981 named by annual protocol restores every annual result byte. All92
nonroute arrays across the four period comparisons are EXACT; actual routes
change. Original ignored wind-file bytes/full route arrays were not retained;
only full annual output identity is claimed. Canonical reader is protected and
unchanged; use scripts/replay_urban_transfer_1981.py (asserts actual metadata),
NOT the unversioned fallback for qualified supply replay.

NEXT FROZEN calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_recovery.json.
Recover original model crop windows on56378 active sources/their5' source pixels,
including53265with positive production and3113with zero production.
No calendars are saved for ANY positive production.455source cells have basin
share (2.67697%of annual potential). Recover base and fully irrigated winter
maximum separately,validate exact stored energies/dtypes,and compare sowing
with saved last-flood month/flow. Do NOT invent dates,use fantasy calendar
engine,duplicate physical grain/workforce,or alter annual energies to fit flood
timing. Original crop_yield first-strict-best season is the intended recovery,
not observed calendar validation. Basin maximum crop identity remains explicit.

Future seasonal port ALSO needs a separate declaration: global rank-one
recruitment W_ij=people_i*city_request_j/61.4M (factorized,not huge dense/CSR),
multiple component harvest timing with ONE physical workforce,monthly routes/
storage/leg delay and annual control. Existing protected fantasy module takes
one boundary per source and sparse recruitment; don't force Earth into it.
Primary central annual rural deficit207112person-years already exists.
403/1115 eligible city areas are q25-filled at15ha; city residents are assumed
density×area,not observed census. Existing independent-transfer/resource/role
adoption gates remain. No new evidence pools;Buringh sizes/climate l unopened.
Climate sidequest archived. Reproduction commands and exact boundaries in report.

# Previous completed fantasy seasonal stage — 16 November 2026

USERarchivedclimatesidequest;latestacceptedsettlementseasonalplan executed.
Deliverable output/urban_candidate_seasonal_20261116/presentation/index.html;
8pairedmaps(raw/corrected×central/lowrequested density×600/300h),CSValltowns,
actualcivilian/staffbudgets. Report reports/URBAN_SEASONAL_20261116.md. Mainatlas,
coefficients,seed1locations/climate/totalpeople unchanged;adoptFalse/gateFalse.

ALL16 CONDITIONAL PHYSICALCERTIFICATES PASS. NOT numericalfixedpoints(all0);
preserved64/512unqualifiedsolverhistories +A1/A2/A3 declarations below/report.
Existingfiniteallocator returns actualdemographicproposal;A3 freezesit and
rebuildsALLsource rural/work/food/stocks/routes atthat exactpopulation. Parent
trial/arrivals saved. No looseningoforiginalphysicaltolerances orfakeconvergence.
Finitepeople-shards NEVERduplicatecroparea/grain/work. Hungryoriginscannotexport.
Fixedmix/downwardselectedstates aren'tmaximumsustainablepopulation forecasts.

600h actualtownresidents control→candidate:
rawcentral9,405,630→9,337,899(−.720%),corrected10,056,808→10,065,607(+.087%).
rawlow4,877,264→4,879,556,correctedlow5,072,973→5,095,909. 300hcentral candidate
4,236,505raw/4,433,264corrected;300hlow2,387,228/2,447,631. ExacttablesinCSV.
Density defines REQUESTS,notfinaloccupancy;thisdoesnotrefit/certifybuiltfootprints.
Candidate600hcentral localruralshortfall49,344raw/34,263corrected personyears;
300h382,579/311,716. AllworldruralfoodsupportFALSE. Missingruralimports/otherdiet,
fullhousehold/draft/transport labour,roles/recruitment rights remainexplicit.

IndependentreviewPASS:8provenance matrices/3,842,205links(maxdiff1.14e-13people),
16cases/16,696town-case rows/3,870,224physical sourcecases/90,255shipmentrows.
Canonicalbisectionstockreplay vsisolatedclosedroot;separatefield/trade/budget
equations;maxgrainresidual1.72e-8personyears. Kernel64initialinventories/5patterns
PASSoriginaltol(max.582).10meaningfultestsPASS. Fresh48initial/parent/finaltrials
reproduceallfinalpeople/production/routesandtown_model.npz/towns.csv BYTEEXACT;
FULL solver histories weren'trerun. See review.json/replay.json/tests.json.

Fundedheadlinecohorts1023raw/1042corrected,EXACT SAME locations/affiliations
bothmodels aspublishedannualheadline. downstream/reach_identity.json PROVES
P2/v2.1mapidentity underprotectedfixedtravelinputs;canonicalbuilderfilesexact
release-reference source. No newmaprenderorindependentreachphysicsclaim. Some
300hsourcevectorschange;theirpoliticalmaps requireseparaterebuildbeforepublishing
thoseoptions.16thinactualstaffingpacketsunderdownstream/,allgatesFalse. Monthly
grain trade itself rebuiltandreviewed. Presentation8348town/scenariopairs,
33392plottedvalues/8PNGs/16staffpackets checked;desktop/mobileviewerpassed.

Allnewsciencecode/recipesfrozen;largeprepared/caseNPZ/freshignored,compact
town_modeltracked. Don'talterproducersorcaches/reusecomputedcasesafterchanging
scientificcode. Reproduction10commandsinreport. EarlierCURRENT/NEXTentriesbelow
arehistorical;NO jobsneedrestarting. Physicalclosureisconditionalcerealonly,
notnewEarthvalidation. Adoption_gate.json remainsFALSEwithconcretereasons.

NEXT FROZEN seasonal_transfer_readiness.json: read-only same-recipe portability
audit/exactALREADYEXPOSED qualified EarthANNUALsupplycontrols andinputcalendar/
work/population/transport availability,BEFOREdeclaringanynewseasonalEarthpilot.
Don'trefitshareorchangefantasymap/physics fromthisaudit. No newsourcepool/heldout
claim. Appropriate independenttransfer andcomplete resource/work/rolegatesstill
precedeadoption. Buringhsizes/climate l stayunopened. Climate sidequestarchived.

# Seasonal qualification implementation history — 16 November 2026

USERARCHIVEDclimatesidequest;accepted settlement seasonal food/labour plan and
saidgoahead. Currentwork output/urban_candidate_seasonal_20261116/. Mainatlas
unchanged;no newclimate work. Frozen seasonal_coupling.json83442f94b:16cases,
raw/corrected×control/candidate×central/low×600/300h,actualseed1samefixedtowns,
originalcalibratedshares. Fixedsparse physicalpeople->town recruitmentmix;shards
partitionPEOPLEONLY,neverduplicategrain/cellworkers. Actualnewruralpeople drive
work/food. Firsteligibleharvest,365d rural/exportstores,90dtownstores,5%loss,
quarterlyfreightmatrixheld3monthbins,1bin perleg delay. Conservativeoverflow-only
source/town exports,not unrestrictedannualpooling. Staff100withinactualtowncap.

Preparation PASS:8people matrices reproducecanonicalown/wider sourcewithdrawals
and remainingruralgrids;4seasonfreightmatrices independentlyreconstructed permap
whosemean +fullprecisionowners/shares are EXACTannualsupplycache. Hugeprepared
caches ignored. Independentfull-distance/compensatedpeoplelink reviewer alsoPASS.
Codeprepare_urban_seasonal.py,polity/seasonal_settlement_network.py andbuild scripts.
10meaningful budget/restriction/legacy-audit/freshcertificate/roundofftests PASS.

Numericalhistory retained explicitly: original64step correctedcandidatepilot
UNQUALIFIED (reference_pilot/model_snapshot.txt,unqualified_result.json,log).
A1a41d792ee derives equivalent clipped-affine inventoryroot for speed;canonical
monthlyfood replay reused. Kernelreview16initialcases/64inventories/5patterns
PASS originaltolerance(max.582ofallowedtol),sourceflagsunchanged. A2 7bb595bac
extendscommonbudget512,no tolerancechange. Rawcontrol512stillfailedfixedpoint
despite actualtownmeals passing because existing foodceiling has1e-8downward
safety;originalUNQUALIFIEDfullhistory/snapshot retainedreference_pilot/extended512.

A3 36c8579ab declares actualfinite-allocationcertificate,not pretend convergence:
after>=64steps freeze returned ResidentAllocation,then rebuildALLphysicalrural
workers/production/food/routes at THATactualpopulation;retainparenttrial/arrivals
forindependentallocatorreplay. Certifyonlyoriginalfood/work/pop/grainchecks pass.
Numericalconverged andphysicalcertificate areSEPARATE. Existingruraldeficits
elsewhereremainvisible; hungryoriginscan'texport;noallworldfoodfeasibleclaim.
Roundingbugfixed: sparsecolumnsum mayputfinitebudgetsulpaboveoriginalrequest;
clipallowancefractionto[0,1]withinalreadydeclared1e-7requesttolerance. Regression
testpass. No physicaltolerance wasrelaxed. Canonicalmodules remainuntouched.

CURRENT:two-worker batch build_urban_seasonal_batch.py computes16cases;log
/tmp/build_urban_seasonal_batch.log,execsession94973 (also ran tests/kernelchecks).
Childrenwriteindependentcasefolders;unmodifiedrun_case science shared. Earlier
serial/batch prototypeprocesses stopped; source snapshots preserved. Don'tstart
duplicatejobs. OnerrorProcessPoolmaywaitqueuedjobs;job nowprints tracebackearly.

NEXTfinish16cases;review_urban_seasonal.py independently checksallactualphysical
sourcework,canonicalbisectionstockpaths,sortedlinkroutes,finiteparentallocator
decision andwholegrainledger. Parent/finalresident distinction isessential.
Then fresh final/parent/initial pointreplay andexactcompactexports (notclaimall
512iterations rerun),actual supportmaps,CSV/report anddurablehandoff. Only then
affectedstaff/reach/trade onqualifiedstates;transfer/diet/work/evidencegatesstill
blockadoption. Casesmustnotclaimnumericfixedpointwhenonlyphysicalcertificate.
Mainmodel/sourcedefaultsunchanged. Climateexperimentbelowisarchivedhistory.

# Northern-steppe-only world/planet experiment complete — 16 November 2026

User explicitly requested IN PARALLEL with settlement:sole northernsteppe target,
noothers,actual maps andplanet parameters. This authorizes isolatedclimatefit
despite olderclimateparked instructions;NO productionchange. Plan9abf33e5c before
search;exact19gene protocol/source frozen beforefit,preserved dae38cbf1.
Report reports/NORTHERN_STEPPE_ONLY_20261116.md;localviewer
output/northern_steppe_only_20261116/presentation/index.html,climate_comparison.png,
target_seasonal_cycle.png,parameters.csv. Allartifactsisolated,adoptFalse.

EXACTtargetexisting paintedclass2 cold_dry (north-centre),onecomponent498cells
ds16. ONLYmean fuzzy cold_dry membership loss;allotherclasses/spill/realismZERO.
Globalphysicsstillcoupled. Existingr44/v22 sharedrecipe,19world/planet genes incl
latitude/northbearing,tilt,retrograde,offmapland,orbit,flux,radius,greenhouse,
cross-equatorialtransport,EBMlandscale. Terrain,day/year/gravityfixed.97evals
(baseline+8×12CMA),ds64/layout1;allnumericsPASS;best96 score.992132vs.002501base.
Budget exhausted,notconvergence/globaloptimum. NoEarthpoolopened.

FINALds16 layouts1/2/3 BOTHmodels,6numericsPASS,no reselection. Meanfield target
score.01779→.96221;medianrain878.5→88.5mm,MAT14.53→10.18C,coldest+1.29→−14.52,
hottest33.01→34.50. BSk16.87%,BWk80.92% vsbothzero baseline. IMPORTANTexisting
cold_dry ruleacceptsDESERT;do notcall97.79%BSk+BWksharepuresteppe/grassland.
Allotherpaintedzone memberships collapse becauseunconstrained,reportexplicit.

Planettilt33.5047→44.9411(close45bound),radius.843026Earth(~5371km),flux.965126,
ecc.007933,perihelion27.935days,greenhouse−.11345W/m²,retrogradestillTRUE.
Northbearing−8.8137→167.9663(~176.8degflip);latcentre39.8340,drawnnortherntarget
moves40.34–46.46N→30.16–37.75N. ThisisfreeWORLDconfiguration,notfixedorientation.
NEoffmapland.0089→.4616,otherlandfractionschange;exact19rowsandboundstable.
One boundedsearchdoesNOTuniquelyidentifyplanetparameters;radiusfirstorderscaling.

Independent review PASSall97vectors/selection/bounds/lockedparams;separatemonthly
overlap/aridity/membership/BSk/BWkfrom6savedmembers+2fieldmeans;freshcoarsebase/
winnerreplayexactscore;adversarialotherzonefieldchanges leaveobjectiveEXACT.
Protectedmainassets/sourcesmatch;presentation19rows/image/linkschecked;desktop/
mobile viewer checked. Scriptsnorthern_steppe_only.py,review_northern_steppe_only.py,
render_northern_steppe_only.py,review_northern_steppe_presentation.py.
Rawdaily members/checkpointignored,preview.npz tracked. Reproductioninreport.

Nextclimateproposal(notyetnewfit):sameonlyregionwithBSk/grasslandrequirementand
pairedfree/fixednorthorientation,declarebeforefitting. Don'tretunepriorobjective
orchooseposthocwinner. SettlementannualsupplyalsoCOMPLETEandpushed94b89a559;
nextsettlementseasonal same-origin coupling describedbelow/report. Preserveboth
directions;climateexperimentdoesn't silentlyadoptorreplace settlementprogramme.

# Annual candidate wider supply complete — 16 November 2026

Continued frozen candidate_supply_robustness.json after68a590d0f. Report
reports/URBAN_CANDIDATE_SUPPLY_20261116.md; output/urban_candidate_supply_20261116/.
Four static comparison PNGs show raw/corrected central_x34 and low_x14 support.
32 scenarios (2maps×2models×2readings×4existing supply/work alternatives),seed1,
no refit/placement/climate/population/default/adoption change. EXACT all4 released
supply CSV/fullNPZ hashes AND whole unrounded results.json control beforecandidate.
Restored float64 network cache ignored; canonical storedfloat32 insufficientexact.

600h central supply raw81.144→80.994%(47→52short towns);corrected84.245→86.614%
(43→42). Flat reading at14.049% extraction raw96.705→96.790%(21short both),
corrected98.197→98.995%(12→9). Shares remain EXACT .3371937035110408 and
.14049021985082757;10% and300h sensitivities retained. Candidate300h central
support35.623%raw/36.375%corrected. Annualsupport ≠ allocatedpopulation orseasonal.

OwnNEWrural grids feed production/food/work. Rural600h central deficits40,064raw/
28,182corrected personyears,4983/4041cells;300h242,239/218,871. All stayvisible,
no graininvented. Sourcework/hours,ruralneed,graintransport/shipments fullyrecorded.
Historical supply minor-road recomputation from node-sorted sites differs from
size-builder's original track order (xor1011raw/932corrected);preserve exact
released SUPPLY network for bothmodels,not silently replace withsize fields.
This olddistinction recorded innetwork receipt/report; controls STILLexact.

Independent review PASS32scenarios/33392town-scenario rows;separate field-work,
compensatedsourcegroups,sortedlinkallocator,fullgrain/source/work ledgers. Max
deliverydifference1.51e-10personyears,received6.69e-11,grainresidual2.15e-9.
Fresh compactexports exact,protected assetsmatch. Presentation4174town/scenario
pairs/4PNGidentities reviewed. Fullsource arrays ignored,compacttown_model tracked.
Five reproductioncommands inreport. Candidatepacket adoptFalse/gateFalse.

NEXT settlement: seasonal coupling,not another annualfit. Finite movement's
multi-origin own/wider draws,changing seasonal freight owners,and existing
one-owner-per-origin settlement_residents interface need explicit nonduplicating
representation on actual harvest calendars beforeclaiming allocation/audit
equivalence. Preserve rural deficits. Coupledfood/work,civilian/staff,thenaffected
reach/trade +appropriatetransfer stillrequired beforeadoption. No newsourcepool.

USER additionally authorized isolated northern-steppe-only climate experiment
IN PARALLEL. Plan calibration/northern_steppe_only_20261116/plan.json committed
9abf33e5c before search; current experiment inprogress. This explicitnewrequest
permits isolated world/planet fitting despite earlier climateparked preference;
no mainclimate adoption/publication. EarlierNEXTentriesbelowhistorical.

# Five-seed candidate sensitivity complete — 16 November 2026

Continued AFTER map push9f7a65633 into declared paired fixed-site seed component.
Report reports/URBAN_CANDIDATE_SEEDS_20261116.md; outputs
output/urban_candidate_seeds_20261116/. Seeds1/7/19/43/97,20area draws/40annual
population cases,20870site-seed rows. No refit/placement/climate change. Canonical
hierarchy builder, same base draws each old/new pair; unchanged2026memberorder.
Seed1 ALL8 old/new CSV/fullfields identities reproduce the map-stage outputs.

Key finding: NO town stays>2x or<half in ALL5seeds. Raw majority-seed doubling7,
halving2;corrected11/1 (counts across ALL sites,not just seed1 outliers).
Median paired site ratio1.0163raw/1.0154corrected. Central resident change ranges
raw−.770%to+2.908%,corrected−2.612%to+2.397%;seed1decrease isn'tstable.
Town p10/p50/p90 and paired ratios/frequencies in town_intervals.csv;these are
5scenario samplequantiles,NOT calibrated uncertainty intervals or validation.
Allrequested residents mettofloatingprecision,populationconserved,annual local
food recomputed. StillNO wider supply orseasonalqualification/adoption.

Independent reviewer PASS:20870rows/40ledgers,full-distanceH/scalarapplication,
annualrural/food,concentration and explicit quantile interpolation;fresh compact
artifacts byteexact. Maxdiffarea1.14e-13ha/rural6.83e-13people. Reuses preceding
independent reviewer with ONLY fixedseed exposed;exactadapter snapshot retained.
Compactmodel.npz tracked,largecasefields/freshignored. Three reproductioncommands
inreport. Mapviewer/PNGs below stillcurrent;no mainatlas publication.

NEXT: remaining annual wider-supply component of SAME COMMITTED
candidate_supply_robustness.json. Exact release4 controls FIRST;missing large
supplyNPZ caches reconstruct on fixed release4nodes/tracks,not old release3.
Then seed1 candidate bothmodes/readings at existing exact34%/14% shares and
declared10%/300h sensitivities;use eachcase's ACTUAL remainingrural people for
production/work/ruralneed,record allgrain/transport deficits/massbalances.
No newfit/seedchoice. Later seasonal finite settlement_residents/audit_origin_food,
civilian/staff demands,reach/trade/transfer still required beforeadoption.
Earlier NEXT entries below nowhistorical for seedwork;climate staysparked.

# Fixed-site candidate map ready — 16 November 2026 (climate parked)

Current deliverable: output/urban_hierarchy_candidate_20261116/index.html,
standalone interactive published/candidate comparison. Raw/corrected, both
density readings, search, synchronized pan/zoom/town details, area/change colours
and CSVs. Static comparison_corrected.png / comparison_raw.png beside it.
Report reports/URBAN_HIERARCHY_CANDIDATE_20261116.md. Main atlas unchanged.

Candidate build declared dc57b1c5c BEFORE fit. Exact SIX published townCSV,
siteJSON/fullfieldsNPZ hashes and unrounded numeric control summaries pass.
Initial control failed ONLY atlas.json receipt: later forest display descriptor.
Failure/log/producer/old metadata archived failed_metadata_control/. A1 committed
9e0c7859d BEFORE retry/fit; removes ONLY land_forest descriptors to compare
metadata, records old/current hashes, every other field/input still exact.
Do not claim the complete historical input receipt is byte-identical.

Full exposed-source fit:664rows/28caps/95pairs,4foldOOF RMS sigma,70phi/c losses.
beta=(1.554938767713789,.1826427224092563),sigma=1.0364605311460373,
phi=.25,c=1.0. This is final TRAINING fit,not another validation result.
Raw1034/corrected1053 SAME sites/population/roads/marks/lore/climate. Runtime-only
guard adapter recorded; candidate metadata adopt=False AND gate.passed=False;
canonical builder untouched. Compact town_model.npz tracked, full fields/prepared
caches ignored. Reproduction commands and scopes in candidate report.

Corrected area55165.90→55197.28ha, central town people13.4650→13.3146M(-1.117%);
raw54415.65→54582.29ha,13.2727→13.1705M(-.770%). Low-reading people+.057%/+.306%.
All requests allocated to floating precision; population residual<7.46e-9people.
Annual LOCAL cereal support corrected264→262/raw245→242 central; imports still
needed, no wider supply rerun yet. Source cells below rural annual need6/68.
Annual population conservation does NOT qualify seasonal source food/work.

Independent review PASS:6 exact controls,70losses,4174site-case rows,8annual
ledgers; max area diff1.14e-13ha/rural2.28e-13people; fresh numeric/array outputs
byteexact. Presentation review2087towns/37566values exact. Chromium desktop/mobile
passes controls,all2087coords,downloads,no exceptions/overflow. Shared painted
roads only in terrain. Review receipts and screenshots alongside map.

NEXT FROZEN candidate_supply_robustness.json: paired fixed-site seeds1/7/19/43/97,
20area draws/40annual population cases, seed1 reproduce current. No refit or
placement. Extreme corrected seed1 changes(.059–50.47×) can arise from residual
reassignment/lore,NOT specific-town predictions. Quantify persistence/intervals.
Also reconstruct exact release4 annual wide-supply controls, then candidate
seed1 on bothmaps/readings,unchanged34%/14% exact calibrated shares and existing
10%/300h sensitivities,using NEWrural source/work budgets. Supply largeNPZ caches
currently absent; restore/rebuild exact fixed-node controls first. Existing
40seed placement ensemble is inappropriate unchanged. Declare adapters,retain
false gate. Full seasonal settlement_residents allocator/audit,sourcefood/work,
staff/reach/trade and appropriate transfer STILL required before adoption.
No climate rerun, Buringh sizes or climate l. Don't redo completed source audits.
Earlier NEXT entries below are history; the new candidate report/plan control.

# Joint hierarchy refresh trial complete — 16 November 2026 (climate parked)

Continued through integration audit AND joint hierarchy trial after8ede6df38.
Readiness declaration8ede;completed source/publishedcontrols,report
URBAN_INTEGRATION_READINESS_20261116.md,outputs urban_integration_readiness.
Bothpublished463×1000populations EXACTfromharvest;releasedH/areas exact atCSV
precision(.1person/.01ha),unroundedtotalareasexact.151residualselection centres,
19capitalshifts,121lore-ranked,3globaltopslots. Raw1034/corrected1053sites fixed.
Fantasyfloodplainport26basins each,ZEROqualifyingcells:don'tchangeclimate/pop.

FOUND oldvalidation scope issues: globalsigma uses allouterresponses;training
OOFmeans canincludeoutertestresponses;19/95centreedges crossfold,trainingratios
couldreadheldoutcentrearea. Preserve old gatefalse/owneradoption;don'trelabel.
Source664/28caps/95edges,76closedtestedges(29/24/12/11);trainclosed47/66/70/83.

NewJOINTtrial declared3b08f56ab (hierarchy_refresh_trial.json)beforefits. COMPLETE
andindependently reviewed:8outerfits/24inner,560gridlosses,2five-seed664ensembles,
all664+strict153area scores,76closedheldoutpairs,6356CSVcells,8freshfilesexact,
4meaningfullabel-isolation/pairclosure/residualmultiset/CRPStests. Newcomponent
polity/urban_hierarchy_trial.py;producer/reviewer/plot scripts same stem.
Report reports/URBAN_HIERARCHY_REFRESH_20261116.md;outputs urban_hierarchy_refresh.

RESULTmodestpositive: same common repairedprotocol,refreshedH CRPS improves1.08%
all664/3.21%strict153;medianforecastMAE1.12/2.93%. PrimaryCRPSslightlyworsefold0;
areaKSmean.0536→.0551(slightlyworse),totalarearatio1.0399→1.0332. Closedpair
exceedshare9.21→8.95%vs6.58%source;medianratio.16806→.16765vs.16770. All11Egypt
strict targets STILLunderpredicted. Selectedphi/c identicalold/newbyfold:
(0,1.1),(1,.9),(.75,.6),(1,.6). NO full-data mapfit/adoption. StandaloneGaussian
andjointscores aredifferent estimands;don'tcompareCRPSnumericvaluestoNLL.

NEXT FROZEN hierarchy_candidate_build.json: finalsourcefit(all664training now,
4foldOOFselectionmeans/RMSsigma,all95pairs,70existinglosses,finalOLScoeffs),then
isolated application on SAMEpublishedsites/population,with exactunchanged
released-model control BEFOREinterpretingcandidate. Rebuild own/wider people
andlegacyannualcerealledgers,bothreadings. Candidatepreviewonly;metadata
gate.passed=False/adopt=False;runtime developmentguardadapter explicitlyallowed
inplan,canonicalfilesimmutable. ControlCSV/JSON/fieldsNPZ identities required;
missingcache reconstruction frompublished packets,NOclimate rerun/placement.
Fullseasonalfiniteorigin/food/labour/supply/staff/reach/transfer remainrequired
beforeadoption. Source28capitalcentres vsfantasy151marked assumption disclosed.
NoBuringhsizes/climate l. EarlierNEXTentries belowhistory.

# Controlled H-input predictive refresh complete — 16 November 2026

Continued AFTER exact-replay push through declared predictive refresh. Plan
population_refresh_pilot.json committed9e19c70ef before outputs. COMPLETED and
independently reviewed:5fixedalternatives,20outer/60inner fits,80support splits,
765predictionrows,200provincecases,40capitalgroups,10070CSVcells,7freshfiles
byteexact;3legacy/control mean/sigma vectorsBITEXACT;4leakage/accountingtests.
Report reports/URBAN_POPULATION_REFRESH_20261116.md;outputs
output/urban_population_refresh_20261116/. No adoptedcoefficients/map/defaults.

POSITIVEbutMODESTdevelopmentresult: samepopulationrecipe on qualifiedfloodplain
input improves pooledMAE2.89%(M1)/2.72%(M1C),RMSE3.49/3.37%;NLL−0.0373/−0.0357.
NLL+MAE improveall4folds;RMSEslightlyworsefold2. Fold3stillweak;all11Aegyptus
targetsSTILLunderpredicted(meanlogresidM1 1.441→1.207,M1C1.466→1.264).
No cure/independentvalidation claimed. P2/Frier wasn'tfit;wouldchangerecipe.
Original664mixedtraining/153stricttargets andoldfolds/capitals unchanged.

NEXT FROZEN integration_readiness.json: readonly actualfantasyharvest/population
equivalence audit +existingfantasyfloodplain-port evidence +FULLhierarchy/ledger
dependency inventory. StandaloneGaussianM1C isNOTpublishedjoint hierarchy's
residualselection/lore ordering. Sameformula isn'tphysicalfield equivalence;
fantasyclimate intentionallyr44,Earthr46. No newclimate rerun,fit,sourcepool,
map/defaultwrite inthatstage. Then declareoneactualfullpipeline comparison,
train-only uncertainty andappropriate evidence/transfer before adoption.
Fullorigin/food/labour checksrequired. Buringhsizes/climate l stayunopened.
PriorNEXTentriesbelowhistory. See exactreplaynotes for restoredcache and A1.

# Exact population-input replay complete — 16 November 2026 (climate parked)

Continued beyond BOTH audit pushes. Exact isolated floodplain grid replay now
PASSES SHA3b57d0cba03802d3693eb46e661771d6375715dc2f17f8555217ff0ff33fb338,
archivedregionbytes and1275qualifyingcells. Canonicalglobal/basin paths STILL
missing,unchanged;newarrayscache inoutput/urban_population_recipe_20261116/restored/.
Theyareignored,notpushed. This is alreadyexposed observed-weather harvest replay,
NOTclimatefitting. Reproducewithscripts/restore_urban_population_inputs.py.

Replay initiallyfailedTypeError(extra_crops) becauseoldFwrapperprecedes generic
Earthcaller maizeAPI. Failedreceipt/log/source snapshot preserved under
failed_legacy_wrapper/. A1(055c6a051)declaredBEFOREretry. Runtimeadapter drops
ONLYextra_crops=None/empty,old_world=True;nondefaultsrejected;originalscientific
files/params unchanged. Sixcontrols pass. Never patch pinned canonicalFscript.

THREEfixedpopulationrecipe comparison COMPLETE/independently reviewed:legacy,
floodplain settlement_base×sameoccupation, floodplaincapacity×history/P2/Frier.
All664records/153strict retainpositiveH,no source refiltering;1315fixedcentrecells,
3massbudgets,6cohorts/306provincecases,7503CSVcells,5fresh numericexports exact.
Review independently derivespopulationeqs/sampler andbruteallcentre ties/radius;
biomeclassifier andlegacyrowmapping reusedexplicitly. Report:
reports/URBAN_POPULATION_RECIPE_20261116.md;complete outputs in
output/urban_population_recipe_20261116/. CompactanonymousHmodel.npz tracked.

KEYRESULT: Aegyptus11strict medianPAIREDHratio2.55(samepopulationrecipe),9.19(P2).
GroupHmedians8355→38017/124747;ratioofmediansisDIFFERENTfrommedianpairedratio.
All-windowpeople119.354M→121.021M/103.518M;allowed54.040M→55.211M/61.400M.
Inputeffectmaterialbut NOarea fit/score/adoption. OppositeMoesiaerrornotexplained.

NEXT FROZEN population_refresh_pilot.json: fivefixedalternatives,M0control,
legacyM1/M1C exactpriorcontrols,and same-recipefloodplainM1/M1C. Mixed664training,
same153strict targets/4provincefolds,unchanged nested_fit and train-onlyinnerOOF
sigma.20outercases/765predictions/200provincecases,allretained. Fullrank/support
checknewX;no newhyperparams/exclusions. NoP2predictivecandidate becauseit changes
recipe relativefantasyapplication. Pairedpoint/properlogscores/coverage+folds,
independentQR/scalarreview,freshfiles,priorcontrolreproduction required.
SuccessfulEarthrefreshstillneeds actualfantasyharvest/population equivalence,
appropriatedeclaredtransfer andfullorigin/food/labour rebuild beforeadoption.
No climate,Buringhsizes/climate l,or population/cityarea multiplier. PriorNEXT
entriesbelowarehistory. Keep pinnedscientificfiles/tests immutable.

# Urban geographic/provenance audits complete — 16 November 2026

Continued from9b85fe35e through TWO independently reviewed audits. Geographic
residuals:24fold/240province/48capital cases,7878CSVcells,5fresh exports exact;
fold3 combinespositivebias andhigher variance,only2/36Houtside trainrange,top1
accounts20–22%SSE. No fold/outlier discarded. ReportURBAN_GEOGRAPHIC_RESIDUALS.

Full51province crosswalk now independently reviewed(664row identities,226basis
aggregates,240named residuals,7873CSVcells,5fresh exports). Province1=AEGYPTUS:
11strict targets all underpredicted by mixedM1,meanlogresid+1.441,NOcapitals.
Province40=Moesia Inferior,single opposite large residual. No causal inference.
Report reports/URBAN_HINTERLAND_PROVENANCE_20261116.md;outputs
output/urban_hinterland_provenance_20261116/. Code/receipt audit only,not newfit.

KEY: current Earth SIZE H is immutable Nov10rome_inputs dd98cc76,settlement_base
×occupation0.32457727,9km nearest occupiedcell60km. Current Earth SUPPLY has
floodplain capacity×history normalized toFRIER61.4M,globalgrid3b57d0cb,Greek-wall
qualified results6155cd48. Fantasy size APPLICATION uses published base×central
occupation,NOTP2/Frier/core-alternative. UpdatingEarthfit toP2alone changes its
relationship to application. Supply success DOESNOT validate unchanged sizeH.

NEXT FROZEN population_recipe_replay.json: exact isolated restore of existing
floodplain grid expectedSHA3b57d0cba03802d3693eb46e661771d6375715dc2f17f8555217ff0ff33fb338,
then SAMEoldsourcegeometry/masks/664rows compare immutablelegacy, floodplain
settlement_base×existingoccupation, floodplainP2/Frier. No newfit/scores/map.
Sourceglobal/basin arrays missing at audit;restoredbaseline341d2056 is DIFFERENT.
Never substitute it and claim qualifiedgrid identity. If restoration mismatches,
preservefailure anddo not adjustparameters. Read exactplanfor conservation,
paired absoluteH ANDnormalizedHshare,all51province/153strict summaries/review.
ZeroHrowsstay. Largearrayscache-only,compactHoutputs tracked. This replays
alreadyexposed observed-weather harvest,NOTnew climate physics/fit. Laterfit
requires declaredrecipeconsistency and alltransfer/food/origin/labour gates.
Climateparked,Buringhsizes/climate l unopened. Priorpinnedcode/tests immutable.

# Urban measurement pilot complete — 16 November 2026 (climate parked)

Continued beyond the source-audit push and COMPLETED the declared predictive
pilot. Plan88c9cb042;eligibility/design/support review committedc7aadb5c9 BEFORE
fit.664legacy rows,153strict exact Inhabited area targets across40provinces;
folds43/43/31/36,only4capitals. All32support splits pass. Sixfixed alternatives
(mixed/strict training ×M0/M1/M1C),24outer cases,72inner train-only fits for
predictive sigma. NOfull-data sigma leakage,no adopted coefficient or map update.

RESULT: strict training doesn't improve any model's pooled MAE/RMSE/NLL. Mixed
H model improvesMAE2.2%against intercept-only but worsensRMSE/NLL;strict H gain
~0.1%MAE and worseRMSE/NLL. Capital covariate helps some mixed summaries but
only4strict targets havecapital status. ALL6 alternatives weak onfold3(36targets/
10provinces),with undercoverage. Don't discard/reweight fold3 or claim proof
that extent definitions are equivalent. Models are standalone conditional
Gaussian regressions,not a full test of joint published hierarchy draws.

Report:reports/URBAN_MEASUREMENT_PILOT_20261116.md;outputs under
output/urban_measurement_pilot_20261116/. Support review reuses previously
reviewed unchanged geometry,checks new rawselection/design independently.
Fit review uses independent GELSYQR/scalar variance+normal densities;all24cases,
918predictionrows,240provincecases,11610CSVcells,6freshfiles exact;4meaningful
leakage/accounting tests. No Buringh sizes/climate l/new sources opened.

NEXT frozen geographic_residual_audit.json: NOFIT. Decompose fixed biases,
variance,NLL and H-support ranges for all6×4foldcases;all40provinces,n<5flags,
largest1/5/10error mass,all4capitals retained. Independent arithmetic +fresh
exports. Then formulate a SMALL independently supported hypothesis (broader
food access,roles,or dated extents) before further fitting. No new exponent grid,
size-derived role labels or geography exclusion. Appropriate transfer and full
origin/food/labour rebuild required before map adoption. Climate remains parked.
Earlier NEXT notes are historical.

# Urban source audit complete — 16 November 2026 (climate parked)

After pushing the negative concentration screen, continued to the declared
source-selection audit. DONE and independently reviewed:1,388cities/885areas,
332aggregatecells,2freshfiles exact;no new fit/scores.1354cities have catalogue
intervals containingAD150;492lackarea(36.3%),862havearea,806remain after legacy
20/30exclusion. Actual geographically filtered/corrected training664. Extents
mix inhabited areas,walls,urban grids;AreasCSV has NO independent area-date
field. City existence is not extent-date certification. Report:
reports/URBAN_DEVELOPMENT_EVIDENCE_20261116.md;outputs/scripts same stem.

NEXT is FROZEN calibration/urban_diagnosis_20261116/measurement_basis_pilot.json:
source-sensitivity comparison on EXACT Inhabited area subset of the existing
664row cohort,shared held-out targets,strict versus mixed training. First prepare
and COMMIT support receipt before any fit:old province4folds,each strict test>=10,
each inner train>=10 and fullrank M0/M1/M1C. Then all6fixed alternatives with
outerprovince folds and innertrain-only OOF sigma;all24outerrows,pairedpoint
errors,proper Gaussian log score and80/95coverage. No new parameter grid,source
pool,clipping,density or map outputs. Do not change eligibility after seeing
scores. Exact label is not date certification; report limits. No Buringh sizes
or climate l. No unqualified urbanprimacy/demographic claims. Plan contains
full metrics/reviewer/next-transfer gates. Earlier next-run entries are history.

# Urban concentration screen complete — 16 November 2026 (climate parked)

Owner's active direction remains settlement diagnosis/concentration first, climate
later. Latest work: reports/URBAN_CONCENTRATION_20261116.md; full320case outputs,
independent review and plots in output/urban_concentration_20261116/. NO variant
adopted: all nonidentity3km group means worsen source-CDF gap and paired log
distance, both readings/families; all60Mesopotamian nonidentity3km draws worsen
CDF gap. Larger maxima alone are misleading. Keep released settlement4/hostedv7
and climate/defaults unchanged.

Corrected supplied-site control also complete:119/27points, native AEQD geometry,
20cases/26tests; report URBAN_GIVEN_SITES_20261116.md. Invalid affine first run
preserved separately; amendment A1 disclosed.3km is primary(allHpositive),9km
retains5Iraq/7Mexico zeroH points, not evidence of uninhabited settlements.

Concentration implementation: polity/urban_concentration.py, scripts/
urban_concentration_screen.py, review_urban_concentration_screen.py and plot script.
Same requested urban-resident budget perbaseline/reading, bounded scalar allocation,
no food-feasibility claim. Review320cases,80identitycontrols,44tests,3fresh numeric
exports; maxbudgeterror5.82e-10people. Prior pinned files unchanged. Don't edit
earlier pinned producers/components/tests merely to add later work.

NEXT (declared development_evidence.json): source/selection audit of existing
Roman catalogue area-availability, exact20/30 exclusions, estimate bases, dating
fields and province folds; compare source versus actual training cohorts and the
survey town thresholds. No fit/scores in that stage; no further exponent search.
Then declare any source-aware predictive pilot before fitting; preserve separate
town-status failure rather than hide it with conditional truncation. Reserved
Buringh sizes and climate l unopened. Origin/food/labour rebuild and appropriate
transfer still required before any map adoption. Earlier entries are historical.

# Urban programme active — 16 November 2026 (climate parked by owner)

Owner accepted the settlement diagnosis/concentration direction; return to climate
later. Plans: calibration/urban_diagnosis_20261116/plan.json (2e059c2c5),
analysis_spec.json (6a362be71), then conditional_sites.json before given-site sizes.
Report: reports/URBAN_DIAGNOSIS_20261116.md. Existing maps/defaults unchanged.

DONE: restore exact source ZIP and owner-supplied Mexico workbook (SHA matches).
Both old results.json and model.npz replay BYTE FOR BYTE. New World Earth NPZ
also matches its old SHA. New inputs/replays isolated under output/urban_diagnosis_20261116/;
raw workbook in ignored data/cache/valley_of_mexico, not redistributed.
12 position / 30 seeded size cases independently reviewed, 12 component controls,
five fresh exports exact. Scripts: prepare_urban_diagnosis.py, urban_diagnosis.py,
review_urban_diagnosis.py. Source/field/size primitives and published files protected.

FINDINGS: archived size test used subset draws, no marked hierarchy or confluences,
and topN source ranks despite count/coverage differences. Source class6 is censored;
1783ha was the MODEL ceiling, not observed upper. Current unmarked confluences do
not cure the failures. Mexico still has ZERO model towns in the9km proxy, so its
size distribution is undefined. Its Classic cohort largest is76ha/1000estimated
people;840ha is from another period. All221 estimates equal PopMax; model/reference
ratio1.72 at upper estimate,3.57 at lower. This is rural/small-settlement evidence,
not a complete large-city primacy test. Do not multiply town counts to fit it.

NEXT RUN (declared conditional_sites.json): supply the119/27 observed town points,
retain fractional coordinates/collisions, allocate model hinterland people once,
then apply unchanged sizes on3/9km with five seeds. This separates size from
placement/count effects and is DEVELOPMENT, not an oracle forecast or blind test.
No capital labels invented; no density or urban fraction fitted; Buringh sizes
and sealed climate l stay unopened. Climate remains parked. The later entries
are historical, including the previous proposal-only status.

# Strategy review — 16 November 2026 (proposals; no new direction adopted)

Latest remote checkpoint reviewed: `5b0d03b19` (canonical and wonderful-mayer
branches shared it). Full assessment: `reports/STRATEGY_REVIEW_20261116.md`.
Release 4 / hosted v7 is current; Earth climate r46, fantasy atlas r44 intentionally;
Egypt-inclusive supply calibration passes in DEVELOPMENT, published share 34%.
Older release-3 / Egypt-failure “live” entries are historical, not current status.

Recommendation for owner consideration: first diagnose settlement observation
definitions and urban concentration on the ACTUAL published pipeline; then a
fixed-total rural/urban allocation comparison if supported. Tenfold hinterland
people changes the released size mean by only ~1.40x in area. The area cap is
~1,783 ha, not 200 ha. The old dense-core count excess is already addressed in
the published tiling; do not reopen WP8 on that obsolete baseline.

Population history remains promising, but start with a bounded pilot against the
existing core prior. Forest change is not a direct people count, and ancient HYDE
allocations are not independent truth. Road-generation testing can proceed as a
separate workstream if target roads are withheld from the generator/cost inputs.
Historical channels are a distinct diagnostic for the Mesopotamian position failure.
State formation and further climate refits are lower-priority proposals; preserve
the owner's painted claims, model defaults and reserved pools. No new blind values
or scores were opened/run by this review. The earlier six directions below remain
proposals; this review does not choose or adopt one for the owner.

# GEOGRAPHY OF CONTROL — 16 November 2026 (owner: natural borders, forests)
- [done] Forest map: C1b forest share published as atlas layer land_forest ("Forest (AD 200 potential)", raw + corrected;
  scripts/forest_map.py --publish; browser check passes).
- [done, NOT adopted] Basin cantons (A3, reports/BASIN_CANTONS_20261116.md): HydroBASINS L8 majority cantons keep accuracy
  (G1) but push borders onto watershed divides (x1.10) while real borders avoid them (x0.65-0.94): G2 fails in all three
  blind pools (T6 Ming 1400, T7 Tang 900, T8 Bosker 1200; now spent). River frontiers diagnostic: real borders avoid rivers
  except Han (x0.27-1.31), so no river-frontier rule was built.
- [done, ADOPTED narrowly] Forest in travel C2 (reports/FOREST_TRAVEL_20261116.md): walking coefficient from forest share;
  blind T9 Ming 1600, T10 Sui 609, T11 Bosker 1700 (spent): G1 and G2 pass by ~0.002. Effect on Earth about zero.
- [done] C2 map probe (control step only): held land -0.4 pts, owner changes on 0.8-1.0 % of land; no release yet (owner).
- [done, NOT adopted] Detailed forest stage 1 (reports/FOREST_DETAIL_20261116.md): farming clearing vs Zanon 2018 AD 200
  (5'; checkerboard blind): fit k = 0. Climate potential ranks Zanon well (Spearman 0.69); level 0.51 beats 0.60 (blind RMSE
  0.170 vs 0.184) -> owner decision. Model density correlates POSITIVELY with AD 200 forest (+0.37): people sit on humid land.
- [DISCARDED by owner] Detailed woodland scenario (untestable placement); script removed (history 88cf9e2d).
- [ADOPTED] Forest layer level 0.51 (blind-verified vs Zanon AD 200); land_forest republished raw + corrected; browser passes.
- [done] Cores diagnostic: cored density removes the wrong-way people/forest signal (+0.37 -> +0.04) but gives no clearing
  signal; forest stays climate-only.
- [done] Internal borders (reports/INTERNAL_BORDERS_20261116.md): map owner rule OA 0.89-0.99 on blind Europe 1400/1600,
  China 1140 (first Earth test of the owner rule; straight-line null equal). Cantons: OA unchanged (G1 fail, not adopted)
  but border recall +0.03-0.09 in all six pools. Real internal borders: divides x1.06-1.12; rivers x1.2-2.1 in Europe 1400+,
  x0.5 in China. Pools spent: Bosker 1400, 1600, CHGIS 1140 (dev reused 1200/1500/1200).
- [done, NOT adopted] River borders (reports/RIVER_BORDERS_20261116.md): crossing cost changes OA by <=0.0005; walking-only
  ownership beats the map's monthly networks in all 7 pools (+0.002..+0.015) but misses G1 (1800 +0.0098). Bosker 1000/1100/1800
  spent. Remaining unused Bosker years: 800, 900 (a walking-ownership test would need them; effect <1 % of contested land).
- [DONE] Release 4 HOSTED (owner: "Publish new atlas") as a NEW artifact https://claude.ai/artifact/XypoZqva951RWZm4ni6FiP
  (versions 1-6; 276 files, 232 MB; downloads capability declared). The old earth_fit/hub artifacts are not visible from the
  account now used; their links moved to atlases/artifact_links_retired.json and the new pack has no hub link.
  To fit the 511-file cap, scripts/package_atlas_artifact.py now bundles every layer .webp (not month frames, not names used in
  the page or scripts, not link images) into data/tiers_bundle_<k>.wasm; the page reads all layer images via tierImage (local
  atlas unchanged: no bundle there). Packed copy browser-checked: 83 layers x 2 climates, no errors.
  Republish: package to the scratchpad, then publish that same path in <=58 MB / <=240-file batches (or pass the url from a
  new session after reading it).
- [done] Owner: "tiny roads that lead to nowhere" on the Settlements map. Cause: the image drew minor tracks but not the
  drawn main roads; 89 of 186 track ends (corrected) meet a main road, none end nowhere. Fix (display only):
  scripts/redraw_settlement_roads.py redraws the 4 release-4 images with main roads in red (control without roads reproduced
  the published images byte for byte); legend item added; publish_settlement_release3/publish_wide_supply_release3 now pass
  roads too. Hosted v7 (4 changed files; packed copy browser-checked, 83 layers x 2 climates).
- Climate parked at r46 (set l unopened); remaining ideas need new Earth data or a new direction from the owner.

# NEW DIRECTIONS — proposed 16 Nov 2026 (owner asked for proposals; none chosen yet; recommended order 1 -> 2, 3 alongside)
1. **Population history over time** (recommended). Occupancy grows with time since farming and states arrived (a ledger from
   the Neolithic). Root of several failures: forest clearing not explained by people, too few/small towns in Mesopotamia and
   Mexico, cores only a partial fix. Earth checks: radiocarbon farming-arrival datasets; Zanon 2018 forest in 250-year slices
   (most slices unused: forest decline through time = independent people record); HYDE time slices; Han census. Large.
2. **Cities: where people were urban.** Rule for the largest cities' size from state age, irrigated alluvium and trade nodes.
   Earth: Chandler / Modelski / Reba, Bosker (check which pools are still unspent). Medium; better after 1.
3. **Generated road network.** Test the minor-track generator against real networks: Roman towns + terrain -> generated
   network vs Itiner-e (cached); Han roads as a second check. Medium; independent.
4. **Where states form.** Predict the number and split of independent polities from towns, terrain and people; Earth:
   Cliopatria (many unused years). On the map only advisory (painted claims stand). Large, research-like.
5. **Climate: monsoons and rain shadows.** New physics: separate the African and Asian monsoons (now one itcz_shift), lee-side
   drying; sealed set l ready. Large and uncertain (four refits stalled).
6. **Herders and the steppe.** Where mobile herding dominates over farming; Earth: D-PLACE / Ethnographic Atlas, historical
   farming-herding frontiers. Medium.
- Sources re-fetched this session (ignored cache): hydrobasins, chgis_v6_20261107 (sha matches), cliopatria_full_20261107
  (pinned archive), bosker_cities_20261107 (Dataverse 24747), hanson2016 (rebuilt from OxREP CSV; A3 dev reproduces within 0.002).

# RELEASE 4 PUBLISHED (settlements; WP3 river confluences) — 16 November 2026
Positions: release-3 tiling x (1 + exp(-(d/15 km)^2)) to river junctions (ROTCLIMATE_CONFLUENCE_K=1.0; dev Han/Rome pass, blind Buringh
1300 pass +0.028). Build: settlement_chain.py calibration/settlement_chain/release4_confluence.json build -> copied to
output/settlement_release4_20261116; publication scripts/publish_release4.sh (settlements, note, supply, ensemble, reach, layers) +
scripts/release4_reach_chain.sh (control v2/v21, supply-fed and 'request') ; images moved to data/release3/reach{,_fed}; originals
restored. Counts unchanged (883/902 proposed, 151 marked); 56-58 % moved (median 1 cell); staffed 1023/1042; held v2.1 66.6/66.8 %.
Controls reproduced all published raw/corrected layers. Browser: settlements 12, supply 8, reach/trade 16, supply reach 8, admin 12,
hierarchy 12; fit hub rebuilt; Windows checkout checked. Imperial access/administration not republished (as release 3).
NEXT (owner, 16 Nov): basin cantons + river frontiers Earth test (A3/E); forest map (C1b) on the atlas.

# CLIMATE CAMPAIGN — LIVE PLAN / TO-DO (owner: "keep going until you get a valid climate update"; updated as work proceeds)
Base: r46 (adopted 15 Nov, Earth only; atlas stays r44 by owner decision). Valid update = policy_v3: dev49 S<=0.995 with T,P <=+1%,
fine28 S<=1.01, then ONE run on an unseen sealed set (now set j, calibration/sealed_20261115j; release recorded from the owner's
instruction for the first dev+fine finalist).
- [done, near miss] Step 1 grand refit on r45 (calibration/grand_refit_20261115/plan.json): best S49 0.995097 (T -0.16%, P -0.82%)
  misses 0.995 by 0.0001. Best: storm_convection 0.52, ice_saturation 1.0, eddy_rate 1.65, instability 1.83, edge_carry ~0.01.
- [done] Step 1b extension: finalist S49 0.99458, fine28 0.982 PASS; sealed set j S 1.016 (rain +4.2%; Java, Cuba, Pilbara,
  Cameroon worse) FAIL. Set j spent. Not adopted. Lesson: dev49 is mid-latitude/subtropical; the free sealed boxes are tropical.
- [found] r45 on the spent pool (44 regions): equatorial continental interiors nearly rainless (W Amazon 3 %, Congo 7 %,
  Angola 5 %, Cameroon 25 % of observed rain); dry-state lock (RH 0.45, soil dry); edge_inner (e81), deeper soil (e82 start
  share) only reach Congo 38 %. Out of the map's band; recorded as an open problem.
- [done] Sealed set k declared inside the map's band (six 300 km boxes, 25-55 deg).
- [done] Step 4 grand refit v2: dev49 1.0023 FAIL (pool 0.966, fine 0.999). Trade-off: v1 (dev 0.9946 / pool 1.023) vs v2.
- [done] Step 5 refit v3 (minimax): best 0.9960 on both sets: FAIL by 0.001. Parameter refits exhausted; set k unopened.
- [done] Step 6 e83 trade_heat_low (trades give way under heat lows): Bengal May winds turn southerly; screen neutral
  (Najd/Algeria/Bengal better, Sahel/Mexico worse); T10 S49 1.0000, pool 1.009.
- [done] Step 7 refit v4 (v3 best + e83, minimax): best 0.9956 FAIL; S49 alone reaches 0.9949 (pool 1.006).
- [DONE] Step 8 refit v5 finalist: dev49 0.99450, fine28 0.975, sealed k 0.964 -> **r46 ADOPTED** (Earth; atlas stays r44).
  reports/CLIMATE_R46_20261115.md; calibration/local_accuracy_20261023/r46_adoption.json. Sealed sets i, j, k spent.
- Open climate problems: equatorial interiors, Bengal, rain shadows; a new sealed set is needed first.

# WP6 MAIZE — 16 November 2026 (owner to-do)
- [done] MAIZE in scripts/land_people.py (FAO 66 maize chapter: base 8 C, upper 30, Kc 1.07-1.12, landrace HI 0.3, low-input
  1-2 t/ha; FAO-33 Ky 1.25; USDA 3650 kcal/kg; grain 1.0 t/ha). Opt-in: analyse(extra_crops=, old_world=False);
  land_people_earth.py --window --extra-crops maize --new-world; ETOPO/slope caches per window. Defaults unchanged (tests pass).
- [done] Declared Earth check (calibration/maize_20261116/plan.json) vs MapSPAM 2010 rain-fed maize (data/cache/mapspam2010):
  Spearman 0.42 (>=0.30), coverage 0.976 (>=0.80; weak: maize suits 95 % of cells), June start in central Mexico: PASS.
- [done] Valley of Mexico blind test (reports/VALLEY_OF_MEXICO_BLIND_20261116.md; cores San Lorenzo, San Jose Mogote, El Mirador):
  P positions PASS (0.616), N rural people PASS (ratio 1.72; Teotihuacan city not in the survey), S sizes FAIL (no model town in
  the surveyed area). Pool spent. Same finding as Mesopotamia: too few, too small towns where people were urban.
- Town count/primacy (both blind size failures): an Earth-test artefact in part (no marked places on Earth; the map's lore
  capitals carry the capital and hierarchy terms); Mesoamerican sites hold ~18 people/ha vs 100-500 in the Old World rules.
- Town count vs density (reports/TOWN_COUNT_DENSITY_20261116.md): in the densest 10 % of Earth blocks the model places 2.3-6.9x
  the catalogue towns (about right elsewhere); WP8: the over-count is the old production baseline's; the published release-3 tiling (history-weighted) already scores
  Han 0.996 / Rome 1.322 deviance vs 1.75 / 1.77 for production. No change needed. Blind size failures = sizes/primacy.
- NEW BLIND POOL reserved: Buringh 2021 European urban population 700-2000 (data/cache/buringh2021, CC0; header only read) for WP8.
- WP3 confluence factor: dev screen pass (k 1.0) and BLIND PASS on Buringh 1300 (+0.028 composite; reports/WP3_CONFLUENCE_20261116.md).
  Map integration declared (calibration/wp3_site_factors_20261116/map_integration.json): ROTCLIMATE_CONFLUENCE_K=1.0 in
  prior_tiling_sites (default off); spec calibration/settlement_chain/release4_confluence.json; [running] staged build
  (settlement_chain.py ... build -> output/chain_staging/release4_confluence); then checks, then publication.
  Staged so far: counts unchanged (883/902), marked unchanged, 56-58 % of proposed towns move (median 1 cell, 70 % within 3);
  placement review passes (reviewer got an independent confluence factor); supply needed ROTCLIMATE_RELEASE3_DIR (added).
  STAGED BUILD COMPLETE (all stages incl. integration/labour/fertility on staged atlases built by scripts/stage_atlas.py +
  export_reach_release3.py; legacy control reproduced all 220 published corrected files). Staffed raw 1023 = 1023, corrected
  1042 vs 1041; fed residents raw 10.97 M -> 10.77 M. [next] publication: settlements panel, supply, control v2/v21 reach on the
  staged staffing, supply reach, reach/trade layers (publish_downstream_release3), imperial access + administration, ensemble,
  browser checks, fit hub, checkout. Staging: output/chain_staging/release4_confluence (ignored).
- WP1 moot (seats are lore inventory). r46 on the map (ds8): zonefit 0.175 = r44, strict 31.4 % vs 32.4 %: no rebuild case.
- [done] Gated dry-heating refit on r46: FAIL (best S49 0.9982; stopped by a container restart at 30/40, disclosed).
  Cause: the land rain belt reaches ~22.5 N in Africa too (Sahel rains 2 months early, false summer rain in Najd/Sahara).
- [done] e84 instability_cap (desert air caps convection; calibration/instability_cap_20261116): screen neutral, FAIL
  (Sahara/Najd better, India worse).
- [done] Joint refit r46 + e84 + dry heating + e83: FAIL (best S49 0.9979; no feasible point). Four refits around r46 now stall at
  0.998-0.999: CLIMATE PARKED at r46 until new physics (African rain belt vs South Asian monsoon; equatorial interiors). Set l unopened.
- [next if 1 passes dev+fine] Step 2: sealed set j once -> adopt r46 (record like r45_adoption.json); atlas rebuild only if owner asks.
- [if 1 fails] Step 3 major rework candidates, in order:
  a. South Asian spring circulation (Bengal: northerlies + e70b branch drying until June, land 4 C too hot) - a land-sea
     pressure/sea-breeze inflow term gated by the sea next to heated land (deserts lack an adjacent warm sea).
  b. Moisture transport in two levels (low-level water blocked by ranges, upper level passes) for rain shadows and inland winters.
  c. Summer rain-making season-aware (humid mid-latitude summers 0.5-0.8x).
- Owner to-do after the campaign: MAIZE (crop model, Valley of Mexico pool).

# r45 ADOPTED (Earth); ATLAS STAYS r44 (OWNER) — 15 November 2026
r45 = e79 moisture carry + refitted rain settings (calibration/local_accuracy_20261023/r45_adoption.json; dev49 0.9901, fine28 1.0098,
sealed i 0.9833, set i spent). Owner: skip the atlas rebuild. Next climate iteration (reports/MONSOON_R45_20261115.md): Bengal
(worst, 1.23) is a spring-circulation error (northerly winds and e70b branch drying until June, land 4 C too hot); e40/e47 trade
with Australia; new e80/e80b heat-low damping fails (deserts). No new sealed set declared yet. NEXT (owner): maize.

# CLIMATE: NORTHERN STEPPE + RAIN SHADOWS — 15 November 2026 (settlement WP5 parked; owner: switch to climate)
reports/NORTHERN_STEPPE_20261115.md. Painted cold_dry zone (40-46 N): atlas median 830 mm, 2.3x the dry threshold, Csa-like
(winter rain on easterlies; planet retrograde, tilt 33.5). r44 on Earth steppes is NOT too wet (Caspian lee 167 vs 128 mm; cold
steppe winters too DRY: Kazakh 239/307, Volga 351/481). World knobs (scripts/probe_steppe_world.py): best 1.9x and it breaks the
Mediterranean/warm zones; a 3,000 m ridge east of the zone: ds8 2.60 -> 2.26. Owner options: rezone as cold-winter Csa, or a range
upwind (east) once rain shadows are stronger.
Rain shadows too weak on Earth (lee 1.35-2.05x obs, windward 0.65-0.73x). calibration/rain_shadow_20261115: one-knob screen FAILED
(25% bar); A1 eddy_rainout candidates E1-E3 FAIL dev49 (S 1.021-1.029; flat humid regions + central Asia/Tibet worse); A2 new opt-in
physics e74 eddy_rainout_relief_km (crest cap only where ground stands above its eddy-scale surroundings) -> F1/F2 gate
(gate2). ALL FAIL: A1 E1-E3, A2 F1/F2 (1.018-1.019), A3 G1/G2 with e74b padded steps (bug: e3's six separately edge-padded
Gaussians differ from one kernel by 5% of the field on regional grids; every earlier e3 result carried it), e74c accounted
crest condensate (screen, worse), A4 e4 eddy height 4/6 km (1.048/1.022). Each lever dries ranges along with the lee; next: accounted
upslope rainout along the mean wind (new physics). Report section 8.
Then e75 upwind-barrier cap on eddy water (eddy_barrier_km/_dz_km/_crest; plan_e75.json, refit_e75.json): crest-height C05
fixes westerly lee basins but S49 1.015 (C10 1.037), frozen 4-knob refit best 1.012: FAIL. Blocker: r44 offsets summer/inland
deficits with lee over-wetting (US Midwest summers 65 vs 93 mm); e75 needs the summer rain-making fix alongside. Section 10.
Summer: e76 instability_t0 (J1 18 C: S49 1.014; with C05 1.026/1.045) and e77 storm_convection (K1/K2 1.000/1.002, neutral): FAIL
(plan_e76.json). Joint refit e75+e77+8 rain settings (joint_refit.json, 40 evals): best S49 0.9986 > 0.995 FAIL; it backed e75 off
(crest 0.06), rain shadows ~r44. Rain-shadow line closed; r44 stays; sealed set i unopened. Sections 11-12.
Cold-interior winters: gate binds, not storms (Kazakh Jan W 2.0/Ws 3.6, RH 0.56). e78 ice_saturation (calibration/cold_winter_20261115):
L1 S49 0.9992, L2 0.9996 FAIL (clean but small). Missing: winter moisture transport far inland. Section 13.
Moisture carry e79 edge_carry (land-edge inflow keeps its water, not RH): M1/M2 fail; joint refit (calibration/moisture_carry_20261115/
joint_refit.json) finalist S49 0.9901, fine28 1.0098 -> PASS dev+fine; 23/49 better, Kazakh/Volga not improved, holdout +3.7%.
NEXT: sealed set i ONCE, only with owner release (scripts: benchmark finalist_params vs r44 on calibration/sealed_20261115i). Section 14. Sealed sets d-h spent; NEW sealed set i declared
(calibration/sealed_20261115i, 6 mountain boxes, audit scripts/audit_sealed_separation.py); open only with the owner's release.
WorldClim vapr zip downloaded into data/cache/worldclim (benchmark_local needs it).

# SETTLEMENT HIERARCHY PUBLISHED (OWNER REQUEST) — 15 November 2026
reports/SETTLEMENT_HIERARCHY_20261115.md. Swap rule tried and reverted (owner). A4 model: M1 means + 0.8 for the 19 seats; every marked
place takes the largest residual of itself + half its 75 km cluster (scripts/settlement_hierarchy_soft.py fit; map via
scripts/settlement_hierarchy_map.py, review_settlement_hierarchy_map.py). Corrected: proposed > marked 43% -> 12%; 13.35 M residents;
84.8% fed at 34%; staffed set unchanged (reach maps kept). Published; checks pass. A4 held-out exceed share 0.8% vs 6.3% = narrow miss.

# CAPITAL TERM ADOPTED ON THE MAP (OWNER) — PUBLISHED — 15 November 2026
M1C (2.095 + 0.124 lnH + 1.255 capital), capital = 19 provincial seats (hierarchy_links province_seat). Plan
calibration/capital_term_map_20261115 (+A1 no top-draw promotion under M1C; +A2 capital & major cities take the 3 largest areas).
scripts/capital_term_map.py (wrapper over build_settlement_release2/3), review_capital_term_map.py, supply via exec_with,
reach chain: build_supply_fed_reach -> run_on_release3 build_control_v2/v21 (folders *_supplyfed_captown_20261115; v21 needs
control_v2 path redirected too); builder images written into data/ moved to release3/reach_fed and originals restored.
Corrected: 11.26 M residents, capital 208k, 91.2% fed at 34%, 1,041 staffed, 68.1% held. Checks pass (browser 3x8, checkout).

# CAPITAL EFFECT (DEVELOPMENT): ROMAN CAPITALS ~3.4x THE SIZE MODEL — 15 November 2026
reports/CAPITAL_EFFECT_20261115.md; plan + A1 before output; scripts/capital_effect.py; Wikidata capitals (data/cache/roman_capitals).
28 matched capitals: factor 3.4 (2.3-5.2), 3.1 without Rome; mean percentile 0.82; 54% in top 14%. Supports lore-rank allocation,
but reordering cannot create >200 ha cities (Mesopotamia failure). M1C REFIT (calibration/size_capital_term_20261115): capital coef >0 in all folds (x2.8-4.1); capital MAE 1.27 -> 0.85;
all-town MAE -1.7% < declared 2% -> NOT ADOPTED. Owner decision whether to adopt on capital-specific evidence (post-hoc).

# OWNER TO-DO LIST (standing)
- ADD MAIZE to the crop model (owner request 15 Nov 2026). Unlocks the Valley of Mexico blind pool (data/cache/valley_of_mexico,
  headers only read) together with New World heartland cores; needs Earth sources for maize yields/phenology first.
- Allchin (ed.) 1995 The Archaeology of Early Historic South Asia (data/cache/allchin_1995, owner-supplied): no compiled table of
  city areas (areas scattered in prose, several seen while searching); not usable as a blind pool.

# REBA/MODELSKI CITY TEST: TOO SPARSE (6 CITIES), NOT SCORED — 15 November 2026
calibration/reba_cities_blind_20261115 (declared before values); scripts/reba_cities_blind.py; output/reba_cities_blind_20261115.
Only 6 Modelski AD 200 cities outside the Roman/Han pools (+2 Chandler AD 100) < declared minimum 10 -> not scored; pool spent.
Cliopatria v0.2.1 rebuilt from Zenodo 23128623 (data/cache/cliopatria/geo). Valley of Mexico survey cached and reserved
(data/cache/valley_of_mexico, 2,052 site-period rows; needs an Earth harvest grid for Mexico; no maize in the crop model).
NOT RUN (assessed 15 Nov): no maize -> harvest-based people wrong; heartland prior uses Old World cores (history ~0 in Mexico)
and a Mesoamerican core would be Teotihuacan itself (circular). Usable only after adding maize + New World cores. Pool still unread (headers only).

# SECOND BLIND POOL SEARCH (15 Nov 2026): NO DIRECTLY USABLE OPEN POOL
Rejected: Chelazzi & Lawrence PLOS One 2026 (zenodo 20172243) ends in the Iron Age; Altinisik 2022 zenodo 7086441 is aDNA;
Palmisano 2021 / Bunbury Southern Levant are radiocarbon-era; Hartwell CHGIS has no historical populations; Stadester 1.0
(zenodo 17180328) is pseudonymous, spline-interpolated from Chandler/Modelski/Wikipedia (derived, not observations).
Candidates needing owner download (login/paywall): Valley of Mexico survey (tDAR project 192; Classic sites with areas;
caveat: maize not modelled); Reba et al. 2016 Sci Data doi:10.1038/sdata.2016.34 (Chandler/Modelski cities with coordinates;
SEDAC login); Early Historic South Asian city areas (Smith 1995/2006 tables; book/papers).

# FIRST BLIND TEST OF POSITIONS AND SIZES: SOUTHERN MESOPOTAMIA AD 200 — BOTH FAIL — 15 November 2026

Report reports/FLOODPLAINS_BLIND_20261115.md; plan ae9e2e36 (+A1 swapped lat/lon before scoring, +A2 SizeHa is a class code,
after first scoring, disclosed). Source: owner-supplied bnza/archiraq zip (data/cache/floodplains_archiraq, ignored).
Positions: sites >= 10 ha at percentile 0.48 (pass 0.55); capture 0.19 vs 0.14 previous rule. Sizes (semi-blind): observed 12
largest = 9 x 40-200 ha + 3 x >200 ha; model none >200 ha, total ~490 ha vs >= 964: FAIL. Likely causes: modern river
lines vs ancient channels (no canals/palaeochannels); size model cannot make plain-scale megacities. Pool SPENT.
Review passed (12), fresh exact. Nothing on the map changed.

# BLIND-POOL SEARCH FOR POSITIONS/SIZES: NOTHING USABLE FOUND YET — 14 November 2026

Calibration page updated (reach rule v2.1 blind: CHGIS 1080 0.737 vs 0.697, Pleiades 550 0.774 vs 0.766; population pattern
blind: Domesday 0.63; trade/administration untested; positions/sizes development only).
Searched for an unseen AD 200-era pool with site positions AND areas:
 - Hartwell CHGIS v5 (doi:10.7910/DVN/29302): schema only, no historical population fields (registered in dataset_usage).
 - Adams/Heartland of Cities, FloodPlains Web GIS (JAMT 2024, doi:10.1007/s10814-024-09197-3; paywalled here), QADIS,
   Hritz digitized maps: no public dataset found (Zenodo API searched).
Spent pools (dataset_usage.json): CHGIS 280/610/742/1080/1200/1580/1820, Bosker 1300/1500, Pleiades -200/550, Domesday.
Candidates still to check: owner-supplied FloodPlains/QADIS site table (Parthian/Sasanian sizes), Bosker 800-1200 (era gap).

# SIZES REFIT WITH GREEK WALLS + SUPPLY AT 0.337: BUILT AND REVIEWED, NOT YET PUBLISHED — 14 November 2026

OWNER: "keep improving our model". Report reports/SIZES_GREEK_WALLS_20261114.md; plan calibration/sizes_greek_walls_20261114.
scripts/sizes_greek_walls.py (M1 refit 1.915 + 0.147 lnH, sigma 1.048, KS 0.063 PASS; control reproduces archive),
build_sizes_greek_walls.py (release-3 sizes; positions identical; 13.62 -> 12.74 M residents), wide_supply_greek_walls.py
(0.337: corrected 89% fed, 33 short; staffed set identical 1042/1023). Existing reviewers pass via scripts/exec_with.py.
PUBLISHED (owner permission): default Settlements = refit sizes + 34% supply; reach note updated (staffed set unchanged);
old supply_central_x39.webp removed. Browser checks (3 x 8) and Windows checkout (2,217 assets) passed.
FLAT READING: calibration/supply_low_reading_20261114 PASSES at 0.140 (flat 100/ha Earth residents); map's release3_low
now uses low_x14 (corrected 99.2% fed, 11 short). Default sliding option keeps central_x34.

# EARTH SUPPLY CALIBRATION PASSES WITH EGYPT (DEVELOPMENT) — 14 November 2026

Report reports/GREEK_WALLS_20261114.md; plan 0612e043; source Hansen GRBS 48 (2008) 259-286 (owner-supplied PDF, not committed).
scripts/greek_walls.py: 58 Greek (Achaea/Macedonia/Epirus) wall-basis Hanson areas -> inhabited share 1/2 (1/3 if >= 100 ha),
sliding density on the inhabited area; with floodplain rule + Frier 61.4 M heartland people: PASS. W/E x1.003, 270 km best,
transfer 0.950/0.951, e95 0.337 (adopted 0.3923, within x1.25). Variants (Asia Minor; literal 150/ha) also pass.
Review passed (280), fresh exact. Fantasy map unchanged.
OPEN OWNER DECISIONS: (1) marketed share 0.39 (without-Egypt) vs 0.337 (with Egypt, development); (2) whether the size
model should discount Greek wall circuits (sizes currently left as owner set).

# EAST/WEST GAP LOCATED: GREECE AND THE FAYUM — 14 November 2026

scripts/east_gap_diagnostic.py (post-hoc) -> output/supply_people_level_20261114/east_gap_diagnostic.json; section in
reports/SUPPLY_PEOPLE_LEVEL_20261114.md. At the west's 95% share: Greece/Aegean 74% fed (339k short; Peloponnese towns
6-15%), Egypt 83% (Arsinoe/Fayum 3%), Asia Minor 96%, Levant/Syria/Cyrenaica/Balkans 100%.
Hypotheses (untested): Greek Hanson areas are 65% wall circuits (37% elsewhere) -> residents overstated; Fayum needs Bahr Yusuf
canal basin. Need a source for the inhabited share of Greek circuits before any sensitivity. Candidate: Hansen, 'An Update on the Shotgun Method',
GRBS (grbs.library.duke.edu article 951; host returned 502 on 14 Nov). Search summaries only (unverified): inhabited share varies
20-90%, smaller cities more built-up, worked examples assume about half. Do not use until read.
Owner earlier: map sizes stay as they are.

# FLOODPLAIN RULE PORTED: NO FANTASY RIVER QUALIFIES; MAP UNCHANGED — 14 November 2026

Report reports/FANTASY_FLOODPLAIN_20261114.md; plan calibration/fantasy_floodplain_20261114. harvest/floodplain.py (rule),
scripts/fantasy_floodplain.py (wrapper on derive(); export.py untouched), review_fantasy_floodplain.py passed.
All 26 atlas basins flood months 0-4 after the winter solstice with 350-560 mm rain: local winter-rain rivers (Tigris-like),
none Nile-like. Settlement base, placement, sizes, supply, reach unchanged; no atlas file rewritten.
Calibration status: share 0.39 inside all near-passes (0.36-0.43); whole-empire supply with Egypt misses transfer 0.884 vs 0.90.

# PEOPLE LEVEL: EGYPT FED, WHOLE EMPIRE STILL JUST SHORT — 14 November 2026

OWNER: "Fix the people side first, then port to the fantasy map." Report reports/SUPPLY_PEOPLE_LEVEL_20261114.md, plan 3244339a.
scripts/supply_people_level.py (heartland pattern on floodplain grid; Frier 61.4 M on Roman land = primary; absolute = sensitivity).
Frier: Egypt 5.77 M, Egyptian cities 89-96% fed at 0.4-0.5, e95 all 0.388, W/E x1.24 kept, transfer 0.884 < 0.90: FAIL (narrow).
Absolute: Egypt 4.83 M but 270 km not kept (W/E x1.33, also without Egypt). Review passed (60), fresh exact.
NEXT: port floodplain rule to the fantasy harvest (declared step, controls), as the owner asked.

# FLOODPLAIN LAND RULE (DEVELOPMENT): EGYPT CAPACITY FIXED, SUPPLY NARROWLY FAILS — 14 November 2026

OWNER: "Go ahead with the floodplain rule." Report: reports/FLOODPLAIN_RULE_20261114.md. Plan b5dd9b73 + A1 + A2 (post-hoc, disclosed).
Rule (scripts/floodplain_earth.py, off-by-default wrapper -> output/land_people/earth_floodplain/earth.npz, ignored; rebuild ~20 min):
HAND<=5 m & <=30 km of navigable river; atlas flood ends Jul-Oct; <100 mm rain in flood months -> full water, annual,
winter cereal (A1), farmed 0.95. T1 PASS (all other regions 0.00%). T2 PASS after A1: Egypt 2.32 -> 5.83 M (orig 10.12 fail).
T3 after A2 (rule in supply production, scripts/floodplain_supply.py): 270 kept (x1.23) but transfer 89.2% < 90%: NARROW FAIL;
e95 all 0.43; without Egypt 0.365. Side effects: Sudan Nile, Hetao (Han-era irrigated; untested), Yarlung Tsangpo.
Review passed (82), full fresh rebuild byte-exact. Fantasy map NOT changed.
NEXT: owner decision whether to port the rule to the fantasy harvest (changes desert-river harvests + downstream);
remaining Egypt gap is people (heartland pattern gives Egypt 6.65 M vs 4.5-5 M).

# ADOPTED SHARE 0.39 ROBUST TO PEOPLE PATTERN; EGYPT STILL OPEN — 14 November 2026 (settlement lane)

Report: reports/SUPPLY_HEARTLAND_PEOPLE_20261114.md; plan declared before output. scripts/supply_heartland_people.py,
review_supply_heartland_people.py passed (68), fresh exact. People = blind-tested heartland pattern capacity x
exp(-D/800) rescaled to the window total. Without Egypt: PASS, e95 0.372 vs adopted 0.392. With Egypt: fails
(Egypt proper 2.55 M people; +yield x2.16 east e95 0.81, transfer 0.86). Crash/OOM fixes in the cache disclosed.
Two-part Egypt fix: part 2 (people follow capacity) = existing heartland pattern; part 1 (floodplain output per km2) open.
FLOOD TIMING CHECK (scripts/earth_flood_timing.py -> output/flood_basin_irrigation_20261113/flood_timing.json): the atlas's own
monthly river flow on Earth floods in the right order but 1-3 months early (Nile Aug vs Sep; Euphrates/Tigris Apr vs May,
r 0.15; Niger Aug vs Oct-Dec: no travel lag). A timing driver needs a lag or a declared ~2-month tolerance.

# EGYPT HARVEST ALONE DOES NOT FIX THE WHOLE-EMPIRE SUPPLY CALIBRATION — 14 November 2026 (settlement lane)

Report: reports/EGYPT_SUFFICIENCY_20261114.md; plan 45f3d8de declared before outputs. scripts/egypt_sufficiency.py
(network memoised; control = archive exactly), review_egypt_sufficiency.py passed, fresh byte-exact.
Egypt yield x1.94/x2.16 (+/- farmers): all FAIL. East e95 0.61-0.67 vs west 0.38 (x1.6-1.75 > 1.25).
Post-hoc diagnostic (egypt_sufficiency_diagnostic.py -> diagnostic.json): the mask includes Sinai/S. Levant, which
supplied most surplus. Egypt proper (lon<=32.6): committed people field 0.71 M (history 4.5-5 M, x6.5 low), city
residents 1.21 M; labour-limited production, so yield barely helps. Nile freight is cheap (Alex-Arsinoe ~30 vs 270).
Fayum barely cropland (4/56 cells irrigated).
FOLLOW-UP DONE (calibration/egypt_people_sufficiency_20261114, review passed, fresh exact): Egypt-proper people
4.5/5.0 M with yield x1/x2.16: ALL FAIL, east never 95% at 270. Farmers eat the land's potential (surplus 0 at
y=1). Binding: output per km2 (1 t/ha x 0.6 farmed x 0.6 sown) AND people at ~0.3 of capacity (occupation).
NEXT: two-part upstream fix: declared floodplain land rule (NCP/Wei/Meso constraints) + people following capacity there.

# FLOOD-BASIN RULE GROUNDWORK: NORTH CHINA PLAIN IS A CONSTRAINT — 14 November 2026 (settlement lane)

scripts/flood_basin_constraints.py -> output/flood_basin_irrigation_20261113/constraints.json; figure
reports/figures/flood_basin_constraints_20261114.png. Diagnostic only, nothing fitted or changed.
Low land <=5 m above a navigable river within 30 km: Nile 24,600 km2, Lower Mesopotamia 64,000, North China
Plain 35,800 (its census set FALLOW: fitted), Wei 900. A terrain-only basin rule would inflate the fitted NCP.
Rain in flood months: Nile 0-4 mm, Meso 26, NCP 382, Wei 328 (Yellow/Wei flood months from literature).
Candidate driver now listed first in calibration/flood_basin_irrigation_20261113/plan.json: flood outside the
rain-fed season AND receding shortly before cool-season sowing (separates Nile from both). NOT declared.
NEXT: qualify a held-out desert river (Indus/Sindh inundation or Niger inland delta) and monthly flow for the
Yellow River, then declare the rule with NCP/Wei/Meso as constraints before any scoring.

# RELEASE-3 PLACEMENT ON VIDARBHA: GUARD PASSES — 14 November 2026 (settlement lane)

Report: reports/VIDARBHA_RELEASE3_20261114.md; plan 3af474e0 declared before outputs (exposed region, not blind).
Primary cohort: 10 km capture release 3 = production = 0.121; mean percentile 0.461 vs environment 0.444.
Rank delta +0.017, capture delta 0.000, support 53, constraints pass. No harm, no measurable gain.
All percentiles < 0.5 but within ~1.4 SE of chance (n~53); post-hoc component breakdown shows no driver. Vidarbha cannot calibrate the site score.
Reviewer scripts/review_vidarbha_release3.py passed (4,536 scalar checks, 794 towns spacing); fresh byte-exact.
EVIDENCE PAGE: atlases/earth_evidence/settlement_calibration/ (scripts/publish_settlement_calibration.py, hooked in
publish_earth_evidence.py; hub link in build_fit_hub.py): layer-by-layer calibration status of the default map.
Browser check scripts/check_settlement_calibration_browser.js passes; Windows checkout check passed (2,217 assets).
Note: pyproj was pip-installed into .venv for the reviewer (the 2026-11-11 reviewer also needs it).

# TIGRIS ADDED: NO CHANGE TO MESOPOTAMIAN ROOT WATER — 14 November 2026 (parallel lane)

Parallel to the field-water lane (crop phenology is that lane's FIRST NEXT; not touched here).
Report: reports/TIGRIS_GAUGE_20261114.md. Plans: calibration/tigris_gauge_20261114/plan.json
(4e19dbee) and field_plan.json (224fe579), both before outputs.

GAUGE: RivDIS Tigris at Mosul (PANGAEA.218902) qualifies on the Hit rules: same six complete
years 1965-67,1969-71, May peak, flood excess 4.82 km3/yr; Hit+Mosul pooled 11.05 vs Hit 6.24.
Baghdad (PANGAEA.218359) only 3 complete years, unscored. Mosul is above the Zab/Adhaim/Diyala:
understated, NOT scaled. scripts/tigris_gauge.py, review_tigris_gauge.py (regex/Decimal/scalar).
FIELDS: scripts/tigris_fields.py reruns the pinned matched-weather case code for the 8
Mesopotamia matched cases with only source_m3 replaced by the pooled excess. Root coverage
UNCHANGED (diff <1e-17); delivered 0.595 -> 0.86 km3, all extra spent as bare-soil evaporation
before sowing; 10.2 km3 flows past (spring peak, Aug-Oct capture window).
Rain-only cases equal archived arrays exactly. review_tigris_fields.py passes (3,078,432
field-steps, max 1.7e-12 mm); fresh files byte-exact.
CAPTURE SEASON DONE (0042b81b declared; reports/CAPTURE_SEASON_20261114.md): pre-sowing /
in-crop canal / both, 24 runs, 8 exact archived controls. Nile +3-6 points with both; Meso
2.5->3.5% (H), 0.7->1.0% (PM) max. No season inflates Mesopotamia.
BASE FLOW DONE (5a718dc8 declared; reports/BASE_FLOW_20261114.md): source = flood excess or 10/25/50%
of TOTAL monthly flow, capture both windows, 32 runs (8 exact controls). Meso root water up to 18-29%
at 50%; Nile saturates first. Nile/Meso fully-watered-equivalent area: flood-only 8.5-21.7x,
10-25% total 1.7-3.4x, 50% 1.3-2.2x; historical pop ratio ~2.3-7.1 (orientation only, post-hoc).
WATER-TO-FOOD TEST DONE (d497bc38 declared; reports/WATER_TO_FOOD_20261114.md): people = root share x
candidate area x model full-water barley energy (1 t/ha) x arable x 0.6 farmed x sown / 1.1M. Pass rule
Egypt >= 3.6 M and Meso <= 2.5 M: 0/32 pass. Meso not inflated 30/32. Egypt CEILING with every field fully
watered: 2.12 M (fallow) / 3.53 M (annual). Egypt is now limited by three rain-fed constants (1 t/ha yield,
0.6 farmed share, 0.6 fallow), NOT water. Papyri hints: tax ~8.3 art/aroura, rents up to 15 (~1.6 t/ha).
NEXT: a declared floodplain-land rule (yield, farmed share, cropping frequency) in the crop model, tested
on regions other than Egypt; do not tune it to Egypt.
FLOODPLAIN EVIDENCE GATHERED (calibration/floodplain_constants_20261114/sources.json, groundwork only): Egypt
basin land one crop/yr (EB1911/Willcocks); Egypt c.1911 cultivated ~2.33 M ha vs HAND candidates 2.46 M ha
(~0.95, upper bound for antiquity); Mesopotamian alternate-year fallow (weak sources); Roman Egypt rent
bounds ~1.6 t/ha. Arithmetic with these constants already known informally -> any test on Egypt/Meso is
development. OWNER DECISION PENDING: floodplain constants change harvests on every map river.
Restore pinned gauge pages with scripts/fetch_flood_gauges.py logic (hit/aswan) and tigris_gauge.fetch().

# Matched meteorology and 32 paired water maps complete — 14 November 2026

Canonical branch: `claude/friendly-turing-43ygeu`. Continued through paid
groundwater, local source qualification and matched weather without pausing at
pushes. Input declaration `df1e174c` / reviewed freeze `6e720369`; field declaration
`1189eb46` preceded new scores. Report: `reports/MATCHED_REGIONAL_FIELDS_20261114.md`.
Normal page: `atlases/earth_evidence/matched_weather/`. This is the latest field
water update. No harvest, population or settlement change is adopted.

Results for Nile capture, five-bin / fractional four-bin root-demand coverage:
PM 52.437 / 66.149% → 53.930 / 67.850%; Hargreaves 68.273 / 80.820% →
70.827 / 81.521%. Euphrates-only PM 0.889 / 1.176% → 0.674 / 0.728%; Hargreaves
2.799 / 3.612% → 2.524 / 2.604%. All 32 cases retained: two regions × two calendars
× capture/control × two reference methods × two meteorological policies. No
winner/calendar selected. Tigris absent. Root coverage is not total-crop ET,
Ky yield, grain, cultivated area or residents. All candidates remain eligible.

Inputs: same 30 samples / all 1,507 assignments, 54,810 complete 2020–2024 LST
dates. All 438,480 overlapping weather values, units and provider geometries
exactly match the old ETo input; reuse reviewed HAR/PM. New rainfall and T2M share
the packet/period. Conserve Gregorian monthly/yearly rain and both leap days.
Temperature: mean within each year/month, then equal-average five years; do not
scale Celsius by month length. Daily extremes/interannual variance are absent.
Annual rain: Nile 38.454 → 110.046 mm; Euphrates 139.958 → 157.692 mm. Historical
river means remain Aswan 1871–1901 / selected Hit 1965–1971, different epochs.

Verified: independent input raw/50-digit Decimal/scalar assignment/CSV checks;
four fresh files exact. Independent scalar field review: 9,114,336 final-cycle
field-steps, 24,112 CSV rows, all annual/monthly/daily arrays, 16 exact archived
controls. All 32 periodic: 31 in two cycles; matched Nile five-bin rain-only in
16. Unchanged 1e-6 mm / 50-cycle rule. Maximum annual-field difference 5.69e-12 mm,
scalar daily residual 1.33e-13 mm, annual joint residual 1.91e-5 m³. Three fresh
field files exact; 952 protected files unchanged. Six browser width/theme cases,
32 numerical rows, 54 filters, 14 downloads, 31 source ZIP members, actual CSV,
images/keyboard/width/navigation and staged Windows/release proof retained.

First next: source-qualify LOCAL crop phenology, stage lengths/thermal time,
basal demand and canopy/root development before declaring regional stage curves.
Generic stage component/source envelopes are already verified; do not redo them.
Keep consistent soil/retention/depletion/drainage and basal diffusion versus soil
evaporation explicit. Regional groundwater remains disabled: the local-source
audit below lacks consistent inputs. No free flux or rate/depth fit to Egypt.
Some observed tables lie inside the supplied 1.5 m root profile: a future local
model needs consistent saturated/unsaturated roots and oxygen/drainage handling.
Historical flow compatibility, shared fantasy weather/river, Tigris, independent
regions and frozen harvest/whole-empire checks remain open. Root uptake cannot
directly replace total-crop ET in the legacy Ky relationship.

Reproduce:

```sh
.venv/bin/python scripts/matched_regional_fields.py --workers 4
.venv/bin/python scripts/matched_regional_fields.py --out output/matched_regional_fields_20261114/fresh --workers 4
.venv/bin/python scripts/review_matched_regional_fields.py
.venv/bin/python scripts/publish_matched_regional_fields.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_matched_weather_browser.py
```

Browser uses localhost:8766. Force-add primary NPZs; fresh/screenshots ignored.
Weather preflight commands are in the next entry. Default release 3 / marketed
share 0.3923 stays: 850 self-fed / 174 importers / 29 short, 91% fed; reach staffing
1042. Egypt calibration, S3–S5, empirical occupancy/provider/size, complete
resources/diets/work, mobile actors and political authority remain open. Earlier
entries are history; this entry controls next work. Commits are checkpoints.

# MATCHED REGIONAL METEOROLOGICAL INPUTS VERIFIED — 14 November 2026

Continued beyond source-auditc315ac23. Declarationdf1e174c preceded new rainfall
capture and common-period meteorological arrays. Report:
reports/MATCHED_REGIONAL_WEATHER_20261114.md. No NEW field score at this checkpoint.

All30samples/54810dates complete;all438480overlapping weather values,units and
provider geometries EXACTLY match the previous audited ETo inputs. Reuse reviewed
HAR/PM;new PRECTOTCORR rain and same-packet T2M. Rain:sum Gregorian month/year,
average five totals,conserve annual amount including both leap days. Temperature:
mean each year/month then equally average five means;do NOT scale degreesC by
month length. Same1507assignments/no candidate removal. Monthly means omit
daily/interannual thermal variation. Whole source/weather/input set tracked.

Independent raw/50digitDecimal/scalar assignment/CSV/full-array checks pass;
360bins/36168mapped T/P cells,four fresh files exact,947protected unchanged.
Area-weighted annual rain: Nile38.454→110.046mm,Euph139.958→157.692mm. Not a local
precipitation accuracy result. Aswan1871–1901/selectedHit1965–1971flow epochs
remain different;modern5yearweather is not a historical reconstruction.

FIRST NEXT: DECLARE paired field comparison before outputs. Matched T/P/ETo
versus prior ETo-only HAR/PM,each2regions×2calendars×2capture/control;all32cases
retained. Keep all candidates as consumers,recompute thermal eligibility only
from declared T choice;fix root/soil/pond/routing/crop assumptions and gauge
volumes. Exact16archived controls,independent full scalar field/CSV/fresh checks.
Groundwater remains disabled:local source audit below leaves inputs unqualified.
No yield/settlement adoption;Tigris/shared flow,independent regions and frozen
harvest remain required. Default release3/marketed share0.3923 unchanged;
Egypt calibration fails. Full S3–S5/resources/work/authority queue remains open.

REPRODUCE: scripts/capture_matched_regional_weather.py; then venvPython
scripts/matched_regional_weather.py; same --out
output/matched_regional_weather_20261114/fresh; scripts/review_matched_regional_weather.py.
Primary forcing.npz must be force-added;fresh ignored. Earlier entries are history.

# LOCAL NILE GROUNDWATER SOURCE QUALIFICATION COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued beyond paid-budget
checkpoint5ca4ae91. Declaration5b3b3af6 preceded source extraction/arithmetic;
abstract/snippet results already exposed and explicitly known development.
Report: reports/NILE_GROUNDWATER_SOURCES_20261114.md. No new fields or adoption.

RETAINED: Amer2019 Table3 printed89/PDF11:40measured water-table depths plus
40EMPIRICALLY FITTED m values,four modern cultivated Delta sites,ten months
November2014–August2015. Wheat/clover/maize/citrus differ;modern furrow irrigation.
Seasonal20–40% contribution and ETa are modeled,not measured capillary flux.
Sakha2023 DOI10.1007/s40333-023-0095-3:three soil layers and all four Table2
inferred seasonal uptake/percentage rows. Real drains1.2m;0.4/0.8m are weir/outlet
elevations,not drain burial depths or fixed observed water tables. One field per
drainage treatment;cultivar replicates within each field. Modern wheat/fertilizer.

FOUND: captured HTML/XML Table2 middle percentages conflict with prose;all four
percentage cells fail uptake/stated actualET arithmetic beyond printed rounding.
Keep cells exactly as source. All-treatment ET is assumed from free-drainage
control and groundwater is inferred residual,not independent measured flux.
Methods give FC39.98%/WP21.70% but no explicit basis/layer assignment there;
TDR monitors field moisture. No invented volumetric/gravimetric storage or root
depth. Equation3 also describes ΔS as moisture% beside mm water depths without
the conversion there. PDF routes returned HTML/errors;finding concerns captured
HTML/XML,not an inspected printed PDF. Do not resolve by silently swapping cells.

VERIFIED: independent PDFplumber geometry vs pdftotext checks80PDFcells;
stdlib HTMLParser/ElementTree vs lxml checks selected tables/24soil numeric
cells;50digitDecimal checks all four discrepancies. Four fresh exports byteexact;
942protected files unchanged,including paid-budget results/controls/review.
Journal HTML/XML tracked under data/source/nile_groundwater_sources_20261114/
(live HTML tokens change);AmerPDF cached/restorable by pinned mirror SHA.

FIRST NEXT: local seasonal groundwater remains DISABLED in regional fields.
Both sources lack a complete consistent soil/root/hydraulic and finite boundary
set;do not keep cycling generic rates/depths toward Egypt's score. Pursue matched
meteorology/period/grid and qualified crop phenology/canopy next while seeking
the missing local retention/FC-WP basis,full root/water-table/irrigation/drainage
series,accessible aquifer specific yield/recharge and salinity/oxygen/transient
constraints. Inspect another primary PDF version before treating the digital
table discrepancy as a printed-paper error. No Dutch O8 graft/free groundwater.

REPRODUCE with SYSTEM python: scripts/nile_groundwater_sources.py; same producer
--out output/nile_groundwater_sources_20261114/fresh; then
scripts/review_nile_groundwater_sources.py. lxml/pdfplumber and pdftotext needed.
Plan/URLs/hashes:calibration/nile_groundwater_sources_20261114/. Fresh ignored.

Latest field update remains regional water maps,24cases/all1507candidates;NilePM
root coverage52.4/66.1% versus archived65.3/79.0%. Root uptake is not totalET/Ky
yield. Default release3/marketed share0.3923:850self-fed/174imports/29short,91%fed;
reach staffing1042. Egypt calibration,shared fantasy flow,Tigris,independent
regions,frozen harvest,S3–S5,empirical occupancy/provider/size,complete resources/
diets/work,mobile actors and political authority remain open. Commits/pushes are
checkpoints. Earlier entries below are history;this entry controls next work.

# FINITE PAID GROUNDWATER ACCOUNTING COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Declarations6e7490d2 and2a072eb8
preceded implementation and fixed synthetic outputs respectively. Report:
reports/PAID_GROUNDWATER_20261114.md. Normal page:
atlases/earth_evidence/groundwater_budget/. Continue beyond commit/push checkpoints.

IMPLEMENTED: harvest/groundwater_fields.py wraps unchanged field kernel one
actual step at a time. Five stocks: top/deep available, surface below-WP, pond
and accessible aquifer above a supplied floor. Empty defaults; bounded supplied
starts. Loss then permission/stock/deficit-limited upward transfer, deep→bound→top;
then previous-pond-only recharge. Recharge and soil infiltration share ONE
allowance. Fresh delivery cannot recharge until next step. Percolation/overflow/
pond release do not return or receive duplicate credit. All five periodic stocks
must converge. Permissions/capacities supplied; no water-table inference.

VERIFIED:223controls;100synthetic forests/4680field-steps/105552history values
independently replayed;max difference1.60e-13. Ten zero-groundwater cases reproduce
EVERY original array exactly. Three empty-start demos,180CSVrows and five-stock
periodic states checked;three fresh files byteexact,937protected files unchanged.
Synthetic40mmstorage costs40m³extra river delivery per1000m²;root uptake
105.416→119.140mm of120mm potential. Stored/no-permission adds no uptake;finite
stock empties. No Earth groundwater field, harvest or settlement adoption.

FIRST NEXT: recover/qualify local soil/hydraulic profiles, seasonal water-table
history, root suction/development, recharge and drainage. Separate measurements
from model-derived fluxes; modern managed plots are not ancient basin defaults.
Do not graft Dutch O8 onto the synthetic soil, infer winter from summer depths,
or select rates/capacities to close Egypt's gap. Declare consistent soil/root/
hydraulic inputs and finite supplies before regional groundwater experiments.
Retain high-water-table oxygen/salinity/transient constraints, forcing period/
grid, shared fantasy weather/river qualification, Tigris and independent regions.
Root uptake cannot replace total-crop ET in legacy Ky without a consistent rule.

REPRODUCE: scripts/paid_groundwater_benchmarks.py; same producer --out
output/paid_groundwater_20261114/fresh; scripts/review_paid_groundwater.py;
scripts/publish_paid_groundwater.py; scripts/build_fit_hub.py --date 2026-11-14.
System Python scripts/check_groundwater_browser.py uses localhost:8766. Canonical
controls runtime receipt pinned separately; fresh reuses it. Force-add primary
synthetic.npz; fresh and screenshots ignored. Browser/Windows receipts retained.

Regional water maps remain latest field update,24cases/all1507candidates.
Nile PM root coverage52.4/66.1% versus archived65.3/79.0%, conditional diagnostics.
Default release3/marketed share0.3923 stays:850self-fed/174imports/29short,91%fed;
reach staffing1042. Egypt calibration, S3–S5, empirical occupancy/provider/size,
complete resources/diets/work, mobile actors and political authority remain open.
Earlier entries below are history; this entry controls the next dependency.

# CAPILLARY HYDRAULIC SOURCE/COMPONENT CHECKS COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued beyond regional maps
074363c0; declaration 3ce2c453 preceded component code/outputs. Full report:
reports/CAPILLARY_HYDRAULICS_20261114.md. Normal page:
atlases/earth_evidence/capillary/. No extra water, field or settlement adoption.

IMPLEMENTED: harvest/capillary_hydraulics.py, supplied Van Genuchten retention/
conductivity and FAO midpoint stationary profile. Suction magnitude cm; height
positive above water table; conductivity cm/day, upward prescribed flux mm/day
converted once. Stable log/Se form; zero flux exactly hydrostatic. This relation
creates no water and is not an aquifer or a field supply model.

VERIFIED: 208 controls (26 new). Two source table parses agree on 28 Dutch
hydraulic profiles and all 41x6 source profile heights. O8 supplied silty-soil
example reproduces all 246 heights within published rounding, with no tuning.
Independent 50-digit Decimal DIRECT source-equation powers/signed-head recurrence
checks 896 hydraulic sample cells and all profile cells; max numeric errors
5.18e-14 in retained units / 1.04e-13 cm. Three fresh numeric exports exact;
932 protected files unchanged, including all regional forcing/field outputs.
Six browser viewport/theme cases, 34 exact rows, seven downloads, actual CSV,
image/keyboard/width/navigation, staged Windows checkout and release proof.

HISTORICAL CONTEXT: recovered official Butzer1976 PDF (current ISAC link points
to a versioned S3 asset; old .pdf URL returned HTML and was not accepted).
Printed p19/PDF35 concerns Omo/Senegal/Chari-Logone analogies, not measured Roman
Nile flux. Printed p90/PDF106 has SUMMER water table at least3–4m, not winter
depth. Butzer1984p105 post-flood high water table is qualitative. FAO56's
approximate1m-below-root convention is distinct from soil-specific FAO61 curves.
No Dutch profile, universal rate, larger root TAW or free groundwater inferred.

FIRST NEXT: declare finite PAID groundwater recharge/storage and its transfer
to the same existing soil/river ledger. Empty initial stocks, explicit accessible
floor/capacity/areas/time units; recharge consumes paid river/rain water; upward
transfer limited by hydraulic permission AND stored stock. No double-credit of
percolation or instant downstream reuse; preserve zero-groundwater/legacy and
all-candidate controls. Local water-table history, storage/soil hydraulic profile,
root suction/development, canopy/drainage and transient/high-water-table crop
constraints remain unqualified. Do not graft Dutch O8 onto the old synthetic
field soil or choose rates/depths to make Egypt pass. Regional forcing-period/
grid consistency and shared fantasy weather inputs remain open. Then Tigris,
independent regions, frozen harvest and whole-empire supply checks.

REPRODUCE: scripts/capillary_source_benchmarks.py; same producer --out
output/capillary_hydraulics_20261114/fresh; scripts/review_capillary_hydraulics.py;
scripts/publish_capillary_hydraulics.py; scripts/build_fit_hub.py --date 2026-11-14.
System Python scripts/check_capillary_browser.py uses localhost:8766. Source
caches restore with pinned hashes; pdftotext required for historical context.
Canonical controls.json holds test-runtime text and is pinned by reference.json;
fresh exports reuse that receipt. Regenerating canonical producer intentionally
requires its downstream review/publication refresh. All source locators/digests
are in calibration/capillary_hydraulics_20261114/plan.json. PDFs stay cached.

Regional water maps remain the latest field update: 24 paired cases, all1507
candidates, exact archived controls; Nile PM root coverage52.4/66.1% versus
archived65.3/79.0%. These are conditional water diagnostics, not crop yields or
residents. Default settlements remain release3/marketed share0.3923:850self-fed,
174imports,29short,91%fed;reach staffing1042. Egypt calibration, S3–S5, empirical
occupancy/provider/size, complete resources/diets/work, mobile actors and
political authority remain open. Full programme live queue/review log updated.
Earlier entries below are history; this entry controls the next dependency.

# REGIONAL FORCING AND PAIRED FIELD-WATER MAPS COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued from e6e0f920.
Declaration 6366d34d preceded regional weather and field outputs; 7a645ea7 froze
30 raw sources/preflight; dadf8859 froze independently reviewed regional forcing
before field scores. Full report: reports/REGIONAL_REFERENCE_FORCING_20261114.md.
Normal page: atlases/earth_evidence/regional_forcing/. New water-diagnostic maps;
no harvest, resident or settlement adoption. Commits/pushes remain checkpoints.

RESULT: Nile capture root-demand coverage for five-bin/fractional four-bin crops:
archived 65.33% / 79.00%; regional Hargreaves 68.27% / 80.82%; regional PM
52.44% / 66.15%. Euphrates-only five/four-bin coverage: archived 3.69% / 4.76%;
regional Hargreaves 2.80% / 3.61%; PM 0.89% / 1.18%, unchanged by capture in these
members. All 24 outcomes retained. Not old total-crop ET, grain, irrigated area
or residents. No winner or season selected; Egypt calibration still fails.

FULL COVERAGE: 1,507 fields assigned to 30 fixed one-degree tile centres before
weather capture, 15 samples per region. 54,810 complete 2020–2024 NASA gridded
weather dates, not station/ancient measurements. Raw sources/URLs/units/grid
metadata/hashes: data/source/regional_reference_forcing_20261114/. Source ZIP
and all numeric files ship with the normal page. Mean/max field-sample distance:
Nile 41.10/67.78 km; Euphrates-only 39.01/67.21 km. Sampling completeness is not
local representativeness or a claim of one-degree native resolution.

POLICY: only ETo changes among legacy_archive, power_hargreaves and
power_penman_monteith. Crops, soils, calendars, WorldClim T/P, thermal eligibility,
all candidate consumers and gauge volumes stay fixed. Five-year mean Gregorian
month totals map conservatively into equal model bins, retaining leap-day amounts.
Modern POWER2020–24 ETo with WorldClim1970–2000 T/P is a declared forcing-only
sensitivity, not a consistent climate reconstruction. Hargreaves/PM share weather,
geometry and assignment; legacy/regional also changes source/period/aggregation.
No point multipliers, local soil fit or crop climate adjustment applied.

SHARED ADAPTER: harvest/reference_forcing.py receives supplied world radiation
and all near-surface weather, with no Earth geometry/default weather invented.
FAO empirical assumptions/time units still need qualification for another world.
Old fantasy harvest adapter exports Tm/Pm, geometry and learned DTR; it does not
supply all vapour/2m wind/solar inputs. Shared algebra is tested; a qualified
fantasy weather connection and shared Earth/fantasy river flow remain open.

VERIFIED: 182 controls; 17,000 scalar/Decimal world-radiation cells and 3,600 bin
cells before outputs. Independent weather review reconstructs 931,770 computed
cells and all 1,507 assignments. Independent field kernel replays 6,835,752
final-cycle field-steps, annual field states/fluxes, monthly ledgers, daily basin
stocks and 18,084 CSV rows. Full daily field trajectories are not exported.
All 24 cases reach periodic stocks in two cycles. Eight legacy cases exactly
match archived arrays; seven fresh numeric files byte-identical; 923 protected
files unchanged. Max annual field difference 3.64e-12 mm; scalar daily mass
residual 1.35e-13 mm. Six browser viewport/theme cases, 26 exact rows, 162 filters,
14 download hashes, 31 raw ZIP members, real field CSV, image/keyboard/width/
navigation checks; staged Windows checkout/release proof retained.

FIRST NEXT: source-check post-flood crop support: local phenology, soil/root
and canopy/basal diffusion, especially the documented high water table and
capillary support. Any groundwater extension must pay for recharge from the
same finite river/field ledger and retain finite storage; no unlimited inflow
or depth/rate chosen to close Egypt. Source recovery is starting in ignored
cache data/cache/recession_groundwater_20261114/. No new groundwater model or
regional outputs declared yet. Period/grid consistency still requires review
before ETo adoption; do not apply point ratios. Add Tigris and independent
regions, freeze harvest translation, then Nile gain AND Mesopotamian
non-inflation and whole-empire supply checks. Pond/access/drainage remain open.

REPRODUCE: scripts/regional_reference_weather.py; same --out
output/regional_reference_forcing_20261114/fresh; review_regional_reference_weather.py.
Then regional_reference_fields.py (canonical reviewed forcing, four workers),
same --out .../fresh; review_regional_reference_fields.py;
publish_regional_reference_forcing.py; build_fit_hub.py --date 2026-11-14.
System Python check_regional_reference_browser.py uses localhost:8766. Source
capture reuses frozen files. Core-only reruns: audit_reference_forcing.py --out
output/regional_reference_forcing_20261114/core/fresh; do not overwrite pinned
canonical core receipt without rebuilding downstream provenance. See full report.

Atlas remains release 3 / marketed share 0.3923: 850 self-fed, 174 importers,
29 short, 91% fed; reach staffing 1042. S3–S5, dated occupancy/provider/size,
complete resources/diets/work, mobile actors and political authority remain
open. Whole-plan live queue/review log updated. Earlier entries are history;
this entry controls the next dependency.

# MATCHED-WEATHER REFERENCE EVAPORATION AUDIT COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued from 60e60c3d.
Protocol 4d93e88b preceded weather capture and site model outputs; 15010e41
froze raw weather and preflight before site results. Full report:
reports/REFERENCE_ETO_20261114.md. Normal page:
atlases/earth_evidence/reference_eto/. No field, harvest or settlement adoption.

FINDING: on identical 2020–2024 NASA POWER daily gridded weather, Hargreaves /
FAO56 Penman–Monteith annual ratios are 0.8077 Cairo / 0.6986 Aswan / 0.7180 Hit.
PM mean annual totals are 2160.3 / 3043.8 / 2381.0 mm; daily Hargreaves gives
1744.8 / 2126.5 / 1709.6 mm. November–March ratios 0.8387 / 0.7116 / 0.7713
are Gregorian-month diagnostics, not the supplied field crop calendars. This
is a method comparison, not measured ETo error, ancient weather or regional
harvest validation. No winner or multiplier adopted.

IMPLEMENTED: harvest/reference_eto.py, daily FAO solar geometry, pressure/wind/
radiation and grass-reference PM, plus matched daily Hargreaves. Supplied 2 m
wind/pressure, dewpoint-derived vapour pressure, albedo 0.23 and G=0; explicit
cloud-ratio bound 0.3–1 (213 days; all raw ratios retained), raw signed ETo and
zero bound (no negative raw ETo in weather rows). Atlas-style monthly comparison
reuses unchanged land_people functions on the same modern monthly weather;
aggregation and solar-geometry effects are separated. Legacy geometry omits
Earth–Sun distance and uses equal-bin/cosine seasonal conventions; unchanged.

INPUTS: all 5,481 requested dates are present and valid at the three declared
coordinates, 2020–2024 local solar time. Full raw NASA JSON, URLs, units, headers,
grid elevations and raw/semantic digests: data/source/reference_eto_20261114/.
Model/satellite grids, not station observations. Provider solar units are
MJ/m²/day (conversion factor 1). Daily mean RH2M is not minimum RH for FAO crop
Equation 70; no field coefficient adjustment inferred. The frozen plan's
Equation 52 chapter locator was a bibliographic error: actual Chapter 3,
corrected in results metadata. Both sources were pinned before capture; no
numerical rule changed.

VERIFIED: 159 controls (22 new), FAO18 rounded 3.9 mm/day, FAO8 radiation 32.2
and 1,000 synthetic days / 18,000 scalar-Decimal cells BEFORE site ETo. The
independent weather reviewer checks raw parsing, QA/units, all 98,658 computed
daily cells, 180 site-year-month rows, 15 annual rows, 36 climatologies and
legacy geometry. Maximum PM difference 1.43e-14 mm/day; fresh results.json and
daily.csv byte-identical; 920 protected files unchanged. Browser: 39 displayed
rows, six viewport/theme cases, 312 filters, ten download hashes, actual daily
CSV, keyboard/width/images/navigation. Staged Windows checkout and release
check retained under output/reference_eto_20261114/.

FIRST NEXT: declare a regional reference-forcing policy before new field scores.
Qualify spatial/period representativeness and humidity, wind and solar inputs,
with matched legacy-forcing controls and the shared Earth/fantasy adapter in
view. Do not multiply all fields by these point ratios or choose a crop calendar
to make Egypt pass. Earlier water adequacy remains conditional on its forcing.
Local phenology, basal diffusion versus root uptake, canopy/root development,
pond access/infiltration/drainage, Tigris and independent regions remain open.
Freeze harvest translation before Nile gain AND Mesopotamian non-inflation and
whole-empire supply checks. No harvest direction inferred from ETo ratios alone.

REPRODUCE: scripts/reference_eto_weather.py, same producer with --out
output/reference_eto_20261114/fresh, scripts/review_reference_eto_weather.py,
scripts/publish_reference_eto.py, then scripts/build_fit_hub.py --date 2026-11-14.
System Python runs scripts/check_reference_eto_browser.py on localhost:8766.
Tracked weather responses are reused; capture_reference_eto_sources.py verifies
them. For core-only checks use audit_reference_eto.py --out
output/reference_eto_20261114/core/fresh; overwriting canonical core/review.json
requires regenerating pinned weather provenance. See report for full sequence.

Current atlas: release 3, marketed share 0.3923; 850 self-fed, 174 importers,
29 short, 91% fed; reach staffing 1042. Egypt calibration, S3–S5, empirical
occupancy/provider/size evidence, complete resources/diets/work, mobile actors
and political authority remain open. Whole-plan live queue and review log
updated. Earlier entries below are history; this entry controls the next step.

# CROP-STAGE SOURCE AND COMPONENT CHECKS COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Fetched latest remote handoff
3e649793; its completed rain experiment superseded the overlapping local draft,
which is preserved in a Git stash. Declaration e470de0a preceded this component
code and outputs. Report: reports/CROP_STAGE_20261114.md. Normal page:
atlases/earth_evidence/crop_stage/. No new Earth field or harvest scores.

IMPLEMENTED: harvest/crop_stage.py, a supplied four-stage StageCurve with point
values, exact interval integrals and actual-duration means. Positive stage
lengths, nonnegative coefficients, bounded crop-age domain; initial/mid constant,
development/late linear. No inferred local phenology or adopted cereal curve.
FAO56 Example30 (dry beans) reproduces all four printed values, exact integral
67.975 coefficient-days and mean0.67975. This is a published arithmetic check.

SOURCE FINDING: Table17 barley Kcb0.15/1.10/0.15, with initial inherited from
cereal heading. Wheat initial/end alternatives retain footnotes and context;
Table11 exports11 stage-duration rows with original planting/region labels,
not a Nile barley calendar. Tables assume RHmin45%/wind2m/s; Equation70 adjusts
mid/end>0.45 outside reference conditions. Kcb includes residual below-surface
soil diffusion: substituting it as pure root transpiration is NOT qualified.
See source facts/claims in output/crop_stage_20261114/reference.json.

VERIFIED: 137 controls (20 new); two source table parses, four published point
checks, independent Decimal review of277 exported intervals and4000 intervals
on100 synthetic curves. Two fresh numeric files byte-exact;917 protected files
unchanged, including prior daily/rain outputs. Six browser viewport/theme cases,
18 exact source/benchmark rows, five download hashes and actual CSV download,
keyboard/width/images/navigation; staged Windows checkout/release check retained.

FIRST NEXT: qualify local crop phenology and ETo/climatic adjustment; declare
basal diffusion versus root uptake, stage canopy exposure/root development and
inundation/drainage treatment BEFORE an Earth stage-curve comparison. Do not
scale generic stage ratios or select location examples because they improve
Egypt. Rain timing has only a small effect in the32 declared cases (eight fixed
illustrations); it does not settle all rain scenarios. Tigris/shared Earth-fantasy
flow and independent regions remain open. Freeze harvest translation before
Nile gain AND Mesopotamian non-inflation and whole-empire supply checks.

REPRODUCE: scripts/crop_stage_benchmarks.py, same producer --out
output/crop_stage_20261114/fresh, scripts/review_crop_stage.py,
scripts/publish_crop_stage.py, scripts/build_fit_hub.py --date 2026-11-14.
System Python runs scripts/check_crop_stage_browser.py against localhost:8766.
Raw FAO sources restore with pinned digests into data/cache/crop_stage_20261114;
the prior Chapter7 cache is reused. HTTP browser user-agent required here.
New publisher is hooked into the normal evidence build. Fresh numeric copies
and browser screenshots are ignored. See report for the exact command sequence.

Atlas remains release3, marketed share0.3923;850self-fed/174imports/29short,
91%fed;reach staffing1042. Whole-empire Egypt calibration, S3–S5, empirical
occupancy/providers/size, complete resources/diets/work, mobile actors and
political authority remain unresolved. Whole-programme roadmap reviewed and
updated. Earlier entries below are history; this entry controls next steps.

# RAIN-TIMING SENSITIVITY COMPLETE — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu (claude/wonderful-mayer-uqbwtb is kept at the
same commit). Continued from e045ab5a, whose declaration
calibration/rain_timing_20261114/plan.json preceded all timing code and outputs.
Full report: reports/RAIN_TIMING_20261114.md. Normal page: atlases/earth_evidence/rain_timing/.

RESULT: on the eight mapped illustrations, delivering each field's monthly rain as 1, 2 or 4
one-day events instead of uniformly changes root-water coverage by at most 0.76 percentage
points (Euphrates-only), at most 0.19 on the Nile with capture (65.3% / 79.0% unchanged).
Not monotone in event count. Uniform within-bin rain is NOT what limits the Nile result.
No pattern preferred; nothing adopted. Development only.

IMPLEMENTED: harvest/rain_timing.py (event windows, common-clock edges, conserved per-step
rain). scripts/rain_timing_fields.py runs the PINNED daily_river_fields.run_case with only the
clock and rain array replaced (the pinned producer, reviewer and coupling are unmodified;
their hashes are asserted). One common clock per calendar holds every event edge.

VERIFIED: 12 preflight controls committed before Earth output (tests/test_rain_timing.py).
Independent review rebuilds pulse rain with plain loops and reuses the reviewed scalar
reference from review_daily_river_fields.py via two declared text substitutions (per-step
rain); 13,165,152 field-steps, max annual field difference 1.6e-12 mm, fresh files
byte-identical, all protected files unchanged. Clock control: uniform on the common clock
matches archived original-clock coverage within 0.021 points (annual field fluxes differ up
to 10 mm in capture cases: operator step-size effect, reported separately). Page checks:
four viewport/theme cases, 32 rows, filters, five download hashes, hub/evidence links.
Staged Windows-style checkout check and release verification pass.

ENVIRONMENT NOTE: this container has Node Playwright only, so the page check is
scripts/check_rain_timing_browser.js (python3 -m http.server 8766), not a Python runner.
Hooked into scripts/publish_earth_evidence.py and the hub link list in build_fit_hub.py.

FIRST NEXT: rain timing can be set aside. Remaining candidates for the Nile shortfall, as the
daily-coupling entry lists: soil/root development, stage basal crop coefficients, bare
diffusion, pond/infiltration/access/drainage and local dates. Declare the next sensitivity
before scores; do not tune to make Egypt pass. Then Tigris and independent regions, shared
Earth/fantasy flow, freeze the harvest translation, and test Nile gain AND Mesopotamian
non-inflation before the whole-empire supply calibration.

Current atlas unchanged: release 3, marketed share 0.3923; 850 self-fed, 174 importers,
29 short, 91% fed; reach staffing 1042. Earlier entries below are history.

# DAILY RIVER-TO-FIELD COUPLING REVIEWED — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued from 31b87d48.
Declarations 30726ae4 (operator/grid) and e4e26b46 (candidate-area policy)
preceded the new Earth outputs. This is exposed development, not independent
regional validation. Full report: reports/DAILY_RIVER_FIELDS_20261114.md.
Normal page: atlases/earth_evidence/daily_fields/ (new water maps, all 256 rows).

IMPLEMENTED: harvest/river_fields.py couples upstream conserved river withdrawal,
area-weighted useful delivery/losses, finite infiltration/ponds, surface drying,
deep bare diffusion and root uptake on the exact supplied fractional clock.
Three soil stocks plus pond carry through zero-initialized periodic spin-up;
all 256 cases converge in 2–12 cycles. Full FAO31 bare total ET is now paid:
background diffusion spends deep water separately, with zero crop uptake.
Whole-step pond shielding and bounded post-depletion diffusion remain explicit
approximations. No groundwater/return-flow credit. Every candidate remains a
water consumer even if thermally crop-ineligible. Rain-only controls matched.

VERIFIED: 105 controls; independent core scalar comparison on 100 forests /
7,532 joint steps, max history difference 1.14e-13 mm. Independent Earth scalar
replay reconstructs 72,914,688 final-cycle field-steps and spin-up convergence;
compares annual per-field states/fluxes, monthly basin ledgers, daily basin
stocks, eligibility and all 192,896 CSV rows. Full daily field trajectories are
not exported/directly compared. Max annual field difference 4.89e-12 mm; three
fresh numeric files byte-identical. All 910 protected files unchanged, including
904 Earth-fit assets and old 96-case/component numeric outputs. Browser checks:
all 256 rows, six viewport/theme cases, 162 filters, nine downloads and navigation;
staged Windows checkout/release check retained alongside other receipts.

DEVELOPMENT FINDING: fixed illustrated barley/1.5 m roots (TAW 225 mm), bare
coefficient 0.15, pond 200 mm, efficiency 1 gives Nile root-demand coverage
65.3% (five-bin crop) / 79.0% (four-bin fractional crop), versus rain-only
0.46% / 0.58%. Euphrates-only 3.69% / 4.76%, unchanged by capture in that member.
These are ROOT transpiration diagnostics, NOT earlier total-crop ET coverage,
grain yield, historical irrigation or residents. No preferred case adopted.

FIRST NEXT: declare a volume-preserving rainfall-timing sensitivity before
new scores. Uniform within-bin monthly rain can continually evaporate from the
surface instead of infiltrating like storms; timing must not be tuned to make
Egypt pass. Qualify local rain events, soil/root development, stage basal crop
coefficients, bare diffusion, pond/infiltration/access/drainage and local dates.
The legacy kc is only a supplied constant root-demand coefficient here, not a
qualified basal curve or the old yield model. One ideal river pool per region;
Mesopotamia still omits Tigris. Add Tigris/shared Earth-fantasy flow and independent
regions, freeze harvest translation, then test Nile gain AND Mesopotamian
non-inflation before whole-empire supply calibration. Do not reimplement the
completed daily coupling or infer a harvest rule from closure alone.

REPRODUCE: scripts/audit_river_fields.py (core before Earth),
scripts/daily_river_fields.py (about eight minutes per 256 cases, four workers),
then same producer --out output/daily_river_fields_20261114/fresh;
scripts/review_daily_river_fields.py, publish_daily_river_fields.py, and
build_fit_hub.py --date 2026-11-14. System Python runs
scripts/check_daily_river_fields_browser.py against localhost:8766.
For verification-only core reruns use --out output/daily_river_fields_20261114/core/fresh;
do not overwrite pinned canonical core/review.json without regenerating
Earth provenance. Main NPZ/CSV and core synthetic NPZ are tracked; fresh copies
and browser screenshots are ignored. The publisher is hooked into the normal
evidence build. See report for exact controls, artifacts and remaining limits.

Current atlas: release 3, adopted marketed share 0.3923; 850 self-fed,
174 importers, 29 short, 91% fed; reach staffing 1042. Whole-empire Egypt failure,
actual occupancy/provider evidence, S3–S5, complete resources/diets/work,
mobile actors and political authority remain unresolved. Roadmap live queue and
review log updated. Earlier entries below are history; this entry controls next steps.

# LAYERED SOIL AND EXACT SUPPLIED CLOCK VERIFIED — 14 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Continued from bf0804f0.
Component declaration ab8afa29 preceded implementation/model outputs; clock
amendment d0739f3f preceded calendar outputs. These are known published component
checks and synthetic tests, not blind regional validation or a local soil fit.

IMPLEMENTED: harvest/soil_drying.py separates top plant-available, deeper
plant-available and surface below-WP evaporable water. TEW and TAW overlap in the
top pool, which is stored once. Water refills explicit pools, pays drainage,
surface evaporation and root uptake. Roots cannot use below-WP water; bare
evaporation cannot directly spend the deep root store. Wetting order, drainage
before ET, evaporation priority and proportional root uptake are explicit
approximations. No pond, groundwater recharge, root growth or free refill.

harvest/field_clock.py splits supplied climate/event boundaries into <=1day
steps, conserves bin totals and repeats rates/state values without scaling.
The soil step receives actual segment duration. Example clock: 379 segments over
365 days, supplied capture 106.458333 days/crop 121.666667 days with no overlap.
These are mathematical phase windows, NOT qualified local dates or daily forcing.

VERIFIED: 90 controls (52 earlier + 23 soil + 15 clock); all 140 numeric daily cells in
FAO56 Examples31/37 match published rounding. Independent HTMLParser/40-digit
Decimal review plus scalar pools: 36,000 profile-days / 108,000 compartment checks,
daily/global closure and Decimal calendar integration. Max model daily balance
error ~1e-13 mm; all 3 fresh numeric files byte-exact. 904 Earth-fit assets AND the
3 numeric files for all 96 earlier Earth field cases remain byte-identical.
No Earth/crop-yield/population scores or default adoption in this stage.
Publication checks pass: six viewport/theme combinations, all 20 displayed
numeric rows and clock metrics, nine download hashes, actual CSV download,
keyboard/navigation, and a fresh Windows-style checkout with verified release.

Report reports/SOIL_DRYING_20261114.md; normal page
atlases/earth_evidence/soil_drying/. Source/benchmark producer:
scripts/soil_drying_benchmarks.py; independent reviewer review_soil_drying.py;
direct publisher publish_soil_drying.py, then build_fit_hub.py --date 2026-11-14.
Browser runner: system python
scripts/check_soil_drying_browser.py on localhost8766. Full numeric states/clock
NPZ and CSV are shipped in output and the normal page; raw FAO caches can be
restored by qualify_flood_storage_sources.py. Normal evidence publisher hook
runs after the earlier field-storage panel; no need to rerun its historical chain.

FIRST NEXT: declare and implement daily river-to-field coupling, with paid water
transfers, net-infiltration/area/volume units, within-bin forcing and pond/drainage
policy. Use the supplied clock without treating all fractional steps as days.
Qualify soil profiles, root development, crop/drainage dates and any groundwater
rate; add Tigris and independent regions and shared Earth/fantasy river flow
before new field/capacity claims. Component equations do not qualify the uptake
operator or a new harvest rule. Keep old96Earth results as development history.
The synthetic pure-bare Kcb=0 case omits deeper diffusive evaporation; do not
infer real indefinite deep-water retention or classify FAO31's basal bare ET
as crop uptake. A future adapter must declare and pay that flux separately.

Current atlas remains release3 with adopted marketed share0.3923:850self-fed,
174imports,29short,91%fed; reach staffing1042. Whole-empire Egypt failure,
actual occupancy, complete resources/work and political authority remain open.
Earlier entries below are chronological history; this entry controls next steps.

# FIXED-CALENDAR FIELD WATER MAPS REVIEWED — 14 November 2026

AFTER checkpoint e1d88d57, continued with primary-source qualification:
reports/FLOOD_STORAGE_SOURCE_QUALIFICATION_20261114.md. FAO56 Chapters7/8
separate a shallow evaporation layer from deeper root-zone water. Generic
Table19+22 envelopes reach300mm barley /360mm winter wheat; these are NOT Nile
soil measurements and do not qualify600mm for adoption. Both source-table parses
and Decimal/float arithmetic agree;18derived envelopes/fresh export byteexact.
scripts/qualify_flood_storage_sources.py reproduces source facts and hashes.
Butzer1984 p105 describes flooding through mid-November in the north and a high
post-flood water table; do not treat standing-water depth as root-zone TAW or
derive a universal exact Roman crop calendar from seasonal descriptions.

FIRST NEXT IMPLEMENTATION: declare surface-evaporation/root-zone separation,
depletion stress and explicit drainage, with an inundation/sowing clock. Validate
against FAO drying examples before new field outputs. Keep all water paid once,
including transfers/groundwater; do not change crop duration or operator order
to close Egypt's score. Local soils, Tigris, independent regions and shared
Earth/fantasy flow remain required. All96field results remain byte-identical.
Normal page now includes generic source constraints and9byte-checked downloads.
Build hub with scripts/build_fit_hub.py --date 2026-11-14; explicit publication date
avoids the UTC host displaying yesterday relative to the owner in Warsaw.

Canonical branch: claude/friendly-turing-43ygeu. Continued from 71f1f192.
Declaration 29b39784 preceded new climate extraction, storage runs and ET scores.
New report: reports/FLOOD_BASIN_STORAGE_20261114.md.
New normal evidence page: atlases/earth_evidence/flood_storage/.

Implemented harvest/flood_storage.py: finite field water, rain spill, pre-sowing
capture, shared-node proportional rationing, paid delivery losses, crop/bare ET,
carry between months and zero-stock periodic spin-up. Uses flood_water.py for
river withdrawals; every monthly source and field ledger closes. All 96 declared
region/crop/store/bare-ET/efficiency/capture combinations retained. Fixed November
five-month calendar on both rivers; no optimizer or tie-based season selection.

FINDING: Nile barley with bare ET=PET and efficiency1 has mean crop ET coverage
9.8%,70.0%,100% at100/300/600mm stores (rain-only9.7%). At600mm,efficiency0.5
reduces coverage to95.4%. With zero bare evaporation,300mm reaches95.0%.
These are UNCALIBRATED storage/evaporation scenarios,not measured root-zone
capacities or crop yields. Do not adopt600mm because it passes water adequacy.
Mesopotamia uses EUPHRATES ONLY; Tigris is absent. Bare ET=PET cases remain33.7%
water-covered with or without capture. This is NOT a complete regional budget
or proof of harvest non-inflation. Both regions remain development; Indus unscored.

Exact old terrain mask:8179Nile /21925Mesopotamian arc-minute candidates,area-
aggregated to489/1018five-minute climate fields. Constant-area totals reproduce
old24553.920/64003.538km². Actual row-latitude area is24497.044/63986.271km².
Whole terrain mask is treated as test fields; no farmed/fallow-area inference.
Optimistic shared river access,negativeHAND and noncontemporaneous climate/gauges
remain explicit limitations. Soil storage,groundwater,drainage/access unqualified.

VERIFIED: 52 combined controls (15 new storage), 96 periodic rows (all 2-year spinups),
72,336 field CSV rows, 868,032 monthly field balances. Independent dictionary terrain
aggregation,raw climate/PET/eligibility checks,scalar simulation from empty stock,
river/soil closure and3fresh numeric files byte-exact.6viewport/theme cases,
all96numeric rows and54filter combinations,real download hashes/navigation pass.
No default map/harvest parameter changed; all 904 Earth-fit files byte-identical.
Fresh Windows-style checkout verifies the release, including new field downloads.

Reproduce: scripts/flood_basin_storage.py,review_flood_basin_storage.py,
publish_flood_basin_storage.py,then build_fit_hub.py; run browser check with
system python scripts/check_flood_storage_browser.py (server on8766). Full field
NPZ and gzip CSV are committed in output and normal evidence page. Public climate
and ETOPO caches remain present; restore with restore_earth_harvest_inputs.py
if reset. New publisher is hooked after the gauge-timing publisher; use the direct
publisher for this page instead of the full historical chain.

NEXT: qualify real field water retention/bare evaporation and groundwater/flood
recession before selecting capacity; add missing Tigris/independent region flow
and access/drainage evidence. Build shared Earth/fantasy river-flow adapter with
explicit monthly units/calendar,then freeze harvest rule and independent tests.
Require Nile gain AND Mesopotamian non-inflation,then unchanged whole-empire supply
calibration. No blind success or adoption follows from these development maps.

CURRENT ATLAS remains release3 with owner-adopted marketed share0.3923:
850self-fed,174imports,29short,91%residentsfed; reach staffing1042. Whole-empire
Egypt failure still open. Complete resources/work, actual occupancy and political
authority remain unresolved; this water diagnostic does not qualify those scopes.

Older entries below are chronological history; this entry controls the next step.

# FLOOD-WATER LEDGER IMPLEMENTED; FIELD ADAPTER NEXT — 13 November 2026

Canonical branch: claude/friendly-turing-43ygeu. Resumed latest remote ec0d09c0.
Release-3 settlements and owner-adopted marketed share 0.3923 remain current:
850 self-fed towns, 174 with imports, 29 short, 91% fed; reach staffing 1,042.
All 904 existing Earth-fit files remain byte-identical. Whole-empire supply
calibration still fails because of Egypt. No flood irrigation adoption yet.

LATEST IMPLEMENTATION: harvest/flood_water.py routes monthly volumes through a
validated drainage forest. Upstream withdrawals are subtracted before downstream
use; useful delivery, paid losses, remaining river volume and outlet volume are
separate. Supplied efficiency is explicit; default 1 is accounting, not fitted.
No storage, return flow, travel delay, crop selection or floodplain adapter yet.
22 new tests / 37 combined controls pass. Separate edge-incidence and demand
complementarity audit: 200 synthetic forests, 80,544 monthly node balances,
exact repeated numeric outputs. No area/harvest scores or default changes.
Read docs/FLOOD_WATER_BUDGET.md; rerun scripts/review_flood_water_budget.py.
Receipt: output/flood_water_budget_20261113/review.json.

EARTH RESTORATION (9b258cc6): WorldClim 5m (five ZIPs), Natural Earth rivers,
ETOPO window and slope-arable cache are present. Separate baseline:
output/land_people/earth_restored_20261113/earth.npz (ignored, 32 MB).
Its regions.json and audit receipts are committed. Arable SHA matches previous
calibration exactly. Independent 11-region audit: areas and irrigation shares
match reference; capacity differences 0–1.44%; Roman field drift +0.353876%, as
previously recorded. Egypt remains 2.32 M. Original regional summary unchanged.
Recreate after reset: scripts/restore_earth_harvest_inputs.py, then
scripts/review_earth_harvest_restoration.py. Source pins:
data/earth_harvest_public_sources_20261113.json. Report:
reports/EARTH_HARVEST_RESTORATION_20261113.md. Use the explicit restored harvest
path in development; do not silently replace an old numeric baseline. Freight
wind caches remain missing; Roman cities.csv and areas.csv ARE present.

TIMING PREFLIGHT (7987fb33): declaration 2aaa35f9 preceded numerical inspection.
Aswan 1871–1901 (31 complete years); Hit 1965–67 and 1969–71 (6 complete years).
Fixed November/five-month compatibility: 0.9443 vs 0.0494. Dimensionless timing
shares are NOT irrigated fractions or delivery efficiencies. Indus Kotri starts
1936: declared pre-1932 check remains UNSCORED, with no post-dam substitution.
Both scored gauges are development inputs, not independent validation.
Report reports/FLOOD_BASIN_SEASONALITY_20261113.md; evidence page
atlases/earth_evidence/flood_basin/. Fetch/produce/review/publish scripts:
fetch_flood_gauges.py, flood_basin_seasonality.py,
review_flood_basin_seasonality.py, publish_flood_basin_seasonality.py.
15 controls, 1,469 source rows, 168 season combinations / 504 phase values;
five fresh output files byte-exact. Source CSV, NPZ, exclusions and licenses ship.
Six viewport/theme checks, keyboard, real download hashes and navigation pass;
Windows-style checkout verifies the release and 2,217 data assets. New fields
NPZs are tracked despite the general ignore rule. The evidence publisher hook is
installed; refresh this panel directly, then build_fit_hub.py. The full historical
publisher chain needs other caches and is unnecessary for this panel.

NEXT: connect the conserved routing ledger to qualified monthly river flow,
flood storage/delivery and physically admissible crop-water demands. Declare
aggregation/priority, crop-calendar tie policy and independent test regions
BEFORE new area/capacity scores. Fully watered seasons can tie in the existing
crop optimizer; do not silently maximize flood timing across those ties.
Do not turn terrain times phase into fully irrigated area. Require Nile gain
AND Mesopotamian non-inflation, then rerun unchanged whole-empire supply tests.
Indus is still unvalidated by the current source. Complete resources/work and
actual sovereignty remain unresolved.

The entries below are chronological history. Their pending 39% owner decision
and parked source-audit priorities are superseded by the current releases.

# MARKETED SHARE 0.39 ADOPTED — 13 November 2026 (ninth pass)

OWNER: adopt Earth-calibrated marketed share. build_wide_supply_release3.py reads 0.3923 from
output/settlement_supply_calibration_20261113/without_egypt/results.json; headline key
central_x39. Corrected: 850 self-fed, 174 with imports, 29 short, 91% fed. Reach staffing set
identical (1,042) so control maps were not rebuilt. Supply maps, default-map legends and notes
republished; browser checks pass.

NEXT UPDATE (groundwork started): flood-basin irrigation for desert rivers, see
calibration/flood_basin_irrigation_20261113/ and its notes.
GROUNDWORK DONE: scripts/flood_basin_groundwork.py -> output/flood_basin_irrigation_20261113/groundwork.json.
Land <= 5 m above the nearest navigable river and within 30 km: Egypt 24,600 km2 (history ~25,000;
model irrigates 9,700). BUT the same test gives Lower Mesopotamia 64,000 km2 where the model is
already too high (capacity 8.2 M vs 0.7-2 M). So terrain alone cannot be the rule; a second factor
is needed (flood timing vs crop season is the first candidate). Plan file is groundwork, NOT a
frozen test declaration: freeze rule and held-out rivers before scoring.

# SUPPLY CALIBRATION PASSES WITHOUT EGYPT; EGYPT HARVEST STILL OPEN — 13 November 2026 (eighth pass)

Report: reports/SETTLEMENT_SUPPLY_CALIBRATION_20261113.md (rewritten). Plan amendments A1, A2.
A1: scripts/land_people_earth.py --deltas observed (map's delta-fan rule with observed Edmonds
areas) -> output/land_people/earth_deltas. Egypt capacity 2.3 -> 2.8 M only (hist 4.5-5);
calibration unchanged. Option is OFF by default; committed Earth inputs untouched.
A2: settlement_supply_calibration.py --without-egypt (lon >= 29 E and lat <= 32 N removed from
demand and supply) PASSES the declared rules: 270 km kept (west/east 1.11), transfer 92%/98%,
e95 = 0.39. Fantasy one third is "low"; at 0.39 fantasy feeds 91% (29 towns short) vs 85% (41).
NOTHING changed on the fantasy map.

OPEN OWNER DECISION: adopt marketed share 0.39 (Earth value) in place of one third?
NEXT UPSTREAM: flood-basin irrigation for desert rivers in the harvest model (Nile gets ~14,500
km2 irrigated vs ~25,000 historical; model people ~1 M vs 4.5-5 M), fitted/tested on Earth, then
rerun the whole-empire calibration. Calibration script options: --harvest, --people, --without-egypt.

# EARTH SUPPLY CALIBRATION RUN; BLOCKED BY EGYPT HARVEST — 13 November 2026 (seventh pass)

OWNER: leave town sizes as they are; continue towards a real calibration.
Report: reports/SETTLEMENT_SUPPLY_CALIBRATION_20261113.md. Plan: calibration/settlement_supply_calibration_20261113.

EARTH CACHES REBUILT (all public, all in ignored data/cache or ignored npz):
  data/cache/worldclim/wc2.1_5m_{tavg,tmax,tmin,prec,elev}.zip  https://geodata.ucdavis.edu/climate/worldclim/2_1/base/
  data/cache/naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson  raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
  data/cache/ncep_ltm/{uwnd,vwnd,wspd}.mon.ltm.nc  downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/<v>.sig995.mon.ltm.1981-2010.nc
  scripts/arable_slope_earth.py (ETOPO via NOAA; arable_5m.npz hash MATCHES the recorded one)
  scripts/land_people_earth.py --out output/land_people/earth  (earth.npz REBUILT, not byte-identical:
  Roman people field differs 0.35% in total; it rewrites tracked regions.json -> git checkout it). pip install h5py.
  Still missing: itinere roads gpkg, Cliopatria, Han shapefile (committed pool masks are used instead).

RESULT: declared test FAILS (east never 95% fed at 270 km; best west/east agreement at grid edge
540; transfer 53%). Cause: harvest model gives Egypt 2.3 M capacity vs 4.5-5 M historical.
Post-hoc without Egyptian cities in the score: 270 km holds (west 0.38 / east 0.47), e95 = 0.42,
one third feeds 88% (fantasy 85%). Earth surplus per rural head 2.15 vs fantasy 2.2.
No fantasy parameter changed.

NEXT: fix Egypt/Nile irrigation in the Earth harvest model, rerun the calibration unchanged;
then owner decision between marketed share 0.42 and haul limit 400 if 95% feeding is wanted.

# ONE-THIRD SUPPLY, SUPPLY-FED REACH, AND ROMAN SUPPLY PILOT — 13 November 2026 (sixth pass)

OWNER DECISIONS: one third of surplus marketed; calibrated residents feed the reach chain;
work towards an Earth-calibratable supply method.

1. SUPPLY CORRECTED (plan amendment A1): production is labour-limited (harvest.field_support,
   600 h/worker); the first build used cereal potential and overstated supply. Corrected
   headline: 832 self-fed + 180 with imports + 41 short of 1,053; 85% of residents fed.
   reports/SETTLEMENT_WIDE_SUPPLY_20261113.md. Map sizes are NOT reduced for short cities.
2. REACH: scripts/build_supply_fed_reach_release3.py overrides institutional_active in the
   release-3 chain packet (affiliated and fed residents >= 150), then build_control_v2/v21 via
   run_on_release3 with folders *_supplyfed_release3_20261113. Default option release3_fed_v21.
3. EARTH PILOT: scripts/settlement_supply_earth.py on the Roman window (static network, grain
   proportional to rural people). m95 about 0.6-0.8 person-years marketed per rural resident;
   fantasy m = 0.74 (one third) / 0.22 (10%). Supports one third. Weak: haul limit sensitivity
   (x5), west/east differ x2, proxy production. reports/SETTLEMENT_SUPPLY_EARTH_20261113.md.

NEXT for a real calibration: restore output/land_people/earth/earth.npz (Earth cereal potential
and labour), build the seasonal sea network on the Roman window, fit haul limit and marketed
share on one half and test on the other and on Han. Also open: apply shortfalls to town sizes?
ledger packet for the new reach; evidence hub.

# WIDER GRAIN SUPPLY SCENARIO PUBLISHED — 13 November 2026 (fifth pass)

Report: reports/SETTLEMENT_WIDE_SUPPLY_20261113.md. Plan: calibration/settlement_wide_supply_20261113.
polity/wide_supply.py + scripts/build|review|publish_wide_supply_release3.py. Transport paid in
grain (1 - c/270 road-km eq., existing trade costs), hinterland to cheapest town, then
cheapest-first shipments between towns. NOT fitted or Earth-tested.
Corrected headline (sliding density, 10% of surplus marketed): 816 self-fed, 171 with imports,
66 largest short, 73% of residents fed. At 33% marketed, or with flat density, all fed.
Atlas: Settlements options release3_supply / release3_supply_x33 (data/release3_supply.json);
default maps' white centre now = fed including imports.

OPEN OWNER DECISION: extraction share (10% legacy vs about one third) before calibrated residents
drive the reach chain; at 10% the 66 largest cities would be cut. Not yet done: feeding
supply-limited residents into review_settlement_integration (civilian_request).

# DOWNSTREAM LAYERS REBUILT ON RELEASE-3 TOWNS — 13 November 2026 (fourth pass)

Report: reports/SETTLEMENT_DOWNSTREAM_20261113.md. Plan: calibration/settlement_downstream_20261113.
Reach, trade, imperial access, administrative links and supply-supported reach (control v2/v2.1)
are rebuilt on release-3 POSITIONS and shown by default through manifests under
atlases/earth_fit/data/release3* (release3_layers.json, release3/admin, release3/hierarchy,
release3_reach.json). atlas.json, release.json and all earlier files are byte-identical.

HOW: polity/release3_placement.py routes F.place_towns to the reviewed positions;
scripts/run_on_release3.py executes any existing builder with output folders redirected.
Publishers that write into the atlas were run IN PLACE, outputs moved to data/release3/, then
`git checkout` restored the published files. export_reach takes ~17 min per climate; staging
atlas names must be unique (trade checkpoints and polity_map cache are keyed by folder name).
Unmodified-exporter controls reproduced published layers byte for byte.

NOT DONE: calibrated residents are NOT fed into the supply chain (kept 7.5% request: owner
decision needed, it would be an untested model); no interactive ledger packet for the release-3
supply reach; work-calendar/visit experiments not rerun; earth_evidence hub not regenerated.
output/fertility_integration_20261106/*_factors.npz was regenerated (ignored cache).

# RELEASE 3 PUBLISHED AS DEFAULT SETTLEMENTS MAP — 13 November 2026 (third pass)

Reports: reports/SETTLEMENT_RELEASE3_20261113.md (positions) and SETTLEMENT_RELEASE2_20261113.md
(sizes). Both branches (claude/wonderful-mayer-uqbwtb, claude/friendly-turing-43ygeu) at the
same commit.

OWNER DECISIONS (binding): lore ranking of marked places MUST stand; sliding 100-500/ha is the
headline density (published Hanson method); the calibrated map is the Settlements default.

Placement: family A (fixed 18 km + heartland prior strength) FAILED 5/8. Family B (production
catchment tiling with exp(-D/L) on score and catchment density, count held by rescaling
seat_people; polity.settlement_locations.prior_tiling_sites) PASSED 8/8 with cross-pool L=800.
Declared limit: NO third family on Han/Rome without new Earth data. Fantasy: unmarked towns
re-placed (420/902 corrected moved), tracks rebuilt, sizes/ledgers recomputed, published as
release3_central (default) / release3_low in earth_fit (data/settlement_release3*).
Milestones 2, 3 (settlements+tracks only) and 4 (settlement map) are met at
development/cross-pool level; NOT blind validation.

NEXT: (a) feed release-3 towns and residents into reach, trade, administration (they still use
legacy towns). (b) Blind transfer when output/land_people/earth/earth.npz is restored.
(c) earth_evidence hub panel / build_fit_hub not regenerated. (d) Wider food supply for
import-dependent towns. Scripts: settlement_fantasy_inputs.py reassembles fantasy placement and
collection inputs with exact controls. Older browser checks that assert joint365 as the
Settlements default will now fail by design.

# RELEASE 2 SIZES PUBLISHED; PLACEMENT STILL OPEN — 13 November 2026 (later session)

Working branch this session: claude/wonderful-mayer-uqbwtb; fast-forwarded into the canonical
claude/friendly-turing-43ygeu at the owner's request. Full account: reports/SETTLEMENT_RELEASE2_20261113.md.

Done: (1) declared official Hanson table audit + exact housing-key join
(output/roman_city_source_recovery_20261113/audit.json, review passed). (2) Release-2
declaration calibration/settlement_release2_20261113/plan.json committed b13f7a3a BEFORE fits.
(3) Earth calibration output/settlement_release2_20261113/results.json: size gate PASSED
(held-out KS 0.058, area ratio 0.945; model lnA = 2.157 + 0.127 lnH, sigma 1.057, R2 ~ 0);
placement finalist fixed18_L800 FAILED (5 of 8 quadrants, needed 6) so legacy positions stay.
(4) Fantasy sizes rebuilt on legacy sites with closed people ledger and local cereal flag;
amendments A1 (wide regional draw), A2 (lore rank gets largest draws), A3 (OWNER: lore rank
strict on final size; one ledger per density reading) and A4 (OWNER: sliding 100-500/ha is the
headline as the published Hanson method; flat 100/ha is the cautious alternative) are post-hoc
and disclosed. OWNER DECIDED: lore ranking of marked places MUST stand. (5) Published as Settlements options release2_central / release2_low in earth_fit
(data/settlement_release2*), NOT default. Browser check 8 cases passed.

Milestones: 2 = sizes qualified internally, placement NOT qualified; 3 = sizes only (tracks,
reach, trade, administration not rebuilt); 4 = optional maps published, default unchanged.

NEXT: (a) placement iteration: fix the regional count split (finalist over-concentrates in the
dense core, production under-concentrates) before spacing; declare before scoring.
(b) A blind transfer needs the private cache output/land_people/earth/earth.npz restored.
(c) Feed release-2 residents into reach/trade/administration. (d) earth_evidence hub panel and
build_fit_hub were NOT regenerated this session. Windows checkout check passed (2111 assets).

Environment notes: fresh container; .venv rebuilt with pip (numpy/scipy/matplotlib/pillow/numba/
pytest/scikit-learn/pyshp/openpyxl/pandas). No Python Playwright: use Node Playwright
(scripts/check_settlement_release2_browser.js) with python3 -m http.server 8766;
serve_atlases.py hung at startup here. Raw Hanson CSVs live only in ignored data/cache
(pinned URLs/hashes in the recovery plan). *.npz outputs are gitignored: fantasy_*_fields.npz
are reproducible with build_settlement_release2.py.

# HANDOFF REQUESTED — 13 November 2026

Owner is running out of usage and explicitly requests wrap-up, commit/push and
handoff to another agent. STOP ongoing work after this checkpoint. No jobs remain
running apart from the local HTTP server. Resume only when the next agent is asked.

Canonical/default branch: claude/friendly-turing-43ygeu; remote Anton2181/rotclimate.
Latest pre-handoff HEAD ab66b509. Earlier:dadbcc46 resets release priority;46d8aaf6
source-filled destination audit;203fc49b source pickup audit;049ba98e rural meals;
38d918bd eight OPTIONAL experimental point maps. All science/review/replay/browser/
Windows checks for these checkpoints passed and were pushed. Latest portable
release:Earthr44,2104byte-exact assets. No PR,merge or default-model adoption.

OWNER'S ACTUAL GOAL: next EARTH-CALIBRATED settlement location/population atlas.
Still milestone2of4:fit/test counts,placement,SIZES. Vidarbha transfer FAILED;
50housing samples haveZEROqualifiedAD150population labels. Do not describe the
eight experimental maps or food/work audits as that release. No credible release
ETA was promised. Further food/staff/storage experiments are PARKED. Detailed
institutions/control/S2–S5 are later work,not blanket blockers for first settlement
release. See roadmap 'Immediate release priority' and four-milestone contract.

Concrete last recovery (preparation only; protocol committed BEFORE inspection):
calibration/roman_city_source_recovery_20261113/plan.json,commitab66b509.
output/roman_city_source_recovery_20261113/source_access.json preserves URLs,
SHA256,encodings,headers and counts. Official Oxford CSVs AREaccessible despite
the broken XLSX and2017PDF links. Cities:1388rows,cp1252;Areas:885rows,UTF8-BOM.
Raw files exist ONLY in ignored data/cache/roman_city_source_recovery_20261113/
(cities.csv,areas.csv,initial_schema.json);redownload using pinned URLs/hashes
if new environment omits them. No requests package installed;stdliburllib works.
No table joins,measurement gate changes,new model fits or scores have been run.
Areas has key/Area/Estimate Basis,NOphase fields. City Start/End does NOT date
housing samples. Do NOT infer all-date occupancy or certify size labels from keys.

NEXT: implement the declared official-table audit and exact author-key join to
data/source/roman_housing_2023/table2.csv;preserve unmatched/ambiguous names,
units,unknown dates and sampling/extent limits. Independently review and freshly
replay before publication. Then freeze a defensible calibration/validation cohort
and genuinely new transfer test BEFORE fitting/scoring. Old Vidarbha is spent.
Only after qualifying the empirical fit:rebuild fantasy settlements on the shared
ledger,then publish/check the normal atlas. Do not add later S4 detours.

Scientific .venv/bin/python;globalpython has Playwright,/usr/bin/chromium.
HTTP8766may still run;restart after environment reset. Private Vidarbha earth.npz
cache missing:full historical evidence writer blocked;use reviewed direct writers
and build_fit_hub AFTER final publication. Stage all assets/release BEFORE
check_atlas_checkout.py. No subagents unless explicitly authorized.

# OWNER PRIORITY: next Earth-calibrated settlement atlas — 13 November 2026

LatestowneraskswhengettingnextEarthcalibratedsettlementatlas. Weansweredhonestly:
no defensiblereleaseETA, stillmilestone2of4 empiricalcount/location/sizefit.
PriortransferFAILED;50housingrecordsstillzeroqualifiedAD150labels. Eightmaps
pushed38d918bd areEXPERIMENTAL,not thepromisedcalibratedrelease. Too muchwork
wentintofood/staffdiagnostics;STOPdetouring. Thefourmilestonecontract explicitly
leavesdetailedinstitution/control/S2–S5tolaterreleases. Preservefullprogramme,
butmakeempiricalcalibrationthereleasecriticalpath.

Latestpush46d8aaf6 completes48source-filled destination outcomes,normalpub,
2104Windowsassets/allcurrentpins/52freshfiles;workingtreecleanbeforethispriority
update. Earlier203fc49b sourcepickups,049ba98e ruralmealconvention,38d918bd8maps.
ALLarepreserved. Loss-aware reserveplanwasdeclared46d8aaf6 BUTNOprototypeor
cohortoutputsrun;PARKIT whilecalibrationrelease2 unresolved.

NEXT recover/qualifyusablecount/location/residentmeasurements andfreeze fit/
comparison/newtransfer BEFOREscores;oldVidarbhaisspent,failure stays. Original
housing2017/workbookaccess404/403;2023table50samplecities has47unknownsample
phases/3incompatibleAD150,alllackcertifiedsampling/extent. No invented dates or
regressionpopulationsasindependentlabels. Websource-recoverycheckinprogress:
Oxfordofficialcitiesdatabase,SocialReactorspublications,DOIeqapevAn8. Exact
originalworkbookSHA5b9fc0195c3b5f2df71d6380174974215280cafd3bf5fa463fbf96969b549b6c.
ThirdpartycsvmirrorfoundbywebsearchbutNOTverified/loaded;notoriginalworkbook.

Milestone1refscomplete;2fit/testcountlocationSIZEpending;3sharedledgerfantasy
rebuildafterqualifiedfit;4normalatlaspublish/QA. No crediblecalendarETAyet.
Prioritize thispath,doNOTclaimexperimentalpointmapsorbalancedledgersareEarth
calibration. Source-role/date/mobile/complete-resource/physicslongtermqueuekept.
Canonicalbranch claude/friendly-turing-43ygeu;pushsinglebranchonly,thenCONTINUE.

# Source-filled destination audit complete — 13 November 2026

CONTINUE AFTER PUSH. Canonicalclaude/friendly-turing-43ygeu only. Latestremote
203fc49b sourcepickupaudit;earlier049ba98e ruralmeals,38d918bd 8newoptional
foodcheckedpointmaps. Current source_filled_destination_20261113 declared203fc49b
BEFOREoutputs,ALL48A/Brows complete. AexactpriorOWNcalendarC packedraw*.95;
Bsource-withdrawnraw*.95ONCE atSAMEreturns/onebinlag. IDsjoinonce. All24plans
includeallactive/partialproviders. Conditionalpeople/capacities/jobs/maps unchanged.

Independent64,804,832joins/9,816,816returnevents/38,736foodinventories/864actors
passedscalarstocks/bracketedroots/conservation. Aexact, BfoodpasssubsetA. ALL
source ruralfailuresretained;allsource/work/destinationconjunctionZERO. Selected
300hfoodpassesraw652->14/671->15,corr696->16/710->17;aggregate gap+0.0141–0.0151pp.
Not observedhunger/mortality. 50controls BEFOREproduction. Fresh49model/field/
eventfiles+3exports exact. 50,088providerCSVrows+24scoped local-source/active-
destinationmassledgersreviewed. Transportloss .05ONLYwithdrawnraw,unfillednot
actualloss;outside/inactivedestmealsunscored. All791Earthassets unchanged.

Normal48rows/2figures/58downloads #source-filled-destination;report
reports/SOURCE_FILLED_DESTINATION_20261113.md. Bothfiguresposted. Browser48rows/
2figures/59links/keyboard/mobile/themes/failurepassed. Windows2104byte-exactassets andverifiedr44release passed;finalpins/52fresh
files/58publishedbytes pass.
Output source_filled_destination_20261113:24events+24fields NPZ,results,controls,
review,replay,providersCSV,transport_and_chain_massJSON,exports/reviews/replay,
presentation,browser/evidence/review. Headers0basedactor/providerIDs.

NEXT declaredcalibration/loss_aware_source_reserve_20261113/plan.json:derive
minimum initial physical reserve r*expm1(hT)/h, zerolossrT. Rates/days/loss units
explicit;no extrafood orfit tooldcases. Needversionedprimitive,zero/finite/
monotonicity/insufficientharvest/quota-mass controls andindependentrootchecks
BEFOREanynewcohort. Laterfixedsourcevariantusesanalytic365daycoveragecapacity,
SAMEproduction/people/harvest/exportcapacity/quota/all24jobs;reportcapacityextra
andproduction/surplusfailures. Itis mathematicalscenario,not actualbuildings/
utilization/cost/adoption. DoNOTjusttune capacityuntilearlierrows pass.

Wholeprogramme release1–4/S1–S5,datedoccupation/sizes/roles/failedtransfer,crew
foodlocation/complete diets/household/draftwork,mobile/nonstate/unaffiliated and
independentphysicsqueue remainopen. Readcurrentroadmapatcontinuations.
Scientific.venv/bin/python;globalpythonPlaywright+/usr/bin/chromium,HTTP8766.
Directreviewedpubthenbuild_fit_hubAFTERfinalpub;stageassets/releasebeforeWindows
checker. Historicalall-evidencewriterstillmissingprivateVidarbha cache. No subagents.

# Physical source pickup audit complete — 13 November 2026

KEEPGOING AFTER PUSH. Canonical claude/friendly-turing-43ygeu only. Latestpushed
049ba98e ruralmeal audit;38d918bd published8new foodchecked optionalpointmaps.
Current source_food_events_20261113 declared049ba98e,ALL24fixed baseline/joint/
previouslyselected calendars now independentlyreviewed. 64,804,832rawrequest
IDs/clocks/cargo,463,992origin two-storeyears/432actors. Ruralharvest fillsphysical
365day store,overflow×.1only entersexportstore;rawsourcepickupsnot.95retained.
Parentexportcapacity fixed export_harvested (365day reserve);no tune/date/replan.

Everypositiveperson ruralorigin STILLfails exposed365day sourceconvention.
SourceBOTHprovidersZERO inall24. Export-only passes840/861raw600,44/724raw300,
869/889corr600,31/754corr300;sameflags acrosspolicies/crews,butrawunfilledamounts
differ0.000342–0.035840%. Not observedfamine/actualauthority. Deststocks/maps
unchanged791assets. Fullperorigin/source/store/eachpickup request/time/ID/raw
withdrawal/deficit NPZs;463992origin+25044providerCSVrows allindependentlychecked.

21newprimitivecontrols+event/chronology=37beforecohorts. Independent200synthetic
cases/1539requests passedbisection+scalar review,largest1.407e-13energy. Full
actualreviewerror4.523e-15energy. Fresh25model+3CSVexportfilesbyteexact. Normal
24rows/2figures/35downloads in #source-pickup-calendars;reportSOURCE_PICKUP_
CALENDARS_20261113.md. Bothfiguresposted. Browser24rows/2figures/36links/keyboard/mobile/themes/failurepassed.
Windows2046assets/verifiedr44release passed.

NEXT declared calibration/source_filled_destination_20261113/plan.json BEFORE
nextoutputs. All24sourceplans compareAexactpriorC packedraw*.95 versusBSAMEjobs/
returntimes butsourcewithdrawnraw*.95ONCE. Desttime=((month+1)*365/12+end/7)%365.
Originalonebinlagretained;sourcepickup andreturndifferentclocks. Keep allactive/
partialproviders,48A/Brows,fullfields/events/CSV. A priorbaseline/joint andselected
foodEXACT, BfoodpasssubsetA. Propagatesourceexport/ruralfail flags separately:ALL
sourceboth stillfail,nonewdestpassrepairsit. Noauto map/default/capacity/resident
adoption. Source-filledjoinprototype polity/source_filled_deliveries.py has12newcontrols;
combinedjoin/event/partition/source50tests pass. Needfullcohortbuilder,indep
scalarroots/fullcargo/mass,bytefresh,normalpub.

Allrelease1–4/S1–S5/datedoccupancy/sizes/roles/failedtransfer/completeworkdiets/
crewcarriedfoodlocation/mobile/nonstate/unaffiliated andphysicsqueue remainopen.
Readcurrentroadmapwholeprogramme everycontinuation. .venv/bin/pythonscience,global
pythonPlaywright+/usr/bin/chromium,HTTP8766. Directreviewedpubthenbuild_fit_hub
AFTERlastpub;stageassets/releasebeforeWindowschecker. Oldhistoricalwriterstill
missingprivateVidarbha cache. No subagents. Pushisacheckpoint;CONTINUE.

# Fixed rural source meal audit complete — 13 November 2026

KEEP GOING AFTER PUSH. Canonical claude/friendly-turing-43ygeu. Latest pushed
38d918bd publishes8foodchecked optional point maps/32visit+48food rows. Current
source_continuous_meals_20261113 phase declared in38d918bd and completed ALL
16local/outside oldmonthly(A)/continuous(B) cases. ALLpositive-person origins
failB atoriginal365day physicalcapacity:oneannualharvest cannotcoverannual
meals PLUSstorage loss. Baggregate gap2.5275–3.1579%,includingexistingproduction
deficits. Noobservedfamine/abandonment,capacitytuning,newexports,residents ormaps.

Independentonepulseclosedforms/scalarledgers/pathschecked1,935,112originaccount
inventories,967,556CSVrows/144localactors;largestpatherror5.821e-11annualmeals.
32controls beforeproduction;9model/field/CSVfreshfilesbyteexact (testtiminglogs
not deterministic data). Fullannualfields+13stockpath/12unmetbins perorigin in
4NPZs;4CSVgzipfiles withIDs/people/production/bothgaps/flags. All791Earthassets
byteexact. Windows2011assets and5UItemplates/integrations exact;browser16rows/
2figures/14byteexactlinks/keyboard/mobile/themes/failure passes. Normal16row/2figure/13downloadpanel #source-continuous-meals,report
reports/SOURCE_CONTINUOUS_MEALS_20261113.md. Postedbothfigures. Noappcodechanged.

NEXT declaredcalibration/source_food_events_20261113/plan.json:two-store rural
andexporteventprimitive. Ruralharvest/continuousmeals/clip/loss;ONLYactualrural
overflow×0.1entersexportstore,quota/excessuncollectedexplicit;discreteRAWpickup
requests,partial/unfilled cargo,no sourcetransportretention. Minimumperiodic
ruralstockthenexplicitquotapulses/minperiodicexportstock. Prototypeharvest/source_food_events.py and21newcontrols alreadyimplemented
UNCOMMITTED;37source/event/chronologytests pass. Needindependent scalarreview
BEFOREnewcohorts. Laterall8cases×baseline/joint+8selected
plans,actualpickupatstart+outward+.25handling,allruralfailuresretained. Preserve
oldsourceclasses/writers/maps. Seeplanforfixed capacities/chronology/priority.

Wholeprogramme currentroadmap updated release1–4/S1–S5. Destinationfood/mandatory
calendar conjunction cannotrepairsourcefood. Datedoccupation/roles/sizes,failed
prospectivetransfer,complete diets/household/draftwork,crew-carriedfood/location,
mobile/nonstate/unaffiliatedintegrationandindependentphysicsqueue remainopen.
Scientific.venv/bin/python;globalpythonPlaywright+/usr/bin/chromium;HTTP8766.
Directreviewedpublisherthenbuild_fit_hubAFTERfinalpublication;stageallassets/
releasebeforeWindowschecker. Historicalall-evidencepublisherstillmissingprivate
Vidarbha cache. No subagents. Pushisacheckpoint,CONTINUE.

# Food-checked visit maps complete — 13 November 2026

CONTINUE AFTER PUSH. Canonical branch claude/friendly-turing-43ygeu only.
Latest previous remote4d496baf; current checkpoint publishes EIGHT optional
foodvisits600/300_crew1/4 point maps, ONE complete provider policy/year AND its
OWN C destination cereal. All32visit/48policyfood rows,2figures and28downloads
are normal research in atlases/earth_evidence/#food-checked-visits;full methods
reports/FOOD_CHECKED_VISITS_20261112.md. No default/calibrated adoption.

Full independent review passed43,164,640trip checks,15,494,400worker-bins,
38,736active food inventories,strict task identities,own food and physical flags.
Summaryreview32rows;mapreview8cases/all173064pointCSVrows/scalar provider stock
paths/masks/pixels. Download review240entries/58436provider outcomes/80rows.
Fresh244model,22map,12download files byte exact. 76focused tests pass. Windows1998byte-exact assets/verifiedr44release. Browser
8maps/7families/providerCSV/foodfail witnesses in6cases/point clicks/mobile/themes/
reload/optional failure/defaultv21;research80rows/2figures/30byte-exact links/
keyboard/mobile/failure/deep link passed. Read receipts in output/continuous_
food_visit_calendars_20261112. Old766data/assets exact;3UIintegration files
explicitly before/after hashed. Source algorithms/pinned prior writers untouched.

Next protocol calibration/source_continuous_meals_20261113/plan.json is declared
BEFORE outputs. Audit SAME fixed rural harvests,people and365day capacities in
ALL local ANDoutside origins of4parents. A oldmonthly versus Bcontinuous meals
and immediate capacity clip;whole inventory convention change,not timingalone.
No newexports/residents/calendars/maps. Keep all16rows/failures/full originfields.
Implementcontrols,independentscalar/oneannualpulseclosedform review,freshreplay,
normalpublication/figures. Then separately declare actual source export event
withdrawals and carried-ration/food-location work. All release1–4/S1–S5/dates/
sizes/roles/transfer/complete resources/mobile/nonstate/unaffiliated remain open.
Read current roadmap live review at every continuation;push is a checkpoint.

Scientific .venv/bin/python;globalpython Playwright + /usr/bin/chromium. Server
8766 local;restart after environment resets. Full historical all-evidence writer
still missing private Vidarbha cache;use reviewed direct publishers then
scripts/build_fit_hub.py AFTER finalpublication. Stage assets/release before
Windows checkout checker. No subagents.

# Active food-checked NEW visit phase after 4d496baf — 13 November 2026

OwnerCONTINUE,doNOTstopafterpushing. 4d496baf pushedcollector-onlyaudit (79tests,
1948Windowsassets/921hubdeps,all769Earthfilespreserved) andcommitted continuous_
food_visit_calendars_20261112/plan.json BEFORE nextoutputs. No subagents.

Newpolity/food_checked_provider_year.py wrapsunchangedstrictselect_provider_years
withcombinedworkbins&OWNfoodC flags,thenexposesphysical12bin,food,qualified
SEPARATELY. Sixnewcontrols+oldyear/partition=22passed beforefundedoutputs.
NEWpointjobs produced by scripts/build_continuous_point_jobs.py (adaptedcopyold
immutablewriter,NEWphysicalparentandnewreservedbudgets,oldexactpathfiles).
Output output/continuous_food_visit_calendars_20261112/funded_results.json and
funded_fields.npz. Countsraw600crew1/4=171871/155548,raw300=150386/136654,
corrected600=179063/163389,corrected300=157533/144167. Allrequests unchanged.
Pointinlinezerobudget/wholeledger controlsranbeforeeachsavedcase. BeforeFULL
calendarproduction,55point/foodwrapper/joint/year/worker/partition/eventtests
passed. Newreview_continuous_point_jobs.py importsunchangedoldindepgraph/scalar
review check_paths/scalar_allocation;session21515 wasrunning24graphs/8scalarcases.
Finish/inspect funded_review.json. NO fullvisitcalendar outputs yet.

NEXT implement build_continuous_food_visits.py:all8fundedcases,each2orders,12bins.
Readonlykey'sfundedarrays toboundmemory. Pointjobsfromfundedserved true;owners=
provider_for_target,crew-personcost=chosen_cost_hours. Passvisit_duration=cost/crew.
Collection-first pack_worker_calendar:physicalvisit=visit_packed. Jointoriginal
pack_joint_worker_calendar:physical=visit_scheduled,binqualified=visit_bin_qualified.
Physicalpointworkcharged evenlatermandatoryfails. Allservicesbeforejobs exactly
NEWf work_secondary_hours[1:,month].sum. CollectionprefixinbaselineMUSTfieldexact
currentcollector-onlycalendar (allcollectionrows/flags;workerendnowincludesvisits,
soverifyadditionalworkbyvisitintervals ratherthancomparingworkerend directly).

EverypolicyALLactive sourcefoodA/B/C (notonlycomplete),samecargo helperslag/retention.
Saveper-policy monthlyfullcollection+visit+workerpackets;fields/events foodscalars.
FoodC selectedonlywithphysicalALL12;wrapperoneWHOLEyear/provider strictbaseline
qualifiedtaskidentitypreservation. Produce32visitrows(8funded/16policy/8selected)
AND48policyfoodrows (baselinefoodduplicatesbetweencrews explicit,shouldexactmatch
currentcollector-onlyfoodfields). Keepall18actors/provider/point partitions.
NEWselectedfields shouldseparate selected_mandatory_complete,selected_food_no_shortage,
qualified;use schedule_unqualified (funded&~finalserved),notcalendar-onlylabel.
Preserveoriginalfunded route/work/capacity channels;all5sumrequestgrid exactly.
Modelselectedphysicalmonthlywork/visit/collection/missing/hours ANDownCfood
initial/final/peak/needed/consumed/unmet/spoil/overflow/duration/period/ledger fields
perprovider. ConditionalNEWparentpeople stayunchangedifqualfails. BaselineQpoints
retained;allfinaltasks subsetNEWhourfundedjobs. Nootherpolicyfood/cargo borrowed.

Thenindep scalarpointallocator/sorted-listworker&crew/cargo/stock/selectedyear
review,freshallresult/fields/calendars/exports bytes,normalresearchall32/48+figs
POSTeveryfigure,methods/review/replay/plan. EIGHTnewdistinctoptionalexperimental
pointmaps afterallQ/mask/pixel/CSV/browser/families/mobile/Windows checks. Likely
seventhpacketfamily. Existingpublisher sourceoldnetworkDuty modelcontainsOLDparent
people/food:mustreplaceALLconditionalnewparentfields/ledgerscorrectly,NOTjustgate
flags;considernewscopedcontinuous-parent baseexport orcarefulfullmodelupdate with
indepreview. No newmaps/defaults untilallfood+job+export checks. Fullhistorical
publisherprivateVidarbhacache stillmissing;directreviewedpublishers only.
Whole release1–4/S1–S5 empirical/mobile/source/rations/diets gaps remainopen.

# NEW collector/food audit verified; continue food-checked visits — 13 November 2026

Owner “Continue,dont stop after pushing”. Canonicalclaude/friendly-turing-43ygeu.
No subagents. Lastpushed4b42b703 (continuousresidents+nextcollectorprotocol BEFORE
outputs). Currentcheckpoint collectoronly,no newvisitmaps yet. PushNOTstop.

* New polity/delivery_partition.py validatesrawpacked+missingcargo byoriginal
  origin/serial/owner;retainsEVERYmissingID/partialload. lagged_return_times keeps
  imposedONE-binlag,end/7phase,365day wrap. Originaloldprimitives untouched.
  7new+10event+7workercontrols=24 passedBEFOREproduction. Fullsuite79expected.
* New build_continuous_collection_calendar.py all4continuousparentcases,NEW
  actualtrips,fundedhomeservices=work_secondary_hours[1:].sum,staff50h/bin.
  No visitjobs. ALLactiveproviders scored forAallplanned/binstart,Bpacked/binstart,
  C SAMEpacked/returnphase. A->Bomissions separatefromB->Cphase. Allrawmissing
  cargoidentifiedatsource;missing_arrivals/missingdestinationpotential areONLY
  counterfactualretainedsupply,NOTactualtransportlossonunshippedgrain. Source
  monthlyplannedexportledgerfrozen,notactualeventsourceinventory. No inventedfood.
* All12rows independent sorted-listphysicalworker/service/wholetripintervals,
  cargo+clock+scalarfood/minperiodic/conservation/216actorchecks pass. Checked
  10,820,096packed/31,767missing IDs,3,873,600worker-bins,9684foodinventories.
  Eachfoodcase includes ALLactiveproviders,includingincomplete/partialdelivery.
* Afoodpassesraw600861/raw300724/corr600889/corr300754. Bfood=734/670/778/710
  (same12mandatorycounts). Cfood688/627/720/671;C BOTH687/625/717/671. Across
  FOURALTERNATIVEscenarios Cfood2706entries,BOTH2700;notdistinctcommunitycount.
  SixfoodpassedCentriesmissingmandatorywork. AggregateCenergygapsSMALLERthanB
  ineverycase BUTmoreindividualfailures;bothsides retained,notbestcaseselection.
* output/continuous_collection_calendar_20261112:48monthlycalendarNPZs+4event/
  4fieldNPZs=56packets;results+packets57freshbytes;4deterministicZIParchives+
  providerCSV+exportmanifest make63freshfiles EXACT. Exportreview all56archive
  bytes/12522providerrecords (inactiveexplicitlyunscored) checked. Newdatafolder
  atlases/earth_evidence/data/continuous_collection_calendar has12downloadfiles,
  localmanifestbasenamesresolve. Checker extendedassetsettoZIP forWindowsbytes.
* Normal #continuous-collection12rows/2figures BOTHPOSTED,12data links+methods.
  Old769Earthfiles/maps/defaults preserved. Browser12exactrows/2figures/13byte
  links/mobile/themes/keyboard/ledgerfailure andglobaldashboard pass. Full79tests
  pass. Windows1948assets byteexactINCLUDINGZIP;921hubdependencies resolve;60source/
  6producer/769Earth hashes current;earlierresearchpageexactexceptnewpanel.
  Checkpointreadytopush,thenCONTINUE. Environmentreadyafter13Novemberresume. Scientific.venv/bin/python;
  globalPlaywright. HTTP8766session11719. FullhistoricalpublisherprivateVidarbha
  cachemissing;directpublish->build_fit_hub AFTERfinalpublish->stage->Windowscheck.
* NEXT: calibration/continuous_food_visit_calendars_20261112/plan.json MUSTcommit
  BEFOREoutputs. All8newraw/corr600/300 crew1/4,exactoldb3_p0target paths. FundNEW
  pointjobs withUNCHANGEDallocate_reserved_visits usingNEWparentstaff/active and
  work_secondary_hours[0,month] ONLY (no missingtriptime reused). 8fundedrows,
  collection-first+jnt-duration-first16policyrows,8selectedyearrows=32visitrows;
  all16policiesA/B/C=48foodrows. Baselinecollectionprefixexactcurrentcollector
  packets despiteaftercollectionvisits. Bothordersactualjobs/worker/foodchecked.
* Newversioned food-yearselectorwrapper:OLD strict select_provider_years canuse
  physicalbinflags & OWNfoodCflag[None,:] ascombinedeligibility,but expose
  selectedphysical12bin,selectedfood,qualifiedSEPARATELY. BaseBoth staysunless
  jointBoth+EVERYbasequalifiedtaskidentity+adds1. OnlyjointBothrecovers;neither
  keepsbaselinephysicaltracebut0qualifiedpoints. No mergingpolicyjobs/food.
  Everyselectedtask subsetNEWfundedjobs. ALLactivefoodrecordsretainedforallorders.
* EIGHTnewOPTIONALexperimentalpointmaps onlyafterallindep allocator/worker/crew/
  cargo/food/selectedyear/mask/pixel/CSV/fresh/browser/mobile/Windows checks. Existing
  sourcepeople remainconditionalifqualificationfails;no people reallocation here.
  Keepoldmaps/defaults (likelyseventhfamilynewmanifest). Necessarydestination
  cereal+suppliedwholecalendaronly,notfullprovisioning/sourceintrabin/rations/
  location/complete diets/observedroles/authority. New map labels muststate scope.
* Entire release1–4/S1–S5programme revisited;datedoccupation/size/providerroles,
  prospectivetransfer,source/ration/location,complete diets/household/draftwork and
  mobile/nonstate/unaffiliated resources remainopen. Wholeplan,pushthenCONTINUE.

# Active NEW collector audit after 4b42b703 — 12 November 2026

Do NOTstopafterpush. 4b42b703 pushed continuous resident replans/fullpublication/
1936Windowsassets/906hubdeps and committed calibration/continuous_collection_
calendar_20261112/plan.json BEFORE nextoutputs. Allprevious milestonesbelow.
New polity/delivery_partition.py retains raw packed+missing cargo and exact
missingorigin/serials;clockhelper retainsONE-binlag. Sevennewcontrols plus10event/
7worker=24pass BEFOREproduction. Existingoldprimitives untouched. New builder
scripts/build_continuous_collection_calendar.py launched4jobs session68023;
freshout2jobs sessionpending (inspectshell/toolreturn,notassume). Outputroot
output/continuous_collection_calendar_20261112. EveryACTIVEnewprovider retained
forfoodAallplanned/binstart,Bpacked/binstart,C SAMEpacked/actualreturnphase.
A->Bcollectoromissions separatefromB->Cphase. AllmissingIDs/cargo retained;
mandatory12bins separatefromfood andconjunction. Collector-only,no visitjobs.
No newmaps. Need independentreview now:sorted-listcollector replay/service/
worker50h/nonoverlap,alloriginaltripserialpartition,actualend/7clock+lag,
B/Csamecargo,ALLactiveprovider scalarstocks/minperiodicity/conservation/actors.
Use old reviewer integrate fromreview_delivery_timing.py and optionalcompiled
stock_end fromreview_meal_headroom.py forindep stockroot;NOproductionprimitive
imports. Everymonthpacket fields collection_origin/serial/worker/start/end/site,
worker_work_hours/calendar_end/idle_hours,worker_offsets/counts,services/flags,
required/unpackedcounts,packedrawcargo,missingorigin/serial/rawcargo. Per-case
fields containsallactive/residents/staff/cap/mandatoryflags/collection/services/
work/planned-arrivals/packed-arrivals/missing-arrivals,A/B/Cinventoryfields/flags.
Events.npz aggregateprovider/time/cargo/tripcounts. Cases+12rows/results producers
andcurrentparent+oldatlas hashpins. Fresh fields/results/all54casepackets exact;
normalresearch all12/actors/providerCSV/figures posted/packets/downloads/browser/
Windows/wholequeue thenpushCONTINUE. CurrentpriorHTTP8766session11719 afterenv
resume ready;oldserver89347dead. Scientific .venv/bin/python,globalPlaywright.

# Continuous destination resident replans published; continue NEW calendars — 12 November 2026

Owner “Continue,dont stop after pushing”. Canonical claude/friendly-turing-43ygeu.
No subagents. Lastpushedaacf2ddb includes continuous-resident declaration BEFORE
outputs. Earlier pushes970bd428 maps,ed6ae653timing,aacf2ddbmealbounds. PushNOTstop.

* New polity/continuous_destination.py extendsThresholdSeededDispatchFeedback:
  _food usesversionedvectorcontinuousbin inventories;solve overwritesdisplayceil
  withcontinuousnormalized42-step/downward-margin helper. Alloldmodel/writerbytes
  intact. New scopedfactoryadapter build_continuous_destination.py restoresold
  factory evenonfailure. Currentnewtrialpeople changesruralmeals/fieldwork/crops/
  sourceexportstocks/dispatch/integertrips/staff. Same64scan/150seed/24resident/
  40work-foodrefinements;90daycapacity scalesCURRENTtrialpeople,notoldmealbound.
* output/settlement_continuous_destination_20261112 all4 replans independently
  source/field/food/people/grain/dispatch/wholetrip/work reviewed. Scalarcontinuous
  inventories/minperiodicstocks/thresholdtrial/displayceil independentlychecked;
  reviewer importsno solver/newfoodprimitive. Fresh11files EXACT (4results/4fields,
  summary,comparison,providerCSV). Newpreparer+separatecomparisonreview all8rows/
  144actors/8348providers;zero providers retained. Oldunrecordedpeak/duration/
  periodicfields stayNULL inCSV. Newfullfieldpackets havepeak/days/periodicity.
* Newtownpeople raw600369668.076(-195.871),raw300274737.734(-709.542),corrected600
  378116.797(-164.036),corrected300281323.342(-721.505). Active861/724/889/754;
  each300hcase losesonesource underunchangedsearchedfamily,NOTimpossibility.
  Allpositivecontinuousbinstartfood/source/monthlyintegerwork pass. NO new
  collector-returnfood qualification;oldrosters cannotfitnewactualshipments.
* Normal #continuous-destination8rows/2figures BOTHPOSTED,14data downloads+methods,
  fullold/newfieldpackets andeveryproviderCSV. Preserveall769Earthatlasfiles/maps/
  defaults. 72focusedtests pass (12newprimitive/factorycontrols;11beforeproduction,
  restorationfailure controladdedafter). Browser8exactrows/2figures/15byte links/
  mobile/themes/keyboard/failure pass (longphraseoverflowfixed). Windows1936assets
  byteexact;906hubdependencies resolve;48modelsource/producer hashes,28comparison
  sources and769Earthfiles current. Earlierresearchpageexactexceptnewpanel. Fullhistoricalpublisher missingprivateVidarbha
  cache;directpublisher->build_fit_hub AFTERfinalpublish->stage->Windowscheck.
* Managedenvready afterstartupnotification;files persisted. HTTP8766 restarted
  session11719. Scientific .venv/bin/python;Playwright globalpython. Do notpoll
  stale process84936 (completed beforeenvironmentresume). Results/reviews/replays
  exist. Browser checker script check_continuous_destination_browser.py running
  session12820 atlastwrite;inspectreceiptifsessiongone.
* NEXT afterpush: committed calibration/continuous_collection_calendar_20261112/
  plan.json BEFOREoutputs. FourNEWcases,allACTIVEproviders retained including
  failed/partialdeliverysources. pack_worker_calendar originalcollection-first,
  no visits;NEWorigintrips,costs,staff50h/bin/fullcalendar,NEWfundedhomeservices=
  work_secondary_hours[1:,month].sum(axis0),equallyshared/divisible. No newworkers.
  Twelvefoodrows:Aallplannedcargo/binstart;BONLYpackedcargo/binstart;C SAMEpacked
  cargo/actualreturnphase inONE-binlaggedbin. A->B omissions separatefromB->Cphase.
  Proveplanned=packed+unpackedcargo origin/month;retainallmissingserials. Old
  trip_delivery_events rejectsmissingtrips:useNEWversionedpartialpartitionhelper,
  doNOTeditoldimmutableprimitive. 0.95retentionONCE,end/7 clock365/12 wrap.
  Reuseeventcontinuousfoodmodel;ALLactiveprovidersscored forA/B/C,notonlycomplete.
  Reportmandatory12bins/foodflags/conjunction necessaryonly. Newcollector-only
  calendarsDO NOTqualifynewvisitmaps;NEWvisittasks/fullrosters/returnfoodstillopen.
  Independentworker/cargo/clock/scalarfood/ledger checks,freshbytes,all12rows/
  actors/providers/figuresPosted/normalresearch/browser/Windows,wholeplan,pushCONTINUE.
* Entire release1–4/S1–S5 programme revisited;datedoccupation,size/providerroles,
  prospective transfer,source withinbin food,crewcarriedrations/location,complete
  diets/household/draftwork andmobile/nonstate/unaffiliated resources remainopen.

# Fixed-staff meal bounds published; continue continuous resident feedback — 12 November 2026

Owner: “Continue, dont stop after pushing”. Canonical branch
claude/friendly-turing-43ygeu. A push is a checkpoint, NOT a stop. No subagents.
Latest pushed before this checkpoint ed6ae653 (timing audit plus meal protocol).

* All16 B/C meal bounds complete:ALL5790calendar-qualified provider-years retained
  twice=11580bounds,46320endpoint inventories. Fixedstaff/originalphysicalcapacity/
  cargo/jobs. Staff-only demand feasible everywhere;full demand fails everywhere.
  Civilian meal-equivalent reductions463.824–627.013/case,0.26649–0.29931% original
  civilian meals. This is CONDITIONAL accounting,not a valid resident rebuild.
* New harvest/meal_headroom.py uses48bisections underunchanged numeric fooddiag.
  Independent review imports neither meal nor eventprimitive;scalar integration,
  separate24alpha bisections andbrent stockroots (optionalnumba independentstock
  endmap only) checkall11580bounds. Everyendpointfield exact underseparatescalar
  arithmetic;near-threshold roundoff explicit,indepalphainterval2^-24. Allactor/
  providerCSVfields/source/cap/staff checks pass. Fresh3files BYTEEXACT.
* Normal #meal-headroom16rows/2figures,7data downloads+methods. BOTHfiguresPOSTED;
  summarylegend fixedafterinspection. No oldEarthmap/file/defaultchanged.
  Scientificcommands .venv/bin/python;Playwright globalpython. HTTP8766 serving
  repo session89347. Fullpublisher stillblockedprivateVidarbha cache;direct
  reviewedpublishers + build_fit_hub.py AFTERfinalpublish. Stage thenWindowscheck.
* 67focusedchecks pass,including7 newvectorprimitivecontrols. Browser16exactrows/
  2figures/8byte links/mobile/themes/failure passes;Windows1922assets byteexact;
  889hubdependencies resolve;298sources/4producers/769Earthfiles current. Earlier
  researchpageexactafterremovingnewpanel. Receipts inoutput/network_visit_meal_
  headroom_20261112. Push thenCONTINUE nextdeclaredwork,notpause.
* NEXT: calibration/settlement_continuous_destination_20261112/plan.json MUSTbe
  committed BEFOREresident outputs. New harvest/continuous_food_stocks.py is
  manufactured-only vectorbinstart inventory,compatibleFoodYear withabsolute
  periodicresidual;7controls/scalarparity/interiorreserve/varyingrates/mixedzero
  loss/capacity/overflow pass. Original food_stocks/event_food_stocks unchanged.
  Implement newversioned ThresholdSeededDispatchFeedback-derived factory overriding
  _food AND displayed continuousfoodceil (oldnormalized42bisection/downwardmargin
  conventions). Keepoldwriter/classbytes. Scopedfactoryrestore onfailure.
* Four SAME raw/corrected600/300h load120k allopen parentcases (underlying8maps),
  old4/new4rows. AtEVERYtrial recompute ruralmeals/civilianfieldwork/sourcecrop/
  exportstocks/dispatch/integerjobs/staff;90daystores scaleswithtrialtotal now.
  Keep64scan/150threshold/24residentrefines/40work-foodrefines. No newmap until
  NEWsource jobs/repackedcoherentyears ANDNEWcollector-returnfood pass. Bpass
  cannotqualifyC. Independentfullsharedledger/work/source/destinationreview,
  freshbytes,alloutcomes/figures/normalresearch/browser/Windows,wholeplan,pushCONTINUE.
* Entire release1–4/S1–S5 programme reviewed;dated occupation/size/provider roles,
  prospective transfer,source withinbin food,crew-carriedrations/location,complete
  diets/household/draftwork andmobile/nonstate/unaffiliated integration stayopen.

# Active follow-through after ed6ae653 — 12 November 2026

Do not stop after push. ed6ae653 pushed destination timing audit and committed
meal-headroom declaration BEFORE outputs. New harvest/meal_headroom.py + six
controls implemented;16 bound rows completed in output/network_visit_meal_headroom_
20261112,all staff feasible,full meals fail. Civilian meal-equivalent reduction
463.824–627.013/case (~0.2665–0.2993% original civilians),NOT a resident replan.
Fresh builder still running session28995;independent scalar/bracket reviewer
session27312 (earlier slow session22868 terminated before results;new review
uses optional numba only for scalar stock end map inside brent root search).
Reviewer uses24independentalpha bisections and48-step producer endpoints;grain
roundoff explicit. Finish review+freshbytes before publication. Prepared scripts:
publish_meal_headroom.py,plot_meal_headroom.py,check_meal_headroom_browser.py.
Do direct publisher -> build_fit_hub AFTERfinalpublish -> stage -> Windowscheck
(release checksum fails ifhub runs before lastpublish). All oldmapfiles protected.
Need normalresearch all16rows,2figures POSTBOTH,8links/browser/mobile/Windows,
roadmap/livewholeprogramme+handoff,thenpushCONTINUE. controls67focused passed.
Next prepared calibration/settlement_continuous_destination_20261112/plan.json
MUSTcommit BEFORE resident outputs. New harvest/continuous_food_stocks.py is
manufactured-only vectorizedbinstart continuous inventory;7controls inclscalar
parity/interiorperiodicreserve/variable rates/zeroloss/overflow pass. No resident
outputs for it yet. After nextpush implement new versioned threshold-seeded
factory overriding_food and new continuous displayedfoodceil;oldcodebyteunchanged.
Four raw/corrected600/300h load120k allopen parents (same8mapcohort) replanfinite
source/food/work withcurrenttrialpeople/capacity. 64scan+staffthreshold+24resident
refines,40dispatchwork/food;old4/new4rows. No maps until NEWjobcalendar ANDNEW
return-phasefoodrecheck. Fullprogramme/empirical/source/ration/diet/mobileopen.

# Destination timing audit completed; continue meal headroom after push — 12 November 2026

Owner: “Continue, dont stop after pushing”. Push is a checkpoint, not a stop.
Canonical branch: claude/friendly-turing-43ygeu. No subagents permitted.
Provider-year map release pushed in970bd428, including the timing declaration
BEFORE outputs. Full prior milestones follow below. No PR requested.

* New harvest/event_food_stocks.py integrates continuous destination meals and
  exponential grain decay between supply pulses;capacity clips at arrival.
  Smallest periodic stock from the clamped affine map,independent of sufficiency.
  Original harvest/food_stocks.py and all older scheduling/food code unchanged.
* New polity/delivery_events.py validates every original origin/month/serial,
  owner,cargo remainder,original ONE-BIN lag and0.95retention applied ONCE.
  Ten manufactured controls pass BEFORE production,including zero loss/demand/
  capacity,minimal reserve,periodic shortage,split events,convention/lag/wrap/
  invalid serials. Previous nine provider-year controls also pass.
* output/network_visit_delivery_timing_20261112:all8 coherent calendars and ALL
  already-qualified providers. A=exact12bin original meals-first model;B=same
  supply at bin starts with continuous meals;C=same continuous model but return
  phases. Same people,cargo,90day original capacity,5%stored loss. A->B convention
  changes separate from B->C phase. Every provider passes A numeric food check;
  zero pass B/C. B unmet about0.2083% annual meals;C0.1909–0.1964%. Phases reduce
  gaps but do not eliminate them. Not physical impossibility or actual hunger.
* Independent review imports neither model nor cargo primitive:17,427,262trip
  identities,2,532,803aggregated pulses,17,370scalar provider/accounting stocks.
  Separate scalar bracketing,all ledgers/providerCSV/18actors eachcase pass.
  Fresh11files BYTE EXACT:results/fields/providerCSV/eight aggregated eventNPZs.
  controls.json runtime text is intentionally not a byte-replay claim.
* New normal #delivery-timing panel:24 exact rows,three figures ALL POSTED,
  methods and15data downloads (including every eventpacket). Direct publisher
  scripts/publish_delivery_timing.py preserves all previous panels. Every Earth
  atlas file stays byte unchanged. No maps/defaults/residents changed by timing.
  Browser24rows/3figures/16byte links/keyboard/344/390/themes/ledgerfailure passes.
  See report NETWORK_VISIT_DELIVERY_TIMING_20261112.md and results/review/replay.
* Runtime skill read;environment ready,unrestricted network. Local HTTP server
  python -m http.server8766 session89347 serves repo. Reuse if alive. Browser
  python global has Playwright;scientific commands .venv/bin/python.
* General andeightmap browser regressions pass;54focusedcontrols pass. Windows
  1915assets byteexact;879hubdependencies resolve;281sources/5producers/769Earth
  atlasfiles current. Earlierresearchpage exactafterremoving newpanel. Release
  verifiedafterfinalpublish/buildhub. Checkpoint ready tostageandpush. Full evidence
  publisher remains blocked on omitted private Vidarbha cache;use direct reviewed
  publisher + build_fit_hub.py. Do not claim historical full rebuild.
* NEXT IMMEDIATELY AFTER PUSH: calibration/network_visit_meal_headroom_20261112/
  plan.json must be committed BEFORE outputs. All8cases × B/C=16rows. Keep all
  original institutional meals/workers AND ORIGINAL physical capacity fixed.
  Multiply only civilian meals byalpha0..1;zero staff-only feasibility checked.
  Full-demand pass keeps1;staff-only failure explicit;otherwise48deterministic
  bisections retain pass/fail bounds under SAME numeric unmet threshold1e-8.
  This is a conditional meal-equivalent bound,NOT a valid resident reallocation:
  source food/field work are frozen. No maps or default change. All providers,
  actors,fields,bounds,independent scalar bracket/review,freshbytes,figures posted,
  normal research/browser/Windows,whole-programme review,push then CONTINUE.
* Entire release1–4/S1–S5 programme reviewed:dated occupancy,size/provider roles,
  prospective transfer,source within-bin food,crew rations/location,complete diets/
  household/draft work and mobile/nonstate/unaffiliated integration remain open.
  Actual resident replanning must recouple the finite source/food/work ledger,
  integer shipments and worker calendar;meal headroom is not that replan.

# Coherent provider-year maps ready; continue destination timing after push — 12 November 2026

Latest owner: "Continue,dont stop after pushing". Push is NOT a stopping point.
Canonical claude/friendly-turing-43ygeu. Lastpushed00d70d62 joint-order comparison
contains the provider-year declaration BEFOREallnewoutputs. No subagents.

* Newpolity/provider_year_schedule.py choosesONE full12bin calendar/provider.
  Baselineyear retained unlessjointalso complete,contains EVERYbaseline packed
  (month,actor,target)identity andadds>=1. Equalsets/losttask retainbaseline;
  onlyjointcomplete choosesjoint;neithercomplete keepsbaseline unqualifiedtrace.
  Inactive sources cannotpass emptyobligations;selectedtasks mustbe originalfunded.
* All8cases independentlyreviewed WITHOUTselectorimport;100176selectedprovider/
  bin worker blocks checked againstcurrent sourcephysical/food certificates.
  Everybaseline gatedtaskretained elementwise;no originalfunded taskbounds crossed.
  Allactor/bin requestpartitions remainwithseparatecalendar-unqualified channel.
  Actualphysicalwork stayscharged evenwhenyearunqualified. Ninecontrols pass.
  Freshresults/fields BYTEEXACT;22freshmap/model/CSV/gridexports BYTEEXACT.
* Gains raw600crew1/4=9572/4147,raw300=8597/2933,corrected600=9846/4496,
  corrected300=7772/2810. Qualifiedcounts raw148477/133196/140515/125199;
  corrected157989/142318/148380/133488. Qualifiedproviderflags EXACTbaseline
  inall8cases (734/671raw,779/711corrected);gains are tasks,notnew institutions.
* Newdata/network_visit_year_complete.json+year_complete/packets,IDs yearvisits
  {600|300}_crew{1|4}. ExistingSupply-supportedreachselector,experimentalonly,
  defaultunchanged. Sixth packetfamily inatlas/settled-reach.js;14readouts add
  provider-year policy andnecessary12binflag. Conditionalparentpeople/food
  remainunchanged whenrosterfails. Pointtasksnotblocks/territory. Annualgate
  necessaryonly,NOT dailyfood/within-bin grain timing/fullannualfood/observedroles.
* Newpublish_provider_year_visits.py supports --out-data scratch exports without
  activatingUI;export_replay.json has22exactfiles. Independentexportreview checks
  everyactor/pointmask,visitedpixelcolor/overlap,unchangedconditionalpeople/food,
  allCSVrows/fivepartitions/sourceIDs/yearchoices. ProviderCSV fullphysicalhours
  remaincharged atfailedsources. Pointproviderscanvarybybin underOLDassignment;
  theyare neverreassigned. Fullfields4.9MB exported once foralleight scenarios.
* Newnormal#provider-year8row/3figure evidence with9workingbytelinks;maps under
  Experimental &diagnostics -> Supply-supportedreach -> Complete-yearcollection
  schedule. ThreefiguresPOSTED. Browser8newmaps/exactcomplete+incompleteprovider
  CSV/pointmasks+pixelclick/sixfamilies/344/390/themes/reload/optionalmanifest/
  parent/binaryfailure pass. Old8pointmaps+32seededoptions/workCSVregressions
  andgeneralevidencefilters/failure pass. Windows1900assets byteexact;860hubdependencies resolve. Finalhashes
  rechecked275sources/3producers/243schedules/163maps/22exports. Earlierresearch
  pageexactafterremovingnewpanel. Receipts inoutput/network_visit_year_complete_20261112.
* Wholeprogramme reviewed:release2 datedoccupation/size/providerfunctions and
  prospective transferopen;release3partialresource/work/yearcalendar;release4
  no calibrateddefault. AllS1–S5/allactors/unaffiliated/mobile/nonstate,complete
  diets/household/draftwork,dailyfood/sourceavailability andfoodlocation stayopen.
  Fullhistoricalpublisher stillneedsomittedprivateVidarbhacache;directpublishers.
* NEXT IMMEDIATELYAFTERPUSH: committed calibration/network_visit_delivery_timing_
  20261112/plan.json BEFOREoutputs. All8cases andalreadyqualifiedproviders,24rows:
  A exactparentmonthly periodicfood recurrence;B continuousmeals/decay withsame
  arrival-bin-start pulses;C SAMEcontinuousinventory withselectedcollectorreturn
  timing insidearrivalbin. KEEPONE-BINdelay and0.95transportretentionONCE.
  Cargo=min120k/remainder byorigin+tripserial;allorigin/month/bintotals exact.
  Sameparentresidentmeals2500/day,90daycap,5%storage loss,365days. Sourcefood
  staysmonthly;crewcarriedrations/foodlocation/dailysourceavailability unqualified.
  Separate A->B timestep/capacity convention fromB->C phase. No map/defaultchange.
  Independentcontinuousinventory/periodic/ledger/cargo/clockreview,freshbytes,
  all24results andfigures/normalresearch/browser/Windows,wholeplan,pushCONTINUE.
* Timingimplementation note from readonlysourceinspection:oldfood_stocks food_year
  eats ENTIREstep meals BEFOREcapacity clip andthenstoreloss. Continuousmodel must
  clip immediatelyaftersupply,soBcontrol isessential. Fixedhazard continuousflow
  ds/dt=-r-h*s. Annualmap isclampedaffine;can derive minimalperiodicstock fromtwo
  boundarymaps andunclippedaffinebalance instead of96spinups/bisections. Verify
  independently;periodicconvergence distinct fromfood sufficiency. No timedfood
  model/results produced before declaration. Originalfood_stocks.py MUSTstaybyte
  unchanged becausemany previous certificates bindit;use a newversionedmodule.

# Fixed-order comparison ready; continue provider-year point maps after push — 12 November 2026

Latest owner instruction: "Continue,dont stop after pushing". A checkpoint push
is NOT a stopping condition. Continue immediately with the declared next task.
Canonical branch claude/friendly-turing-43ygeu;original map/certificate code stays
byte unchanged. No subagents permitted unless explicitly requested.

* Joint-order declaratione4d274da BEFOREoutputs. Newpolity/joint_worker_calendar.py
  merges SAMEcollector/point jobs bydecreasing per-worker duration;collectionwins
  ties,thenorigin/serial oractor/target. Same100-supportedworkers whereactive,
  50dutyh/bin,212.92calendar coordinates,divisiblehomeservices. Physicallyscheduled
  visits keepintervals/work evenif latercollectionfails;binqualification separate.
* All8cases×2fixedpolicies=16rows;bothpolicy12bin flags recomputed requiringactive
  sourceandALLmandatorycollection/servicebins. Necessary delivery-schedule gate,
  NOT daily provisioning,within-bin grain timing,completeannualfood oractualroles.
  Nine newcontrols +7oldcontrols pass. Independent sorted-listmixed job replay,
  everyworker/crew interval andchannel ledger passes:21,509,178collectorrecords,
  1,259,374original visits,7,752,000worker-bins.98freshoutputs BYTEEXACT. Old145
  baselinefiles/currentphysicalreviews and163mapfiles unchanged.
* All8bin-qualifiedcounts rise;collector omissionsalso rise. Raw600crew4 monthly
  137796->141624 but12bingate129049->118884. Corrected600crew4 145972->150104
  but137822->126369. Allfourperson12bin counts decline6850–11453;oneperson gated
  counts rise6350–7640 while fewerprovidersfinishyear. No winningpolicy adopted.
* Published NETWORK_VISIT_JOINT_ORDER_20261112.md,normal#joint-order16rowpanel,
  3figures andresults/review/replay/plan/matchedworkerCSV. ThreefiguresPOSTED.
  Browser16exactrows/3figures/6byte-exactlinks/24worker-policyCSVcalendars,
  344/390/light/dark/keyboard/inventoryfailure andgeneralevidencefilters pass.
  Windows1872assets byteexact,850hubdependencies resolve;final
  receipts inoutput/network_visit_joint_order_20261112.
  Use direct reviewedpublishers;historicalfullpublisher lacksprivateVidarbhacache.
* Entireprogramme reviewed:release2datedsize/occupation/providerrole/transferopen;
  release3partialresource/scheduling;release4nocalibrateddefault. S1–S5/allactors/
  unaffiliated/mobile/nonstate,completediets/household/draftwork,daily provisioning
  andwithin-bin grain timing remainopen. Neither greedyfailure norcohortfilter
  establishesphysicalimpossibility,absentcommunities orpoliticalauthority.
* NEXT IMMEDIATELYAFTERPUSH: calibration/network_visit_year_complete_20261112/
  plan.json committedBEFOREnewoutputs. Choose ONE full12bin policy/provider.
  Ifbaselineyearcomplete retainit unlessjointalso complete,contains EVERYbaseline
  packedactor/target/binidentity andadds>=1task. Equalsets orlostbaseline task
  keepbaseline. Ifonlyjointcomplete choosejoint;neithercomplete keepsbaseline
  asunqualifiedtrace,mapsnoqualifiedvisits. Neverunionjob successes acrosscalendars.
  Prove elementwisebaselinegatedtaskinclusion andsubsetofORIGINALhour-fundedtasks.
* Newoptionalexperimentalpointfamily inexistingSupply-supportedreach,all8cases;
  keepalloldmaps/defaults/cohorts. Displayselectedpolicy/yearstatus andqualified
  pointcounts;addcalendar-unqualified deficit tooldroute/crew/capacity partitions.
  Entireselectedphysicalworkerwork stayscharged evenwhenproviderunqualified.
  Gateisnecessarydeliveryschedule,notannualfood/roles/territoryqualification.
  Raw/correctedpairedpointfigures+chart,allnewfiguresPOSTED;independent review,
  byteexactfreshcases/exports,pointCSV/providerCSV/fullfields,normalresearch,
  sixfamilyUI/mobile/failure/Windows,wholeplan,pushandCONTINUE. Readexactprotocol.
  No year-selection outputs have been produced before this declaration.

# Worker-calendar publication complete — 12 November 2026

Resumed the latest remote branch claude/friendly-turing-43ygeu at a60e853f;
fetch found no newer remote work and the checkout was clean. The owner asked
to continue,so the earlier usage-limit publication pause is now resolved.

* Finished the pending calendar publication without changing the physical
  model,original result/review/replay files or any of 163 protected map files.
  Original declaration bdd6135c;four collection/eight visit cases,seven controls,
  145 fresh-file replay and independent sorted-list/interval/crew/hour review
  retained. No need to rerun the multi-million-job experiment just to publish.
* New scripts/plot_visit_calendars.py and publish_visit_calendars.py validate
  current producers,sources,reviewer,schedules and replay hashes before output.
  Normal Earth evidence panel #visit-calendar has four collection/eight visit
  rows,three figures and results/review/replay/plan plus worker/task CSV downloads.
  All earlier evidence panels are checked unchanged. Figure illustration uses
  first eligible four-person case/bin and lowest provider with both job types;
  first12 visit workers,filled with lowest others. Figure IDs start at1;CSV at0.
* Three new figures POSTED. Browser checks exact12rows,3loaded figures,6byte-exact
  local links,real CSV download,12workers'interval nonoverlap/duty/calendar caps,
  keyboard,344/390px,light/dark,older panels andisolated inventory failure.
  General evidence filters/downloads also checked. Seven worker controls pass.
  Windows checkout/launcher and complete hub link closure recorded in the final
  publication_verification.json under output/network_visit_calendar_20261112:
  Windows1867assets byte exact,r44 verified,and841hub dependencies resolved.
* These are per-bin model packing counts,not annual food-supported visits.
  Any missed mandatory collector trip leaves the unchanged annual delivery plan
  uncertified. Collection-first fragmentation is an algorithm restriction;
  greedy failure is NOT proof no schedule exists,abandonment or authority loss.
  Supplied availability/divisible services do not qualify actual staffing roles,
  complete service-job rosters or daily provisioning. No new Earth data/default.
* Entire release1–4/S1–S5 programme revisited in roadmap. Release2 dated size/
  occupation/provider functions and prospective transfer remain open;release3
  partial cereal/resource/scheduling implementation;release4 no calibrated
  default. All actors/unaffiliated/mobile/nonstate,complete diets/household/
  draft work and daily provisioning remain in scope.
* NEXT: before new allocation scores,commit a separate declaration comparing
  alternative packing order on SAME original jobs,providers,crews andworker caps.
  Keep original collection-first results/maps;distinguish bin-level calendars
  from annual mandatory-delivery qualification. No alternative-ordering protocol
  or outcome was added during this publication. Source/phase/measurement and
  mobile/resource dependencies remain open;do not treat scheduling as calibration.
* Full historical evidence publisher still needs omitted private Vidarbha Earth
  cache. This change uses its reviewed direct publisher and registers the hook;
  it does not claim a full historical rebuild.

# Usage-limit checkpoint — push calendar work, publication pending — 12 November 2026

Owner latest instruction: "Almost out of usage, get pushing". This overrides
starting another experiment after the checkpoint. Map/grid work already pushed
through bdd6135c on canonical claude/friendly-turing-43ygeu. Save current calendar
work and resume HERE next session; do not restart or repeat completed maps.

* Calendar declarationbdd6135c BEFOREoutputs. Newpolity/worker_calendar.py and
  build_visit_calendars.py implement original8plans/4parents. Integerfloorstaff,
  50h/bin dutycap,common7*365/12hcalendar;divisiblehome services first;wholecollector
  trips LPT/earliestworker viaheap,then originalcrew1/4visits synchronized atsame
  providers. Alljob/member intervals recorded. No partialcrews,extra visits or
  budget borrowing. Collectionfailure blocks provider/bin visits.
* Sevennewcontrols pass;145freshfiles (144scheduleNPZ+results) BYTEEXACT.
  Independentreview_visit_calendars.py uses sortedlists,notnewallocator,andchecks
  everycollectoridentity/worker interval,originalvisit/provider,crew nonoverlap,
  calendar/duty caps andwholemonthlyledgers. Finalreceipt review.json records
  completion:FINALCERTIFICATEPASSED for all4parents/8cases. Sourcecode mustremainhash-compatible.
* Raw600/300unpackedcollectortrips11630/4825;corrected10932/4214. Packedwithin-bin
  visits raw600crew1/4=147819/137796;raw300=135630/125940;corrected600=156465/145972;
  corrected300=143809/133867. These are GREEDY per-bin packing outputs,NOT annual
  food/visit qualification. ANYunpackedmandatorytrip leaves unchangedannualfood
  deliveries uncertified. Collection-first fragmentation can cause visitmisses;
  no physicalimpossibility,abandonment orauthorityloss inferred.
* Report NETWORK_VISIT_CALENDAR_20261112.md saves complete4+8tables/method/limits.
  PENDING: normalresearchpublisher,calendar/shortfallfigures (postall),downloads,
  browser/mobile/Windows checks andwhole-programme review atpublication. No new
  calendarfigures oratlasoptions created;all previousmaps/defaults unchanged.
  No next alternative-ordering experiment declared orrun. Predeclare separately
  if advancing after publication. Keep release2/S1 datedsize/occupation/transfer,
  complete diets/household/draftwork,dailyprovisioning/providerfunctions and
  S5/allactors/unaffiliated/mobile/nonstate scope open. Fullhistoricalpublisher
  stillblockedbyomittedprivateVidarbhaEarthcache;use reviewed directpublisher.

# Forty target-grid scenarios published; continue worker-calendar audit — 12 November 2026

* Continued after4f592bfe per DONOTPAUSEAFTERPUSH. Canonicalfriendly-turing-43ygeu.
  Griddeclaration4f592bfe BEFOREoutputs. No subagents used/permittedbycurrentrules.
* Five designs b2_p0,b3_p0,b3_p1,b3_p2,b5_p0 timesoriginaleightfood/collection/visit
  scenarios=40. Same originalallocator andreservedpatrolslice;no spare-extension
  mixing/winnerselection. phased_land_targets clips negativephase-anchoredtiles,
  nearestlandtocentre/gridIDtie;alllandarea countedonce;raw/correctedIDs exact.
* Prepare reuses same directed footgraphs/searches acrossdesigns;permonth/design
  target/path packets bound memory/files. Everywalkinglandcell within oldfullnet
  footprint. Independent geometrygroups,allrecordededges/endpoints/costs,new
  eligibilityDijkstra onindependently rebuiltgraphs,scalarallocation,integerjobs,
  allactor/bin partitions/zero-budgetcontrols/fullproviderledgers passall40.
  Same establishedSciPypathalgorithm acknowledged. Fournewgeometrycontrols;
  21focusedchecks pass. Fresh132target/routefiles+6results/fieldfiles BYTEEXACT.
  b3_p0baseline targets/routes/allarrays EXACT;entire15MB NPZbyteidenticaloldfile.
* Phasecompletion spreads0.185–0.265pp acrossthreeDIAGONALphasesonly. Corrected
  600h/crew4 spacing7.36/11.04/18.40km completes254850/163423/66645 of575040/
  260496/97212requests. Densergrid raisesabsolutecompletedcount butlowersfraction
  oflargerworkload. Notnumericalconvergence orreasonselectcoarsestgrid. All40
  reported;normalresearch40rows/4figures/6bytelinks/keyboard/mobile/themes/failure
  pass;alloldmaps/defaults remainintact. AllfourfiguresPOSTED.
* Fullprogramme reviewed:release2 empiricalsize/occupation/prospectivetransfer
  open;3partialcereal/monthlytaskimplementation;4nocalibrateddefault. S1–S5/all
  actors/unaffiliated/mobile/nonstate,completediets/household/draftwork anddaily
  provisioning/providerfunction evidence persist. Historicalfullpublisherstill
  blockedbyomittedprivateVidarbhaEarthcache;direct reviewedpublishersused.
* Windows1862assetsBYTEEXACT,r44launcherverified;832hubdependenciesresolve.
* NEXT IMMEDIATELY aftercheckpoint: committedprior declaration
  calibration/network_visit_calendar_20261112/plan.json. Originaleightb3_p0visit
  plans/fourfoodparents only. Integerfloorstaff each50h/bin,commoncalendar7*365/12
  working-hourcoordinates;servicesA/B equallysharedmandatoryhomeintervalfirst.
  EVERY origin_trips collectorjob useschecked monthlyout/in7dayhours+.25handling;
  LPTduration/origin/serial,earliestavailableeligibleworker. Explicitmandatory
  collectionshortfalls;blockplannedvisitsifany mandatoryjobunpacked. Thenoriginal
  crew1/4plannedvisits,originalprovider,LPTduration/actor/target;chooseearliest
  calendaravailable crew withremaining50h/member,startsynchronizedmaxavailability.
  Dutyhours excludeidle;calendarsincludeit. No overlap/fractionalcrews/movedvisits
  oraddedtasks. Greedypackingfailure NOTproofno scheduleexists. Recordalljob/worker
  intervals/sourcehashes;independentscalar/interval/ledgerreview,freshreplay,
  charts/normalpublication/browser/Windows,wholeplan,pushandCONTINUE.
* Readactualsourcearrays ratherthanoldsummarycounts:rawinputs1034providers,
  corrected1053. Raw600 institutionalstaff values0/100,861active. Raw600has3063143
  annualcollectortrips. Oldmonthlywork raw_paths.npz owner/local_index/out/in match
  parentorigins;originalpointfields supplychosen_cost_hours/served/provider. Split
  collectionschedulesbyparent/month toboundmemory/files. No dailyfood/observed
  availability/institutionalroleclaim evenifconstructive workerpacking succeeds.

# Spare-provider audit published; continue declared target-grid audit — 12 November 2026

* Continued immediately after75e7fd16 map push per DONOTPAUSEAFTERPUSH. Same canonical
  claude/friendly-turing-43ygeu. Spare-assignment declaration75e7fd16 BEFOREoutputs.
* New polity/spare_visits.py leaves alloriginalcompletions/providers immutable.
  ONLYremaining reservedpatrolslice funds originalcapacity-unmet pointtasks on
  checked sameactor,crew-supported routes. Sortpending bymincrewcost/actor/target,
  choosecheapestcurrentlyaffordableprovider once. No reroutingoriginals,borrowing
  collection/services/grossunusedhours,crossbins orglobaloptimumclaim.
* All8cases independentlyscalar/routecost/request/wholeproviderledgers reviewed;
  freshresults/fields BYTEEXACT. Sixnewmeaningfulcontrols,17focusedtotal pass.
  Raw600crew1/4 additions414/1087;raw300233/709. Corrected600297/1117;300192/795.
  Overallcompletion +0.07–0.43percentagepoints. Onepersoncrews recover19.7–22.8%
  oforiginalcapacitymisses;fourperson4.9–6.9%. Unreachable/initialcrewgates unchanged.
  Feasiblelowerbound,remainingmisses NOTprovedunavoidable. Alloriginalmaps intact.
* Normal research8rowtable/1chart/5bytelinks,keyboard/344/390/themes/inventoryfailure
  pass. ChartPOSTED. Report NETWORK_VISIT_SPARE_ASSIGNMENT_20261112.md andexact
  results/review/replay/prior-declaration downloads. No mapfamily/defaultadoption.
* Fullrelease1–4/S1–S5programme revisitedinroadmap;release2datedsize/occupation/
  prospectivetransfer open,3 partialcereal/monthlytasks,4nocalibrateddefault. All
  actors/unaffiliated/mobile/nonstate,completediets/household/draftwork anddaily
  individualroster/provisioning/providerfunction evidence remainopen.
* NEXT aftercheckpoint: calibration/network_visit_target_grid_20261112/plan.json
  committedBEFOREoutputs. Five designs:b2_p0,b3_p0,b3_p1,b3_p2,b5_p0. Clippedtiles
  startatnegativephase;nearestlandcenter lowestglobalIDtie,coveralllandexactlyonce.
  All8parents/originalassigner for40cases;NOspareextension so grid effects isolated.
  b3_p0exactoriginaltargets/routes/allocations mandatory. Reuse monthlyfootgraphs/
  searches acrossdesigns,recordpaths inpermonth/design packetstoboundmemory/files.
  Independentreview/freshreplay,all40results,phase/spacing charts andpointcomparison
  figures,normalresearch/browser/Windows,wholeplan,pushandCONTINUE. Spacingchanges
  taskdensity,notpure numericalconvergence;phase probespointgeography. No winner
  selection/default ornewmapfamily withoutseparatedeclaration.

# Conditional walking point-visit maps ready; continue spare-provider audit — 12 November 2026

* Continued after9c3e7420 per owner DONOTPAUSEAFTERPUSH. Canonical branch
  claude/friendly-turing-43ygeu. The9c3e7420 duty protocol preceded all outputs.
* Eight raw/corrected ×600/300farmhours ×crew1/4 cases use SAME threshold-checked
  open120k-load parents. Fixed27,843landtargetIDs match across climates;~11.04km
  grid. Conditional one task per retained actor/point/bin,not observed demand.
  Walking-only graphs preserve original roads/tracks/seasonal costs,exclude all
  ferries/sea/river auxiliaries. Every eligible land cell within old full-network
  footprint;recorded two directed legs +on-site work pass ration limits.
* ONLY parent work_secondary_hours[0] funds whole visits. Collection/services
  unchanged;no borrowing unusedgross orotherchannels. Sameactor cheapest initially
  affordable provider assigned once;each provider rations cost/target sorted tasks.
  Independent reviewer imports neither new selector nor allocator:targetgeometry,
  every recorded directed path edge,endpoints,costs,scalar assignment,integer
  tasks,actor/target/bin partitions,zero-budgetcontrols andfullmonthlyledgers pass.
  Freshraw/correctedpathJSON/NPZ plusresults/fields BYTEEXACT.11focusedtests pass.
* Corrected600h completes179097/260496crew1 visits(68.8%),163423crew4(62.7%).
  Corrected300h157726/144383. Raw600h171885/155572;raw300h150501/136787,denominator
  258696. Most unmet tasks lack an eligible walking route under these assumptions;
  crew4 exposes more provider competition. Spare hours coexist with unmet tasks.
* Eight optional POINTmaps in existing Supply-supportedreach selector;no filled
  territorialblocks. Three map/chartfigures POSTED. PerproviderCSV hasmonthly
  completed visits andreserved/used/unused patrolhours;pointCSV retainsallrequested
  actor/points,fourbinmasks andchosenproviderindexes;fullfields downloadable.
  Eight maps/exactCSV+point downloads/five packetfamilies/reload/344/390/themes/
  optionalmanifest,parent,gridfailures pass;older32seededoptions pass;normal
  evidence8rows/3figures/8byteexactlinks/keyboard/mobile/themes/inventoryfailure
  andgeneralfilter/downloadfailure checks pass. Windows1853assetsBYTEEXACT,r44
  launcherverified;activehub816localdependenciesresolve. Oldmaps/defaultspreserved.
* Full release1–4/S1–S5programme reviewed in roadmap. Release2 empiricalsize/
  occupation/transfer open;3 partialcereal/monthlyconditionaltaskimplementation;
  4 no calibrateddefault. Individual dailyrosters/provisioning,datedproviderroles,
  completediets/household/draftwork,allactors/unaffiliated/mobile/nonstate persist.
  Full historicalpublisher stillblocked by omittedprivateVidarbhaEarthcache;
  direct reviewedpublisher preservesalloldpanels,nofullrebuildclaim.
* NEXT IMMEDIATELY aftercheckpoint: committed declaration
  calibration/network_visit_spare_assignment_20261112/plan.json. Keep original
  servedtasks/providers immutable;use ONLYremaining patrolhours toaccept original
  capacity-unmet tasks fromspare sameactor providers. Independentlycheck/replay,
  diagnosticchart/normalpublication,wholeprogrammemonitoring;pushandCONTINUE.
  Feasible additionalvisits are a lowerbound,notglobaloptimum. Target-grid
  sensitivity follows. Originalpointmaps stayunchanged unlessseparatelydeclared.

# Threshold-checked map versions ready; continue with actual duty destinations — 12 November 2026

* Continuedafter354f9a52push,perownerDONOTPAUSEAFTERPUSH. Seededprotocol354f9a52
  BEFOREoutputs. Canonicalfriendly-turing-43ygeu. Oldmodel/writer BYTEUNCHANGED.
* NEWpolity/settlement_seeded_dispatch.py:64residentgridplusEXISTINGstaffactivation
  seed(100staff+50civilian),24refinements towardnextgrid,thenmergedpoint/fullfood/
  work/sourcegates and40finaldispatchrefinements. No newfitparameter/globaloptimum.
  Versionedadapterscopeseffectiveclassperworker,restoresfactoryonfailure,hashesall
  actualcodeandbothdeclarations;old16outputs/producersremainvalid. Meaningfulunit
  testrecovers15.0–15.1personstaffedbandmissedby64grid;factoryfailuretestpasses.
* All16cases independentlyreviewed:population,ruralfield/reapingwork,threefood
  recurrences,originintegertrips,monthlyhours,secondaryrequests,oldresidentcontrols
  ANDindependentlyreconstructedthresholdfeasibility/seedselection/overlap. Source
  foodgatepassesallpositivecases.16freshresult/fieldpairsBYTEEXACT.60focusedtests.
* All8open activeflagsAND18actor/cell/binmasks EXACToldfoodsets. Raw600/300sources
  861/725,corrected889/755. Corrected300/120k=282044.846934townpeople;raw275447.276027.
  Corrected300/60k236034.648262;raw226104.287230. Original600pop stable<.0001.
  All8closedcaseszero. SourcecountlosswasNUMERICAL,notphysicaldecline/authorityloss.
* Newseparate data/settlement_dispatch_seeded.json+dispatch_seeded/packets,distinct
  dispatchv2...IDs. Existingselectors exposeThreshold-checkedfood+collection first
  amongexperimentals. Originalfeedback/coarsepacketfiles/defaults untouched.
  Earlierworknotesexplicitlywarnnarrowrangemisses;newnotesshowboundarycheck.
* Newraw/correctedmapfigures+scenariochartPOSTED;reportSETTLEMENT_DISPATCH_SEEDED_
  20261112.md andnormal16row/3figure evidencepanel,withsearch-errorhistoryretained.
  32newmapoptions/exactCSV/monthlywork/celldownloads/fourfamilies/reload/344/390/
  light/dark/3failurecases pass;sourceindexnoall-v2disablefromoldprefixchecks.
  Previous32coarseand16feedbackoptions/CSVs/failuresalso pass;normalnewpanel8
  bytelinks/16rows/3figures/keyboard/mobile/themes/inventoryfailure pass;general
  inventoryfilter/download/paginationpass. Windows1826assetsBYTEEXACT,r44verified,
  activehub807localdependenciesresolve;88original/base/feedback/coarsefilespreserved.
  Actualnetworkpoint-visitprotocoldeclaredBEFOREanynewtarget/cost/taskoutputs.
* Entireprogramme reviewed inSETTLEMENT_CONTROL_ROADMAP_20261110.md. Release2
  empiricalsize/occupation/prospectivetransferopen;3partialcereal/work;4nocalibrated
  default. S1-S5/allactors/unaffiliated/mobile/nonstate,complete diets/household/
  draftwork andproviderfunctionevidence persist. Neither knownseednoruniform
  dispatchfamilyprovesglobaloptimum;staff-onlycollector assumptions explicit.
* NEXT IMMEDIATELYAFTERCHECKPOINT: predeclareactualnetwork duty targetpoints and
  roundtripcosts;chargevisits ONLYtoSAMEalreadyreservedpatrolhoursslice,notfresh
  staffbudgetsorcollection/servicehours. CurrentcoloredmapsarePOTENTIALtravel
  access,notactualvisiteddestinations/fundedpatrolcoverage/authority. Preserve
  unknownmobile/nonstate/unaffiliatedscope andmissionassumptions;continueafterpush.

# Finer grid finds missed staffed branches; implement declared correction — 12 November 2026

* ContinuedIMMEDIATELYAFTERmapmilestonepushd302ac74,perownerDONOTPAUSEAFTERPUSH.
  Canonicalfriendly-turing-43ygeu. Searchprotocol includedind302 BEFOREauditoutputs.
* Fourcentralopen120kloadcases:64vs32intervals,same24/40refinements. ALL396overlap
  arraysBITEXACT.600hchanges<.0001people,ZEROsourceflags.300hfinergrid recovers10
  sources eachclimate:raw710->720,corrected743->753. ExplicitEXISTING150staff
  activationprobe finds5more raw/2corrected fine-zero feasible sites. Probe150±1e-6
  alluppereligible sitesretained;notresidualselected. Largestfinechange153.836/
  156.343people. SOURCELOSSESINOLD300MAPSWEREPARTLYNUMERICAL,NOTphysicalimpossibility.
* Independent16completefine/probe recordscheckoriginpeople/work,rural/export/town
  recurrences,integertrips/monthlyhours/sourcefood;allpositivefinecasesalso pass
  originalsourceaudit. Freshresults/fieldsBYTEEXACT. Old16mapsandallsourcehashes
  preserved. Newreport SETTLEMENT_DISPATCH_SEARCH_20261112.md,normalresearchpanel
  andexplicitcorrectionwarningontheoldmapsevidence. ThisisnotnewEarthskill.
  Searchpanel4rows/5workinglinks/keyboard/344/390/light/darkpass;Windows1768
  assetsBYTEEXACT,r44verified,798hublocaldependenciesresolve.
* NEXT threshold-seededsolverdeclaredcalibration/settlement_dispatch_seeded_20261112/
  plan.jsonBEFOREnewseededscores.64grid+explicitexistingstaffactivationpoint,
  24refinementsfromnewseedtonextfailedgrid;recomputeeveryfood/work/sourcegate.
  Newsubclass/versionedartifactskeeporiginalDispatchFeedback/builderbyteunchanged;
  distinctoptionalmapversion,notquietlyoverwritingold16maps. Runall16cases/review/
  replay/plots/normalatlas/browser/Windows,thenCONTINUEafterpush.
* Entireprogramme reviewedagain;release2empiricalsize/occupation/transferopen,
  release3partialcereal/resourceimplementation,4nocalibrateddefault. FullS1-S5,
  actors/unaffiliated/mobile/nonstate remain;actualgeographicpatrolwork,nextafter
  searchcorrection,stillunqualified. Datedroles/complete diets/household/draftwork
  andalternativecollectorpopulationbudgetsremainopen.

# Joint dispatch/collection/resident maps; continue after pushing — 12 November 2026

* Owner explicitly says CONTINUE,DONOTPAUSEAFTERPUSHING. Push isonlycheckpoint.
  Canonical claude/friendly-turing-43ygeu. Declarationde42d1c3 BEFORE16jointoutputs.
* NEWpolity/settlement_dispatch.py wraps originalCerealFeedback withoutchanging
  itsproducer. EVERYtrial recomputes ruralpeople/work/cereal/meals and workcaps
  uniformcatchmentdispatchwithintegertrips.40workrefinements,old33residentpoints+
  24refinements;final40foodrefinements removeoverdelivery. Actualorigin/export/
  destination inventoriesand SAMEplan feedexistingmonthlyshared secondaryduties.
*16cases:raw/corrected,farm600/300h,load60000/120000kcal,allopen/3binsclosed.
  Samefinitepeople/food/path/freight/store/loss/delay,600staffh/year,7walkh/day.
  Suppliedscenariofamily,NOTglobaloptimizer/empiricalsize/authorityqualification.
* Corrected600/120kopen:378280.833townpeople/889staffsources;fixedaudit95358.736/368,
  oldfood419264.390/889. SAMEfinalruralallocationreference957.424Bdepartedkcal->
  363.569B,zero destinationunusedfood;collection22.172M/53.340Mstaffhours.
  Corrected300:313740/755oldfood->280212/743,access5.551->5.492bins. 600source
  footprintsunchanged,sizesshipmentschange. All8closedcaseszero under90daystores.
* Independentpopulation/work/monthlyinventory/referenceexport/trip/hour/request/
  oldresidentcontrol checks passALL16. Source-food audit additionallypasses every
  positivecatchment. Sixteencase results+fieldsBYTEEXACTfresh. Residualcomparison
  usesactualtermroundoffbound,oldjointbalancegate unchanged. Outsidepeople preserved.
* ReusedEXACToldsourcefootprints;independentlyassembledall18actor/cell/binmasks,
  originalall-source reference exact. ThesearePOTENTIALtwo-waytravel footprints,
  NOT actualgeographicpatrolstaffing. No newclimate/sites/tracks/data ordefault.
* Newoptionaldata/settlement_dispatch.json +dispatch/packets;oldfeedback/ andall
  originalpackets/mapfiles preserved. ExistingSettlements/Supply-supportedreach
  selectors+8cases/climate behindExperimentals.10readouts/worknote,monthlyworkCSV,
  percasefielddownloads. Newoptionalpacketfailureisolated;all3packetfamilieswork.
* Threefiguresposted(raw/correctedmaps+scenariochart),normalresearchpanel16rows,
  reportSETTLEMENT_DISPATCH_20261112.md.32newmapoptions/exactCSV/fielddownloads,
  switching/reload/344/390/light/dark and3failurecases pass.56focusedmodel/evidence/
  launcher/package tests pass;notfullsuite. Oldprivateglobalcache stillomitted;
  nofullhistoricalbasepublisherclaim. Standardnewdirectpublishers used.
  FinalQA:previous16feedbackoptions/CSVs/failures retained,newnormal evidence9
  localbytelinks/16rows/3figures/keyboard/mobile/themes/failurepass;generalpanel
  filters/downloads/paginationpass. Windows1764assetsBYTEEXACT,r44launcherverified;
  activehub793localdependenciesresolve. SearchcheckdeclaredBEFOREnewauditoutputs.
* Wholeprogramme reviewed inSETTLEMENT_CONTROL_ROADMAP_20261110.md;Release2open,
  3partialcereal,4nocalibrateddefault;fullS1-S5/allactors/unaffiliated/mobile/nonstate.
* NEXT IMMEDIATELYAFTERCHECKPOINT: declare64vs32residentintervals onfourcentral
  open/largerloadcases plusEXPLICIT150totalpeople staffactivation probe. Known
  discontinuitycanhidefeasibleislands;certifyoverlapandanyrecoveredpositivesbefore
  inferring physical/sourceimpossibility. Preserveoriginal16maps. Thenactual
  networkduty-destination work anddispatch-familylimits;datedempiricalsize/role/
  occupancy/prospectivetransfer andcomplete diets/household/draftwork remainopen.

# Monthly collection, patrol and services share one staff-hour budget — 12 November 2026

* Continued afterhousingmilestonea00c1140;canonical friendly-turing-43ygeu only.
  Workprotocol7ccd5891 committed/pushedBEFOREnewpaths/workoutputs. No newEarthdata.
* NEWpolity/monthly_work.py prices integercollectortrips against originaldepartures,
  two-waypathdays,7walkinghours/day,.25handlinghours,and60000/120000kcal/load supplied
  stressunits. SAMEinstitutionalresidents supply600annualhours split12;allopen or
  zero-basedbins6/7/8closed. No rural/civilian/newstaff,animalwork or freetransport.
* prepare_monthly_work.py reproducesoriginalnodes/localorigins/owners/12accessmasks
  EXACTforbothclimates. Newparentedge/timepackets retained;no town/track/climatesolve.
  Fourcentral7.5%foodcases(raw/corrected,farm600/300h),2loads,2profiles=16cases.
* Wholeyearworkqualification requires originalsourcefoodgate ANDcollectionfits
  EVERYmonth. ReservecollectionONCEthenrationpatrol14h/session andtwo neutral
  servicechannels1/2h/request together. Unsupported/unreachable/capacityunmet and
  unusedhours explicit. Nevercutshipmentswhileclaimingoldfedresidents;refused
  fixedcasesarenot newpopulations,famine,zeroinstitutions or authoritymasks.
* Corrected600farmh:368/889staffsitespass at120000kcal/load,72at60000. Collection
  shortfalls16.85M/63.88Mhours. Allthreeclosedmonthprofilesrefuseeveryfixedcase.
  Corrected300hpasses724/755atlargeloadbecauseoriginalexportsarelower,notnewwelfare
  skill. Fixedshipmentsmayoverdeliverunusedfood;refusal doesNOTprove fewerresidents
  necessary afternewdispatchallocation. Largerloadqualifiedcaseswouldoverspend
  50770hoursifsecondarychannelsindependentlyreusedfullsparebudgets;newpoolprevents.
* Independentscalarreview:463992ancestorpathbins,1855968origintripbins,200352
  providerbins;all16cases/actorandunknownaffiliation/requestledgerschecked. Sixfresh
  files(results,fields,bothpathNPZ/JSON)BYTEEXACT.69focusedmonthly/service/feedback/
  resident/housing/launcher/package tests pass;notfullsuite. Originalfood/people/
  staff/modelpacketsunchanged;noactualpatrolfootprintsornewdefaults.
* Newreport SETTLEMENT_MONTHLY_WORK_20261112.md;chartpostedinchat. Normal evidence
  panel16rows/downloads plusbasepublisher/packagehooks. Fullhistoricalpublisher
  stillrequiresomittedprivateEarthcache;newdirectpublisherpreservesoldpanels.
  FinalQA:9newbytedownloads,oldhousing7+9links,generalfilters/pagination/failure,
  keyboard/344/390/light/darkpass;Windows1706assetsBYTEEXACT,launcherverifiesr44.
  Activehub784localdependenciesresolve. No backgroundnumericaljobleft running.
* Entireprogramme reviewedagain in SETTLEMENT_CONTROL_ROADMAP_20261110.md:
  release2empiricalsizes/occupation/prospectivetransferopen;3partialcereal;4noadopted
  default. S1-S5/allactors/unaffiliated/mobile/nonstate scope remains.
* NEXT jointsolverdependency:collectionhoursANDselectabledispatchvolumesINSIDE
  resident/ruralwork/grain/storagefeedback,withsamefoodsourcegates. Avoidwasteful
  fixedshipmentsbeforeinferresidentreductions;alternativecollectorsmustpartition
  SAMEfinitepeople/work. Actualnetworkprovider/patroldestinations,datedroles,
  complete diets/household/draftwork andmobileoccupancyremainopen. No newindependent
  utilitymapfamily. Datedhousingmeasurementacquisitionstaysopen,separately.

# Province-blocked housing density comparison — 12 November 2026

* Resumed latest remote2179335e,not stale local a59cf567;checked out canonical
  claude/friendly-turing-43ygeu. Owner requests continuing development.
* Declaration0161dae2 committed/pushed BEFOREscores. Three equal-city-weight
  log sampled-property-density models,leave-province-out. All50cities/23provinces;
  predeclared>=1%26cities/16provinces;>=10%11cities explicitly unscored because
  a held-province fold leaves<10trainingcities. Allsource records retained.
* Allcohort areaMAE.493316->.451165,provinceMAE.538533->.487090;15provincewins/8losses.
  Medianfactor WORSENS1.5061->1.5244. Coverage adds nofullcohortaveragegain;its
  coefficient changes-.008547 to+.118668 on>=1%cohort. No universal/scaling/adoption
  claim. AllAD150gates unchanged,no censuszeros or requests sent to allocator.
* Independent scalar normal-equation review:228predictions,117fits,234training
  coefficients,684household-unit checks; fresh results.json BYTEEXACT.29focused
  housing/launcher/package tests pass. PriorPDF50rows/150fields rechecked. Raw/
  corrected atlasfood/model bytes and previous preparation/review/replay unchanged.
* Newreport SETTLEMENT_HOUSING_DIAGNOSTIC_20261112.md and chart postedinchat.
  Normalcollapsed evidencepanel6rows/7byteexact locallinks;keyboard/344/390/light/
  dark/optionalinventoryfailure pass. Previoushousing9links and generalfilter/
  pagination/download/failureUI pass. Publisher/package hooks wired. Staged
  Windows-style checkout1699assets BYTEEXACT;standardlauncher verifies r44.
* Fullhistoricalbasepublisher hits omitted PRIVATE output/land_people/earth/
  earth.npz inoldVidarbhapublisher;cannotclaimfullsource rebuild. Restored oldpage/
  registry then applied newdirectpublisher;allpreviouspanelsretained. No invented
  global replacement. Originalcataloguelinks404/ORA403;no cityjoin certificate.
* Wholeplanreview saved in SETTLEMENT_CONTROL_ROADMAP_20261110.md. Release2still
  open,3partialcereal,4nocalibrateddefault;S1-S5/allactors/unaffiliated/mobile/
  nonstate remain. Furtherdensitytuning cannot replace datedphase/extent/sampling.
* NEXT concreteimplementation: declare monthly collection/patrol/service claims
  against SAME supported cohorts andhours,not a fresh fullstaffbudget peractivity.
  Retain origin grain/population/food gates,unsupportedprovider andunmetwork;all
  rates remain suppliedscenarios. Datedhousingacquisition stays separate/open.

# Usage pause: reviewed housing evidence and living whole-plan checkpoint — 12 November 2026

* Owner asked to tie up and commit/push for now due usage. No new experiment or
  background simulation is left running. Canonical branch friendly-turing-43ygeu.
* Owner also requires revisiting ENTIREplan after EACHcompleted step and expanding
  as needed. Saved authoritative live review/queue and whole-plan reviewlog at
  reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md; read it at EVERYcontinuation.
  Full release1–4 and S1–S5/allactors/unaffiliated/mobile/nonstate remain in scope.
* Finer scan complete,pushed8745b931:132overlap arrays exact,max0.000294719people
  change,zero source switches; independent food/work,fresh replay,browser and
  Windows1688assets pass. Original eight feedback scenarios/maps unchanged.
* Housing preparation declared8745b931,source-access amendment fef3e9e8 BEFORE
  table extraction. Original2017authorlink404,publisherPDFreturnsHTML;original
  pinnedHansonworkbook404. No false claim these were recovered. Open2023primary
  PDF pinned648928e26e1694303ea56251c4ea5afae3551ed2e51072e4630587fe2903479b;
  supplementaryCSV403. Normalized licensedTable2 now retained under data/source/
  roman_housing_2023,50rows not original52. Authorcitykeys,no coordinates/fuzzyjoins.
* New polity/settlement_size_evidence.py returns conditional sampled-density
  population at declared household size; refuses unresolved/mismatched phase,
  unverifiedrepresentativeness/extent before year-specificcalibration. Missing
  endpoint not continuousoccupation. No annualfit,labelimputation or defaultchange.
* Source50rows/150numericfields all matchPDF,150conditional3/5/7household scenarios
  independentdecimalchecked;18focusedtests pass; freshresults BYTEEXACT. Source
  page visually reviewed. Median investigatedfraction1.1108%,24below1%,39below10%.
  Three explicitAD150exclusions(Calleva/Verulamium/Corinium),47phaseunknown;all50
  stilllacksite-representativeness/contemporaneous-extentcertificate. ZEROeligible
  means unresolvedmeasurement,not zeropeople. NoCountyPOP/cityarea-to-census shortcut.
* New sizeevidencechart postedinchat;report SETTLEMENT_SIZE_EVIDENCE_20261112.md.
  Normal evidence panel/downloads and basepublisher/package hooks added. Models
  unchanged. Final QA:23focused size/launcher/package checks pass;9served local
  links byteexact,keyboard/mobile/light/dark pass;Windows-style1695assets byteexact
  and standardlauncher verifies r44. Receipts under newoutputfolder.
* NEXT per liveplan: phase/extent/representativeness and authorcitykey joins before
  year-specificsizefit; if a mixed-period diagnostic is worthwhile,freeze groups,
  baselines/metrics/exclusions BEFOREscores and labeldevelopment,notAD150validation.
  Keep existing finitepeople/ruralworkers/grain/food/staff/reach consumer. Full
  diets/draft/household/collection/patrolwork and actualmobileoccupancy remain open.
  Never call sourceprep a calibrated fantasyrelease or repairedVidarbhatransfer.

# Finer cell-feedback scan completed — 12 November 2026

* Continued after061e6ef8 was pushed. Committed scan declaration preceded outputs.
* Four7.5% cases doubled intervals32->64 with same24 refinements. All132 overlap
  feasibility/source-support/destination-unmet arrays BIT EXACT. Largest total
  delta0.000294719people, no site changes1person, ZEROsource flags changed.
* Independent final work/monthly food and positive source-food audits pass;
  fresh results.json/fields.npz BYTE EXACT. No original scenario/map/default changes.
  This is tested-grid robustness, NOT proof no narrow feasible islands or optimum.
* Continuing actual resident-size evidence: inspect housing-derived observations
  and occupation/date provenance before treating derived-area estimates as labels.
  Current shared ledger remains partial cereal; release2/S1–S5/allactors retained.

# Actual cell population/work/food feedback now feeds optional settlement and reach maps — 12 November 2026

* Owner explicitly requests continuous development after pushes. Protocol a59cf567
  was committed/pushed before actual cell-feedback outputs; continued directly.
  Only canonical branch claude/friendly-turing-43ygeu is maintained.
* Current r44 raw/corrected inputs reconstructed from PUBLISHED packets, not old
  Nov5 production caches. Administrative density exact; existing local foot owners
  EXACT, all12 parent-forest outward/return months rebuilt. Local origins19371/
  19295; populations5.691M/5.675M from full reference53.120M/53.429M. Outside
  people stay rural. Harvest any-land and transport majority-land masks both
  checked exactly,3142partial coastal cells retained under their own rules.
* NEW polity/settlement_feedback.py changes remaining workers ANDrural meals on
  every relocation trial.40%workers;600/300annual listed hours;30-day reap within
  same annual budget. Actual net crop energy, rural/export stores, path access,
  source departures/delivery loss/delay and destination stores feed SAMEplan.
  Deficit origins export zero; anypositive town requires whole origin catchment
  rural support. Earlier audit_origin_food additionally passes positive groups.
*8declared cases: raw/corrected x600h shares5/7.5/10% +300h7.5%. Corrected7.5%600h:
  419264townresidents/889conditional sources; frozen-rural reference421484/894.
  300h313740/755. Local source deficits163corrected/185raw at600h remain visible,
  outside deficits also retained. NO global/all-diet or real-famine qualification.
* Nonmonotone feedback:33fraction points +24bracket refinements per independent
  site. Final points independently certified; NOT global optimality. All8JSON+
  cellNPZ byte-exact fresh replay. Direct independent work/monthly inventory
  review passes, including per-origin shipments and whole-world population.
  Original annual-throughput convergence tolerance preserved; source float32
  area arithmetic independently reproduced.107model checks +5launcher/package pass.
* Same audited cohorts now select seasonal two-way reach. Reconstructed town/
  tracks plusALLsources reproduce published actor/cell/season reference EXACTLY
  in both climates. Independent footprint assembly passes all18actors. Corrected
  600h7.5% access6.382bins vs6.413frozen-rural;300h5.551. Footprints cached with
  hashes. No population-to-power multiplier, new affiliation or changed defaults.
* Separate optional data/settlement_feedback.json+feedback/ packets; ORIGINAL
  atlas.json,settled_reach.json and original model/grid GZ bytes preserved. Active
  Earth UI Experimentals exposes4new scenarios perclimate in SAMESettlements and
  Supply-supported reach modes. New packet cache permits safe family switching.
  Readouts include origin budget/source-food gate; same ledger/CSV/cell audits.
  Evidence badge explicitly Experimental,not inherited old partly-tested claim.
* Both new figures reports/figures/settlement_feedback_{maps,scenarios}_20261112.png
  posted in chat. Browser all16mapoptions, exactCSV/cell downloads, reload/mobile/
  dark/failure isolation passes; original22cases/792CSV rows and v2/v2.1 defaults
  regressions pass. Normal evidence page new8row panel/directmaplinks and methods.
* NEXT after this milestone push: already-declared scan_check.json freezes4central
  7.5% cases,64intervals vs32, same24refinements. Require all33overlap points EXACT,
  report any hidden feasible branch/changes; do not silently alter original8maps.
  Then empirical resident-size/occupation and complete resource calibration remain
  open. Release2not complete; release3shared ledger advanced as partial cereal
  scenarios; release4new calibrated default pending. FullS1-S5/allactors/mobile/
  nonstate scope persists. Keep developing after pushes; no metadata-only detour.

# Finite resident consumer and source-food gate — 12 November 2026

* Continued AFTER pushing placement milestone702a6dfe, per owner instruction.
  Single canonical branch remains claude/friendly-turing-43ygeu. Both new map/
  chart figures from the224-placement comparison were posted in chat.
* New polity/settlement_residents.py WRAPS unchanged SettlementPlan allocator.
  Origin people and a caller-supplied transfer share fund civilian ANDstaff
  residents once. One owner per origin; unassigned/unused people remain rural.
  Zero/tiny budgets cannot create a minimum town or staff. Population partition
  and destination seasonal food are checked. No old producer sources changed.
* audit_origin_food hard gate binds declared origin departures to destination
  arrivals (retention/delay), protects meals of returned rural people, and closes
  one grain ledger including stocks/losses/unused food. Mutated records refused.
  Large shipments cannot hide rural meals through loose relative tolerances or
  floating-point range. Source grain must already reflect remaining field work.
* build/review_settlement_residents.py:20existing atlas food cases, shares5/7.5/10%
  =60sensitivities. Reference catchment people are SCENARIO envelope, not measured
  inhabitants. Market IDs disjoint. All20old allocations replay with ZERO civil/
  staff difference. Independent scalar caps review62,610site/scenario records.
  Fresh results.json/fields.npz byteexact.94focused tests pass,not fullsuite.
* Corrected joint365 at7.5%: town total812545.873 ->812204.400; conditional sources
  1011->1010. Rural remainder40263180.758 fromsame41075385.158referencepeople.
  At5% newtown801473.333. These are bookkeeping sensitivities,NOT newcensus fits.
* Manufactured100-person rural/town examples balance grain (with/without20% freight
  loss) below1e-6kcal; insufficient ruralmeals rejected. Actualatlas cases STILL
  use old-arrival rural-food claim: ruralfood/production/collection/reach NOT
  recomputed and actualsource-food gate NOT qualified. Do not adopt these as the
  normal numeric map. Expose this gap plainly; manufactured proof is not Earthfit.
* Normal evidence page newcollapsed residentpanel6rows/5downloads, retained joint
  and old source panels, publisher/package wired. Browser/mobile/dark/download/
  optional-inventory failure checks passed. Production source packets unchanged.
* Final QA: resident+joint browser panels, mobile/light/dark/failure UI pass;
  Windows-style checkout1652byte-exact assets; active hub750local dependencies
  resolve, including5new resident files. Both fresh outputs byteexact.
* NEXT actual integration: recover compatible CELL origin people, remaining field
  work and net crop harvests; recompute rural meals and collection under relocation.
  Solve feedback between fewer town people ->more rural needs ->less export;
  refuse unresolved/nonconverged cases. Pass source-food gate before SAMEplan feeds
  staff/reach. CountyPOP/footprint imputations still not resident-size truth.
  Release2stillinprogress,3fantasyrebuild/4numericpublicationpending;allactors,
  unaffiliated/mobile/nonstate and S1–S5 remain. Continue after push, no new
  independent utility map family. Details SETTLEMENT_RESIDENTS_20261112.md.

# Complete-input joint placement comparison finished — 12 November 2026

* Resumed from canonical remote4c6af479 after fetching the newer work; local Nov5
  snapshot was stale. ONLY maintained branch remains claude/friendly-turing-43ygeu.
  User explicitly requests continuing after commits/pushes and posting every map.
* Ran the already-declared224placements:21variants x5seeds x2pools,10old-clipped
  history ablations and4paired controls. Sources/people/eligibility fixed. Natural
  budgets1239Han/1292Rome, never observed-site counts. Han corrected coverage,
  Rome original paired population control, both checked supported histories.
* Lead remains b1_L450_f0: meanQ .622264 vs fixed18 .570611 and production .392029.
  UniqueF1 .522733Han/.401515Rome; spacingKS .059990/.054013. Fixed18 has higher
  uniqueF1 .592089/.422381. Pareto: b1_L450_f0,b0.7_L450_f0,fixed18_L800. Weight.8
  prefers b0.7; .4/.6 prefer b1. Source-history repair Qdelta only+.000479/+.000462
  on current common inputs. No claim of large new skill or rescued Vidarbha guard.
* New polity/settlement_joint.py, driver/reviewer/plot/publisher/browser scripts.
  Independent dense-distance/min-cost matching replays ALL224metric sets, budgets,
  eligibility, uniqueness, adaptive symmetric/fixed/legacy spacing, ranking/ranges,
  frontier/sensitivity. Fresh224producer replay results+positions BYTE EXACT.
* Exact derived population/history NPZs are committed and verified. This resumed
  checkout omits upstream private output/land_people/earth/earth.npz; input scope
  explicitly records this. No claim raw/global preprocessing rerun; prior source
  certificates remain archived/unchanged. Do not invent a replacement global file.
* Figures reports/figures/settlement_joint_{maps,tradeoffs}_20261112.png posted.
  Normal atlas evidence new collapsed panel6rows/7downloads, all224positions,
  protocol/scores/review/replay; basepublisher/package wired. Browser new+previous+
  general inventory passes344/390/light/dark/download/failure checks.71related
  tests passed. Frozen source/production atlas packets unchanged; r44 active.
* NEXT substantive consumer: finite resident/catchment allocation into SAME
  seasonal-food SettlementPlan. Never add 7.5% town residents or100-person minima
  on top of all existing rural people; cap civilian ANDstaff transfers by one
  origin budget, leave residual rural and unreachable people explicit. Urban
  share remains a scenario; no resident-size qualification from district POP or
  imputed Roman areas. Do not detour into new institution mechanisms.
* Release2(count/location/size) still IN PROGRESS; shared-ledger fantasy rebuild3
  and normal numeric map4 PENDING. All actors/unaffiliated/mobile/nonstate, S1–S5
  persist. No default adoption or fresh/blind claim. Continue after push.

# Supported core histories checked; joint point experiment declared — 11 November 2026

* Source repair/completecount/atlaspublication bbc31fd0 committed+pushed;continued.
  Core-source protocol5136c09e pushed BEFORE newhistoryfields. Only maintained
  branch friendly-turing43ygeu;no oldbranchrecreation,keepgoing aftereachpush.
* NEW polity/core_travel.py excludesunsupportedcoarsenednodes,requirescoveredcores,
  keepsoldcosts/forestshares/coarsen3/8neighbourgeometry.4meaningfultests pass:
  full-support exactoldkernel forfloat32ANDfloat64,unknownwatercorridorblocked,
  unsupportedcorethrows(no nearestvalid rescue). FirstEarthcompatibility run found
  implicitfloat64relief conversion;fixedpreserveactualsourcefloat32mean;A nowEXACT.
* build_core_population_inputs.py cases Aoldglobal,Bonlycorrectedcoastalrelief,
  Ccorrectedoldprefix+regionalNEappend32–48N125–134E,supportnonrectangular,unknown
  excludednotcheapwater. AlloldnodesB<=A,C<=B under1e-7kmguards. Oldarchived800
  histories replay EXACT onbothpoolgridsincloldclippedHanextent. New450/800fields
  cover/connect ALLrequired50349Han/56378Romanlandcells. No pointscore computed.
* Output/core_population_inputs_20261111 distances.npz +han_history/rome_history,
  results/review/replay. HanDchanges[-79.8258,+671.2788]km,mean+6.4708,1564cells
  longer(oldedgeclampingbiasfixed);Rome[-136.3097,0],mean-27.0384. Fixedcosts
  forest2/sea1/relief1;theseareeffectivekmprior,not calibratedoccupationage.
* Independent review_core_population_inputs.py certifiesedgeBellmanbounds and
  tightdescendingpredecessorsforallfinitecoverednodes(positiveweights) across
  2,950,384directedarcs,withoutsecondnewkernelDijkstrarun;bothconsumergridschecked.
  Freshdistances/bothhistoryNPZ/resultsJSON byteexact. Normalatlaspopulation-source
  panelnow includesnestedcorestatus+3downloads,14local links total,browserpass.
* NEXT ACTUALPOINTEXPERIMENT already declared calibration/
  settlement_joint_locations_20261111/plan.json BEFOREANYnewplacements/scores:
  samecompleteHan+oldRomanpopulationinputs,bothcheckedcorehistoryfields;
  commonnaturalproductioncounts,existingeligibility,adaptivec.35/max45km,seeds
  [1,7,19,43,97]. Densitypower[.5,.7,1] inlegacydensityterm;historyL[450,800],
  floor[0,.1,.3,1] withfloor1Lduplicateomitted=21variants;210draws +10oldclipped
  L450power1ablation +4production/fixed18controls=224placements. No observedcount
  budget,parameterselectiononIndia,sourcepointanchors orplanet/climatefit.
  Meanseed/equalpoolQ old .6weight,frontier,weight.4/.8sensitivity;aggregate
  tradeoffsallowed,engineering/accountingconstraintshard. AllpoolsSPENT,noblindclaim.
* NOW stage/commit/pushcorechecks+declaredpointplan,thenRUN224comparison promptly,
  independentreview/plots/normalatlasresearch/pushandcontinue. Do notstallatmetadata
  ornewinstitutiondetour. Sourcepipeline corrections notthemselves new pointskill.
  Count/size release2inprogress;residentallocation/sharedledgerfantasyrelease3/
  normalNUMERICatlas4pending. Fullroadmapallactors/mobile/nonstate unchanged.
  ~56MBfree,no fullZIP/sitecopy. Exactstagepaths only,olduntrackedlogsnotours.

# Population coverage repaired; coastal NoData fixed; complete count replay — 11 November 2026

* Latest pushed source/protocol snapshot e552238f on single maintained/default
  claude/friendly-turing-43ygeu. New source correction/count/publication now ready
  for final QA/commit/push. User explicitly wants continuation AFTER pushing.
* Old ND bug FIX in scripts/land_people_earth.py.wc: honour TIFFGDALNoData tag42113;
  keep valid negative elevations andzero.2regressiontests. Existing physicalclimate
  rotclimate.earth._wc already handled tag;bug affected food/arable/relief harness,
  NOT a new atmospheric/rainfall skill gain. Allworldr44/ledger defaults unchanged.
* Private regional sources ready(data/cache/earth_population_extension_20261111):
  WCmonthly tavg/prec/elev localarchives;Tmin/Tmax downloaded bounded192MiB inRAM,
  onlyregionalarrayscached.ETOPO60s 960x840 DODSsourcecoords validatedall8chunks.
  Corrected sourceparser includes bothFloat64maparrays,strictcounts/byte/schema.
  New script prepare_population_extension.py and1parser test;no rawZIPdisk copies.
* Original plan25a83318 +failedoverlap/source/compute artifacts +NoDatacorrection
  protocol e552238f preserved BEFORE newcorrection. Initial1370landcontrolcells:
  T/P/PET/aridityexact,irr diff5.8e-18;5arablefallbackcells mismatch .77. All5 have
  cachedslopeNaN and0fineland;oldglobalrelief32774–32861m versuscorrect6–93m.
  Causeoldwc onlymasked<-1e30,ignoredactual-32768seaNoData. Failedv1 remainsfailed.
* correct_population_extension.py implements2NAMEDguards original8fields/thresholds:
  legacyNoDatafallback EXACTLYreproducesfrozenglobal;correctlydecodedtile EXACTLY
  matchesexplicitcorrectedreference(exceptirr5.8e-18).No loosening/dropcells.
  Global sparsepatch17,903landcells:arable/density1274,capacity1183,relief17903.
  Capacityratiofirst(newarable/oldarable) thenmultiply avoids1ulp churn inunchanged
  cells. OriginalglobNPZneveroverwritten;oldvintage decoder recoverablee552snapshot.
* NEW output/earth_population_extension_20261111/han_corrected_inputs.npz fillsall
  1586missingrequiredcells;128oldcoveredlanddensitycellschangetraceablyfromcoastfix,
  ZEROwithinHanallowedmask.Allotherarraysinclregionalaridity/elev/roads fixed.
  originalinsidepopulation exactlyreconstructs fromglobalbefore correction.
  population_covered flag reflectsoldcoverage plusactualfilledrequiredcells;
  history_covered onlygeographicflag,ALLcorehistoryrequiresrebuildbeforepointfit
  becauseoldglobalrelief changed andoldhistoryclips125E. Do not useforqualification.
* Source review review_population_extension.py:17,903directglobalpatchcells,
  cropcapacityfromoriginalfullformula,21,920overlapfield-cellcases,allinputlineage,
  oldartifactsunchanged. Freshreplay patch/newHan/correctionJSON byteexact.
* count_population_extension.py reusesfrozencountfamilies oncompleteHan +ORIGINAL
  Romanpairedcontrol (Rome populationnotyetpatched;explicitscope).160cases:
  2domains(full_corrected/old_supported_corrected),2blockscales,2responses,5betas,
  separate/sharedscales,2pools. No archived production-rate means innewfit.
  Fullprimary1280Han/1115Romanrecords;allpositive-countblockpredictionspositive.
  Fullrole-specificbeta.5 devHan2.640869/Rome1.867583/mean2.254226;
  beta.7 mean2.297089. Same-domainALLcomparisonsreproducepreviousscores exactly
  (coastchangesoutsideHanallowed);doNOTcallwider-domainvalueaccuracygainoversmaller.
* Count review review_count_population_extension.py:2780blocks,640foldcases,
  8800metrics/all160rows +multiplicity/unchangednonpopblocks. Freshcountreplay
  results/blocks/predictions byteexact. Both replayreceipts underrespectiveoutputs.
* New report EARTH_POPULATION_EXTENSION_20261111 +figures
  population_nodata_correction_20261111.png, population_extension_han_20261111.png
  posted. Publisher publish_population_extension.py wiredbasepublisher/package;
  normalatlasEarthevidence latestsourcepanel5rows/11localdownloads. Hubrefreshed.
* Browsernew+previouscount+generalevidence pass (including344/390/lightdark and
  missingoptionalinventoryUI).136relatedtests +6evidenceaudit tests pass. Fullbase
  publisher initiallycaught PREEXISTINGstaleinventorycrop_model .68 vsactive.60.
  Refreshed VERSIONED output/earth_components_refresh_20261111 (oldledgerpreserved),
  551records,exactlyonevaluechange /single_crop_sown_share .68->.60,no newfit/default
  changes. Basepublisher choosesfreshinventory;alloldandnewpanelsnowrebuildpass.
  Currentdata ledger/CSV +inventory_refresh.json preservecomparison. Hubrefreshed.
* NOW finishfocusedstagedWindows/linkclosure,no fullZIP/sitecopy (~69MBfree);commit/push ONLY
  friendly. ThenKEEPGOING supportedcoretravel rebuild withsameoldcostparameters,
  supported-domainmask(nonrectangularoldglobal+NEtile) ratherthanclamp/unknownsea;
  proveoldalgorithmcompatibility beforepointfit. Correctedglobalpatchreliefmatters
  forcoastaltravelprior. No newholdoutclaimfromspentHan/Rome/Vidarbha.
* Future completepointcomparison mustsupplynewhistorywithnewfoodinputs,distinguish
  countbudget/roles/residentpop,andfeedSAMEpeople/food/staff/controlledger.
  Fullroadmapallactors/mobile/nonstate unchanged;firstmaprelease2stillINPROGRESS,
  release3fantasyrebuild/4normalNUMERICatlaspending. No institutional detour.
  Exactgit-addpaths only;hundredsofolduntrackedlogsnotours. Do not stopatpush.

# Count/size audit finds missing population input, not an ecological zero — 11 November 2026

* User wants continuous work after pushing. Single canonical/default remote remains
  claude/friendly-turing-43ygeu; never recreate ecstatic. Vidarbha transfer was
  committed/pushed55cce3df; count protocol f0b14adb, multiplicity correction4799a588,
  coverage sensitivity3f56dd58 all pushed before their respective corrected fits.
* NEW scripts settlement_counts_earth.py/review_settlement_counts.py and modules
  polity/settlement_counts.py,population_coverage.py. Full results under
  output/settlement_counts_20261111. No fantasy ledger,point,track,staff/control or
  r44 physics changes. Count/size report SETTLEMENT_COUNTS_20261111.md.
* BIG FOUND INPUT BUG: old Earth global output covers0–56N,-12–125E. E.earth_people
  returns density0 ANDcovered=False beyond;Nov10 input preparation ignored covered.
  Han allowedland50349cells:1586missing (128466km²),13sourcecells/13records outside.
  Six99kmblocks positive count/zero P (11records) entirely outside coverage.
  NOT proof no ecological food/local people/administrative seats. Rome all covered.
* Count primary multiplicity recovered from original sources + EXACT old matching:
  raw1294Han/1354Roman,allowed1280/1115records,1264/1085distinctcells. Frozenreal
  arrays alreadynp.unique; initial mistaken record==cell attempt preserved under
  invalid_deduplicated_target_attempt with invalid-unit status,not modelselection.
  Legacy nearest-land rescues14Roman inside records,0Han; explicit inheritedlimit.
* Full_frozen and covered_only sensitivity both retain100/300nominal blocks
  (actual99/297km),all4fixedquadrants,beta[0,.5,.7,1,1.5],role-specific/sharedscales,
  record/distinctcelltargets,all176rows. Fullregionunqualified and retainsinfinite
  losses;no floor/area-only adoption. Covered-only1267Han/1115Romanrecords:
  role-specific beta.5 dev/recordHan2.678864/Rome1.867583,mean2.273223 vsbeta.7
  mean2.316263(1.86%gain),stillcountmass relocation~63.6/50.9%.Sharedcontrols can
  improve more;not retroactively selectednewvalidatedwinner. Cataloguecounts not
  true complete urban census;no observationmodel/independent qualification.
* Resident-size sourceaudit:RomanAD1501354records,862positivearea,492missingarea,
  56exact20/30ha candidates,806otherpositive(not automaticallymeasured/contemporary).
  Oldreaderfillsmissingrankmedians.1338AD150missingenddateflags.CountyPOPdistrict
  population,not seatresidentlabels.All sourceyears/types/adjustmentflagsretained.
* Independent review:2780directblocks,704heldfoldcases,9680metrics,rawsourceunits,
  independentfrozenE.samplercoverage,multiplicity and all176rows. Fresh replay
  results +bothNPZbyte-exact.133relatedtests pass;newcoverageguardtwo tests included.
* New figures counts +population_coverage_20261111 posted(user saw initial plotting
  pool-filter bug then corrected figure;numeric results unaffected). Publisher wired
  basepublisher/package;newpanel5rows/9localdownloads. Browsernew+previous passes
  mobile344/390/lightdark. FinishstagedWindows/linkclosure andpush before next step.
* NEXT ACTUAL WORK:extend missing ecological population inputs,not anotherparameter
  search on zero-filled area. Missing required Han bbox37.5976–42.4898N,
  125.00017–129.03504E. No cached old output/polity_earth/han.npz. Existing source
  global32MBNPZ,WorldClimelev/prec/tavg zips,arable5m2.7MBonly;NOetopo60window.npy,
  NOlocalTmin/Tmax zip. ~87MBfree;do not download120MBarchive to disk/fullZIPsitecopy.
* Feasible next:declare extension BEFOREnewsourcevalues,regional5m tile32–48N,
  120–134E (lat top aligns original4deg irrigation bands). OfficialTmin/Tmax archive
  can be boundedreadinRAM then cacheonlyregionalmonths;ETOPO60s OPeNDAP regional
  subset~3MB. Reuse exactland_people.analyse/FALLOW0.6,slopearabilityparameters,
  distance/HANDirrigation,settlement_fields/centraloccupation. Buildallfieldswithhalo,
  compareoverlap36–44N122–124E tooriginalglobal (awayfromtileandold125Eboundary),
  gatesbeforeusingnewdensity. PreserveeveryoriginalcoveredHaninputcell exactly,
  replaceonlymissingdensity/aridity withqualifiedextension inNEWartifact,never
  overwritefrozeninputs/global. Requireallallowedlandcovered. Coretravelhistory
  alsoclipsold125boundary;countfitdoesnotuseit,butfuturepointcomparison mustnot
  pretendclippedhistoryisfullphysicalextension. Extendhydro/terrainconsistently.
* Firstmap queue:1refs/rulesdone;2count/placement/sizeinprogress;3fantasysharedledger
  and4normalnumericatlaspending. FullS1c/d/e,S2–S5,all18actors/mobile/nonstate scope
  persists. Sourceprivatecoords notGit. Exactgit-add only;olduntrackedlogsneveradd.

# Primary survey transfer completed: candidate fails capture margin — 11 November 2026

* Owner wants continuous work after each commit/push. ONLY maintained/default
  remote branch claude/friendly-turing-43ygeu; never recreate the retired branch.
* Preparation plan 5d7d0b00 and actual transfer protocol d0c65f94 were committed
  before new source records / regional environmental lookup and scores respectively.
  Read calibration/settlement_vidarbha_transfer_20261111/plan.json exactly.
* NEW PRIMARY source Zenodo3670055 v2: 268 AllSites, 134 exact settlement joins,
  all usable coordinates; 82 EH-S yes /41 no /9? /2blank. Independent preparation
  review passed. One religious orphan does not affect settlement cohort. Old failed
  literature catalogue3667657 remains unchanged; shared ID strings not place merges.
* Transfer run output/settlement_vidarbha_transfer_20261111/results.json:
  121/134 inside assigned nominal 13km frames; 13 excluded, never reassigned.
  Primary EH-S:74 records,53 distinct cell-frame units (21/16/16); support passes.
  Natural legacy budgets419(3km),375(9km),not observed-source count fitting.
  FixedL800 mean local percentile .460951 vs leadL450 .469767 (+.008816).
  Fixed capture10km16.6667% vs lead five-seed mean6.25% (delta-.104167): FAIL
  predeclared-.10 engineering tolerance. All24 numerical placement constraints pass.
  No adoption; no fantasy population/food/tracks/staff/control/physics changes.
* Independent review:134 joins,2412 full-grid matches (pyproj/direct sphere vs
  producer projection/KDtree),7290 scalar metrics,24 constraints. Fresh replay
  byte-exact results.json plus4 exact numerical NPZ identities.25 targeted tests
  pass. Do not claim a new full-suite result until run.
* Producer settlement_vidarbha_transfer.py reuses exact frozen allocators/scorer.
  Both3/9km grids common inputs:globalEarthdensity/occupation+annualaridity,
  bilinearWorldClimelevation/nearestfinite land,NaturalEarthrivers,roadszero,
  oldglobalcoretravel. One-cell smoothing changesphysicalscale;coarserglobalaridity
  commoninput limitation;3km does not create 3km climate. Private IDs/coordinates
  only data/cache/vidarbha_survey_2016/transfer_matches_*;public NPZ model-only.
* New figures reports/figures/settlement_vidarbha_{transfer,geography}_20261111.png
  posted to user. Reports VIDARBHA_SURVEY / SETTLEMENT_VIDARBHA_TRANSFER_20261111.md.
  Publisher wired to basepublisher/package; normal Earth evidence panel has6rows,
  all sensitivities/downloads, explicit failed verdict. Hub manifest refreshed.
* IMPORTANT Reba/Modelski AD100-200 already exposed in great_cities_check.py,
  POPULATION_20261023 and population_density_research_20261023. Exposure registry
  corrected. Source freshness never inferred from missing registry entry.
* Four-milestone release queue:1 Earthreferences/rules COMPLETE for release;
  2 count/location/size fit INPROGRESS (regional lead fails);3 sharedledger fantasy
  rebuild PENDING;4 normal atlas publication of new numeric map PENDING. Research
  page publication is not the final map milestone. Full S1c/d/e,S2-S5,all18actors,
  unaffiliated/mobile/nonstate programme persists. Active climate r44 unchanged.
* NEXT finish browser/mobile/link closure/focused Windows-byte QA, commit/push ONLY
  friendly, THEN KEEP GOING: audit count/role and resident-size Earth reference
  support, compare opportunity geography and realization separately. Vidarbha now
  spent; no retuning then fresh-holdout claim. Do not detour into new institutions.
  ~80MBdiskfree: no full portable ZIP/sitecopy. Old untracked logs must not be added.

# Geographic-transfer field source declared — 11 November 2026

* Latestpush2ef81095 verifiedonsinglecanonical/defaultfriendly-turing43ygeu.
  Ecstaticremotebranchretired,don'trecreateit. Userexplicitlywantscontinuationafter
  eachpush;do notpauseatmilestones. Fullfour-releasemilestonespersistonroadmap.
* Runtime/networkchecksread,currentspec36running/unrestricted,noVPN/secrets.
  Workspaceclean;remoteHEAD==local2ef81095. ~108MBfree,no fullbundle/sitecopies.
* IMPORTANTnewhistorysearchFOUNDReba/Modelski alreadyused:research_notes/
  population_density_research_20261023.md and reports/POPULATION_20261023.md.
  Absencefromexposure-registerwasnotproofnew. DoNOTuseasfreshblindsource.
* NEXTplan calibration/vidarbha_survey_20261111/plan.json declaredBEFORECSVzip
  records/modellookup. NEWseparateprimary2016fieldsurveyZenodo3670055(v2),
  CCBY4.0,139013byteSiteRecords.zip,5CSVtableswithSiteCode joins,Northlatitude,
  Eastlongitude,SiteType,SurveyZone,phaseflags. DoesNOTrepairfailed3667657census.
* Onlynewreadme/schema/Zenodometadatareadsofar;old60mastercoords/390censusrows
  exposedthroughpreviouspreparation. CompareactualID/coordinateoverlap explicitly.
  Private readme+SHAatdata/cache/vidarbha_survey_docs_20261111;paperPDFfetchfailed
  boundedPDFcheck,relevantpublisher/searchmethodsread(joAD61),don'tclaimfullpaper.
* Paper/readmedescribe3targetedframesChammak/Mandhal/Pauni,about7.5%area surveyed;
  notcompletecitycensusorbackgroundabsence. SiteType=settlementrequiredforpositive
  contexts;EH-S Satavahanaperiod-compatible,notexactAD200date. Need chronology/
  coverage/unit gatesbeforecomparison. Newrealrecordsnotyetloadedorcounted.
* NOWcommit/pushdeclaredpreparationplan,downloadONLYsmallreadme/recordzip,prepare
  5tables/hash/joins/coordinate/phase/overlapchecks,independentreview. Ifusable,
  freezeactualtransfercomparisonBEFOREmodelscoringandRUNit(no metadata-onlystall).
  Singlefriendlybranchonly. Physicsr44unchanged;fullS1c/d/e,S2–S5/allactor/mobile/
  nonstatescopepreserved. Firstlocation/populationreleaseisthepriority.

# Branch consolidation complete; dated references checked — 11 November 2026

* CANONICALONLY:claude/friendly-turing-43ygeu (existingGitHubdefault). b7809a32
  atomicallypushedallhistorythereanddeletedredundantecstatic-wozniakwith24b0a505
  expectedtipguard. Botholdhistoriesareancestors,nouniquecommitslost. RemoteHEAD/
  branchabsenceverified;localfetch/upstreamrepairedafterretiredrefcausedfetcherror.
* GitHubadminsettingPATCHwas403;usingexistingdefaultcompletedconsolidationwithout
  adminintervention. Launcher/hub/READMEtargetfriendly,verifiedr44releaseunchanged
  inallclimate/settlementidentities;onlybranch/evidencemetadatarefreshed.5launcher/
  packagingtests pass. output/branch_consolidation_20261111/checks.jsonrecordsproof.
* LATESTOWNERasks4remainingmilestonesuntilnewcalibratedsettlementmap:releasepath
  fixedinroadmaptop. Stillmilestone1:Earthrefs+locatedtransferpool/comparisonfreeze.
  Roles/controlS2–S5laternotblanketprerequisitesforfirstlocation/populationrelease.
* f0f3b892scopecomparisonimplemented polity/institution_scope.py+5tests;
  prepare/review/publish_institution_scope.py,report INSTITUTION_SCOPE_20261111.md.
  Output/institution_scope_20261111/results/review/replay. Authorpolicyhashesin
  calibration/institution_scope_20261111/sources.json.5007rows/4675groups,
  independent10014row-policychecks. Explicitvsdocumentedpositive200groups:
  hierarchy0->26(with24numericrows),largestpop4->18(with14numericrows).
  Preserveunknowns/ranges/alternatives. NOTnewmaporfit. Nochosenpolicy/modelscores.
*131tests pass (126settlement/evidence+5launcher/packaging);fresh2artifactreplay
  byteexact,3initialparentartifactsunchanged. Newscopepanel2rows/5downloads,
  basepublisher/packagewired,strongerSeshatdate-prepstatuspreserved. Browsernew/
  previous/general evidence,344/390light-dark,downloadSHA/exposureallpassafter
  restartingstoppedHTTPserver. Server8766currentsession26470. Publisheridempotent.
*196Windowscriticalfilesbyteexact,698activehublinksresolve;normalstandard-library
  launcherverifiedEarthr44andcanonicalfriendlyguidance. FullZIPnotbuiltunderquota.
* NOWcommit/pushONLYfriendly. Thenprioritize
  locatedprospectivetransferpool/frozencomparisonforrelease1,notnewinstitution
  mechanismdetours. Seshatprovidespolityattributesnotcoordinates;alloldlocation
  poolsspent(exposedHan/Rome/CHGIS/Bosker/Pleiades/Domesday),Vidarbhaunready.
  Reba/ChandlerglobalhistoriccitysourceNOTlistedinexposureregister/localsearch,
  possibleSouthAsiatransfercandidate:metadataaudit/protocolBEFOREtargetvalues/
  scores,checkactualoverlap/coveragefirst. Noindependentclaimfromabsenceofregistry.
* Full S1c/d/e,S2–S5,allactors/mobile/nonstate,r44physicsremain;singlebranchonly.

# Single development branch and four-milestone settlement release — 11 November 2026

* LATEST OWNER REQUEST:continue,and consolidatebranches;do NOTkeeppushingboth.
  Canonicalbranch claude/friendly-turing-43ygeu (existingGitHubdefault).
  Fetchedbothremotetips:c851ad63f586f59ac69c0cc4127b8c3e88de7050,0uniquecommits
  eitherway. Localf0f3b892addsdeclaredscopeprotocol,fullydescendedfromboth.
* Triedcanonicalecstaticfirst(24b0a505pushedthere);GitHubdefault-settingPATCH
  rejectedHTTP403 Resource not accessible by integration. Safefallback:useexisting
  defaultfriendly-turing,so noadminsettingschangeoruserinterventionneeded.
  Launcher/hub/READMEbranchguidanceupdatedtofriendly;retireecstaticONLYwith
  expected24b0a5059add3b18c0bfa9fdb691d03d50771c86tipguard+ancestrycheck. Preserve
  history;oldplans/receiptsretainoriginalbranchrefs,don'trewritefrozenprotocols.
  FuturemilestonespushONLYcanonical. Do notrecreateretiredbranchfromoldautodrivers.
* Useraskedhowmanyuntilnewcalibratedsettlementmap:FOURremainingreleasemilestones,
  nowpersistedattopof reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md:
  (1)finish/freezeEarthreferences+transferpool,(2)fit/testcount-placement-sizes,
  (3)couplefantasyrebuildtoSAMEpeople/food,(4)normalHTMLatlaspublication/QA.
  Stillin(1);calibrationfailurecanadditerations,nofixedpassdatepromised.
* Detailedinstitution/de-factocontrolcalibrationandS2–S5remainlaterqueue,notblanket
  prerequisiteblockingfirstsettlementlocation/populationsrelease. DoNOTdropfull
  roadmaporclaimcurrentcandidatecalibrated. Seshatdoesnotsupplylocationtransfer
  coordinates;exposedHan/Romearenotprospective. Preserveallactors/nonstate/mobile.
* NEXTcontinuealreadyfrozenf0f3b892scopecomparison (below);prioritizesettlement
  hierarchy/largestpopulationdatepreparationforrelease1,notendlesssideprobes.

# Documented institution-scope comparison declared after source push — 11 November 2026

* c851ad63/providerprep and protocol831d0b11 pushed/verified BOTHbranches;continued.
* NEXT calibration/institution_scope_20261111/plan.json declaredBEFOREnewscope/
  AD200counts. Compareexplicit_only vsdocumented_parent_scope,all10vars/5007rows;
  nofit/modelscores. Authorrepo292b042cef3dde3d43b2c7723dec41a173c2a163 pinnedin
  data/cache/institution_date_policy_20261111/repository.json,README+Template.py.
* AuthorREADME+check_dataframe confirmsfullyundatedsingle ORflaggedmultiple
  ->parentduration;dated/undatedmixture rejected. ImplementONLYdeclaredscopepolicy,
  noauthorpackageexecution,randomrange/disputesampling,interpolationorclipping.
* Keepone-sided/reversed/outofparent/invaliddatesexplicit,multialternatives
  unmerged,rawunknowns/rangespreserved. Parent-scoped≠directlydatedrole. Need
  independentreview,tests,freshreplay,publication/QA andpushBOTHafterresults.
* All oldsource/atlasresultsfrozen;providerrole/staffgatespersist,fullS1c/d/e,
  S2–S5,allactors/mobile/nonstate,r44physics. Noproductionadoption.

# Provider audit/Earth institution source complete, ready to push — 11 November 2026

* Protocol831d0b11 BEFORE newproviderfields or Polarisrows. Newhelper
  polity/institution_evidence.py preservesrawcodes/valueintervals/datebounds;
  3tests added. prepare_institution_evidence.py produces aggregateearth_preparation
  andprovider_audit underoutput/institution_evidence_20261111;NOmodelmatching/scores.
* PinnedPolarisrepo55ca5fbc2b563ddbbc1a3413071d4bd243d0a5fa;workbook2899093bytes.
  sources.json identifies7privatefiles (workbook,license/readme,codebook/article
  texts,releaseutils/notebookreadONLY). RepoMITwordingsoftware/docsdoesnotalone
  establishdatascope;rawworkbook/text stayprivate,noapprovalquestionneeded.
* 8sheets,626polities/uniqueIDs,10targetvars5007rows,alltargetpolityjoinsmatch.
  Mostvariabletimeboundsmissing(e.gbureaucrats470/492);sourceexportcopiesAPI
  boundsbutnull-defaultsemanticsNOTestablished. DoNOTsilentlyinheritpolityspans
  orclaimAD200fit. UnexpectedSA/A~Pcodesunresolved,1reversedpopulationrange,
  1malformedmilitaryrange,duplicatekeys and10outofparentintervalrecords preserved.
* Metadata suspiciousaliasprofessional_military_officer -> 'Professional Lawyers'
  in legacyEquinoxcolumn. Canonicalname/APIjoinsused;nocrossreleasealiasjoin.
* Readcodebook:professionalabsence≠nogovernance;hierarchyofpeople≠settlement
  hierarchy;buildingsalone≠specialistbureaucracy. Unknown/inferred/transition/
  disagreement notcollapsed. UCLpaperTurchin2018DOI10.1073/pnas.1708800115read.
* Independentreview5007targetrecords/8sheets/38actorcohorts,all4atlasinputs
  unchanged. Report/figuremade/posted,publisher/base/package/attributeswired.
 121tests pass;fresh3artifactprep/reviewbyteexact;new/previous/evidencebrowsers,
 344/390light-dark,downloadreviewSHA,sourceexposurepass;publisheridempotent.
*179Windowscriticalfilesbyteexact,693activehublinksresolve,rawthirdpartysources
  excluded. NOWcommit/pushBOTH. SourceprepNOTsealed/independent/calibrated.
  THENresolvenulldates/code/aliassemanticsandprovider evidencebefore
  monthlyserviceclaims. OfficialSeshatdata page linksSeshatDatasetAnalysis;
  officiallinkedrepo matildaperuzzo/SeshatDatasetAnalysisREADMEactuallydocuments
  singlenodatevalues ANDdisputednodatevalues spanningparentstart/end. Thisis
  documentedanalysispolicy,notindividualdatedroles. Needpinrepocommit/codeand
  verifyimplementation,noforeigncodeexecution. DoNOTcopyrandomsampling/interpolation
  orrange/disputeimputation. Declarestrictvsdocumentedparent-scope policyBEFORE
  newAD200counts;keeppartial/malformed/conflictingandout-of-parentdatesexplicit.
  Full S1c/d/e,S2–S5,r44scopepreserved.

# Provider audit and Earth institution-source preparation declared — 11 November 2026

* Capacityd27700b2/protocol3d3a6c4e pushed/verified BOTH branches. Continuedafterpush.
* Inputaudit found~86% year-store staffatgeneratedpainted-claimhypotheses,not observed
  institutions:raw84600/98700,corrected87000/101100. Actualsitecounts1034raw/1053
  corrected,151marked and12unresolvedeach. Capacityreport/HANDOFFsitecountcorrected.
* PRIORITYbefore monthlyserviceclaims:providerrole/staff evidence and scenario
  eligibility,notbetterroutesaroundunqualifiedall-town100personcohorts. Do not
  equatefortifiedtownwithprofessionalsoldiers,monasterywithgarrison,missinginfo
  withabsenceoflocal/nonstategovernance. All18actors+unresolvedmuststayvisible.
* NEXT calibration/institution_evidence_20261111/plan.json declared BEFOREPolaris
  workbookrows/values ornewproviderfields. OfficialSeshatdata linksPolaris2026
  2.76MBxlsx onGithub;metadataonlyknown. Preparation-only:pincommit/hash/license,
  schema/time/uncertainty/coverage;NOmodelmatching/scores/fitsorancientstaffcounts.
* UCLTurchin2018PDFdownloaded/privatepdftotext,DOI10.1073/pnas.1708800115,cache
  data/cache/institution_sources_20261111/turchin2018.txt+download.json. RawPDF
  removed. CodebookURLisPDF11.15MB,first8MBboundedfetchrejected;retry16MBbound
  if needed,retaintext/hashonly. Primarycodebooklivewebsite403;officialOxford
  methods/data pagesread. No rawthirdpartyworkbookorarticletextinGit/portable.
* Full S1c/d/e,S2–S5,activeclimater44 andallactor/nonstate/mobilescopepersist.

# Capacity consumer complete, ready to push — 11 November 2026

* Protocol3d3a6c4e before results. Newpolity/service_capacity.py supported_staff_hours
  validates SAMESettlementPlan resident/foodcohort;explicitotherdutiesreservedfirst.
  fulfil_services rations requestedHOURS acrossallchannels together,no extrafood/
  people/staff,no automaticrerouting/maxflow.8unit tests pass,includinglimits.
* Builder/reviewer/plotter/publisher under scripts/*settlement_service_capacity.py;
  output/settlement_service_capacity_20261111:fields.npz/results/review/figureprovenance.
  FrozenactualEarth raw/corrected1034/1053sites x10foodcases x3commitments=60cases.
 20periodicfoodchecks matcholdledgers;60perorigin/providerhourcases independently
  recomputed,twoatlaspackets byteexactvsa9b3858c. No worldchanges,r44staysactive.
* Arbitraryworkunits:600grosshours/cohortresident/year;0/50/100%otherduties;each
  SAMEresident2neutralrequests/yearcost1&2h;identitylocalchoice. Noncalibrated.
  joint365raw/corrected98.26%/98.39%fulfilledunder0and50commit,0under100commit;
  toyworkloadmostlynonbinding,substantialunusedhours. Noparameterretuningafteroutcome.
* Newfixedlocalmapmade/posted,allmodelsitesoriginalpositions/residents;coastline
  fromsamebinarylandlookup. Newcollapsedresearchpanel6rows/figure/6downloads.
  Basepublisher/package/attributeswired.118tests pass,fresh3artifactreplay byteexact.
  New/previous/evidencebrowser,mobile344/390/light-dark,NPZdownloadSHA pass;publisher
  idempotent.161Windowscriticalfilesbyteexact,686activehublinksresolve. FullZIP
  unbuiltunder~120MBquota. NOWcommit/pushBOTH;continueactualmonthlynetwork/shared
  commitmentinputaudit/design ratherthanassumepatrol/collectionworkisfree.
* Full S1c/d/e,S2–S5 and prospectivequalification remain. Staffaffiliationstilllegacy
  scenario,notactualinstitution. Includeallactors/unaffiliated/mobile/nonstate.

# Capacity consumer declared after composition push — 11 November 2026

* Compositiona9b3858c and protocol5e650062 pushed/verified BOTH branches. Continue
  afterpushasuserrequested. All110tests/browser/replay/142Windows/679links passed.
* NEXT calibration/settlement_service_capacity_20261111/plan.json declares BEFORE
  capacityresults:shared multi-channel proportionalhourrationing,explicit committed
  hours,food-supported SettlementPlanstaff,no rerouting/maxflow/extraresidents.
* Exercise BOTH frozen Earth raw/corrected settled_reach.json.gz,allfoodcases;
  replayrecordedperiodicfoodwithoutnewfoodalloc. Fixedidentityproviderchoice,
  2neutralrequests/resident/year,cost1&2hours,gross600hours/staff,other-duty
  commitments0/50/100%. Arbitrary stressunits,NOT empiricancientrates or worldmaps.
* Publishaggregatecouplingchecks/figure,replaytests/QA,commit/pushBOTH;then monthly
  actualsupportedprovidernetwork/sharedpatrol-collection-servicecommitments. Legacy
  controlhoursunquantified;don'tassumefreebudgetorpromotearbitrarycapacities.
* Full S1c/d/e,S2–S5,activephysicsr44andallactor/nonstate/mobilescopepersist.

# Source composition complete, ready to push — 11 November 2026

* Protocol5e650062 committed before supportcounts/scores. Five of ten declared
  group/cohort cases pass30positive/negativeunit gate. Sourcepartition full65village,
  84vicus,7smalltown,1mixed,269roadside-only =426. Strict64/81/7/1/0 =153.
* Fullpositivecellunits47/47/6/1/154;strict46/44/6/1/0. Failedsmalltown/mixed and
  strictroadside remain explicitly unscored; no outcome-directed merges/gaterepair.
* Fixedone-day history serviceglobalAUCvillage.3930/vicus.8822;strict.3884/.8899.
  Localfull.4748/.5557,strict.4723/.5533,below respective suitability. Corpus
  composition/geography matters; no qualified economic/military/AD200role claims.
* polity/role_composition.py,two tests,evaluator/reviewer/plot/publisher/browser
  scripts;output/settlement_role_composition_20261111. Review2970globalAUCs,
  6270stratumAUCs,330blockmeans,10partition/gates,21oldartifacts unchanged.
* SourceSmith2016chapter2p38 reread from pinned text: road association defines
  village/roadside,vici civilianfort-origin,authorsrecommendseparatefunctions.
  Newsemantic_sources.json captureshash/anchors,not an inventedempiricalcoefficient.
* Report/figure made and imageposted;newindependentcollapsedatlaspanel10rows,
  5explicitunscored,5aggregate links. Basepublisher/package/attributeswired.
*110tests pass;freshresults/reviewbyte-exact,21earlierartifactsunchanged. Browser
  new10rows/5unscored/figure/5links,byte-matchedreview,344/390light-dark;previous
  controls/general evidence pass. Publisheridempotent,142Windowscriticalfiles
  byteexact/679activehubdependenciesresolve. No fullZIPunder~125MBquota.
* NOW commit/pushBOTH;then continue
  capacity-limited service primitive with explicit staff-hours/food-supported
  inputs,unmet demand and SAME resident/food/staff/institution/control ledger.
  No production adoption. Preserve full S1c/d/e,S2–S5 and activeclimater44.

# Source composition protocol declared after controls push — 11 November 2026

* Controls milestonee567dec2 and protocol720fcaa2 pushed/verified on BOTH branches.
* NEXT calibration/settlement_role_composition_20261111/plan.json declared before
  new subclass supportcounts/scores. Five-part source-label partition x full/strict,
  central30unit gate eachclass,all66oldfields,all9coordinates/spatial/effort checks.
  Failed groups stay failed; no outcome-directed merging,subset/winner selection.
* THEN capacity-limited service primitive with explicit real staffing/food inputs,
  unmet requests and shared ledger,not more arbitrary scalar-role promotion.
* Full S1c/d/e,S2–S5,activeclimater44,allactors/nonstate/mobile scope unchanged.

# Service opportunity controls complete, ready to push — 11 November 2026

* First milestone70e50882 and protocol192c7eb3 pushed/verified on BOTH maintained
  branches. User explicitly wants continuation AFTER pushes; continue autonomously.
* Next protocol720fcaa2 committed BEFORE opportunity/null fields or scores. New
  polity/service_opportunity.py, four unit tests; builder/evaluator/reviewer scripts
  and output/settlement_service_controls_20261111. All66predictors,9coordinates,
  both full/strict cohorts, all travel/mass cases retained. No fitting/adoption.
* Strict one-day recorded-road history interactionAUC.6453 versus inverse-mass.6462;
  corresponding local.5059 versus suitability.5748. Global denominator effect,
  not qualified roles. Uniform/environment/history allsame1292globalopportunities.
* Independent review1188directAUCs,378old diagnostics,18oldfields,18requestledgers,
  9nulls and54actualFULL-window rival-normalization comparisons. New report/figure
  made and posted; publisher/base/package/attributes wired.108focusedtests pass;
  fresh4artifact replay byte-exact,17previous artifacts unchanged vs70e50882.
* Browser9rows/figure/6links,byte-exact modelNPZ,mobile344/390/light-dark pass;
  previous service/evidence panels pass. Publisher idempotent. Focused Windows
  checkout/linkclosure receipt underoutput; nofullZIPunder~145MBquota.
* AFTER PUSH predeclare source-role composition check before new subclass scores:
  village/vicus/smalltown distinct, noautomaticmilitary/market/AD200functions. Same
  cohorts/offsets/support/sourceeffort and all declared controls, no bestcase tuning.
* Full S1c/d/e,S2–S5 and physicsqueue remain. Active climate r44; no production
  settlement/control changes. Qualified future roles must feed SAME finite
  people/food/staff/institution/control ledger, allactors/nonstate/mobile scope.

# Finite service demand published after recovery — 11 November 2026

* Full S1c/d/e,S2–S5 and separate physics queue persist. Environment returned with
  all core files/results intact. Local protocol192c7eb3 frozen BEFORE service fields
  or strict-subset scores; no production adoption, active physics remainsr44.
* New primitive polity/service_demand.py partitions each origin's finite potential
  requests across competing expected opportunities. Requests are NOT extra people,
  food,staff or completed services. service_access.py reuses directed Tobler land
  routes, both legs constrained, no water/corner shortcut or political travel wall.
* Fields/scoring/review scripts under scripts/*settlement_service_demand.py; output/
  settlement_service_demand_20261111 has fields.npz,manifest,results,review.6 scenarios
  (roads/no roads x .5/1/2days),21predictors,9offsets,full/strict context contrasts.
* Strict context subset153source/147included nucleated records,97positive cellunits
  vs797farm/villa,45mixed. Per-centre globalAUC≈.64–.65 but2day local50km≈.55–.56,
  below suitability≈.575 locally. No chosen predictor; geography/opportunity effect
  may explain gain. All scenarios/strata retained, no fitting or role-date inference.
*104 combined tests pass. Independent review378direct AUCs,6requestledgers,27exact
  previous refs,18actual FULL original-window graph/rival checks vs crop. Fresh-output
  replay4artifacts byte-exact;13 previous source/numerical artifacts unchanged.
* Standalone publisher/base restoration/package recipe now complete. Native service
  panel8rows/2figures/6links, downloaded modelNPZ byte-exact, mobile344/390/light-dark,
  previous role panel and general evidence functionality pass. Figures posted last
  round, corrected map bounds1965x930; no raw archive locations/cache redistributed.
* Recovery note below is historical. Current source dataset remains exposed,
  conditional development. New service exposure tracked; do not label independent.
  FullZIP/sitecopy unbuilt under quota;108 Windows-style critical files byte-
  exact,666 local dependencies resolve,publisher idempotent. No actual world
  settlement/control map changed.
* NEXT (continue after commit/push): predeclare and run candidate-availability
  uniform/environment/history masses, zero-travel D/m and inverse-mass controls,
  plus local reference-demand comparator. Keep same full/strict cohorts and all
  old geography/effort/offset checks. Need show interaction adds more than a
  geographic division by sparse opportunities before promoting functional roles.
  Qualified roles must feed SAME population/food/staff/institution/control ledger,
  all actors/nonstate/mobile populations. No every-region veto introduced.

# Service-demand recovery in progress — 11 November 2026

* Environment interruption occurred DURING publication patch; core source/results/
  figures survived intact. New publisher/base/packaging/attributes edits did NOT
  land. Current localHEAD192c7eb3 is protocol-only; last verified remote56c9f3ff.
* New modules polity/service_demand.py and service_access.py, builder/evaluator/
  reviewer/plotter under scripts/*settlement_service_demand.py; report under reports.
  Protocol calibration/settlement_service_demand_20261111/plan.json frozen192c7eb3
  BEFORE fields or strict-nonroadside scores. No production adoption.
* output/settlement_service_demand_20261111:fields.npz/fields.json/results.json/
  review.json. Review passes378directAUCs,6requestledgers,27exactoldreferences and
  18 actual FULL original-window graph/rival checks versus cropped fields.
* Nine new unit tests passed before interruption; combined104 suite still pending.
  Fields implement finite potential requests, not people/food/staff/completed services;
  both directed walking legs constrained; all scenarios preserved.
* Strict subset153source/147included nucleated records,97cellunits vs797farm/villa,
 45mixedcells. Requests-per-centre≈.64–.65 overall, but only≈.55–.56 local50km versus
  suitability≈.575. Broad opportunity/geography effect; no chosen predictor/default.
* Two figures generated and posted: settlement_service_demand_scores_20261111.png
  (2100x870), maps (1965x930 after tightbboxfix). No raw archive positions shown.
  Map fixed roads/B1; hatched outside modelwindow,blue water,grey no displayed value.
* NOW finish standalone publisher + base restoration + package recipe/attributes;
  browser/mobile/links; combinedtests/replays/Windowsfocusedcheck; update exposure/
  full roadmap; commit/push BOTH maintained branches. Rawcache NOT Git. FullZIP
  unavailable under~155MB free quota. Preserve S1c/d/e,S2–S5 and physicsqueue.
* AFTER: test candidate opportunity masses(uniform/environment/history),zero-travel
  and inverse-mass controls BEFORE attributing gain to service interaction. No
  after-outcome predictor reversal/adoption. Must feed SAME ledger before qualified
  world settlement/control changes; all actors/mobile/nonstate scope persists.

# Conditional role diagnostic complete: weak, no fitting/adoption — 11 November 2026

* Full S1c/d/e and S2–S5 programme remains on roadmap. Protocolcccab768 pushed to
  BOTH branches BEFORE matching/predictor scores. Current diagnostics now exist;
  older "no scores yet" entries are historical checkpoints. Do NOT relabel rural
  Britain unscored or independent. Physics staysr44, production world maps unchanged.
* New code polity/observed_role_contrast.py; scripts/prepare_,evaluate_,review_
  settlement_role_contrast.py. Optional requirements-settlement-research.txt pins
  pyproj3.7.2, installed locally without pip cache. Standard atlas launcher unchanged.
* Target: selected-archive WHOLE-RECORD nucleated vs farm/villa DOMESTIC=yes exclusive
  context labels;426/2049source rows, not datedAD200 roles or true absence. Central
  included419/1938; exclusions byclass retained (window/nonland/disallowed), no
  nearest-land rescue.9km original Roman400x600 grid verified by AEQD reconstruction.
* Primary797farm/villa and249nucleated cell/class units across891cells;155mixed cells
  kept in BOTHclasses/ties. Repeated excavations do not add primary mass.30unit/class
  gate passes. Private matches/data/cache/settlement_role_contrast_20261111/matched.npz
  NOT redistributed. Public prep/results/review allaggregate.2475selected points
  projected, NOT whole3652archive or a source map.
* Transformer: offline available OSGB36->WGS84(6), reported2m, NOT source precision.
  Best OSTN15grid unavailable, recordedpipeline/warning/software versions. All9offsets
  central,±2/±5km EACH British-grid axis preserved; no best-coordinate selection.
* RESULTS: uniformAUC.5; existing suitability.547840 vs historyL450intensity.519037.
  Equal50km-block means.601456/.585896,63bothclassblocks/81observed; NOT heldout.
  Coordinate ranges.5209–.5478 vs.5038–.5190. All region/fieldwork/AREA strata retained;
  single-class strata null. RankAUC reviewed independently with direct pairwise
  comparisons,27values. No parameters fitted, thresholds tuned, institution assigned
  or production changed. Centre placement quality does not qualify role inference.
* New report SETTLEMENT_ROLE_CONTRAST_20261111.md and secondfigure posted in chat.
  Dedicated collapsed Earth evidence panel has3rows/5aggregate-doc links. Current
  dataset_usage and data_queue mark source scored conditional development. Older
  publishers now preserve stronger exposure rather than downgrade it on rerun.
*95 tests pass. Preparation AND private matches fresh-output byte-exact;10 previous
  artifacts unchanged vs54fcb2f3. New/previous/evidence browser panels/figure/filter/
  download/error/mobile344&390/light-dark pass. Raw source/caches not inGit/portable.
*88 Windows-style critical files byte-exact;658 local dependencies resolve;
  normal launcher release verifies. Full ZIP/site copy not rebuilt under quota.
* NEXT: explicit functional/service-demand mechanism AND source observation model,
  not more historyL tuning or automatic promotion of intensity into role labels.
  Before road-derived candidates, freeze robustness excluding roadside labels to
  avoid a definitional route association. Accessible rural demand/competition/
  finite surplus are hypotheses, not proved causes. Keep timing/source selection
  and independent-transfer gaps; qualified roles must feed SAME people/food/staff/
  institution/control ledger for all actors and mobile/nonstate populations.

# Next conditional role diagnostic declared — 11 November 2026

* Completed history/phase milestone54fcb2f3 and protocol710af13a are pushed and
  verified on BOTH maintained branches. Full programme remains below/on roadmap.
* NEXT executable protocol calibration/settlement_role_contrast_20261111/plan.json
  declared BEFORE source-to-grid prediction matching or role AUC. No contrast scores
  exist yet. Source-only preparation counts426domestic-nucleated-only vs2049domestic-
  farm/villa-only;23any-label overlaps excluded from this contrast, not deleted.
* Target is WHOLE-RECORD selected-archive context, not contemporaneous AD200 roles,
  true absence, market activity, census or institutional authority. Mixed model cells
  retain both classes/ties. Primary unit weighting cell/class; source rows remain
  distinct. Uniform, existingenvironmental and fixedL450centre-intensity predictors;
  no tuning/fitting or background land absence. Needs trusted grid transform and
  explicit coverage/effort/coordinate-offset diagnostics BEFORE any interpretation.
* Original Rome400x600 input schema inspected; no matched source/predictor values
  computed. No pyproj/cs2cs currently installed; choose documented library pipeline
  rather than hand-coded geodesy. Read runtime package skill before installing.
* Protocol gives preparation gate30cell-class units/eachclass; report failures, do
  not move extent/threshold. Frozen diagnostics may be weak/reversed; report all.
  No production adoption merely for positive AUC. All S1c/d/e and S2–S5 remain open.

# History boundary tested; successive-role chronology documented — 11 November 2026

* FULL queue remains reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md. No stage is
  abandoned: S1c actual occupation/role evidence, S1d credible transfer, S1e shared
  resident/food/staff/control rebuild, and S2–S5 remain. Active physics stays r44.
* New S1c protocol/driver committed710af13a BEFORE new boundary results. Reuses
  frozen adaptive producer/scorer/allocator unchanged. L150/225/300/450/650 x c.35/.5
  x5seeds x2exposed pools =100evaluations. ALL1202Han/1292Rome counts, eligibility,
  intensity normalization and pair constraints pass.20 overlapping450km runs replay
  old metric rows and actual coordinates EXACTLY. Old studies remain immutable.
* Results output/settlement_history_boundary_20261111: old c.35/L450 remains combined
  lead Q.62140955, gain0; now interior to tested range. New c.5/L300 is Pareto:
  uniqueF1 .5236Han/.4034Rome, spacingKS .0778/.1373. Five combined Pareto alternatives
  retain old c.35/L450,c.5/L450,fixed18/fixed27. Weights.4/.6 retain oldlead; .8c.5/L450.
  Not global optimum, actual occupation age, unseen transfer, significance or adoption.
* New chronology source: authors2016 Britannia Monograph29 Chapter1 printed10–11
  documents phase-date fields as major settlement changes and farm->villa successive
  labels; Chapter2 printed20 discusses palimpsest/classification limits. Metadata
  calibration/settlement_phase_evidence_20261111/semantic_sources.json records PDF
  byte/text hashes and URLs. Large PDFs streamed to pdftotext, not retained; text
  stays private under data/cache/roman_rural_britain_metadata/book. Raw not redistributed.
* New polity/settlement_phase_evidence.py/audit_settlement_phase_evidence.py retain
  date order, flag review cases, NEVER assign role intervals.1031 consistent change
  records,10requiringreview (4missingbounds,3reversed,3outofspan),2611nochangerecorded.
 146 records bothfarm/villa. General purpose now documented; direct export-column
  dictionary and role-to-change mapping still absent. Do not keep calling all phase
  meaning unknown; do not equate source tags with contemporaneous AD200 functions.
* Review blocks add exact numericXY and normalizedcounty+name to old associations:
 83nontrivial/189records,3546totalcomponents,largest8. ALL3652observations retained.
  Blocks are NOT physical-place merges, population units or independent spatial folds.
  Sharedname can describe villa+nearbycemetery; centroid can represent investigations.
  Approx2500publishedsettlements is NOT a de-duplication target or duplicate count.
* New reports SETTLEMENT_HISTORY_BOUNDARY_20261111.md and
  SETTLEMENT_PHASE_EVIDENCE_20261111.md; history sensitivity figure posted in chat.
  Earth evidence page has two collapsed research panels/10aggregate-doc links.
  Existing rural roles/coordinate panels retained; normal launcher release refreshed.
  Narrow344px check caught old inventorycard word overflow; scoped wrapping fixed in
  base publisher and standalone continuation. No actual world/control/physics map change.
*89 focused tests pass. Independent review100/20; source audit fresh-output byte-
  exact, all7prior source/numerical artifacts unchanged vs32ca2173. New and old rural/
  evidence browsers pass, keyboard/figure/344&390px/light-dark tested. Full ZIP/site
  copy not rebuilt under quota; package recipe includes new docs/figure/protocols.
*70 Windows-style critical files byte-exact;652 local page dependencies
  resolve, standalone publisher idempotent, launcher release verifies.
* NEXT: declare role-specific conditional evidence units/targets BEFORE scores:
  broad-period archaeological role footprints vs dated residential nuclei vs dated
  institutions. Undated records cannot be used as precise AD200 functions or true
  absence; excavated evidence frequencies are not a census. Define coverage/grouped
  spatial splits and uncertainty sensitivity without waiting for a perfect gazetteer.
  Preserve actual history/transfer gaps, then wire qualified allocations into SAME
  people/food/staff/institution/control consumers across all actors/nonstate areas.

# Operational rural-coordinate interpretation verified; no model adoption — 10 November 2026

* Full programme remains reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md. First
  current-turn milestone9ad8a181 (role evidence) pushed/verified on BOTH branches;
  continued immediately with coordinate investigation. Do not drop S1c/history,
  S1d/credible transfer, S1e/shared-ledger integration, or S2–S5.
* NEW audit scripts/audit_roman_rural_coordinates.py compares six declared exact
  named sites with eight Historic England official National Grid references.
  Operational CSV X_REF_MAP=easting/Y_REF_MAP=northing in British-grid metres:
  all8 references/all6 sites within1km; min11m/median54m/max188m. Reversed axes
  min29km,0/8 within1km. Web-Mercator-Y interpretation gives0.094–5.877deg latitude,
  outside published49.74–55.82 envelope for ALL3652 records. No whole-source projection.
* This is exposed schema investigation, NOT a sealed/model accuracy test. Known
  values/search results disclosed in calibration/roman_rural_coordinates_20261110/
  plan.json. Preserve plan_v1.json and its recorded hash: before any distances,
  official Chysauster had3refs; amendment retains/compares ALL3, never nearest/drop.
  Keep8point/all6site accounting distinct. Point definitions differ; precision and
  official export-CRS certification NOT established. Do not call54m global accuracy.
* Reynolds Cardiff thesis cached15.5MB, Table4.6 printed65–66 uses same MAP labels
  but reverses axes. Checked PDF directly; URL/SHA in plan, not redistributed. HE
  six source HTMLs in data/cache/roman_rural_britain_metadata/anchors; pins in output
  source_snapshot.json; changed pages fail, missing pages can be reacquired.
* New report ROMAN_RURAL_COORDINATES_20261110.md and aggregate figure under
  reports/figures/roman_rural_coordinates_20261110.png, posted in chat. Atlas source
  panel now adds collapsed coordinate details/figure/4downloads (15total); raw CSV/
  HTML/PDF not included. Role/preparation audits and both numerical settlement
  studies remain byte-exact vs9ad8a181. No model maps/physics/pop/staff/actor changes.
*77 focused tests pass. Fresh-output audit/source receipt byte-exact; tampered anchor
  page rejected. Browser nested keyboard/mobile/dark/figure/15links pass. Full ZIP/
  site copy still not rebuilt under quota; recipe includes new report/figure/plans.
*49 Windows-style critical files byte-exact,643 local links resolve; publisher
  idempotent and standard launcher verifies the refreshed release.
* NEXT: actual place identities (association blocks alone insufficient), PHASE_DATE1/2
  and function dates, and positional uncertainty/coverage. Operational grid/axis
  interpretation is now usable with explicit source/inference limits; do not keep
  treating its basic identity as totally unknown. Before any score, declare grouped/
  spatial role-specific calibration/resolution/sensitivity. Do not fit farms to
  county-seat targets or turn roles into authority. S1 history/transfer remain open;
  qualified changes must enter SAME resident/food/staff/institution/control chain.

# S2 role evidence implemented; physical-place calibration gates remain — 10 November 2026

* Read reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md on every continuation. S1c
  occupation history, S1d credible transfer, S1e coupled resident/food/control rebuild,
  S2 hierarchy and S3–S5 remain open. Do not replace them with evidence-only overlays.
* New polity/role_evidence.py and scripts/prepare_roman_rural_roles.py compile the
  pinned rural-Britain observations into11 overlapping context channels. Each
  channel counts once per record, never people/staff/actor authority. All3652
  records retained;3002 multi-channel; no unknown observed source labels. Explicit
  domestic observation stays separate from residential/morphological context.
* Official advanced-search UI confirms roadside settlement/jetty omitted from the
  old lookup; taxonomy discrepancy resolved. Official date help documents start−100
  = Middle Iron Age or earlier (628 records), end400 = end-Roman-period convention
  (1295).2641 spans AD200-compatible,117unknown,892 outside recorded span,2zero-
  ambiguous. Every specific role remains UNDATED; extra phase fields unresolved.
* Exact TYPE/HER_NAME/DESCR associations yield3564 validation blocking components:
 3499singletons,65nontrivial/153records, largest8. All keys stay inside components.
  These are NOT physical-place merges or independent folds; only88 record units
  linked vs published approx3600records/2500settlements. No folds/scores assigned.
* Official map.html uses client3857/display4326 and loads27700, but directly requests
  WMS layers. This does NOT establish CSV X_REF_MAP/Y_REF_MAP CRS/precision. One-
  record query500/WFS schema404 documented; no CSV transform or source target map.
* New report ROMAN_RURAL_ROLES_20261110.md, explicit crosswalk/semantic source URLs
  and pinned local content hashes under calibration/roman_rural_roles_20261110.
  Raw CSVs and HTML remain cache-only, not redistributed. No place/population/staff/
  affiliation/control or physics changes; initial preparation and both numerical
  settlement studies byte-exact vs7835271d. Role audit fresh-output byte-exact.
* Earth evidence page (normal .bat launcher) has nested collapsed role panel,
 11overlapping channels and11aggregate/doc downloads; crosswalk and source semantics
  included in packaging recipe. Browser keyboard/mobile/dark, filters and downloads
  pass.64 focused tests pass;37 Windows-style critical files byte-exact and638
  local dependencies resolve. Full portable ZIP not rebuilt under disk quota.
* NEXT: resolve actual physical-place identities, CSV CRS/precision, PHASE_DATE1/2
  and coverage before role-specific grouped/spatial calibration protocol. Association
  blocks already implemented but not sufficient spatial independence. S1 history/
  transfer can proceed independently; S1e must rebuild SAME resident/food/staff/
  institution/control consumers after qualification. Keep all actors/nonstate groups.

# S2 rural preparation complete; roles/coordinates still unresolved — 10 November 2026

* FULL queue remains reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md; do not drop
  S1c history, S1d transfer, S1e shared-ledger/control integration or S2–S5. Physics
  has its separate queue. Adaptive settlement milestone88ea2104 is pushed to BOTH
  maintained branches; exact108 results and all climate/map fields remain unchanged.
* Rural preparation plan frozen066db539 BEFORE site tables read. Public exact ADS
  encoded download links work; unencoded guessed links403. Metadata/schema/role
  lookups verified; five raw tables cached locally under reviewed ADS research terms,
  NOT redistributed. Only aggregate outputs/source hashes published.
* source output/roman_rural_preparation_20261110:3652 core/site IDs join; all declared
  PKs unique, role/association orphans0. Major-role observations4365,608multi-role
  records; minor5970,1549multi-role. Minor lookup omits356 observations (principally
  roadside settlement), retained explicitly. Raw IDs are NOT unique physical places.
* 3535 numeric ordered occupation spans,117missing;2641 compatibleAD200, not proof
  each role active then. AREA means EXCAVATED/INVESTIGATED area; never full urban
  area/population. Separate settlement-size wordlist has1466uncertain records.
* Actual core export has X_REF_MAP/Y_REF_MAP, NOT documented X_REF/Y_REF OSGB fields.
  No automatic alias, projection or target map; units/precision remain unresolved.
  Extra PHASE_DATE1/2 also need interpretation. Sources overlap Roman geography and
  excavation selection: no independent/sealed status and NO model score.
* CSV correctness fix: Sniffer inferred doublequote=False, misreading later escaped
  quotes. Shared reader now standard comma/Excel. Regression includes quotes,
  commas,newlines. Vidarbha old source/audit preserved; parser_correction.json proves
  unchanged row counts/zero joins/axis findings/decision. Removed false unnamed-cell
  warning, corrected some distinct-text counts. No climate/settlement runs change.
* New reports ROMAN_RURAL_PREPARATION_20261110.md and SETTLEMENT_ROLE_CONTRACT_20261110.md
  distinguish record/place/dated function/institution actor. Do NOT treat all villages,
  farms/roads/roles as authority sources, convert icon diameter to area, or read a
  legion founding number as troop strength. Shared people/food ledger must consume
  roles once; no automatic Empire owner from a Roman-period source.
* QA:52 focused tests pass; fresh preparation snapshot/audit byte-exact; both
  numerical settlement studies unchanged vs88ea2104. Normal source/adaptive/evidence
  browsers pass; native collapsed panel, keyboard, aggregate downloads and mobile/
  dark tested. Focused Windows26critical files/634local dependencies pass; launcher
  release verifies. Full ZIP/site copy not rebuilt under quota.
* NEXT concrete work: document exported MAP CRS/precision from official mapping
  metadata, resolve physical-place grouping (association/project IDs are not proven
  site groups), phase/role timing and taxonomy. Then freeze role-appropriate
  calibration/splits, controlling repeated observations/coverage. No role-only overlay
  without settlement/population and institutional/control consumers. S1 remains open.

# Adaptive settlement spacing complete; no adoption; transfer source rejected — 10 November 2026

* Read reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md at every continuation. Full
  S1–S5 programme persists: locations/occupancy; roles/hierarchy; differentiated
  authority; shared surplus/institutions; mobile/nonstate communities. S1 remains
  unfinished, not dropped. Physics has its separate queue below.
* New S1c plan calibration/settlement_intensity_20261110/plan.json committed a9a4a635
  before outcomes. New isolated polity/settlement_intensity.py leaves frozen old
  allocator/source hashes and72-evaluation study UNCHANGED. Relative centre weight
  normalized to requested count, local separation c/sqrt(lambda) capped45km;
  symmetric pair distances>(r_i+r_j)/2, no9km cutoff. This is NOT population or
  occupation-age dynamics. Same prepared inputs and1202Han/1292Rome counts.
* Completed108 evaluations: L450/800/1500 x c.25/.35/.5 x greedy/draw; stochastic
  five fixed seeds. All counts/eligibility/pair constraints/intensity budgets pass
  independent review. Selected draw_c0.35_L450 Q .6214 vs best old fixed .5697
  under NEW declared .6 uniqueF1 +.2 rankNormalized +.2(1-KS). No per-pool veto.
* Lead means: uniqueF1 Han .5213/Rome .4020 (production .3358/.3668), spacingKS
  .0601/.0552 (production .7705/.6829), blockrank .6207/.4981. Fixed18 alternative
  retains HIGHER uniqueF1 .5912/.4224 at worse spacingKS .4723/.4065; retain Pareto
  alternatives, do not claim universal dominance. Lead L450 is a grid boundary,
  not a universal calibrated historical scale. No new blind/transfer qualification.
* New reports SETTLEMENT_INTENSITY_20261110.md, VIDARBHA_PREPARATION_20261110.md;
  two maps/plots in reports/figures. Research published in normal Earth evidence
  page; older study remains. Main Earth/free/Whittaker maps/r44 defaults unchanged.
* IMPORTANT S1d preparation source result: plan vidarbha_preparation_20261110 frozen
  at same a9a4a635 BEFORE CSV read. API/file checksums pass, but master60 coordinate
  rows join ZERO of389 settlement IDs (390 rows,one duplicate); documented axes
  yield0 plausible pairs, swapped interpretation60. Never silently swap/fuzzyjoin.
  No target maps, climate/prediction lookup or model scores computed. Source is
  prepared/unscored and NOT READY for located transfer, not a model test failure.
  Current registry/data queue updated; other two candidates remain metadata-only.
* Next: S1c history/role/resolution robustness and credible S1d source resolution or
  alternative. Audit Roman rural Britain for S2 role/phase/coverage if useful; no
  reuse of old sites as unseen. S1e must later rebuild towns/tracks plus the same
  people/food/staffing/control ledger. No generated town is independent authority.
* QA:45 focused tests pass; all108 draws reviewed; fresh-directory JSON/positions
  replay exact; normal atlas browsers pass (new/old studies, source labels, filters,
  downloads, light/dark/mobile). Focused Windows29critical files and628local page
  dependencies pass; launcher release verifies. No full ZIP/site copy under quota.
* S2 rural-source preparation can proceed while resolving S1d. Audit source role,
  phase and coverage without using a rural inventory as an administrative census;
  retain all S1c/history and S1e shared-ledger requirements.
* Source/input/result hashes and positions retained in output/settlement_intensity_20261110;
  review_settlement_intensity.py checks all108. Old prepared NPZs remain required
  and tracked; no raw-source download needed for repeat. Vidarbha raw CSVs cached,
  only aggregate audit published. Disk still tight; avoid full-site copies/ZIPs.

# Settlement/control S1a/b complete; S1c/d next — 10 November 2026

* Owner approved the WHOLE programme. Read reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md
  at every continuation: S1 count-separated locations/occupancy; S2 roles/hierarchy;
  S3 local versus central authority; S4 collectible surplus/institutions; S5 mobile
  and nonstate communities. Do not drop later stages after a failed candidate.
* Initial S1a/b COMPLETE: new polity/settlement_locations.py, frozen12-variant plan
  committed17c73556, 72 evaluations (two exposed pools; five seeds where stochastic).
  Counts stay1202Han/1292Rome; no eligibility/food/population change. NOT ADOPTED.
* New current-source slope/HAND/FALLOW.600 Earth inputs were reconstructed; they
  are NOT exact Nov7 inputs. Prepared han/rome_inputs.npz plus receipts/results/
  positions are tracked under output/settlement_locations_20261110 for exact replay.
  Never use old Nov7 JSON metrics as controls against these new arrays.
* Frozen composite lead: draw_9km_old_cores_L800. Han proximityF1 .430→.592,
  blockrank .170→.577, spacingKS .771→.195, uniqueF1 .336→.473. Rome proximity
  .432→.460, rank .383→.473, KS .683→.184, BUT uniqueF1 .367→.358. Means over
  five seeds; plot alwaysseed1. No new blind/independent validation.
* IMPORTANT retained alternative: greedy_18km_old_cores_L800 improves UNIQUEF1 in
  BOTH pools (Han.591/Rome.422), at worse spacingKS .472/.407 than the9km lead.
  Next S1c: study this location/spacing tradeoff and historical occupancy/roles;
  do not silently replace the frozen lead or call inspected tradeoffs unseen.
* Follow-up metadata queue: reports/SETTLEMENT_CONTROL_DATA_QUEUE_20261110.md and
  calibration/settlement_locations_20261110/data_queue/candidates.json. Vidarbha
  archaeological inventory (non-Roman geography) for S1d/S2 audit; Roman rural
  Britain for S2 roles; Wiseman/Cambridge phased archaeobotany for S4. NO target
  CSVs/coordinates or scores loaded, NO sealed status granted. Vidarbha methods
  readme/source receipt tracked: YCoord=longitude, XCoord=latitude (counterintuitive).
  Audit schema/date/coverage/recording effort before any prospective score.
* S1d needs a defensible prospective protocol/new pool before adoption. Han/Rome,
  Sui/Tang/Hellenistic/medieval/Domesday remain exposed. 9km exclusion rejects
  exactly9km pairs, creating a spacing-error floor; this is not village validation.
* If qualified, S1e rebuilds towns/tracks + shared food/staffing + control TOGETHER.
  Then S2–S5 remain mandatory. Current parent S1 unfinished; production maps/r44
  unchanged. Normal Earth evidence page now shows comparison and full roadmap;
  base evidence publisher preserves this section, portable recipe includes docs.
* QA:31 focused tests, served evidence/settlement browsers, exact fresh-directory
  results+positions replay,21 critical CRLF-checkout assets and620 linked research
  dependencies pass. Standard launcher verifies release. Full portable ZIP/full
  site Windows snapshot not rebuilt under disk quota; packaging recipe updated.
* Recovery: scripts/recover_settlement_sources.py han/rome; optional pyshp dependency
  added. Full sources need WorldClim + arable_slope_earth + land_people_earth. Raw
  scratch caches are large; disk quota nearly full. Only NEW reproducible source
  downloads/ETOPO scratch and an old temporary bundle were pruned, not experiment
  records. Source receipts remain. Future preparation uses --out NEW_ID; replay
  tracked prepared arrays needs no source download. Physics has its separate queue.

# Mixing reuse INTEGRATED; physical climate stays r44 — 10 November 2026

* After ALL frozen P8d search/coastal/publication steps completed and were committed4d89cf1c, integrated
  the EXACT proposed solve_moisture function. Three cache lines only; no physical coefficients, forcing,
  equation, tolerance or climate adoption change. Whole49 development paired runs match every result
  array byte + numerical histories + original monthly climate. Integrated Japan replay matches all9
  array hashes/diagnostics too. Core field bytes themselves remain the same mathematical r44 model.
* 64 focused tests PASS (moisture/condensation/exchange, integrated cache, observer, fitter/RNG/report).
  Regression now loads immutable output/moisture_mix_reuse_20261110/source_before.py and compares the
  INTEGRATED function against uncached arithmetic. Original source/proposed snippets protected -text.
* CPU timing: five known profiles only; Japan pilot6.5% less, expanded four4.6% less pooled CPU. No
  general wall-speed or climate-accuracy gain claimed. integration.json records old/new source SHA,
  proposal/body equality and exact49 summary SHA; report MOISTURE_MIX_REUSE_20261110.md.
* Historical shape-specific probes and P8d source guards deliberately reject running against changed
  model source. To reproduce/resume those frozen experiments/checkpoints use recorded pre-integration
  revision4d89cf1c; do not weaken their guards. Keep their original protocol/results intact. Future
  experiments need NEW output identities on current source; no parameters/corrections retrained here.
* New publisher publish_moisture_mix_reuse.py adds implementation study + compact field-hash/timing
  JSON to normal accuracy companion, preserving previous scientific sections. Final QA PASS:
  browser78studies/178images (light/dark/mobile/downloads), Windows1560exact assets, refreshed portable
  bundle/extracted launcher. Main Earth/free/Whittaker map folders have ZERO diff; research assets current.
* Full-model replay compares every result-array byte and every reported Result.numerics diagnostic;
  detailed linear-solver iteration histories are also compared in small regression cases. Do not
  overstate the archived Result.numerics summaries as full internal per-iteration traces.
* Next physics work: a NEW predeclared designed monthly-field/process calibration (see
  reports/CALIBRATION_STRATEGY_20261110.md); 51 short CMA trials are not global-minimum proof. Use the
  rainfall-source audit to distinguish missing circulation/drying/import from temperature compensation.
  Keep aggregate v3 scoring/comparability, no every-region veto, no relabelling spent f/g/h as unseen.
  Any actual physics replacement still needs separate qualification before corrections/atlas rebuild.

# Joint ocean/land refit COMPLETE — 10 November 2026

* FINAL: all3 starts finish17 evaluations (51profiles/2499regional solves), no failed trial; all48 actual
  optimized proposal vectors replay EXACTLY from the seeds/costs, max difference0. All checkpoint states
  n17/two generations/no pending and JSON-normalized best/full params verified. Final journals, full
  best params, identities and resumable optimizer/RNG states now retained at their original chain paths.
* Best S49: r44 1.0000; warm1.0132434; warmC3 .99613647. C3 T−1.6533%, P+0.8806%, combined−.3864%:
  misses the required .5% improvement. None advances; no extra fine28/spent-h run, unseen pool or adoption.
* All24 predeclared marine runs PASS. SSTcurveMAE r44 2.27124, warm1.91636, C3 2.12623; marine-aircurve
  MAE1.62089,1.71053,1.47838 respectively. Separate WOA/NCEP references, not observed fluxes or ocean budget.
* Automatic continuation FINISHED (continuation.log says DONE); do not restart its old PID/session.
  Search/followup summary+status completed. Publisher moves study into completed experiments; full report
  and plots in normal climate-accuracy page. r44/v2.2 Earth map fields/corrections stay adopted/unchanged.
* 49-region mixing-cache equality study also COMPLETE/PASS: every byte of T/Tsl/P/W/u/v/E/snow/days,
  all reported numerical diagnostics and original fresh-reference monthly T/P match. It is still an ISOLATED
  proposal until core integration; all frozen-source checks/publication must finish first. No accuracy gain.
* Model/scoring source remained exactly frozen for this campaign. Any subsequent cache integration must
  preserve this original source lineage; old checkpoint resume requires the matching pre-integration code.

* Historical11:09UTC checkpoint: all starts finished phase9; second-generation r44 running. Phase9 best S: r44 1.0000,
  warm1.024742, C3 1.002804; none qualifies. Immutable phase9_checkpoint contains all3 matching journals,
  full best params, search identities and optimizer+RNG pickles, with a16-file SHA manifest and recovery
  directions. Verified n9/one generation/no pending candidates, JSON-normalized best and full params.
* audit_joint_refit_sampling.py replays actual proposals from frozen seeds/costs, no climate runs.
  All first generations match exactly; run at end for all48 optimizer proposals. Finalist checker now
  requires this replay before freezing follow-up identity. Reader tuple/list mismatch fixed and regression
  tested: pickle regional pairs are tuples; normalize to JSON before comparing to JSONL. Tests21pass.
* Report helper also verifies the frozen driver/campaign/plan hashes, beyond model/reference guards.
  These are read/checkpoint changes only; frozen optimizer/model/scoring sources remain unchanged.

* Search launched 10:06 UTC; driver PID1256 on this host (inspect actual processes after resume, never assume
  a PID survived). Frozen driver identity a87f03c6e88d1c8f275973592132c48948715deedc1fcfc59eda503608fcc9ac.
  Three controls complete: r44 S1.0000, warm S1.024742, warmC3 S1.015581. First r44 offspring are worse;
  search still running, no conclusion until all51. Planned two generations/start are NOT convergence.
* New read-only report/publisher scripts: report_joint_ocean_land_refit.py checks all49 raw error pairs,
  recomputes aggregate scores, rejects duplicate/gapped trial indices, verifies frozen source hashes,
  plots every trial. publish_joint_ocean_land_refit.py publishes saved progress OUTSIDE completed studies
  until both search and follow-up finish. Three downloadable JSONL journals are exact snapshot records.
* check_joint_ocean_land_finalists.py implements predeclared followup_plan.json: after clean completion,
  verify state n17 / two generations / JSONL best consistency; freeze all3 cost-best profiles; run fresh
  r44+3 marine audits. Only cost-best profiles passing existing S49/T/P screen get fresh paired49 replay,
  fixed fine28 and all spent-h stress. No substitute finalist, unseen pool, tuning, or adoption. Driver is
  resumable against its frozen input identity; avoid editing its source once follow-up begins.
* Tests20pass (16 optimizer/source/RNG +4 reporting/pair/replay). Browser checker now parses JSONL as
  per-line JSON, requiring sequential indices, rather than attempting a single JSON object.
* Active physics/maps remain r44/v2.2. Progress panel changes research/evidence assets only; regenerate hub
  release hashes after publication and check normal launcher/Windows/portable. No raw atlas rebuild.
* First saved panel (6/51 evaluations, 10:20UTC): browser75completed studies/174images PASS; Windows1552
  byte-exact assets PASS; portable2148files/709links/fresh launcher PASS. Bundle refreshed in /tmp.
* After search: `.venv/bin/python -u -I scripts/check_joint_ocean_land_finalists.py`, then publish with
  `.venv/bin/python -I scripts/publish_joint_ocean_land_refit.py` and `scripts/build_fit_hub.py`.
* Automatic continuation already running (session21009; inspect process after resume). Its log is
  output/joint_ocean_land_20261110/continuation.log. Waits for current driver PID1256 clean completion,
  checks finalists, publishes research, rebuilds hub; stops on any failure. Does NOT stage/commit/push
  final results; review and run final browser/Windows/portable QA before that milestone. Never launch a
  duplicate follow-up while this wrapper runs. Its Python command is visible in process list/session.
* Baseline rainfall figure added: plot_joint_reference_seasons.py verifies monthly-archive SHA and solver
  receipts, plots Japan/Bengal/NorthQueensland/Patagonia; southern calendars restored by six-month roll.
  Equal-region49 monthly MAE32.454mm, annual-within25% .37559, median relative-error regional mean .41724.
  Illustration only, no changed score: Japan winter-wet/summer-dry; Bengal .21x observed annual; Queensland
  1.95x; Patagonia .95x regional annual but only10% wet cells within25%. Regional means hide local error.
  Four illustrated monthly archives are tracked so a fresh checkout can regenerate these figures.
* Saved 11/51 panel: r44 first generation finished with no gain. Browser75completed studies/175images,
  Windows1554byte-exact assets, portable2150files/711links and extracted launcher all PASS. No active or
  retired climate-map folders changed. Subsequent optimizer records are still advancing outside Git.

# Current r44 moisture-source audit COMPLETE — 10 November 2026

* Separate unchanged-baseline observer audit, NOT new P8d optimizer evaluations. Four known regions
  (Japan/Bengal/NorthQueensland/Patagonia) reproduce saved monthly climate/observations bit for bit,
  pass actual case hashes/all numerics; signed terms reconstruct residual within .000023mm/month.
  Regional-mean integrated absolute equation residuals <.6mm/year, versus large climate errors.
* Bengal modeled444 vs observed2143mm/year: advection−32, convergence+319, storm+516, evaporation+284,
  diffusion+90, drying−732. Queensland1707vs874: parameterized convergence+1183, advection+744,
  drying−944. Current signed concentration-equation contributions, NOT causal effects of switching off
  terms or proof of globally conserved water/energy. Monsoon drying is subset of drying, never add twice.
* Frozen plan calibration/r44_rainfall_sources_20261110/plan.json; wrapper audit_r44_rainfall_sources.py
  reuses existing check_moisture_sources.audit_one. Artifacts output/r44_rainfall_sources_20261110.
  New publisher adds source chart + two actual rain-ratio maps, downloadable data, completed study and
  dataset exposure entry. Both figures posted in chat. No physics coefficients/maps adopted or changed.
* Reports/R44_RAINFALL_SOURCES_20261110.md. Separate CALIBRATION_STRATEGY_20261110.md verifies primary
  literature (Petrov2025 LiMMo, Williamson2013 history matching, Couvreux2021 process calibration);
  proposals only, not changes to current search/selection or an implemented emulator/LES boundary layer.
* Browser76completed studies/177images, Windows1557exact assets and portable fresh-launcher checks PASS.
  Research/evidence publication only; main r44/v2.2 Earth and retired atlas map folders unchanged.
* Current campaign continues: r44 and warm first generations have no improvement over their controls;
  C3 branch still running first generation. Direct seeded first-population replay for r44/warm exactly
  matches all actual proposed parameters (0 difference); uneven draws are seed variation, not resume drift.

# Isolated moisture-mixing reuse candidate — 10 November 2026

* NOT integrated into rotclimate; leave all model/scoring modules unchanged until the full P8d search,
  finalist diagnostics and research publication finish. Separate interpreter compiles a small proposed
  solve_moisture function; caches the previous residual check's vapor mixing target for the next Picard
  solve at that identical W. Cache is saved before adding condensate. Legacy non-residual calls unchanged.
* scripts/probe_moisture_mix_reuse.py, _expanded.py; output/moisture_mix_reuse_20261110 and _expanded
  retain exact before/proposed source snippets, frozen protocols and ABBA CPU measurements. Warmup then
  baseline/reuse/reuse/baseline; compare ALL result arrays and all reported numerics, not merely T/P scores.
* Japan r44 pilot CPUratio .9350; expanded Bengal .9179, Queensland .9619, Patagonia .9524, warmC3Japan
  .9757; expanded pooled CPUratio .9539. Every output field + numerical history EXACT. Wall times suffer
  concurrent-search contention; do not report wall-speed claims. No climate-accuracy gain or adoption.
* Four new tests cover residual checks on/off x condensation on/off; exact W/P, iterations/residuals,
  linear histories, fewer mixing calls only when residual checks active. Combined tests25pass.
* reports/MOISTURE_MIX_REUSE_20261110.md. If integrating later, extend exact replay to full dev set and
  preserve old function as immutable reference; move prototype-specific tests to integrated function.
  Probe helper deliberately expects the old source shape and refuses silent reinterpretation after a
  core edit. It must be adapted/retired when core integration occurs. Current published atlas unchanged.
* Full49 paired byte/numerical replay NOW RUNNING in separate workers (session25704), while C3 finishes
  calibration. scripts/check_moisture_mix_reuse_all49.py; output suffix _all49_float_resolution; log under
  joint_ocean_land_20261110/mix_reuse_all49_float_resolution.log. All9 result arrays hashed byte-for-byte,
  full numerics compared, control T/P tied to original fresh reference archives. Equality only, NOT timing.
  Do NOT edit any rotclimate module or helper source until this also finishes.
* Initial all49 attempt aborted at case identity: caller used int56 while reference uses float56.0;
  case_hash JSON metadata distinguishes numeric representation. Float56.0 matches frozen Iberia hash
  exactly; no geographic/cache data changed and current calibration is unaffected. Old failed namespace
  _all49 retains protocol, original source-exact driver and reason; corrected run has a NEW directory.

# Joint ocean/land refit frozen plan — 10 November 2026

* Campaign calibration/joint_ocean_land_20261110/campaign.json frozen BEFORE optimizer candidates:3starts,
  six shared numeric parameters (SST offset/current strength + land offset/amplitude/thermal/radiative time),
  v3S49 objective, no per-group veto. Starts r44, warm15/r44-exchange, warm15/C3-exchange. Fixed Earth
  forcing, model SST/winds, geography and strict numerics. Existing phenomenological response parameters.
* Budget17each = start +2CMAgenerations x8, total51evaluations/2499regional solves; phases1/9/17 interleave
  equally. No dropping weak starts. This is an early bounded refit, not convergence/global-optimum proof.
* Fresh49 references verified.48exactly reproduce original r44; Tripolitania matches known Nov2 recovered
  footprint182cells instead of historical195. Direct WorldClim raw rebuild EXACTLY matches current cache;
  originals retained. reference_reproduction.json records both; use FRESH paired references, no free gain.
* gate_calibrate v3: shared numeric knobs only, fixed Earth boundary, start inside bounds; candidate case
  hashes checked before model solve; start/policy/code/software frozen. NumPy RNG saved/restored so exact
  sampling survives generation-boundary pauses; tests16pass. Legacyv2 objective behavior retained.
* Driver scripts/run_joint_ocean_land_refit.py runs interleaved phases. Root output/joint_ocean_land_20261110;
  run.log, status.json, eachstart/evals.jsonl +state.pkl. Model/benchmark/scoring sources/start profiles/policy
  must stay FIXED while running. Plotting/UI helpers may be developed separately. No new blind pool.
* After51: report all trajectories/failures, marine diagnostics on six known coasts for all3best profiles.
  Qualifiers S49<=.995 and aggregate T/P<=1% get fresh dev benchmark/finer28 +spent-h stress, as declared.
  No adoption/independent validation in this campaign; keep r44/v2.2 atlas +corrections until qualified.

# Shared SST screen COMPLETE — 9 November 2026

* Frozen calibration/shared_sst_screen_20261109/plan.json committed4fba2f09 before runs. Four coordinated
  directions (+1.5/+3K global SST offset and -1.5/-3K current strength), with r44 or C3 exchange, plus fresh
  paired r44/C3:36/36 numerical checks pass. Six selected known regions, not new validation or optimization.
* output/shared_sst_screen_20261109/{protocol,summary,comparison}.json stores full rows/metrics and verifies
  identical cases + changes only in the predeclared shared fields. Earth forcing/geography/numerics fixed.
* Results: reference T1.6836/P.42662, S6=1, coastal SSTcurveMAE2.271. warm15 S1.0336/SST1.741;
  warm15_C3 S1.0188/SST1.746; warm30 S1.0803/SST1.611; warm30_C3 S1.0678/SST1.612. SST improves23-29%,
  land aggregate worsens1.9-8.0%. None passes screen. RejectedC3 S.9938 but T+1.4% fails component guard.
* Reports/SHARED_SST_SCREEN_20261109.md; scripts/publish_shared_sst_screen.py adds plot/table/JSON as newest
  study in normal local climate-accuracy page. Observer/decode/frame/cap tests6pass; all new figures posted.
* Do NOT call this a global minimum or a six-coast improvement. It reveals joint sea/land compensation;
  any broader refit needs multiple starts (r44 and warm15_C3 useful contrast), aggregate v3 scoring without
  old per-group penalties, broader49+spent sensitivity, marine adequacy reported, finer checks + newly
  declared independent milestone. No new sealed pool or atlas climate replacement. r44/v2.2 remains adopted.
* Audit CLI now accepts --plan/plan.cell_km and records canonical full-field rain_loss beside T/marine
  diagnostics. Exact previous audit source retained in d0099f9e; current pilot source in4fba2f09. Use NEW
  output directories after source changes, do not overwrite historical protocols. Dataset register updated.
* Frozen new plan/candidate JSONs and reference receipt have -text attributes for Windows byte hashes.
* Final QA: browser75studies/173images PASS, light/dark/mobile/JSON downloads; Windows1550byte-exact
  assets PASS; portable2142files/703links/fresh launcher PASS. Nine new frozen plan/candidate/reference
  files separately pass Windows core.autocrlf byte-hash check. Evidence in output/shared_sst_screen_20261109.
  Bundle /tmp/rotclimate_v22_atlases.zip refreshed. Main Earth/free/Whittaker map folders unchanged this round.

# P8b audit COMPLETE — 9 November 2026

* Frozen6regions x r44/rejectedC3 audit complete; no fit or new sealed pool. All12 numerical checks pass.
* Final outputs output/air_sea_audit_20261109_operator_state; original outputs output/air_sea_audit_20261109
  retained. Cap count at coefficient state is78.7%Japan/75.3%Korea vs solved-air90.6/88.2 (small fixed-point
  differences counted in original); replay_check proves all climate/flux monthly arrays EXACTLY identical.
* Four original hook/frame/unit tests plus new NOAA decoding and cap-state tests:6pass. Observer on/off all
  model fields bit-identical on r44 andC3. NOAA static netCDF4 references metadata-verified1991-2020 sigma.995;
  h5py optional dependency added. Raw reference cache ignored, reference.json + URL/hash metadata tracked.
* Strong compensation evidence: TopEnd SST−4.25C; Levant SST−3.48C, C3 landMAE2.006->1.792 but marine-air
  bias−.13->−1.17C. NewGuinea land worsens while marine air warms .37C. Not one universal cooling mechanism.
* Reports/AIR_SEA_AUDIT_20261109.md; scripts/publish_air_sea_audit.py adds two plots + JSON to normal local
  climate-accuracy page, newest study first. Browser74studies/172images passes, light/dark mobile/downloads.
  Exposure register explicitly marks reused/spent cases. Earth r44/v2.2 map data remain unchanged.
* Next: screen four shared SST-offset/current-strength directions, with/without C3, under fixed Earth
  forcing/geography and verified numerics. Need rainfall_loss alongside T and marine monthly-curve MAEs.
  Before changing audit CLI for configurable plans, commit this exact audited source/version and results.
  Pilot only; no adoption from six development regions. Broad49/finer gates + new independent milestone
  needed before any future r45. No regional masks or observed SST/wind inputs allowed.

# P8b heat-exchange diagnostic — 9 November 2026

* Frozen plan calibration/air_sea_audit_20261109/plan.json: six known/spent regions x r44/failed P8a C3,
  56km; no new coefficient, fit, sealed pool or adoption. Driver scripts/audit_air_sea_exchange.py.
* Added opt-in model.heat_record: final output-year last linear heat solve's actual SST, solved air,
  rate-evaluation air, relaxation rate and heat winds. No physics equation changed. Four tests PASS:
  r44/C3 observer-on/off every field and numerics bit-identical, units and southern calendar/wind frame.
* Audit output output/air_sea_audit_20261109. Driver downloads sigma0.995 air/winds, verifies NOAA DAS
  period1991-2020 and units, hashes sources, freezes protocol, compares WOA SST separately. NCEP is sigma
  0.995, NOT a fixed995hPa level; older report mislabels the coordinate. Do not infer observed flux from
  mixed-period NCEP/WOA climatologies. Recorded model flux is conditional on assumed slab depths.
* Code observation: P8a nominal2K/day cap retains baseline lambda floor, so is not a universal hard cap.
  Quantify on actual solver states; preserve rate-state vs solved-air difference within .05C convergence.
* Run: OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -I scripts/audit_air_sea_exchange.py
  --workers3 --out output/air_sea_audit_20261109 (use actual CLI --workers 3).
  Keep model modules + driver fixed while running; each region/config JSON and final summary are resumable
  only against the same protocol. Add plots/report and development-only diagnostic to accuracy page after.
* Active Earth atlas remains r44/v2.2, both branches at029ef42a before this audit; no map regeneration needed.

# v2.2 Earth atlas released — 9 November 2026

* Complete r44/v2.2 lake + delta atlas, including both raw/corrected food, administration, work, fertility,
  settlements and control, is published locally under atlases/earth_fit. Hub + release manifest refreshed;
  normal .bat launcher verifies Earth r44 snapshot572564df73bd. Free/Whittaker folders remain EXACT archives.
* Missing r44 correction final/fold models and portable release dependencies were recovered, tracked and pushed
  in 9a95cf71. Replayed original rounded CV scores, not new unseen gains; do not relabel models as old bytes.
* Full driver completed output/atlas_v22_calendar_fix/stages_done. Original output/atlas_v22 climate stages
  reused under an explicit receipt; only failed cereal-work CLI producer changed. Fix2b84be09 uses Harvest's
  full delta irrigation, not geometry() alone. Both crop-parity checks pass (max20.9kcal/ha packet rounding).
* Publisher now preserves labour-grid downloads through the hash-pinned ancestor review; six provenance
  tests cover missing/ambiguous/changed grids. Canonical browser checker tests ACTIVE atlas, both control
  variants, current scenarios/CSVs, mobile and failure isolation. Archives are kept exact, not upgraded to
  current UI requirements. Mobile scenario-label overflow fixed in shared template, copied to Earth only.
* QA in output/atlas_v22_calendar_fix: browser_smoke.json PASS; settlement_browser/review.json PASS
  (raw/corrected,792 CSV rows, defaultv2.1, work grids, four failure modes); ledger_audit.json PASS
  (529080 site-bin ledgers, includes historical packets); windows_checkout.json PASS1545byte-exact assets;
  portable.json PASS2135files/696links/fresh launcher; publication_tests.log8pass (6 provenance+2packaging).
* Bundle /tmp/rotclimate_v22_atlases.zip includes active Earth + retired snapshots, current release/recovery/
  cereal methods and lake/delta figures. README now correctly calls Earth active. Dataset exposures f/g/h SPENT.
* Comparison output/atlas_v22_calendar_fix/release_comparison.json: corrected food ceiling226.340->226.412M;
  default held land67.4078->67.4735%, sources1010->1011. These are scenario outputs, not Earth-validation gains.
  EXPORTED corrected target38.4480->38.4564%; MONTHLY correction gate38.5488->38.5657%. Don't conflate them.
  River check107systems/11through-lakes passes; extra3years land monthly rain change<=.15mm.
* Joint guard follow-up COMPLETE: require_strict now rejects observed winds (as it already rejects observed
  SST). 27 joint/input tests PASS; both Earth/world boundaries reject substitutions, direct Earth diagnostics
  remain available, real solver invariance passes. Adopted r44 model-wind outputs unchanged; no atlas rebuild.
* Page refresher now selects ACTIVE rather than merely excluding the two named retired fits; older
  earth_physics page also stays byte-identical. Actual refresh verified all3 inactive pages preserved.
* Next actual physics design: reports/PHYSICS_NEXT_20261109.md (heat-flux audit then multiple starts under
  fixed Earth forcing). P8a failed h, r44 remains adopted. No new independent Earth accuracy claim this round.
* Source freeze has ended. Completed build identities deliberately retained; future source changes require
  a NEW ROTCLIMATE_V22_OUT rather than rewriting these successful runs' manifests.
* Cache preservation: output/atlas_v22/cache_archives.json records verified gzip copies of new checkpoint
  PKLs. Raw paths symlink to /tmp; if lost, restore from gzip+SHA (no re-simulation). Old ZIPs/atlas backups
  also preserved in /tmp; locations output/atlas_v22/prior_backup_locations.json. Active site stays in workspace.

# r44 models RECOVERED; v2.2 release ready — 9 November 2026

* Full original reconstruction pipeline completed and its receipt verified.
  New T cluster-CV1.5062430788C, rain loss0.43177809165: both reproduce the old
  rounded1.506 / .4318 references. New hashes, NOT byte-identical originals.
  All final/fold models, protocols, metrics and release dependencies now tracked.
* scripts/freeze_r44_corrections.py first verifies full training/source/observation
  receipt, then freezes a small release manifest so applying models does not
  require an untracked raw training cache. check_v22_release_inputs verifies this
  manifest plus actual model physics and stale resume identities. Actual artifact
  preflight passes; intentional stale resume was rejected.
* v2.2 world checkpoint regenerated: output/r44_lakes_world/candidate_001.pkl
  (87MB, intentionally local simulation cache). Strict observed numerical checks
  passed. --simulate-only exported no site assets. No physical model source
  changed during generation; keep them fixed for release checkpoint identity.
* Current local accuracy page now correctly says r44 (it said current r43).
  49-region RAW original development: T1.861483C / rain.488261; separate31-region
  correction replay raw T1.699588->1.506243 / rain.442646->.431778. Do NOT mix the
  two pools into a paired improvement. Earlier labelled studies retained.
* scripts/publish_current_earth.py reproduces overview/figure/data; dataset
  exposure download now matches current source register (f/g/h SPENT). Recovery
  figure posted in chat. Methods reports/R44_RECONSTRUCTION_20261109.md.
* release_v22_deltas now refreshes current accuracy + hub after pages, so the
  normal .bat release fingerprint is updated after data promotion. See existing
  driver stages for pending world export/diagnostics/add-ons. Earth only; free
  and Whittaker folders remain exact retired snapshots.
* Tests this round:36 joint+soil/fertility before integration addition, then27
  joint/release/launcher (includes actual rejection of r43 corrections on r44).
  Hub browser desktop/mobile/archived links passed; Windows checkout1509 assets
  passed before recovered model byte-check extension (rerun final staged site).

# Local hub / release preflight — 9 November 2026

* Joint repair + reconstruction preregistration pushed8a3871c7 to both refs.
* r44 correction reconstruction RUNNING through existing retrain driver. Main
  log output/earth_correction_r44_20261107/reconstruction.log; per-stage logs in
  same folder. Dev31/fine28/fine14 simulations complete; old correction cases
  and fitting/field collection follow. These are REPLAYS, not fresh validation.
* Preparing v2.2 verified world checkpoint with new --simulate-only option in
  scripts/build_atlas_variant.py. Tool session91680; log same reconstruction
  folder/world_checkpoint.log; checkpoint output/r44_lakes_world/candidate_001.pkl.
  No live atlas touched. Model source files must stay fixed while these run.
* Latest checkout had stale local hub/release manifest (unverified startup), even
  though Earth atlas data are r44. build_fit_hub now uses atlas_set.ACTIVE for
  the main plate and explicitly archives free/Whittaker. All3 data snapshots
  remain checksummed. Launcher marks retired snapshots and defaults to Earth
  if no hub exists. Browser desktop/mobile + archived URLs passed; launcher
  now verifies Earth r44. No scientific map data changed by this refresh.
* scripts/check_v22_release_inputs.py blocks missing/mislabelled correction
  models and stale resume identities BEFORE simulation/export. Release driver
  calls it and accepts ROTCLIMATE_V22_OUT for a new run directory. Do not
  promote v2.2 until recovered models/receipt verified. R43 metadata relabelling
  is rejected by an actual-model/protocol hash test.
* After fitting, force-add recovered final/fold NPZ and protocol/evaluation
  JSONs so future checkouts contain them; write a reconstruction result that
  compares actual hashes with lost original hashes, and CV with prior rounded
  reference T1.506C / rain.4318. Then complete v2.2 lake/delta release, normal
  browser/Windows/portable checks and push. No new sealed f/g/h pool to open.

# Resume / joint-boundary repair / missing r44 corrections — 9 November 2026

* Fetched and fast-forwarded from a3b07756 to latest21e7c215. Earth fit only;
  retain free/Whittaker snapshots. Uncommitted old crop-water draft superseded
  by Nov6 soil_water_dual/fertility work; preserved under ignored
  output/local_drafts_20261109/abandoned_water_prototype.
* Reproduced14 failures in tests/test_joint_inputs.py: nine Params fields not
  partitioned. Fixed terrain_file as WORLD geography and eight storm_plateau
  response/switch fields as SHARED physics. Tests prove invented terrain never
  enters Earth, stale world physics cannot replace shared values, and real
  solver output is identical under irrelevant world changes.36 targeted tests
  pass. No physical equation, r44 coefficient or Earth forcing changed.
* v2.2 terrain/lake+delta release is NOT yet in the local atlas. Its checkpoint
  output/r44_lakes_world/candidate_001.pkl is absent (regenerable). More critically
  calibration/earth_correction_r44_20261107/{temperature,rain_pattern}/correction.npz
  were never committed/saved; owner confirms no separate copy. Do NOT substitute
  r43 models or change their metadata to r44.
* Recovery plan pinned before retraining at
  calibration/earth_correction_r44_20261107/reconstruction_plan.json. Use existing
  scripts/retrain_earth_corrections.sh, TAG=r44, canonical r44 OUT/CAL. Original
  rounded cluster-CV reference T1.506C / rain.4318; not a tuning target. New
  hashes and model protocols must be committed (force-add ignored calibration
  folders). Whole-cluster dev31 CV; old Norway/SE Africa checks are SPENT
  reproduction, not fresh validation. No new sealed pool opened.
* Workspace is tight. Three generated portable ZIP backups moved to /tmp
  (rotclimate-atlases-before-20261109.zip, rotclimate-r43-before-20261109.zip,
  rotclimate-r42-before-20261109.zip) to preserve them while freeing build space.
  Rebuild the current portable bundle after release; do not delete science inputs.

# Owner preference (8 Nov 2026): post every new map or figure in chat (SendUserFile) as soon as it is generated.
# P8a coast coupling refit — 8 November 2026 (NOT adopted)

* New switch e51b `ocean_unstable_cap` (K/day ceiling on e51 convective warming; default off; rotclimate/model.py).
* Screen (12 dev regions): e51 alone overheats East Asia winter; e3 alone and e51+e51b(2 K/d)+e3 help.
* Plan calibration/maritime_p8_20261108: 4 candidates all pass dev49 (S49 0.991-0.993) + 28 km; finalist C3
  (e51 0.5 d, cap 2 K/d, e3 0.5 d). Owner released sealed set h: S 1.0014 FAIL (Top End 2.02 -> 2.24, New Guinea
  1.58 -> 1.73; tropical coasts cooled by e3). r44 stays; set h SPENT. Next climate milestone needs a new sealed set.
* Note: joint.validate_partition() already fails on 9 unclassified older fields (storm_plateau_*, terrain_file).

# Tiered colours on the hosted atlas — 8 November 2026

* Cause: the host caps an artifact at 511 files, so earlier publishes left every *_tiers.webp out (89 files); the hosted
  page then asked for missing images whenever "Tiered colours" was on. Locally it always worked.
* Fix: scripts/package_atlas_artifact.py bundle_tiers() concatenates the tier images into data/tiers_bundle_<k>.wasm
  (8 MB parts; 2 parts, 14.5 MB) and writes meta.tiers_bundle {parts, files: path -> [part, offset, length]} into
  data/atlas.json; atlas/index.html tierImage() cuts the image out in the browser (smooth ramp while loading). No
  bundle locally, so the local atlas still loads the files. Checked all 33 tiered layers, both climate modes:
  27 from files / bundle (pixel-identical) + 6 drawn by population.js; smoke passes. Hosted Earth fit v44
  (496 files). Next pack diff base: scratchpad pack_d2. Month layers have 11 frames by design (11-month year).

# Population ledger P3, blind on Domesday 1086 — 8 November 2026

* Plan calibration/population_ledger_20261108/plan.json (+ amendment 1); scripts/population_ledger_p3.py; report
  reports/POPULATION_LEDGER_20261108.md. Owner supplied the Hull places + statistics databases (Access .mdb, CC BY-NC-SA)
  -> data/cache/domesday/ (gitignored; access_parser in .venv).
* Dev (seen): Han AD 2 rank P0 capacity 0.287, P1 base 0.428, P2 heartland occupancy 0.820; ten-region RMS ln 1.653 -> 0.965.
* Blind (once): 20 km blocks rank P0 0.395, P1 0.431, P2 0.630 (all pass >= 0.30); England total P0 9.95 M, P2 0.79 M
  vs 1.2-2.6 M (fail) -> atlas keeps the supplied budget. Badges: land_density partial (0.43), land_density_cores
  experimental -> partial (0.63, now in the core view). Hosted Earth fit v43 (evidence.js). Domesday SPENT.
* Next for the level: occupancy that grows with time since first farmed/governed (F15b + polity age), fresh blind pool.

# Owner decision (8 Nov 2026): the free and Whittaker fits are RETIRED; work focuses on the Earth fit only.
* scripts/atlas_set.py (ACTIVE = earth_fit) filters every add-on loop and scripts/refresh_atlas_pages.py; atlases/free_fit and
  atlases/whittaker_fit stay as their last published snapshot (hosted pages untouched, not deleted; URLs in
  atlases/artifact_links_retired.json, removed from artifact_links.json so the Earth-fit pack drops its links to them).
* Release driver for the Earth fit only: scripts/release_earth_fit_d1.sh (D2b re-export on the staged atlas, promote, add-ons).
* RELEASED + HOSTED 8 Nov 14:47 / 15:00: Earth fit with D1 + D2 + D2b + fine simulated rivers (smoke passes, 70 layers);
  hosted https://claude.ai/artifact/ABFAoyPzTuMNVWmByPxctF versions 40-42 (pack diffed against scratchpad pack_r44r; next
  diff base: pack_d1). Food capacity 255 -> 225 M, settlement scenario 186 -> 165 M, control held 68.2 -> 67.0 % (raw).

# Block D: arable land from slope (D1) + irrigation by height above the river (D2) — 8 November 2026

* D1 (calibration/geography_control_20261107/plan_D1.json): arable share a(S) = 0.018 + 0.982 / (1 + (S / 2.75 deg)^1.29)
  of the ~1.85 km slope, fitted on Copernicus GLO-90 with the GAEZ slope rule; blind tiles 12/12 better (RMSE 0.308 ->
  0.184, bias +0.036). Map (harvest/export.py geometry, atlases with a terrain file): tiers 0.85/0.58/0.44/0.30 (were
  constants 0.85/0.75/0.45/0.08); land mean unchanged (0.744 -> 0.739). data/arable_slope_model.json.
* D2: irrigation x exp(-H / 10 m), H = height above nearest river; HID 1900 (Siebert et al. 2015) blind AUC 0.539 -> 0.671.
* Earth harness on both (scripts/land_people_earth.py defaults --arable slope --irrigation hand; ETOPO 60" via
  scripts/arable_slope_earth.py; irr_distance kept for water distance in polity/earth.py). FALLOW 0.68 -> 0.600 (NCP AD 2
  census). No-harm: regional populations RMS 1.701 -> 1.652 (Egypt worse: Nile floodplain wider than the 6 km distance
  rule); control dev BA Rome 0.8488 -> 0.8485, Han 0.6637 -> 0.6628 (whole Earth chain rebuilt in a worktree).
* D4 (roads) already on the eroded terrain by construction (travel graphs use the atlas elevation). D3 (valley towns)
  inherits through density (D1) and the site score's flat-ground and river terms; no separate Earth refit yet.
* Release: scripts/release_d1_arable.sh + release_d1_arable_addons.sh (Earth-fit from the v2.1 checkpoint; free and
  Whittaker food chain refreshed in place, backups in output/atlas_d1/previous_atlases). Report: reports/ARABLE_SLOPE_20261108.md.
* D2b (plan_D1 "D2b", scripts/irrigation_reach_d2b.py): reach 6/12/24/48 km x H0 5/10/20 m scored on AUC + amount vs
  HID 1900 (arid cells); dev chose 6 km x 5 m; blind Americas (now spent) amount 2.51x -> 2.33x, AUC 0.725 -> 0.726: H0
  10 -> 5 m (harvest/export.py IRRIGATION_HAND_H0, land_people_earth.HAND_H0). FALLOW kept 0.600; regions RMS 1.652 ->
  1.653; Egypt +0.64 -> +0.72; control dev BA Rome 0.8485 -> 0.8485, Han 0.6628 -> 0.6628. ADOPTED. Wider reach ranks better but over-irrigates more. Residual = Nile delta fan (12.5k km2 HID
  vs 5.2k model: distributaries) + arid rivers over-irrigated where 1900 is history-shaped (Mesopotamia, Niger).
  Exploration scripts/explore_irrigation_discharge.py (dev only; route over a domain 8 deg wider; burn NE rivers; WorldClim
  lakes passable). Map refresh: scripts/release_d2b.sh (Earth-fit only; it alone has a terrain file).
* Block D CLOSED (plan_D1.json closing_note): delta rule not for the map (map coasts sit at ~1 m by construction, so a
  height-based delta rule would irrigate every coastal lowland); D3 covered by the settlement model's fitted suitability
  (slope / relative elevation lost LOPO) + D1 density; D5 = v2.1 on the terrain-aware chain, dev unchanged, released.
  Next per reports/CONTROL_MAP_V2_PLAN_20261107.md: Steps 2-3 (village-scale settlement + predicted population ledger),
  Domesday 1086 blind declared before download. Still open: the evolve() m^4 units refit (B2, hill fit, plan_R1).
* Domesday pool reserved (dataset_usage.json domesday_1086_blind), NOT downloaded. Access (8 Nov): the Open Domesday API
  (opendomesday.org/api/1.0/...) returns 404 on every endpoint; the Hull data moved to digitalcollections.hull.ac.uk
  (collection 3t945r28b: Places database + statistics content.accdb, CC BY-NC-SA 2.0 UK) behind a browser bot check;
  UK Data Service SN 5694 needs a registered login. Needs the owner to download the files (or choose another pool).

# Drawn rivers kept in the eroded map (plan_R1) + height map as climate lever (plan_T1) — 8 November 2026

* Owner: "all of our drawn rivers also have to be there in the eroded map". Strict check (scripts/terrain_rivers.py check):
  released v2 failed (1.3 % of drawn-river cells drained along the river; 0/107 rivers). Height map v2.1
  (output/terrain_erosion_20261107/map_height_v21.npz): 100 % / 107 of 107, 0 climbs, below every bank. Hybrid
  breach-fill bed at 0.6 x tier ramp + 11 px valley + banks +10 m + Barnes 2014b flats + PF-eps; Earth-fitted on the
  B2 ETOPO windows (joint loss 1.70 -> 0.72 dev, 1.35 -> 0.93 check); hills now tier-1 only, 1,600 m (Earth lowland
  KS 0.045). Tiers 2-4 band shares 0.984/0.516/0.862 (v2 0.962/0.495/0.832). Climate: +0.12 pts corrected vs v2,
  climate-grid river recall 0.65 -> 0.77. Report: reports/RIVERS_TERRAIN_20261108.md.
* Bug found: fastscapelib accumulate() multiplies by cell area; areas passed accumulate(dx^2) were m^4 (river boost
  inactive; "rivers_on_channel 1.0" and B2 M3 = 1.00 meaningless). Reported areas fixed; evolve() numerics kept
  bit-identical because every Earth fit used them. Fixing evolve properly = re-run B2 dev, hill fit, plan_R1 fit.
* plan_T1 (owner: height map helping the climate calibration, tiers intact): band position per upland tier gives
  +0.29 pts corrected (uplands low in their bands, both halves better) < frozen +0.5; ceiling of the lever +0.44.
  Steering tier-1 hills hurts (hills are zero-mean relief). Not adopted. The painted-zone misfit is lowland moisture.
* RELEASED 8 Nov 02:22 (smoke passes free/earth/whittaker; live r44-on-v2 backed up in output/atlas_r44r/previous_atlases).
  Hosted: earth v39 (447 changed files in 4 batches; *_tiers.webp still left out for the 511-file cap), free v35,
  whittaker v24 (13 changed add-on files each).
  Release: scripts/release_r44_rivers.sh + release_r44_rivers_addons.sh (checkpoint output/r44_rivers_world from the
  v2.1 climate check via scripts/make_release_checkpoint.py; params calibration/map_world_r44_terrain21). build_control_v21
  now shades with the atlas's own terrain_file.

# RELEASED: Earth-fit atlas r44 + height map v2 (task 84 + plan D) — 7 November 2026

* Params.terrain_file (rotclimate/config.py; geography.elevation_fullres, climate grid, render.py, atlas.py) -> height
  map v2 everywhere in the Earth-fit atlas (calibration/map_world_r44_terrain/params.json). Climate check (plan_D):
  strict zone agreement +0.73 raw / +0.60 corrected, |dT| 0.39 C. r44 corrections in the corrected climate.
* scripts/release_r44_terrain.sh (staged base) + scripts/release_r44_addons.sh (promote + all add-ons, compute ->
  publish order); live r43 backup local in output/atlas_r44/previous_atlases/earth_fit_r43. Smoke passes all three.
* free_fit / whittaker_fit keep the tier ramps (height map v2 is built on Earth-fit tier tops); their add-ons were
  recomputed consistently. Report: reports/R44_TERRAIN_20261107.md.
* Hosted (republished 7 Nov): earth v35 (4 batches; 492 data files, *_tiers.webp left out for the 511-file cap),
  free v34 and whittaker v23 (22 changed add-on files each; .gz sent as application/wasm).

# Owner: unmarked hills allowed; deserts may be holes — done 7 November 2026

* Height map v2 revised (plan_B2 map_v2_B3_revision_1): no tier compression; Earth-fitted unmarked lowland hills
  (terrain_erosion.hills: 2nd steady-state run, log-normal uplift 80 km / sigma 1.2 / 1,000 m, soft cap 500 m) so
  tier-1 slopes of ~9 km block means match Earth lowlands (median 0.160 vs 0.167 deg; KS 0.069; hill_fit.json).
  Tier-1 elevation p90 164 m, p99 502 m. Rivers 100 % on channels. Climate still on today's elevation.
* plan_A3: enclosed pockets with median P/PET < 0.2 or < 0.5 people/km2 stay holes. Blind 1200 / 1820 / 1500 (spent):
  BA unchanged (0.744 / 0.360 / 0.600) -> adopted. Map: 0.1-0.85 % of land returns to holes.
* Earth-fit control v2.1 shading now from height map v2 (display only; free/whittaker keep their own tier shading).
  Hosted: earth v31, free v33, whittaker v22. Next for the owner to choose: plan D rebuild on height map v2.

# A2 / C1 results: borders follow food, towns and enclosure, not slope, ruggedness or forest — 7 November 2026

* A2 (plan_A2.json): ruggedness travel cost (1 + beta R) lowers dev BA for all beta > 0; beta* = 0; blind pools
  1200/1820/1500 NOT opened (released unused in dataset_usage.json).
* v2.1 cartography + painted claims (light tint + fine line where claimed but unheld). Hosted: earth v30, free v32,
  whittaker v21. Smoke passes.
* C1 (plan_C1.json + amendments 1-2, REVEALS TW6 in data/cache/reveals_20261107, CC BY 4.0): Whittaker biome lookup is
  wrong for temperate Europe (woodland/shrubland -> 0 forest; open land overstated by 0.29). Adopted C1b: forest =
  clip((P/PET - 0.3)/0.2) x clip((GDD5 - 300)/300) x 0.60 (blind open-land RMSE 0.326 vs 0.556). Population clearing
  not adopted (0.346). No rank skill anywhere (|rho| <= 0.11). C1b not yet wired into the map (C2 travel test pending;
  effect is a near-uniform ~10 % friction change).
* Report section 8 lists options for the owner: D rebuild on height map v2; cartographic frontier smoothing; C2.

# B done to owner review: height map v2; discs are the travel model, not the terrain — 7 November 2026

* plan_B2 (amendment 1 before blind): C* (m 0.35, noise 24 km, sigma 0.6, boost 10,000 km2, no smoothing) adopted:
  blind divides better 3/4 (Guizhou worse), slope KS 4/4. Map v2 = ramps + compressed eroded detail (tier 1 x0.50,
  tier 3 x0.82), rivers 100 % on channels, bands pass the Earth reference - 5 pts; climate keeps today's elevation.
  output/terrain_erosion_20261107/map_height_v2.npz (committed); review figures reports/figures/height_map_v2_review_*.png.
* KEY: real-terrain 2-day Tobler zones are discs too (IoU 0.92-0.98 vs ramps, circularity 1.15). Next: Earth-fit a
  terrain-channelled travel cost (pack animal / cart slope response, valleys, passes) + two-state border test
  (CHGIS 1200 Southern Song vs Jin, declare first), then C land cover, then D rebuild. Downstream waits for the owner's
  look at the height map.

# Geography plan: A shipped (control v2.1 default); B generator + Earth test running — 7 November 2026

* Owner: "go with what you think" -> recommended defaults (tiers kept at climate scale with Earth-like relief inside,
  rivers within 1.8 km, ungoverned pockets as an explicit class, order A -> B -> C -> D).
* A (plan_A.json): summed influence C* (tau 2 d, lone reach 2.5 d) dev mean BA 0.763 -> 0.820 but blind late antique 550
  0.752 vs v2 0.766 (fails by 0.004; dense Pleiades sources inflate a sum). Fallback F = v2 + enclosed pockets passed
  (Song 1080 0.697 -> 0.737, 550 0.766 -> 0.774) -> atlas default "v2.1" (scripts/build_control_v21.py; flat fill over
  hillshade, border lines, hatched unadministered upland 2-3 % of land, MMU 3 cells). Hosted: earth v29, free v31,
  whittaker v20. Round-2 idea: saturating union 1 - prod(1 - p_s) instead of a sum (needs a new blind pool).
* B: scripts/terrain_erosion.py = steady-state stream power (chi integral of k_sn A^-m on fastscapelib routing, k_sn
  rescaled to the tier ramps at 14 km; marked rivers burned + boosted). Map preview uncalibrated
  (reports/figures/terrain_erosion_preview.png). Earth test scripts/terrain_earth_b2.py (plan_B2.json, ETOPO 60"
  windows in data/cache/etopo2022_60s via OPeNDAP). First dev look (Apennines): divides 16.7 -> 11.5 km, slope KS
  0.59 -> 0.11, isochrone IoU 0.932 -> 0.951. Real terrain keeps only ~50-60 % of middle tiers inside their bands, so the
  map's faithfulness check uses the Earth M5 reference. M3 (new rivers at 500 km2) is degenerate (sketch covers them).

# Owner: control v2 is dotty; geography should shape borders -> plan written — 7 November 2026

* Diagnosis (output/control_v2_20261107/diagnostic_dots.json, reports/figures/control_v2_dots_diagnosis.png): map slope
  median 0.025 deg vs Earth 0.30 (tier 1 = 70 % of land spans 0-62 m; tier ramps are smooth domes); small held patches
  circularity 0.96 (2-day discs); 161 enclosed holes (141,000 km2) are uplands (765 m vs 39 m, forest 40 vs 20 %).
  Earth: Roman/Han frontiers enriched on desert edges (56 vs 12 %, 25 vs 7 %); relief/rivers mixed.
* Plan: reports/GEOGRAPHY_CONTROL_PLAN_20261107.md. A (summed influence, governable-hole rule, cartography), B (eroded
  height map: stream power + imposed marked rivers + tier projection at climate scale; Earth "posterize and
  reconstruct" test), C (forest: PNV + KK clearance, REVEALS blind), D (rebuild chain, control v3), E (crossings,
  passes, soils, coasts, floods). Owner decisions listed in section 5 (tier strictness, river exactness, holes, scope).

# r44 on the map: raw climate IDENTICAL; corrections retrained — 7 November 2026

* scripts/check_r44_map.py (output/r44_map_check/summary.json): map world (seeds 1-3, downsample 8) under r43 and r44
  (calibration/map_world_r44/params.json = r43 world + four e72 fields): T, P, u, v max |diff| 0 (bit-identical; no map
  plateau). r44 corrections (calibration/earth_correction_r44_20261107; held-out T MAE 1.506 vs r43 1.537 C, rain loss
  0.4318 vs 0.4384) move the corrected map -0.39 C mean (|d| 0.41, p95 0.77, max 1.30 C), rain ratio median 0.998
  (5-95 % 0.925-1.083); corrected strict zone agreement 37.70 -> 37.83 %. r44 checkpoint: output/r44_world/ (local).
* NOT yet released into atlases/earth_fit: the corrected-mode cascade (add_corrected_climate.py, then pasture, farm work,
  administration, coverage, presence, settlement fertility chain + control v2) must rerun on the r44 corrections; the
  atlas stays r43-labelled until then. Raw-mode packets need no change.
* Sealed set h declared (calibration/sealed_20261107h, eight unseen climates) for the next climate milestone (P8).

# Control map v2 PUBLISHED as the de facto default; settlement model blind-tested — 7 November 2026

* Supply-supported reach opens on v2 (joint365 staffing + P2: staffed towns and the painted roads within 2 year-round
  days of them; held where the nearest polity <= 2 days). Built by scripts/build_control_v2.py (output/control_v2_20261107):
  held land free 65.2 %, earth raw 66.0 %, earth corrected 67.2 %, whittaker 63.8 %. The publisher adds the option
  (publish_settlement_integration.py --origin output/settlement_fertility_20261106). Smoke passes all three (local + packed earth_fit).
  Hosted: earth v28, free v30, whittaker v19 (only changed files sent: page, evidence.js, settled-reach.js,
  data/settled_reach.json, v2 webp; earth_fit now 494 files).
* polity/settle.py restored to its reviewed bytes (the settlement chain hashes it); the configurable calibration copy is
  polity/settle_experiments.py (identical towns at default arguments).
* Unmarked settlement model (calibration/settlement_model_20261107/plan.json, reports/SETTLEMENT_MODEL_EARTH_20261107.md):
  fitted weights NOT adopted (G2 fails by 0.003). Current model blind: Sui 610 count +11 %, F1 0.48 at 25 km, block rank
  0.29, AUC 0.63 for 1300 cities beyond the limes. Towns too even (spacing KS 0.76): real clustering is population
  history, so next step is a time-dependent population ledger as the density input (task 83 + F15b). S1/S2 spent.
* Round 2 (plan_round2.json): towns on the Earth-tested cored density (old heartlands, L 800 km). Dev mean F1 0.453 ->
  0.533, block rank 0.274 -> 0.512. Blind Tang 742: F1 0.538 -> 0.551, M1 0.40 -> 0.50, KS 0.80 -> 0.74, but count -20 %
  (G4) and 1300-city AUC inside the limes 0.771 -> 0.754 (G5) fail: NOT adopted. Round 3 idea: E1 count from the bare
  density, sites from the cored; needs a new blind pool (no unspent AD~200 site pool known). Tang 742 + 1300-inside spent.

# Fertility integration PUBLISHED — default bare three-field at AD 200 N 27.5 — 6 November 2026

* User chose: fix low-N artifact, then bare three-field default. Fix: residues scale with stand
  below 0.5 t grain (STAND_T; option, rounds 1-2 reproducible); recheck on spent data: dev loss
  0.1711 -> 0.1705, Broadbalk 1926-67 unchanged.
* Map (bare / joint365): sources free 201/1,207, earth raw 278/1,044, earth corr 273/1,064,
  whittaker 333/1,053; cereal 0.53-0.84x; access 2-3 vs 7 bins. Clover third: 614-1,010 sources.
* Published into atlases (publish_settlement_integration.py --origin
  output/settlement_fertility_20261106); viewer default fert_bare. Hosted artifacts republished
  (earth v25, free v27, whittaker v16) incl. coverage/administration/presence/pasture/farm-work.
  Packager fixed (raw feature packets, manifest .wasm refs, .gz as application/wasm); hosted
  earth_fit drops tier twins (511-file cap). Smoke passes all three.
* Report: reports/FERTILITY_INTEGRATION_20261106.md.

# r44 ADOPTED (r43 + e72d plateau-steered storms) — 7 November 2026

* e72c failed sealed set f (S 1.011, eastern Siberia); e72d (reach 15 deg, split jet) after declaring set g:
  S49 0.9902, 28 km 0.9859, unseen set g 0.9785 (five boxes; yunnan excluded before outcome: overlaps policy-v2 sealed).
* r44_params.json + r44_adoption.json (calibration/local_accuracy_20261023). Sets f and g spent; next unseen set must be
  declared before further climate development. Audit now reads every calibration region file.
* Map worlds unchanged (no plateau > 2.5 km). Next release step: retrain Earth corrections on r44, rebuild + republish
  the Earth-fit atlas (corrected default climate changes).

# P6 East Asia: e72c (plateau-steered storms) QUALIFIES on development data — 7 November 2026

* e72 (band meets plateau) inert: model band 40-53 N over East China all year. e72b (cold-season gate, window terrain):
  East China x0.904, S Brazil x0.880 but East Asia short. e72c (global 0.5-deg plateau ring, earth.plateau_profile):
  k10c East Asia rain x0.947, all-31 x0.987, T x0.990.
* Policy v3 gate (plan_gate.json): S49 0.9912 (T -0.86 %, P -0.89 %), S28 0.9859: PASS. retired_b 1.013 (reported).
* NOT adopted yet: the unseen sealed stage needs set f, which stays closed until the owner releases it.
  Candidate: calibration/east_asia_p6_20261107/candidate_e72c_k10c_params.json. Map world unaffected (no plateau > 2.5 km).
* Report: reports/EAST_ASIA_E72_20261107.md.

# Earth control round 2 + BLIND test — no food case passes; transport only stays default — 7 November 2026

* Round 2 (dev, plan d9d2ff99): scaled rural claim L1 (0.6 x produced) + reach P2 (staffed towns + roads within 2 year-round
  days): Rome 0.835 vs legacy 0.820, Han 0.682-0.692 vs 0.700; bare staffs 84 % / 92 % (40 / 76 % before).
* Blind (plan 092f4ab4, Pleiades Hellenistic 200 BC + Neo-Assyrian 700 BC vs Cliopatria any-state; now SPENT): G2 passes
  for all food cases (legume 0.654 vs 0.649, 0.612 vs 0.606), G1 fails in B1 (staffed 49-73 % of Pleiades settlements,
  which include villages). No default change. Lesson: next blind pool needs documented administrative/urban centres.
* e72 storm_plateau (P6) implemented opt-in (bit-for-bit off), dev31 screen running (output/east_asia_p6_20261107).
* Queue: reports/CONTROL_MAP_V2_PLAN_20261107.md (control v2, settlement spread, population; Domesday 1086 blind).

# Earth control test — transport-only map is the DEFAULT again (frozen rule) — 6 November 2026

* Plan d1935f2b (before results); scripts/earth_control_test.py runs the atlas chain on the Rome (Hanson AD 150 +
  Itiner-e) and Han (AD 2 seats) Earth windows. Report reports/EARTH_CONTROL_20261106.md; output/earth_control_20261106.
* BA Rome / Han: legacy_0 0.820 / 0.700; reference 0.697 / 0.641; joint365 0.698 / 0.633; legume 0.689 / 0.630;
  bare 0.606 / 0.603 (staffs 40 % of Roman towns, 76 % of Han seats). No food case passes G2; bare also fails G1.
* Default -> legacy_0 on Supply-supported reach and Settlements (atlas/settled-reach.js); "; default" dropped from the
  fert_bare label; every scored case's note carries its Earth result (publisher reads results.json); badges updated.
* Cause (post hoc): the every-month staffed-source patrol rule (no roads) loses 0.06-0.12 BA before food; bare fallow
  breaks the fixed rural claim (0.6 x old harvest) where F < 0.6 -> 23 % rural need unmet in Rome, no surplus.
  Next: rural claim scaled by F (one ledger); reach rule closer to transport (roads, year-round days); blind pools.
* Date palms: September harvest (perennial, no crop-window calendar), fixed before any Rome result.

# Atlas core view + evidence badges — PUBLISHED (3 atlases + hosted v26 / v17 / v28) — 6 November 2026

* atlas/evidence.js: tier + Earth test for every layer id (fallback by topic) and for the settlement /
  supply options (reach_defacto, reach_towns). Tiers: earth / partial / scenario (core view) and
  experimental / diagnostic (behind the "Experimental & diagnostics" switch). Sources: evidence_spec.json
  + reports (R43, POLITY_V3 / STRENGTH / SEASONS, FORAGING_EARTH, LANGUAGE_AREAS, FERTILITY_INTEGRATION).
  Painted-world atlases (no corrected climate / physics_profile) mark climate "partly tested".
* index.html: CSS-drawn badges (shape, not colour), topic names carry their best tier, legend ends with
  "Evidence: <tier>. <test>", minor sensitivities hidden from the option list (core: fert_bare default,
  fert_legume, joint365, legacy_0 = the only option scored on Earth as a control map, 0.81 / 0.80).
  Deep links to hidden modes turn the switch on; #all=1 and localStorage rotclimate-all keep it.
* Earth-fit core view: 56 of 82 layers, 11 of 15 topics. Smoke test records the core view, then checks
  every layer with the switch on. Update evidence.js when a layer's test status changes.

# Fertility integration (AD 200 N 27.5) — COMPUTED, NOT PUBLISHED, default undecided — 6 November 2026

* harvest/fertility_regimes.py (vectorised emulator, validated within 4 %, bare-fallow 19 % low),
  scripts/fertility_integration.py (earth / earth_figure / maps), scripts/extend_settlement_fertility.py
  (fert_transfer/bare/legume cases on the SAME chain, all 9 earlier cases kept), publisher note.
* Factor F = Y_land(regime) / (0.68 A0) (absolute; first ratio pass exploded, superseded before publish).
* Earth anchor: NCP needs no transfer (water-limited; m* = 0) -> transfer = bare. Census mean |log10|:
  previous 0.538, bare 0.407, legume 0.682 (Gaul 0.10-0.22 -> 0.55-1.24; Sichuan 0.09 -> 0.59).
  [Superseded by the stand-residue rerun 9decd991: bare 0.459, legume 0.685; Gaul 0.31-0.69, Sichuan 0.29.]
* Map: bare cuts wheat/barley grain to 0.42-0.77x and staffed sources ~1,000 -> ~200-330; legume
  1.2-1.5x grain. Zero-grain cells below 26 kg N uptake are a residue-relation artifact.
* Viewer default reverted to joint365; nothing written into atlases. Waiting on user's default choice.
  Report: reports/FERTILITY_INTEGRATION_20261106.md.

# Soil fertility ROUND 2 — credible equilibrium, QUALIFIES blind on Broadbalk 1926-67 — 6 November 2026

* Plan 517f33da (before fit/test read) -> amendment d5b57277 (crop N-demand curve; the
  only one; superseded fit A kept) -> selection 4d282c4c -> single eval 47a05f5c.
* Changes (options in harvest/soil_fertility.py; defaults reproduce round 1 bit-for-bit):
  measured start SOC (Broadbalk 28.8 t C 1843 e-RA; Hoosfield 33.8 RothC), I = F + measured
  wet deposition (Goulding 1998: 4 kg 1855 -> 18 kg 1980), thermal uptake in vegetated months
  capped by demand curve, fitted FYM humification (returned RothC 0.02), clover residues cut.
* Fit (spent data + Broadbalk SOC <=1914 + rwf3 aggregate): F 43.4, uptake 0.15, kappa 2.26,
  M0_woburn 1.55. FYM SOC matched; fallow +0.29 vs +0.14 long run; plot-3 SOC stays ~30 vs 24.
* Broadbalk 1926-67 (strips 3/21/22, 5 sections with fallow 1-in-5): T1 level 0.154 vs existing
  0.219, bias -0.065 (round 1 0.259, FAILS); T2 manure 0.137 vs null 0.322 r .15; T3 fallow
  0.135 vs 0.282 (obs x1.91, model x1.48; weeds not modelled). QUALIFIES. Now SPENT. Note 13
  of that dataset quoted one strip-14 value (not a target).
* Equilibrium (scripts/soil_fertility_regimes_r2.py sweep): at fitted ~52 kg input unmanured
  continuous 0.87 t/ha (Broadbalk plateau). Bare fallow ~no per-crop gain in equilibrium,
  halves per-land output. Clover rotation and FYM dominate.
* AD200 HINGE: non-fertilizer N input. Fitted value lumps real inputs + model loss error.
  Literature ratio pre-industrial / 1850-1925 ~0.4-0.65 -> 20-35 model kg -> per-land yield:
  unmanured 0.2-0.5, bare-fallow systems 0.07-0.25, W/B/clover 0.8-1.0, 5 t FYM 0.8-1.1,
  10 t FYM 1.4-1.7. Needs a decision or a further constraint.
* Next: integration step (declared): AD200 input; regime as land shares (crop / fallow /
  legume / pasture -> manure); per-cell equilibrium grain per land ha from climate + soil
  class (replace Rothamsted soil); feed shared grain -> residents -> reach. Check kappa
  outside England.
* Report: reports/SOIL_FERTILITY_ROUND2_20261106.md.

# Soil-fertility state (RothC + N) — QUALIFIES blind on Exhaustion Land — 6 November 2026

* NEW `harvest/soil_fertility.py`: RothC-26.3 carbon (published constants, from
  RothC_description.pdf) + SUNDIAL-style N (BIO/HUM C:N 8.5), one mineral pool,
  uptake, Burns single-reservoir leaching with dual-ledger drainage. N ledger
  closes. Drivers `scripts/soil_fertility_common.py`.
* Protocol: plan 288d1eaa (before any fit or Phase II read) -> amendment 7aaddff3
  (Hargreaves x monthly factors to RothC's Rothamsted 0.75*pan table, 448 vs 717
  mm/yr; spin-up 25 t C vs RothC 31; drainage 190-250 mm/yr vs 94) -> selection
  66c67e7b (fit on SPENT Broadbalk + Woburn: I 23.8 kg N/ha/yr, uptake 0.20/month,
  kappa 2.26 x A0, prior manure 2.42 t C/yr) -> single eval 55774a8a.
* Exhaustion Land 1902-1935 (rex4, CC BY; plots with 1856-1901 histories, nil
  since 1902, clover 1905/06-11 on 5-10): M1 manure memory 0.163 vs null 0.322
  r .68; M2 legume memory 0.212 vs 0.300 r .65; M3 level 0.161 vs existing 0.223
  (r .61 vs existing -0.59). QUALIFIES. Now SPENT. Misses: manure memory decays
  too fast (known RothC miss on Hoosfield 7-1), clover overpredicted, P/K adds.
* Disclosed: rwf3 (wheat-fallow) page aggregates seen -> development only. Scorer
  crashed twice before any output (serialisation; path); rerun deterministic.
* Woburn caveat: "unmanured" stratum includes plots 10a/11a after their 1877-81
  FYM; never-manured plots 1 and 7 run down MORE (wheat -42/-44 %, barley
  -70/-51 %). Report amended.
* NOT READY FOR PRODUCTION: regime preview (`scripts/soil_fertility_regimes.py`)
  equilibrium continuous unmanured 0.46 t/ha (Broadbalk plot 3 held 0.7-1.0 for a
  century with ~constant SOC); bare fallow no benefit (rwf3 says +0.14); floor
  collapses at lower N input (AD200 pre-industrial deposition is lower).
* Next: constrain equilibrium on development (Broadbalk plot-3 SOC stability +
  yield plateau, rwf3 aggregate), revise clover residues, ground AD200 N input
  (deposition + free-living fixation), then a fresh reserved test (Saxmundham
  rotations?). Regime choice (fallow/manure/legume) belongs to the shared
  settlement chain (manure <- livestock <- pasture), not a new map.
* Report: reports/SOIL_FERTILITY_20261106.md.

# Crop-water ledger + Woburn reserved site — 6 November 2026

* User priority: the Earth-calibrated basis for the control map (grain ->
  residents -> institutions -> reach). Post every figure as it is made.
* NEW `harvest/soil_water_dual.py`: FAO-56 dual coefficient (Allen et al 1998
  ch7 eq69-79 evaporation layer, ch8 eq81-88 root zone). ONE store; T and E are
  each debited once; drainage above field capacity; storage carries across seasons
  (no free sowing refill). 6 tests in `tests/test_soil_water_dual.py` (closure,
  bounds, bare soil <= TEW, no double spending, reduces to `soil_water_year`,
  stage-1 rewetting). Production still uses `harvest/soil_water.py`.
* Broadbalk DEVELOPMENT diagnostic (spent pool; declared in
  `calibration/low_input_yields_20261105/water_ledger_development.json`;
  `scripts/broadbalk_water_ledger.py`; output/broadbalk_water_20261106).
  Closure 1e-12 mm over 48 yr. Wetter = LOWER yield on every measure (winter
  drainage r -0.24 plot3 / -0.40 FYM; season E -0.43/-0.35; T ratio -0.19).
  Water is not limiting; explains old r -0.38. Drainage only ~94 mm/yr (Hargreaves
  high in humid climate, July 146 mm); drain gauges DR20/40/60 need an e-RA
  account -> not used. Leaching fit k=0.109/100 mm, LOO skill ~0.
* Woburn: own met starts 1928 (station WMS), trials end 1926 -> matched weather
  will never exist. Frozen `woburn_plan.json` BEFORE reading yields declared
  Rothamsted (~40 km) as a regional proxy (not silent). Amendment
  `woburn_amendment.json` before scoring (lime coded L0, DD/MM/YYYY sow dates;
  the first run selected 0 rows, nothing seen).
* RESULT (`scripts/woburn_yields.py`, output/woburn_yields_20261106): wheat
  unmanured n21, obs 0.98 t/ha: A0 logMAE .150 r -.23 skill -.12; A (x0.933) .154
  skill -.16; B (A + leaching) .152 r -.11 skill -.18. NOT QUALIFIED; no
  production change. Barley A0 r +.14 skill +.12, A/B worse.
* KEY FINDING: unmanured plots RUN DOWN, manured hold. Barley unfertilised
  1880-84 1.87 -> 1895-99 0.84 t/ha (-55 %), FYM 2.64 -> 2.23 (-16 %); wheat
  1.21 -> 0.77 (-36 %) vs FYM 1.80 -> 1.60. Run-down floor at both sites
  0.7-0.9 t/ha (Broadbalk 1901-25 0.69) ~ model level. Missing component is a
  SOIL-FERTILITY (nitrogen) state driven by land-use history, not water.
* Woburn strata now SPENT (dataset_usage.json `era_woburn_wheat_barley_1877_1926`).
  Broadbalk already spent. Reserved climate f untouched.
* Next: literature-grounded soil-N state (run-down under continuous cropping,
  recovery under fallow/manure/legume rotation), developed on spent Broadbalk +
  Woburn, evaluated on a genuinely separate record (e.g. other Rothamsted
  classicals' early years, Hoosfield aggregates already seen -> not usable as
  blind). Any qualifier feeds the shared grain -> residents -> reach chain.
* Report: reports/CROP_WATER_WOBURN_20261106.md.

# Historical wheat yield benchmark — 5 November 2026

* Latest user priority remains Earth calibration of all components, with utility
  budgets feeding shared settlements/control. No new independent map family.
* New direct historical benchmark, not simulated climate: Broadbalk wheat yields
  + Rothamsted observed monthly temperature/rain. Sources CC BY4.0, pinned under
  `calibration/low_input_yields_20261105`; cache `data/cache/era_low_input_20261105`.
* Preregistration `0ffa8aac`; disclosed input-availability amendment `0e016777`
  BEFORE numerical yield scoring. Original complete-temp rule gave only15 train
  years. Accept provider means missing at most1 daily temperature reading per
  month; retain complete-record test subset. Keep20-year minimum and split.
  Source harvest1883/sow1886 impossible date EXCLUDED, not silently repaired.
* Selection+producer frozen `67b7aa1c`: 20 training primary years1879–1900, 25 test
  years1901–1925. Same physical unfertilized plot3 in both: TEMPORAL at ONE SITE,
  not independent geographic validation. FYM/mineral/other strata kept separate.
* Grain source units t/ha/year already, ~85% dry matter (not measured). Unit in
  workbook fields_metadata, absent JSON field schema. Do not divide by area
  again or compare gross grain to calories after seed/milling losses.
* Mean-temperature column blocks, NOT monthly extremes. DTR is monthly means of
  daily Tmax–Tmin. Rain missing-day counts flagged; trace-only0.05mm/day bound is
  conditional, not proved error bound. RAIN5 historical substitution retained.
* Chronological Sep(previous year)–Aug(harvest year), no cyclic window wrap or
  future autumn leakage. Existing wheat response with sequential100mm reference
  soil state, still NOT a crop-specific transpiration/evaporation ledger.
* RESULT: yield scale0.933. Test logMAE .21287 -> .19930 (6.4%); RMSE .40836 ->
  .36911t/ha; r=-.37786; RMSE skill vs training-mean constant remains -15.3%.
  FAILS qualification despite level improvement. Strict-complete23-year subset
  also fails. NO AD200 or production crop/climate/population/control adoption.
* Actual winter dates: only2/25 seasons meet current temperature/length/heat
  rules;22 length failures,15 temperature failures (overlap),1 season outside
  fixed crop-year. Doesn't prove dormancy/waterlogging/nutrients causal.
* `check_earth_yields.py` independently replays metrics/grid/aggregate units and
  optional source rows. Frozen producer snapshot67b7 supports later code edits.
  180 year/management aggregates are45 shared weather years, not180 independent
  experiments. Public packet/CSV/scores/plot in atlas Earth evidence page.
* Broadbalk scored pool now SPENT. Woburn wheat+barley files pinned/downloaded,
  targets UNOPENED/UNSCORED pending observed local weather (Rothamsted cannot be
  silently treated as Woburn station). Hoosfield aggregate means already seen
  during source discovery. Reserved climate f not opened/run.
* Next mechanics: chronological conservative crop-water ledger, separating crop
  transpiration from bare-soil evaporation/drainage (Allen et al1998 FAO56 ch8/9).
  Verify conservation and no repeated soil-water spending before fitting yield.
  Constrain winter phenology/management; earlier failed chilling-clock remains
  rejected. New mechanisms may use Broadbalk explicitly as DEVELOPMENT, then
  evaluate on genuinely reserved data once matched inputs exist.
* Methods: reports/HISTORICAL_WHEAT_20261105.md. Standard `.bat` atlas hub links
  evidence with result, figure, protocol/amendment/source identities/downloads.
  Existing 4 production atlas folders unchanged; release/evidence hashes updated.

# Earth calibration evidence programme and failed split audit — 5 November 2026

* USER PRIORITY: calibrate every part on Earth as evidence permits. Prioritize
  observed processes and independent household/land/work evidence over more
  scenario maps. Keep all utility budgets feeding shared residents/control.
* First evidence ledger: 11 components / 551 selected numeric configuration
  records. `rotclimate/evidence_audit.py` and
  `calibration/earth_components_20261105/evidence_spec.json` distinguish
  published relationships, actual fits, definitions, scenarios and unreviewed
  evidence. Covers selected JSON and literal top-level constants, NOT every
  function-body coefficient; counts are not degrees of freedom or % calibrated.
* Open VDSA source DOI 10.5281/zenodo.8224522 (CC BY 4.0), files pinned with
  publisher checksums + SHA256. Fetcher never executes downloaded Stata code.
  Raw survey data remain cached, respondent names are not exported. Published
  pseudonymous task records permit independent replay without cached raw files.
* Preregistered plan/source in `e8e09152`, training selection/producer snapshot
  in `5ddb6d20`, before evaluation. Modern 2009–2014 manual wheat/barley task
  benchmark uses actual plot hectares, household size and human hours. Never
  treat wages as hours, output value as grain, or bullock hours as human work.
  Complete subplot/season keys; ambiguous repeats/bundled tasks excluded.
* IMPORTANT FAILURE: initial name-based district split had MAHARASHTRA versus
  MAHARASTRA (Akola) aliases. Independent replay found FIVE households in both
  folds, 7 observations each. Original 1,635-case validation claim is withdrawn;
  original computation retained. Entire affected evaluation district removed
  (29 records), leaving 1,606 wheat observations / FOUR districts, no panel
  overlap. Scale 3.432 not refitted. Restricted error .459 -> .176; within-factor
  two 20.9% -> 80.8% (equal-district weights). This is POST-AUDIT DIAGNOSTIC,
  not new untouched or fully prospective validation; no qualification claimed.
* New `harvest/panel_validation.py` guard rejects cross-fold households.
  Current benchmark runner refuses the flawed old split/stale identities; do
  NOT bypass it for a new fit. Original archived runner is in `5ddb6d20`.
  Publisher verifies historical producer identities against that Git snapshot.
  `audit_earth_reaping_panels.py` records failure and restricted diagnostic;
  `check_earth_component_results.py` independently replays both computations.
* ZERO cases pass strict recorded low-input screen; no evaluation barley.
  No AD200 default adopted, no model scientific outputs changed. 40% workforce,
  annual/reaping availability, rural demand, stores, imports and institutions
  remain scenario assumptions. Modern fit is not ancient technology calibration.
* Dataset exposure register marks evaluated pools spent and original VDSA
  evaluation flawed; reserved climate f was NOT opened or run. A new study
  needs canonical place IDs/panel integrity and independent evaluation data.
* Normal hub has Earth calibration evidence page (`atlases/earth_evidence/`):
  searchable ledger, graphs, full source/plan/audit downloads and visible caveats.
  Hub text corrected so legacy Han/Roman tests do not validate new food/control
  coupling. Methods: `reports/EARTH_COMPONENT_CALIBRATION_20261105.md`.
* Next: canonicalize geographic identities BEFORE any new fit; acquire matching
  historical/low-input crop/area/work records. Investigate workload per area
  versus harvest mass without selecting a mechanism on this spent pool. Replace
  rural food claim + workforce together from independent compatible households;
  then storage/imports/freight, settlement sizes and actual institutional reach.
  Census capacity fits identify products of yield/area/cropped share/food need,
  not each factor separately. Do not add independent final utility families.

---

# Listed cereal work → food → settlements → reach — 5 November 2026

* Previous integration milestone `cbed21e5` is pushed to BOTH publication refs.
* Added three explicit work sensitivities to the SAME settlement/reach modes:
  `work600_30`, `work600_10`, `work300_30`. Keep food-only default `joint365`;
  no empirical worker calibration selects a new default. All earlier six cases,
  summaries, collection assignments and masks are preserved EXACTLY.
* `harvest/field_support.py` limits complete annual cereal activities by listed
  total and reaping work of the SAME reference workers. Reaping is a subset,
  not double-counted hours. Rural meals remain fixed when grain production
  falls; a deficit cell exports nothing. The resulting single grain ledger
  changes residents, institutional availability and same-source paired reach.
* Reference workers = 40% of the earlier fixed rural cereal-food claim divided
  by 2,500 kcal/day. This is an internally testable food/work allocation, NOT
  observed/census residents. It inherits the baseline claim's dependence on
  potential production. Future population calibration must change the rural
  food claim AND worker anchor together. Never add these scenario people to
  census/occupation/FORGE/pastoral totals.
* Earth corrected: 600 h / 30 d retains 99.79% of grain and 1,062 sources;
  600 h / 10 d retains 1,059; 300 h / 30 d retains 994 versus food-only 1,064.
  Food-only → tighter annual-work access: 7.36 → 6.83 area-weighted bins.
  Other climates lose 31/80/53 sources in the tighter annual-work case.
* `scripts/extend_settlement_labour.py` reuses the frozen first-stage cases;
  sources/inputs hashed, checkpoints reusable. Publisher now takes `--origin`
  and publishes this extension from `output/settlement_labour_20261105`.
  IMPORTANT: invoking publisher with no origin republishes the earlier six-case
  version; use the extension origin for the current release.
* New source/cell work audits, figures and methods in
  `reports/SETTLEMENT_LABOUR_20261105.md`. Normative Columella field counts and
  FAO simultaneous-resource budgeting motivate the mechanism, not worker shares,
  actual deadlines, complete household work or historical productivity.
* Existing viewer selectors expose all three work cases, their budgets/fixed
  rural deficit, CSV fields and downloadable cell audits. Work is partial:
  draft services, other foods, household tasks, processing, water volumes,
  labour exchange/mobile communities and political rights remain unresolved.
  Future utility budgets must constrain this SAME allocation and broad actor
  scope, not create independent final map families or ecology→institutions.

---

# Joint food → settlement → available reach sources — 4 November 2026

* Implemented the user's requested loop into the EXISTING `reach_towns` and
  `reach_defacto` modes, all four climate packets. Default is `joint365`, with
  a transport-matched unconstrained reference, 90/no origin stores, 1% collection,
  smaller 25-person cohort and explicitly labelled legacy comparisons.
* New core `polity/settlement_support.py` solves a seasonal resident ceiling,
  then allocates requested civilians and institutional residents from ONE
  conserved pool. A community can persist without a cohort. Only available
  affiliated cohorts emit same-site two-way reach; no population-power weights.
* All 151 marked icons join bijectively using grid coordinates and kind, with
  coastal snapping kept separate. Raw art pixels differ from atlas pixels.
  Co-located markets merge. Unknown marked affiliation never inherits claims;
  generated-site claim affiliation remains an explicit hypothesis.
* Earth corrected: 1,085 candidates; year-store case has 1,082 communities and
  1,064 staffed sources versus 1,074 reference sources. Civilian requests fall
  from 3.44 M to a 0.79 M alternative allocation; this is NOT a census revision
  or validated town-size prediction. 1% collection leaves 107 sources and
  1.44 area-weighted access bins versus 7.40 reference / 7.36 year-store.
* Candidate generation and path friction remain fixed across cases. Food
  collection has local road/foot eligibility, no sea imports or measured freight
  throughput. Staffed-source reach includes proposed person-transport links.
  Compare food effects ONLY with the matched reference, not the legacy engine.
* `scripts/review_settlement_integration.py` computes/reuses source/input-hashed
  reviews. `publish_settlement_integration.py` publishes optional runtime mode
  replacements without altering `atlas.json` or climate/crop/FORGE packets.
  `atlas/settled-reach.js` lazy-loads ledgers/masks; manifest or Harvest failure
  restores original modes. Missing detailed ledgers retain precomputed plates
  with a visible explanation. Controls remain conditional.
* Methods/scope: `reports/SETTLEMENT_INTEGRATION_20261104.md`; literature access
  in `research_notes/settlement_integration_20261104.json` (Palmyra 2022 paper,
  Erdkamp publisher introduction, FAO storage). Coefficients remain scenarios.
* First integration only: other foods, household work, drinkable water volume,
  livestock nutrition, grain exchange, camps and rights are NOT jointly solved.
  Next work should constrain the same resident/source allocation with these
  budgets, not add independent utility map families or infer institutions from
  ecology. Retain broad polity/nonstate scope and explicit missing evidence.

---

# Required integration into settlements and control — user clarification

* The user explicitly requires ALL utility/resource maps to feed back into
  settlement and control predictions. Standalone diagnostics are intermediate
  evidence, not the development endpoint. Prioritize integration before adding
  further independent map families.
* Food, feed, storage, water, labour and transport must constrain a shared,
  conserved allocation: where communities can persist, their supportable size,
  seasonal relocation/supply dependence, and provisioned institutional presence.
  Apply this across imperial, other-state and nonstate/mobile scenarios.
* Next implementation milestone: supply-constrained settlement scenarios that
  consume the existing seasonal budgets, followed by supply-supported control
  scenarios anchored to those settlements/institutions. Show the causal path
  from resource constraint to changed settlement/presence/reach, alongside the
  baseline and uncertainty. Do not substitute a food/population power multiplier
  or assume that ecological feasibility proves staffing, allegiance or ownership.
* The first local-cereal integration is now implemented (see milestone above).
  Feed, household labour, water volumes, exchange and mobile-community
  allocations still need to constrain this same system; those utility layers
  must not be described as fully integrated. Missing evidence stays unscored.

---

# Readable circuit insets — 4 November 2026

* Continued after pushing `5d953c4c`, per the user's preference to keep working.
  A view-only follow-up makes compact circuits readable within regional tests.
* Inset defaults to route detail (at least eight fine-cell widths of context),
  with a Show whole tested landscape / Focus on route toggle. `pm_frame` is
  preserved in shared URLs and across climate/atlas navigation. No new map
  button or always-visible global selector was added; unscored cases hide it.
* Browser checks all four packets, both framing states, URL reload, identical
  food readouts/CSV before and after toggling, narrow/dark layouts, water cases,
  and optional-packet failure isolation. Science/data are unchanged from
  `5d953c4c`; its 122 tests and independent model review remain applicable.
* Screenshots/receipts: `output/inset_readability_20261104`. Normal `.bat` atlas
  copies and portable bundle are refreshed. Methods describe framing separately
  from the tested landscape extent. No simulation, recalibration or agents.

---

# Origin storage and regional resource circuits — 4 November 2026

* Continued `b919802e`. User said Continue. Same two normal atlas buttons,
  now 11 provisioning scenarios and 3 landscape tests (local; regional with
  sparse outer bases; regional with additional outer bases), all 4 climates.
  No climate, yield, ownership or population recalibration was adopted.
* `harvest/mobility_landscape.py` and `scripts/regional_resource_circuits.py`:
  regional radius 20 fine cells (~73.6 km), retaining the earlier radius-5
  (~18.4 km) bases. Add a stride-4 outer lattice, then offset (2,2). Keep the
  original herd, individual grazing footprint, 7-day pack, slope speed and
  2 travel-days/bin. Transit land supplies paths, never extra food at a base.
* Regional ground is the home-connected fine land component, with no water
  corner cuts. Each move includes its actual fine-node path. Location indices
  refer to candidate patches; segment indices refer to separate ground nodes.
  Grassland/Neck: 157/233 bases on 1,257 cells. Tarani: 70/107 on 608. Mixed
  resource anchor is an island with 13 connected cells; no overland expansion.
* Controls: fixed home; best fixed base over EVERY connected fine cell,
  including unsampled bases, with continuous reserves; optimistic per-bin
  single-patch maximum ignoring travel, with continuous reserves. The last
  is a RESOURCE UPPER BOUND, not a route. Both controls are unchanged between
  sparse/additional outer samples. Local → sparse → additional choices cannot
  reduce optimum feeding; independent review checks both nested comparisons.
* Same grassland example, regional additional bases, mobile versus best fixed:
  Free 88.60% vs82.74%; Earth raw86.73% vs88.42%; Earth corrected89.36% vs90.71%;
  Whittaker81.87% vs71.33%. This is climate-fit sensitivity, not proof of actual
  camps/nomads or ecological determinism. Anchors and return phase remain
  assumptions. Half-day reserve refinement changes support by at most0.137pp.
* Four new food cases vary ONLY origin stores (365→90/0 flow-days), collection
  (10→1% of rural overflow), or rural stores(365→180 demand-days). Destination
  stores/ration/paths/freight stay fixed. RuralFood.exportable centralizes the
  no-export-if-annual-rural-deficit rule; an early-glut/future-deficit test guards
  it. Original7 food cases/balances, local circuits and collection grids exactly
  match baseline values. No new food/power multiplier or population sum.
* Earth corrected fully supplied sites: baseline151;90-day origin store131;
  no origin stores0;1%collection92;rural180store0. The last is a CEREAL-ONLY
  rural ledger with protected meals, not actual famine. Origin tests retain
  the SAME prescribed dispatch policy; they aren't maximum trade capacity.
  Flow-days of annual exportable supply are not days of destination demand.
* Research: Brottem et al.2014 publisher ABSTRACT only on forage connectivity;
  Turner/Schlecht2019 mobility scale distinction; FAO bulk-storage sizing.
  No coefficients copied from inaccessible text or claimed as ancient facts.
  Protocol/limitations in research_notes/presence_mobility_scale_20261104.json.
* UI keeps 2 buttons, adds landscape-test selector and URL/CSV pm_scale state;
  origin assumptions visible in readouts/CSV. Main circuit image now follows
  BOTH water case and landscape test, with matching inset/ledger. Water-excluded
  home remains unscored. Core/frontier and irrelevant controls stay hidden.
* Methods: reports/PRESENCE_MOBILITY_SCALE_20261104.md. Builder records new
  receipts in output/presence_mobility_scale_20261104, preserving prior study
  outputs. Config data/presence_mobility_model.json v2; payload adds mobility_scales
  and complete fine-ground production/adjacency for independent controls.
* Validation:122 analytical/component tests; public review79,728 site-bin food
  ledgers,120 closed circuits,8 reserve refinements; exact baseline preservation;
  nested-choice and upper-bound invariants. Browser4 packets,11 food scenarios,
  2 mobility views×3 tests×2 water cases,3,024 CSV rows, URL/state/narrow/dark/
  downloads and4 failure fixtures. Existing3-atlas smoke passes. Windows and
  portable publication receipts accompany this milestone.
* Figures regional_circuits.png and origin_storage.png were posted. Next:
  standing forage/hay quality and its work/carry budget, home/return-phase
  sensitivity, watering and shared competing users. Preserve perfect-foresight,
  no-nutrition/no-demography/no-actual-camp caveats. Never infer polity types,
  absence of communities or sovereignty from resource feasibility. No agents.

---

# Sustained presence and seasonal resource circuits — 4 November 2026

* Continued `6949ea71`. User approved proposals 1 (food support) and 3 (mobile
  resource circuits). New normal atlas buttons: Political reach → Sustained
  presence (7 scenarios); Livelihoods → Seasonal circuits (2 views, 4 fixed
  landscapes, 2 water cases). All four matching climate packets are published.
  No climate, food-capacity, population or ownership baseline was changed.
* Methods/results: `reports/PRESENCE_MOBILITY_20261104.md`. Assumptions:
  `data/presence_mobility_model.json`. Primary mobility framing is Turner &
  Schlecht 2019; Roth 1999 was consulted only through metadata, not full text.
  Research access and coefficient limitations are recorded explicitly.
* `polity/sustained_presence.py`: all 151 verified marked sites, including 10
  with unresolved affiliation. A single published wheat/barley crop supplies
  protected rural meals, finite rural stores and separate on-farm export stores.
  No export from a cell with unmet annual rural demand. Seed isn't deducted
  twice; the legacy `NEED_KCAL` storage/draft allowance is never used.
* One cell supplies at most one site through a fixed base-bin parent-tree path;
  both directions along that same path must qualify each dispatch bin. Existing
  roads/terrain/weather/ford costs, constant off-path pace; no density feedback,
  generated tracks, ferries or river/sea freight. These are collection areas,
  not control polygons. Permission across painted claims is assumed open.
* Collection is 10% of rural overflow; origin stores hold a year of exportable
  flow, freight 5 tonnes edible cereal-equivalent/bin, delivery delay one bin,
  retention 95%, stored-energy loss 5%/year. Every quantity is a scenario, not
  measured ancient logistics. Group sizes 100/500, destination stores 0/90 days,
  two busy adjacent dispatch bins interrupted, alternative tied crop calendar,
  and a fivefold freight sensitivity. All stocks and in-transit food repeat.
* Earth corrected: 100-person baseline fully supplied at 151/151 sites; a
  two-bin interruption without destination stores at 0/151, with 90-day stores
  at 151/151. For 500 people, unchanged freight caps annual support around 41%
  by construction; fivefold freight fully supplies 135/151 sites. Food support
  does not establish actual staff, labour, shelter, pay, institutions or control.
* `harvest/seasonal_mobility.py`: exact dynamic programming on the declared
  finite location/reserve graph. One unsplit herd, 100 DM reference units,
  6.25 kg/unit/day, 7-day carried reserve in one-day increments. Transit meals
  use prior carried feed; destination food cannot feed the past. Only visited
  current-bin growth is collected, once. Same home AND feed at year end.
* Four previously fixed pasture examples, radius five cells (~18.4 km): Tarani,
  two landscapes outside named claims, and Neck. Not observed camps or societies.
  Reference movement 10 km/day modified by slope, maximum two travel-days/bin.
  Water sensitivity applies to occupied bases within 10 km of mapped water;
  an excluded home is unscored, not proof of no water or impossible occupation.
  Enroute watering, potable volume, wells, carry effort, nutrition and herd
  demography remain unknown. The assumed seven-day pack is 4,375 kg DM.
* Critical control: Earth-corrected fixed home → circuit → best fixed base:
  Tarani 36.6 → 75.1 → 76.0%; grassland 85.6 → 88.4 → 88.5%; mixed resources
  98.2 → 98.3 → 98.4%; Neck 84.8 → 96.2 → 96.2%. NONE beats the best fixed
  base (continuous reserve). Don't portray gains against arbitrary homes as
  evidence that mobility wins. Half-day reserve refinement changes support by
  at most 0.137 percentage points. Perfect foresight of a climatological year;
  finite-graph optimality is not global physics or historical validation.
* `scripts/build_presence_mobility.py` pins sources/inputs/public assets and
  reuses matching complete packets. Public gzip JSON includes stocks, patch
  production, adjacency and actual intermediate paths. Catchments are row-major
  little-endian uint16, 0 unassigned, otherwise site index+1. No joint allocation
  of the four independent herd experiments or addition to population totals.
* `atlas/presence-mobility.js`: matching Harvest/gzip identities, conditional
  controls, URL state, selected-site 84-row CSV and herd 24-row CSV, route inset
  with patch letters and seasonal table. Site selection updates the climate at
  the snapped source cell. Missing/bad packets remove only these two layers;
  a pasture failure retains Livelihoods when circuits are available.
* Validation: 116 analytical/component tests; independent public checks of
  50,736 site-bin ledgers, 40 closed circuits and actual paths; four reserve
  refinements. Combined food-ledger relative residual <4.1e-11. Browser covers
  four packets ×9 views, 1,008 food/480 herd CSV rows, state, water exclusions,
  narrow/light/dark layouts, conditional controls and failure fixtures. Existing
  three-atlas smoke passed. Windows/portable receipts accompany publication.
* Outputs: `output/presence_mobility_20261104`. Figures `food_support.png` and
  `resource_circuits.png` were posted. Next: poorer origin stores/collection,
  producer and clearing labour, independently declared wider seasonal gradients,
  standing-feed quality, watering, real camps and competing users. Preserve the
  negative controls: no biome-to-nomad or food-to-power rule. No agents spawned.

---

# Worldwide source/seasonal coverage audit — 4 November 2026

* Continued1faf860c. User asked how to improve de facto maps, approved a
  worldwide evidence/seasonality audit retaining original ownership baseline.
  Normal Political reach →Coverage audit is ONE extra button/six dynamic views,
  all18 actors, 3source scenarios, 1/2/4day per-leg budgets; all4 climate packets.
* Sources141 linked of151 verified marked sites;10 affiliation-unknown/conflict;
  Kudā additionally position/symbol-unverified, not routed. Explicit aliases
  data/polity_affiliation_aliases.json; workbook owner/commandery and icon
  signals retained. Lakui conflicting signals stays unknown; OCR-unmatched
  nonimperial sites not guessed by fuzzy joins. SourceCSV/JSON also shows claim.
  All data provisional game-world evidence, not independent observations.
* Source scenarios: evidence-linked; add unknown marked-site affiliations
  from painted claims; add existing generated administrative/market sites.
  Known affiliation isn't overwritten by a different claim. Roads NEVER
  emit authority here, legions not fixed sources, no strength/rank/refuge
  multiplier. Generated sites aren't observed villages/camps/institutions.
* Avādāyā/Neck have0 linked inventories: selected evidence coverage unscored,
  not zero actual control/empty land. Corrected expanded case supplies28/62
  source nodes; Neck claim-only has4. Unknown marked-site access is a separate
  evidence signal, NOT a new polity or an inferred local-autonomy footprint.
* Coherent same-site condition: A→cell AND cell→A within B. Merge AFTER each
  individual-site test; nearest out-A +nearest back-B does not qualify. Sites
  fixed/assumed available; qualifying site/actor may vary across months. No
  capacity/staffing/food/permissions/mobile-camp/sovereignty inference. Common
  central-density transport incl proposed tracks/landings in all source cases.
  Additive beat-or-wait/minparallel engine from hierarchy audit; differs from
  legacy fair-spell/refuge metric, so not an engine-controlled old/new contrast.
* Six views: paired seasonal bins, cyclic longest gap, simultaneous actor
  overlap, source-addition sensitivity, outward-without-same-site-return bins,
  unaffiliated marked-site access. Missing actor baseline makes gain unscored.
  Aggregate12bins can involve different actors: not persistent single control.
* Corrected2days/leg: all12bins ANYactor8.64%land linked →9.18%claim-added →
  47.19%generated. Outward/no-return anybin2.94%linked. Overlap anybin0.11%
  linked/7.16%generated. Land-fraction weights on majority-land travel grid.
  These are source sensitivity, NOT accuracy or observed political shares.
* polity/coverage_audit.py +scripts/review_world_coverage.py stream bounded
  forward/reverse Dijkstra per unique source, checkpoint every3months; complete
  packets reused only with source/input/binary identities. Old science modules,
  climate/food/population and de facto ownership exports remain unchanged.
* Gzip packets~1MB each, lazy browser load; uint32lookup +[3cases,18actors,
  2directions,Nland]words +[2directions,Nland]unknown words. Eachword12×2bit
  classes0>4days/1≤4/2≤2/3≤1. Do NOT bitwiseOR classes (1|2 givesfalse3);
  merge monthclass MAX or thresholded seasonal masks. Read helper
  scripts/read_coverage_grid.py usesNumPy; normal server remains stdlib.
* UI actor/source/budget+view URL state, LRU mask cache, conditional controls;
  original de facto/polity views now link to source audit. No new topic sprawl.
  Bad identity/gzip/unsupported DecompressionStream removes only audit layer.
  Source inventories/table show unscored missing actors;54row pointCSV allcases.
* 103 linked analytical tests pass. Browser4×6views,648actor/scenario/budget
  CSV checks,4096packing cases, missing baseline, lazy/reused fetch, URLs,
  controls/mobile/downloads, original-baseline links and3 failure cases pass.
  Oldall3 smoke passes. Independent grid-reader example checked. Windows/ZIP
  verified in publication receipt; launcher6views/18actors, release pinsmanifest.
  Gzip assets byte-exact in Windows checkout. Scientific figure and viewer posted.
* Methods reports/WORLD_COVERAGE_20261104.md; outputs output/world_coverage_20261104.
  Next: independently curate missing nonimperial affiliations/OCR aliases,
  documented seasonal camps/mobile support, provisioned/staffed presence and
  institutional ties. Do not infer these from biome or multiply power by food/
  taxable people; previous negative controls still apply. No climate recalibration.

---

# Worldwide pasture/feed resource maps — 4 November 2026

* Continued from e205c539 scope correction. New Livelihoods topic in all normal
  atlases (Earth raw/corrected matched): 3 buttons/6 views for annual usable DM,
  annual feed equivalents, lean-bin new growth, minimum zero-loss feed reserve,
  90-demand-day buffer shortfalls and mapped water distance. ALL245031 land
  cells included; polity claims only label illustrative geographic examples.
  This is a feed-resource diagnostic, NOT a complete pastoral population model.
* Primary sources researched: FAO2012 feed assessments; FAO Kenya Annex5§7.4
  reference250kg TLU/6.25kgDMday; Mottet/Assouma2024 FBS DOI10.3389/fanim.2024.
  1354728 (DM alone doesn't establish energy/protein adequacy); Illius/O'Connor
  2000 heterogeneity abstract (publisher403, no equations/coefficients copied).
  research_notes/pasture_20261104.json; config data/pasture_model.json.
* harvest/pasture.py excludes assigned crop area from forage (arable×.6),
  reuses published Miami NPP and existing Harvest forage shares .5aboveground,
  .25usable, biome-dependent edible fraction. Annual coefficients remain
  assumptions, not newly validated sustainable grazing. No crop-residue credit.
* Uncalibrated seasonal weights clip(T/15,0,1)×P/(P+50), normalized to annualDM.
  Positive annual supply with no active weight stays unknown, not uniform.
  Current4packets happen to resolve all cells. Synthetic unknown case tested.
* Constant test demand=.5annual usableDM. Cyclic minimum zero-loss capacity;
  90-demand-day buffer uses minimal repeating inventory, explicit overflow
  and consumption once, via existing food_stocks.py. Maxledgerresid<5e-11kg/km².
  Standing forage/hay undifferentiated; no preservationlabour/quality, protein,
  energy, herd dynamics, migration, water volume, animal products or new people.
  365day reference accounting year/12equalbins, not the world's civil calendar.
* Median minimum reserve days Free33.5/Earthraw37.2/Earthcorrected35.6/Whittaker47.
  Land share >90days12.8/14.6/15.3/19.3%. Corrected Earth~25%annualDM outside
  named claims. These are conditional resource figures, not herd counts/famine.
  Waterdistance is mean land proximity to mapped rivers/lakes: no permanence,
  salinity, wells, measured drinking capacity or species-specific gate assumed.
* Four fixed-anchor examples from published Earthraw eligibility: Tarani
  agricultural resources, nonimperial grassland outside named claims, mixed
  resources outside named claims, Tribes of the Neck. Map labels do not assign
  livelihoods or institutions. No selection on new reserve outcomes/validation.
* scripts/build_pasture_maps.py pins inputs/sources, renders maps+publicNPZ and
  compact binary; sources frozen climate/Harvest unchanged. atlas/pasture.js
  checks loaded Harvest and binary identities, exposes CSV and NPZ downloads.
  AnnualDM float32 to preserve tiny positives; ratios1/60000,reserve.01days,
  water.1km and integer shortfall bins, explicit nodata. Coastal resource
  readout retains original click before station-card snapping; other cards
  retain their old selection behaviour. Conditional occupation controls hidden.
* 97 analytical/component tests pass. Pasture browser4×6 views/16pilotCSV-NPZ
  checks, outside-claim/tribal/nonimperial coverage, state/download/mobile,
  corruptedidentity/binary isolation pass. Existing hierarchy browser4×6 and
  all3 atlas smoke pass. Windows checkout/portable hashes in publication receipt.
  Launcher prints Livelihoods6views; release pins manifests. Normal .bat viewer
  updated. Figures world_resources.png and seasonal_profiles.png posted.
* Methods reports/PASTURE_RESOURCES_20261104.md; output/pasture_maps_20261104.
  Next: energy/protein/standing-forage quality and water dynamics; then conserved
  herd/mobility and shared household food/land/labour scenarios. Do not add these
  feed equivalents to old farming/pastoral/FORGE population totals. No cropfood/
  human-consumption integration or physics recalibration adopted this milestone.
  Integration caution: legacy scripts/land_people.py NEED_KCAL=1.1e6 already
  includes a storage/draft-animal allowance. Replace that proxy explicitly
  before charging those same requirements again in a joint household/feed LP.

---

# Scope correction: all societies, not only the Empire — 4 November 2026

* User explicitly wants other polities (sparse spreadsheets) and communities
  outside polities, including mobile pastoral/other tribal societies. Do not
  focus subsequent provisioning/population work solely on imperial administration.
* Separate livelihood, mobility, settlement form and political organization;
  no automatic nomad=nonstate or tribe=pastoral equivalence. Sparse evidence
  stays unknown/scenario-based, not an invented imperial hierarchy.
* General food/feed/water/storage/exchange model must work outside claims.
  Existing claimed-only proposed administrative-town generator is not a global
  inhabitability or village/camp model. Do not simply remove its claim mask
  and extrapolate administrative-seat counts. Unclaimed does not mean empty.
* Farming/pastoral/FORGE capacities currently compare scenarios; do not sum
  them into extra populations without shared land/resource accounting. Annual
  grazing proxy is not a seasonal herd/mobility model. Institution collection
  and garrison support become optional overlays on wider local livelihoods.
* Next pilot should include nonimperial agricultural, mobile pastoral/mixed,
  and settled nonstate cases. See reports/WORLDWIDE_PROVISIONING_SCOPE_20261104.md.
  This is a recorded scope update, not newly implemented model/maps.

---

# Recorded administrative hierarchy maps — 4 November 2026

* Continued from 71b52b47. New Administration → Administrative links: one
  button/six views on all normal fits, including matching Earth raw/corrected.
  Recorded 72 seats →19 provincial capitals →Aēnaha. 70 verified seats,
  51 nontrivial local links; Kudā and Thalamâtâs/Pitané remain unresolved.
  No nearest-parent inference or game balance coefficients adopted.
* Two controlled person-transport cases: marked-settlement coastal/river
  interchange eligibility with no generated tracks; add proposed tracks and
  proposed-town interchanges, explicitly retaining marked interchanges.
  Both retain current central-density path friction. Interchanges inferred,
  not proven harbours. Recorded authority sources/hierarchy held fixed.
* Isolated polity/administrative_hierarchy.py selects MINIMUM directed
  duration among parallel alternatives (legacy CSR sums them). Additive
  beat-or-wait sea edges, NO legacy whole-voyage fair-spell blend. This is
  a separate travel calculation; do not compare its absolute times as if
  it differed from old access only by infrastructure. No legacy source
  modules or frozen climate/food/political exports changed.
* Four legs retained per seat/bin/case: capital→province, province→seat,
  seat→province, province→capital. Provincial reply=sum middle2; imperial
  reply=sum4 under SAME frozen monthly conditions. No courier relays,
  institutional delay, changing weather during voyage, capacity/provisioning
  or political-border permissions. Twelve model snapshots, not civil months.
* Median worst-snapshot imperial reply over69 noncapital seats, marked→
  proposed days: Free60.5→59.6;Earth raw62.7→61.0;Earth corrected62.7→61.6;
  Whittaker61.8→60.0. All69 finite allbins both cases, not validated service.
  Physical-transport benefit is modest versus old access's large gain from
  adding proposed authority sources. Do not conflate those two mechanisms.
* Six views: longest provincial reply ×2cases; longest imperial reply ×2;
  marked seasonal range; worst imperial reply days saved by proposed transport.
  Schematic connectors NOT paths or control polygons. Coloured dots only
  describe seats; outer rings provincial capitals. Map views have fixed-day
  scales. Select recorded seat +7/14/30/60day comparative reply budget for
  within-budget bins and longest cyclic over-budget gap. No budget validated
  as a political cutoff. Capital self-links explicitly zero, unknown seats
  unscored, full directional seasonal CSV/NPZ and selected24rowCSV downloads.
* Optional atlas/administrative-hierarchy.js verifies inventory, food binary
  and travel JSON identities. Failure removes only new layer. Fixed old
  Administration failure handling to retain topic if hierarchy remains valid.
  Commandery/budget/view/climate URL state, normal climate-selection sync,
  irrelevant core/frontier/malaria/month/tiers controls hidden on new maps.
* Runner scripts/review_administrative_hierarchy.py hashes all inputs/source,
  resumes only identical complete packets; 4-thread directional shortest paths.
  Small links.npz perpacket retained in output/administrative_hierarchy_20261104.
  Publisher, comparison-plot and browser scripts named administrative_hierarchy.
  Methods reports/ADMINISTRATIVE_HIERARCHY_20261104.md cites Smith/Glatz/Evans-
  Rivers/ORBIS as motivation, not validation of lore hierarchy or thresholds.
* 91 linked analytical tests pass. New browser checks4packets×6views, directed
  CSV versus NPZ, budget counts, capital self-links, unresolved searches,
  state/downloads/mobile/control hiding and bad identity/data failure isolation.
  Previous access browser4×12 and oldall3 atlas smoke pass. Windows checkout,
  portable bundle and byte identities verified in publication receipt. Launcher
  prints19 capitals/6 new views; release pins hierarchy manifests. Comparison
  figure posted. Physics unchanged; no new climate-calibration claim.
* Next: conserved provisioning/staffing before control inference; settlements
  share population and food budgets. For communication itself, evidence-backed
  courier relay/institutional delays and time-varying long voyages are missing.

---

# Workbook-backed administration and seasonal access — 4 November 2026

* User supplied Imperial Commanderies.xlsx and Ravages Master sheet (1).xlsx,
  explicitly game-era evidence rather than authoritative physical parameters.
  Originals remain local under /workspace/attachments; do not commit them.
  scripts/import_imperial_datasheets.py extracts only geography/admin columns
  to data/imperial_datasheet_evidence.json, with workbook hashes and sheet rows.
  Excludes game supply/population caps, loyalty, wealth, factions, notes/players.
* Owner list/key data/imperial_administration.json: all 72 names agree with
  reference workbook. Stable IDs resolve split districts and differently named
  temple seats. Preserve Tašar/Garaz town-sheet name conflict (IC4C5), Uγra/Uyra
  spelling evidence. 70 verified marker seats. Kudā has no matching symbol,
  Thalamâtâs conflicts with Pitané seat flag: both excluded as seat sources,
  candidate evidence retained. Named inventory 152 vs 151 drawn symbols; Kudā
  is an unmarked Elder Village, not a merged capital icon. 14 legion positions;
  founding numbers untranscribed, never strength. 25 imperial fort markers.
* New optional Administration topic in normal Free/Earth/Whittaker pages,
  Earth raw+corrected matched: 4 packets, 3 buttons/12 views each. Six cases:
  verified seats; add marked places; add proposed towns; add generated tracks;
  add road cells as sources; separate forts+legion scenario. Same ports/river
  landings incl proposed-town ports throughout, so NOT observed-only transport.
  Threshold 2 person-days, 12 equal climatological frozen-condition bins. Count,
  cyclic longest isolation, annual log-mean versus continuous access, paired
  gains, plus placement seeds 1/2/3 recurrence within10km (not probability).
* Earth corrected all-12-bin claim-area shares: seats14.8%, marked15.7%,
  towns63.0%, tracks65.9%, roads70.7%, military7.0%. Main gain is adding proposed
  sources, not tracks. Sparse seat inventory doesn't prove weak actual control.
  Old de facto, climate/food/population binaries and legacy polity code unchanged.
* Sources/scripts: polity/administration.py, administrative_world.py,
  seasonal_access.py; scripts/audit_administrative_inventory.py,
  review_imperial_access.py, publish_imperial_access.py, plot_imperial_access.py.
  Full review/source hashes in output/administrative_inventory_20261104 and
  output/imperial_access_20261104. Shared atlas/administration.js verifies food
  binary/inventory/grid identities; mismatch removes topic, keeps climate usable.
  Centre CSV, typed inventory, NPZ and selected-place CSV available in viewer.
* 87 linked component tests pass. New browser verifies 4 packets x12 views,
  CSV/NPZ consistency, all4096 masks, controls/state/downloads/mobile and bad
  identity; prior cereal browser and all3 old smoke checks pass. Windows-style
  checkout and portable bundle verified for publication (see receipt).
  Launcher prints Administration/70-of72; release pins sidecar hashes. Methods:
  reports/IMPERIAL_ACCESS_20261104.md; comparison PNG posted during work.
* Next: use workbook province/commandery hierarchy for explicit capital-to-seat
  continuity; threshold/source uncertainty; conserved food/staffing provisioning
  before control claims. Recorded hex memberships are game evidence, not adopted
  physical terrain or independently validated boundaries. No physics recalibration
  this milestone. Keep literature proposals/negative controls in view.

---

# Food and work maps in normal atlases — 3 November 2026

* User asked to work toward new maps. Delivered Food and work topic in normal
  Free/Earth/Whittaker viewers, including Earth raw +corrected:4matchedpackets.
  Cereal field work button has5views(hours, croppedland, reapingstaff10/20/30days);
  Calendar alternatives button showsdistincttiedoptimalharvestboundarybins.
* harvest/work_maps.py uses exactdecodedpublished kcal_wheat/barley, target1M
  netkcal, Columella336/208listedhours/ha and48/32reapingh/ha under explicit8hday,
  approx.25ha/iugerum. Least-work singlecereal, not totalwork/population or a
  full seasonal household plan. All4packets choosebarley withcurrentinputs;
  don't pretend cropchoicemap hasdiversity. Landmap is forwork-efficientcrop,
  NOT independentlyminland; reapingstaff usesprescribedwindow, notrealdeadline.
* Regenerated allcerealwindows onall245031landcells perpacket. Maxdifference
  fromexportedcropenergy~20.9kcal/ha (packingprecision +float32rounding). Retains
  allbestboundaryties(currentmonthlymodel), notnewdailyclock/observedcalendar.
  Ambiguouscells free187932/Earthraw187398/Earthcorrected194256/Whittaker164414.
  Manyties aremodelambiguity, notestimatedagriculturalflexibility/probabilities.
* Builtsidecars data/farm_work.json, sixwebps perpacket, uint16calendarbin and
  NPZvalues. Existingfrozen atlas.json/climate/harvest inputs unchanged andchecked.
  Sourcehashprovenance frozen inmanifest. atlas/farm-work.js verifiesmatching
  Harvestfingerprint/metadata/calendar/loadedbinaryhashes beforeexposingreadouts.
  Mismatchremovesnewtopic/layers, keepsnormalclimateworking, visiblesourcemessage.
  SharedHarvestUI exposesread-onlyfieldgetter/buffer forverifiedreuse,nodoublefetch.
* UI:2buttons, oneviewselectoronlywhereused; nooccupation/malariacontrols inwork
  maps. PlaceCSV/nullmissing values, fullNPZ+methoddownloads, shareablehashstate,
  corrected/rawmatching, dark/light/mobile.73focusedcomponenttests pass; existing
  atlasbrowser smoke passesall3. Newbrowserchecks4packets×6views and numerical
  CSVagainstNPZ, controlhiding/restoration, badidentity fail-closed.
* Source/report CEREAL_WORK_MAPS_20261103; outputs output/cereal_work_maps_20261103.
  Figure work_maps.png posted. refresh_atlas_pages copiesnewoptionalJS andonly
  enablesifmanifestexists; legacyearth_physics disabled. Launcherprintsnewtopic
  andcounts67/72/69layers. Hubreleasealsoverifiesnewmanifesthashes.
* Next: fulltask evidence, climate/workabilitydeadlines, crop-specificcultivars,
  finitewater andjointseasonalfood/stores/work. Existingyield/rainwaterirrigation
  proxy andcold/drymargins remainlimitations. Newmaps havenoindependenthistorical
  validation, state/inequality inference, weatherprobabilities orclimateadoption.

---

# Minimum listed field work for required output — 3 November 2026

* Continued after labour milestone d70c3e00 (pushedbothbranches). Added
  minimum_farm_work to the same shared LP; target>=need, minimizechosenwork
  resource, keepallotherresource/season/landlimits. InfeasibleFarmPlan is an
  explicit error, never hidden foodshortfall or zero requiredwork. Maximum-
  output and minimum-work marginals separated.30focused analyticaltests pass.
* demo_required_farm_work.py uses EXPLICIT hypothetical netfood/ha100wheat,
  80barley, annualneed300arbitraryunits. Historical Columella listedfieldtasks
  only. Fourha:barley3.75ha/780h;3.5ha:wheat1+barley2.5/856h;3ha:wheat3/1008h.
  These are analytical controls, NOT historicalyield or subsistence estimates.
  Insufficientland2.9ha ceiling290;10dayreap ceiling200 => bothinfeasible,
  workloadnull NOTzero. No calorie/population conversion, seasonalconsumption
  and foodstocks notyetjointlyoptimized, omittedhousehold/animalcare unchanged.
* Allpriorseven field-area controls remain unchanged aftersharedsolverextension.
  Sourcehashreceipts refreshed by rerunning, not manually patched. Published
  workshop verifies bothstudies, fullschedules and missingvaluehandling.
* Next: missingtask evidence and jointseasonalfood/stores/work formulation,
  actualcrop/cultivar/workability validation. These LPs solve their supplied
  linear scenarios, not the nonconvexclimatecalibration or globaloptimum question.

---

# Seasonal field-operation scheduling — 3 November 2026

* Continued after world-route8560dc0e and paired-audit5f6e55ff (both pushed).
  New harvest/labour.py plans complete annual activity hectares and every
  required operation within supplied windows. Shared seasonal human/team
  resources, land budget, divisible LP activities, no implicit winter-to-harvest
  labour transfer. Separate simultaneous resources supported; no task precedence
  beyond supplied windows, weather workability, endogenous hiring or integers.
* Historical task counts independently transcribed Columella2.12.1–2: wheat
  4+1+2+1+1+1.5=10.5days/iugerum;barley3+1+1.5+1=6.5. These stop at threshing
  floor, not full food/subsistence work. Approx .25ha/iugerum and8h/day are
  explicit scenario conversions. FAO whole-farm LP is method foundation;
  Bogaard2025 motivates constraints, not coefficients/inequality prediction.
* Manufactured73×5day schedules: same2920annual farm-allocationhours,
  wheat narrow10dayreap =>1.6667ha vs4ha if ignoreseasons or widenreaping30days.
  Sameannualbudget withadditionalharveststaffing also4ha; within3workers×8h/day
  upperenvelope, NOT banked wintertime. Moreland/fasterprep remain1.6667ha.
  Barleynarrow2.5ha comparesworkablearea NOTfood/nutrition. Everytask/budget
  checked;18focusedtests and61linkedcomponenttests pass. No ancientfarm-size,
  foodadequacy, leisure/surpluslabour or population predicted.
* research_notes/farm_labour_20261103.json stores sourcecounts/cachehashes and
  allassumptions. outputs output/farm_labour_20261103; report FARM_LABOUR_20261103.
  New economy_labour_section.py verifies source/input/figure/ledger identities.
  Existing atlas farming/population/climate remain unchanged; published workshop
  only. No climatebenchmark F used or new climatefit adopted.
* Next integration: missing threshing/processing/storage tasks, complete household
  and animalfeed/care budgets, crop-calendar/workability windows, parameter ranges
  from evidence; then minimum work for a supplied food need, not a biome-driven
  civilization score. Current numerical marginals are not historical regime labels.

---

# Same-path seasonal freight connector — 3 November 2026

* Continued after publication3b65b92b. New connector57ef94cb retains physical
  time, freight cost and mode along identical directed legs. Actual raw-r43
  geography recomputed from current atlas (not old Oct25 economic NPZ).
* Fixed endpoints/drawing fractions committed before routing; 12months ×2
  directions retained. A→B26.3–78.1days, B→A28.1–77.6days. These are monthly
  snapshots holding conditions fixed throughout transit, edgewise sailing
  expectation (not whole-voyage weather-spell model). One least-cost path,
  not a fastest journey or cost/time Pareto set.
* Food integration assigns SAME manufactured harvest/budget to either endpoint
  in turn. Both directions meet365farm+146town need under assumed storage365/30
  and departurecap4units/5days. Food ledgersclose2.85e-14; NOT inferred ancient
  population/production/cargo. Finite ships/empty returns are not modeled.
* Audit finds155directed endpointpairs with parallel alternatives permonth;
  legacy CSR sumsduplicates. Isolated connector choosesleastcost thenfastesttie
  and keeps that leg's time/mode. Maximum local summed/selected ratios4.48–20.10
  across months are NOT path-level or map errors. Legacy graphs unchanged.
* publish_freight_corridors.py verifies source/inputhashes and same-path totals,
  renders stored paths with readable white-cased sea lines and correct transfer
  legend. economy_freight_section.py publishes all24paths and assumptions.
  Report FREIGHT_CORRIDORS_20261103.26 focused freight/food/directed tests pass.
* Paired audit then completed with prospective plan8560dc0e: ten fixedsources,
  fourtrade months, identicaltopology/reachability, only155parallelpairweights
  differ eachmonth. No costincrease; all360sampled directedtownpairs unchanged.
  BroadMAmax+.0107%, localMAmax+.0735%; maxindividualroutecostdrop7.807roadkm,
  up to2.654%reachableclaimedpeople have >1roadkm saving for a source/month.
  Small sampled aggregateeffect, not a large trade-map discrepancy explanation.
  Data output/parallel_freight_20261103/review.json. Legacy maps unchanged.
* Next: historical seasonal labour and fixed operation windows; retain
  faster/costlier paths before shortage inference; finite fleet/return-voyage
  scenarios and actual-world crop/storage/labour validation remain separate.

---

# Linked cereal, soil-water, food-stock and provisioning prototypes — 3 November 2026

* Owner approved the four-step implementation (published cereal development,
  continuous crop-sequence soil water, storage, directed town provisioning)
  and asked to continue during work. Components now implemented and linked in
  a manufactured end-to-end scenario, with explicit assumptions. Normal r43
  climate and production farming/population layers remain adopted unchanged.
  No claim of independently validated ancient town sizes or crop yields.
* Daily development harvest/phenology.py independently implements LPJmL4
  Schaphoff2018 eq73–79 and S10/S11 parameters; reference photoperiod disabled
  as paper, explicit cultivar thresholds required to enable it. Source v4
  checked for PVD<=10 and PHU lower-bound conventions, no upstream C imported.
  Country-separated protocol calibration/cereal_phenology_20261103/plan.json
  committed before fitting, selected global parameters frozen f805ea3c before
  evaluation. 237training records/62countries;29evaluation/16countries;19QC
  exclusions. The underlying Sacks dataset was previously inspected, NOT unseen.
* Cereal eval complete/pushed79194116. Equal-country penalized duration error:
  existing heat-only ablation train58.96/eval51.99days; published heat adaptation
  with NO chilling36.96/28.56 (no nonmature eval); fixed45day winter chilling
  97.28/74.05; training-selected global scale.8/PVD15 gives90.86/68.06 with2
  nonmature eval cases (365day penalty retained). Generic chilling fails this
  test; don't adopt that failed candidate or call old ablation atlas date skill.
  Prescribed observed sowing, WorldClim centroid climate, no frost/biomass/yield
  model. Eval pool now scored; don't retune and call it untouched.
* harvest/soil_water.py: FAO56 eq81–88 daily fixed-root-zone conservation,
  no refills between crops, explicit finite field irrigation, periodic state.
  Reproduces published Example37 within.05mm rounding. Field budget != routed
  river supply. No snow/frozen soil, dynamic roots, ponded rice or groundwater.
* harvest/upland_food.py links supplied feasible upland seasons to the shared
  water ledger and individual seasonal Ky responses; no half-weight second
  crop or repeated seed deduction. Explicit analysis guard refuses severe
  deficit extrapolation; no positive food from zero ET demand. The integrated
  demo derives maturity using the new heat-only clock under manufactured
  temperature and prescribed sowing; actual world calendars remain unvalidated.
* polity/food_transport.py is a time-expanded cyclic capacitated food LP:
  directed routes, delay, net retention, seasonal capacity, stocks/spoilage,
  aggregate consumption priorities, then freight/holding-cost minimization.
  Food quantities != gravity weights, costs don't consume calories; no food
  from hidden initial/transit stocks. Ford/Fulkerson1958 is the flow foundation;
  storage/priorities/losses are declared adaptations, not a price equilibrium.
* Complete scenario backend pushed fefecd4b, then zero-ET guard added. Six
  manufactured development->water->harvest->stores->town cases: town need met5.5/54.2/
  69.2/69.2/100/84.9%. Last pair isolates seasonal closure with ample farm
  storage. Initial cases expose a stronger storage bottleneck. No estimates of
  actual granary capacities, famine frequencies or towns. Separate food/water
  ledgers close to floating-point tolerance.97 focused tests pass.
* Evidence reports CEREAL_DEVELOPMENT_20261103 /SEASONAL_FOOD_SYSTEM_20261103;
  outputs output/cereal_phenology_20261103 and output/seasonal_food_system_20261103.
  Economy lab now leads with both studies, methods, full-data downloads, and
  folds previous experiments. Current producer helper
  scripts/economy_component_sections.py verifies all source/result/image hashes.
  Desktop/mobile/dark/light,11downloads, nested-details keyboard checks pass.
  A workspace restart occurred after these checks; restart a local no-store
  server on port8766 for final browser QA. No science jobs remain running.
* Next world integration requires cost AND time for the SAME selected route,
  cargo capacities, rural budgets and town-demand scenarios. Existing graph
  costs are road-km equivalents: NEVER turn them into travel days or treat
  gravity weights as grain. Historical storage/labour, actual cultivar chilling
  and crop-specific soil-water/yield validation remain before production maps.
  River irrigation needs basin/allocation accounting; current finite field
  supply prototype does not create it. All Earth-climate F remains unused.

---

# Observed calendar diagnostic identifies winter-phenology gap — 3 November 2026

* All source-backed joint-calendar and reserve prototypes were published and
  pushed41b76ca9 after345793f2. Continued after pushing with an actual modern
  observed-calendar diagnostic, as owner specifically requested academic basis.
* Committed prospective diagnostic e6224742 BEFORE group-score inspection:
  calibration/crop_calendar_observations_20261103/plan.json. Authors' Sacks2010
  CSV cached locally (1.2MB), raw SHA fixed. Parser keeps all qualifiers; source
  Exclude groups explicitly flagged and separate (notes explain crop weighting
  or ambiguous sequential/spatial cropping). 1510raw ->481 mapped/basic-valid,
  9source-flagged,472unflagged;1025unmapped +4invalid dates. Generic millet not
  treated as foxtail. Source cold summaries missing != zero. No tuning/adoption.
* Unflagged winter wheat138 records:55 outside current duration envelope,
  22 still outside with full-bin30.4day tolerance;54/137 climate summaries have
  below-zero exposure. Winter barley49:13/2 outside,13/48 exposure. Unqualified
  rice145:36/2 outside,0/143 exposure. Every group and record retained publicly.
  This is a necessary-duration/descriptive exposure check, NOT exact predicted
  dates, full agronomic validation, ancient cultivars, independent CI, or an
  exact monthly-model rejection rate. No Earth climate F data touched.
  This Sacks dataset has now been inspected diagnostically; do not later call
  aggregate reuse an unseen test. Freeze geography-separated training/evaluation
  before phenology fitting, disclose prior inspection, and check dependencies
  before treating MIRCA (shared calendar inputs) as independent evidence.
* Next meaningful process: published spring/winter phenology, including dormancy,
  vernalization and photoperiod (Schaphoff2018 LPJmL4 DOI10.5194/gmd-11-1343-2018).
  Not implemented yet; don't claim the new selector solves these processes or
  just widen bounds until all observations fit. Couple sequence soil-water and
  assess period cultivars/labour/yields before adopting population or food maps.
* New files scripts/check_observed_crop_durations.py (optional --download with
  exact source hash), reports/OBSERVED_CROP_CALENDARS_20261103.md,
  output/observed_crop_durations_20261103.62 focused tests pass. Economy lab
  now leads with observed evidence and full-data/declared-plan downloads;
  desktop/mobile/light/dark and all9downloads pass. Figure/source checksums
  guarded in builder. Research manifest updated; sequence/storage numerical
  comparisons rerun unchanged to keep their provenance current.

---

# Joint crop calendars and reserve uncertainty — 3 November 2026

* USER STEERING: keep new mechanics grounded in real academic literature.
  Explicit source/assumption register research_notes/crop_sequences_20261103.json:
  Waha2013/2020 (sequences and sowing), FAO33 response/FAO56 (water), Sacks2010
  observed calendars as a future independent check, not yet scored. The code
  is a simplified prototype, not LPJmL/GAEZ reproduction or ancient validation.
* Joint window selector committed/pushed345793f2; retains all216 annual crop
  windows and optimizes up to2 compatible crops; both-turnaround and year-wrap
  constraints. Existing secondary weight.5, water gate and different-crop rule
  held fixed ONLY to isolate selection. All per-crop maxima exactly reproduce
  production. Same fixed4,096 raw-r43 fantasy samples:113 improved,263 example
  pairs,3150 with tied optima. One-bin turnaround110/261/3094. All12 jointly
  rolled climate/soil origins exactly match energy/count/boundary union on256
  fixed cells. Production yields/population/physics remain unchanged.
* New calendar_stock_bounds computes min/max no-loss reserve requirements
  across ALL tied annual optima, retaining unknown perennial timing. Conditional
  harvest pulses, uniform need equal to annual harvest, zero loss; no ancient
  storage/loss/population coefficient fitted.162 samples show calendar-dependent
  reserves, max range30.815days; five-day vs daily bounds differ≤4days. Five
  perennial-only cases have blank CSV bounds (not zeros). Formula checked against
  independent cyclic-deficit and repeating inventories in120 cases/3 clocks.
  58 focused tests pass. Sources harvest/{crop_sequences,calendar_stocks,
  calendar_sample}.py; reports CROP_SEQUENCES_20261103 /CALENDAR_STORAGE_20261103.
  Outputs under output/crop_sequences_20261103 and output/calendar_storage_20261103.
* Normal .bat hub's economy lab now presents both comparisons, academic source
  register, CSV and explicit limits. Older manufactured/tie checks folded into
  keyboard-operable details. Desktop/mobile/light/dark/downloads pass, no
  overflow. Public models still require observed-calendar evaluation, coupled
  crop-specific sequential soil water, historical labour/cultivar evidence and
  revalidation of capacity/fallow before adoption. No new physics trials active;
  r43 remains adopted and F remains unused.

---

# Calendar evidence and final drying qualification — 3 November 2026

* Stronger dry-branch qualification is COMPLETE/REJECTED, a55cb748, pushed to
  both branches. S61=1.0023168712, temperature +.05438%, rain loss +.40899%;
  historical49 S=1.0054999951, rain +.94186%. No fine or reserved F case ran;
  F remains unopened. All six declared physics/publication jobs now finished.
  Normal r43 physics remains adopted. Public latest section and full paired
  evidence: atlases/climate_accuracy/data/dry_branch_validation.json.
* Actual crop-calendar ambiguity now quantified by a passive production-model
  audit on4,096 systematic raw-r43 fantasy land samples. Original kcal mix
  reproduced, individual crop yield drift0. Calendar origin changes mix in226
  samples; alternative individually-optimal masks permit a better pair in58.
  Largest local gain47.12%, unweighted sample energy sum+.151%; NOT whole-map
  area/population forecasts. No production crop/yield/population layer changed.
  harvest/calendar_audit.py, scripts/audit_crop_calendars.py,
  reports/CROP_CALENDARS_20261103.md, output/crop_calendar_audit_20261103.
  Five analytic/control tests plus Harvest/food stocks:31 tests pass.
* Economy lab now includes this observed model diagnostic beside its explicitly
  manufactured inventory experiment. Desktop/mobile dark/light browser passes.
  Final publication QA: Windows1,061 byte-exact assets; portable1,625 files,
  644links; climate companion73 studies/169 images with working keyboard and
  deep links. Final receipts in output/crop_calendar_audit_20261103 and
  output/dry_branch_validation_review_20261103. ZIP stays local under the
  food_stock_prototype output folder; all bundle sources indexed and hashed.
  Next: retain all feasible crop windows, jointly select compatible sequences
  (turnaround, same-crop policy, perennial timing explicit), validate calendar
  behavior, then connect to stocks. No precise harvest dates from tie-breaking.
  Town grain balance, household labour, finite irrigation, seasonal herds and
  state provisioning remain researched proposals, not quietly adopted models.

---

# Economy lab publication and one frozen climate qualification — 3 November 2026

* Complete r43 is live. Normal .bat hub now links Food, farming and society
  (atlases/economy_lab/): six researched proposals plus the isolated food-stock
  example. Actual production climate/economic layers remain unchanged by this
  lab. Desktop/mobile, both themes, downloads and no-overflow pass; portable
  1,621 files /639 links and Windows 1,058 byte-exact assets pass. Source
  outputs/receipts: output/food_stock_prototype_20261103 (ZIP stays local).
* Existing dry-branch rate .4/day is prospectively frozen in
  calibration/dry_branch_validation_20261103/plan.json (2cf3763a). Only one
  parameter differs. Fresh baseline numerical reproduction PASSED; candidate
  full61 running at 14:19 UTC. Session66825 / PID4148, supervisor20952;
  output/dry_branch_validation_20261103.log. Scientific source c20f99bd private
  model; do not edit its frozen orchestrator/shared source dependencies.
  Pipeline: full61 gate -> paired fine28 -> reserved F ONCE if qualified.
  No auto-adoption. F remains unopened as of this note. Supervisor --status
  checks real process identity; environment shutdown stops work.
* Public fixed-face section now includes the completed NEGATIVE fitted-flux
  screen, browser checked. No fitted transport physics was adopted.

---

# Human-model prototype and final physics-screen outcomes — 3 November 2026

* Economic proposals have been PRESENTED to the owner after complete r43
  publication. First bounded implementation now harvest/food_stocks.py:
  net-edible energy inventory, explicit capacity/spoilage/overflow/unmet food,
  finite-year and smallest-periodic-reserve modes, exact zero-loss minimum
  capacity. No atlas economic model, crop yield, population or FORGE changed.
  38 focused Harvest/FORGE/inventory checks pass; stale settlement_cored test
  fixture repaired. Manufactured demo: identical annual365 harvest/demand,
  capacity200 gives164 shortage days for one harvest vs0 for two; no actual
  world prediction. Report reports/FOOD_STOCKS_20261103.md; full demo receipt
  output/food_stock_prototype_20261103. Calendar ties/perennials/double crops
  need validation before integration; don't manufacture exact harvest dates.
* All five earlier pipeline jobs COMPLETE and pushed. Fitted-vs-upwind screen
  b1691d33: fitted S8=2.18614 vs production, upwind-flux2.11131; fitted rain
  loss4.76% worse than upwind flux, no adoption/F. Default numerical control
  passes. Do not call reduced numerical smearing a climate improvement.
* Bound probes0c142313: lower marine thresholds do not help. Stronger existing
  dry-branch rate0.4/day gives S8=.97461255, T−.7879%, P−4.2896%; combination
  S8=.97546346. Reused8-region evidence ONLY; not selected/adopted by that
  screen. Any broader qualification must prospectively freeze one candidate,
  reproduce full61 control, report historical49 separately, then fine/F gates.
  F remains unopened. Keep the owner's human-model priority; no new physical
  family such as geometric conductance has been implemented/launched.

---

# Verified release complete — 3 November 2026, 14:30 Warsaw

* R43 atlas publication COMPLETE and pushed to BOTH branches in1ac032ab.
  The normal .bat-served Earth atlas is now actuallyr43 (70 raw /55 corrected
  layers, all5 languages). Corrected strict target agreement37.4727%, raw34.4712%.
  Matching corrections and ALL climate/food/people/foraging/political/trade/language
  exports complete. Raw9-layout and3-extra-year diagnostics pass; cycles repeat.
  Browser checks all3 atlases, Windows1,053 byte-exact assets, portable1,613
  files/627links pass. Launcher and page display actual r43 metadata. Source
  snapshot remains8cfdf7b4 with validated scientific model03c4351f.
* Full61 storm study COMPLETE/REJECTED, results9d3d6ab1, public evidencefe7ffc46.
  S61 1.026560 /1.016619. F remains unopened. Do not advertise the initial8-region
  gain as broad improvement or select a failed family.
* User's requested next phase: return to c.200AD state/farming/trade/anthropology
  and present proposals. Concrete researched note now reports/ECONOMY_PROPOSALS_20261103.md,
  with existing-feature/source audit research_notes/economy_proposals_20261103.json.
  Recommend agricultural seasonal stocks + real grain provisioning, then labour;
  finite irrigation needs audited catchments (current flow index is not m3/s).
  Optional forager storage already exists and was rejected, so don't sell it as
  new validated progress. Forager cycles need numerical checks before risk maps.
* Fitted transport screen is now ACTIVE (source-pinnedc20 model), profile reference,
  session40089. Bounds session47219 waits for that complete screen. Both reuse8
  development regions, no F/adoption. Supervisor4645 monitors live processes;
  status command .venv/bin/python -I scripts/continue_climate_work.py --status.
  No new physics families have been launched; geometric conductance is backlog
  only. Continue the user's human-model direction while the declared screens run.

---

# Owner's next priority and latest result — 3 November 2026

* USER STEERING: after the next full physics update, return to the c.200 AD
  state/farming/trade/anthropology model and PRESENT proposals for mechanics
  or maps. Finish the current verified r43 atlas release and full61 report,
  then present concrete researched choices. Draft prepared in
  output/econ_proposals_20261103/proposals.md: seasonal food/storage, actual
  grain provisioning, finite irrigation water, household labour, pastoral
  transhumance and delivered fiscal surplus. Existing forager storage was
  tested/rejected; avoid proposing it as a new proven gain. Modern papers
  support mechanisms, not universal200AD coefficients or climate determinism.
* Storm61 COMPLETE, auto-committed/pushed9d3d6ab1. Both profiles rejected:
  storm-r42 S61=1.02655993 (rain+5.2287%), storm-r43=1.01661899 (rain+2.8546%).
  No finalist, fine test or F run. F remains unopened. Source-pinned study
  fully finished; no score from partial cases. Broad research producer
  scripts/publish_storm_expansion.py verifies full raw packets and handles
  failed profiles as unscored. Its public page/browser QA is ready.
* R43 raw exports, nine-layout sensitivity and3-extra-year settling checks
  COMPLETE; annual cycles repeat. Matching corrected layers COMPLETE.
  Corrected full export is now freight season3/4 (13:24UTC). Then languages,
  identity, promotion/browser/Windows/portable/push. Keep checking supervisor
  status; final publisher waits for committed research at the package boundary.
* Fitted transport and calibration-bound probes remain prospectively queued
  after atlas publication, then sequentially. They can continue in background
  while economic proposals are discussed; don't open further physics families
  before honouring the user's priority. A geometric storm-conductance idea is
  documented ONLY as backlog in reports/NEXT_PHYSICS_20261103.md, unimplemented.

---

# Resumed after environment restart — 3 November 2026, 13:49 Warsaw

* One-command recovery/status now available:
  `.venv/bin/python -I scripts/continue_climate_work.py --status` reads actual
  processes, never stale marker text. Run without --status to attach/resume
  all five committed jobs and monitor them in the foreground. Supervisor
  session4645 currently attaches to all five live drivers, without duplicates.
  It cannot keep a shutdown workspace alive; rerun after environment restart.
  Two process-identity/argument-matching tests pass. Do not claim overnight
  computation merely because a saved marker says running.
* Host restarted between overnight and today's Continue: no overnight progress
  after01:10UTC. Fetched origin; both remote refs are ancestors, no external
  changes. Do not mistake stale running markers for live processes.
* ACTIVE snapshot builder session35814; publisher47579. Raw world export is
  COMPLETE and stages_completed=[world]. Diagnostics resumed (two workers);
  corrected layers/full corrected export and language/QA/push follow. Matching
  r43 correction training remains complete. Snapshot scientific model03 pinned.
* ACTIVE storm61 session91042, one worker nice5. Full61 damped control PASSED:
  max monthly drift .0035593 C/.0493469mm, same forcing/observations. First fixed
  physical profile resumes after40 passed cases; second must also finish before
  selection/fine/unopenedF. Private source03, active plan_v2 unchanged.
* ACTIVE fitted-flux screen session40089 waits for full r43 publication, using
  private sourcec20f99bd. The new default-upwind numerical implementation passed
  111 focused tests. No climate result for fitted flux yet; do not imply one.
* Retrospective search design audit:36 unique proposals, rank9, condition6.53;
  whole-start linear prediction MAE .57/1.34/.65%, comparable to .86% gain.
  No unseen data, new candidate selection or global-minimum certificate.
  Public plot/evidence ready, browser71studies168images, no errors.
* New prospective fixed bound-probe screen follows the completed fitted screen
  (then reuses its exact fresh pinned-source r43 control). Four profiles:
  positive marine threshold .15/.05, branch drying .4/day, .15/.4 combination.
  Zero threshold is intentionally AVOIDED because it disables the marine gate.
  Eight reused regions only, no selection/fine/F/adoption/atlas change.
  Driver scripts/screen_parameter_bounds.py; plan calibration/parameter_bounds_20261103.
* Space3.1GB after removing three superseded generated ZIPs; latest verified
  r42 final bundle and all maps/source/results preserved. Cleanup receipt tracked.
* Main atlas template now shows actual metadata physics_profile in loaded-data
  status. Final r43 publisher will refresh normal pages from this template.
  Both remote branches must be atomically pushed at milestones. Continue after
  pushes, post generated maps, never claim a background job survived a restart.

---

# Latest running jobs — 3 November 2026, Warsaw

* Main physical option c20f99bd: conservative fitted vapor face transport,
  `moisture_flux_scheme="exponential"`, default upwind unchanged. 111 focused
  tests plus 33 declaration/operator tests pass. Screen frozen in6bd040ae,
  private modelc20f99bd, session12649 waits for r43 publication; no F/adoption.
  Plan calibration/fitted_flux_20261103/plan.json. Main driver/helper hashes
  are frozen; do not edit them during active studies.
* Atlas source-data preflight restored pinned /land/ after /ravages/. Snapshot
  scientific sources unchanged; all harvest provenance inputs verified present.
  Current build session28453 and publisher37574 (older sessions failed). Raw
  farming/population/foraging exports now complete; political/trade export runs.
  Source-root repair remains8cfdf7b4, original validated model03c4351f.
* Storm61 session62644 is integrating its full numerical control, no physical
  candidate yet; see output/storm_expansion_20261103b/status.json. Main helper
  scripts/run_atlas_snapshot.py cannot be edited while this frozen driver runs.
  Future initial sparse-checkout setup must include /land/ as well as /ravages/;
  current snapshot has them manually restored from its exact pinned commit.
* Completed factorial now published to research companion, all four scores and
  matched monthly curves; browser QA70 studies166images, no errors. Producer
  scripts/publish_storm_factorial.py. Default model/atlas labels remain separate.
* New zero-integration observer scripts/diagnose_face_convergence.py observes
  fixed-state point-to-flux advection difference on verified raw r43 world.
  It is not a rainfall prediction and does not include removing the old import
  closure. Two analytic tests pass; outputs output/face_convergence_20261103.

---

# Active continuation — 3 November 2026, 01:40 Warsaw

* r43 is adopted (58e19b16), after all 39 search records, paired reproduction,
  fine28 and sealed-e validation. S49=.991378006, fine28=1.008070474,
  sealed-e=.999790900 (effectively tied). T49=1.878921 C, rain loss=.49314846.
  All planet/orbit settings fixed. E is now spent; reserved F remains unopened.
* Normal atlas STILL r42 pending the complete pinned r43 rebuild. Build session
  98719, publisher 68393. Snapshot: output/atlas_r43/snapshot, source 8cfdf7b4,
  scientific model exactly validated 03c4351f. Correction training COMPLETE.
  Linked input receipt paths and omitted Ravages data repaired in f75e631c;
  exact snapshot helper repair is merged into main (c0d87cfc). Raw world climate
  checkpoint verified, target agreement 34.2273 -> 34.4712%; no relabelling of
  older served maps. Rebuild is resuming export from its saved checkpoint.
* Original conservative replay COMPLETE (03c140e2), no winner. Isolated storm
  factorial COMPLETE (a4e131d2): storm-only S8=.9729019, rain loss -4.36%,
  temperature -1.06%. Flux alone S8=2.1720; added accounted rainout S8=1.1108.
  This is reused eight-region development evidence, not adoption/generalization.
* Broader fixed storm-r42/storm-r43 comparison prospectively declares 61 regions
  (49 historical + spent D/E), reports S49 separately, no regional/group veto.
  Driver scripts/expand_storm_exchange.py active plan is plan_v2.json under
  calibration/storm_expansion_20261103. Session 62644 (one worker, nice5),
  output/storm_expansion_20261103b/status.json, own pinned model worktree03.
  Plan A stopped at setup waiting for failed training receipt: ZERO integrations.
  Revision B changes orchestration hashes/output only; all parameters/policy
  unchanged. Full damped control first; then BOTH61 cases before selection,
  one frozen finalist -> paired fine28 -> reserved F once. No auto-adoption.
* Public research companion adds completed r43 calibration and raw world preview;
  generated by scripts/publish_r43_calibration.py. Keep it committed before the
  final atlas publisher packages. Historical r39 cards explicitly historical.
* Exact resumable market-access/trade checkpoints committed03c4351f. Source
  snapshot isolates atlas from main development; don't alter shared raw input
  archive bytes or legacy shared derived cache files while studies are active.
* ALWAYS atomic push BOTH refs: claude/ecstatic-wozniak-rtrwd2 and DEFAULT
  claude/friendly-turing-43ygeu. Launcher fix badaefe7 fresh port/URL/no-store and
  verified release.json is published to both. User wants continuous iteration,
  commits/pushes at milestones, generated maps posted, no pause after pushes.
* CPU quota2, disk ~2.4GB free. Main .venv scientific libs; system python has
  Playwright, Chromium /usr/bin/chromium. Long jobs foreground persistent exec
  sessions. No new subagents. Dates Europe/Warsaw. Research server8766 running.

---

# Active continuation — 3 November 2026 (Warsaw)

* The workspace restarted; old processes/sessions were gone. Resumed frozen
  three-start search in persistent session **34654** (nice 5, two workers) and
  conservative replay in **97823** (nice 10, one worker). No source or parameter
  changes were made to either. Third search start has 9/13 records; starts 1/2
  each have 13. Best still chain 1, n=7, S49 0.9913780. No sealed-e results.
* **Automatic paired validation is now queued**, session **70465**, using
  `calibration/r42_multistart_validation_20261102/plan.json`. It waits for all
  39 records; freezes and commits one finalist plus all records; reproduces
  both full dev49 vectors and actual reference footprints; runs paired fine28;
  commits qualification before opening sealed e only if both gates pass.
  Every outcome/raw packet is retained. It commits/pushes its own artifacts,
  but does NOT adopt physics or rebuild an atlas. Four targeted tests passed.
* **Launcher stale-page fix is published** in badaefe7 to BOTH branches:
  `claude/ecstatic-wozniak-rtrwd2` and default `claude/friendly-turing-43ygeu`.
  The default was an ancestor and was fast-forwarded, without history rewrite.
  User's screenshots proved their metadata were current (70 Earth modes,
  Whittaker 1.44%) but browser showed the old 22 October hub. Normal launches
  now use a fresh available port plus unique URL; explicit ports remain
  supported. Launcher prints folder, checkout branch/commit, and r42 release
  only if all metadata and normalized hub hashes match atlases/release.json.
  build_fit_hub regenerates that manifest; packaging includes it. Windows
  line-ending normalization is tested. Real stale-cache/browser test, 1,000
  Windows-checkout assets, portable launch and three unit tests passed.
  Receipts/screenshot: output/launcher_refresh_20261102. User was told to pull,
  close the old tab, rerun the .bat, and use its new URL. Never say the launcher
  automatically downloads updates; it still serves local files only.
* Conservative screen: numerical control and first THREE physical profiles
  complete (4/5 total). Combined ratios vs r42 control: flux+storms 2.1144,
  mass-balanced counterflow 1.4562, independent reservoirs 1.6166. The final
  resolved-drying profile is running. None adopted; no partial-profile score.
  Source review/figure: `scripts/review_r42_transport.py` and
  `output/r42_transport_review_20261102`. Research companion now opens on
  these results, explicitly marking pending outcomes, with 32 verified raw
  packets. `scripts/publish_r42_transport.py` updates it; browser navigation,
  dark/light, mobile, images and downloads passed before the fourth data row.
* New prospective factorial, committed in e23ba585, queued in session **71498**
  behind the original screen. Plan: calibration/r42_storm_factorial_20261102.
  Four profiles: vapor flux alone; symmetric storms alone; accounted crest
  condensation; flux+accounted condensation. Baseline r42 eddy_rainout is ZERO;
  the latter two explicitly ADD eddy_rainout=1 (local saturation), not an
  inherited active cap. All four construct with the same Earth planet, no
  imposed wind/SST. Maximum 32 reused-region integrations, no retuning, unseen
  evaluation, adoption or normal atlas changes. Driver will publish all results
  to both branches. Report: reports/TRANSPORT_FACTORS_20261102.md.
* `scripts/review_r42_multistart.py` is ready for selection.json after all starts.
  It plots every start and estimates descriptive region-mix sensitivity. This
  resampling is explicitly not selection-corrected generalization uncertainty.
  Analytic scaled-error test passed. Do not run it before selection exists.
* Canonical model/benchmark sources remain frozen for all active/queued studies.
  Independent producers/plots may change. Keep the normal atlas on adopted r42
  until a fully qualified candidate is reviewed and adopted. Future atlas
  publication must keep BOTH remote branches current, not just development.

---

# Post-publication physics continuation — 2 November 2026, 15:48 UTC

* All atlases are published and verified; see release notes immediately below.
  Latest pushed bookkeeping/preview commit **e95a9677**, release **c55e705c**.
* Conservative replay session **61643** passed all eight damped numerical
  controls (forcing/observations equal, strict checks passed, all monthly
  field drifts within prospective limits). It is now integrating
  `flux_conservative`, followed by counterflow and reservoir variants.
  Live status: `output/r42_conservative_replay_20261102/status.json`.
  This experiment cannot adopt physics or update the atlas. Its driver will
  retain every profile outcome, commit its completed result packet, and push.
* Three-start calibration session **75930** reached **chain 3** at 15:46.
  Chains 1 and 2 completed 13 evaluations apiece. The best remains the chain-1
  candidate S49 0.9913780 (T −0.27%, rain −1.46%). Wait for all 39 and the
  selection.json finalist before validation. No sealed-e evaluation yet.
  The portfolio driver itself does not commit, validate or adopt candidates.
* Canonical model/benchmark sources remain frozen for BOTH active experiments.
  Do not change their source hashes mid-run. Next after portfolio completion:
  freeze/commit the one finalist, reproduce paired dev49 on current geometry,
  paired fine28 (California, western Europe, Japan, NZ), then only if both
  qualify run the declared unseen set e once, with r42 as its paired control.
  `scripts/validate_v3.sh` defaults to r41 and spent set d: override these or
  run its steps explicitly. Aggregate improvements count; regional/group
  regressions are reported, not individual vetoes. Reproduction checks must
  account for the recovered Tripolitania footprint, not its obsolete cache.

---

# r42 atlas PUBLISHED — 2 November 2026, 15:43 UTC

* **Release commit c55e705c is pushed** to
  `origin/claude/ecstatic-wozniak-rtrwd2`; remote HEAD was read back and matched.
  The normal `atlases/earth_fit` folder and `.bat` launcher now serve r42.
  Free-fit and Whittaker map data are byte-unchanged; Whittaker remains 1.44%
  outside the diagram. Three final browser tests passed, Windows checkout
  retained 1,000 byte-exact assets, and the portable bundle passed 560 links,
  1,554 entries and the fresh extracted launcher. Receipts:
  `output/atlas_r42/final_qa/{publication,completion,portable}.json`.
* Earth atlas: 70 raw modes, 55 corrected modes, all five language layers
  restored. Raw target-zone strict agreement 34.23%, corrected 36.56%; these
  fantasy-world target agreements are separate from Earth validation skill.
  R42-trained dev31 correction scores: temperature 1.7144 -> 1.5616 C,
  rainfall loss 0.4347 -> 0.4233 with geographic clusters held out.
* Release session 83151 and finalizer 95390 both finished successfully.
  Do not rerun promotion. Old r41 atlas is retained in
  `output/atlas_r42/previous_atlases/earth_fit_r41`; complete portable ZIP is
  `output/atlas_r42/final_qa/rotclimate_r42_atlases.zip` (not in Git).
  The prospective publication source freeze has completed.
* Calibration session **75930** is running again. Its two workers were
  temporarily SIGSTOPed at 15:37 to prioritize atlas export; watchdog session
  33364 automatically resumed both at 15:43. This changed no model inputs,
  tolerances or candidate order. Search still uses frozen source identities.
  Do not edit canonical model code until the search completes.
* Conservative replay session **61643** started its damped numerical control
  at 15:43 after observing the verified publication marker. California has
  completed. Watch `output/r42_conservative_replay_20261102/status.json` and
  `reference_damped.log`. It must pass forcing/observation equality, strict
  checks and declared monthly-field drift before any physical profiles.
  Its canonical model sources remain frozen too. No candidate adoption or
  sealed-e evaluation has occurred.
* Posted rainfall/Whittaker preview is retained in
  `output/r42_atlas_preview_20261102`; rendering now reads both exact published
  Git revisions, so later atlas overwrites cannot invalidate the comparison.
  User was told the atlas is ready and to pull then run start_atlases.bat.

---

# Current jobs — 2 November 2026, 15:35 UTC

* The r42 release is still running in session **83151**. Raw export and
  correction training finished; corrected climate, farming, population and
  foraging exports finished. Corrected political reach is routing freight
  (season 2/4 complete). Watch `output/atlas_r42/corrected.log` and
  `output/atlas_r42/resumed_20261102.log`. The served Earth atlas remains r41
  until staging is complete. Latest user ETA: 15–25 more minutes at 15:32 UTC,
  including final checks and push; explain any overrun honestly.
* Finalizer session **95390** waits on RELEASE DONE using committed
  `calibration/r42_atlas_publication_20261102/plan_v2.json`. Do not edit its
  guarded model/producer/template/research sources. It will promote/verify
  the release, smoke-test all three atlases, test checkout/portable launch,
  commit only its declared artifacts and push. Preserve the r41 backup.
* The three-start search is still session **75930** (nice 10). First start
  completed 13 evaluations; second has 11/13 logged. Best provisional S49
  0.9913780 relative to r42 (temperature −0.27%, rain loss −1.46%). No adoption
  or sealed-e run before all starts and finalist validation.
* New conservative-moisture replay is committed and queued in persistent
  session **61643**, nice 10, one worker. It waits for finalizer status
  `finished_pushed`; see `output/r42_conservative_replay_20261102/status.json`
  and its sibling `.log`. Prospective plan/README:
  `calibration/r42_conservative_replay_20261102`. Eight existing development
  regions, a damped numerical control first, then four existing conservative
  transport/counterflow/reservoir profiles, maximum 40 new integrations.
  Strict checks unchanged. All outcomes retained, no partial-profile averages,
  no automatic adoption or map changes. It commits/pushes only its own results.
  Three targeted tests passed. Canonical physics is unchanged.
* Created and posted a comparison of r41/r42 corrected annual rainfall and
  Whittaker maps: `output/r42_atlas_preview_20261102/`. Existing exported maps,
  no model rerun; script and byte hashes retained. The final atlas still needs
  trade export and final QA. Free/Whittaker map data are unchanged.
* Latest pushed commit before this note: **031985b2** (queued physics screen).

---

# Release completion queued — 2 November 2026

* Active publication declaration is
  `calibration/r42_atlas_publication_20261102/plan_v2.json` (committed).
  `scripts/finalize_r42_atlas.py --run .../plan_v2.json` is running in persistent
  session **95390**, at nice=5. Watch
  `output/atlas_r42/final_qa/automation_status.json` and
  `output/atlas_r42/finalization.log`. The older plan.json was NOT executed
  and is superseded; its self-source guard no longer matches.
* This job waits for the existing release's RELEASE DONE marker, checks source
  identities (including the declared hub-label change), raw r42 checkpoint,
  matching physics/correction models, language layers and unchanged other-fit
  map data. It browser-tests the final atlases, tests Windows checkout and the
  complete portable bundle, then commits only whitelisted release artifacts
  using git commit --only and pushes the resulting commit. User's unrelated
  staged work and already-staged deletions are covered by an actual Git test.
  Eighteen new targeted tests pass in this iteration.
* The publication plan guards producers, templates and the research companion.
  Do not edit those files while waiting. Do not run another finalizer or
  start the promotion script again. If the job fails, inspect its exact
  receipt and retained logs; preserve the declaration and unfinished work.
* Raw r42 atlas browser check passed; shared physical settings match the r42
  profile exactly, strict world target agreement is 34.23% (r41 32.56%).
  All nine surroundings checks and the three-extra-year repeatability check
  passed. Production is waiting for the separately started correction job.
* Temperature correction training is complete: dev31 raw monthly T MAE 1.7144
  -> cluster-held-out 1.5616 C. Full-grid 14 km field reconstructions have
  completed; rain pattern training/evaluation follows. Release and correction
  jobs serialize their common output via flock and a verified receipt.
* New research companion passed keyboard/deep-link, mobile/dark/light checks;
  Windows checkout preserves 997 asset bytes exactly. Updated portable bundle
  passed 560 links / 1551 archive entries / freshly extracted launcher. These
  checks precede the final r42 corrected atlas; that gets its own final QA.
* Best provisional search result is now S49 0.9913780 relative to r42 (T −0.27%,
  rainfall loss −1.46%), still only partway through the first of three starts.
  The old 0.56% candidate remains historical intermediate progress. No early
  adoption, no sealed-e evaluation. Current campaign source hashes unchanged.

---

# Iteration update — rainfall processes and atlas release, 2 November 2026

This section supersedes the earlier job-stage notes.

* Production physics is unchanged r42. The three-start 49-region campaign is
  still active (`output/r42_multistart_20261102b`). First generation has one
  provisional candidate S49 0.9944235 (T −0.96%, rain −0.15%); historical
  holdout group +7.75%, retired desert group −8.37%. Do not adopt/select early:
  all 39 evaluations, paired fine-grid and frozen finalist/sealed validation
  remain required. Set e is untouched. Background search has nice=10.
* Completed four **full-footprint r42 moisture diagnostics**, exactly
  reproducing ordinary T/P benchmark errors. Plan and receipts:
  `calibration/r42_rain_diagnosis_20261102`, `output/r42_rain_diagnosis_20261102`.
  Tripolitania's main error is false summer rain (JJA 1.146 vs 0.007 mm/day),
  whereas North India's monsoon is weak (2.623 vs 5.643). Signed column terms
  are concentration-equation tendencies, not global mass conservation or
  independent water-origin tracers. Monsoon drying is a subset of total drying.
* Completed isolated **continuity-limited branch drying** probe. Frozen copy
  lives under `experiments/descent_continuity_20261102`; it does NOT replace
  or monkeypatch production. Ordinary / disabled / enabled runs in four regions
  all pass; disabled reproduces all eight full-domain output arrays exactly.
  Aggregate four-region error **worsens 1.50%** (rain +2.70%, T +0.30%); India
  rain improves 2.56%, desert worsens 8.18%. Not adopted or advanced.
  Source diff, raw fields and every result retained in
  `output/descent_continuity_20261102`; report `reports/RAIN_PROCESSES_20261102.md`.
* The served **Climate accuracy** companion now opens on these completed
  results, with two figures and eight verified raw-packet downloads. Its old
  r39 headline cards are explicitly historical; the current r42 overview
  links the release/reference-recovery evidence. Publication script:
  `scripts/publish_r42_rain_processes.py`. No normal map fields changed.
* r42 raw atlas export has finished (14:19 UTC); diagnostics are running.
  Release is still `output/atlas_r42/release.sh`, persistent session 83151,
  `output/atlas_r42/resumed_20261102.log`. Raw trade export was expensive:
  463,000 physical graph nodes, not the 116×250 climate grid. `py-spy` read-only
  stack sampling confirmed progress in market access, then ordered shipments.
* **Correction training is now running independently in parallel**, at nice=5:
  session 75656, log `output/atlas_r42/corrections_early.log`, per-case logs
  under `output/earth_correction_r42_20261101`. The release will call the same
  script later. `scripts/retrain_earth_corrections.sh` now locks its output;
  a complete artifact/source/input-cache checksum receipt permits reuse,
  otherwise ordinary per-case source/reproduction checks apply. Never start
  another unlocked writer to these folders. Canonical rotclimate/*.py remains
  unchanged so the running atlas checkpoint/search source identities hold.
* Eleven new unit tests passed for diagnostics, continuity bounds and training
  receipts. The new research page passed browser checks before its historical
  headline relabel; rerun after that text update. Finish Windows checkout,
  portable package and current/final atlas browser QA before final publication.
* On release completion: inspect corrected models/evaluations, raw/corrected
  atlas browser flows, preserved language layers, page notes and hub. Commit
  all r42 release assets and correction models (force-add required ignored NPZ
  model files), retain previous r41 atlas outside publication. Push to
  `claude/ecstatic-wozniak-rtrwd2`. Do not rerun the whole promotion script once
  its r41 backup exists. Do not treat intermediate fit progress as adoption.

---

# Latest state — reference recovery, 2 November 2026

This supersedes the running-search details in the next section.

* The original pilot stopped at its first logged r42 control: 48/49 error
  pairs reproduced exactly, but Tripolitania did not. Auditing the actual
  case hashes with the original float-valued `cell_km` confirms **48/49
  input cases match exactly**, too. Tripolitania has 182 scored land cells
  versus the archived 195 despite identical scientific-source and WorldClim
  archive hashes. The exact old aggregation cache is unavailable; a legacy
  name-only cache key is a possible cause, not a proved diagnosis.
* Fresh **paired r41/r42 runs on all six retired-c regions** completed strict
  checks and retained raw NPZ cell packets in
  `output/r42_reference_recovery_20261102`. Reconstructing S49 with these
  matched inputs gives **0.9628116258** vs r41, still a 3.72% improvement.
  Every one of the 49 recovered r42 reference error pairs matches the saved
  current control to 1e-10. Original scores and failed runs are retained.
* Active search is now the prospectively frozen revision
  `calibration/r42_multistart_20261102b/campaign.json`, same bounds, seeds,
  39-evaluation budget and selection rules, with retired-c references from
  the fresh run. Output `output/r42_multistart_20261102b`, execution session
  75930, two workers. Original `output/r42_multistart_20261102` is a STOPPED
  diagnostic run, not an active search. Sealed set e remains unseen.
* The revised search's first full control completed: S49 = S31 = 1.0, all
  49 reference error pairs reproduced to 1e-10. Candidate evaluations have
  now started; no candidate is adopted. The first control and frozen search
  identity are retained in `output/r42_multistart_20261102b/chain_1`.
* The r42 atlas simulation completed and saved its verified checkpoint;
  export is running. Its persistent release session is still 83151. The
  served atlas stays r41 until staged corrections and exports finish.
* Do not edit `rotclimate/*.py` while the release/checkpoint and calibration
  sources are frozen. A future cache fix should include complete geometry
  and source identity in aggregate cache keys or manifests and explicitly
  handle legacy unmanifested NPZs. Do not silently relabel an old score.

---

# Active continuation — 2 November 2026

Read this section before the older handoff below.

* Fetched `origin/claude/ecstatic-wozniak-rtrwd2` at `46db7674`, the newer
  development branch. The old checkout's two terrain numerical-probe commits
  remain on local branch `work`; its untracked outputs were preserved. Active
  branch: `work-latest-20261102`, tracking the newer remote branch. Both remote
  branch fetch refspecs are now configured locally.
* Adopted physics **r42**, not r39. Archived paired 49-region raw results:
  monthly T MAE **1.9770 -> 1.8849 C**, rain loss **0.51530 -> 0.50077**,
  S49 **0.9626111** vs r41. 29 regions improve / 20 worsen under the combined
  metric. Set d S **0.9406**. These are regional benchmarks, not global skill.
* **The served Earth atlas is still r41 until the release completes.** The
  inherited r42 release stopped during the simulation in the previous
  environment. Its path was hardcoded to `/home/user/rotclimate`. The resumed
  `output/atlas_r42/release.sh` is repository-relative and builds corrections,
  corrected animations and language layers in staging before promotion;
  the r41 atlas is retained. Do not label the atlas r42 before promotion.
* Calibration mismatch fixed: `scripts/gate_calibrate.py` now accepts
  `scoring_policy: v3`, equal-region S49 including retired a/b/c, reports
  group regressions without penalties, keeps the individual T/P safeguards.
  Legacy v2 plans retain their objective. v3 resumes freeze the plan,
  references and source identities. r42's archived score matches the independent
  release gate exactly. 69 targeted tests passed (calibration, guarded search,
  physics switches and Earth corrections).
* Frozen pilot `calibration/r42_multistart_20261102/campaign.json`: three
  independent CMA starts (r42 and two scrambled Sobol centres), 13 evaluations
  each, existing r42 parameter bounds, no orbital/world changes. Each start
  first reproduces r42 over all 49 regions to 1e-10. No sealed evaluation
  occurs in the runner. This tests starting-point sensitivity within one
  parameter box; it cannot prove global optimality.
* Fresh sealed set e: `calibration/sealed_20261102e`. Six scored rectangles
  checked against all 61 earlier definitions, none overlapping; forcing halos
  are not independent. Never use this set in search or mechanism design.
  Freeze one finalist after the S49 / 28 km gates before its single evaluation.
* Running jobs use persistent foreground execution sessions. In this executor,
  shell-detached `nohup ... &` children were terminated after their launching
  shell ended; those interrupted logs/output directories were preserved.
  A subsequent clean restart has no completed candidate yet at this handoff's
  initial writing. Check processes and receipts; do not trust stale PIDs.
  - r42 release: `output/atlas_r42/resumed_20261102.log`, per-stage logs in the
    same directory. Execution session 83151.
  - search: `output/r42_multistart_20261102/status.json`, `chain_1.log`,
    `chain_1/evals.jsonl`; execution session 90518. Two workers alongside the atlas build. Resume with `.venv/bin/python -u -I
    scripts/run_calibration_portfolio.py --campaign
    calibration/r42_multistart_20261102/campaign.json --out
    output/r42_multistart_20261102 --workers 2` in a persistent session.
* The first full control reached a logging integration error (`n` counted both
  evaluations and regions), before metrics were persisted. Fixed by keeping
  `n_regions` separate; a real CMA/log/checkpoint/resume integration test now
  covers the path. The failed run and exact source are retained in
  `output/r42_multistart_20261102_recording_failure`; the clean replacement
  must reproduce its baseline before any candidate claim.
* On finishing the atlas: browser-smoke raw/corrected views, package and verify
  the portable bundle, then commit/push all release assets and update the
  r42 report. Packager now includes r40-r42 and current foraging/language/reach
  method reports, and avoids claiming the Earth atlas is still r38/r39.
  Do not rerun the whole release over a promoted atlas/retained r41 backup.
* Portable bundle verification passed: 543 links, 1537 archive entries, fresh
  extracted launcher. Current browser smoke checks passed all three atlases.
  Windows-style checkout passed 986 byte-exact atlas assets after fixing
  `.gitattributes` to include nested corrected-climate JSON/CSV/binary files.
* Dependencies restored: scikit-learn added to requirements; installed the
  existing Playwright package's Chromium headless shell for browser checks.
* Accuracy figure and paired aggregate details:
  `output/r42_resume_20261102/{r42_accuracy.png,accuracy.json}`.

---

# Handoff — Earth corrections, physics gaps and r40 (30 October 2026)

Branch `claude/ecstatic-wozniak-rtrwd2`. Previous handoff (regional rainfall
benchmark, terrain research cores, detached jobs of an earlier container that
no longer exist): `reports/handoffs/BEFORE_EARTH_CORRECTION_20261030.md`.

## State

* Adopted Earth physics is now **r40** (`calibration/local_accuracy_20261023/r40_params.json`), also in the Earth-fit atlas:
  r39 plus e55/e55b monsoon westerlies, e56 shelf rule, e58 sea column under
  cold air, and refitted itcz_shift / precip_tau_days / monsoon_descent.
  Gate S 0.9932, 28 km 0.9953, sealed six 0.9671 (used once for r40).
  Evidence: `output/physics_gaps_20261030/refit3/`, report §12.
  The Earth-fit atlas publishes r40 on the r38 world geometry (see Next 1).
  New switches in `rotclimate/model.py` (e54-e61) all default off;
  r39 and r40 cells reproduce bit for bit.
* The Earth corrections below were trained on **r39**; r40 versions are in
  `calibration/earth_correction_r40_20261031/{temperature,rain_pattern}`
  (`scripts/retrain_earth_corrections.sh`; held out T 1.807 -> 1.548 C,
  rain 0.4329 -> 0.4201; 14 km T 1.283, rain 0.4424). Use the pair that
  matches the physics (they check its hash).
* Fresh-container setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt scikit-learn`;
  WorldClim 2.1 5′ `tavg prec elev vapr` zips into `data/cache/worldclim/`
  (geodata.ucdavis.edu); `python -I scripts/prepare_woa18.py --download`.
  The r39 dev31 run then reproduces every archived cell hash.
* New: `rotclimate/correction.py` (numpy-only application),
  `scripts/train_earth_correction.py`, `scripts/evaluate_earth_correction.py`,
  `scripts/plot_earth_correction.py`, `tests/test_earth_correction.py`.
  Rain pattern: `scripts/collect_earth_fields.py` (full-grid monthly winds),
  `scripts/train_rain_pattern.py`, `scripts/evaluate_rain_pattern.py`.
  Model files: `calibration/earth_correction_20261030/` and
  `calibration/earth_rain_pattern_20261030/` (final model, 12 held-out fold
  models, evaluation, protocol hashes each). Evidence and figures:
  `output/earth_correction_20261030/`. Report: `reports/EARTH_CORRECTION_20261030.md`.

## Measured (held out by geographic cluster)

Monthly land T MAE 1.793 → 1.540 °C over 31 regions, every policy group
better; 28 km pairs 1.896 → 1.274; 14 km pairs (atlas scale) 1.908 → 1.288; sealed Norway/SE Africa 2.621 → 2.143.
Worse: six regions (South Brazil +0.22 °C worst), seasonal range MAE +6 %,
coldest month +1 %. Köppen agreement ~unchanged (rain dominates classes).
Rain *amount* corrections were **rejected** (cluster holdout made unseen
continents worse). A **local rain pattern** (wind over terrain, 300 km local
mean removed) passes: loss 0.4424 → 0.4281, every group better, 4 regions
slightly worse (western Europe +0.027); 28 km −1.8 %, 14 km −1.5 %, sealed
−2.4 %. Köppen exact 47.1 → 48.6 % with both stages; main group dips on fine
grids (California, New Zealand). A domain-mean version made broad shifts on
the larger map and was replaced. Air-coupled SST seasonality (e53) and coupling retunes
were tested and **rejected** (S 0.999–1.023), code reverted.

Full test suite: 1605 pass; 7 fail identically on the pre-session commit
7e0b146 (harvest `settlement_cored`, Mediterranean spin-up `column_projector`,
zonefit missing `calibration/r19p_earthlike/best_params.json`).

## Physics gaps (reports/PHYSICS_GAPS_20261030.md)

* New reference: `scripts/prepare_ncep_reference.py --download` (NCEP/NCAR R1
  1991-2020 monthly surface winds, SLP, RH, precipitable water via PSL
  OPeNDAP; the plain download URL is refused, OPeNDAP text works but rate-limits).
* New diagnostic switch `wind_source="observed"` (grid.obs_wind) and
  `scripts/attribute_observed_forcing.py`: observed winds give North India
  933 mm (r39 256, obs 761); observed winds+SST fix the maritime lag; Mexico,
  Texas, Iran flood (rain settings fitted to wrong winds).
* Circulation is the largest gap (single zonal ITCZ, no monsoon westerlies,
  land winds 1.8x too strong, winter trades 2-6x); SST 1-3 C too cold
  (global offset -4.4 C), mid-latitude SST range too large; Tibet too wet.
* New opt-in `dry_heating` / `dry_heating_chi0` (e54): best 3.0 / 0.6 gives
  S 0.9933 but former-holdout 1.038 and mid-latitude 1.027 groups worsen
  (Chile, East Asia downwind of the Gobi); not adopted. All new switches
  default off; r39 cells reproduce bit for bit.
* New opt-in `monsoon_westerly` (e55; plus `itcz_shift_ocean`, which failed):
  cross-equatorial trades turn westerly toward the ITCZ with inflow at the
  boundary-layer angle. w 0.7: North India 256 -> 482 mm, Arabian Sea July
  wind 6.4/3.4 (NCEP 6.9/5.1), but East Australia, East China, Iran wetter;
  training group S 1.045.
* e55b `monsoon_pressure_hpa`: turn only where the model's own pressure falls
  poleward (Arabian Sea yes, Coral Sea/Caribbean no). Frozen refit
  calibration/monsoon_refit_20261030 (48 evals) best: w 0.934, G 2.95,
  dry_heating 0.09, precip_tau 10.93, monsoon_descent 0.0211 -> gate S 0.9938,
  rain -1.5 %, 28 km S 0.9984, but training 1.0055 and mid-latitude 1.0005
  fail; not adopted, sealed six unused. Validation:
  output/physics_gaps_20261030/refit/ (scripts/validate_monsoon_refit.sh).
* e56 `shelf_warm_currents`: the warm subtropical current is scaled by
  1 - s*(1 - deep-sea share), so the Kuroshio stays off the East China Sea
  shelf (East China coastal SST bias +2.6 -> +0.6 C at s 1). Second frozen
  refit calibration/monsoon_refit2_20261030 (shelf + itcz_shift): best w 0.935,
  G 3.29, s 0.62, itcz 14.43, precip_tau 10.08, descent 0.0190 -> gate S
  0.9949, rain -1.7 %, 28 km S 0.9962, training 1.0005 fails (California,
  Iberia); not adopted, sealed six unused. output/physics_gaps_20261030/refit2/.
* e57 `zonal_land_friction` (belts slowed over land, 300 km): US Midwest,
  western Europe, Great Basin better, Central Asia/Anatolia/Levant lose
  westerly water; net harmful. The one model wind is both surface wind and
  ~850 hPa transport wind.
* scripts/compare_column_water.py: winter column water 1.3-1.85x NCEP pw in
  14 regions, winter rain error follows it (r 0.67 log); summer rain 0.5-0.8x
  with columns ~right (r 0.08): summer needs rain-making physics.
* e58 `ocean_column_air`: sea column saturates at the column temperature
  where that is colder than the SST. Korea winter 292 -> 155 mm (94 obs),
  training group 0.988, but Japan/S Brazil/British Isles lose annual rain.
* Third frozen refit calibration/monsoon_refit3_20261030 (+ e58, wider
  precip_tau): 56 evals, one candidate clears every group and is the lowest
  cost -> validated (gate 0.9932, 28 km 0.9953, sealed six 0.9671) -> r40.

## Rules to keep

* The correction is valid only for r39 physics (hash in its metadata);
  refit after any physics change. Keep raw output alongside corrected.
* Score honestly with whole clusters held out: neighbouring regions overlap.
* Do not tune on the sealed regions (norway, southeast_africa); they have now
  been used once for this milestone.

## Next

0. Physics: summer rain-making. reports/SUMMER_RAIN_20261030.md: humid
   summers lack 10-22 % column water (from the sea), x3 through the RH gate;
   e59 (warm air over cooler sea, gated by subsidence), a frozen refit with
   ocean_rh/e58/tau (best S 1.0008) and slower sea uptake all fail against
   r40. Next: season-aware rain-making (mid-latitude summer convection is
   ~absent: instability from 22 C, closure ~0.1 mm/day) and winter overflow
   of supersaturated columns. eddy_rh_cap (e38b) + land_recycling refit
   (calibration/eddy_cap_refit_20261030) passed gate 0.9946 and 28 km 0.9981
   but sealed six 1.0135 (NE US rain +27 %): NOT adopted (judgment; policy
   lists sealed as a record). e60 eddy_cap_contrast_k (cap only for cold-air
   outbreaks) refit: gate 0.9942, 28 km 0.9972, sealed six 1.0406 (NE US
   winter 44 -> 12 mm vs 77): not adopted; the cap deletes real warm-frontal
   precipitation. The sealed six have been run for 3 candidates: declare a
   fresh sealed set before the next adoption. Next physics: direction-aware
   eddy moisture transport (eddies weakened against strong offshore mean
   flow: winter monsoon coasts). e61 eddy_upwind_days built and screened:
   fixes East Asian winters but floods west-coast winters (r40's over-land
   westerlies 2-5x too strong); needs a separate transport wind (~850 hPa)
   beside the surface wind. cold_high_storms 0.25-0.40: small clean gain
   (S 0.998), refit candidate. Then North India's pre-monsoon cold. Gate any change against r40 (REF_NAME=r40 REF_FIT=...
   in scripts/validate_monsoon_refit.sh).
   31 Oct (reports/TRANSPORT_WIND_20261031.md): the transport/surface wind split
   (e62 heat_land_friction / water_land_friction) does not help alone; the
   interiors lack a warm winter sea (scripts/compare_sea_surface.py: r40's
   Mediterranean ~6 C too cold in January, west-coast seas' ranges ~2x WOA18).
   North India's plain sits on the latitude's mean land column (2-3 C too
   cold). Dry heating gated to warm ground (e54c dry_heating_warm_c) + small
   frictions: refit calibration/dry_heat_refit_20261031 passed dev31 (S 0.9879,
   North India T 3.40 -> 2.99) and 28 km (0.9893) but the FRESH sealed six got
   worse (1.0405: Kazakh steppe, Hokkaido ranges grow): not adopted. The fresh
   sealed set has now been seen once (declaration.json seen_by); a dry-heating
   design that spares cold steppes should come with another fresh set.
   e63 inland_sea_lag_days (lagged enclosed seas) alone just shifts East Asia's
   sea error from spring to autumn.
1. World refit for the invented map on r40 (calibration/map_world_r40,
   scripts/world_campaign_r40.py): NOT published. Coarse best 0.1922 vs
   0.1895 but every better candidate breaks a zone/Mediterranean guard; the
   start fails every native protection (zonefit 0.1796 vs 0.1828, strict
   33.1 vs 35.0 %, Med dry 9.0 vs 6.4 %). Audit layouts 590xxx unused.
   reports/R40_WORLD_20261031.md.
   RULE (user, 31 Oct): a release better on the Earth test updates the atlas.
   So atlases/earth_fit is now r40 physics + r38 geometry (reports/ATLAS_R40_20261031.md;
   r38 backup in output/atlas_r40/previous_atlases/). Hosted artifacts (hub,
   free, earth, whittaker; URLs in atlases/artifact_links.json) republished
   with all local features (FORGE etc.): scripts/package_atlas_artifact.py ->
   Artifact publish per atlas; check with scripts/check_atlas_smoke.js.
   Earth-fit atlas has a Corrected topic (scripts/add_corrected_layers.py,
   r40 corrections on the atlas checkpoint; zone agreement 33.1 -> 35.6 %;
   rerun it after any rebuild of atlases/earth_fit, refuses other physics).
2. Fresh sealed set declared 2026-10-31: calibration/sealed_20261031/
   (hokkaido, canadian_prairies, kazakh_steppe, namibia_kalahari,
   southern_italy, north_queensland; no model run on them yet). Use
   SEALED_SPEC=calibration/sealed_20261031/regions.json with
   scripts/validate_monsoon_refit.sh; the old sealed six are development data.
2. Physics for the maritime lag: the land air is ~95 % sea-controlled because
   the land equilibrium is the latitude's continental column (2.3 °C mean over
   Britain). Needs a land surface layer / two-tile coast and recalibration.
   31 Oct (reports/SEASON_PHASE_20261031.md): much of the late spring is the
   band column's temperature-driven snow albedo (53 N: April 4.3 C colder
   than October, real interiors ~0). e65 ebm_land_ice keeps a share of it
   (ice sheets keep all); 0.5 + continental_mean 7 screens S 0.9837 (holdout
   1.0049). Frozen refit calibration/land_ice_refit_20261031 (validate with
   sealed set b). e64/e64b shelf seas following the air: harmful, off.
3. Small: two-scale relief lapse (+~0.8 % T alone).

## Food, foraging and political reach side project (31 Oct)

* Earth-fit atlas opens on the Earth-corrected climate (user, 31 Oct: no
  separate "Corrected" topic): scripts/add_corrected_climate.py renders a full
  corrected copy (climate layers, station packet, farming, population,
  FORGE, political reach) with the normal exporters into data/corrected/;
  one Climate switch (#climate=raw) shows the raw simulation; the change maps
  sit under Fit checks. Supersedes add_corrected_layers.py (topic) and
  add_corrected_food.py. Rerun it after any rebuild of atlases/earth_fit,
  any change to an exporter, or export_reach.py (it needs winds12.npz).
* FORGE's first Earth test (reports/FORAGING_EARTH_20261031.md; frozen plan
  and aquatic addendum in calibration/forager_binford_20261031/): Binford's
  hunter-gatherers with observed climate, North America fits, the rest of
  the world tests. Adopted: terrestrial food x0.5 + coastal/freshwater fish
  (test error x3.0 -> x1.8, fish-share rank 0.78); all atlases rebuilt with a
  Fish share map. Not adopted: long-window median/mean summaries (missed the
  0.02 allowance), food storage (worsens the fit). Weak spot: California /
  Northwest Coast ~3x too sparse; marine scale at its grid edge.
  Data: data/cache/binford_dl (CRAN binford 0.1.0), data/cache/naturalearth.
* Political reach (reports/POLITY_SEASONS_20261031.md): autumn mud ADOPTED
  by a second frozen addendum (addendum_mud_pet_20261031: topsoil layer gives
  both rasputitsa seasons at 6 unseen stations, no mud at 10 dry controls;
  polity.seasons.TOPSOIL_MM = 25; all three atlases' reach rebuilt).
  Droogers-Allen PET changes nothing. Monsoon-coast closure not adopted.
  State strength (reports/POLITY_STRENGTH_20261031.md): second design with
  independent city networks (Parthian capitals; excavated Xiongnu centres)
  is informative and chooses gamma 0: no strength term. Western Med sailing
  diagnosed (scripts/polity_sea_west.py): the west is slow (light NCEP winds,
  'uncertain' storminess in July), long upwind passages ~3x fast (no waiting
  for fair winds). A waiting rule needs ORBIS (test T7) to be tested blind;
  ORBIS is not in the container (o_sites.csv, new_routes.topojson under
  data/cache/orbis). Earth polity data rebuilt by scripts/prepare_polity_data.py
  (data/cache, not committed).

## 1 November 2026 round (reports/SEASON_PHASE_20261031.md sections 5-7)

* East Asia's spring warmth (3-4 C, the refits' blocker) is NOT the sea, the
  surface winds (observed WOA18 + NCEP swapped in: unchanged), the lapse rate
  or cloud shading alone. The storm band is planet-wide (45 N in April) while
  East Asia's jet and fronts stay at 30-35 N; and wet_cooling acts only above
  the annual mean, flattening summers so springs/autumns end too warm.
* New opt-in levers (all off, bit-identical): e66 warm_current_seasonality
  (fixes British seas, worsens land: compensating error), e67
  continental_sea_air (fixes Korea's seas, not the land), e68 storm_baroclinic
  (+ _cold_c, _max_deg; storm band on the model's baroclinic zone), e69
  wet_sun (+ _ref; sunshine-driven wet cooling; with wet_cooling 0 East China
  2.00 -> 1.30 C), world lever ebm_land_scale (planet land by latitude).
* Frozen refit calibration/spring_refit_20261101 (e65 + e68 + e69 + continental
  terms) running; validate with sealed set b (still unseen) -> r41 if it passes.
* Political reach: dry-land towns need water within 40 km on Earth (22.9 km on
  drawn maps, scaled to Natural Earth river density); ORBIS cached
  (data/cache/orbis); sailing constants not adopted (ORBIS blind test).
* FORGE aquatic addendum 2 not adopted (marine scale grid-edge is the NW Coast).
* Off-map land: scripts/offmap_earth_test.py measures the skill an invented
  surrounding costs on Earth (British Isles 0.77 C RMS, mostly systematic, not
  layout noise); full run pending.
* Data fetched for these tests (user-approved, data/cache, not committed):
  HydroRIVERS v1.0 NA/AS/AR tiles (hydrorivers), CLIWOC 2.1 logbooks
  (cliwoc), ORBIS v2 sites + routes (orbis).
* FORGE salmon (reports/FORAGING_EARTH_20261031.md): eight frozen attempts
  with HydroRIVERS; best = attempt 7 (sea-ice factor on the marine supply +
  a_salmon 300, upstream thinning L 800 km, outlets 2-15 C): leave-one-area-out
  CV 0.442 -> 0.372, NW Coast 0.577 -> 0.302, Arctic 0.65 -> 0.52, world
  unchanged; the Subarctic fold always worsens (post-epidemic densities?), so
  not adopted by the rule. A user decision could carry attempt 7 to the maps.
* Sailing: CLIWOC confirms the polar (close-hauled 0.82 vs model 0.85; Casson's
  0.45 rejected). Waiting rule halves ORBIS's error (0.522 -> 0.306) but adds
  Casson scatter (Etesian short passages; western Earth-only storminess); next
  design recorded in reports/POLITY_SEASONS_20261031.md.

## 1 November 2026, after r41 (in flight)

* r41 adopted (reports/R41_20261101.md); release pipeline
  output/atlas_r41/release.sh rebuilds the Earth-fit atlas, retrains the
  corrections and re-exports the corrected climate. Sailing waiting rule
  adopted (SAILING_RULE "wait"), reach of free/whittaker fits rebuilt with it.
* Sealed set b is spent; sealed set c declared
  (calibration/sealed_20261101c: Nova Scotia, middle Volga, Tripolitania,
  northern BC coast, Tibet, Ethiopian highlands; never run).
* W2 frozen (calibration/map_world_r41_planet/plan.json,
  scripts/world_campaign_r41.py): world refit with tilt, eccentricity,
  perihelion, starlight, greenhouse and land-by-latitude free, 300 km
  continuation fixed, guarded search inside the coarse screen. Needs the
  'world_screen' guard form in rotclimate/calibrate.guard_penalty (patch kept
  in the session scratchpad; apply after the r41 release finishes, since the
  release hashes rotclimate sources).
* P3 frozen (calibration/maritime_refit_20261101/plan.json): sea swing (e66,
  e67, e64) + land coupling + wet_sun_ref (r41 warms dry ground); needs a
  plain r41 run of retired sealed set a as its extra reference first.
* FORGE attempt 10 frozen (addendum_forest10): game x (1 - c x closed-forest
  share) for the eastern Subarctic's over-prediction, CV with salmon + ice.
* Results since (1 Nov, later): r41 atlas released and republished (corrected
  climate default, change maps under Fit checks, r41-trained corrections:
  T −11 %, rain −3 % held out). W2 world refit with planet levers: no world
  qualifies (reports/WORLD_PLANET_R41_20261101.md); the best finalist gains
  strict agreement 32.6 → 37.3 % and the Mediterranean but loses the painted
  desert (hot-dry recall 0.246 → 0.176); the nine audit layouts are still
  unseen. FORGE attempt 10 (closed-forest game) not adopted: only the
  Subarctic wants it. P3 maritime refit search running; its validation (sealed
  set c) is queued in output/maritime_refit_20261101/after_search.sh.
* P4 desert refit (reports/DESERT_HEAT_20261101.md): new opt-in e70, e54e,
  e71 (+b/c/d). Candidate 39 passed dev31 (S 0.9826, every group) and 28 km
  (0.9964) but failed sealed set c (S 1.0159: Tibet warmed, Volga/BC coast
  cooled by the land-offset compensation). Not adopted; r41 stays. Sealed
  set c is spent; set d declared (calibration/sealed_20261101d: Egypt,
  Thailand, Finland, central Siberia, Yucatan, Kenya; never run). Next: e71
  without summer-ascent areas (plateaus, monsoon) and without a global offset.
* F11: Mooney (1928) early-contact estimates do not support the epoch
  explanation for the eastern Subarctic (ratio ~1.0 east, 1.3-1.8 west);
  the Shield over-prediction is a model error (soil/wetland, next).
* Desert refits #2 and #3 (P4b/P5): #2 not adopted (sealed d not run);
  #3 (calibration/desert_refit3_20261101, core drying e70b/c + gated e71 with
  rain/top/chi0 gates) search in flight, output/desert_heat_20261101/
  search3.log; validate the best on sealed set d by hand if it beats r41.
* FORGE F14 lifeways (hunters / gatherers / fishers + camp moves) adopted and
  live in the atlases (data/forager_lifeways.json). F15 contact-basin culture
  areas not adopted (ARI vs Murdock areas).
* Language areas from below (reports/LANGUAGE_AREAS_20261101.md; plans in
  calibration/language_areas_20261101/): the owner wants languages grown from
  the land and compared with the polities only at the end.
  - Layer 1 (Gavin group splitting on FORGE density), 1b and 1c: counts within
    x1.5-1.8, richness R2 0.17-0.28; not adopted. Owner to decide on
    illustrative use.
  - Layer 2 (Pinhasi 2005 Neolithic dates): plain distance beats terrain/sea
    and crop-slowed waves held out (950 vs 987/1121 y); 1.0 km/yr, r 0.83.
    Farming spreads by distance; crop rules decide only where it roots.
  - Layer 2b (Diamond's nine homelands): neither FORGE nor productivity
    places hearths (AUC 0.75-0.78 < 0.80). Hearths are the owner's choice.
  - Layer 2c (Nichols / Michalopoulos): ADOPTED. Terrain + land-quality
    variation predict language density on held-out macroareas (R2 0.34 vs
    0.28 climate only, 5/6 macroareas). Fantasy-map preview
    (scripts/language_map_preview.py): ~130 languages, Xšāça ~48; polity
    borders barely follow likely language edges (0.23 vs 0.19).
  - Layer 2d (hearths from the map alone): Earth base rate x productivity
    gives 0.42 expected independent hearths on the map (66 % chance farming
    came from beyond); land beyond (SW 72 %, SE 45 %) and homeland
    latitudes point south; on-map best guess the west coast.
    Model's surroundings picture (layout 1) shows big seas; land link only to
    the NW (cold) -> P(on-map hearth | farming present)
    = 0.34/(0.34+0.66 q), ~70-90 % unless a narrow crossing/land link exists.
  - The preview is in all three atlases (and hosted) as the 'Languages'
    topic: scripts/add_language_layers.py (density, one draw of territories,
    likely boundaries vs de jure borders), labelled illustrative.
* FORGE F13 (food store scored on Binford's storage): not adopted (held-out
  rho 0.00); Binford's ET 15.25 threshold gives rho 0.72 (his own rule).
* Polity A1 (steppe reach from herding land, no polygons): Xiongnu 0.950
  (centres alone 0.728), Tang-Turgesh 0.900 vs bar 0.904; not adopted. Next:
  Tang protectorate garrisons as sources.
* P7 (reports/AUTUMN_PHASE_20261101.md): subtropical land peaks 4-9 days
  early; the marine air does not follow the sea (eddy mixing 1.43/day vs
  air-sea 0.37/day). Fast coupling (e51+e3 0.5 d) helps the Mediterranean
  and British coasts, hurts East Asia (+0.4-1.2 C MAE); blocked by P6.
* P6 evidence (r41): East Asia spring rain 0.5-0.7 of observed, winter rain
  2-3x (Japan, Korea, North China Plain); warm bias peaks Mar-May.

## 1 November 2026, evening: policy v3 and r42

* The owner set aside "no group may get worse": adoption now follows overall
  accuracy (calibration/local_accuracy_20261023/policy_v3.json): S over the 49
  development regions (dev31 + retired sealed a, b, c) improves >= 0.5 %, T and
  P within +1 %, paired 28 km within 1 %, the next unseen sealed set not worse.
  Groups are reported only. scripts/gate_v3.py + scripts/validate_v3.sh.
* r42 = desert refit #3 candidate 1 (e71 compression warming + e70b/c branch
  drying): S49 0.9626, 28 km 0.990, sealed set d 0.941 (rain -11 %). Holdout
  1.039 and mid-latitude 1.022 as groups (Manchuria, NZ, southern coasts).
  reports/R42_20261101.md; release output/atlas_r42/release.sh.
* Sealed set d is spent; declare sealed set e before the next search.
* Future searches: score on S49 (no group penalty) to match policy v3.
