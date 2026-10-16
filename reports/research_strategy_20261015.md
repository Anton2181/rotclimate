# Research strategy: diagnose what can be fixed before searching harder

15 October 2026. Requested while the four-layer overnight experiment is running.
This is a development proposal, not a change to that experiment's settings,
selection rules or publication policy. No seasonal simulation or calibration
was launched. Production and running-experiment sources remain untouched.

**Follow-up after completion:** the [overnight review](v10_overnight_review.md)
finds that the imposed targets exaggerate upper-air temperature departures
compared with local pressure-level reanalysis. The signed departures below are
still correct relative to those targets; they are not equally large errors
against actual free-air climatology. Rainfall failures remain substantial.

## Main recommendation

**16 October, regional attempt analyzed and handed off:** the fixed transport
comparison stopped at 6/8 cases. All four controls reproduce exactly and all
16 saved years verify. Both bulk candidates are wetter but unsettled; the
California parcel candidate fails the retained water-availability guard.
The immediate priority is conservative cloud/transport compatibility and the
layer-3 annual repeatability failure, before another fit or long run. Keep the
atlas and NOAA pause. See the
[current handoff](HANDOFF_20261016.md).
The prepared-protocol note below describes the earlier state of development.

**16 October, open transport comparison prepared:** external donor-cell
inflow/outflow now remains fixed while internal theta/vapor transfers use the
coupled correction. Known-answer open-wave error falls 75–90%; 133 checks and
sixteen independent short input probes pass, including external heat/water,
cloud-dose and restart checks. A fixed eight-case user-run regional comparison
is prepared under the existing local-matched humidity and synthetic weather.
It implements the strategy's paired mechanism test before another fit.
Estimated 1–2 hours with a resumable two-hour invocation cap. No actual annual
climate was launched by the assistant; atlas unchanged. See
[protocol and run command](v10_regional_transport.md).

**16 October, conservative transport candidate implemented:** a shared-limiter
flux correction reduces false rain 26–54% in the known-answer periodic contact
and improves smooth transport on every tested grid. Seventy fixed manufactured
comparisons complete; 79 focused checks pass and fourteen upwind controls match
saved parent results exactly. The closed rising circulation becomes wetter
under the unchanged clouds. This is a numerical candidate, not a regional
rainfall fix or a new fitted coefficient. Open-boundary flux contracts,
larger-mesh cost and frozen cloud-dose compatibility come before a user-run
regional comparison. See [results and remaining development](v10_flux_transport.md).
All frozen climate sources/evidence and the fantasy atlas remain unchanged.

**16 October, process laboratory completed:** 166 manufactured parcel paths,
18 closed circulations and ten periodic contacts now separate thermodynamic
path refinement, physical exchange and numerical mixing. Path refinement
adds a little condensate in the wet cases. Actual toy-grid refinement reduces
the cloud-rule gap while total rain still moves. Most decisively, conservative
upwind transport creates cloud at a saturated warm/cold contact whose exact
inviscid translation makes none. This is numerical evidence in a manufactured
case, not a measured fraction of regional rainfall error. It implements the
strategy's analytic-limit and resolution checks and motivates a less diffusive
conservative transport comparison before another cloud-parameter fit.
See [findings and declared next gates](v10_cloud_lab.md). No annual climate or
download was run; 79 focused checks pass and the atlas remains unchanged.

**16 October, completed cloud-path diagnosis:** all four final-year replays
reproduce exactly and verify independently. Matched-input Iberia-domain arid
summer rain is 93.1% parcel-generated; 94.9% of that parcel rain first saturates
beyond the layer face, compared with 47.3% on the winter coast. This supports
the next common-forcing vertical-path/mixing comparison rather than immediate
selection of a rain-evaporation law or another regional sweep. California's
similar summer signature in land already too dry makes universal suppression
an especially poor objective. The diagnostics do not establish that above-face
saturation is invalid. See [verified results](../output/v10_cloud_geometry_review/review.md).

**16 October, model-comparison research:** a new [primary-source review](model_precipitation_research_20261016.md)
compares cheap circulation models, operational cloud schemes and controlled
microphysics testbeds. Isca's fast-precipitation configuration is a useful
counterexample to blaming immediate fallout alone. KiD provides a direct
methodological precedent for using V10 as a common-forcing cloud-process
laboratory. Separate rain-shaft evaporation and finite condensate transport
from the larger question of coherent storm dynamics. A later coarse-global /
regional architecture requires subdaily multivariable forcing and checked
mass/pressure compatibility; existing monthly ExoPlaSim comparisons do not
already provide this. Current replays and all frozen sources are unchanged.

