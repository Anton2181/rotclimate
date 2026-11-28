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

e114c (root_abs_beta true), screen_e114c.log - CLOSED, neutral, no adoption:
| rc1 gain 3 p0 700 p1 400 lat 15-22 | S97 1.0024 [0.9973, 1.0077] | arid 1.007 |
| rc2 gain 6 p0 500 p1 500 lat 12-20 | S97 1.0024 [0.9972, 1.0077] | (identical: depth saturates; the effect is the wetness reference) |
| rc3 gain 2 p0 500 p1 500 lat 15-22 | S97 1.0033 [0.9988, 1.0077] | |
Right direction in the warm southern dry tropics (Zambia u3_9s_32e +1.17 -> +0.89 C, Mato Grosso u3_11s_55w +1.35 ->
+0.80, Angola s3_2s_15e 0.77), but the northern dry tropics, already too cold, cool further (r_11n_2w -1.33 -> -1.79,
s3_7n_10w, u3_11n_18e, Nicaragua s2_12n_85w). Rain amount does not separate them (both ~1,000 mm, 5-6 month dry
seasons). The asymmetry (south warm, north cold at the same rain) is the lead: the northern dry tropics' cold bias
(C1) and the southern warm bias need one shared cause, not a soil store. root_* stays default off.
