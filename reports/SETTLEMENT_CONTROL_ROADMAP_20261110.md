# Settlement and de facto control development roadmap

Owner approved 10 November 2026. This is the durable queue for the whole programme,
not just its first experiment. Read this alongside the current entry in HANDOFF.md
at every continuation. Physics development has its own queue; neither queue
silently replaces the other.

## Working rules

* Every milestone records code, Earth data exposure, results, limitations, adoption
  decision, atlas consequences, and the next unfinished task. Commit and push
  milestones to the single maintained/default branch, `claude/friendly-turing-43ygeu`
  (owner consolidation request,11 November2026). A failed experiment does not complete
  its parent stage or cancel later stages.
* Follow the dependency chain: environment → occupancy and land use → settlements
  → shared people/food allocation → institutions and transport → differentiated
  control. New utility layers must have an explicit consumer in this chain.
* Include all actors, unaffiliated communities and mobile populations. Missing
  markers are missing evidence, not proof of empty or ungoverned land.
* Keep recorded sites, game-era administrative scenarios and generated hypotheses
  distinguishable. A generated town is not independent evidence for its owner.
* Keep one population, land and seasonal food ledger. Do not add overlapping
  farming, pastoral or foraging capacities or invent institutional staff.
* Separate development, spent evaluation and genuinely prospective tests. Han,
  Rome, Hellenistic sites, Sui 610, Tang 742, the inspected medieval city pools and
  Domesday are already exposed. New dates sharing sites are not independent by
  default. Never rerun an old test and call it blind.
* Publish qualified changes through the normal Windows launcher atlas; preserve
  previous defaults when evidence is insufficient. Expose experimental results
  as research, with their status, rather than silently replacing the main map.

## Next settlement-map release: four milestones

This is the near-term release path. The longer S1–S5 programme below remains
tracked; detailed institutional roles and differentiated control are subsequent
releases, rather than reasons to keep postponing a settlement-location/population
update. None of these milestones is complete merely because code tests pass.

1. **Freeze usable Earth references and comparison rules [COMPLETE for this release].** Finish
   the declared date-scope preparation for settlement hierarchy/largest-settlement
   evidence, retain uncertainty and role/source limits, and secure a defensible
   located transfer pool. Seshat's polity attributes do not supply settlement
   coordinates. Previously exposed Roman/Han pools remain development data.
   Completed the dated Seshat support comparison and prepared the separate primary
   Vidarbha field survey. Frozen transfer rules committed in d0c65f94 before new
   model scores; source now spent after its first parameter-transfer comparison.
2. **Fit and test counts, placement and population sizes [IN PROGRESS].** Keep count
   budgets separate from placement, compare the existing Pareto alternatives,
   inspect geographic/local errors and run a frozen geographic transfer test.
   Select on declared aggregate tradeoffs with physical/accounting constraints;
   do not require every region to improve. Failure means another fit iteration,
   not calling an unqualified map calibrated.
   First Vidarbha test: 53 primary cell–frame units; all 24 placement constraints
   pass, but adaptive L450 loses 10.42 percentage points of 10 km capture against
   the fixed L800 control, beyond the declared 10 point margin. No adoption.
   See SETTLEMENT_VIDARBHA_TRANSFER_20261111.md. Next: audit count/role and resident
   size evidence on existing Earth pools; do not relabel another tuning run on
   this survey as a fresh geographic holdout.
   Count/size audit now completed on exposed pools (SETTLEMENT_COUNTS_20261111.md):
   the frozen Han inputs silently zero-filled 1,586 land cells beyond the global
   population raster, including 13 source cells. Full-region count fits unqualified;
   a declared supported-domain sensitivity improves count deviance only 1.86%
   with beta0.5 versus0.7, with large spatial errors. CountyPOP is not seat residents;
   Roman positive areas and median fills remain separate. NEXT extend missing
   ecological inputs consistently, verify overlapping existing values, then rerun
   full-region count development and continue shared-ledger resident allocation.
3. **Rebuild fantasy settlements on the shared ledger [PENDING].** Preserve
   marked anchors, distinguish occupancy from carrying capacity, allocate
   residents/food once and rebuild affected tracks and downstream inputs.
   Unsupported institutional roles/staff remain uncertain; the legacy fixed
   cohort at every eligible town is not an empirical staffing calibration.
