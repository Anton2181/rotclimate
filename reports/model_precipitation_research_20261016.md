# How other models handle moist ascent, cloud formation and rain placement

16 October 2026. Primary-source literature, model documentation and source-code
review, performed while the user runs the frozen cloud-geometry replays. No
climate integration, calibration, new atmospheric dataset download or atlas
update was launched. Running sources, preparation and experiment evidence are
unchanged. Recommendations below are proposals, not implemented improvements.

**Follow-up after the user's replay completion:** all four saved years verify
and reproduce exactly, using 5.78 integration minutes. The matched-input
Iberia-domain arid summer case gets 93.1% of its rain from the unmixed parcel
operator. Of that parcel rain, 94.9% first saturates beyond the layer face,
versus 47.3% on the winter coast; 99.8% enters a pre-step recipient with RH
below 70%. This prioritizes a controlled path/mixing experiment in the
proposed process laboratory. It does not establish that cloud onset inside a
layer is invalid or quantify real entrainment/evaporation. California's similar
summer signature occurs in land that remains too dry. See
[verified diagnosis and figure](../output/v10_cloud_geometry_review/review.md).

## Finding that changes the development priority

**A more elaborate cloud scheme is not, by itself, a convincing remedy for
our winter drought.** Some useful idealized circulation models also precipitate
condensate immediately. What they retain is evolving atmospheric dynamics and
a distinction between resolved large-scale condensation and unresolved
convection. Our current five-layer experiment prescribes a projected flow and
synthetic disturbances; latent heating does not generate a dynamically coupled
storm. That is a structural difference, not a demonstrated attribution of
our rainfall error. [Isca model paper](https://gmd.copernicus.org/articles/11/843/2018/)
explicitly documents a primitive-equation moist model with fast precipitation
and no atmospheric liquid-water store.

The project evidence supports investigating two problems separately. At fixed
monthly incoming water, local humidity reduces reference-arid summer rain in
the Iberia domain from 86.35 to 73.08mm, toward 57.17mm reference. Coastal
winter rain only changes 59.10 to 61.28mm, against 439.18mm reference. California
remains at 92.96mm against 534.82mm and its Mediterranean-to-arid classification
worsens. These are paired prototype results, not proof of a unique cause. See
[verified saved-field review](../output/v10_spatial_humidity_review/review.md).

My inference is to prioritize coherent winter weather alongside cloud-process
work, rather than expect rain evaporation, cloud delays or another humidity
coefficient to provide the missing winter supply/ascension. Evaporation can
reduce surface rain directly; any increase elsewhere would require transport
or climate feedback, which must be measured rather than assumed.

## Comparison of model approaches

Each row names a specific implementation or configuration. These models are
not interchangeable, and this is not a ranking of their regional rainfall
accuracy. Computational burden below refers to additional mechanisms relative
to V10, not measured execution times on this computer.

| Model/configuration | Condensation, convection and precipitation | Useful lesson for this project |
|---|---|---|
| Current V10 cloud bound | Prescribed net air exchange; donor air cools to the next midpoint and can condense before mixing. Liquid immediately reaches the surface. | Separate lifting, cloud conversion and delivery before changing them. |
| SPEEDY / SPEEDY.f90 | Height-dependent humidity relaxation produces large-scale precipitation; a separate simplified Tiedtke mass-flux scheme handles convection. | A cheap model can separate physical roles without detailed microphysics. [Condensation](https://samhatfield.co.uk/speedy.f90/module/large_scale_condensation.html), [convection](https://samhatfield.co.uk/speedy.f90/module/convection.html). |
| Isca, simplest moist configuration | Fast large-scale precipitation; separate simplified Betts–Miller column adjustment, including a buoyancy trigger. | Immediate fallout can be a useful idealization when the circulation and convective treatment are appropriate. [Model](https://gmd.copernicus.org/articles/11/843/2018/), [scheme](https://execlim.github.io/Isca/modules/convection_simple_betts_miller.html). |
| PlaSim / inspected ExoPlaSim rain module | Separate Kuo convection and large-scale saturation adjustment; falling rain/snow can evaporate/sublimate and alter temperature/humidity. | Even an economical GCM distinguishes production aloft from precipitation surviving to the surface. [Source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/plasim/src/rainmod.f90). |
| SpeedyWeather.jl, ImplicitCondensation | Coupled humidity/latent-heat adjustment and optional top-down rain evaporation. | A diagnostic falling flux is an intermediate option before adding advected cloud/rain stores. [Documentation](https://speedyweather.github.io/SpeedyWeatherDocumentation/stable/large_scale_condensation). |
| ECMWF IFS stratiform cloud scheme | Cloud fraction plus cloud liquid, ice, rain and snow are prognosed; hydrometeors move, grow, fall and evaporate. Convection is separate. | Cloud formation, microphysics and delivery are different operations; cloud area matters. [Cloud scheme](https://confluence.ecmwf.int/spaces/FUG/pages/673550508/Section%2B2A.1.5.3%2BStratiform%2Bcloud%2Bprocesses%2Band%2Bprecipitation), [physics](https://www.ecmwf.int/en/research/modelling-and-prediction/atmospheric-physics). |
| WRF with Kessler warm-rain microphysics | Water vapor, cloud water and rainwater; cloud-to-rain conversion, rain sedimentation and evaporation. Coarse-grid convection uses a separate scheme. | Two additional water stores provide a small structural prototype, without immediately adding ice/aerosols. [Code](https://raw.githubusercontent.com/wrf-model/WRF/master/phys/module_mp_kessler.F), [WRF guidance](https://www2.mmm.ucar.edu/wrf/site/documentation/users_guide/physics.html). |
| CAM6 family / CLUBB | Subgrid turbulence and shallow clouds use a joint distribution of vertical velocity, temperature and moisture; microphysics handles hydrometeor evolution. | Avoid representing every cloudy updraft as perfectly unmixed, or every cell as completely homogeneous. [NCAR tutorial, pp.15–19](https://www.cesm.ucar.edu/sites/default/files/2025-07/2025cesmtmccluskeyfowler.pdf). |
| Smith–Barstad orographic model | Linear airflow response with cloud conversion, fallout delays, advection and lee evaporation. | Terrain-driven rain depends on finite time and stability, rather than just positive upslope motion. [Original paper](https://journals.ametsoc.org/abstract/journals/atsc/61/12/1520-0469_2004_061_1377_altoop_2.0.co_2.xml). |

### Low-cost circulation models are important counterexamples

In SPEEDY.f90, large-scale humidity relaxation supplies latent heating and
diagnoses precipitation from the column's moisture loss. Its convection module
has distinct instability, entrainment and mass-flux machinery. This does not
show that copying its RH thresholds would reproduce its climate; those
thresholds operate inside a different complete system. [Condensation module](https://samhatfield.co.uk/speedy.f90/module/large_scale_condensation.html),
[convection module](https://samhatfield.co.uk/speedy.f90/module/convection.html).

Isca's simplified Betts–Miller scheme computes a lifted parcel and CAPE,
relaxes temperature/moisture toward reference profiles, and corrects the
column enthalpy budget. It distinguishes precipitating deep adjustment from
nonprecipitating shallow adjustment. This is a column closure, not simply
permission for each resolved upward face flux to produce rain. [Scheme documentation](https://execlim.github.io/Isca/modules/convection_simple_betts_miller.html).

In inspected ExoPlaSim `rainmod.f90`, `mklsp` adjusts supersaturation with
latent heating, `kuo` is separate, and `mkrain` processes falling precipitation
through lower levels. `nevapprec=1` is the source default, subject to namelist
overrides. The `rcrit` setting is associated with cloud diagnosis; it must not
be mistaken for the large-scale rain trigger in `mklsp`. These details were
checked in source, rather than inferred from the Python interface. The linked
master branch is mutable; inspect the installed revision before implementation.
[Source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/plasim/src/rainmod.f90).

### There are two affordable steps between immediate fallout and full microphysics

**Diagnostic falling rain:** SpeedyWeather's documented option passes a rain
flux downward, evaporates a bounded fraction in subsaturated layers, returns
the water to vapor and includes the corresponding latent cooling. It does
not require that this condensation operator carry a prognostic cloud-water
and rainwater field. The documentation supports switching re-evaporation off;
do not assume a particular example's setting is every configuration's default.
[Implementation documentation](https://speedyweather.github.io/SpeedyWeatherDocumentation/stable/large_scale_condensation).

**Cloud and rain stores:** WRF's inspected Kessler routine keeps `qv`, `qc`
and `qr`, converts cloud water to rain, subcycles a downward sedimentation
flux to satisfy its fall-speed stability condition, and returns evaporated
rain to vapor with cooling. This separates time spent as cloud from time
spent falling. Its warm-rain-only assumption is a mechanism simplification,
not a complete winter cloud treatment. [Kessler source](https://raw.githubusercontent.com/wrf-model/WRF/master/phys/module_mp_kessler.F).

For V10 these are separate proposals. A diagnostic column flux could test
surface survival with little new state, but cannot represent horizontal drift
during a finite fall time. Adding cloud and rain stores can represent drift,
but requires new advection, phase-change, sedimentation, energy and checkpoint
accounting. Neither is a justified automatic replacement while the present
geometry diagnosis is still being evaluated.

### Higher-complexity schemes represent wet and dry parts of the same cell

IFS allows partially cloudy, grid-mean subsaturated cells rather than treating
grid-mean RH as in-cloud RH. Its saturation adjustment uses an assumed
subgrid temperature/humidity variability. That is relevant to our homogeneous
bulk rule versus perfectly unmixed ascending-parcel bound, although neither
one is the IFS scheme. [ECMWF moist-physics description](https://www.ecmwf.int/en/newsletter/164/meteorology/major-moist-physics-upgrade-ifs).

CLUBB similarly represents subgrid variability, including correlations among
vertical velocity, heat and moisture, rather than just a universal critical
RH. The CAM6 lineage also changes over releases: the 2023 PUMAS paper describes
the CAM6 MG2 baseline, while the 2025 NCAR tutorial presents PUMAS. Do not merge
those into one timeless default configuration.
[2025 tutorial](https://www.cesm.ucar.edu/sites/default/files/2025-07/2025cesmtmccluskeyfowler.pdf),
[PUMASv1 model description](https://gmd.copernicus.org/articles/16/1735/2023/).

The transferable idea is a conservative representation of cloudy air and its
environment, with their mixture fraction and shared heat/water budgets. A
full joint-PDF turbulence and multi-moment microphysics package would introduce
many unsupported states/closures before our forcing problem is resolved. A
two-population mechanism experiment is a more manageable proposal, not a
claim to implement CLUBB or reproduce its performance.

### Orographic rain is a transport-and-timescale problem

Smith–Barstad separates cloud conversion and fallout times and includes
airflow dynamics and downslope evaporation. A useful scale is wind speed
times a conversion/fallout delay; terrain width relative to such scales affects
where rain lands. Its assumptions include approximately saturated, steady,
linear flow and restricted stability, so it is not an all-season global rain
scheme. In particular, copying a downstream smoothing kernel without its
source/evaporation constraints would discard much of the physical point.
[Smith and Barstad (2004)](https://journals.ametsoc.org/abstract/journals/atsc/61/12/1520-0469_2004_061_1377_altoop_2.0.co_2.xml).

This is useful for manufactured ridge tests and later terrain downscaling.
It does not justify moving the same water over every ridge repeatedly, or
restoring the earlier V9 spillover knob under a new name. We need actual
vapor depletion and conservative condensate transport.

## Why coherent winter storms deserve a separate development path

An ERA5 Mediterranean moisture-budget study finds that transient storms
maintain much of winter land net precipitation, with a different seasonal
role for the time-mean/stationary circulation. Its transient term is estimated
as a residual, with acknowledged budget and discretization limitations; it
is not an exact directly observed flux target. Its DJF/JJA comparisons also
do not equal our October–March/April–September response averages. [Tootoonchi
et al. (2025)](https://wcd.copernicus.org/articles/6/245/2025/).

Our stronger vortices and aligned boundary-moisture pulses do not constitute
a frontal temperature structure or a momentum response to latent heating.
Fixed monthly gross water controls remove amount as one confound, but do not
match the evolving horizontal/vertical moisture transport, stability or cloud
area of real weather. Those are still open hypotheses, rather than a licence
to increase random storm strength until rainfall matches.

A useful published benchmark combines mountain-triggered baroclinic waves
and idealized moist physics; it tests how frontal rain bands and terrain
interact, and compares different dynamical cores. Its explicit appendix uses
three water species in a Kessler scheme. This is an example of a controlled
test, not a ready-made forcing module for our kinematic regional engine.
[Hughes and Jablonowski (2023)](https://gmd.copernicus.org/articles/16/6805/2023/).
NCAR also documents the [moist baroclinic-wave test](https://www.cesm.ucar.edu/models/simple/fkessler).

My larger architectural recommendation is to investigate a coarse global
circulation model as a source of coherent seasonal weather for the fantasy
region, followed by a separately validated conservative regional model.
ExoPlaSim is a candidate because the project already has an adapter and a
prior coarse experiment; Isca offers an explicit hierarchy of physics. Their
existence does not establish either model's fidelity for this fantasy world.
[ExoPlaSim paper](https://arxiv.org/abs/2107.07685),
[Isca framework](https://gmd.copernicus.org/articles/11/843/2018/).

This is more than extracting monthly mean winds. It needs time-aligned wind,
temperature, humidity and surface-pressure output, a compatible pressure/grid
mapping, boundary handling and checked dry-mass/heat/water fluxes. Surface
pressure and atmospheric mass vary in such a driver, whereas the present
regional experiment fixes its layer masses. A projection cannot silently
remove physically important divergence. Physical omega also must not be
equated to coordinate-interface exchange over sloping layers. No driver
download or GCM run is prepared by this research review.

## Changes worth testing, and the evidence each needs

| Proposal | It could address | It cannot establish alone | Evidence required before a regional batch |
|---|---|---|---|
| Refine vertical cloud path with matched dry mass/forcing | Rain sensitive to large midpoint jumps | Real storm frequency or missing moisture convergence | Geometry replay identifies affected interfaces; compare continuous and discretized parcel paths with consistent heat/work accounting. |
| Conservative cloudy/environment mixing | Perfectly isolated parcels overpredicting survival of cloud in dry environments | Buoyant convection from a net resolved flux | Account for both populations' dry mass, water and heat; demonstrate the dry/moist environment contrast on a fixed test. |
| Bounded top-down rain evaporation | Condensate reaching the surface through dry lower air | Missing winter condensation or horizontal drift | Layer-by-layer water/latent-heat budgets, finite evaporation rates, and a justified treatment of cloudy versus clear portions. |
| Cloud/rain stores and finite fallout | Cloud conversion delay, drift, peak/rain-shadow location | The correct source of large-scale ascent | Transport/phase-change/fallout limiting cases and a controlled ridge transect. |
| Coherent front or coarse-GCM weather | Seasonal storm routes, moisture/temperature covariance and dynamics | Regional topographic detail or unbiased cloud microphysics | Compatible mass/pressure/thermal forcing and a paired controlled case; externally credible weather before frequency fitting. |
| Separate buoyant convection closure | Unresolved instability-driven heat/moisture transport | Mechanically forced stratiform rain | Virtual-temperature buoyancy/CAPE/CIN, compensating environmental mass transport and conservation; isolate from resolved lifting. |

The first four are moderate local structural changes, of differing scope.
The fifth is a larger forcing/architecture change with higher potential
relevance to the winter deficit. The sixth is conditional on actual instability
evidence. These are engineering judgments, not measured success probabilities
or estimates of run cost. More detailed ice/aerosol microphysics is a later
question; a warm-rain toy can test transport and delivery without claiming to
validate real winter precipitation.

## A better calibration and evaluation process

Single-column modeling is an established way to test parameterized physics
under prescribed dynamical forcing. E3SM's documented framework can replay a
full-model column and compare process cases with observations or LES, while
acknowledging that isolated columns cannot establish three-dimensional remote
feedbacks. That is a useful methodological precedent for our cheap mechanism
tests, not evidence that a column test fixes regional climate. [Bogenschutz
et al. (2020)](https://gmd.copernicus.org/articles/13/4443/2020/index.html).

Adopt a fixed sequence before another broad fantasy fit:

1. **Manufactured process cases:** stable dry column; stable saturated air
   forced upward; rain entering dry lower air; ascending parcel mixed with
   dry/moist surroundings; one saturated ridge with a controlled wind;
   prescribed moist front crossing a ridge. These are new proposed tests,
   not a claim that the complete suite already exists.
2. **Compare closures under identical forcing:** distinguish the existing
   bulk rule, current unmixed bound, and one new conservative proposal.
   Change one mechanism at a time before any factorial interaction test.
   Preserve input column water, actual gross boundary input, dry mass and
   thermal targets where those are declared controls.
3. **Evaluate process responses:** cloud formation, evaporation, surface rain,
   exit flux, layer heat changes, coast/lee placement and interface sensitivity.
   Track numerical refinement separately from physical parameter changes.
4. **Regional comparisons:** use California and Iberia for development,
   retaining winter coastal/Mediterranean error and arid summer cell/month
   error as separate responses. Declare another region before selecting on it;
   repeated development catalogues are not untouched validation.
5. **Learn constrained responses:** fit a small response model to physically
   meaningful quantities and discard regimes that cannot improve winter rain
   without dry-interior damage. Keep several feasible candidates and spend
   subsequent user-run simulations on uncertainty or a discriminating test,
   rather than repeatedly selecting the highest aggregate score.
6. **Fantasy transfer last:** use the planet's own thermal/circulation forcing,
   then retain the existing per-world Mediterranean, cold-dry and hot-dry
   protections. Observed Earth T/profiles cannot simply be transplanted into
   the atlas as a newly predictive climate model.

This sequence is this project's proposed workflow. The E3SM and baroclinic-wave
sources motivate controlled evaluation, but do not prescribe our thresholds,
fantasy target rules or an optimizer that is already implemented here.

## Mistakes the comparison warns against

- Gating **all** upward flow on CAPE. Mechanical frontal/orographic ascent and
  subgrid buoyant convection need different treatment; the existing net face
  flux is not already a convective plume plus compensating environment.
- Evaporating rain instantly to grid-mean saturation. Mean RH below 70% is
  not the RH inside a raining cloud, nor an evaporation timescale. The current
  geometry replay does not directly measure in-cloud RH or a drop-size spectrum.
- Moving latent heating to wherever rain lands. Condensation heats where it
  occurs; subsequent evaporation cools where it occurs. A rain-shift operation
  cannot stand in for a phase/energy budget.
- Adding a cloud store while keeping all old immediate precipitation. That
  would duplicate water removal unless the old path is consistently replaced.
- Treating a half-time-step test as vertical convergence, or a refined upper
  grid as permission to invent humidity above the native data coverage.
- Treating a good cloud fraction or humidity threshold as verified surface
  rainfall skill. Formation, conversion and delivery are distinct responses.
- Assuming a sophisticated model is unbiased in California or Iberia. This
  review compares mechanisms; it performs no new intermodel climate validation.

## Handoff from the research, updated after diagnostic completion

The four exact cloud-geometry replays have now finished unchanged and their
saved-only verification passes. Their contrasting seasonal late-onset/dry-air
signature prioritizes the coarse parcel path and mixing as the next local
mechanism comparison. They cannot settle the missing storm-circulation question
or independently select a rain-evaporation law.

After reviewing those results, implement one controlled mechanism proposal
with the cheap process cases first. In parallel conceptually, audit whether
the existing ExoPlaSim experiment can supply suitable subdaily output and a
credible large-scale winter circulation; do not start a new global run just
to obtain another attractive map. The six-hourly NOAA audit remains paused.
No new annual command is proposed by this research review.

The existing ExoPlaSim adapter was also inspected without executing it.
`scripts/exoplasim_run.py` configures the global model and saves annual
postprocessed archives; it does not explicitly request the time-aligned
subdaily pressure/wind/T/q stream needed by this proposal. The comparison
script averages monthly output from the last years and applies a temperature
lapse correction. Neither operation establishes a usable weather-boundary
dataset. Inspect actual archive variables, sampling, units, planet setup and
the installed model revision before commissioning another user-run GCM job.

### An especially useful precedent: KiD, a microphysics laboratory

The Met Office's Kinematic Driver (KiD) was designed to compare cloud
microphysics under prescribed flow, without changing dynamics and radiation
between schemes. Its original intercomparison found differences in surface
rain onset and accumulation even with common forcing. A later warm-rain
benchmark explicitly distinguishes such controlled comparisons from feedbacks
in a fully coupled model. [Shipway and Hill (2012)](https://rmets.onlinelibrary.wiley.com/doi/abs/10.1002/qj.1913),
[warm-rain benchmark (2023)](https://journals.ametsoc.org/view/journals/atsc/80/5/JAS-D-21-0275.1.xml).
There are published [test specifications and code](https://adehill.github.io/KiD-A/).

This is a particularly close methodological fit for V10. Preserve its existing
conservative kinematic machinery as a **process laboratory**, with a common
forcing/diagnostics interface and swappable cloud operators. Use few-cell
columns and ridge slices to distinguish immediate removal, a diagnostic rain
shaft, and finite cloud/rain stores. Compare to analytic limits and a declared
finer reference solution; fine resolution is not automatically observational
truth. None of those operators earns Earth/fantasy climate validation merely
by matching the laboratory reference.

The Python-based [PPPY framework paper](https://gmd.copernicus.org/articles/13/443/2020/index.html)
offers another example of isolating parameterizations and examining time-step
dependence. [CliMA's KinematicDriver.jl](https://github.com/CliMA/KinematicDriver.jl)
also exposes prescribed-flow microphysics experiments and calibration tools.
These are precedents for a reusable comparison interface, not an instruction
to install Julia or another full framework. Our existing NumPy engine can
adopt the experimental method without immediately porting those libraries.

For a minimal local implementation, the essential contract would be:

- Each operator receives the same pressure, temperature, vapor, optional
  condensate stores and imposed transport; it returns phase tendencies,
  falling fluxes and explicit water/heat diagnostics.
- Internal phase changes conserve vapor + cloud liquid + rainwater. Only
  boundary transport, surface exchange and the bottom precipitation flux
  alter total column water. Conversion of cloud to rain is not a second
  latent-heat release.
- Conversion/heating and later evaporation/cooling are recorded separately.
  Sedimentation stability and pressure-path refinement are independent tests.
- The current frozen operator remains the exact regression control. Any
  richer energy convention needs its own declared budget, including transport
  and energy carried out by precipitation, rather than hiding a residual in
  the already diagnosed prescribed-flow work.

This full cloud/rain-store interface remains proposed rather than completed. It
would let the next calibration identify which process fails before spending
another regional year on each possible combination.

The actionable research result is a **two-part development direction**:
validated cloud-to-surface delivery for local placement, and coherent
circulation/weather forcing for the large winter deficit. The current evidence
does not justify choosing one as the sole cause or promoting a new atlas.

## Implementation follow-up: manufactured laboratory completed

The first local laboratory is now implemented in separate files, preserving
all frozen regional physics and evidence. It covers fixed pressure paths with
an independent thermodynamic ODE, conservative finite-population exchange,
an integral/flux-matched vertical-grid comparison and an exact-answer periodic
transport contact. This follows the controlled-comparison method above; it
does not implement KiD itself or the proposed cloud/rain stores.

The laboratory demonstrates that numerical upwind mixing can create
condensate even with perfect water/heat closure, while finer toy vertical
grids change total rain substantially. Physical mixing can also either create
or suppress clouds, depending on the populations. These results prioritize a
less diffusive conservative transport comparison before fitting an entrainment
coefficient. They do not quantify this mechanism's regional importance or
resolve missing winter circulation. See [results and next gates](v10_cloud_lab.md).
No real annual run, download or atlas update was performed.

The next numerical branch is also implemented: a bounded, shared-coefficient
flux-corrected transport prototype. It reduces artificial contact rain and
smooth-advection error while preserving the parent cloud rules. In the closed
rising circulation it makes more rain, not less. This supports separating
transport accuracy from physical calibration. It does not add cloud/rain
stores or coherent weather. The prototype currently supports only closed/
periodic meshes; see [tested results and open-boundary development plan](v10_flux_transport.md).
