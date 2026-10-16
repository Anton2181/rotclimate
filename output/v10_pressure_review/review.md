# Completed pressure-based heat-transport comparison

Four cases / 16 cycles; 16.67 saved minutes. All settle.

| Case | Rain MAE | MAE change | Rain / reference | Minimum coverage | Prescribed work, W/m² | Broad screen |
|---|---:|---:|---:|---:|---:|---|
| california_uniform | 40.07 | -1.59 | 1.18 | 82.9% | 23.87 | True |
| iberia_uniform | 32.20 | +0.13 | 0.42 | 76.0% | 14.29 | False |
| california_spatial | 30.33 | +0.45 | 0.10 | 54.3% | 16.25 | False |
| iberia_spatial | 35.02 | +0.11 | 0.05 | 34.2% | 5.69 | False |

The dry-law correction passes its manufactured limits but does not resolve regional rain placement or the spatial-wind drought. California uniform-flow MAE improves modestly but remains worse than zero rain; other cases worsen. Diagnosed work is exchange with an unsolved prescribed circulation, not an independently verified total-energy budget. No atlas promotion.

Next priority: measure missing transient moisture/thermal forcing rather than launch another frequency sweep. Boundary imports, cloud/transport physics and vertical quadrature remain unresolved. No further seasonal run started here.
