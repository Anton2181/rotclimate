# B5 hot-land cold bias (24 Nov 2026, r53) - PARKED

Pattern (r53, annual T bias by real latitude of the 61 dev regions): 5-20 S mean +1.26 C (9 of 10 too warm:
southern Amazon, southern Congo, Zambia, Tanzania); 5-20 N mean -1.06 C (Sahel, Deccan; also north India -2.6,
Najd -2.6, Iran -2.1 further north). The cold bias is year-round (north India -2 to -3 C every month; Najd -4 to
-5 C Jul-Sep). Not a mirroring artefact: cross-equatorial transport sign is right, and mirroring itcz_mean (W5)
made the south warmer still (drier).

Screens vs r53 (v5 pool; gates warm_c 20, mean_c 12):
| set | S61 [90 %] | notes |
| dry_heating 1 | 1.0070 [1.000, 1.014] | Najd 0.92, Iran / Deccan / north India 0.96-0.98; southern dry tropics, Namibia, Tripolitania 1.05-1.10 |
| + e113 cold-sea exemption (21 C, 300 km) | 1.0061 | Namibia 1.102 -> 1.094 only: the region is the Kalahari interior |
| dry_heating 2 + e113 | 1.0193 | |
| dry_heating 2, arid gate 0.5 | 1.0006 [0.998, 1.004] | arid gate drops the seasonal north India / Deccan gain |
| dry_heating 3, arid 0.5 | 1.0012 | |
| dry_heating 2, arid 0.3 | 1.0023 | |

Reading: the land column has no handle that separates the long-dry northern subtropics (too cold) from the
short-dry, forested southern tropics and the Kalahari plateau (too warm); soil dryness in the 69 mm bucket is
similar in both. Candidate structural work (not started): a deep-root / forest water store that keeps tropical
forest evaporating through a short dry season (cools the south), separate from the bucket that gates dry heating.
e113 stays in the code, default off.

## e114 root-zone depth (probe, 24 Nov 2026) - no effect; the cause is missing rain
rainprobe r53 (run calendar; mirrored): southern Amazon t_10s_66w rains ~750 mm/yr against ~1,900 observed, so
e114 (rain above 1,200 mm deepens the bucket) never engages (root_gain 3: Jan T 24.5 -> 23.6 only). Its dry
season is rainless (0.2 mm/month vs 22-84 obs) and 3-5 C too hot (April 32.1 vs 27.3). Column water is 28-32 mm
in the wet season and 15 mm in the dry (observed Amazon precipitable water ~45-55 / ~30-35). r_7s_59w the same
(wet season 110-175 mm/month vs 215-320). The southern-tropics warm bias is a column-moisture deficit in
continental interiors fed from a sea 1,500-2,500 km upwind (beyond the 1,100 km pad), not a soil or radiation
term. e114 stays in the code, default off. Lead: moisture supply into deep continental interiors (edge humidity
for land boundaries, e81 edge_inner, recycling efficiency), tested at pad 1,100 and 2,200.
