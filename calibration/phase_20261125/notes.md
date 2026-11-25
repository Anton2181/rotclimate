# East-coast early phase under r56 (25 Nov 2026)
phase_lag r56: west coasts late (NZ +28 d, British Isles +18, BC +11), east coasts early (Japan -9, Hokkaido -9,
east China -7, Nova Scotia -6, Korea -5); east coasts spring +2.5 to +5.6 C, Jul-Aug -1.5 to -2.7 C.
e135 probe (not kept): coastal land seasonal anomaly blended toward the sea's, x exp(-coast/100 km) x chi.
Zonal sea, 0.5: Japan MAE 1.63 -> 1.61, Hokkaido 2.48 -> 2.23. Model's own nearby sea (last step), 0.5 / 1.0:
Japan 1.60 / 1.68, Hokkaido 2.24 / 1.96, Nova Scotia 1.91 / 2.15 (r56 1.78). Only damps amplitude; the spring
overshoot stays. Next: compare the model's spring sea there with WOA (sstdiag) and spring snow / fog on land.
e121 land_phase_days under r56: 10 / 20 / 30 d -> S97 1.0098 / 1.0346 / 1.0711 (continental 1.05-1.22, highland
1.05-1.27; Japan 0.95-0.96); 20 d + e134b 1.0335. Rejected again (as at r53).

sstdiag vs WOA18 (r56): the sea off the east coasts swings too little (Japan 7.4 C peak-to-peak vs 12.4; Nova Scotia
9.8 vs 15.5; spring +1-2 C, August -3 to -4 C), but the land barely feels it (high chi). The spring error is the land
equilibrium itself: Japan April land_eq 17.2 vs obs air 10.9, May 21.2 vs 15.7; Nova Scotia May 12.5 vs 8.3.
e136 probe (not kept): sst_damping x clip(1 + k x basin_side) (less damping off east coasts), k 1 / 2: Japan MAE
1.84 -> 1.80 / 1.78, Nova Scotia 1.95 -> 1.97, British Isles / NZ unchanged. Next lead: why the east-coast spring land
equilibrium runs 4-6 C hot (spring cloud: Baiu / sea fog under onshore flow off a cold sea; land_eq has no
onshore-cold-sea cloud term).

## e136 + e137 probe under r57 (26 Nov 2026), not kept
e137: coastal land in continental air cools toward a colder nearby sea (model SST, ~400 km): coast_cool x
exp(-coast/km) x chi x (Tl - sea)+, with e136 (less e98 damping off east coasts). Five-region test (MAE vs r57
japan 1.84 / korea 1.77 / nova_scotia 1.94 / hokkaido 2.67 / british_isles 1.48):
| coast_cool, side, km | japan | korea | nova_scotia | hokkaido | british_isles |
| 0.3, 0, 100 | 1.83 | 1.75 | 1.89 | 2.59 | 1.52 |
| 0.3, 1, 100 | 1.78 | 1.73 | 1.89 | 2.61 | 1.52 |
| 0.6, 1, 100 | 1.77 | 1.72 | 1.84 | 2.52 | 1.56 |
| 2.0, 1, 100 | 1.75 | 1.68 | 1.78 | 2.20 | 1.75 |
| 3.0, 1, 250 | 1.90 | 1.85 | 2.61 | 2.24 | 2.10 |
The cooling lands in summer, not spring: in the model's March-April the nearby sea is not colder than the land, so
there is nothing to cool toward. The east-coast spring error is the land column's spring warming rate there, while
interiors and west coasts (Volga -4.6, Kazakh -4.0, prairies -3.5, BC -3.7 C in April) run cold in spring: regional,
opposite signs; no global lever. PARKED.
