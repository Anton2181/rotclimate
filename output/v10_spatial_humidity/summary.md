# Local boundary-humidity comparison

Status: complete; 12/12 cases. Atlas unchanged.

| Case | Coastal winter rain | Change from uniform | Monthly MAE change | Med still arid | Gross incoming water change | Settled |
|---|---:|---:|---:|---:|---:|---|
| control_california_bulk_uniform | 56.37 mm | +0.00 mm | +0.000 mm | 92.8% | +0.0% | True |
| control_california_parcel_lower_uniform | 91.83 mm | +0.00 mm | +0.000 mm | 75.4% | +0.0% | True |
| control_iberia_bulk_uniform | 31.65 mm | +0.00 mm | +0.000 mm | 97.0% | +0.0% | True |
| control_iberia_parcel_lower_uniform | 59.10 mm | +0.00 mm | +0.000 mm | 94.9% | +0.0% | True |
| test_california_bulk_local | 63.19 mm | +6.82 mm | -0.398 mm | 91.3% | +11.9% | True |
| test_california_bulk_local_matched | 56.91 mm | +0.54 mm | +0.054 mm | 92.8% | +0.0% | True |
| test_california_parcel_lower_local | 101.90 mm | +10.07 mm | -0.795 mm | 72.5% | +11.9% | True |
| test_california_parcel_lower_local_matched | 92.96 mm | +1.13 mm | -0.243 mm | 78.3% | +0.0% | True |
| test_iberia_bulk_local | 34.90 mm | +3.24 mm | -0.145 mm | 97.5% | +4.5% | True |
| test_iberia_bulk_local_matched | 33.26 mm | +1.61 mm | -0.064 mm | 97.5% | +0.0% | True |
| test_iberia_parcel_lower_local | 64.11 mm | +5.01 mm | -0.527 mm | 94.4% | +4.5% | True |
| test_iberia_parcel_lower_local_matched | 61.28 mm | +2.18 mm | -0.639 mm | 94.4% | +0.0% | True |

Uniform controls must reproduce exactly. local_matched is the distribution contrast at fixed monthly gross input; local changes both pattern and amount. The dry flow and original nominal storm pulse remain unchanged. No hourly observed weather, parameter selection or fantasy publication.
