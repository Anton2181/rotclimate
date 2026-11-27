# K1 result: wide training REJECTED under the declared rule (27 Nov 2026)

Physics r58w (run output/ppe_20261127/edgez/zonal, 97 regions). Raw monthly T MAE: all 1.6269 C, dev31 1.6814 C.
Reference: the 31-region recipe on the same run, held-out dev31 1.5091 C.

| variant | clusters | best held-out all-97 | dev31 at that pair | worst region change | rule |
|---|---|---|---|---|---|
| link 1500 km | 12 (largest 39) | 1.5183 (0.8/0.0) | 1.5289 | u2_59n_76w +0.380 | fails |
| link 1000 km | 34 | 1.4783 (0.8/0.0) | 1.4848 | u2_59n_76w +0.560 | fails |

Every weight pair fails the declared per-region limit (no region worse by more than 0.25 C): isolated regions
far from any training neighbour (u2_59n_76w Hudson Bay, u2_27n_23e central Sahara) worsen by 0.4-1.8 C. The
averages improve (1000 km: all-97 -0.149 C vs raw; dev31 1.485 vs the 31-region recipe's 1.509), but nothing is adopted.
Next idea (needs its own declaration): fade the correction where a cell's features lie outside the training
regions' support, so isolated climates are left raw.
