# Spring timing (G3) under r63 — 28 Nov 2026

Spring-minus-autumn monthly bias (MAM - SON) over all 107 r63 reference cases: rms 2.0 C.
- Interiors cold in Apr-May (Volga -5.2/-5.5, Kazakh -4.8, E Europe -2.8, prairies, 56-58 N Siberia, BC).
- East-Asian coasts warm Mar-May (Japan +3, Hokkaido +4, E China +4).

Volga land budget (r63, lb.py): zonal column Apr 3.5 ~ Oct 4.3 (observed Apr 7.2 > Oct 5.4);
continental centre/amplification -3.5 in Apr; snow albedo -1.4; sea-air mixing ~-1.3.
Snow is gone by May, yet May-Jun stay 4-5 C cold: wet_cooling (-2..-6 C) under a spring rain
excess (May 61 vs 34 mm). Toggles on Volga: snow_albedo 0 +1.1 C Apr; wet_sun 0 +0.7; dry_coupling 0 nil.

Japan: land equilibrium Mar 9.8 vs observed 6.2 (sea-level) with the sea warmer still (13.7):
only continental cold-air advection can hold it; not a local land term.

e151 land_phase_cont_days (one-sided e121: deep-continental land cycle earlier; default off):
  ph10        S97 1.0422   ph10 + continental_mean 5.0  1.0458   ph18 + cm 4.5  1.1295
  Helps Volga/BC/E Europe/prairies, hurts Mongolia, Tibet, 40N94E, Hokkaido, Canadian Shield
  (already on time). REJECTED: same east-west trade as e121/e130/e138.
Conclusion: the spring error is not a phase or snow-albedo term. Leads: the spring rain excess
over western Eurasia (storm band too far north in May) and lacking cold advection to east coasts;
both need transport-level changes, deferred to the r65 recalibration.
