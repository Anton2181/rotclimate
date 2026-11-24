# Maritime range and phase (24 Nov 2026)

Trigger: plan_W9 finalist w1_011 failed fine28 (S28 1.0173) on the seasonal range of California and NZ.

## e125 continentality_maritime (separate slope for chi < 0.5), base mw70l25 (S97 0.9819)

| run | S97 | temperate | mediterranean |
|---|---|---|---|
| cm70 | 0.9813 | 1.002 | 1.007 |
| cm40 | 0.9810 | 0.999 | 1.011 |
| cm00 (no maritime damping) | 0.9808 | 0.996 | 1.016 |

All within noise. cm00 widens maritime ranges (W Europe range error -1.49 -> -0.92, NZ -1.21 -> -0.90,
Japan -1.42 -> -1.0) but British Isles overshoots (+0.46 -> +1.30) and monthly MAE barely moves.
Phase lag is unchanged (NZ +33 d, British Isles +28/+25, Patagonia +24, W Europe +19/+18).
Conclusion: range is not the main maritime error; the lag is. e125 parked (default 1 = off).

Winter land coupling at 50 deg: (S/Sref)^1.71 / 1.3 d gives ~20 d, plus radiative 26 d, so winter land air
is nearly pure advected sea air with the sea's late phase. Next: screen land_radiative_days and
land_coupling_insolation (screen_cpl.log).

## Coupling screen (base mw70l25)
| run | S97 | temperate | lag NZ / BI / Patagonia / W Europe |
|---|---|---|---|
| rad15 (land_radiative_days 26 -> 15) | 0.9808 | 1.004 | +34 / +27 / +25 / +19 |
| rad8 | 0.9788 | 1.001 | +32 / +26 / +24 / +18 |
| lci12 (land_coupling_insolation 1.71 -> 1.2) | 0.9793 | 1.001 | +33 / +27 / +24 / +19 |
ebm_land_ice 0.47 -> 0 (6-region test): warms maritime/inland cold biases (BI MAE 2.08 -> 1.92, E Europe
1.65 -> 1.45) but lag unchanged.

## Stage breakdown (scripts/land_budget.py, new 'sst' tap), British Isles, monthly C
| | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land_eq | -7.3 | -6.6 | -2.5 | 4.0 | 8.9 | 12.9 | 17.0 | 15.4 | 10.3 | 5.9 | -0.3 | -5.2 |
| model sea (land cells) | 2.6 | 1.2 | 1.2 | 2.5 | 4.7 | 7.7 | 11.9 | 13.8 | 12.8 | 10.7 | 7.7 | 4.9 |
| air | 3.5 | 2.6 | 2.7 | 4.1 | 6.3 | 9.3 | 13.4 | 14.6 | 13.3 | 11.3 | 8.4 | 5.7 |
| observed | 4.0 | 4.1 | 5.7 | 7.4 | 10.5 | 13.1 | 15.2 | 15.1 | 12.8 | 9.8 | 6.5 | 4.7 |
With observed SST (diagnostic only): air 7.8 7.6 8.0 9.2 10.7 12.7 14.8 15.4 14.4 12.9 10.8 9.0 (winter +4 C).
Model open sea vs WOA18: W Europe 5.7..19.3 vs 9.8..17.9; NZ 5.8..15.5 vs 12.1..17.5 (swing ~2x, winter 4-6 C cold).

Diagnosis: two compensating errors. (1) The air over maritime land is ~95 % sea air in winter (land coupling
~1/20 d against ~1 d advection), so it follows the sea; real British winter air sits ~5 C below the sea.
(2) The regional sea is ~2x too seasonal and 4-6 C too cold in winter, which keeps winters right but makes
spring 3-4 C cold and the cycle late. e98 (sea alone) failed in Nov because (1) then makes winters too warm.
Next: grid sst_damping x land_radiative_days on 6 regions.
