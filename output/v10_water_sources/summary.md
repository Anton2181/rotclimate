# Water sources and paired synthetic weather

Status: complete; 20/20 cases complete.

Fixed physics and parameters. Last-vapor-source tracers do not feed back into climate. No download, optimization, best-seed selection or atlas update.

| Case | Rain / reference | Monthly MAE | Boundary / ocean / land share of land rain | Settled |
|---|---:|---:|---|---|
| california_uniform_s41 | 1.18 | 40.07 | 92% / 8% / 0% | True |
| california_spatial_s41 | 0.10 | 30.33 | 91% / 8% / 0% | True |
| iberia_uniform_s41 | 0.42 | 32.20 | 83% / 17% / 0% | True |
| iberia_spatial_s41 | 0.05 | 35.02 | 64% / 36% / 0% | True |
| california_uniform_s67 | 1.17 | 39.95 | 92% / 8% / 0% | True |
| california_spatial_s67 | 0.10 | 30.47 | 92% / 8% / 0% | True |
| iberia_uniform_s67 | 0.41 | 32.22 | 83% / 17% / 0% | True |
| iberia_spatial_s67 | 0.05 | 35.11 | 64% / 36% / 0% | True |
| california_uniform_s103 | 1.17 | 39.86 | 92% / 8% / 0% | True |
| california_spatial_s103 | 0.09 | 30.52 | 92% / 8% / 0% | True |
| iberia_uniform_s103 | 0.42 | 32.25 | 83% / 17% / 0% | True |
| iberia_spatial_s103 | 0.05 | 35.04 | 63% / 37% / 0% | True |
| california_uniform_s149 | 1.19 | 40.32 | 92% / 8% / 0% | True |
| california_spatial_s149 | 0.10 | 30.32 | 91% / 9% / 0% | True |
| iberia_uniform_s149 | 0.42 | 32.13 | 83% / 16% / 0% | True |
| iberia_spatial_s149 | 0.05 | 34.97 | 64% / 36% / 0% | True |
| california_uniform_s211 | 1.16 | 39.57 | 92% / 7% / 0% | True |
| california_spatial_s211 | 0.10 | 30.35 | 91% / 9% / 0% | True |
| iberia_uniform_s211 | 0.42 | 32.29 | 83% / 17% / 0% | True |
| iberia_spatial_s211 | 0.05 | 35.00 | 64% / 35% / 0% | True |

## Completed matched wind contrasts

| Region / storm seed | Spatial − uniform annual rain | Spatial − uniform coastal winter rain |
|---|---:|---:|
| california / 41 | -433.3 mm | -273.5 mm |
| iberia / 41 | -154.7 mm | -123.0 mm |
| california / 67 | -430.6 mm | -271.7 mm |
| iberia / 67 | -154.3 mm | -123.1 mm |
| california / 103 | -432.1 mm | -274.2 mm |
| iberia / 103 | -155.6 mm | -124.7 mm |
| california / 149 | -435.8 mm | -273.7 mm |
| iberia / 149 | -155.3 mm | -123.6 mm |
| california / 211 | -425.4 mm | -268.4 mm |
| iberia / 211 | -154.2 mm | -120.7 mm |

Initial-vapor shares, coast/interior and winter source amounts, per-source gross import/export and physical budgets are in state.json and annual checkpoints. Land evaporation resets the source tag; this is not original molecular ancestry. Domain gross transport is not a regional precipitation efficiency. Five synthetic catalogues measure sensitivity to this generator, not actual weather uncertainty. Warm-up cycles and cells are not independent climate replicates. A partial batch is not the verdict from all five paired catalogues. Existing broad screens are reported, not used to pick a winner. No atlas promotion.
