# World 402 resolved; next coastal-storm proposal

Update: the original storm check stopped on world 302 under its zero-increase
rule. The user has since selected a 5% target rule for already-good worlds;
see [the results and continuation](storm_balance_results.md). The protocol
below records the original experiment, which remains preserved.

14 October 2026. The user ran the simulation. Assistant work was saved-field
analysis, preparation of the next batch and fast tests. No new simulation,
calibration or atlas export was launched by the assistant.

## Numerical retry result

The world-402 anchor converged with two full warm-up years and the larger
temperature iteration allowance. All physical parameters, damping fractions,
calendar and strict convergence tolerances were preserved.

| Measure | Result |
|---|---:|
| Elapsed time | 77.0 minutes |
| Overall strict agreement | 54.36% |
| Mediterranean dry land | 3.11% |
| Mediterranean Cs land | 57.78% |
| Cold-dry agreement | 72.95% |
| Hot-dry agreement | 62.75% |
| Failed temperature/linear/moisture checks | 0 |

The difficult date is day 153.3. It needed temperature retries on seasonal
steps 11, 36 and 61, corresponding to that date in each of the three years.
The first occurrence used 384 iterations at damping 0.25, 768 at 0.125 and 720
at 0.0625: 1,872 total, exceeding the old 1,344 total allowance. The next two
occurrences needed 1,793 iterations each. Each accepted solve passed the
unchanged 0.05°C undamped-update test; the largest final accepted update was
0.049997°C. All linear solves and scaled local moisture-equation checks passed.

The larger cap changes the numerical trajectory and permits longer damping
stages. This demonstrates a usable converged result for this case, not a proof
of uniqueness of the coupled solution or a reason to loosen the tolerance.
The original failed case remains unscored and preserved. Both designated fresh
anchor worlds now have usable strict-convergence results; this does not turn
them into untouched statistical tests or establish every numerical limit.

The atlas retains the earlier published world-1 climate: 48.87% strict agreement
and 11.59% dry Mediterranean land. Its metadata records that earlier publication;
the additional world-402 evidence is saved separately under
`output/overnight_validation_retry/`. Its results are absolute scores, not a
climate improvement over an otherwise identical valid world-402 baseline.

## Physical lead: reduce the coastal storm imbalance

The third-ranked overnight screening proposal, `storm_asym_low`, changes coastal
storm asymmetry from 0.2600 to 0.1 and retains the shortlist's 5% narrower storm
width, 5.7793° versus the broad anchor's 6.0835°. No other physics changes.

Matched world-1 screens, both with eight warm-up steps:

| Measure | Broad anchor | Proposal |
|---|---:|---:|
| Mediterranean dry land | 12.02% | 9.22% |
| Mediterranean Cs land | 37.24% | 43.05% |
| Cold-dry agreement | 68.30% | 73.36% |
| Hot-dry agreement | 57.16% | 63.24% |
| Overall strict agreement | 48.90% | 50.98% |

Median paired rainfall changes across each painted zone are consistent with the
desired regional response in this screen: Mediterranean annual +9.38 mm,
winter +21.15 mm and summer -11.47 mm; cold-dry annual -21.28 mm and hot-dry
annual -36.95 mm. These are regional medians of cellwise differences, not a
conservative global water budget. Temperature changes are small. The settings
still need full warm-up and multi-world checks; screening is not acceptance.

## User-run batch

```sh
caffeinate -i .venv/bin/python -u scripts/check_storm_balance.py --run
```

The default without `--run` prints a read-only plan. The batch reuses the five
matching, converged anchor simulations with verified source, parameter,
seasonal-calendar and warm-up provenance. Each candidate/anchor pair uses the
same numerical parameters: the original 192-iteration first-stage allowance on
worlds 301/302/1/401 and the successful 384 allowance on world 402.

At most six new sequential simulations:

1. Check the fixed proposal on development world 301 first. This world rejected
   both previous proposals. Stop immediately on numerical or zone-limit failure.
2. If it passes, check worlds 302 and 1, with two full warm-up years. Capture the
   world-1 result for a possible atlas export without another climate run.
3. If all development worlds pass and the declared ranking improves, compare
   one versus two warm-up years on world 1 using continuous monthly and seasonal
   fields and the existing settling limits.
4. If settling passes, check the proposal against the saved anchors on validation
   worlds 401 and 402. These worlds have already been examined; do not describe
   them as a new untouched test set.
5. Publish a coarse-grid atlas only if every preceding check passes. Preserve
   the previous atlas with the existing verified staging/rollback mechanism.

The per-world guards are unchanged: cold-dry loss <=2 points, hot-dry loss <=3,
overall loss <=1, no Mediterranean dry-area increase and Cs-area loss <=2.
Report separately whether dry Mediterranean land is <=5% on all five worlds.
Passing relative guards does not establish good absolute climate everywhere.

Allow roughly 3–6 hours if all stages execute; difficult retries may take longer.
Failures stop the batch early. Exact matching completed cases resume. A complete
batch is not rerun or republished when the same command is repeated. A changed
model/input or experiment manifest is rejected. An export failure can retry
from the captured climate without repeating the simulations.

Results and progress are under `output/storm_balance_checks/`: `summary.md`,
`comparison.json`, `run.log`, per-case diagnostics/fields and a captured world-1
result. An accepted publication also saves `selected_params.json`, publication
metadata and an atlas backup. The atlas is retained on rejection, failed
numerics or failed seasonal settling.

This batch does not repeat the six-hour finer-grid run or check denser seasonal
sampling. Any publication explicitly records that the candidate's finer grid
and 73-date calendar have not been checked. It is a guarded coarse-grid
development update, not a final resolution-independent climate verdict.

Sixteen focused tests pass, including read-only planning, matching per-world
numerics, warm-up/provenance rejection, source/output protection, early rejection,
failed numerical exclusion, conditional publication and completed-run reuse.
Fake orchestration never launches a real climate simulation or touches the
live atlas. The actual read-only plan verified all five reusable controls;
the original simulation source/input fingerprint remains unchanged.
