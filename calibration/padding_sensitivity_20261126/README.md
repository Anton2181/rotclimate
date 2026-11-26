# Fixed r58 padding-sensitivity experiment

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
