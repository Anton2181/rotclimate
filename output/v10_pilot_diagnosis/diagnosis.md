# First V10 Earth pilot: diagnosis

Water accounting passes; rainfall skill fails. Frozen snapshots diagnose operators, not annual causal attribution.

| Region / mode | Mean annual model / observed (mm) | Monthly MAE (mm) | Rain settled + stores | Maximum cell (mm/year) |
|---|---:|---:|---|---:|
| california / storms | 1469.1 / 401.8 | 115.9 | True | 26575 |
| california / mean_only | 1315.9 / 401.8 | 108.3 | True | 22261 |
| iberia / storms | 1013.1 / 424.2 | 89.6 | True | 22785 |
| iberia / mean_only | 931.7 / 424.2 | 88.6 | False | 20098 |

## Findings and limits

All twelve saved years have verified array hashes and pass the declared physical budget checks. The frozen model/input fingerprint matches. These are accuracy failures, not a lost-water numerical instability.
California storms worsen monthly MAE by 7.60 mm relative to mean-only. Iberia storms worsen it by 0.96 mm, but the Iberia mean-only case fails the soil-settling limit (3.66 mm at p95 versus 1 mm); that pair is diagnostic, not a settled verdict.
The mean-flow cases already have extreme rain. The largest errors are not caused solely by transient storm frequency.
Air temperatures are reset by prescription every step. Condensation loses latent energy without warming the air. The resulting cold reservoir can continuously strip moisture from incoming air. This is a structural hypothesis supported by the source and frozen tendency diagnosis; a coupled run is required to test its annual consequences.

california: 13.4% of land exceeds 3,000 mm/year and supplies 70.4% of predicted land rain. At the maximum-rain cell, the frozen January lower condensation implies 1.50 K/hour of latent heating that the fixed-temperature engine cannot retain.
January frozen step: 8.62 mm/day mean land rain, 37.1% from the upper layer. Disabling only terrain drag in this frozen snapshot gives 8.28 mm/day. Lower-layer saturation matters as well as the diagnosed vertical return. The changed-flow snapshot is not a new equilibrium or a predicted annual reduction.

iberia: 11.1% of land exceeds 3,000 mm/year and supplies 77.5% of predicted land rain. At the maximum-rain cell, the frozen January lower condensation implies 1.31 K/hour of latent heating that the fixed-temperature engine cannot retain.
January frozen step: 6.25 mm/day mean land rain, 21.3% from the upper layer. Disabling only terrain drag in this frozen snapshot gives 6.08 mm/day. Lower-layer saturation matters as well as the diagnosed vertical return. The changed-flow snapshot is not a new equilibrium or a predicted annual reduction.

## Next mechanism test

Transport approximate moist static energy with water, retain latent heating during saturation adjustment, and relax temperatures toward the same observed reference on a declared finite time scale. Use exactly the same circulation first; then disable its terrain-drag term as a separate ablation. Keep observed rain out of the engine. Report water and energy budgets, temperature departures, rainfall extremes, and settling. A lower rainfall error caused by implausible temperature drift is not a validated improvement.
This follows the role of latent heating in [NOAA/GFDL moist adjustment](https://www.gfdl.noaa.gov/bibliography/related_files/yk9801.pdf) and the [NCAR static-energy formulation](https://www.ncl.ucar.edu/Document/Functions/Contributed/static_energy_atm.shtml). It is an approximate kinematic test, not a full atmospheric energy or momentum model.
Terrain/rain physics remains a later question: [Smith–Barstad (2004)](https://journals.ametsoc.org/view/journals/atsc/61/12/1520-0469_2004_061_1377_altoop_2.0.co_2.xml) also motivates airflow and cloud/evaporation treatment beyond instant fallout.

No seasonal simulation, calibration or atlas export was run in this analysis. The current atlas remains unchanged.
