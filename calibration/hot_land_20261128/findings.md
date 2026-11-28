# North India cold plains / C1 (28 Nov 2026), vs r63

land_budget (north_india, cells < 300 m, r63): land_eq 1.5-3 C below observed_sl in the dry months; the air step
cools a further 1.3-2 C every month (transport; e108/e100b/e100c tried 24 Nov, calibration/south_asia_20261124).
cloud_radiation is 0 in r63: the whole cloud-stage cooling (-0.7 to -1.6 C) is the clear-sky longwave term
(local column vs the lw_ref_rh reference column at the zonal land temperature). Without it the plain is 0.5-1.6 C warmer.

e148 lw_obs_pw (observed NCEP PW in the longwave on Earth grids), screen_e148.log - neutral, CLOSED:
| lw05 0.5 | S97 0.9993 [0.9980, 1.0007] |
| lw10 1.0 | S97 0.9990 [0.9963, 1.0017] |
Northern dry tropics improve (Sahel, W Africa 0.96-0.98), southern dry tropics warm (Mato Grosso, Bolivia,
Kalahari 1.02-1.04): the same north/south split as e114c. North India gains only 0.1-0.5 C.

Conclusion across e114b/c, e146, e147/b, e148: every local land-column lever moves the northern (cold) and southern
(warm) dry tropics together. The split is hemispheric at equal rain, soil and height -> the next lead is something
that differs by hemisphere/season in the forcing: the zonal land reference (ZonalClimate land(lat, d)) in the two
hemispheres' dry seasons, or perihelion (SH summer sun 7 % stronger) handling in the land equilibrium.

Land budgets r63 (air vs observed_sl = observed + 4.35 K/km x elevation), run months:
| r_11n_2w (N, ~250 m)  | -1.9 -2.1 -1.3 -2.9 -2.9 -1.2 +0.3 +1.1 +0.6 -1.5 -2.6 -1.5 | dry season cold, wet season warm |
| r_14s_32e (S, 827 m)  | +1.1 +0.9 +0.9 +1.4 +1.9 +0.7 +0.9 +0.9 +0.8 +0.6 +1.0 +1.4 | near-constant offset |
The two are different problems, not one hemispheric cause:
- South (broad ~1 km plateaus: Zambia, Tanzania, Congo rim, Highveld): a constant offset = the 4.35 K/km sea-level
  reduction; at ~6.5 K/km it vanishes. The steep 3-4 km Andes are right at 4.35, so a uniform or relief-based lapse
  fails (e146, e147). Lead: lapse rate as a function of the column, e.g. moist-adiabatic lapse from the column
  temperature/humidity (warm moist tropics ~5-6 K/km near 1 km, smaller aloft) rather than one fitted constant.
- North (low dry tropics, Ganges plain): dry-season land column too cold (longwave vs a moist reference column,
  -0.7 to -1.6 C) plus transport; wet season slightly warm. C1, unchanged.
