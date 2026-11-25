# e132 probe: clear-sky sunshine (cloud_radiation, e4/e43) under r56 - REJECTED (25 Nov 2026)

Diagnosis first (scripts/land_budget.py, now with LB_MAX_ELEV and a sea-level-equivalent observed row): the earlier
budget compared sea-level air with observations at elevation. Like for like, north India's plains (< 800 m) are 1-4 C
too cold (Jan air 12.6 vs 16.7 sea-level obs; air below both land_eq 14.8 and the sea 18.3, so transport cools it,
as in calibration/south_asia_20261124), Najd 2-4 C too cold with air ~1 C under its land_eq. r56 has cloud_radiation 0:
a clear dry sky only loses longwave (cloud_longwave 0.22), with no extra sunshine.

Screen vs r56 (97 dev regions):
| set | S97 [90 %] | notes |
| cloud_radiation 0.5, domain ref | 0.9997 [0.9986, 1.0008] | neutral |
| cloud_radiation 1.0, domain ref | 0.9996 [0.9974, 1.0019] | arid 0.994; north India unmoved |
| cloud_radiation 0.5, earth ref (e43) | 1.0031 | tropical_wet 1.032 |
| cloud_radiation 1.0, earth ref | 1.0075 [1.0009, 1.0138] | arid 0.985 but S Amazon / Congo +0.2-0.4 C (s_0s_28e, r_7s_59w, u_5s_66w 1.09-1.13) |

Reading: the same trade-off as B5 (calibration/hot_bias_20261124): anything that warms clear, dry land also heats the
southern tropical interiors, which the model makes too dry (too clear). That moisture deficit, not a land term, blocks
the hot-tail fix. Next lead: moisture supply into deep tropical interiors. cloud_radiation stays 0.
