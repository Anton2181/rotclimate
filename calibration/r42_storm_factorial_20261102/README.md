# Isolated vapor/storm comparison

See `reports/TRANSPORT_FACTORS_20261102.md`. Four exact parameter files and their
source hashes are fixed before integrations. The driver waits for the complete
original conservative replay, then runs all four eight-region profiles and
publishes every outcome. It does not tune parameters, evaluate unseen boxes,
adopt physics or change an atlas. Two profiles add accounted condensation at
local crest saturation; baseline r42 has that parameter disabled.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -I \
  scripts/run_r42_storm_factorial.py \
  --plan calibration/r42_storm_factorial_20261102/plan.json --workers 1
```
