# Shared transport factors: six completed numerical controls

All six fixed 24-hour comparisons pass the predeclared state and independent
saved-state energy/water checks. Both backends use the qualified fast phase
root. Every reference reproduces the preceding fast-phase archive exactly,
including scalar history. Every candidate final array is also byte-identical
to its reference in these three cases. This is numerical qualification; it
provides no measured gain in rainfall skill.

| Region | Reference calls (s) | Reused calls (s) | Time reduction | Factorizations before/after |
|---|---:|---:|---:|---:|
| north india | 42.03 | 24.00 | 42.9% | 1152/576 |
| mexico | 27.27 | 22.56 | 17.2% | 1152/576 |
| pacific nw | 19.02 | 16.76 | 11.9% | 1152/576 |

Times sum all 96 actual coupled calls, including cold first-step work. Backend
order alternates by region as declared before outcomes. No timing samples are
dropped and there is no speed threshold. These are observed paired timings;
they are not a repeated-timing confidence interval or a further comparison
against the original slow phase solver.

Each run makes 1,152 scalar solves. Exact factor reuse reduces factorizations
from 1,152 to 576 without changing matrix assembly or physical function bodies.
Cache snapshots detect changes to shape, indices and coefficients, including
in-place mutation. Cache scope is one advance. The retry test verifies that a
failed singular factorization cannot accidentally reuse a stale prior factor.

The focused physics/numerical suite has 374 passes. Reconstructed saved total
energy relative error is below 1.6e-15; water error is below 3e-16. Complete
initial/final arrays, paired per-call timings and counts, source hashes and
literal protocols are retained in `output/shared_transport_20261029` and the
research atlas downloads.

The numerical backend is qualified for future prototype experiments. Earth r39
and all normal world/biome/population maps remain unchanged. No recalibration
or physical-model adoption occurs. The separate prototype count is 87 starts /
83 completions /four retained earlier numerical failures; legacy 1934/1929 is
unchanged. The next experiment extends wet/dry soil-water sensitivity to fourteen
days, with fixed daily checkpoints and no fitted initial soil state.
