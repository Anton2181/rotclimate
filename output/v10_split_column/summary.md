# Controlled five-layer upper-column split

Status: complete; 12/12 new cases complete. Atlas unchanged.

| Case | Old → new rain MAE | Old → new rain/reference | Coastal winter rain | Settled | Broad screen |
|---|---:|---:|---:|---|---|
| california_uniform_split_dry | 40.07 → 28.99 | 1.18 → 0.46 | 237.3 mm | True | False |
| california_spatial_split_dry | 30.33 → 32.24 | 0.10 → 0.04 | 26.0 mm | True | False |
| iberia_uniform_split_dry | 32.20 → 32.27 | 0.42 → 0.23 | 97.5 mm | True | False |
| iberia_spatial_split_dry | 35.02 → 34.66 | 0.05 → 0.05 | 16.3 mm | True | False |
| california_uniform_split_rh300 | 40.07 → 28.42 | 1.18 → 0.66 | 271.5 mm | True | True |
| california_spatial_split_rh300 | 30.33 → 31.62 | 0.10 → 0.06 | 30.1 mm | True | False |
| iberia_uniform_split_rh300 | 32.20 → 31.92 | 0.42 → 0.28 | 111.4 mm | True | False |
| iberia_spatial_split_rh300 | 35.02 → 34.61 | 0.05 → 0.07 | 16.6 mm | True | False |
| california_uniform_split_column_matched | 40.07 → 27.37 | 1.18 → 0.54 | 250.5 mm | True | True |
| california_spatial_split_column_matched | 30.33 → 31.98 | 0.10 → 0.05 | 24.7 mm | True | False |
| iberia_uniform_split_column_matched | 32.20 → 32.09 | 0.42 → 0.26 | 104.3 mm | True | False |
| iberia_spatial_split_column_matched | 35.02 → 34.66 | 0.05 → 0.06 | 15.0 mm | True | False |

Three fixed hypotheses: dry above 300 hPa; offshore RH300 retained at 150 hPa; the latter with boundary column vapor concentration matched to the old four-layer value after saturation caps. Upper humidity assumptions are not observations. Matched column concentration does not guarantee identical wind-weighted inflow. Lower/aggregate upper horizontal circulation is retained; the new internal interface and thermal/moisture structure are resolved.

Temperature remains reference-informed, momentum is prescribed and flow work is diagnosed. Existing broad screens are development evidence, not climate validation. Read source input/protocol, thermal/layer/work budgets and coastal/interior seasonal responses together. No automatic selection or atlas publication; original source-tag evidence is preserved.
