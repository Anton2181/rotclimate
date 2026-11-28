# Deep-root store revisited (e114b/e114c, 28 Nov 2026), vs r63

Zambia/Tanzania probe (r63): dry-season +2 C, wet-season rain half of observed although column water >= NCEP
(heat raises saturation, column RH ~0.6). Looser dry PW nudge (excess 0.15, rh0 0) does not cool: not the
vapour greenhouse.

e114b (tropical latitude fade on the deep store), screen_e114b.log, all FAIL:
| rt1 gain 3 p0 700 p1 400 lat 15-22 | S97 1.0052 [1.0003, 1.0103] |
| rt2 gain 3 p0 500 p1 500 lat 15-22 | S97 1.0060 |
| rt3 gain 6 p0 500 p1 500 lat 12-20 | S97 1.0087 |
Cause found: evaporation efficiency is soil_w / (0.75 cap); a deeper cap lowers it for the same water, so the
deep store DRIES the dry season (r_14s_32e warmer). e114c (root_abs_beta) judges wetness against the shallow
bucket instead.
