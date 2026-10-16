# Diagnose moist ascent and the finite cloud path

## Completed — 16 October 2026

All four exact final-year replays finish in 5.78 saved integration minutes.
The independent [saved-only review](../output/v10_cloud_geometry_review/review.md)
verifies physical reproduction, source/config/evidence hashes, monthly input,
annual water/energy/thermal balances, layer rainfall, subsets, fixed pressure
weights and reconstructed summaries. Maximum annual water error is
3.4e-12mm and energy error 9.6e-6J/m². The new review and existing diagnostic
paths pass 25 focused tests, including deliberately rehashed corruptions.

The matched-input Iberia-domain arid summer case has 68.08mm parcel rain out
of 73.08mm total. Of the parcel rain, 94.9% first saturates beyond the true
layer face on the path to the receiving midpoint, and 99.8% enters pre-step
environmental RH below 70%. The late-onset fraction is 47.3% for winter coastal
parcel rain. In the interior summer mask, 97.6% of parcel rain is generated at
the third tested interface; its mean rain-weighted midpoint gap is 214hPa.
The domain includes North Africa. These are fractions of actual rain, not
fractions of excess/error or directly measured evaporation potential.

California shows the same contrast: matched-input late-onset fractions 95.7%
in reference-arid summer land versus 26.4% on the winter coast. Its arid
summer land is already too dry against the reference, so suppressing this
signature everywhere would be an inappropriate target. Both regional winter
deficits remain unchanged by these passive replays.

The next development priority is a controlled vertical-path and conservative
mixing comparison in small manufactured columns/ridge slices. Above-face
cloud onset can be physically legitimate; simply clipping all such rain is
not a valid refinement experiment. Pre-step dry environmental air does not
by itself measure entrainment, in-cloud humidity or evaporation. A separate
circulation/weather investigation remains warranted for winter drought.
See the [cross-model research review and KiD precedent](model_precipitation_research_20261016.md).
No new seasonal job or atlas change follows automatically from these results.

The original prepared protocol below is retained unchanged.

## Original protocol

16 October 2026. The [completed local-humidity comparison](v10_spatial_humidity.md)
improves Iberia-domain summer rain placement modestly, but leaves coastal
winter rain at 61.28mm versus 439.18mm reference. California remains at
92.96mm versus 534.82mm. The dominant winter deficit survives both local
humidity and the deliberately unmixed lower-interface cloud bound. Keep the
fantasy atlas and the completed experiment sources/evidence.

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_geometry.py --run
```

Four exact final-year diagnostic replays, estimated 10–25 minutes, with a
45-minute invocation cap and monthly checkpoints. Use the same command to
resume. California and Iberia each replay the uniform and local-matched
lower-interface case from the exact state preceding their saved final year.
No warm-up, new candidate climate, calibration, download or atlas publication.
Every physical array and original ledger must reproduce except elapsed time.
The assistant does not launch the four annual replays.

## What this isolates

The cloud bound cools ascending donor air from one layer midpoint to the next,
then removes liquid condensate before mixing. This is a large finite path,
not a resolved cloud trajectory. Previous half-time-step checks were stable,
but did not test vertical refinement, entrainment, cloud memory or rain
evaporation. Source tags established last vapor entry; they did not explain
why that water condenses in the wrong season/location.

The passive collector records monthly cell/interface fields for the first
three ascending interfaces:

1. Upward dry mass, carried vapor, and the exact actual parcel condensate.
2. The subset of actual parcel rain whose relaxed dry-adiabatic path is still
   unsaturated at the **true layer face** and reaches saturation only farther
   into the receiving layer. No face-based alternate precipitation is applied.
3. The subset entering a cell with pre-step environmental RH below 70%.
4. Rain-weighted midpoint pressure gaps and vapor-weighted donor RH.
5. Actual parcel rain from a lifted parcel colder than the pre-step recipient.
   This is a temperature contrast, not a virtual-temperature buoyancy or CAPE
   calculation, nor a justification for suppressing mechanically forced ascent.
6. Full actual rain by layer, reconciling every cell/month and the original
   scored-land parcel ledger independently.

The tiny existing relaxation shift is inverted to a dry potential-temperature
path so that its receiving midpoint exactly reproduces the frozen parcel
calculation. It does not infer observed cloud bases or implement a moist
adiabatic path. [Unidata's rising-parcel example](https://unidata.github.io/MetPy/latest/examples/calculations/Mountain_Problem.html)
distinguishes dry ascent to first saturation from later moist ascent. That
provides context for this diagnostic, not validation of the prototype's
instant liquid fallout or a claim that the layer midpoint method is wrong.

Summaries cover coast, interior, reference-Mediterranean, reference-arid,
other reference land, scored land and the full domain. Winter is October–March;
summer April–September. Reference regimes are determined from the same
WorldClim rain/surface temperature as previous tests. The Iberia domain includes
North Africa; regime masks and coastal-distance masks must not be summed
together. One reused synthetic catalogue (67) remains a mechanism test.

## How results guide the next change

Compare winter coastal/Mediterranean transport and conversion separately from
arid summer rain. A large fraction of late-path, dry-recipient rain would
justify a controlled vertical-refinement or entrainment experiment, each
separate from humidity changes. It would not justify clipping rain at the
face or using painted/reference zone IDs in physical rules.

If very little moist air ascends in winter, another condensation coefficient
cannot establish a missing storm route. Revisit prescribed circulation,
vertical motion and transient thermal/moisture structure. Monthly cached
reference fields do not establish observed storm covariance; the six-hourly
NOAA audit remains paused. If appreciable vapor ascends but rarely condenses,
inspect donor RH/pressure path and thermal structure before adding water.

Gross upward-vapor sums can revisit cells/interfaces. Their ratio to parcel
rain is a conditional transfer diagnostic, **not unique atmospheric supply,
a rainfall ceiling, or the rainfall of a different climate**. Dry receiving
air does not by itself quantify entrainment or evaporation. All diagnostics
are measured on the unchanged realized trajectory.

No new parameter sweep or production change follows automatically. A new
physical proposal must preserve accounting, isolate its mechanism, and test
winter rain and dry-interior placement together. The user runs annual jobs.

## Readiness and provenance

The new collector and runner have tests for an independently constructed
above-face saturation case, nonmutation, rain/subset reconciliation, exact
physical replay, monthly restart, completed-case reuse, evidence corruption,
budget resume, stale preparation, protected output and read-only default.
174 focused tests pass (16.54 seconds), including the previous accounting,
forcing, source-tag, cloud, numerical and Köppen checks. Four independent
real-input probes of 60 simulated seconds each pass exact parcel reconstruction,
physical nonmutation and water/energy/thermal checks. They are not seasonal
simulations or annual rainfall evidence. No real annual output was launched.

Prepared protocol/checks: `output/v10_cloud_geometry_preflight/manifest.json`.
User outputs: `output/v10_cloud_geometry/{progress.json,state.json,summary.md,cases/}`.
Frozen parent source:
`97afe7ac31cf7e9d9409f9d75b87a81314ec78a21a5c7c696717b38f4c2e662e`.
New prepared source:
`f4e611b7479154cfc0b7391bab9fe9e437de6d6d0e51f5082ac52b8e6da9634c`.
Both current and frozen-parent identities were checked after preparation.
Existing inputs, calendars, prior results and atlas assets remain unchanged.