**16 October, completed local-humidity follow-up:** twelve cases / 28 saved
years verify independently, with four exact controls and all declared physical,
settling and thermal checks. At fixed monthly gross input, native boundary
redistribution reduces Iberia-domain reference-arid summer rain 86.35 → 73.08mm
(57.17mm target), but coastal winter rain barely improves 59.10 → 61.28mm
(439.18mm target). California's reference-Mediterranean-to-arid fraction
worsens 75.4% → 78.3%, despite slightly better aggregate MAE. This implements
the strategy's separation of supply/distribution from cloud response and
shows why headline error alone is insufficient. See
[verified maps/seasonal errors](../output/v10_spatial_humidity_review/review.md).

The completed cloud-path task implements sections B/D below: four exact passive
cloud-path replays, measuring moist ascending transport, the actual cloud-rain
subset first saturating above the true layer face, pressure gaps, and dry
pre-step environmental air. No alternate physics or candidate climate is
applied. Results can justify vertical refinement, entrainment, or a return to
the circulation problem; they cannot by themselves validate any of those
fixes. See [protocol](v10_cloud_geometry.md). The user runs annual work; NOAA
remains paused and the fantasy atlas is unchanged.

Make calibration answer two questions: **which climates can this model produce,
and which missing mechanism prevents the desired combination?** Finding the
highest average score is a later step. In particular, Mediterranean winter rain
and a dry continental interior must be separate observable responses, rather
than two casualties of a single broad wetting control.

The proposed improvement has three parts:

1. Process diagnostics that distinguish moisture supply, transport, cooling and
   rain placement, with a few decisive manufactured tests.
2. A constrained calibration that learns parameter responses, keeps several
   acceptable settings, and spends runs on uncertainty or conflicting evidence.
3. A fantasy-map inference problem that separates physical coefficients from
   uncertain mountains, surrounding geography and large-scale circulation.

These are recommendations specific to this project's evidence. They do not
establish that every painted zone is jointly achievable.

**Implementation follow-up, 15 October:** layer rain/signed thermal accounting,
dry ridge and pressure/height tests, hybrid geometry, mass-consistent flow and
nested paired storm catalogues are implemented. The completed storm controls
now have a saved-only coastal/interior winter/summer response table, per-unit
secants and full rain-change maps. They expose a California wet-interior/dry-coast
conflict rather than support another frequency sweep. A separately frozen
four-case spatial monthly wind test is prepared; the user runs it. See
[results, response figure and next protocol](v10_spatial_wind.md).
Formal history matching, constrained fantasy response solving, adaptive run
selection, source-water tracers, transient flux covariance and explicit fantasy
geography hypotheses remain outstanding. Old acceptance evidence is preserved.

**Further follow-up:** all spatial-wind cases settle but severely underproduce
rain. Before more forcing adjustments, independent dry-law probes expose a
limitation of passive approximate-MSE transport under prescribed flow. A separate
pressure-based dry-theta version passes constant-pressure and Poisson-transfer
limits, with explicit diagnosed flow-work accounting. Raw horizontal/vertical
heat contributions also contain cancelling mass-divergence terms and must not
be interpreted alone as parcel heating. A four-case matched thermal-transport
comparison is prepared for the user; see
[dry-law audit and new protocol](v10_pressure_thermodynamics.md). No claim is made
that this demonstrated local flaw caused the regional rainfall failure.

**Completed thermal comparison:** the four pressure-based cases settle, but
rainfall remains misplaced or severely deficient. Three monthly-MAE results
worsen slightly; California uniform improves modestly and still loses to zero
rain. The updated Köppen maps retain extensive Mediterranean-to-arid errors.
The next prepared step now implements the transient-covariance measurement in
section C: bounded six-hourly reference analysis, without seasonal integration
or parameter fitting. A later paired-versus-time-separated weather test must
first resolve pressure/mass and boundary consistency. See
[completed results and weather-audit protocol](v10_weather_audit.md).

