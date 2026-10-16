# Near-term climate development plan

## Latest: regional transport stopped at 6/8; handoff prepared

16 October 2026. All 16 saved annual records and six summaries independently
verify; all four upwind controls reproduce exactly. FCT bulk coastal winter
rain increases 56.91→90.23mm in California and 33.26→59.15mm in Iberia, still
far below reference. Neither candidate settles. California has substantial
layer-3 endpoint temperature changes (max 10.72°C on scored land); Iberia
narrowly misses the endpoint criterion and worsens arid summer monthly MAE.

The California FCT parcel candidate then stops with
`Ascending parcel condensate exceeds transported water.` Only its configuration
is saved; the exact failing step is unknown. The Iberia parcel candidate is
unstarted. Preserve the `needs_diagnosis` evidence and frozen sources. Do not
reset or repeat this command unchanged, clip rain, or start another sweep.

Next work is saved-field/controlled-example diagnosis of repeatability and a
conservative transport–cloud interface, with coherent winter weather retained
as a separate research branch. No new long run is recommended yet. All real
simulations remain user-run; atlas unchanged; NOAA six-hourly fetching paused.

Read the [current handoff](HANDOFF_20261016.md)
and [verified saved-only review](../output/v10_regional_transport_review/review.md).
Six new review checks pass. Older run instructions below record previous stages.

## Previous: open boundaries and restart checks pass; regional comparison prepared

