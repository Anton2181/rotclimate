# Completed overnight sweep and atlas review

Follow-up: the world-402 retry has now converged. See the
[retry results and next coastal-storm checks](storm_balance_checks.md).
The failed-validation status below describes the original overnight batch.

14 October 2026. Analysis of the user's completed, resumed batch. The assistant
ran saved-result analysis and fast tests only. No new seasonal simulation,
calibration or atlas export was launched here.

## Outcome

The resumed batch finished at 18:04 after 10.29 hours, including a 6.31-hour finer
grid simulation. It processed all 64 planned sweep settings across 24 controls:
63 yielded usable screening results and one failed temperature convergence.
There are no deferred settings. The 79 successful case records include anchors,
validation and identical-setting aliases; they are not 79 independent trials.
Two case records failed in total, including fresh anchor world 402.

Only the two best passing screening proposals received all three development
world checks. Both failed the declared cold-dry protection limit. The selected
fit is therefore the original broad seasonal anchor. This does not establish that
every screened setting fails, or that an acceptable fit is impossible.

The atlas was rebuilt and published from the converged coarse anchor with two
full warm-up years. Verified the live numerical metadata, packed-array bounds
and current image files. The original model/runner/input fingerprint still
matches the experiment. The previous atlas is preserved at
`output/overnight_mediterranean/atlas_previous_20261014_180402/`.

Atlas model-grid strict agreement remains **48.87%**, with **11.59%** of painted
Mediterranean land classified dry. The mean fuzzy rule score is a different
metric. Exported images are 3x source resolution; the simulation grid remains
downsample 8. The requested <=5% dry Mediterranean target is not met.

## The finer grid converges, with modest regional drift

Same anchor physics, world 1, 25 seasonal dates/year and two warm-up years:

| Measure | Coarse grid (8) | Finer grid (4) |
|---|---:|---:|
| Overall strict agreement | 48.87% | 48.90% |
| Mediterranean dry area | 11.59% | 13.00% |
| Mediterranean Cs area | 37.27% | 35.92% |
| Cold-dry agreement | 68.05% | 69.41% |
| Hot-dry agreement | 56.27% | 56.74% |
| Temperature/wind iterations, all 75 steps | 1,920 | 1,957 |
| Moisture iterations, all 75 steps | 2,745 | 3,032 |
| Largest linear-solver sweep count | 196 | 661 |
| Elapsed simulation time | 37.4 minutes | 378.3 minutes |

Both runs pass temperature, moisture and linear convergence on every seasonal
step, including warm-up. Neither needed temperature damping retries. The finer
run's long duration was not caused by repeatedly exhausting the temperature
iteration cap. Its grid has roughly four times as many cells; individual linear
solves require more work. The recorded maximum sweep count supports this
explanation, but is not a full CPU profile or a mean sweep count.

The single fine/coarse publication guard failure is **+1.41 percentage points
of dry Mediterranean area**. Under the predeclared zero-increase rule it is
excluded from publication, while retained as usable diagnostic evidence. The
other regional guards pass. This is a modest residual grid dependence rather
than the earlier collapse in overall agreement. It does not prove convergence
to a grid-independent limit or verify temporal sampling.

An approximate continuous-field comparison aggregates each 2x2 fine-cell block
onto its coarse footprint, keeping only all-land, valid blocks painted entirely
the same target zone on both grids. For the 2,858 retained Mediterranean blocks:

- Median paired annual-temperature change: -0.002°C; absolute 95th percentile
  change: 0.068°C.
- Median paired annual-rain change: -3.47 mm; absolute 95th percentile change:
  27.22 mm.
- Median paired winter rain: -2.64 mm; summer rain: -0.46 mm.

The continuous differences are small over most of this region. Shoreline,
terrain and target sampling also change with resolution, so do not attribute
the entire 1.41-point classification difference to one numerical mechanism.

## Parameter changes improve Mediterranean land but can damage cold-dry land