**Source-water follow-up:** while NOAA rate-limits the reference-weather audit,
a separately fingerprinted 2.5-hour user-run batch now implements passive
last-vapor-source accounting. Twenty fixed cases pair uniform/spatial winds
across five synthetic storm seeds, with unchanged physical solutions and an
exact seed-41 reproduction check. This diagnoses supply/export/rain placement
and catalogue sensitivity; it does not replace the real transient-covariance
measurement or trace original ancestry through soil. See
[water-source batch](v10_water_sources.md). No parameter search is prepared.

**Completed source-water follow-up:** all twenty cases / eighty cycles verify
and settle. The severe spatial-wind drought survives all five synthetic
catalogues. Roughly 98–99% of incoming boundary/local ocean vapor is exported
in those cases. Cached flow probes do not support a huge projection-induced
monthly wind reversal. A separate profile integral reveals that the single
top cell represents only about 27% of native moisture in its 608–300 hPa
portion. Splitting that known band improves the profile-only quadrature to
about 95%, earning a controlled vertical-structure prototype rather than
proving a rainfall fix. See [completed review and next design](v10_water_sources_review.md).
This implements the strategy's source accounting and vertical-quadrature
diagnosis. Real transient covariance, above-300-hPa humidity treatment,
arbitrary-layer climate implementation and fantasy transfer remain unresolved.

**Five-layer implementation follow-up:** the separate structural experiment is
now prepared with controlled coarse circulation, pressure-consistent upper
thermal targets, explicit zero/retained-RH300 incoming-humidity assumptions
above the data coverage, and an old-column-water matched control. Twelve
fixed cases reuse four completed controls. Sixty focused tests and forty-eight
independent short regional probes pass; the user runs the seasonal batch.
Actual climate benefit, annual settling, real transient weather and fantasy
transfer remain untested. See [five-layer protocol](v10_split_column.md).

**Completed five-layer follow-up:** all twelve cases settle and verify. The
California matched-column MAE gain comes entirely from reducing errors in
previously over-wet cells; errors in already dry cells increase in aggregate,
and Mediterranean-to-arid errors worsen. Column matching still raises actual
gross import by 9.6–15.3%, while about 97–98% of the upper-humidity-induced
rain increment forms in the unobserved highest layer. This is a practical
example of why the strategy requires separate continuous coastal/interior
responses and physical controls before ranking by a single score. See the
[completed five-layer review](../output/v10_split_review/review.md).

A cached three-hour circulation audit finds coastal winter descent in both
spatial backgrounds, mostly unreversed by the existing synthetic events.
The [next event-forcing design](v10_event_forcing_plan.md) therefore separates
episodic lifting from humidity timing, preserving monthly dry circulation
and requiring a genuine gross-import control. This is mechanism-test design,
not an implemented or observationally validated weather model. The NOAA
six-hourly reference remains unavailable through the attempted endpoint.

**Event-forcing implementation:** the [new paired mechanism test](v10_event_forcing_plan.md)
is ready for the user. It controls monthly mean dry circulation and **gross
incoming vapor**, separately varying convergence fluctuations and local
boundary moisture timing. Its first two held-boundary controls must match
the completed climates before ten mechanism cases proceed. Actual humidity
means/variances, evaporation, heat transport and flow work remain diagnosed,
not incorrectly claimed fixed.

A forcing-only design audit found the original fourfold fluctuation had only
about a 1% effect on coastal winter positive ascent. It chose the smallest
of fixed tested doses 1/4/16/32/64 with at least 10% contrast in both regions:
sixteen gives +12.2% / +16.2%. No new seasonal outcome or observed rainfall
was used. This applies the strategy's inexpensive mechanism/power checks
before committing long runs; it is not calibration of observed storm strength.
Ninety focused tests and 48 independent short regional probes pass. Formal
history matching and realistic high-frequency forcing remain outstanding.

**Completed event-forcing follow-up:** all twelve cases settle, both held-water
controls pass and monthly actual boundary import remains matched. Stronger
lifting adds coastal winter rain in both regions, largely through middle-layer
condensation, but closes only 8.7% / 4.6% of the original deficit. The moisture
timing contribution is small and not uniformly positive. Ocean evaporation and
land recycling respond, so fixed boundary input is not fixed total vapor supply.
See the [verified saved-field review](../output/v10_event_review/review.md).