16 October 2026. The candidate now preserves the original external donor-cell
inflow/outflow and corrects internal transfers only. Open-wave transport error
falls about 75–90% under identical supplied water/heat. 133 focused tests and
sixteen independent <=60-second real-input probes pass. No real annual run,
calibration or download was launched by the assistant.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_regional_transport.py --run --hours 2
```

Roughly 1–2 hours, with a two-hour invocation cap and monthly resume. The
fixed eight-case protocol has four exact saved-year upwind controls, then
four FCT candidates on the same local-matched humidity and weather, with both
bulk/lower-interface cloud rules in California/Iberia. Each candidate repeats
3–6 forcing cycles to check settling. It is not a parameter search or new
weather catalogue. Repeat the same command after a budget stop; inspect a
`needs_diagnosis` failure before changing anything.

The prepared short-step extrapolation is 46–92 candidate minutes plus controls
and overhead. Compare coastal winter and reference-arid summer errors, with
the original physical/temperature guards. All frozen sources and parent
evidence remain unchanged; the fantasy atlas and NOAA pause remain unchanged.
See [protocol, tests, timing and decision rules](v10_regional_transport.md).

## Previous: coupled transport candidate passes its first numerical comparisons

16 October 2026. Implemented a bounded, conservative flux correction with one
shared face coefficient for theta/vapor. Seventy fixed manufactured comparisons
complete in seconds; 79 focused checks pass. Fourteen upwind controls match
the saved parent exactly, and source/evidence fingerprints remain unchanged.

False contact rain falls 26–54% across the tested grids. Smooth-profile error
falls 87% at 32 cells and 98% at 256. These are known-answer numerical tests,
not regional rainfall scores. In the unchanged closed circulation the candidate
instead makes more rain, showing why numerical accuracy cannot be selected
by preferring less precipitation. Candidate rain remains sensitive to grid
and time step; the spatial curve is not monotonic.

Next: support open boundaries with identical prescribed incoming heat/vapor
fluxes, test larger multidimensional manufactured meshes, check compatibility
with the frozen donor-cell cloud dose, and measure cost before preparing a
small user-run regional comparison. No annual command is ready yet. The
candidate currently rejects open boundaries rather than silently dropping
their sources. Atlas unchanged; NOAA stays paused.
See [implementation/results/next gates](v10_flux_transport.md) and
[saved audit/figures](../output/v10_flux_transport_lab/audit.md).

## Previous: manufactured process lab reveals transport/phase sensitivity

16 October 2026. Implemented and completed 166 manufactured parcel paths,
18 closed two-column circulations and ten periodic transport controls;
6.02 seconds of numerical work, with no regional integration or download.
79 focused checks pass. Frozen sources and the completed geometry evidence
identities remain unchanged.

Splitting the same thermodynamic ascent adds about 0.5–4% condensate in the
wet cases rather than suppressing it. Finite dry-air exchange can suppress
clouds, while saturated warm/cold exchange can create them. In the separate
vertical-grid toy, the unmixed-minus-bulk gain shrinks 0.2504 → 0.00165mm
from 4 → 256 layers, but total rain still changes substantially. Convergence
cannot be inferred from the small gap.

The exact inviscid periodic contact should make zero rain. First-order upwind
mixing instead makes 0.4053g/kg at 32 cells, falling to 0.1441g/kg at 256;
an exact-shift control makes zero. This is a demonstrated numerical cloud
artifact in a manufactured case, not an attribution of regional error.

Next: compare a less diffusive conservative transport option with the frozen
upwind rule, using passive-tracer, saturated-contact and closed-column tests.
Keep cloud physics and forcing fixed. Require coupled heat/moisture transport,
positivity, explicit ledgers and spatial/time checks before preparing any
regional batch. Coherent winter storm forcing remains a separate problem.
No new long job is needed yet. Atlas unchanged; NOAA remains paused.
See [laboratory findings and next development gates](v10_cloud_lab.md) and
[saved audit/figures](../output/v10_cloud_lab/audit.md).

## Previous: cloud-path diagnosis verified; use a common-forcing process laboratory

16 October 2026. All four cloud-geometry replays finish and reproduce their
saved physical climates exactly; 5.78 integration minutes. Source/config/file
integrity, physical water/energy/thermal ledgers, monthly actual input, layer
rain, diagnostic subsets and pressure weights verify. Twenty-five focused
tests cover the new reviewer and its dependencies.

In matched-input Iberia-domain arid summer land, parcel rain accounts for
93.1% of all rain; 94.9% of parcel rain first saturates beyond the layer face
and 99.8% enters pre-step environmental RH below 70%. The late-onset fraction
on the winter coast is 47.3%. California shows 95.7% versus 26.4%, but its
arid summer land is already too dry. These are diagnostic signatures, not a
valid instruction to delete all late-onset rain or a measured evaporation law.

Next: small manufactured column/ridge comparisons of vertical cloud paths
and conservative cloudy/environment mixing, following the KiD-style common-
forcing methodology. Preserve the current operator as an exact regression
control. Coherent winter storm forcing is a separate larger investigation.
There is no new long run to launch before that process design is prepared.
See [verified replay analysis](../output/v10_cloud_geometry_review/review.md),
[completed protocol](v10_cloud_geometry.md) and [model research](model_precipitation_research_20261016.md).
Atlas unchanged; NOAA remains paused.

## Research while cloud-geometry replays run

16 October 2026. A primary-source comparison of SPEEDY, Isca, ExoPlaSim,
SpeedyWeather, IFS, WRF/Kessler, CAM6/CLUBB and the Smith–Barstad orographic
model is saved in [the model research review](model_precipitation_research_20261016.md).
It changes no running source or protocol. Some useful idealized GCMs also
precipitate condensate immediately; missing cloud storage alone is not a
demonstrated explanation of our winter drought.

The review recommends two connected directions: a KiD-style common-forcing
cloud-process laboratory, and a separately audited source of coherent winter
weather. Diagnostic rain evaporation is a smaller proposal than cloud/rain
stores with horizontal drift. Neither should be selected before interpreting
the current geometry evidence. Coarse-GCM weather requires subdaily pressure,
wind, T and q plus compatible mass/heat/water mapping; existing monthly atlas
comparison output is not already such a driver. No new long command is added.
The current exact replays continue unchanged; NOAA remains paused.

## Current: local humidity helps summer placement; diagnose the cloud path

16 October 2026. All 12 humidity cases / 28 saved years verify; four exact
controls, all settling and temperature guards, annual budgets, signed thermal
ledgers, monthly incoming water and independently rebuilt summaries pass.
The batch used 34.68 integration minutes.

At the same monthly gross input, the lower-interface Iberia-domain case reduces
reference-arid summer rain 86.35 → 73.08mm (57.17mm target), and cell/month
summer MAE 16.05 → 14.14mm. Its coastal winter rain only changes 59.10 →
61.28mm (439.18mm target). California changes 91.83 → 92.96mm (534.82mm target)
and reference-Mediterranean cells still arid worsen 75.4% → 78.3%.
The small declared mechanism screen is not an atlas-selection rule. See the
[verified seasonal/Köppen review](../output/v10_spatial_humidity_review/review.md)
and [completed result with original protocol](v10_spatial_humidity.md).

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_geometry.py --run
```

Four exact final-year passive diagnostic replays, estimated 10–25 minutes;
45-minute invocation cap, monthly resume. Record actual upward vapor and rain
by interface, first saturation relative to the true layer face, and pre-step
environmental RH/T. This separates inadequate moist ascent from dependence
on the unmixed finite cloud path before another physics change. It is not a
new parameter sweep. See [diagnostic interpretation/limitations](v10_cloud_geometry.md).
The user runs the four annual replays. NOAA remains paused; atlas unchanged.
174 focused tests and four independent 60-second input probes pass. Exact
physical replay and monthly restart also pass on tiny manufactured climates.
The prepared source and frozen parent identities are unchanged.

## Previous handoff: source replay verified; local humidity comparison ready

