# Coupled reservoir linear backend

`experiments/reservoir_block_solver.py` solves the existing two-reservoir
transport operator with a2x2 local block for lower/upper water at every cell.
Four-direction Gauss–Seidel sweeps retain the original horizontal donor faces,
vertical donor exchange, reaction, diffusion and prescribed boundaries. This is
a numerical backend change, **not a physical rainfall retune or a climate run**.

Every result is checked against the independent original sparse matrix and its
prescribed boundaries. A small update alone cannot pass. Failed sweeps either
raise or recover by solving that same sparse matrix, followed by the same actual
equation check. Negative/nonfinite water, invalid settings and singular local
blocks fail. Eight new tests plus nine original operator checks pass, including
three independent random sparse/face-ledger comparisons, uniform specific humidity
over terrain, exact boundaries and insufficient-work rejection/recovery.

Paired synthetic benchmark `output/reservoir_blocks_20261026/` alternates timing
order over two repetitions after separate JIT warmup, fixed56km cells and the
same physical operator/source/reaction/boundary values:

| Grid | Two-layer unknowns | Sparse median ms | Block median ms | Largest water difference mm |
|---|---:|---:|---:|---:|
|24x30|1440|2.74|1.87|4.99e-9|
|48x64|6144|13.22|5.73|8.59e-9|
|72x96|13824|39.62|15.38|1.38e-8|

The largest example takes about2.6times less linear-solve time in this small
benchmark. This is not a full-season speed claim or a statistically broad
hardware benchmark. All block results pass their actual matrix tolerance and
an independently evaluated face/vertical water ledger. No climate integrations
are added. Core seasonal coupling, sources/ocean exchange, per-layer nonlinear
rain and column budgets still require their own implementation and tests.

The original sparse prototype is retained as an independent reference. No
published climate, economic map or accuracy score changes because of this
backend benchmark.
