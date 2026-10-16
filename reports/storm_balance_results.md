# Storm balance result and user-selected Mediterranean protection

14 October 2026. The user completed the simulations and selected the revised
Mediterranean protection rule. Assistant work was saved-field analysis, a
resumable continuation and fast tests. No simulation or atlas export was run
by the assistant.

## Completed result under the original rule

The fixed coastal-storm proposal completed two converged development-world runs
in about 57 minutes. The original batch then rejected it on world 302 and
preserved the atlas. It did not run the main atlas world, the candidate warm-up
pair or candidate validation worlds.

| Measure | World 301, anchor → trial | World 302, anchor → trial |
|---|---:|---:|
| Mediterranean dry land | 3.67% → 3.61% | 1.54% → 1.87% |
| Cold-dry agreement | 69.16% → 69.31% | 53.54% → 58.90% |
| Hot-dry agreement | 64.22% → 62.35% | 34.31% → 38.33% |
| Overall strict agreement | 54.14% → 53.95% | 50.32% → 51.12% |

All temperature/wind, moisture and linear checks passed, including two full
warm-up years. World 301 passes every original regional guard. World 302 fails
only the zero-increase Mediterranean dry-area rule: +0.334 percentage points.
Cold-dry, hot-dry, overall and Mediterranean Cs-area protections pass on both.
These are usable physical results, not numerical failures.

## Rainfall attribution: a regional trade-off, not just label noise

On world 302, the painted Mediterranean region has 2,994 valid model cells.
Dry cells increase from 46 to 56: 16 newly dry cells, six cured cells and 40
persistent dry cells. All are steppe classifications; no desert classification
appears in this comparison.

For the 16 newly dry cells, median paired annual rainfall falls 33.48 mm,
with winter -11.80 mm and summer -22.42 mm. Mean annual temperature rises only
0.042°C. None crosses the winter-70% classification boundary. Rain loss moves
them across the aridity threshold: this deterioration is physical in the model
and should not be dismissed as harmless classifier noise.

For the six cured cells, median annual rain also falls, by 24.01 mm. All cross
the winter-70% boundary; the model's annual dryness threshold drops by about
140 mm, changing their labels to Mediterranean. Their classification gain is
not an increase in annual water supply.

Across the whole Mediterranean region, median paired changes are annual rain
+17.58 mm, winter +25.03 mm and summer -5.51 mm. Thus an overall winter-rain
improvement can coexist with a locally drier strip. These are medians of
cellwise differences; they are not a conservative global moisture budget.

World 301 shows the same regional tension: 28 newly dry and 30 cured cells,
giving a net reduction of two dry cells. The new dry cells lose a median
37.72 mm of annual rainfall. Only looking at the net dry-area percentage would
hide where the rain changed.

## Revised rule explicitly selected by the user

The user chose:

> Allow up to 5% dry Mediterranean land on worlds already below that target,
> while requiring improvement on the worst world.

The continuation declares this rule before further simulations:

- Per-world Mediterranean dry-area limit: `max(anchor dry share, 0.05)`.
- Worst-world Mediterranean dry area must strictly decrease, on the complete
  development set and again on all five checked worlds.
- Other limits remain unchanged: cold-dry loss <=2 points, hot-dry loss <=3,
  overall loss <=1 and Mediterranean Cs-area loss <=2 points per world.

Both completed runs pass the revised rule. This does not yet qualify the fit:
the main atlas world still needs its full warm-up comparison. The original
zero-increase rejection remains unchanged in `output/storm_balance_checks/`.
The new policy and the user's preference are stored separately in the new
experiment manifest and, if published, atlas provenance.

## Continue without repeating the completed simulations

```sh
caffeinate -i .venv/bin/python -u scripts/continue_storm_balance.py --run
```

Default without `--run` is read-only. Reuse the exact, verified world-301/302
candidate runs and all five converged anchors. At most four new simulations:

1. Main atlas world 1 with two full warm-up years; capture the completed climate.
2. World 1 with one warm-up year, to check seasonal settling against the first run.
3. Candidate validation world 401, if preceding checks pass.
4. Candidate validation world 402, if preceding checks pass.

Every candidate/anchor pair retains matching numerical settings, including the
successful larger temperature allowance on world 402. No physics or classifier
changes are introduced. The fixed proposal still changes only storm asymmetry
and storm width relative to the broad anchor.

The batch stops on a failed numerical, protected-zone, settling or worst-world
improvement check. If all pass, export the coarse-grid atlas from the captured
world-1 climate, with the previous atlas backed up. Report separately whether
all worlds reach <=5% dry Mediterranean land; acceptance of an improvement is
not a claim that the final goal has been met. Candidate finer-grid and denser
seasonal-sampling checks remain explicitly untested.

Allow roughly 2–4 hours if all remaining stages run; stiff cases can take longer.
Exact matching completed cases resume. Results are in
`output/storm_balance_target_checks/`, including `summary.md`, `comparison.json`,
the policy/provenance manifest, per-case fields/histories and publication records
if accepted. Neither prior experiment is overwritten or republished on resume.

Validation: 27 focused fast tests pass. They cover the exact target-rule boundary,
unchanged regional protections and original policy, genuine worst-world
improvement, reuse of the old wrapper's case identities, early stopping,
settling/validation gates, conditional atlas publication, manifest protection
and completed-run reuse. The real read-only plan verified both reused candidate
cases and all five controls, and confirmed that the original model/input source
fingerprint is unchanged. No new long task was launched by the assistant.