4. **Publish and check the normal atlas [PENDING].** Regenerate the Earth atlas
   served by start_atlases.bat, verify identities/links/browser/mobile/Windows
   behaviour, show before/after maps and calibration limits, then commit/push
   the single maintained branch.

These are four release milestones, not four guaranteed commits or a promise
that one calibration run will pass. S1c/d/e qualification and the shared ledger
still apply. Keep S2–S5 and all actors/unaffiliated/mobile/nonstate communities
on the durable queue after this first release.

## Successive stages

### S1 — Count-separated, clustered settlement placement [IN PROGRESS]

- [x] S1a: Preserve the current Earth-tested count as a separate budget; implement
  candidate placement with explicit eligibility, marked anchors, reproducible
  seeds and reported shortfalls. Count must not change with the history prior.
- [x] S1b: Compare clustering and locations on declared development Earth pools;
  isolate count separation, spacing and history-prior effects. Report seed spread,
  counts, 25 km matching, 100 km block rank and nearest-neighbour spacing.
- [ ] S1c: Resolve historical occupancy assumptions. Do not equate food capacity
  with actual population or use Rome as a timeless medieval urban attractor.
- [x] S1c initial mechanism study: distinguish centre intensity from people,
  test adaptive local spacing and450/800/1500km history scenarios on exposed
  Earth pools, retain exact-location/spacing alternatives and review all counts.
- [x] S1c grid-boundary robustness: [100 shorter-scale evaluations](SETTLEMENT_HISTORY_BOUNDARY_20261111.md),
  protocol710af13a,20 exact overlap controls; old450km lead retained inside the
  expanded range. No accuracy gain or global-optimum proof.
- [ ] S1c remaining: historical occupation-age/role evidence; spatial-prior scenarios
  do not establish actual past occupancy. Preserve this gap through population/control work.
- [ ] S1d: Freeze a finalist and identify a defensible prospective transfer pool
  before evaluating it. Record coverage, site roles, shared geography and dates.
- [ ] S1e: If qualified, rebuild settlements, tracks, food-supported institutions
  and control together; show actual before/after atlas maps. Otherwise record
  rejection and the next S1 experiment. Parent S1 remains unfinished.

Done means: count and placement are genuinely independent, clustering improves
without an unacceptable aggregate location loss, transfer has been assessed, and
the downstream consumer chain has been reviewed. A passing unit test is not an
Earth qualification.

### S2 — Rural settlements, market hierarchy and institutional roles [PREPARATION IN PROGRESS]

- [x] Initial source preparation: frozen066db539 before observations;3652 joined
  rural-Britain records, role multiplicity and date/size fields audited without
  predictions or scores. [Report](ROMAN_RURAL_PREPARATION_20261110.md) and
  [consumer contract](SETTLEMENT_ROLE_CONTRACT_20261110.md).
- [x] Compile role-context observations and exact-association validation blocks;
  resolve missing lookup labels from the official search and document date censoring.
  [Role compiler](ROMAN_RURAL_ROLES_20261110.md): no scores, allocations or adoption.
- [x] Test coordinate interpretations against six declared sites/eight official
  references: [OSGB-compatible X=easting/Y=northing supported](ROMAN_RURAL_COORDINATES_20261110.md),
  not whole-source precision or model accuracy.
- [x] Document general phase-date purpose from authors2016 methodology and audit
  internal date integrity: [1031 consistent/10 requiring review](SETTLEMENT_PHASE_EVIDENCE_20261111.md).
  Roles may be successive; exact-point/name review blocks retain189 observations
  without physical merges or assigned function intervals.
- [ ] Resolve actual physical-place scope, CSV positional precision and specific phase
  semantics; retain the operational coordinate interpretation with explicit
  uncertainty, not official export-CRS certification. Association blocks are not
  site merges, and site dates are not role dates.
  Record IDs/investigated area are not settlement counts/population. Keep source
  overlap, coverage and spatial leakage explicit before role-specific scoring.

- [x] Initial conditional context diagnostic: [weak existing predictors](SETTLEMENT_ROLE_CONTRAST_20261111.md),
  no fitting/adoption; source exposure updated, all mixed cells and scenarios retained.
