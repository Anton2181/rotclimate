# Mediterranean screening and next bounded calibration

13 October 2026. Analysis of user-run simulations only. No atlas change.

## Paired fresh-surroundings results

All four runs match the current model-source fingerprint and exact expected
parameters. All enabled temperature, moisture-equation and linear-solver checks
pass. The stronger temperature damping was needed on two steps of broad-pattern
world 301. These checks do not establish grid or seasonal spin-up independence.

The painted map, terrain, planetary geometry and label rules are identical;
only the procedural surroundings seed and the stated storm parameters differ.
The focused candidate narrows the storm width by 20% and raises exchange by 25%.
Both use seasonal contrast 0.7. Percentages below are fractions of the relevant
painted land area; dry Mediterranean includes both desert and steppe.

| Metric | Broad 301 | Focused 301 | Broad 302 | Focused 302 |
|---|---:|---:|---:|---:|
| Overall strict agreement | 54.20% | 51.24% | 50.43% | 48.65% |
| Mediterranean dry area | 3.97% | 0.07% | 1.67% | 0.00% |
| Mediterranean Cs area | 59.12% | 63.63% | 70.51% | 73.61% |
| Mediterranean strict recall | 55.34% | 56.95% | 65.23% | 63.76% |
| Cold-dry strict recall | 69.62% | 47.42% | 54.04% | 38.37% |
| Hot-dry strict recall | 64.61% | 62.84% | 34.61% | 46.96% |

Across these two surroundings, the broad pattern averages 52.32% agreement,
2.82% dry Mediterranean land, and 61.83% cold-dry recall. Focused averages
49.95%, 0.03%, and 42.90%, respectively. Focused costs 22.19 and 15.67 percentage
points of cold-dry recall for only 1.60 and -1.47 points of Mediterranean recall.
Its hot-dry effect changes sign between worlds. Keep the broad seasonal profile
as the development anchor, consistent with the user's priority to protect the
cold-dry zone. Do not promote either candidate to the atlas yet.

Two paired worlds are a screen, not a statistical robustness verdict. Historical
world 1 still has 12.02% dry Mediterranean land under the broad profile, despite
the two fresh-world values being below 5%. The cold-dry and especially hot-dry
variation also shows substantial sensitivity to uncertain surroundings. Seeds
301/302 now guide development and must not be called untouched final tests.

## What caused the focused candidate's cold-dry damage?

Offline comparison of exactly the same cells finds:

| Cold-dry cells | World 301 | World 302 |
|---|---:|---:|
| Total painted cells | 1,978 | 1,978 |
| Lost correct label | 487 | 374 |
| Newly correct | 48 | 64 |
| Lost cells now classified Csa | 452 | 351 |
| Median paired annual-rain increase on lost cells | 80.14 mm | 64.13 mm |
| Median paired summer-rain increase on lost cells | 28.72 mm | 23.87 mm |
| Median paired mean-temperature change on lost cells | -0.034°C | -0.051°C |

The model makes these places wetter and moves them across the aridity boundary.
This is physical-field damage, not merely a forest display-policy conflict.
The combined width/rate experiment does not identify which of its two changes
caused the wetting. Do not infer either knob's individual effect from it.
Machine-readable attribution is in
`output/mediterranean_validation/cold_dry_damage.json`.

## Next finite experiment

`scripts/tune_mediterranean.py` prepares three fixed one-parameter probes around
the broad seasonal anchor, with all geometry and numerical settings fixed:

| Probe | Changed setting | Value |
|---|---|---:|
| Drier exchange | Exchange rate reduced 10% | 0.898496/day |
| Stronger seasons | Seasonal contrast 0.7 → 0.8 | 0.8 |
| Slightly narrower | Storm width reduced 5% | 5.779318° |

These are bounded hypotheses, not known improvements or a continuous optimizer.
The earlier 20%/25% combined change is excluded. Each probe first runs on the
known difficult Mediterranean world 1, then world 302 (weak hot-dry result), then
301. It is compared with the identical-world broad anchor after each run.
Reject it immediately on any of the following per-world changes:

- Cold-dry recall falls by more than 2 percentage points.
- Hot-dry recall falls by more than 3 points.
- Overall strict agreement falls by more than 1 point.
- Mediterranean dry area increases.
- Mediterranean Cs area falls by more than 2 points.

This is rejection of an already violated hard constraint, not early rejection
based on an average score estimate. A better result elsewhere cannot rescue it.
These are visible development limits chosen to implement the user's preference,
not scientific confidence bounds. Relative protection also does not turn a low
baseline recall, such as hot-dry world 302, into an acceptable final fit.

Only probes passing all three worlds can be suggested. Rank these by their
worst-world Mediterranean dry area, then mean overall agreement; require an
improvement over the anchor. Report separately whether dry Mediterranean land
is at most 5% on **every** world. The saved patch audit also tracks cured,
persistent and newly dry Mediterranean cells, so a shifting patch remains visible.

Reuse the two completed fresh-world anchors. Reverify anchor world 1 under the
current strict retry settings instead of silently reusing an older result with
different settings and no source fingerprint. This requires at most ten new
simulations: one anchor plus three probes on three worlds. Early constraint
rejection reduces the budget; completed exact matching new runs resume.
Allow roughly 35–100 minutes at recent speeds, with extra time possible for
difficult temperature retries. All runs are sequential and persist individually.

```sh
.venv/bin/python scripts/tune_mediterranean.py --run
```

Without `--run` this only reads saved anchors and prints the plan. It never
changes production parameter files or the atlas. If no probe qualifies, retain
the broad anchor and stop this search; investigate the surroundings/transport
sensitivity before expanding the parameter search. A qualifying result still
needs independent surroundings, resolution and periodic spin-up checks before
atlas selection. The user runs every long task.

Validation: 31 focused tests passed, including per-world rejection, incomplete
candidate exclusion, stale cache protection, convergence enforcement and the
read-only default. Only the plan and fast tests were run by the assistant.
