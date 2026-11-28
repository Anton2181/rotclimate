# Kalahari (worst region, loss 1.89) rain chain, r63, 28 Nov 2026

namibia_kalahari (1,078 m): model summer rain 0-1 mm/month vs 20-50 observed; summer +2 C; column 13-19 vs NCEP 17-25 mm.
Rain components (scratchpad rainparts), summer run months 6-9:
1. Wet PW nudge extended to 30 deg (lat0 30, lat1 35, strength 2): column -> 22 mm (near NCEP), still no rain.
2. Observed-descent cap off (convective_omega 0): no change (not the cap; NCEP 500 hPa omega here is weak
   descent in midsummer, ascent in spring - genuine, Sahel/Queensland phases align).
3. sverdrup (1.20): the dynamic factor 0.26-0.33 -> 0.86-1.10 when off; equatorward low-level flow reads as descent.
4. Column capacity Ws 56-64 mm (real ~50): physics-v3 Ws = w_sat(T_col - 0.5 lapse h) credits half the plateau
   height -> e149 ws_height_frac (default 0.5): at 1.0 Ws 49-56, RH 0.33-0.41.
5. With 1+3+4: RH 0.35-0.41 just above rh_threshold 0.317, dyn ~1, rain still ~0.1 mm/day (obs ~1.6): the gate
   ((rh - 0.317)/0.683)^1.5 ~ 0.05 and the Bretherton convective closure exp(11.4 (rh - r0)) cannot fire at
   semi-arid column RH. rh_spread 0.1 (e22) adds nothing.
Conclusion: the Kalahari (and interior Australia, same signature) needs a heat-low convection trigger (surface
heating x boundary-layer moisture) that column-RH closures lack. New physics; risk = Sahara/Arabia summer rain.
e149 screened on its own (plateaus everywhere: Zambia wet-season RH ~0.6 at 800-1,300 m is the same capacity issue).