- [ ] Explicit functional/service-demand and observation model, including a declared
  non-roadside robustness contrast before road-derived predictors; no intensity-to-role shortcut.
- [ ] Separate villages, markets, ports, administrative seats and garrisons;
  roles may overlap. Preserve known anchors; do not classify from icon size alone.
- [ ] Allocate resident populations and service catchments from the same rural
  population and food ledger. Fit sizes/roles using appropriate Earth evidence.
- [ ] Model settlement interactions and demand for routes, checking that demand
  does not create cost-free transport or double-count generated infrastructure.
- [ ] Validate counts, clustering, rank/size and role-specific performance;
  distinguish administrative-seat datasets from village surveys and urban lists.
- [ ] Rebuild available administrative/military sources and atlas outputs.

Literature starting point: Bevan & Wilson (2013), doi:10.1016/j.jas.2012.12.025.
Done means: role-specific settlements feed the actual authority model, not merely
another descriptive overlay.

### S3 — Local administration, central connection and military reach [PENDING]

- [ ] Connect existing administrative-link diagnostics to local institutional
  persistence and central coordination; include non-imperial actor structures.
- [ ] Distinguish local administration, fiscal collection, military access and
  nominal claims. Losing a capital link must not erase local institutions.
- [ ] Retain identifiable enclosure assumptions and unknown/unscored areas.
- [ ] Validate each relationship against relevant Earth evidence, reporting the
  limits of historical extent polygons as proxies for local obedience.
- [ ] Integrate differentiated control into the main atlas without selector clutter.

Literature starting point: Smith (2005), doi:10.1111/j.1467-8306.2005.00489.x.

### S4 — Collectible surplus and sustained institutions [PENDING]

- [ ] Audit existing production → household needs → storage → collection → freight
  → civilian/staff allocation as one seasonal ledger; reuse current machinery.
- [ ] Constrain staff, collection and transport by resources, capacity and explicit
  access/permission scenarios. Fed residents do not automatically become soldiers.
- [ ] Feed viable institutions into local administration and central coordination;
  roads improve travel but are not independent authority sources.
- [ ] Test seasonal failures, shortages and source-inventory sensitivity on Earth;
  distinguish annual effective access from reliable seasonal presence.
- [ ] Publish the resulting settlement and control changes together.

Literature starting point: Mayshar, Moav & Pascali (2022), doi:10.1086/718372.
Appropriability motivates a hypothesis to test, not a cereal-to-state shortcut.

### S5 — Mobile and nonstate communities [PENDING]

- [ ] Connect existing grazing/foraging and seasonal-circuit experiments to actual
  occupancy, with water, feed, camp locations and non-overlapping resource use.
- [ ] Represent local communities, negotiated passage and overlapping seasonal
  rights without forcing permanent towns or a single tribal state everywhere.
- [ ] Feed mobile occupancy and institutions into settlements/control while
  distinguishing land use from exclusive political sovereignty.
- [ ] Validate mobility/resource use with suitable Earth analogues; expose missing
  evidence and avoid inferring social organisation from biome alone.
- [ ] Publish integrated results for imperial, other-state and nonstate areas.

## Cross-cutting work, required at every stage [ONGOING]

- [ ] Ensembles over site draws, historical occupancy and uncertain affiliations;
  report recurring centres/control and scenario sensitivity, not uncalibrated
  probabilities presented as confidence.
- [ ] Maintain data/source identities, Earth exposure register, population/food
  conservation checks and separate component versus end-to-end validation.
- [ ] Keep normal launcher atlases, explanatory text and exports consistent;
  post useful generated maps during development.

## Current resumption point

S1a/b's original72-evaluation fixed-count study remains unchanged. S1c now adds
the [108-evaluation adaptive intensity study](SETTLEMENT_INTENSITY_20261110.md):
all1202Han/1292Roman counts preserved; expected centre intensity explicitly is
not population/food or occupation age. No production adoption. The selected
adaptive0.35/450km variant has uniqueF1 .521Han/.402Rome, spacingKS .060/.055;
best fixed18km has higher uniqueF1 .591/.422 at worse spacingKS .472/.407.
Both remain on the Pareto frontier. New Q .621 vs best fixed .570 is a declared
development tradeoff, not percentage accuracy or prospective validation.

