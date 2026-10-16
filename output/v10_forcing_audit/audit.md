# V10 heat result and circulation audit

All completed heat cases and frozen pilot provenance were verified. No new climate integration or calibration was performed.

| Region / case | Mean annual rain (mm) | Monthly rain MAE (mm) | Lower / upper T departure p95 (°C) | Settled |
|---|---:|---:|---:|---|
| california_mean_only_heat | 2745 | 224.65 | 13.55 / 18.02 | False |
| california_mean_only_heat_no_drag | 1652 | 137.86 | 10.02 / 15.79 | False |
| california_storms_heat | 2946 | 235.70 | 13.42 / 18.05 | True |
| california_storms_heat_no_drag | 1771 | 143.57 | 10.03 / 15.85 | False |
| iberia_mean_only_heat | 1296 | 118.65 | 18.70 / 11.77 | False |
| iberia_mean_only_heat_no_drag | 778 | 76.10 | 8.94 / 10.02 | False |
| iberia_storms_heat | 1416 | 122.99 | 18.72 / 11.77 | False |
| iberia_storms_heat_no_drag | 819 | 76.10 | 9.63 / 10.07 | False |

8/8 cases fail the declared temperature-departure screen; 7/8 fail rain/storage settling. California storms with drag: monthly rainfall MAE 115.87 → 235.70 mm. Temperature departures are from an assumed vertical profile, not independently observed temperatures at those levels. The atmospheric reference is needed to check the screen itself.

4/4 original controls now meet the unchanged settling checks; any extra unchanged years were verified from their saved arrays. The 24 new heat integrations took about 7.52 minutes in saved timings.

## Structural finding

The prescribed lower/upper representative heights differ by 7.12 km. Terrain slowdown in the lower flux is compensated by direct exchange with the upper layer. This treats a mountain-induced flux adjustment as deep atmospheric exchange, rather than resolving shallow uplift/return. With coupled static energy, moving lower-layer air to that height can strongly cool the upper layer before latent heating and other terms.

california: the monthly p95 absolute dry vertical-exchange contribution at the prescribed reference profile ranges 13.7–23.4 K/day. This is an operator diagnostic, not net atmospheric cooling, a measured reanalysis tendency, or a newly simulated climate.
iberia: the monthly p95 absolute dry vertical-exchange contribution at the prescribed reference profile ranges 6.5–13.0 K/day. This is an operator diagnostic, not net atmospheric cooling, a measured reanalysis tendency, or a newly simulated climate.

The coupled drag cases produce 60.3%–69.6% of domain rain in the upper layer. Without drag that share is 1.9%–17.5%. The cases still fail the declared screening criteria. Heat retention alone did not solve the rainfall excess; the simplified circulation/vertical representation needs an independent check.

## Atmospheric reference

### california

Offshore ocean mask: 184 model cells; 17 unique native reference cells. Nearest horizontal cells and log-pressure interpolation, not an independent sample at every model cell.

| Lower-level mean | Winter (Dec–Feb) | Summer (Jun–Aug) |
|---|---:|---:|
| Model eastward wind (m/s) | 5.87 | 3.48 |
| Reference eastward wind (m/s) | 4.53 | 1.26 |
| Reference northward wind (m/s) | -0.09 | -6.49 |
| Model target temperature (°C) | 10.39 | 13.17 |
| Reference air temperature (°C) | 6.58 | 13.20 |
| Model boundary mixing ratio (g/kg) | 7.21 | 8.68 |
| Reference mixing ratio (g/kg) | 4.46 | 5.27 |

2.5-degree 1981–2010 reanalysis versus 1970–2000 land/1971–2000 sea normals; nearest horizontal cells and log-pressure interpolation. Monthly means do not measure transient storm covariance. Native cells are repeated on the model grid, not independent samples. No terrain omega-ratio claim or precipitation scoring.

### iberia

Offshore ocean mask: 317 model cells; 28 unique native reference cells. Nearest horizontal cells and log-pressure interpolation, not an independent sample at every model cell.

| Lower-level mean | Winter (Dec–Feb) | Summer (Jun–Aug) |
|---|---:|---:|
| Model eastward wind (m/s) | 5.82 | 3.23 |
| Reference eastward wind (m/s) | 2.29 | 0.23 |
| Reference northward wind (m/s) | -0.77 | -3.98 |
| Model target temperature (°C) | 13.29 | 16.81 |
| Reference air temperature (°C) | 7.46 | 15.15 |
| Model boundary mixing ratio (g/kg) | 8.77 | 11.04 |
| Reference mixing ratio (g/kg) | 4.62 | 6.03 |

2.5-degree 1981–2010 reanalysis versus 1970–2000 land/1971–2000 sea normals; nearest horizontal cells and log-pressure interpolation. Monthly means do not measure transient storm covariance. Native cells are repeated on the model grid, not independent samples. No terrain omega-ratio claim or precipitation scoring.

Reference: NCEP/NCAR Reanalysis 1 monthly 1981–2010 climatology, data provided by [NOAA PSL, Boulder, Colorado, USA](https://psl.noaa.gov/). [Verified atmospheric-product metadata](https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/uwnd.mon.1981-2010.ltm.nc.html).
These are reanalysis estimates, not direct independent observations at every grid point. The normal period differs from the existing rainfall benchmark; this is an audit of structure, not a quantitative validation of rainfall skill.

## Next decision

Defer further extensions or fitting of these heat cases. First check the assumed mean circulation and vertical thermodynamic structure against the atmospheric reference. Use that evidence to choose between shallow/multiple-layer terrain circulation and revised mean-flow/boundary forcing. Separate terrain uplift from deep synoptic ascent. Keep all observed rainfall out of the forcing; no new climate integration or atlas publication is part of this audit.
