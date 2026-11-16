# Release-4 settlement diagnosis — 16 November 2026

This is development diagnosis on already-spent source pools, with no new fit,
blind claim or adoption. Climate remains parked. The owner-supplied Mexico
workbook matches its original SHA256 exactly. Both original transfer producers
now reproduce their results JSON and model NPZ byte for byte in isolated paths.

Plans `2e059c2c5` and `6a362be71` preceded the new diagnostic cases. Original
producers, source files and the published atlas are unchanged. Restored inputs,
path redirections and source identities are in
`output/urban_diagnosis_20261116/input_receipt.json`.

## What the first comparison establishes

The unmarked release-4 transfer uses confluences and the released size metadata,
with no invented capital/centre labels. The base coefficients, scatter and area
bounds equal the archived M1 when those labels are absent. It therefore does not
test the fantasy map's lore-anchored hierarchy effect.

|9 km case|Mesopotamian model towns in footprint proxy|Mean model area over five seeds, ha|Mexico model towns in footprint proxy|
|---|---:|---:|---:|
|Archived placement, subset draws|12|489.071|0|
|Same placement, full-window draws|12|630.320|0|
|Release-4 confluences, full-window draws|11|454.346|0|

These counts are inside a mask made from observed sites, not an independently
documented surveyed polygon. The entire-window count remains 77 in Mesopotamia
and 10 in Mexico. At 3 km the original town position percentile/capture is
0.481/0.186 for Mesopotamia; release 4 gives 0.483/0.161. Mexico changes from
0.616/0 capture to 0.586/0. These are exposed, conditional diagnostics.

Moving residual draws from the survey subset to the full window changes the
particular seeded realizations. One full-window draw produces a surveyed model
town above 200 ha. That does not establish improved expected performance:
exchangeable independent draws have the same marginal law. Nor does it rescue
the original five-seed area/band comparison. There is no hard 200 ha size cap.

Most importantly, a size-distribution comparison with no predicted towns is
undefined. Mexico's zero-town outcome identifies a placement/count/coverage
problem; it cannot by itself estimate an error in the size curve. The original
top-N comparison also combines missing towns with size concentration, rather
than isolating the size law.

## Observation findings

- Mesopotamian `SizeHa` is a six-class code. The final class has a lower
  representative of 201 ha in the authors' code; no observed 1,783 ha upper
  limit is supplied. That upper limit came from the model. It is preserved only
  to reproduce the original test. New distribution diagnostics retain an open
  upper tail and report a KS lower bound, not an imputed-area KS or p-value.
- The possible AD 200 occupation phases are broad intervals. They are not an
  exact simultaneous census. The authors also compute time-block/aoristic
  summaries; these require interpretation before fitting a temporal model.
- Mexico has 221 selected Classic/Early Classic records, 27 with at least 10 ha.
  Their total area is 1,099.1 ha; their largest is **76 ha**. The earlier report's
  840 ha figure is the all-period maximum, not the selected Classic maximum.
  The largest single population estimate is only **1,000 people**. This selected
  rural/small-settlement cohort does not supply a large-city population ranking.
- The selected Mexico estimates sum to 20,227 people, with bounds 9,745–20,227.
  All 221 single estimates equal their corresponding upper estimates. The
  archived model/reference ratio is therefore 1.72 against the upper estimate
  and 3.57 against the lower one. The previous broad population pass is
  conditional on the chosen estimate, not robust across the supplied range.
- The resulting 18.40 people/ha is a relationship among source estimates, not an
  independently calibrated census density. The public metadata describes area
  as site hectares and population as an estimate. Its estimation method and
  Teotihuacan's precise exclusion are not confirmed by this audit. Applying
  the Old World 100/ha reading to these areas implies 109,910 residents; the
  sliding reading implies 118,136. Neither is adopted as a correction.
- Site-buffer masks depend on the resolution. Their area and source-to-grid
  collisions are retained separately for 3 km and 9 km. Missing model towns
  inside this proxy is not an unbiased estimate of regional catalogue coverage.

The independent reviewer reconstructs the raw cohorts and grid snap, scalar
tie-aware hinterlands, confluence prior, direct size equations, interval CDF
bounds and all CSV cells. Twelve observation-component controls pass, including
exhaustive finite-interval imputation checks. Five fresh diagnostic files
reproduce byte for byte. Receipts live under `output/urban_diagnosis_20261116/`.

## Next discriminating control

Before fitting urban concentration, supply the observed town locations as a
diagnostic and evaluate the unchanged size rule there. Keep original people,
coefficients and seeds; allocate hinterlands once and retain coordinate
collisions rather than losing them to a grid. This asks whether the size rule
still misses the distribution when placement and count are supplied. It is an
explanatory control, not a forecasting or prospective-validation result.
