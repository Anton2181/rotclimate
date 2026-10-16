# Overnight sweep and atlas update

Prepared 14 October 2026 at the user's request. The user runs the batch; no
seasonal simulation or calibration was launched by the assistant.

From the project directory:

```sh
caffeinate -i .venv/bin/python -u scripts/overnight_mediterranean.py --run --hours 8 --workers 3
```

Keep the terminal open. The command inhibits idle sleep while it runs. Eight
hours is a soft work budget: stop starting new cases before the stage deadline,
but finish cases already running and the atlas export. It may finish sooner or
run beyond eight hours. An hour is reserved for atlas generation. The batch
records unfinished trials rather than claiming the full sweep completed.

## Work included

1. Check one versus two full warm-up years for the broad seasonal anchor and
   the current 5% narrower shortlist on world 1. Each seasonal solve retains
   strict convergence checks. Compare monthly/seasonal continuous fields.
2. Plan 64 bounded trial settings over 24 climate controls: 48 coordinate
   endpoints, then 16 joint Latin-hypercube probes with a fixed seed. Reuse
   identical settings, including an endpoint identical to the incumbent.
   The eight-step warm-up screen only proposes candidates; it never qualifies
   a fit for publication. The two exact saved short-warm-up anchors are reused.
3. Check the two best screened proposals on development surroundings 1/302/301
   with two full warm-up years, alongside the unchanged broad anchor. Reject
   a candidate if any world violates a declared limit. Record individual solver
   failures and continue independent jobs.
4. Choose one candidate from the development worlds, check its warm-up
   sensitivity, then validate it against the anchor on surroundings 401/402.
   Do not repeatedly try new candidates against these validation worlds. If
   the candidate fails or checks are incomplete, fall back to the verified
   broad anchor. These are small validation sets, not a statistical spin verdict.
5. If time permits before the atlas reserve, run matched finer-grid world 1
   checks of the chosen fit and anchor. Use the finer result only if both
   converge, dry-zone constraints pass and the same guards do not flag drift
   from the coarse chosen result. Otherwise export the verified coarse model;
   record this explicitly. Seasonal sampling remains 25 steps/year: this batch
   does not claim a separate 73-step temporal-resolution verification.
6. Build the atlas from a captured completed simulation, without rerunning its
   climate. Update all current climate layers, packed arrays, climographs,
   year animations, comparison and context images. Preserve the interactive
   page and its similarity controls, and historical experiment illustrations.

The 24 controls cover storm exchange/rate/width/seasonality/asymmetry/reach,
Hadley and ITCZ positions/migration, mean wind and monsoon controls, recycling,
ocean evaporation, rain-out rate/humidity threshold, upslope/instability rain,
wet-ground cooling and land/sea temperature offsets. Exact named bounds are
in `scripts/overnight_mediterranean.py:SPACE` and the saved experiment manifest.
The starting value is inside every range. Map size, terrain, spin, orientation,
planetary geometry, surrounding-land fractions and classifier rules stay fixed.
This is a broad bounded sweep of climate physics, not an exhaustive global
search over all possible worlds.

## Selection and validation

On each checked world, relative to its matched broad anchor:

- Cold-dry agreement may fall by at most 2 percentage points.
- Hot-dry agreement may fall by at most 3 points.
- Overall agreement may fall by at most 1 point.
- Mediterranean dry area must not increase.
- Mediterranean Cs area may fall by at most 2 points.

Rank complete passing candidates by worst-world Mediterranean dry area, then
mean overall agreement. Report separately whether the <=5% dry-area goal is met
on every required checked world. Do not silently loosen a guard to publish a
better-looking average. Relative protection of a weak anchor does not prove a
good absolute fit for that zone.

Warm-up development tolerances compare one and two years on the same world:
95th-percentile temperature changes <=0.1°C; annual/seasonal rain changes <=5 mm;
monthly rain changes <=1 mm. Apply them across painted land and separately to
Mediterranean/cold-dry/hot-dry regions. These are declared development tolerances,
not a universal convergence theorem. A chosen simulation must converge and pass
its warm-up check before it can become an atlas. If no settled, converged
captured simulation exists, preserve the current atlas and report the failed
checks. Extra CPU time cannot make an invalid result publishable.

## Resuming and outputs

Results live in `output/overnight_mediterranean/`:

- `summary.md`: readable outcome, per-world comparisons, actual atlas fit and
  changed controls; `summary.json` contains the full state.
- `run.log`: progress and numerical failure summaries.
- `experiment.json`: profiles, bounds, seeds, guards and source/input fingerprint.
- `cases/`: independent results, convergence histories and exact cropped fields;
  full simulations and transport archives are retained only where needed.
- `atlas_export.log`: atlas build details.
- `selected_params.json`: parameters of the published atlas simulation.
- `atlas_previous_.../`: complete previous atlas data for rollback.
- `atlas_publication.json`: publication status, selected fit and backup path.

Repeat the same command to resume matching completed cases. Cached failures are
excluded without wasting the night repeating them. Deferred cases can run on a
later invocation. A changed source/input manifest requires a new `--out` so old
results are not silently mixed with a different experiment. Avoid editing model
or source-map files while this batch is running.

The atlas is built in a separate staging directory. Verify image files,
numerical metadata and binary-array bounds, then rename the previous data into
the backup and replace it. A failed replacement rename rolls back immediately.
If the normal 3x image export fails, retry export at source image resolution
using the same verified climate, without rerunning any climate simulations.
Model-grid resolution and exported image scale are reported separately.

Validation: 41 fast checks pass, including complete fake batch runs, failed fresh
validation fallback, failed warm-up preservation, hard per-world guards, budget
deferral, cache provenance/deduplication, incomplete binary rejection and atlas
replacement rollback. Fake orchestration/calendar solves never run real climate.
Only the read-only plan, saved-result analysis and fast tests were run here.
