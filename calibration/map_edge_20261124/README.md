# A1 map-edge test (plan_20261124), in progress

r52 on 13 regions with the map margin (pad) doubled, 1,100 -> 2,200 km; scored boxes unchanged.
Run: output/ppe_20261124/A1/r52_pad2200 (benchmark_local --pad-km 2200).

S13 (pad 2200 vs 1100) 1.098, T +10.8 %, P +8.7 %; mean |change in T_mae| 0.40 C, |change in P_loss| 0.12.

| region | T_mae 1100 -> 2200 | annual bias | P_loss | rain mm (obs) |
|---|---|---|---|---|
| s_2n_43e Somalia | 1.20 -> 1.31 | -0.15 -> -0.34 | 3.895 -> 3.982 | 3788 -> 3787 (445) |
| s_0s_28e Congo | 2.37 -> 1.88 | +2.35 -> +1.72 | 0.551 -> 0.277 | 776 -> 1220 (1523) |
| t_1s_63w Amazon | 1.38 -> 1.34 | +1.37 -> +1.33 | 0.462 -> 0.636 | 1568 -> 1244 (2663) |
| north_india | 3.24 -> 3.24 | -2.63 -> -2.70 | 0.581 -> 0.739 | 499 -> 350 (746) |
| bengal | 1.95 -> 2.38 | -0.84 -> -1.47 | 0.703 -> 0.890 | 998 -> 735 (2112) |
| algeria_sahara | 1.11 -> 1.25 | -0.30 -> -0.73 | 0.181 -> 0.263 | 17 -> 3 (25) |
| namibia_kalahari | 1.58 -> 1.36 | +0.82 -> +0.32 | 1.063 -> 1.009 | 23 -> 29 (236) |
| chile | 2.40 -> 2.30 | +1.72 -> +1.67 | 0.557 -> 0.562 | 288 -> 273 (479) |
| canadian_prairies | 2.61 -> 4.69 | -1.22 -> +1.55 | 0.199 -> 0.593 | 437 -> 688 (406) |
| us_midwest | 1.58 -> 2.53 | +0.82 -> +1.84 | 0.279 -> 0.349 | 766 -> 927 (878) |
| japan | 1.77 -> 1.91 | +0.57 -> +1.10 | 0.402 -> 0.423 | 1306 -> 1546 (1563) |
| western_europe | 1.85 -> 1.97 | -0.12 -> +0.41 | 0.272 -> 0.253 | 952 -> 928 (881) |
| southern_italy | 1.69 -> 1.25 | -0.54 -> +1.04 | 0.299 -> 0.290 | 673 -> 683 (797) |

Reading so far: the model's answer depends strongly on map size; r52 is fitted to 1,100 km maps. Somalia is
unchanged with Arabia on the map, so the map edge does not explain it at this margin.
Pending: pad 3,300 (convergence), prairie stage budgets at both margins (prairies_pad*.json).
