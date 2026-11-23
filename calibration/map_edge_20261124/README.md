# A1 map-edge test (plan_20261124), DONE

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

## Pad 3,300 km (12 regions, Somalia dropped)
| region | T_mae 1100 -> 2200 -> 3300 | bias | P_loss |
|---|---|---|---|
| Congo | 2.37 -> 1.88 -> 1.78 | +2.35 -> +1.72 -> +1.58 | 0.551 -> 0.277 -> 0.347 |
| Amazon | 1.38 -> 1.34 -> 1.26 | +1.37 -> +1.33 -> +1.19 | 0.462 -> 0.636 -> 0.500 |
| north_india | 3.24 -> 3.24 -> 3.14 | -2.63 -> -2.70 -> -2.62 | 0.581 -> 0.739 -> 0.719 |
| bengal | 1.95 -> 2.38 -> 2.58 | -0.84 -> -1.47 -> -1.86 | 0.703 -> 0.890 -> 0.798 |
| algeria_sahara | 1.11 -> 1.25 -> 1.21 | -0.30 -> -0.73 -> -0.72 | 0.181 -> 0.263 -> 0.287 |
| namibia | 1.58 -> 1.36 -> 1.25 | +0.82 -> +0.32 -> -0.03 | 1.063 -> 1.009 -> 0.911 |
| chile | 2.40 -> 2.30 -> 2.39 | +1.72 -> +1.67 -> +1.89 | 0.557 -> 0.562 -> 0.544 |
| canadian_prairies | 2.61 -> 4.69 -> 5.32 | -1.22 -> +1.55 -> +2.29 | 0.199 -> 0.593 -> 0.690 |
| us_midwest | 1.58 -> 2.53 -> 3.28 | +0.82 -> +1.84 -> +2.89 | 0.279 -> 0.349 -> 0.388 |
| japan | 1.77 -> 1.91 -> 2.28 | +0.57 -> +1.10 -> +1.66 | 0.402 -> 0.423 -> 0.457 |
| western_europe | 1.85 -> 1.97 -> 1.80 | -0.12 -> +0.41 -> +0.64 | 0.272 -> 0.253 -> 0.239 |
| southern_italy | 1.69 -> 1.25 -> 1.56 | -0.54 -> +1.04 -> +1.43 | 0.299 -> 0.290 -> 0.299 |

S12 vs pad 1100: 1.121 (2200), 1.149 (3300). Mean |change in T_mae| 0.43 (1100->2200), 0.25 (2200->3300): not converged.

## Prairie stage budget (prairies_pad1100.json, prairies_pad2200.json)
All land-column stages agree within 0.5 C; the whole difference is the air (heat transport) step: January air
-9.2 C (pad 1100) vs -1.0 C (pad 2200), observed -14.2. With the Pacific upwind on the map, westerly transport
carries marine warmth across the Rockies into the interior.

## Conclusions
1. The atlas is NOT a whole world: it is a 3,680 x 1,703 km map with the same 1,100 km pad (config map_width_mi,
   map_height_mi, pad_km; procedural off-map fill). Calibrating at pad 1,100 therefore matches deployment; switching
   calibration to large maps is NOT warranted (and A4, a whole-Earth run, is dropped).
2. But the model is strongly domain-sensitive: continental interiors downwind of an ocean warm 2-3 C in winter
   as the upwind ocean comes onto the map (prairies, Midwest, Japan, Europe). At pad 1,100 the edge boundary is
   partly compensating a physics error: winter marine heat crosses mountain ranges too freely (B1). The atlas's
   own interiors depend on what its procedural off-map fill puts upwind.
3. Somalia is unchanged with Arabia on the map: not an edge effect. The Congo gains rain with more domain (edge
   humidity starves it at pad 1,100).
4. Method change: B1-type mechanisms are also scored on this 12-region set at pad 2,200 as a domain-robustness
   diagnostic; a mechanism that cuts the pad 1,100 -> 2,200 drift is preferred over one that only improves pad 1,100.
