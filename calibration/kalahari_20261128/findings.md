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

e149 (global ws_height_frac), screen_e149.log - FAIL: 0.75 S97 1.0075, 1.0 S97 1.0354 (highland 1.35/1.86:
Altiplano, Tibet, Great Basin, Mongolia, California far too wet).
e149b (first 1.5 km only, tropical fade), screen_e149b.log: wb1 (15-25) 0.9942, wb2 (10-18) 0.9911 [0.9834, 0.9980],
wb3 (0.75) 0.9957. wb2 dev6 PASS vs r63 (arid 1.0015, tropical_dry 0.962), fine28 1.000, sealed HH FAIL S 1.0115
[0.998, 1.038] (rain +3.7 %: already-wet boxes wetter). CLOSED, r63 stays. The dev gain is in the drier tropical
plateaus (Katanga, Zambia, CAR); wet lowland boxes get wetter. A wetness gate (e.g. only where the column is below
NCEP PW) would be the next variant, but HH is spent and the next run needs a new set.

e149c (dry-only gate), screen_e149c.log: wc1 (10-18) S97 0.9920 [0.9866, 0.9966], worst regime 1.000; dev6 PASS vs r63,
fine28 1.000, sealed II FAIL S 1.0016 [0.999, 1.013] (neutral: five of six boxes lowland). CLOSED, r63 stays.
The development gain sits in a handful of tropical plateau boxes (CAR, Katanga, Angola, Ecuador); new sets drawn at
random in 0-18 deg mostly miss them, so two sealed sets (HH, II) did not confirm it.