16 October 2026. All four source replays finish and reproduce the physical
climates exactly. Source stores/rain, physical budgets, monthly inputs and
recomputed summaries verify. The misplaced reference-arid summer rain is
74.9% boundary-labelled, 16.9% local ocean evaporation and 8.2% land recycling
in Iberia; California's boundary fraction is 90.7%. These are last-vapor-entry
labels, not causal fractions or soil ancestry. This deprioritizes soil
evaporation as the principal direct water source.

The prototype applies offshore-mean humidity on every boundary, including
continental inflow. A cached forcing comparison now uses native local humidity,
with both absolute and monthly-gross-input-matched variants. At fixed summer
input, Iberia land-boundary-cell vapor falls 15.1%; marine-cell input increases.
This is a contrast to test, not an annual rainfall result or a proven cause.

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_spatial_humidity.py --run
```

Four exact final-year controls plus eight fixed local-humidity climates;
estimated 45–75 minutes, 90-minute invocation cap and monthly resume. Winds,
cloud operators, terrain and nominal storm timing remain fixed. Compare both
bulk and lower-interface cloud rules to separate input and closure effects.
162 focused tests, two complete forcing tables and twelve independent
<=60-second probes pass. No real annual case was launched by the assistant.
NOAA stays paused; atlas unchanged. See [source results](../output/v10_cloud_source_review/review.md)
and [new protocol and decision criteria](v10_spatial_humidity.md).

## Previous handoff: cloud-bound review complete; four source replays ready

16 October 2026. All 52 cloud-bound jobs complete; 192 saved years and 438.7
integration minutes. Four exact physical controls, summaries, all annual water/
energy/thermal balances, settling and monthly gross boundary input verify.
The lower-interface coastal winter gains repeat across four catalogues:
+31.9–39.5mm California and +25.3–27.9mm Iberia. Halving the permitted time
step changes coastal winter rain by at most 0.173mm across twelve checks.
This does not establish vertical/horizontal grid convergence or a validated
cloud scheme.

Rain placement remains the main obstacle. In the seed67 Iberia-domain case,
reference-Mediterranean and other land improve monthly MAE by contributions
of +0.700/+0.738mm, but reference-arid land offsets -1.337mm. Its summer rain
increases to 86.3mm against 57.2mm reference while winter stays 19.8mm against
103.5mm. The domain includes North Africa. Keep the fantasy atlas.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_sources.py --run
```

Four exact final-year diagnostic replays, estimated 10–25 minutes, 45-minute
cap and monthly resume. Passive labels identify last atmospheric vapor entry;
cloud condensate inherits the ascending donor's labels before bulk mixing.
This distinguishes boundary/ocean supply from local land recycling without
changing the climate or attributing original soil ancestry. 153 focused tests
and four independent <=60-second source probes pass. No annual replay was
launched by the assistant. See [completed maps/results](../output/v10_cloud_review/review.md)
and [source-replay protocol](v10_cloud_sources_replay.md). NOAA remains paused.

Season clarification: the frozen rainfall response uses October–March winter
and April–September summer. Earlier prose calling response winter November–
April was incorrect; no completed response values changed.

## Previous handoff: short cloud-mixing screen and conditional overnight test

16 October 2026. The user asks for small decisive checks followed by useful
overnight work without a 4am handoff. The afternoon run stopped normally at
51 jobs. All four original diagnostics and the first four catalogues' 32
climates are available; stronger lifting helps but drought remains severe.
Its remaining catalogue cases stay resumable.

