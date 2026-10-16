# Cached storm-ascent audit

23360 independent circulation constructions on the 3-hour clock. No climate states advanced. Cached inputs; no downloads.

At the fixed 607.95 hPa interface, upward-positive g × vertical dry-air mass flux is reported in Pa/s (the opposite sign to omega). November–April matches the rainfall review. These are engine-implied motions, not observed vertical velocities or country-only area statistics.

| Region / background | Coastal winter signed background | Signed storm increment | Positive-only background | Positive-only with storms | Storms reverse descent |
|---|---:|---:|---:|---:|---:|
| california_uniform | +0.07853 | +0.00045 | 0.11567 | 0.11714 | 0.63% |
| california_spatial | -0.03683 | +0.00045 | 0.01822 | 0.01853 | 2.08% |
| iberia_uniform | +0.01694 | +0.00109 | 0.05598 | 0.05693 | 0.85% |
| iberia_spatial | -0.03257 | +0.00109 | 0.01303 | 0.01458 | 1.94% |

Positive-only means average max(ascent, 0), including zeros in descending cells/times; they are not the mean conditioned on ascent. Signed storm contributions cannot be inferred by subtracting positive-only means.

## Implication and limits

The prescribed spatial monthly background has net coastal winter descent in both regions. The same synthetic storm perturbations that act on the uniform background mostly fail to overcome that descent. This identifies a forcing mechanism consistent with the dry spatial-wind runs; it does not prove that the monthly background should be reversed or increased. Terrain, projection and coarse pressure interpolation remain part of this imposed engine circulation.

The events explicitly perturb wind/convergence but do not carry a moist warm sector or frontal temperature anomalies. Internally transported humidity can still correlate with winds; this audit does not measure that covariance or infer a real storm amplitude.

An independent [ERA5 Mediterranean moisture-budget study](https://wcd.copernicus.org/articles/6/245/2025/) finds that submonthly eddies sustain winter net precipitation over land while the mean circulation partly opposes it. That supports testing event-linked forcing rather than making the monthly mean artificially wet. The study concerns the Mediterranean, not validation of this California experiment or a measured parameter choice.

Next development: a bounded, conservative event/front mechanism test with an identical monthly mean supply and paired timing control. Separate imposed lifting from moisture timing; record actual import and coastal/interior rain. Obtain accessible high-frequency reference data before claiming realistic event statistics. No further parameter or storm-seed sweep is justified by this audit.

Reproduce this forcing-only audit:

```sh
.venv/bin/python scripts/audit_v10_storm_ascent.py --write
```
