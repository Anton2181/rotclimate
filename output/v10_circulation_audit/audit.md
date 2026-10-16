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

No independent atmospheric grids were downloaded in this saved-only diagnosis. The prepared reference audit will compare monthly ocean-side wind vectors, humidity and vertical temperature/height profiles before another model redesign.

## Next decision

Defer further extensions or fitting of these heat cases. First check the assumed mean circulation and vertical thermodynamic structure against the atmospheric reference. Use that evidence to choose between shallow/multiple-layer terrain circulation and revised mean-flow/boundary forcing. Separate terrain uplift from deep synoptic ascent. Keep all observed rainfall out of the forcing; no new climate integration or atlas publication is part of this audit.
