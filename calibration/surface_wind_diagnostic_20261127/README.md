# Six fixed surface-wind diagnostics

Prospective design, committed before private preparation or integration. Exactly
three model-wind controls followed by three observed-wind interventions, ordered
Somalia, Sahara, North India. Same56km cells,1100km pad and scored footprint.
Private225 regular files use current unchanged physical source plus frozen cache.
All original solver tolerances and convergence requirements apply. Any failed or
interrupted scientific attempt is preserved; stop without automatic retry or
altering numerical settings. Completed packets are immutable.

Only wind_source changes to observed in the intervention arm. The verified
NOAA PSL NCEP/NCAR1991–2020 sigma0.995 surface climatology is bilinearly sampled
on the full padded physical grid, then mapped with the existing equidistant
projection Jacobian (rotation AND metric). Restrict this design to its three
northern regions; do not reuse it silently for southern mirrored cases.
Preparation checks the inverse geographic transform and records full forcing
arrays/coordinates/Jacobian plus file hashes before any climate integration.
Prescribed monthly inputs are read-only. Actual heat/moisture wind samples must
match the production monthly-center interpolation exactly, across the saved
year. No second friction factor is applied. Both transport velocities change;
all coupled heat/moisture/source responses are retained rather than assigned
isolated causal shares. SST and every other coefficient remain fixed.

All three baseline controls must reproduce saved monthly T/P/E/W/u/v, calendar,
instantaneous gain/sink/W/P/winds and every moisture-budget field byte-exact.
Each run must pass the original numerical certificate and signed local equation
at the original0.01 criterion with documented archive rounding only. Independent
post-review rechecks inputs, parameter differences, exact controls, projected
forcing, actual raw solver wind and local accounts; reports regional T MAE,
existing rain loss, annual rainfall and all signed source changes, plus figure.
No accuracy gate is invented: this observational intervention is diagnostic
and cannot be adopted as a climate law for a fictional map even if beneficial.

Launch from repository root with .venv/bin/python (never dereference its symlink),
nice10 and OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS all1. Run
scripts/run_surface_wind_diagnostic.py to prepare only, then the same with --run.
No background study is resumed. W18c remains permanently closed, AA unopened,
r58 retained, atlas r51 unchanged. Future calibration requires a current-source
paired reference; this diagnostic is not that qualification.
