# Broader conservative-storm comparison

This is a new prospective **61-region** development pool: historical dev49 plus
spent sets d/e. Historical S49 remains separately reported. Reserved f remains
unopened until one candidate passes full development and paired finer-grid
qualification. The aggregate and safeguards retain the previous numerical
thresholds; no individual region or group veto applies.

Two exact parameter sets test conservative storm exchange with r42 strengths
and with r43 strengths. Neither changes the planet/orbit or imposes observed
wind/SST. Legacy concentration-form mean-wind transport remains: this is not a
globally conservative atmosphere. Both families finish before selection.

The damped r43 reference first reproduces retained raw monthly fields, with
strict criteria unchanged. Six raw-reference cases in spent d are generated
before checking the complete 61-region numerical control. A failed control
stops all physical candidates. Partial or failed candidates get no mean score.

The model and benchmark run from the pinned r43 snapshot. The driver waits for
correction training to finish so it does not compete with that stage, and keeps
the scientific source stable while main-tree experiments may continue.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -I \
  scripts/expand_storm_exchange.py \
  --plan calibration/storm_expansion_20261103/plan.json --workers 2
```

All outcomes are retained and pushed to both branches. The driver does not
adopt physics or modify normal atlas data.