The next [passive four-year diagnostic replay](v10_delivery_replay.md) reuses
the exact saved preceding-year states, avoiding another parameter search or
spin-up. It requires bitwise-identical physical results and records local
water budgets, humidity/ascent overlap and condensation opportunities across
transport/thermal-relaxation stages. Opportunities are not an alternative
climate and may count the same vapor repeatedly. This implements process
diagnosis on a controlled realized trajectory; observed high-frequency
forcing, causal changed-physics tests and fantasy transfer remain outstanding.

**Three-to-four-hour user handoff:** the user requested longer unattended work.
The [new bounded batch](v10_afternoon_delivery.md) puts those four process
diagnostic replays first, then repeats four fixed forcing contrasts across
eight synthetic catalogues and two regions, with exact final-year diagnostic
replays for the original/steady and lift16/linked pair. This combines process
diagnosis with paired response repeatability; it does not optimize amplitudes
or select a favourable catalogue. Gross water-input matching is within each
catalogue/region, not across catalogues. Previously used catalogues are not
untouched validation or an observational uncertainty sample. The invocation
budget is 3.75 hours, with monthly resume and no atlas publication. 113 focused
tests and 24 independent short regional probes pass; no real annual integration
was started by the assistant.

## Evidence that changes the priorities

**Completed cloud-source follow-up, 16 October:** all four exact final-year
replays verify. Last-vapor-entry labels attribute 74.9% of Iberia-domain
reference-arid summer cloud rain to boundary input, 16.9% to local ocean
evaporation and 8.2% to land recycling. This deprioritizes soil evaporation as
the principal direct supply, without claiming its causal influence is only 8%.
The [verified source review](../output/v10_cloud_source_review/review.md) directs
attention to regional inflow and the cloud/circulation treatment.

The old offshore-mean humidity is imposed on every edge. The next
[local-humidity comparison](v10_spatial_humidity.md) uses already cached native
monthly fields at each boundary pressure, with absolute and monthly-gross-input
matched controls. Winds and nominal weather timing stay fixed. Forcing-only
preparation shows the matched pattern reduces Iberia summer input at land
boundary cells by 15.1% while preserving the monthly total. No new climate
benefit is claimed. This applies the strategy's input audit and controlled
placement/amount separation, rather than more parameter search. 162 focused
tests and twelve independent short probes pass; the user runs the annual cases.

**Completed cloud-bound follow-up, 16 October:** all 52 cases / 192 saved years
verify and settle. The lower-interface gain repeats across four synthetic
catalogues, and twelve half-step checks change coastal winter rain by at most
0.173mm. This addresses one numerical sensitivity, not spatial-resolution
convergence or realistic cloud validation. The source treatment is still an
unmixed, immediate-liquid-fallout limit.

Saved field analysis now exposes the next process conflict: in seed67 Iberia,
monthly-MAE gains in reference Mediterranean/other land are offset by worsening
reference-arid land, especially in summer. The [verified maps and seasonal
decomposition](../output/v10_cloud_review/review.md) replace an aggregate-score
ranking with explicit placement diagnostics. A separately fingerprinted
[four-year passive replay](v10_cloud_sources_replay.md) now attributes cloud
rain to the ascending donor's last-vapor-entry label before recipient mixing.
It requires exact physical reproduction, no new spin-up or parameter search.
This extends the strategy's source/process accounting to the changed cloud
rule; tags alone will not establish the causal value of suppressing recycling.
153 focused tests pass; the assistant started no real annual replay. The
fantasy atlas is unchanged.

**16 October process follow-up:** the bounded afternoon run stops normally at
51 jobs, with all eight region/catalogue forcing comparisons from its first
four catalogues available. Stronger lifting helps consistently but leaves
substantial drought. Rather than complete more catalogue repetitions first,
three inexpensive checks now test the mean-cell cloud closure: saved winter
thermal-stage diagnostics, a constructed mixing counterexample and 24
independent <=60-second real-input steps. None is a new annual climate result.
They motivate a [staged cloud-mixing sensitivity](v10_cloud_mixing.md): exact
controls, a short regional screen, then fixed synthetic-weather and half-step
checks if the screen passes. This advances process diagnosis, not history
matching or a validated cloud scheme. The prototype's unmixed parcel/immediate
liquid-fallout assumptions are deliberately strong; a gain would require a
more realistic representation before any fantasy transfer or atlas update.