Actual history/occupation-age interpretation and role/resolution evidence remain
unfinished S1c work. The initial450km minimum is now bracketed by the declared150–650km sweep;
all100 evaluations preserve counts and20 overlap controls replay exactly. The old
lead is retained with no Q gain, not a universal historical scale or global optimum. Do not mistake unchanged population totals
or an intensity normalization for calibrated demographic occupancy.

S1d source audit: [Vidarbha](VIDARBHA_PREPARATION_20261110.md) is NOT ready as
supplied:60 coordinate rows,390 settlement rows/389 unique IDs,zero joins; axes
conflict with the readme. This is a frozen preparation-only source-quality result:
no model predictions, maps or scores. Resolve the source or obtain another
role/coverage-appropriate source before a located transfer test. Do not silently
swap axes or fuzzy-match IDs, and do not label the model failed/successful here.

The [data queue](SETTLEMENT_CONTROL_DATA_QUEUE_20261110.md) records this exposure
and now includes the completed initial Roman rural Britain preparation for S2.
Its3652 core/site IDs join,608 records have multiple major roles,2641 date spans
are AD200-compatible; these are not unique settlements or dated institutions.
The follow-up [role compiler](ROMAN_RURAL_ROLES_20261110.md) resolves all observed
source labels, retains11 overlapping context channels and documents628 left-censored
starts/1295 end-period conventions. Exact-association blocking connects153 records
in65 nontrivial components without physical merges or assigned folds. A follow-up
[six-site/eight-point coordinate audit](ROMAN_RURAL_COORDINATES_20261110.md) supports
operational OSGB-compatible X=easting/Y=northing in metres (all references within188m;
reversed axes minimum29km), despite conflicting thesis labels. Whole-source precision
and individual function intervals remain unresolved; the later source-methodology
audit documents the general purpose of phase fields as major settlement changes; no whole-source projection/target map. Resolve
place scope/function dates/precision and coverage before role-specific calibration.
The11 November audit retains1031 internally consistent change records and flags10
for review, without sorting/clipping or assigning roles. New point/name blocking
includes189 related observations, not physical-place merges. Do not force the
approximate published settlement total through automatic de-duplication. Source raw tables are cached only; aggregate diagnostics are public.
Phased crop/collection evidence for S4 remains metadata-only. Exposed Han/Rome/Sui/Tang/Hellenistic/
medieval/Domesday pools cannot be relabelled unseen. Additional development use
is allowed if declared. Next source acquisition should audit role/phase/coverage
and overlap before freezing any scoring protocol.
S2's rural-source schema/phase/role audit can proceed while S1d seeks a usable
transfer source; its initial record-level preparation is complete, while the
remaining interpretation and calibration are open. This is not closure of S1 or
a reason to abandon deferred coupled integration. Standard CSV-reader correction
removed a false unnamed-cell warning in Vidarbha; zero joins/axis conflict remain,
and all climate/settlement results are unchanged.

Then S1e rebuilds towns/tracks and the SAME resident/food/staffing/control chain
after qualification. S2–S5 remain required. No parent stage is complete or dropped.

## Milestone log

|Date|Milestone|Evidence/decision|Next|
|---|---|---|---|
|2026-11-10|Full programme persisted and pushed; commit67f68aad|Five stages, completion criteria, cross-cutting requirements|S1a/b|
|2026-11-10|Development protocol frozen; commit17c73556|Twelve variants, fixed counts, exposed data only, no adoption|Recover inputs and run|
|2026-11-10|S1a/b initial comparison complete|See settlement-locations report; no production adoption|S1c/d, then S1e; retain S2–S5|
|2026-11-10|Next Earth data candidates audited at metadata/schema level|Vidarbha, Roman rural Britain, Cambridge crop/collection evidence; no target tables/scores or sealed status|Occupancy/tradeoff work and preparation-only source audit|
|2026-11-10|S1c adaptive spacing/history study; protocols a9a4a635|108 exposed evaluations, all budgets/pair constraints pass; no adoption|History/role robustness and S1d transfer|
|2026-11-10|Vidarbha preparation completed, no predictions scored|Zero coordinate/settlement joins and conflicting axes; source not ready|Resolve or replace source; keep S1d and S2–S5 open|
|2026-11-10|S2 rural preparation frozen066db539 and completed|3652 joined observation records, multiple roles, date/size/schema audit; no predictions or scores|Resolve place/coordinate/phase/taxonomy and declare calibration|
|2026-11-10|CSV escaping reader corrected and both sources rechecked|Original source/audit preserved; Vidarbha primary findings unchanged, no model results changed|Keep lineage and regression cases; continue full programme|

