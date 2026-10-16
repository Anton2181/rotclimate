# V10 heat and terrain mechanism test

Fixed circulation and observed temperature relaxation targets; no calibration or atlas update.
Eight coupled cases with five-day temperature relaxation, plus at most two unchanged baseline settling years.

| Region / case | Monthly rain MAE (mm) | Rain p99 (mm/year) | Settled | Lower / upper T departure p95 (°C) |
|---|---:|---:|---|---:|
| california_storms original (year 3) | 115.87 | 19485 | True | prescribed |
| california_mean_only original (year 3) | 108.27 | 16146 | True | prescribed |
| iberia_storms original (year 3) | 89.57 | 11521 | True | prescribed |
| iberia_mean_only original (year 4) | 88.61 | 9845 | True | prescribed |
| california_storms_heat | 235.70 | 34976 | True | 13.42 / 18.05 |
| california_mean_only_heat | 224.65 | 32444 | False | 13.55 / 18.02 |
| california_storms_heat_no_drag | 143.57 | 23350 | False | 10.03 / 15.85 |
| california_mean_only_heat_no_drag | 137.86 | 18936 | False | 10.02 / 15.79 |
| iberia_storms_heat | 122.99 | 24530 | False | 18.72 / 11.77 |
| iberia_mean_only_heat | 118.65 | 22103 | False | 18.70 / 11.77 |
| iberia_storms_heat_no_drag | 76.10 | 12575 | False | 9.63 / 10.07 |
| iberia_mean_only_heat_no_drag | 76.10 | 11381 | False | 8.94 / 10.02 |

Lower rainfall error is not sufficient: inspect water/static-energy budgets, settling, and temperature departures.
Provisional departure guards: monthly p95 <=5°C lower / <=10°C upper. These are declared screening choices, not an independently validated energy closure.
The heat case changes thermal transport, latent feedback, and finite relaxation together; it does not isolate each one separately. The no-drag case additionally removes only the terrain term from the prescribed circulation; real terrain, air masses, temperatures and reference rain are retained.
Observed temperatures remain relaxation targets and boundary forcing. Do not claim independent temperature prediction. Surface evaporation latent enthalpy and the relaxation reservoir are explicit external energy inputs; this is not a closed Earth energy budget.
