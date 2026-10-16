# Delivery diagnostics and fixed weather robustness

Status: budget_reached; 51/100 jobs. Reference replays 4/4; climates 32/64; new-weather diagnostic replays 15/32. Atlas unchanged.

| Catalogue / region | Stronger lift: coastal winter gain | Lift + linked moisture gain | Linked minus shifted | MAE change | All settle |
|---|---:|---:|---:|---:|---|
| s67_california | +28.60 mm | +31.97 mm | +2.68 mm | -1.871 mm | True |
| s67_iberia | +15.23 mm | +16.28 mm | +1.44 mm | -1.139 mm | True |
| s103_california | +44.74 mm | +48.85 mm | +1.93 mm | -2.697 mm | True |
| s103_iberia | +30.21 mm | +31.77 mm | +1.73 mm | -1.681 mm | True |
| s149_california | +36.89 mm | +41.02 mm | +4.23 mm | -2.669 mm | True |
| s149_iberia | +24.95 mm | +26.50 mm | +2.08 mm | -1.801 mm | True |
| s211_california | +27.46 mm | +29.70 mm | +1.50 mm | -2.209 mm | True |
| s211_iberia | +25.09 mm | +26.24 mm | +1.57 mm | -2.169 mm | True |

Fixed paired synthetic-catalogue sensitivity; no best-seed selection or observational climate confidence interval. Input is matched across conditions within each catalogue/region, not across different catalogues. Unsettled cases remain labelled. Diagnostics require exact physical replay; stage condensation opportunities are not alternative-climate rainfall.
