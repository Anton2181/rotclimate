# Reusing an identical moisture mixing target — 10 November 2026

An isolated implementation avoids recomputing the storm-mixing target at the start of a Picard
iteration when the preceding residual check already evaluated it at exactly that water state.
Neither water nor the mixing operator changes between those two evaluations. The cached value
is the vapor target, before any condensate is added for the equation residual. Legacy iterations
without residual checks retain their original calls and arithmetic.

**Integrated after the frozen joint-response campaign completed; no climate-accuracy change.**
The original studies used a reviewed function in an isolated interpreter and restored the original
module function on exit. The final integrated function exactly matches that verified proposal.

The Japan pilot uses warmup followed by baseline/reuse/reuse/baseline runs. Its mean CPU times are
5.919 s and 5.534 s (ratio 0.935). An expanded, separately identified repetition gives:

| Known case/profile | Baseline CPU, s | Reuse CPU, s | Ratio |
|---|---:|---:|---:|
| Bengal, r44 | 4.369 | 4.010 | 0.918 |
| North Queensland, r44 | 3.765 | 3.621 | 0.962 |
| Patagonia, r44 | 3.972 | 3.783 | 0.952 |
| Japan, warmer-sea/C3 starting profile | 6.083 | 5.935 | 0.976 |

Every run has **identical T, sea-level T, precipitation, water, winds, evaporation, snow, sample
days and all reported numerical diagnostics** relative to its control. The four expanded cases use
4.6% less pooled CPU time; this small sample does not establish a general speedup. Wall times
are affected by the simultaneously running calibration and must not be used as speed ratios.

Four unit cases also retain identical water, rain, iteration counts, residuals and linear-solver
histories: residual checks on/off, each with/without storm condensation. Mixing call counts fall
only in the residual-checked cases. This tests that vapor and condensate are not confused and
that existing legacy behavior remains intact.

Protocols, sources before/proposed, per-run measurements and exact-replay receipts are under
`output/moisture_mix_reuse_20261110/` and `output/moisture_mix_reuse_20261110_expanded/`. These use
known development cases; they are not fresh climate validation or additions to the 51-candidate
physics budget. No physical coefficient, forcing, tolerance or adopted atlas field changes.

The full 49-region byte/numerical check is complete under
`output/moisture_mix_reuse_20261110_all49_float_resolution/`. All nine result-array byte hashes
and all reported numerical diagnostics match; each control also reproduces the frozen fresh r44 monthly
temperature/rain archives. The integrated function is source-identical to the tested proposal,
an integrated Japan replay matches every archived array hash/history, and 64 focused tests pass.
The regression test now compares the integrated function to the immutable pre-optimization body.
No coefficients, equation, tolerance, annual-cycle setting or adopted atlas climate field changed.
Full-model replay compares the result's reported `numerics` diagnostics; detailed linear-solver
iteration histories are additionally compared in the small regression cases.

The calibration, coastal diagnostics and publication completed before integration. Its frozen
pre-integration source revision is `4d89cf1c88067611e3ae91f278f39f7865a48614`, recorded alongside
old/new module hashes in `output/moisture_mix_reuse_20261110/integration.json`. Historical studies
and checkpoints retain their original source identities; use that revision to replay/resume them.
The old source-shape probes intentionally reject silently running against the integrated function.

The full-region check's initial setup was blocked by an input identity check: integer `56` and float `56.0` produce
different JSON metadata in the existing case hash. Using the benchmark's float resolution exactly
reproduces the frozen input identity; no geography or cached fields changed. The initial rejected
namespace and source-exact driver are preserved. The corrected check uses a new output directory.