|2026-11-10|S2 executable role-evidence compiler and association blocks|All observed labels mapped explicitly; source date conventions documented; no scores, allocations or production changes|Resolve place/MAP/phase/coverage gates, then declare role calibration; retain S1 and S3–S5|

|2026-11-10|Coordinate interpretations tested after role milestone9ad8a181|Six exposed named sites/eight official references support OSGB-compatible XY metres; all points retained, no offset fit or model score|Place identities, extra phases, positional uncertainty and coverage before calibration; preserve full roadmap|

|2026-11-11|Declared shorter history-scale experiment completed|100 exposed evaluations,20 exact overlap controls, no Q gain;450km now interior and300km alternative retained|Prioritize actual occupation/role evidence and appropriate transfer over more L tuning; keep S1e/S2–S5|
|2026-11-11|Source-methodology chronology and identity audit|Major changes documented;1031 internally consistent/10 review records;189 observations blocked, no physical merges or role intervals|Declare role-specific conditional/dated targets and grouped/spatial coverage before scoring|

## Next declared experiment: conditional role contrast

[Protocol](../calibration/settlement_role_contrast_20261111/plan.json),11 November:
compare recorded nucleated versus farm/villa contexts among domestic-observation
records, with cell/class weighting, no background absence and no AD200 role claim.
Source-only counts426/2049 are known; no source-to-grid matching or contrast scores
yet. Test existing predictors without tuning, report coverage/effort and positional
sensitivity, keep mixed-cell ties. This is the next S2 diagnostic, not closure of
S1, dated-role calibration or permission to turn categories into political sources.

## Conditional role contrast completed,11 November2026

The [declared diagnostic](SETTLEMENT_ROLE_CONTRAST_20261111.md) passes preparation
and is now scored: suitabilityAUC.548 versus history-intensity.519; all coordinate
scenarios retained, no fitting/adoption. Selected-archive contexts are not a
settlement census or datedAD200 functions. Source exposure is updated; do not
relabel this pool unscored or independent. Prior protocols/audits remain historical
checkpoints. Next, define an explicit role/service-demand and observation model,
with a non-roadside contrast before road-based predictors, grouped spatial/effort
checks, and the SAME downstream population/food/staff/control consumers.

## Finite service-demand mechanism tested,11 November2026

[Protocol192c7eb3 and results](SETTLEMENT_SERVICE_DEMAND_20261111.md): competing
reachable opportunities partition finite potential requests; no people/staff/food
created. Both directed land legs constrained.378AUCs,6requestledgers,27oldrefs and
18full-window checks pass. Strict global gains≈.65 weaken locally≈.55–.56; no
predictor/default or world role/control adoption. This completes the initial
service-allocation primitive/test, not S2's qualified role model or S1c/d/e.

Next predeclare availability-mass and zero-travel/inverse-mass controls before
attributing improvements to interaction. Keep source observation/timing and
transfer gaps explicit. S3–S5 remain required and actual consumers must share the
same resident/food/staff/institution/control ledger across all actors.

## Opportunity controls completed,11 November2026

[Protocol720fcaa2 and results](SETTLEMENT_SERVICE_CONTROLS_20261111.md) keep all
three mass assumptions, six travel cases, nine coordinate cases and both source
cohorts. Strict global one-day history interaction.6453 is almost reproduced by
inverse opportunities alone.6462; local interaction.5059 remains below existing
suitability.5748. No fitting, winner selection or production role/control adoption.
1188AUCs,378exact old diagnostics,18old fields,18requestledgers,9nulls and54full-
window comparisons pass. This closes the declared ablation, not S2 or S1c/d/e.

Next declare source-role composition before new subclass scores: distinguish
recorded village, vicus and small-town contexts without assigning military,
market or dated functions automatically. Keep observation selection, timing,
spatial/effort and transfer gaps. S3–S5 and the shared downstream ledger remain
required; all actors, unaffiliated and mobile/nonstate groups stay in scope.

