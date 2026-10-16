# Mass-consistent wind and storm-delivery check

Status: complete. Ten fixed cases; no optimizer or atlas export.

| Case | Rain MAE | Rain / reference | Wet-reference coverage | Settled | Provisional rain/thermal screen |
|---|---:|---:|---:|---|---|
| california_anchor | 33.70 | 0.77 | 80.7% | True | True |
| iberia_anchor | 32.01 | 0.23 | 75.0% | True | False |
| california_mean_only | 41.49 | 1.24 | 76.6% | True | False |
| iberia_mean_only | 32.13 | 0.44 | 71.0% | True | False |
| california_rare_storms | 41.66 | 1.28 | 85.9% | True | True |
| iberia_rare_storms | 32.07 | 0.46 | 79.2% | True | False |
| california_winter_storms | 43.69 | 1.42 | 91.4% | True | True |
| iberia_winter_storms | 32.44 | 0.54 | 85.3% | True | True |
| california_frequent_storms | 48.94 | 1.63 | 94.4% | True | True |
| iberia_frequent_storms | 34.16 | 0.67 | 86.3% | True | True |

The anchor differs from each completed hybrid baseline only in velocity-to-mass-flux construction and its column projection; its old rate-one weather catalogue is retained. Other controls restore the reference humidity multiplier and vary nested storm count.

| Completed hybrid baseline | Rain MAE, mm/month | Rain / reference | Wet-reference coverage |
|---|---:|---:|---:|
| california | 30.26 | 0.43 | 52.0% |
| iberia | 32.84 | 0.21 | 58.6% |

| Region | Old / new maximum middle-layer face speed, m/s |
|---|---:|
| california | 27.9 / 9.7 |
| iberia | 13.4 / 6.4 |

Face velocities use face dry mass consistently. The earlier cell-flux/store proxy can differ on steep mass gradients; both conventions are retained in the manifest. Projection enforces stationary column mass with explicit open-boundary adjustments, not a prognostic momentum/radiation system. Temperature remains observation-informed.

The provisional screen requires settling, closed budgets, temperature departures <=5/10°C (lower/upper), annual rain ratio 0.5–1.75, at least 80% of reference non-arid land receiving >=1 mm/year, and rain p99 <=4 times reference. This coverage threshold is a minimal dry-gap check, not evidence of a realistic rainfall map.

A provisional rain/thermal pass is diagnostic evidence, not independent validation. Geometry, rain-out closure and old acceptance evidence remain unchanged.