The declared cold-dry loss limit remains 2 points per world. Two-year warm-up
checks now complete for both shortlisted proposals:

| Proposal | World | Anchor → trial Mediterranean dry | Anchor → trial cold-dry agreement |
|---|---:|---:|---:|
| Storm width 4.8° | 1 | 11.59% → 6.71% | 68.05% → 67.44% |
| Storm width 4.8° | 302 | 1.54% → 0.84% | 53.54% → 56.17% |
| Storm width 4.8° | 301 | 3.67% → 1.90% | 69.16% → 65.57% |
| Seasonal exchange contrast 0.85 | 1 | 11.59% → 7.82% | 68.05% → 68.25% |
| Seasonal exchange contrast 0.85 | 302 | 1.54% → 0.77% | 53.54% → 49.65% |
| Seasonal exchange contrast 0.85 | 301 | 3.67% → 2.54% | 69.16% → 65.52% |

The first proposal fails on world 301 by losing 3.59 points of cold-dry
agreement. The second fails on worlds 302 and 301, losing 3.89 and 3.64 points.
The combined random probes did not produce a new passing screen finalist.
Warm-up sensitivity remains tiny for the two starting profiles, as documented
in the first-session report; initialization is not the main explanation for
the remaining dry strip in those tested configurations.

## Fresh surroundings: one valid result and one numerical failure

Fresh anchor world 401 converged: overall agreement 50.27%, Mediterranean dry
2.27%, cold-dry agreement 54.80%, hot-dry agreement 33.43%. These absolute dry-zone
scores remain weak; protecting a baseline is not proof that its climate is good.

World 402 stopped at seasonal step 11, day 153.3, during its first warm-up year.
The temperature/wind stages used 192, 384 and 768 iterations with damping 0.25,
0.125 and 0.0625. The final undamped update was 0.08081°C across the full
interior and 0.05400°C in-map, both above the 0.05°C stopping threshold. Even
the final stage's minimum update, 0.07648°C, never passed. Its late history
oscillates with a shrinking envelope, which motivates testing a larger bounded
iteration allowance; it does not guarantee eventual convergence.

World 402 has no valid climate score. The published atlas correctly records
`fresh_checks_complete: false`. The batch being complete does not mean its
independent validation is complete.

## Next action: one numerical retry, then the remaining physical lead

Prepared `scripts/retry_overnight_validation.py`. Its default prints a read-only
plan. The user can run:

```sh
caffeinate -i .venv/bin/python -u scripts/retry_overnight_validation.py --run
```

This performs one coarse-grid world-402 simulation with 50 warm-up steps and 25
scored steps. Only `t_iters` changes, 192 → 384, giving stage caps
384/768/1536. All physical parameters, damping fractions, calendar and strict
temperature/linear/moisture tolerances are retained. It saves separate fields,
transport diagnostics, histories and provenance under
`output/overnight_validation_retry/`, resumes exact matching results and
preserves the overnight outputs and atlas. A failure remains unscored.
No promise of success is implied by the larger finite cap.

Eight focused tests pass, covering strict parameter preservation, two-year
warm-up, read-only planning, source/input mismatch rejection, original-output
protection, failed-result reporting, cache reuse and bounded damping behavior.
The actual read-only plan was also checked against the completed experiment;
the simulation was not launched by the assistant.

After resolving that numerical check, the next physical proposal to examine is
the already screened `storm_asym_low`, ranked third. Against its matching
eight-step-warm-up anchor, it changes Mediterranean dry area 12.02% → 9.22%,
cold-dry agreement 68.30% → 73.36%, hot-dry agreement 57.16% → 63.24%, and overall
agreement 48.90% → 50.98%. It uses coastal storm asymmetry 0.1 together with the
shortlist's 5% narrower storm width (5.7793° versus the atlas's 6.0835°).
These screening gains are provisional: it still needs matched two-year warm-up,
development-world and subsequent validation checks. No further physical fit is
selected or published from this single-world screen.
