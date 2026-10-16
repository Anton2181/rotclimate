# V10 Earth rainfall pilot

Fixed physics, observed temperature/SST forcing; no calibration and no atlas publication.
WorldClim 1970–2000 land normals; NOAA OISST 1971–2000 sea normals (one-year period difference).
Sea data provided by [NOAA PSL, Boulder, Colorado, USA](https://psl.noaa.gov/). Land data: [WorldClim 2.1](https://www.worldclim.org/data/worldclim21.html).
A three-year repeated forcing cycle is a settling check, not three independent climate samples.

| Region / mode | Settled | Annual bias (mm) | Annual RMSE (mm) | Monthly MAE (mm) | Winter fraction MAE |
|---|---|---:|---:|---:|---:|
| california / storms | True | 1067.3 | 3452.7 | 115.9 | 0.283 |
| california / mean_only | True | 914.1 | 2948.6 | 108.3 | 0.242 |
| iberia / storms | True | 588.9 | 2429.6 | 89.6 | 0.285 |
| iberia / mean_only | False | 507.5 | 2248.5 | 88.6 | 0.265 |

Unsettled cases are diagnostic only. Small water-budget errors establish accounting, not rainfall skill.
No target-zone labels or observed precipitation enter the transport, evaporation or weather forcing.

california: storms minus mean-only monthly MAE = +7.60 mm (negative favours storms); eligible settled comparison: True.

iberia: storms minus mean-only monthly MAE = +0.96 mm (negative favours storms); eligible settled comparison: False.