Saved winter-stage analysis, a manufactured mixing counterexample and 24
independent <=60-second regional steps motivate a new subgrid cloud-bound
test. The current model homogenizes incoming air before requiring grid-average
saturation. Separately represented moist ascending parcels can condense when
that mean-cell rule does not. This is not yet an annual rainfall fix.

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_cloud_mixing.py --run --stage overnight --hours 7
```

The first four exact controls/four regional screens take roughly 20–40 minutes.
Expansion proceeds only if the declared settling, thermal and minimum-effect
screen passes; otherwise it stops. The fixed 52-job design includes four
catalogues, a lower-interface-only primary test, an all-interface sensitivity
and half-step numerical controls. Estimate 5–8 hours with a seven-hour
invocation cap and monthly resume. For a short pause after the screen, use
`--stage smoke --hours 0.75`, then resume with the overnight command.
139 focused tests and 24 independent short probes pass. No real annual run
was launched by the assistant. Keep the atlas; NOAA remains paused. See
[protocol, assumptions and safeguards](v10_cloud_mixing.md) and the
[three inexpensive audits](../output/v10_cloud_mixing_audit/audit.md).

## Previous handoff: user-requested three-to-four-hour batch ready

15 October 2026. The user requested 3–4 hours of unattended work. The new
batch puts the four exact passive delivery replays first, then repeats four
fixed forcing contrasts across eight synthetic catalogues and two regions,
with final-year diagnostics of each original/steady and lift16/linked pair.
100 jobs total: four reference replays, 64 climates and 32 new-weather replays.

```sh
caffeinate -i .venv/bin/python -u scripts/afternoon_v10_delivery.py --run --hours 3.75
```

Estimated 3–4 hours, stopping near a 3-hour-45-minute invocation budget if
unfinished, with monthly checkpoints and same-command resume. This extends
the previous short handoff to the requested duration; it does not optimize
parameters or pick a favourable weather seed. The diagnostics remain first.
Matched incoming water applies within each catalogue, not across catalogues.
Some catalogues have been used previously: this is synthetic-weather
sensitivity, not untouched validation or observed climate uncertainty.
Sources and evidence are frozen. Atlas unchanged; NOAA remains paused.
113 focused tests, two prepared forcing calendars and 24 independent
<=60-second regional probes pass. No annual climate was launched by the
assistant. See the [batch protocol](v10_afternoon_delivery.md).

## Previous handoff: event experiment reviewed; four diagnostic replays ready

15 October 2026. Twelve cases / 48 cycles complete in 31.03 saved integration
minutes. All settle, both held-boundary controls pass and physical/thermal/
monthly gross-input ledgers verify. Stronger intermittent lifting improves
coastal winter rainfall, but the linked-moisture case reaches only 70.2 / 35.5 mm
against 534.8 / 439.2 observed. Only 8.7% / 4.6% of the original deficit is
closed; these Earth pilots still replace most Mediterranean cells with arid
climate. Keep the current fantasy atlas.

The new rainfall increment forms mostly in the middle layers; moisture
timing adds only a small, nonuniform benefit. Ocean evaporation and land
recycling also change despite matched boundary input. About 98% of vapor
input still leaves without precipitation. Do not run another amplitude or
seed sweep before measuring the actual coastal delivery/condensation stages.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_delivery.py --run
```

Four single-year diagnostic replays from the saved preceding-year states,
estimated 5–15 minutes, 45-minute cap and monthly resume. Require exact
original physical arrays and ledgers. Collect regional vapor budgets,
joint RH/ascent distributions and instantaneous condensation opportunities
before/after prescribed heating. These are passive diagnostics, not the
rainfall of a changed climate; opportunity sums may recount the same vapor.
No warm-up, parameter fitting, NOAA access or atlas update.

One hundred focused tests and twelve independent <=60-second regional
operator checks pass; no real annual replay was launched by the assistant.
See [results and maps](../output/v10_event_review/review.md) and the
[diagnostic protocol and interpretation](v10_delivery_replay.md).

## Historical handoff: matched-import event experiment ready

15 October 2026. The [event-forcing implementation and preflight](v10_event_forcing_plan.md)
are complete. User-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run
```

Twelve cases; about 45–75 minutes, two-hour invocation cap, monthly restart
and same-command resume. Two held-boundary controls run first and must
reproduce the completed climates within declared small tolerances before
the ten mechanism cases. Each region tests original/strengthened convergence
fluctuations with steady/event-linked/shifted boundary moisture.

The monthly mean dry circulation and actual gross incoming vapor per month
are controlled. A forcing-only power audit caught that the proposed fourfold
convergence fluctuation changed winter coastal positive ascent by only 1%.
Sixteen is the smallest of fixed tested doses 1/4/16/32/64 meeting a declared
10% contrast requirement in both regions: +12.2% / +16.2%. No new climate
result or rain target was used to choose that dose; observed amplitudes and
complete frontal thermal structure remain unverified.

Ninety focused tests, two tiny manufactured checks, full forcing-calendar
invariants and 48 independent <=60-second regional probes pass. The original
fourfold preflight and source snapshot are preserved. Prepared final tables
are in `output/v10_event_preflight_lift16/`. The assistant started no real
seasonal simulation. NOAA stays paused; atlas and frozen parents are unchanged.

## Completed: five-layer review; event-forcing design

15 October 2026. Twelve cases / 48 cycles complete in 31.85 saved integration
minutes; all settle. Saved source/input/evidence identities, physical budgets,
summaries and signed annual thermal changes verify. The lower California MAE
does not solve the user's Mediterranean problem: its column-matched control
changes reference Mediterranean land becoming arid from 46.4% to 56.5%, while
spatial California/Iberia remain 94.2% / 98.0%. All of the California uniform
net MAE gain comes from correcting previously over-wet cells; already dry
cells worsen in aggregate. Keep the current fantasy atlas.

Matched column concentration still imports 9.6–15.3% more boundary water.
About 97–98% of the upper-humidity-induced rainfall increment forms in the
unobserved highest layer. Do not select a climate on MAE or the broad screen.

A cached three-hour flow audit constructs 23,360 independent circulations,
without advancing climate states. Both spatial monthly backgrounds imply
coastal winter descent. Current synthetic events reverse descent at only
2.08% / 1.94% of sampled coastal cell/time pairs. This supports investigating
episodic ascent and associated moisture rather than another seed/frequency
or blanket-humidity sweep; it is not a measured real-storm parameter choice.

Next is the [bounded event-forcing design](v10_event_forcing_plan.md): control
monthly dry circulation and **gross vapor influx**, separate lifting from
humidity timing, and require coastal winter wetting rather than just lower
average error. Implementation/preflight are not yet complete; there is no new
seasonal command to run. Leave the NOAA audit paused rather than repeatedly
retrying 429 responses. The assistant ran saved-field/forcing analysis and
39 fast tests only.

See the [completed review and maps](../output/v10_split_review/review.md) and
[storm-ascent audit](../output/v10_split_review/storm_ascent.md). The entries
below retain earlier handoffs and their original commands/estimates.

## Historical handoff: source-water review complete; five-layer ready

15 October 2026. All twenty source/weather cases settle after four cycles;
112.1 saved integration minutes. Full annual evidence, summaries and source
balances verify, and all four seed-41 physical controls reproduce exactly.
Spatial-wind rain remains only 37.7–40.9 mm in California and 21.2–23.1 mm in
Iberia, versus 401.8/424.2 mm reference. The five catalogues produce the same
failure. About 98–99% of boundary/ocean vapor is exported in those cases.

Cached no-storm flow checks do not show a huge projection-induced reversal.
A separate vertical-profile audit finds that one top cell represents only
26.7–27.4% of native-reference moisture in its 608–300 hPa portion. A proposed
split at 300 hPa improves that profile-only measure to 94.5–95.5%, without
extrapolating unobserved upper humidity or claiming a rainfall result.

The separate five-layer structural test is implemented with matched coarse
circulation, zero/retained-RH upper humidity and an old-column-water control:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_split_column.py --run
```

