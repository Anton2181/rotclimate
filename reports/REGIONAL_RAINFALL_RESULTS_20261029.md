# Regional complete-month rainfall results

Pooled primary score is withheld until all six primary wet/dry months complete and pass saved-state budgets.

north india: wet/dry MAE 7.254/8.092 mm/day versus r39 5.955; mean wet/dry rainfall 0.861/0.000 versus observed 8.092.

mexico: wet/dry MAE 1.861/3.023 mm/day versus r39 2.088; mean wet/dry rainfall 1.225/0.000 versus observed 3.023.

4 of7 candidate months are complete. All complete fields are scored; no incomplete-month loss is substituted.

| Region | Profile | Observed | Model | MAE | Bias |
|---|---|---:|---:|---:|---:|
| north_india | r39 | 8.0923 | 2.4080 | 5.9545 | -5.6843 |
| north_india | wet | 8.0923 | 0.8613 | 7.2542 | -7.2309 |
| north_india | dry | 8.0923 | 0.0000 | 8.0923 | -8.0923 |
| mexico | r39 | 3.0234 | 1.5907 | 2.0883 | -1.4326 |
| mexico | wet | 3.0234 | 1.2252 | 1.8608 | -1.7982 |
| mexico | dry | 3.0234 | 0.0000 | 3.0234 | -3.0234 |
| pacific_nw | r39 | 0.6806 | 0.8383 | 0.2051 | 0.1576 |
| pacific_nw | wet | 0.6806 | pending | pending | pending |
| pacific_nw | dry | 0.6806 | pending | pending | pending |
| mexico | wet450 (numerical) | 3.0234 | pending | pending | pending |

The primary objective and masks were committed before prediction. Scores are area-weighted per case, then averaged equally across three regions and two initializations. Mexico wet450s is excluded from that primary mean. Geographic bins, wet/dry differences, numerical sensitivity and cold-liquid diagnostics are retained in the downloadable JSON.

The reference controls exactly reproduce archived r39 monthly float32 fields and pass strict checks. Raw annual r39 output is reaggregated by Gregorian overlap; observed normals and all model predictions use identical centered224-km footprints.

These are reused summer region/month pairs under fixed simulated lateral reservoirs, not independent global forecasts, held-out tests or annual validation. Flat terrain, missing nonlinear momentum, liquid-only physics and a partial380-hPa atmosphere remain limitations. No calibration or physics adoption. Checkpoint continuation after an environment interruption retained the daily prefix and independently reproduced a complete subsequent day byte exactly for both India branches. Original per-step histories before interruption were not flushed and are not fabricated.