## Source-role composition completed,11 November2026

[Protocol5e650062 and results](SETTLEMENT_ROLE_COMPOSITION_20261111.md) distinguish
five source-label groups in both old cohorts;five cases pass the fixed30unit gate,
five stay explicitly unscored.2970globalAUCs,6270stratumAUCs and330blockmeans checked
independently. Village/vicus one-day history serviceglobal.3930/.8822,local.4748/
.5557;strict differences persist. No fitted/selected predictor or world adoption.
Smith2016chapter2p38 explicitly distinguishes civilianfort-origin vici and differing
possible functions. Labels do not date actual staffed institutions or authority.

Next implement capacity-limited potential services with finite staff-hours and
food-supported inputs,unmet requests and shared consumers. Do not promote a scalar
centre-intensity or archive label directly into institutions/control. Timing,
coverage,prospective transfer,S1c/d/e,S2qualification and S3–S5 remain required.

## Shared finite service-work consumer implemented,11 November2026

[Protocol3d3a6c4e and diagnostic](SETTLEMENT_SERVICE_CAPACITY_20261111.md):food-
supported staff remain inside SAMEresident/food ledger;otherduties reserve hours
beforeallservicechannels share the remainder. Unreachable/capacity deficits and
unused hours explicit,no rerouting/maxflow/extra population.20originalfoodcases
replayed,60workscenarios independently checked,sourcepackets unchanged.8unit tests.
Illustrative600hours/staff and1/2hourrequestcosts are NOT Earth-calibrated rates;
no empirical/production role/control adoption. Lightworkmostlynonbinding,not a fit.

Next monthly actualsupported-provider access plus explicit pooled labour claims
for collection,patrol and services. Binarypatrolreach currentlyhasnohourledger;
do not silently reuse allstaff for eachactivity. Keep source-time/coverage/transfer
qualification and full S1c/d/e,S2–S5,allactor/mobile/nonstate scope.

## Provider evidence and new Earth institution source,11 November2026

[Protocol831d0b11 and preparation](INSTITUTION_EVIDENCE_20261111.md) expose an
importantprior:85.71%/86.05% of raw/corrected year-store staffcomesfromgenerated
painted-claimhypotheses. All18actors/unresolvedretained;markedaffiliation also
isnotmeasuredworkforce. Foodfeasibilitycannotproveastaffedinstitution.

SeshatPolaris2026pinned55ca5fbc,8sheets/626polities/5007targetinstitutionhierarchy
records preparedwithoutpredictions/scores. Unknown/inferred/absent/ranges retained.
4511lackcompleteexplicitrowtimebounds;neednull-scopepolicy,code/alias/range/duplicate
reviewbeforeAD200comparison. Independent5007records/38actorcohortschecked,
4atlasinputsunchanged,121tests. Rawthirdpartyworkbook/textprivate;notsealedorfit.

Prioritybefore monthlyserviceclaims:separateproviderrole/evidence/timefromstaff
quantity,resolveEarthsourcesemantics,anddeclareactualinstitutiondevelopment/
transfercomparisons. Hierarchyofplacesisnothierarchyofpeople;absenceoffulltime
specialistsisnotabsenceofgeneralist/nonstategovernance. Keep SAMEfinitepeople/
food/staff/controlledgerandfull S1c/d/e,S2–S5. No productionadoptionornewphysics.

## Dated references and bounded map-release path,11 November2026

[Protocolf0f3b892 and scope comparison](INSTITUTION_SCOPE_20261111.md) reconstruct
10014row-policy cases without sampling,interpolation or value fitting. Documented
parent scopes give26year200hierarchy groups and18largest-population groups,
with24/14numeric source rows;explicit-only gives0/4groups. Original dates and
competing/unknown values remain. This advances release milestone1's references,
not map calibration. Located transfer and frozen comparison rules remain open.

Owner requested four milestones to a new settlement location/population release:
the explicit path is at the top of this roadmap. Detailed institution/control
work remains tracked for later releases. Consolidated development now uses ONLY
`claude/friendly-turing-43ygeu`;redundant publication branch retired with history
preserved. Do not push both or recreate the retired branch from old plans.
