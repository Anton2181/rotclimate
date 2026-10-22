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

## Milestone 2: make Whittaker diagram coverage a selection constraint

The published Whittaker fit leaves **8.5215%** of source-map land outside the
unchanged diagram (5.9778% on its coarser model grid). Its former objective
measured target-biome match and had no explicit penalty for total map coverage.
The outside pixels include cold/wet mountains and wet mild lowlands; their
median annual rainfall is 3,223 mm and their median elevation 2,346 m. The full
baseline diagnosis is `output/iteration_20261022/outside_baseline.json`.

`whittaker-covered` is a separate objective. It retains the strict crosswalk
score and subtracts an all-land outside-area penalty plus capped distance debt
to the union of the original polygons. Its coverage includes unpainted land
and source-resolution terrain. The annual interpolation is algebraically
identical to the renderer's monthly-field average, without allocating twelve
full-size maps; it exactly reproduces the published baseline outside share.
Old objectives and biome classification remain unchanged. No fields are clipped
or grey cells assigned a nearest biome.

Coefficients and publication gates are explicit in `data/whittaker_coverage.json`:
1% outside allowance, area weight 2, distance weight 0.1, and publication gates
of at most 2% outside land with a strict biome objective at least 0.46. These
are scenario-selection preferences, not physical laws or newly observed data.
25 focused coverage, crosswalk, classifier and calibration checks pass,
including invalid land, unpainted land, distance gradients, annual rendering
and per-layout objective aggregation.

The bounded physical screen in `scripts/refine_whittaker_coverage.py` compares
seven predeclared humidity/lapse/orography profiles over layouts 1–3 at ds32,
then two profiles at ds16. It preserves source and parameter hashes, numerical
certificates and failed cases. Native ds8 verification and atlas publication
are separate gates; the existing atlas stays active until they pass. The free
and Earth fits are unchanged. Training layouts are reused, so this measures
fit and scenario sensitivity rather than independent predictive validation.
