# Six fixed diagnostic captures after the completed padding study

The nine-case physical study is complete and reviewed. Its saved scored
monthly states and instantaneous import/drying show compensating changes,
but cannot separate advection, diffusion, storm exchange and marine humidity
exchange. This follow-up declares **six additional diagnostic integrations**:
Somalia, Sahara and North India at 1100 and 4012 km, all three original-size
controls first. The middle padding is not rerun. This is no extension/retry
of the original budget and no search for a better padding or parameter fit.

Use the previously validated diagnostic-only marine-export patch in a fresh
regular private source/cache copy. Main W18c source/shared inputs and the
completed padding snapshot stay unchanged. All physical parameters, solver
tolerances, footprints, observations and raw reference packets remain fixed.
Each replay must reproduce every saved T/P/E/W/u/v monthly value, trace
gain/sink/water/rain and calendar in dtype, shape and bytes. Require its
original numerical certificate and the unchanged 0.01 local residual criterion,
with explicit float32 export rounding bounds. Preserve failure receipts;
one failure stops execution and no automatic retry is allowed.

The complete local equation includes surface evaporation, signed marine
exchange, total linear drying, convergence import, advection, diffusion and
storm exchange. Monsoon drying is a subset of total drying, not an additional
source to sum. Residuals retain instantaneous absolute/RMS/max checks so annual
cancellation cannot hide failure. This is concentration-equation accounting,
not conservative planetary closure, boundary flux or tagged rain attribution.

The plan and execution scripts must be committed before preparation/run.
One worker runs at nice10 or lower, with OMP/BLAS thread variables exactly1.
Preparation imports no physical model and executes no integrations:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  nice -n 10 .venv/bin/python -u -I scripts/padding_budget_capture.py
```

Add `--run` to execute the fixed six captures. A singleton lock and immutable
protocol prevent duplicate/drifted execution. `status.json` includes real
step progress and timestamps. The independent reviewer runs automatically
after all six pass. Actual scientific findings still need agent review.
Neither program adopts climate, changes main source, alters W18c selection
or gates, opens fine/sealed targets, builds an atlas or commits/pushes results.
