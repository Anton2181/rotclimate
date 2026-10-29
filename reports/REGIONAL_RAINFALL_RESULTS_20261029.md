# Regional complete-month rainfall results

Pooled primary score is withheld until all six primary wet/dry months complete and pass saved-state budgets.

north india: wet/dry MAE 7.254/8.092 mm/day versus r39 5.955; mean wet/dry rainfall 0.861/0.000 versus observed 8.092.

mexico: wet/dry MAE 1.861/3.023 mm/day versus r39 2.088; mean wet/dry rainfall 1.225/0.000 versus observed 3.023.

Even if every remaining primary case had zero MAE, the candidate mean would be at least 3.417 mm/day versus r39 2.749. This configuration therefore cannot beat the declared objective. This is a mathematical bound, not its completed pooled score; all planned cases continue.

5 of7 candidate months are complete. All complete fields are scored; no incomplete-month loss is substituted.

| Region | Profile | Observed | Model | MAE | Bias |
|---|---|---:|---:|---:|---:|
| north_india | r39 | 8.0923 | 2.4080 | 5.9545 | -5.6843 |
| north_india | wet | 8.0923 | 0.8613 | 7.2542 | -7.2309 |
| north_india | dry | 8.0923 | 0.0000 | 8.0923 | -8.0923 |
| mexico | r39 | 3.0234 | 1.5907 | 2.0883 | -1.4326 |
| mexico | wet | 3.0234 | 1.2252 | 1.8608 | -1.7982 |
| mexico | dry | 3.0234 | 0.0000 | 3.0234 | -3.0234 |
| pacific_nw | r39 | 0.6806 | 0.8383 | 0.2051 | 0.1576 |
| pacific_nw | wet | 0.6806 | 0.5086 | 0.2699 | -0.1720 |
| pacific_nw | dry | 0.6806 | pending | pending | pending |
| mexico | wet450 (numerical) | 3.0234 | pending | pending | pending |

The primary objective and masks were committed before prediction. Scores are area-weighted per case, then averaged equally across three regions and two initializations. Mexico wet450s is excluded from that primary mean. Geographic bins, wet/dry differences, numerical sensitivity and cold-liquid diagnostics are retained in the downloadable JSON.

The reference controls exactly reproduce archived r39 monthly float32 fields and pass strict checks. Raw annual r39 output is reaggregated by Gregorian overlap; observed normals and all model predictions use identical centered224-km footprints.

These are reused summer region/month pairs under fixed simulated lateral reservoirs, not independent global forecasts, held-out tests or annual validation. Flat terrain, missing nonlinear momentum, liquid-only physics and a partial380-hPa atmosphere remain limitations. No calibration or physics adoption. Checkpoint continuation after an environment interruption retained the daily prefix and independently reproduced a complete subsequent day byte exactly for both India branches. Original per-step histories before interruption were not flushed and are not fabricated.

Complete-month modeled water identities on the frozen footprints, all rates mm/day. These are inferred model stores/fluxes, not observed evaporation or water-origin tracers. P=E+net import−vapor storage change.

| Case | Rain | Net evaporation | Net import | Vapor change | Soil change |
|---|---:|---:|---:|---:|---:|
| north_india_wet_900 | 0.86133 | 1.43335 | -0.80956 | -0.23753 | -0.57202 |
| north_india_dry_900 | 0.00000 | 0.00000 | -0.07089 | -0.07089 | 0.00000 |
| mexico_wet_900 | 1.22516 | 1.89607 | -0.89747 | -0.22656 | -0.67091 |
| mexico_dry_900 | 0.00000 | 0.01297 | -0.28623 | -0.27326 | -0.01297 |
| pacific_nw_wet_900 | 0.50857 | 0.75911 | -0.32742 | -0.07688 | -0.25054 |
