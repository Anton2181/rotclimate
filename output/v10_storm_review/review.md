# Storm delivery: measured responses

Ten cases / 35 cycles; 32.37 saved integration minutes. All settle.

| Case | Monthly MAE | Skill against zero rain | Annual rain | Coast / interior annual rain | Minimum coverage | Broad screen |
|---|---:|---:|---:|---:|---:|---|
| california_anchor | 33.70 | -0.6% | 309.2 | 258.0 / 238.6 | 80.7% | True |
| iberia_anchor | 32.01 | 9.4% | 97.0 | 145.9 / 4.6 | 75.0% | False |
| california_mean_only | 41.49 | -23.9% | 498.4 | 407.1 / 356.5 | 76.6% | False |
| iberia_mean_only | 32.13 | 9.1% | 184.6 | 247.7 / 21.8 | 71.0% | False |
| california_rare_storms | 41.66 | -24.4% | 512.5 | 416.3 / 361.1 | 85.9% | True |
| iberia_rare_storms | 32.07 | 9.3% | 193.5 | 259.7 / 22.2 | 79.2% | False |
| california_winter_storms | 43.69 | -30.5% | 570.2 | 464.1 / 378.9 | 91.4% | True |
| iberia_winter_storms | 32.44 | 8.2% | 229.2 | 310.3 / 23.8 | 85.3% | True |
| california_frequent_storms | 48.94 | -46.1% | 655.1 | 548.6 / 404.0 | 94.4% | True |
| iberia_frequent_storms | 34.16 | 3.4% | 285.4 | 393.4 / 25.7 | 86.3% | True |

Skill = 1 - monthly cellwise MAE / zero-rain MAE. Positive is better than zero rain. The broad screen did not require this skill and is preserved unchanged.

| Region / paired change | Coastal winter delta | Interior winter delta | Coastal summer delta | Interior summer delta | MAE delta |
|---|---:|---:|---:|---:|---:|
| california / humidity_0.8_to_1 | +115.42 | +68.71 | +42.91 | +53.80 | +7.96 |
| california / storms_0_to_1 | +7.79 | +1.77 | +1.43 | +2.91 | +0.17 |
| california / storms_1_to_4 | +32.00 | +7.92 | +15.77 | +9.85 | +2.03 |
| california / storms_4_to_8 | +68.76 | +16.05 | +15.77 | +9.06 | +5.24 |
| iberia / humidity_0.8_to_1 | +53.65 | +14.26 | +60.14 | +3.38 | +0.06 |
| iberia / storms_0_to_1 | +9.47 | +0.30 | +2.57 | +0.08 | -0.06 |
| iberia / storms_1_to_4 | +36.60 | +1.37 | +13.97 | +0.27 | +0.36 |
| iberia / storms_4_to_8 | +76.05 | +1.78 | +7.07 | +0.13 | +1.72 |

Finite matched secants at one weather seed. No inferred global feasibility, independence of pixels/settling years, emulator or history matching. Fantasy protected-zone constraints are not Earth metrics.

No new seasonal integration, calibration or atlas publication.