Twelve new cases; four saved controls reused. Estimated 45–75 minutes,
90-minute invocation budget and monthly resume. Sixty focused tests and
forty-eight independent <=60-second regional probes pass, including exact
four-layer reproduction, plus 730 boundary-only queries verifying the
column-water match. No NOAA access, parameter optimization or atlas update.
No seasonal run was started by the assistant. See
[completed source review](v10_water_sources_review.md) and
[new experiment and decision protocol](v10_split_column.md).

## Completed: bounded water-source / paired-weather batch

15 October 2026. User requests 2–3 hours of unattended work. The six-hourly
NOAA audit is rate-limited, so the prepared batch uses cached inputs only:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_water_sources.py --run
```

Twenty fixed cases: two regions × two background wind modes × five paired
storm seeds. Add passive last-vapor-source tracers; preserve the corrected
climate physics and settings. Trace boundary/ocean/land/initial water into
coastal/interior winter rain and gross export. Reproduce seed 41's saved
physical arrays exactly; report all paired seed results without selecting a
winner. Roughly 2–3 hours, 2.5-hour invocation budget and monthly resume.
No downloads, parameter tuning or atlas update.

Thirty-nine focused tests and sixteen independent actual-state <=60-second
operator probes pass. No seasonal run was launched by the assistant. See
[design, interpretation and run instructions](v10_water_sources.md). Retry the
short reference-weather audit separately later; these synthetic catalogues
do not measure real moisture/wind covariance.

## Completed heat comparison; separate weather-reference audit

15 October 2026. All four pressure-based heat-transport cases settle in four
cycles (16.67 saved minutes), but the rain problem remains. California uniform
MAE improves 41.66 → 40.07 mm and still loses to zero rain; the other three
cases worsen slightly. Spatial-wind annual rain is only 9.9% / 5.2% of reference
in California / Iberia. The updated Köppen maps show 84.1% / 98.5% of reference
Mediterranean cells becoming arid in those cases. Preserve the demonstrated
dry-law repair without promoting the climates. The atlas stays unchanged.

Next user-run command:

```sh
.venv/bin/python -u scripts/audit_v10_weather.py --fetch --run
```

Reference download and analysis only, no climate simulation. Measure six-hourly
moisture/wind covariance and high-transport humidity/temperature composites
before preparing another forcing experiment or parameter sweep. Four fixed
January/July 1990/2000 windows, two marine boxes, 56 sequential bounded requests;
normally several minutes, 30-minute invocation budget, 96 MB cache cap and
same-command resume. NOAA returned HTTP 429 to one tiny metadata probe, so live
array format remains unverified. The command stops on rate limits without an
immediate retry and preserves completed cache entries.

Fifteen offline tests, actual-grid native-point selection and frozen-source/
completed-evidence checks pass. No seasonal simulation or live weather batch
was launched by the assistant. See [results, maps and decision protocol](v10_weather_audit.md).
The entries below preserve earlier stages and their then-next commands.

## Completed spatial-wind check — 15 October 2026

All four cases settle in four cycles; sixteen saved cycles take 13.70 minutes.
None qualifies. At humidity 1.0 California gets only 47.3/401.8 mm reference
annual rain, Iberia 21.6/424.2. California lower MAE accompanies severe drying;
Iberia MAE worsens. Spatial mean winds alone are insufficient. The atlas stays
unchanged.

Independent dry-law probes identify a concrete thermal-transport issue: passive
approximate-MSE transport can cool dry air along a tilted constant-pressure
surface, although the dry-adiabatic pressure law requires no temperature change.
A separate dry-theta transport step passes that limit and a pressure-transfer
test, with explicit diagnosed energy exchange with the prescribed circulation.
Large old horizontal/vertical heat terms also include cancelling mass-divergence
contributions; their separate magnitude cannot establish drought causality.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_pressure_thermo.py --run
```

