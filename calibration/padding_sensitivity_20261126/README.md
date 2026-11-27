# Fixed r58 padding-sensitivity experiment

**Superseded before any integration:** the scientific design is carried
forward unchanged under `calibration/padding_sensitivity_parallel_20261127/`.
Only scheduling, output namespace and private prepared-cache reuse change.
The former waiting queue was stopped, and this original runner is blocked
by `superseded_before_run.json` to prevent a second nine-run budget. The
original plan and preparation/protocol evidence remain preserved below as
historical context; use the replacement's explicit commands for execution.

This study tests the regional-domain sensitivity identified in
`calibration/convergence_boundary_audit_20261126/findings.md`. It changes
padding only, with **no physical coefficient change or candidate selection**.
The frozen reference is r58, even if another profile is adopted later.

The fixed budget is nine integration attempts: Somalia (`s_2n_43e`), Sahara
(`u_21n_21e`) and North India, each at 1,100, 2,220 and 4,012 km padding.
The latter values add exactly 20 and 52 cells to each side at 56 km spacing.
Using round 2,200/4,000 km margins would shift the grid and confound the test.
The scored footprint and observations must remain unchanged.

Historical context: `calibration/map_edge_20261124/README.md` already reports
strong domain sensitivity at r52 and almost unchanged Somali rainfall under
1,100→2,200 km padding. Larger maps worsened the pooled result and did not
stabilize it at 3,300 km. The separate
`calibration/edge_moisture_20261124/findings.md` retains rejected r53 edge-humidity
changes. This study does not supersede those outcomes or move deployment's
calibration margin. It tests current r58 with exact integer-cell alignment
and explicit instantaneous import/drying traces; the older observations and
scores must not be pooled with its new matched-footprint results. An observed
lateral-humidity boundary would be a separate methodological change, not an
authorized substitute in this padding-only diagnostic.

Preparation copies 89 physical source files, seeded caches and two numerical
helpers to `output/padding_sensitivity_20261126/model/`. These are regular
private files, not writable symlinks or hard links. Derived Earth cases are
built there, leaving the active W18c source and shared caches unchanged.

Preparation command (no climate integrations):

```sh
nice -n 10 .venv/bin/python -u -I scripts/padding_sensitivity.py
```

The preparation reviewer checks all nine footprints against the original
observations, source/cache digests and storage isolation. It also invokes
the actual `--run` CLI while W18c is active, requiring refusal before any
attempt receipt is created. Its preparation-only record is not climate
validation or a completed experiment result.

The physical study is deferred until W18c has a terminal campaign status
**and its supervisor has exited**. Then run:

```sh
nice -n 10 .venv/bin/python -u -I scripts/padding_sensitivity.py --run
```

An operational queue, `scripts/run_climate_followups.py`, can perform that
handoff automatically. It waits for a terminal W18c state and for both its
supervisor and benchmark workers to exit, then runs this unchanged nine-case
study and its reviewer. It uses a singleton lock and frozen dependency hashes.
Its dry check is:

```sh
.venv/bin/python -I scripts/run_climate_followups.py --check-only
```

When the queue is live, let it start the study; do not launch a second copy.
Its state/logs are under `output/climate_followups_20261127/`. It stops for
agent review if W18c disappears without finishing, a padding attempt is
interrupted, a dependency changes or a command fails. Failed commands are not
automatically retried. Preserve the failure state and record a recovery
review before resuming. Seventeen tests cover these transitions and the live
dry check starts no children.

This queue changes no scientific budget, parameter, candidate selection or
gate. It never applies the pending source patch, adopts a climate profile,
commits results or publishes an atlas. The padding diagnostic may run after
W18c exits while its finalist awaits agent review: it uses its own frozen r58
copy and exposed development cases. Inspect the resulting figure and review
the finalist separately before any source/application or adoption decision.

All three 1,100 km controls run first. They must reproduce strict current-runtime
r58 monthly temperature/rain arrays exactly at float32; Somalia and Sahara
also reproduce E/W/u/v. Every numerical criterion is unchanged. A failed
control closes the study before expanded-domain runs. Larger-domain failures
are retained, and no failed/incomplete cases are pooled into a full score.
An existing attempt without a result blocks automatic repetition and requires
a recorded recovery review; do not rerun an interrupted integration blindly.

The runner saves actual instantaneous gain, sink, W/P and scored monthly
T/P/E/W/u/v. After it finishes, independently review the fixed-footprint
differences and render the results. Do not call the largest domain truth if
changes remain substantial, choose a padding by rainfall accuracy, or infer
isolated convergence causality: larger domains change several operators.
No fine/sealed region use, atlas build or climate adoption is authorized by
this diagnostic plan. Any proposed physical candidate needs a separate
prospective experiment and all current gates.

The post-run reviewer is ready:

```sh
.venv/bin/python -I scripts/review_padding_sensitivity.py
```

It refuses to review preparation-only inputs. Once results exist, it checks
the original control arrays independently, exact scored observations/calendar,
integer cell translations, source/certificate/file hashes, and monthly P/W
against independently integrated instantaneous traces. All three padding
pairs are compared in each region. Changes retain signed means, monthly
absolute/RMS/max differences and annual RMS/max differences, so opposite
seasonal errors cannot disappear in an annual average. Import and drying
use instantaneous rate×water before averaging. Failures and unavailable pairs
remain explicit, and no aggregate score or best padding is produced.

Fifteen synthetic-data tests cover those calculations, seasonal cancellation,
rate/water covariance, moved cells, changed observations/calendar, missing
cases and archive reproduction. The reviewer readiness receipt is only a
software check, not a physical result. Inspect its actual figure and write
findings after the study runs. The larger domains still use regional
projection and transport assumptions; increasing padding does not turn them
into a whole-planet simulation.

Seventeen unit tests cover translated footprints, changed observations,
terrain/coordinates, missing/extra cells, the campaign interlock and private
copy isolation. Existing r58 qualification and historical replay caveats
remain in force; old scalar-score mismatches are not reinterpreted here.

Preparation is complete and independently reviewed: 219 private regular files,
45,612 exact static-value checks, all nine footprints, and a live CLI refusal
while W18c is active. Scored cells remain 24 in Somalia, 25 in Sahara and 494
in North India. Somalia/Sahara grids are 45×45, 85×85 and 149×149; North India
grids are 59×67, 99×107 and 163×171. Coordinates match within the declared
1e-10 degree tolerance. `preparation_review.json` records zero integrations
and no attempt receipts; it is not a physical result or a validation pass.