Existing results establish excessive humidity and incomplete wind/temperature
forcing in the original two-layer prototype. Correcting those inputs is
necessary, but is not sufficient evidence of a working rainfall model.

I captured the first eight completed forcing settings in both regions from the
running batch. These are the 2×2×2 wind/temperature/humidity controls, all with
shallow terrain return, 120 km spacing and weather seed 41. Final-year arrays
were checked against their recorded hashes. The snapshot is retained at
[`output/research_strategy_20261015/evidence_snapshot.json`](../output/research_strategy_20261015/evidence_snapshot.json).
It is an exploratory subset, not the overnight verdict. The remaining terrain,
weather, parameter and resolution checks can change the conclusions.

| First fully reference-informed control | California | Iberia |
|---|---:|---:|
| Repeated years to settling | 4 | 5 |
| Mean annual rain / reference | 2.91 | 0.94 |
| Reference non-arid land receiving at least 1 mm/year | 67.2% | 70.6% |
| Lower-layer p95 absolute temperature departure | 7.69°C | 8.51°C |
| Upper-layer p95 absolute temperature departure | 17.63°C | 13.61°C |
| Coast minus interior annual rain, model | −186 mm | +298 mm |
| Coast minus interior annual rain, reference | +460 mm | +564 mm |

The signed departures are informative: California's two upper layers have median
departures of −6.02 and −7.23°C. This is cooling relative to the new reference
targets, even though the earlier forcing audit found that the old targets were
too warm. Replacing the target does not remove the model's transport/thermal
imbalance. Tightening relaxation might conceal that imbalance; it must be
tested with tendency accounting rather than assumed to repair it.

There are strong interactions. In California, switching to reference humidity
changes monthly rainfall MAE by −39.02, −13.55, −20.64 or **+27.50 mm** depending
on the other two forcing choices. The last value is the fully corrected
wind/temperature background. These are matched factorial contrasts in this
four-layer geometry, not replicas of the original two-layer audit. They argue
against choosing a humidity multiplier independently of the thermal and wind
closure. All sixteen controls fail at least one eligibility requirement.

The 120 km masks contain only 67 California and 172 Iberia land cells. These
cells are spatially related and are not independent observation replicates.
Both regions are already development evidence. No significance claim follows
from this snapshot, and it does not justify changing the live protocol.

## 1. Highest-priority physical hypotheses

### A. Vertical transport and thermodynamics may remain inconsistent

The four-layer engine closes its declared water and approximate static-energy
ledgers. Closure alone cannot establish correct circulation, vertical structure
or rainfall. Momentum and radiation are prescribed; condensation retains latent
heat, but the resulting temperature is relaxed toward an imposed profile.

The highest layer represents 60% of atmospheric dry mass using one pressure,
temperature and height. Heights are fixed offshore offsets added to terrain;
surface pressure follows a fixed 8.4 km scale height. All local land-season
temperature variations are also copied into the upper relaxation targets.
These are substantial approximations, even with reference-derived offsets.

**Decisive tests, before another large tuning batch:**

- An initially unsaturated, uniform flat-domain case with evaporation and other
  sources disabled must not manufacture rain or temperature structure.
- A dry parcel crossing one smooth hill should follow the model's stated
  adiabatic/static-energy relation. Check pressure–height consistency separately
  against a hydrostatic reference. A conserved quantity can still be coupled to
  an inappropriate pressure coordinate.
- Repeat the hill with prescribed interface exchange versus no interface
  exchange. Save dry-static and latent-energy tendencies separately, including
  horizontal transport, every vertical interface, evaporation, condensation and
  relaxation, with signed local ledgers.
- Compare a pressure-integrated reference profile with the midpoint profile;
  only then test a more evenly resolved upper column. Changing layer count
  alone should not also change boundary humidity, integrated dry mass or storms.

**An important control distinction:** `terrain='none'` removes the drag-induced
flux modification. It does not remove elevation from layer heights, pressure,
saturation or the observed surface-temperature pattern. It therefore does not
mean “no mountains” or “no orographic effect.” Add separate artificial controls
that flatten geometry/pressure and homogenize the temperature pattern, one
intervention at a time. Keep these labelled as mechanism tests, not Earth
climates.

