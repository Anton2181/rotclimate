# Six-hourly reference weather audit

Status: fetch_paused.

NOAA returned HTTP 429; Retry-After: not specified. No immediate retry; cached files preserved. Rerun later.


Fluxes are kg m⁻¹ s⁻¹ over 925–300 hPa, not rainfall or a closed regional boundary budget. Covariance is computed in time at each native point before spatial averaging. Neighboring pixels and successive weather samples are correlated; no independent-sample confidence interval is claimed.

Top eastward transport is a descriptive composite, not identified cyclones. Only two years and January/July are sampled. Reanalysis is model-informed and coarse, with pressure-level/native terrain limitations. The lowest 1000 hPa level is excluded to reduce below-surface contamination; the 925–300 hPa column excludes lower and upper water transport. Liquid-reference relative humidity is diagnostic, not mixed-phase cloud physics.

Current synthetic model vortices do not carry event-linked boundary temperature/humidity anomalies. This does not mean the model’s internally transported moisture has zero covariance. Use these measurements to decide whether a coupled weather-forcing mechanism earns its next prototype, not to fit precipitation or infer rainfall from vapor flux alone.

Data provided by [NOAA PSL](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis/pressure/catalog.html). No seasonal climate integration, calibration or atlas change.
