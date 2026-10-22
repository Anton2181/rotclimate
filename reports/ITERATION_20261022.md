# Iterative improvements after the three-fit publication

## Milestone 1: certify every direct linear solve

The SciPy-only backend previously marked any finite result as converged, even
when its residual exceeded the requested tolerance. It also did not enforce
`solver_require_convergence`. The direct recovery used by the Numba backend
already checked the interior equation, but omitted an explicit boundary check.

Both direct paths now use the same certificate: maximum diagonal-scaled interior
equation residual and prescribed-boundary error, bounded by the original
boundary-scaled requested tolerance plus the existing floating-point roundoff
allowance. No physical constants, discrete operator or tolerance were changed.
Failed certificates remain failed in observed numerical diagnostics. Strict
runs raise; permissive runs warn once. Nonfinite direct answers record failure
before raising.

47 focused checks pass, including manufactured variable-flow solutions for both
transport stencils, deliberately inaccurate interior and boundary results,
nonfinite outputs, capped-sweep recovery, temperature retries and existing core
checks. Evidence: `output/iteration_20261022/solver_certificate.json`.

The published nine main-map layouts used no direct solves. Their climate assets
and original provenance stay unchanged; this milestone does not claim new fit
accuracy or rerun the completed calibration campaign. Existing frozen campaign
manifests correctly retain the sources of their original builds.