Possible fixes depend on which test fails: consistent pressure/height geometry,
better layer quadrature, a finite-depth terrain response, or conservative
stability-driven mixing. Saturation adjustment removes supersaturation;
convective adjustment additionally treats unstable vertical stratification.
The distinction is established in [Manabe and Strickler's original
study](https://www.gfdl.noaa.gov/bibliography/related_files/sm6401.pdf); it does
not establish that convection is the dominant error here. Diagnose instability
before adding a convection scheme.

### B. Condensation may rain out in the wrong place and too efficiently

The current closure precipitates condensed water immediately at its formation
cell. There is no cloud-water transport, finite conversion/fall time, or
evaporation of falling precipitation. Persistent mountain peaks and dry nearby
land are consistent with a placement/efficiency problem, although they do not
uniquely identify it.

First measure rain by layer, elevation, windward/lee position and distance from
the coast. Compare incoming vapour, condensed water, surface rain and outgoing
vapour along a simple ridge transect. If moisture supply is reasonable but
nearly all condensation falls at the first obstacle, add a conservative cloud
store and finite fallout with subsaturated evaporation.

[Smith and Barstad](https://training.weather.gov/wdtd/courses/woc/winter/physiogeographic/cool-season-orographic/story_content/external_files/Smith%20and%20Barstad%202004.pdf)
explicitly distinguish airflow response, cloud conversion, advection, fallout
and downslope evaporation. Their theory motivates a mechanism test; its linear
near-saturation assumptions are not a replacement for all regional weather.
The earlier V9 spillover trial was unproductive. A new version earns its place
only through this specific diagnosis, including whether it worsens dry-interior
protection.

### C. Mean forcing may miss the weather that actually imports moisture

Monthly, horizontally uniform offshore winds/humidity cannot describe moist
storm sectors, land/ocean differences at all four boundaries, frontal thermal
structure or stationary circulation. In general the mean moisture flux contains
a covariance term: mean(q·v) = mean(q)·mean(v) + mean(q′·v′). Adding arbitrary
vortices need not reproduce that term.

The [ERA5 Mediterranean moisture-budget
study](https://wcd.copernicus.org/articles/6/245/2025/) identifies winter wetting
by transient eddies and opposing contributions from mean circulation. That
supports measuring these separately, rather than treating a fitted storm count
as evidence that transient transport is correct.

A next diagnostic version should save mean and transient moisture-flux
convergence, storm-conditioned boundary imports and land/coastal/interior
budgets. Compare with suitable reference flux products or a bounded sample of
submonthly atmospheric fields. Monthly climatology cannot recover covariance.
Use spatially varying reference profiles as a controlled Earth test, without
letting observed precipitation enter the engine.

### D. Numerical mixing may be doing some of the cloud physics

Donor-cell transport is conservative and positive under the CFL condition, but
also diffusive. Mixing parcels with different temperatures and humidity can
change saturation nonlinearly. Budget closure will not reveal an erroneous
rainfall distribution caused by truncation error.

Use an analytically translated, everywhere-unsaturated moisture/temperature
front, then a saturated-front/ridge test. Compare phase, amplitude, rain and
temperature at fixed terrain and forcing with smaller time steps and grid
spacing. Only if errors are large, prototype a positive flux-limited transport
scheme. Distinguish timestep error, advection error and changing coast/terrain
sampling; the live grid sweep mixes some of these effects and cannot isolate
all three by itself.

### E. Evaporation and boundaries may supply compensating water or energy

Ocean evaporation is capped and has explicit latent input, but there is no
prognostic surface-energy budget. A conserved atmospheric ledger does not make
that energy supply physically correct. Boundary humidity also uses an offshore
profile on land boundaries, capped by local saturation.

Break down water import by side and level, ocean evaporation by fetch, recycling
and precipitation efficiency. For energy, distinguish large opposing sources
from a small net residual. Test domain padding at fixed interior resolution.
Prioritize a surface-energy limit or improved boundary profiles only if these
terms account for the actual error. Land snow/storage upgrades remain useful
later for summer drought and wetlands; they are weaker first explanations for
missing Mediterranean winter rain.

## 2. A calibration process that diagnoses its own limitations

### A. Learn acceptable regions, rather than only one champion

Use history matching as a feasibility stage: eliminate settings inconsistent
with independently declared process ranges and protected-zone limits, retaining
an ensemble of plausible survivors. [Couvreux et
al.](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2020MS002217)
demonstrate process-based, multi-case calibration used to expose limitations
of parameterizations as well as acceptable parameter ranges. [Hourdin et
al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10355829/) discuss retaining
alternative acceptable configurations and structural uncertainty.

For this project, build inexpensive predictors from **compatible archived
runs** first. Never merge different physics/source IDs, grids, warm-up policies
or input versions as if they were repeats. Categorical terrain/rotation choices
remain separate factors. With limited evidence, use a small active parameter
subset and compare simple regularized predictors before adopting an elaborate
Gaussian process. Hold out complete settings/worlds/regions when testing
predictions; nearby pixels and repeated warm-up years are not independent data.

An empty estimated feasible region means “none found with these runs, tolerances
and predictor,” not proof that the painting is impossible. Audit predictor
errors and unexplored parameter space before declaring a structural limitation.

### B. Measure whether the available controls point in the needed direction

This is the most useful project-specific addition. Form a response vector with
Mediterranean winter rain, summer rain, continuous aridity margins, coastal
contrast, cold-dry and hot-dry guard metrics, and temperature departures.
Estimate a local response matrix from genuinely paired archived runs; add a
few matched perturbations only where coverage is missing.

Ask whether a bounded combination of parameter changes can increase winter
rain on the dry Mediterranean strip while keeping the protected zones within
their limits. A constrained local linear solve can answer that question cheaply.
Scale outputs by declared tolerances and inspect correlated/indistinguishable
parameter directions. Verify any suggested combination with a real simulation.

If every measured direction wets the interior along with the coast, that is
evidence to introduce a different transport path or barrier response, rather
than merely increasing search duration. This is a local, approximate diagnosis,
not a global infeasibility certificate. The current forcing interactions show
why it must be checked at more than one background setting.

### C. Choose the next runs for information as well as improvement

Proposed batch allocation: roughly half near feasible improvements, one quarter
where competing predictors/mechanism hypotheses disagree, and one quarter for
unexplored controls or deliberate stress cases. These fractions are initial
design choices, not measured optimal allocations. Rank expected information or
feasible improvement against measured runtime; retain some slow/uncertain cases
so a cost penalty does not simply hide difficult physics.

Use a coarse model only after paired coarse/fine runs establish that it predicts
the relevant decisions. Learn a correction and uncertainty from those pairs;
audit a sample of coarse rejections at higher resolution. [Multifidelity
methods](https://arxiv.org/abs/1806.10761) combine cheap and expensive evidence
while retaining the expensive model for accuracy. They do not justify a
coarse-only winner or a promised speedup here.

Each campaign should return a feasible set, active constraints, unresolved
hypotheses and an explicit next decision even if it finds no improved atlas.
Stop expanding a search when another wave adds little useful evidence; move
to the mechanism test that distinguishes the remaining explanations.

### D. Make comparisons genuinely paired

Fantasy `beyond_seed` changes surrounding geography; V10 weather seeds change
storm realizations. They measure different uncertainties and must not be pooled.
Repeated forcing years measure settling, not additional independent climate
samples.

A shared weather seed also does not guarantee shared storms when storm rate
changes: the current Poisson catalogue consumes a different sequence of random
draws. A future runner can generate a master marked event process and use
thinning to obtain nested lower-rate catalogues. Share event positions,
strengths and dates across appropriate comparisons; validate ensemble
conclusions on new seeds. Do not modify the catalogue during the live run.

### E. Use continuous physical targets alongside the existing labels

The fantasy dry strip's classification is sensitive to Köppen's winter-70%
boundary, which lowers the aridity threshold by 140 mm. Preserve that standard
rule. Save winter/summer/annual rain, temperature and distances to the aridity
and summer-drought boundaries; distinguish extra winter water from redistribution
or a threshold crossing. Also retain spatial maps of newly damaged and repaired
cells, rather than only net dry area.

Future calibration can use smooth physical margins for guidance and exact
existing classifications/guards for acceptance. Do not optimize by redefining
the painting or relaxing protected-zone rules. Forest, swamp and warm-wet rules
overlap; display-policy changes are separate from climate improvement.

## 3. Specific avenues for the fantasy map

### First: identify the missing winter route

Under unchanged physics, the known surrounding worlds produce about 1.5–11.6%
dry Mediterranean land. Their effects exceed the recent local parameter gains.
Some of that spread is amplified by the seasonal classification boundary, but
saved fields also show real rainfall changes.

For a conservative future engine, tag water by source: external boundary,
different ocean sectors and land recycling. Transport the tags with exactly the
same fluxes and rain removal as total water; soil/cloud stores need consistent
tags if included. Check that tags sum back to total water. This identifies where
water came from, not the climate response to removing its source.

V9's nonconservative mixing cannot supply this exact source accounting. Its
saved local terms remain diagnostic evidence, not a globally conservative tag
budget.

### Second: replace arbitrary surroundings with explicit geography hypotheses

Keep the drawn map, scale and climate target fixed. Define a small set of
coherent exterior worlds differing in winter ocean fetch, upwind land/barriers
and enclosed-sea connections. Describe those differences before fitting.
Compare identical physics across them, then assess residual procedural
uncertainty within each hypothesis. Do not silently choose an exterior only
because it maximizes the painting score.

The atlas ultimately represents one world. We should distinguish selecting its
plausible surrounding geography from asking whether physics transfers across
several worlds. Physics coefficients can be constrained by Earth cases;
orientation, latitude and exterior geography are fantasy-world inference
variables. They should not all compensate for one another in the same
unrestricted optimization.

### Third: test rain-shadow geometry and seasonal storm paths

Broad isotropic exchange can deliver winter water to the Mediterranean and leak
it into the cold-dry interior. Candidate alternatives are wind-aligned,
conservative storm transport; stability-dependent blocking/diversion; and a
terrain response that distinguishes a pass from a solid barrier. They must
depend on geography and circulation, never on painted zone IDs.

The map's four elevation tiers do not uniquely specify a realistic mountain
surface. Generate a small ensemble of terrain reconstructions preserving tier
order, drawn ridges/coasts and independently justified drainage constraints.
Test whether unresolved passes or broad ramp shapes control the dry strip.
Rivers may constrain terrain, but if used for fitting they cease to be an
independent validation dataset. Wetland/soil diagnostics cannot repair a
missing atmospheric winter route by relabelling the land.

For retrograde circulation, test a manufactured east–west mirror with all
relevant vectors, storm translation/rotation and geography transformed
consistently. Reversing the sign of a zonal wind is not a planetary circulation
model. [Retrograde-Earth experiments](https://esd.copernicus.org/articles/9/1191/2018/)
show substantial changes in continental precipitation, storm tracks and ocean
circulation. The existing coarse ExoPlaSim experiment could constrain broad
seasonal boundary flow after checking its inputs/provenance; it cannot resolve
the painted coastal strip. A regional conservative downscaler driven by a
credible large-scale circulation is a longer-term alternative to adding many
independent rainfall knobs.

## 4. Practical sequence after the current batch

1. **Use the completed batch fully.** Compare matched forcing/terrain controls,
   failure signatures, uncertainty across weather and paired resolution checks.
   If nothing qualifies, report that without promoting the least-bad score.
2. **Isolate the dominant mechanism.** Prefer the small dry-column, ridge and
   transport-front tests above. Add local signed diagnostics and rain-by-layer
   in a new, separately fingerprinted branch. Do not rerun the whole sweep just
   to obtain missing tendencies; a few representative cases should suffice.
3. **Make one physical change and test transfer.** Use matched California and
   Iberia controls. After development, declare an additional, previously unused
   region before choosing settings; neither existing region is untouched
   validation. Include dry-interior and coast/lee structure, not just total rain.
4. **Bridge to fantasy forcing explicitly.** Earth V10 currently uses observed
   temperature and prescribed atmospheric profiles. Before any atlas run,
   construct mass-consistent flow and a thermal closure under the fantasy
   planet's own forcing. Copying California boundary profiles to the fantasy
   map would not be a transferable climate model.
5. **Check main-map and dry-zone stress worlds first.** Keep identical controls
   and the user's existing per-world protections. Then use response learning,
   constrained feasibility and adaptive batches for any larger search.

The retained acceptance policy is Mediterranean dry area <=max(anchor,5%) per
world, strictly improved worst-world dryness, and losses no greater than
2 points cold-dry, 3 hot-dry, 1 overall and 2 Mediterranean Cs area. These gates
do not imply that the desired <=5% target is already achieved everywhere.

No new long command is needed while the current experiment runs. This proposal
does not alter its frozen protocol, launch an automation or update the atlas.
