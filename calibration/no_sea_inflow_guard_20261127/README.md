# Guard warm-sea relaxation when the domain has no modeled water cell

The old nearest-sea EDT provides an outside-domain index on an all-land
grid. Reading SST at that index can create a warm-sea relaxation source or
drying target from land. The new guard enables this branch only when the
existing modeled sea mask (`~grid.land`) contains a cell. It does not alter
how water bodies are classified, boundary moisture or mixed-grid arithmetic.
This is independent of the rejected marine-equilibrium target cap.

The regression reproduced positive marine reach on an all-land grid before
the fix. After it, 30 focused tests pass: four actual coupled homogeneous-grid
comparisons, a mixed-grid source-index check and the existing moisture,
transport, reservoir and marine-export suites. Homogeneous land/sea runs have
zero added land marine exchange and physical arrays byte-identical to the
inflow-disabled controls.

The full 97-domain cached-geometry audit finds four all-land cases: Kazakh
steppe, `r_12n_22e`, `r_40n_94e`, `s2_7n_23e`. The guard can physically affect
those domains; it is not merely a diagnostic change. Do not relabel old
reference scores as current or claim a new climate qualification.

The prospective regression budget is seven new regional integrations at
56 km / 1100 km: those four plus mixed Somalia/Sahara/North India controls.
Compare with the preserved fresh current-runtime r58 golden fields, requiring
the same input case identities/observations/coordinates and exact float32
control fields. Require unchanged numerical certificates and report all four
affected responses, including degradations. No parameter fit, solver change,
automatic retry, fine/sealed target or atlas/adoption step is included.
The existing physical source epoch is explicitly changed for this regression;
this comparison is not a new 97-region paired reference for future selection.

Run once after the plan is committed:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  .venv/bin/python -I scripts/benchmark_local.py \
  --fit calibration/local_accuracy_20261023/r58_params.json \
  --cell-km 56 --pad-km 1100 --workers 2 \
  --out output/no_sea_inflow_guard_20261127/guarded \
  --region-specs calibration/no_sea_inflow_guard_20261127/regions.json \
  --regions s_2n_43e u_21n_21e north_india kazakh_steppe r_12n_22e r_40n_94e s2_7n_23e
```

If interrupted, inspect surviving workers and complete receipts before any
recovery; do not blindly repeat the benchmark. Before using the corrected
source for another calibration or atlas, establish a new source/protocol
reference epoch and carry any changed continental behavior into its review.
