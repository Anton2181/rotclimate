# Deep-root store at low rain thresholds (e114, 24 Nov 2026) - PARKED, no adoption

Screen vs r53 (v5 pool, 61 regions), log screen_e114low.log:
| set | S61 [90 %] | T | P | S49 |
| rootA root_gain 3, p0 500, p1 500 | 1.0035 [0.997, 1.010] | +0.8 % | -0.1 % | 1.005 |
| rootB root_gain 6, p0 500, p1 500 | 1.0087 [1.000, 1.019] | +1.2 % | +0.6 % | 1.006 |
| rootC root_gain 3, p0 700, p1 400 | 1.0007 [0.996, 1.006] | +0.5 % | -0.3 % | 1.003 |

A deeper store helps the Sahel / Mali / Darfur / Zambia (0.88-0.95) but cools the already cold mid-latitude wet
lands (western Europe, Alps, Pacific NW, Bengal 1.05-1.07) and leaves the southern Amazon worse (t_10s_66w T MAE
1.66 -> 1.86).

Why the southern Amazon does not respond (t_10s_66w, r53, run calendar = real months rolled by 6):
  model rain  0.2 0.2 0.2   8  50  95 101 139 146 126   9  0.2  mm/month
  observed   23  37  84 139 196 229 265 247 230 160  92  36
  model T   24.5 26.7 30.0 32.1 30.4 28.0 27.8 28.1 28.0 26.9 26.0 24.9
  observed  25.1 26.1 26.9 27.3 26.9 26.5 26.5 26.5 26.6 26.4 25.9 24.9
The wet season is too short: it starts ~2 months late (run months 3-4 = real Sep-Oct, observed 84-139 mm, model
0-8) and ends a month early (run month 11 = real May, 92 obs vs 9). The +3 to +5 C error is the pre-onset heat of
those missing months. No soil store fixes rain that never falls; the lead is the onset of the southern
continental wet season (the land rain belt's southward reach and its moisture supply in spring), not the land
energy balance. e114 stays default off.