Four fixed cases at humidity 1.0: uniform/spatial winds in both regions, each
paired with its completed old-MSE control. Change thermal transport only; record
prescribed-flow work rather than claim a new closed total-energy system with no
momentum model. Estimated 15–30 minutes, one-hour cap and monthly resume.
No search, download or atlas export. 76 focused tests, four manufactured
dry-law probes, four saved-state operator comparisons and twelve independent
actual-input checks pass. No seasonal run was launched by the assistant. See
[results, physical law, energy policy and protocol](v10_pressure_thermodynamics.md).

## Completed mass-projection/storm check — 15 October 2026

Ten cases / 35 cycles complete in 32.37 minutes. All settle; six pass broad
screens, but no California case beats the zero-rain monthly error baseline.
Increasing storms improves minimum-wet coverage and Iberian rain amount while
worsening California monthly error (41.66 → 48.94 mm at humidity 1.0). In
California the coast is too dry while the interior is already too wet; Iberia
is dry in both. No atlas update is warranted.

The first saved-field paired response table now separates coastal/interior
winter/summer changes. Storms are more selective for coastal winter rain than
the humidity multiplier, but the tested increases still worsen monthly skill.
Response secants, full rain-change maps and a response-plane figure are saved
in `output/v10_storm_review/`. This applies the strategy's response-analysis
stage without claiming global feasibility, history matching or independent
validation from cells/settling years.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_spatial_wind.py --run
```

Four fixed spatial-background-wind cases, humidity 0.8/1.0 in each region.
Reuse all four completed uniform-wind baselines; retain the same storms,
humidity boundary profiles and thermodynamics. Cached local pressure-level
winds are sampled bilinearly to avoid native-grid steps, then mass-projected.
Estimated 15–30 minutes, one-hour cap and monthly resume. No search, download
or atlas publication. 65 focused tests and twelve independent single-step
input checks pass. No regional seasonal simulation was launched by the
assistant. See [measured responses and new protocol](v10_spatial_wind.md).

## Completed coordinate check — 15 October 2026

Four cases / sixteen cycles complete in 10.00 minutes; all settle and none
qualifies. The hybrid path removes high-level mountain rain, but California
receives only 43% of reference annual rain and Iberia 21%. Coverage remains
52% / 59% under the minimum-wetting screen. Monthly MAE falls from 64.26 to
30.26 mm and 37.71 to 32.84; this does not establish realistic rainfall.

The next isolated change converts prescribed velocities to actual face-mass
fluxes and projects them to stationary column continuity. Using consistent
face velocities, California's no-storm middle-layer maximum changes from
27.90 to 9.71 m/s, Iberia's from 13.37 to 6.44. The earlier 54–56 m/s figure
used a different flux/cell-mass diagnostic. Local reference wind errors remain
substantial, so rainfall gains alone cannot validate this circulation.

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_storm_delivery.py --run
```

Ten fixed cases: a projected-flow anchor and reference-humidity zero/one/four/
eight-storm controls in both regions. The old rate-one events are retained
exactly; added storms form nested catalogues. Roughly 20–45 minutes, with a
90-minute invocation cap and monthly resume. No search, download or atlas
publication. If frequent storms still leave dry gaps or create excessive peaks,
investigate spatial circulation/front forcing before tuning more parameters.
See [completed result, projection and decision protocol](v10_storm_delivery.md).
55 focused tests and 28 independent single-step input probes pass. No regional
seasonal simulation was started by the assistant; old fingerprints are intact.
The entries below preserve the earlier research history.

## Completed upper-air check — 15 October 2026

