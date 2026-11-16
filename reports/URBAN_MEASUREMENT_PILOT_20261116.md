# Source-basis predictive pilot — 16 November 2026

Training only on extents labelled exactly `Inhabited area` does not improve
predictions on the common held-out target set. Hinterland population has little
aggregate added skill, and one held-out province fold is consistently weak.
No new size law or map update is supported by this development pilot.

This does not establish that extent definitions are equivalent. The smaller
strict training sample can itself lose precision, and the source still lacks
independently certified extent dates. Nor is this a complete test of the
published hierarchy's joint random-draw/centre-selection algorithm: the fixed
alternatives here are conditional Gaussian log-area regressions.

## Declaration and support before fitting

`calibration/urban_diagnosis_20261116/measurement_basis_pilot.json` was committed
in 88c9cb042 before pilot preparation. The independently checked anonymous
design and support receipt were committed in c7aadb5c9 **before fitting**.
The unchanged current cohort has 664 records. Exact `Inhabited area` selection
leaves 153 records in 40 provinces, with fold counts 43/43/31/36 and only four
existing capital labels. All 32 declared outer/inner training supports pass
sample-size and full-rank checks; no membership or model was changed on scores.

The existing geographic eligibility, exact 20/30 exclusion and Greek wall-area
adjustment are preserved. Some inhabited-area records with exact 20/30 values
therefore remain excluded; that filter is not newly certified by this pilot.
Support review reuses the pinned, previously reviewed geometry and independently
checks the new source joins, basis selection, corrections, capital labels,
province encodings and design. It is not a new independent geometry validation.

There are six fixed alternatives: mixed/strict training crossed with intercept
only (M0), intercept plus ln hinterland people (M1), and those terms plus the
existing capital indicator (M1C). Every alternative predicts exactly the same
153 strict target records in the original four province-hash outer folds.
For each outer fold, three inner province folds estimate predictive sigma from
out-of-fold squared errors within its training cohort. Neither mean coefficients
nor sigma use any outer-test area. No full-data residual variance is borrowed.

## All six results

Scores pool the identical 153 outer-held-out records. Lower errors and Gaussian
negative log density on log area are better. Coverage is descriptive; the
intervals are predictive assumptions, not certified source measurement error.

|Training basis|Model|Log-area MAE|Log-area RMSE|Gaussian log-area NLL|80% coverage|95% coverage|
|---|---|---:|---:|---:|---:|---:|
|Mixed|M0|0.8225|1.0362|1.4572|82.4%|96.7%|
|Mixed|M1|0.8047|1.0383|1.4615|82.4%|95.4%|
|Mixed|M1C|0.7930|1.0120|1.4343|83.0%|96.1%|
|Strict|M0|0.8294|1.0436|1.4728|81.7%|95.4%|
|Strict|M1|0.8283|1.0702|1.5256|83.0%|96.1%|
|Strict|M1C|0.8172|1.0540|1.5223|83.0%|95.4%|

For mixed training, adding H reduces MAE by about 2.2% but worsens RMSE and proper
log score. For strict training, its MAE improvement is about 0.1%, again with
worse RMSE/log score. This provides no consistent case for a much stronger H
effect. Capital information helps some summaries, especially mixed-training
log score, but four strict target capitals give little support for broad claims
about primacy or unseen regions. No fitted coefficient is adopted.

Every alternative has its largest aggregate error in outer fold 3, comprising
36 strict targets in ten provinces. Examples:

|Alternative|Fold 0 NLL|Fold 1 NLL|Fold 2 NLL|Fold 3 NLL|
|---|---:|---:|---:|---:|
|Mixed M0|1.4090|1.4180|1.4010|1.6102|
|Mixed M1|1.3792|1.3693|1.3708|1.7478|
|Mixed M1C|1.3497|1.3688|1.2916|1.7363|
|Strict M0|1.4065|1.4192|1.4059|1.6734|
|Strict M1|1.4057|1.4179|1.4015|1.9045|
|Strict M1C|1.3831|1.4063|1.3533|1.9726|

Strict M1C's fold-3 coverage is 63.9%/86.1% for nominal 80%/95% intervals.
Pooled coverage can obscure a geographic weakness. The province folds are
hash-based groups of provinces, not contiguous geographic regions. The full
fold and 240 per-province summaries remain visible; no weak fold is removed,
reweighted away or converted into a new tuning target.

## Next step and limits

The next declared stage is `geographic_residual_audit.json`: decompose the fixed
predictions by province, predictor support, bias, dispersion and capital status.
It performs no refit, outcome-selected exclusion or new model ranking. Its aim
is to distinguish a few large errors from a broadly miscalibrated geographic
relationship before choosing another mechanism. H is a local catchment proxy,
not a measurement of interregional food access or administrative importance.
Those are possible later predictors only with independent, appropriate inputs
and a declaration that prevents size-derived labels leaking into prediction.

The Roman areas remain conditional catalogue extents whose dates/availability
are imperfect. Known catalogue locations enter H, so this is not a site forecast
or settlement census. No survey pool is newly scored; Mexico is not a large-city
primacy target. No random-size distribution, density, urban population budget,
food feasibility, climate or map layer is changed. A later model needs source-
appropriate evidence and declared transfer, followed by the existing origin/
food/labour reconstruction before any adopted map update.

## Review and reproduction

Independent review imports neither pilot producer nor nested-fit component.
It uses GELSY QR least squares, scalar inner-OOF variance, independent normal
log density/quantiles, and checks all 24 outer cases, 72 inner fitted receipts,
six alternatives, 918 prediction rows and 11,610 CSV cells. Six fresh numeric
files reproduce byte for byte. Four tests explicitly check outer-label and
ineligible-label isolation, scalar dispersion accounting and support rejection.
All protected prior inputs/results are unchanged.

Complete artifacts are in `output/urban_measurement_pilot_20261116/`.

```sh
.venv/bin/python scripts/prepare_urban_measurement_pilot.py
.venv/bin/python scripts/prepare_urban_measurement_pilot.py --out output/urban_measurement_pilot_20261116/fresh
.venv/bin/python scripts/review_urban_measurement_support.py
# The eligibility/design/support review must be committed before the fit:
.venv/bin/python scripts/urban_measurement_pilot.py
.venv/bin/python scripts/urban_measurement_pilot.py --out output/urban_measurement_pilot_20261116/fresh
.venv/bin/python scripts/review_urban_measurement_pilot.py
```
