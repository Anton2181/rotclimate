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