Both corrected-target cases settle in four cycles, but rainfall MAE worsens:
California 71.12 → 75.48 mm/month; Iberia 40.90 → 41.42. Highest-layer rain is
46.4% / 39.4% of scored-land totals. Horizontal thermal transport cools there
on average while vertical exchange warms. A dry one-step ridge test isolates
upper cooling caused by the prescribed terrain-following path with no rain,
relaxation or vertical exchange. This is a kinematic hypothesis, not proof that
terrain-following coordinates are invalid.

Next controlled user-run comparison:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_coordinates.py --run
```

Four 60 km cases: reference-aligned sigma and hybrid paths in both regions,
fixed setting/seed, three to six cycles, roughly 20–40 minutes with a one-hour
cap and monthly resume. Record the changed implied winds alongside rainfall;
do not promote by rain/thermal score alone. No search or atlas publication.
See [result, geometry protocol and limitations](v10_coordinate_check.md).
43 focused tests and eight frozen-input operator checks pass. No new regional
seasonal simulation was started by the assistant; old fingerprints are intact.

## Completed overnight result — 15 October 2026

The four-layer batch completed 215 cases / 944 repeated years in 6.15 hours;
none passes the original rules. All settle and budgets close. Finer grids were
correctly skipped. Saved-state review also finds an important thermal-screen
issue: the old targets copy surface anomalies into upper air. Direct local
pressure-level comparisons give much smaller upper errors; rainfall still
fails, including skill against a zero-rain error baseline. All three numerical
stops reproduce as legal tiny clock remainders, without climate integration.

Next bounded experiment, with completed baselines reused:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_upper_air.py --run
```

Two 60 km cases, about 10–20 minutes from comparable timings, one-hour cap.
Only the upper-air targets change; record layer rain and signed thermal-process
contributions. No search or atlas publication. See
[results, limitations and the new protocol](v10_overnight_review.md).
Thirty focused tests and four frozen-state operator checks pass; no new regional
seasonal run was started by the assistant. Historical source fingerprints and
acceptance rules are unchanged. Earlier entries below retain their history.

Updated 14 October 2026 after the storm-balance check and the user's choice of
Mediterranean protection.
The user runs all seasonal simulations and calibrations. Assistant work is
analysis, implementation and fast tests.

## Latest direction: investigate a larger physics change

The user requested new avenues beyond local parameter changes. The recommended
next development is an isolated v10 water/atmospheric-mass and transient-storm
prototype, accompanied by real-Earth rainfall tests and explicit larger-scale
geography hypotheses. A fast saved-state audit identifies nonconservative local
mixing and a large mismatch between concentration advection and a flux-divergence
operator under the current winds. This is structural evidence, not a prediction
that a one-line correction improves precipitation.

The user authorized this direction. The first isolated two-layer water/storm
engine and bounded Earth rainfall pilot are now implemented; see
[implementation, assumptions and run protocol](v10_prototype.md) and
[the research review](new_physics_avenues_20261014.md). Temperature is observed
forcing in this first stage, so only rainfall is evaluated. Twenty-five new
tests and the relevant previous audit/policy tests pass (49 total). No production
source was changed and no regional simulation or calibration was started.

The user has now completed the first pilot. All twelve years pass water-budget
checks, but rainfall accuracy is poor: California storms give 1,469 mm/year
versus 402 observed; Iberia gives 1,013 versus 424. Storms worsen California's
monthly MAE; Iberia's mean-only control is still settling in soil water. Extreme
mountain rain is present even without storms. Frozen-state diagnosis points to
the missing thermal feedback from condensation as well as terrain circulation.

The subsequent heat/terrain experiment has also completed. All eight cases fail
at least one screen; California's settled heat-with-drag case doubles rainfall
MAE. All four original controls now settle after one extra unchanged Iberia year.
Saved-field analysis identifies direct exchange across a 7.12 km representative
height gap as a suspect terrain-circulation approximation. Temperature screens
also rely on unverified surface-to-level offsets. Inspect independent atmospheric
profiles before extending/tuning these cases. See [results and reference-audit
protocol](v10_forcing_audit.md).

The atmospheric-reference audit is complete. It confirms excessive lower-boundary
moisture, missing southward summer winds and incorrect thermal-profile targets.
The user requested an 8–10 hour overnight task. A separate four-layer experiment
now tests reference-constrained forcing and shallow terrain return, with broad
parameter coverage, weather transfer and numerical refinement. See
[the frozen overnight protocol](v10_overnight_20261015.md).

Next user-run command:

```sh
caffeinate -i .venv/bin/python -u scripts/overnight_v10.py --run --hours 9
```

Thirteen matched controls in both regions and 144 California settings at 120 km;
then 60 km weather/transfer checks and 30/15 km refinement for qualifying settings.
Maximum 322 cases, three to six cycles each, constrained by a nine-hour invocation
budget. Monthly checkpoints and source/input/evidence hashes support resuming.
The prepared manifest and 52 frozen-input operator checks are saved; the assistant
started no seasonal simulation. Ninety-eight relevant fast tests pass. The batch
uses existing inputs and does not publish an observation-forced Earth prototype
to the atlas. Original V10, the heat experiment, the atmospheric audit and
production V9 fingerprints are preserved.
The existing storm continuation below remains a frozen V9 comparison. The user's
selected 5% Mediterranean rule and dry-zone protections persist.

## Completed sweep and atlas

All 64 planned settings were processed: 63 usable screening results and one
numerical failure. Both shortlisted proposals completed development worlds
1/302/301 and failed the per-world cold-dry protection limit. Other screened
proposals have not all had those checks; this is not a proof of infeasibility.

The atlas was rebuilt from the original broad seasonal anchor with strict
convergence and two warm-up years. Overall agreement is 48.87%; Mediterranean
dry land remains 11.59%. The finer-grid anchor converged after 6.31 hours, giving
48.90% overall and 13.00% Mediterranean dry land. Its +1.41-point dry-area drift
violates the declared zero-increase guard, so the atlas uses the coarse result.
Live metadata, binary bounds and images were verified. The requested <=5%
Mediterranean dry-area target remains unmet.

Fresh world 402 now also converges with a larger bounded temperature iteration
allowance and unchanged physics/tolerances: 54.36% overall, 3.11% dry Mediterranean
land, 72.95% cold-dry agreement. Both designated fresh anchor worlds have usable
strict-convergence results. Original simulation sources and fingerprinted inputs
are unchanged. See the [retry and next batch](storm_balance_checks.md),
[overnight final review](overnight_final_20261014.md) and
[first-session report](overnight_results_20261014.md).

## 1. Numerical retry complete

The user-run world-402 retry took 77 minutes. All 75 seasonal solves pass the
strict temperature, moisture and linear checks. The difficult date in the first
year needed 1,872 temperature/wind iterations across three damping stages,
exceeding the previous 1,344 total cap. The same date also converges in both later
years. Results and histories are in `output/overnight_validation_retry/`.
The original failed case and atlas publication record are preserved.

## 2. Continue the storm proposal under the user-selected Mediterranean rule

```sh
caffeinate -i .venv/bin/python -u scripts/continue_storm_balance.py --run
```

The fixed `storm_asym_low` proposal completed worlds 301 and 302. Both numerical
checks pass. On 301, Mediterranean dry land changes 3.67% → 3.61% and cold-dry
agreement 69.16% → 69.31%. On 302, dry land changes 1.54% → 1.87% and cold-dry
agreement 53.54% → 58.90%. The original zero-increase rule rejected that +0.33-point
Mediterranean change, stopping after about 57 minutes and preserving the atlas.

The user explicitly chose to allow up to 5% dry Mediterranean land on worlds
already below that target, while requiring improvement on the worst world.
New per-world dry-area limit: max(anchor, 5%). Worst-world dry area must strictly
improve on the development set and all five checked worlds. Keep cold-dry loss
<=2 points, hot-dry loss <=3, overall loss <=1 and Cs-area loss <=2 points.
The original experiment and its rejection remain preserved; the policy change
is declared separately before further runs.

Reuse both completed candidate worlds and all five anchors. The continuation
starts with world 1 using two warm-up years, then its one-year settling check,
then candidate validation worlds 401/402 if each stage passes. At most four new
sequential simulations, roughly 2–4 hours if all stages execute; difficult cases
may take longer. Every pair uses matching numerics. The proposal's physics and
classifier are unchanged. Validation worlds already examined are validation
evidence, not a newly untouched final test set.

Publish a coarse-grid atlas only after all declared checks pass, from captured
world-1 fields without another simulation. Record the unchecked finer grid and
denser seasonal calendar and preserve the previous atlas. Results go in
`output/storm_balance_target_checks/`. Default is read-only; completed cases
resume. Twenty-seven focused fast tests pass. No real seasonal simulation or
atlas export was launched by the assistant. See the
[completed result, rainfall attribution and revised protocol](storm_balance_results.md).

## 3. Remaining numerical and physical work

The finer grid no longer shows an overall agreement collapse. Approximate
matched Mediterranean footprints have median annual-rain change -3.47 mm and
95th-percentile absolute temperature change 0.068°C. A small classification
difference remains; coastline/terrain sampling also changes. Another fine run
should answer a new selection question before spending six hours on it.

Temporal sampling remains 25 dates/year; no separate 73-date check was completed.
Warm-up sufficiency was established for the two tested starting profiles, not
every possible candidate. Weak swamp fit and forest display conflicts remain
separate rule/physics issues. Changing display labels cannot be described as
an improvement in rainfall.

The user's requested end-of-sweep atlas update is complete. Further atlas
changes require a converged, adequately settled candidate with its checks and
limitations recorded. No new seasonal solve or export was run by the assistant.
