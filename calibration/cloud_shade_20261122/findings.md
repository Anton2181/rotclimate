# e105 rain-cloud shading vs r51 (22 Nov 2026) — FAIL, parked default-off

Screens (policy v4 vs r51, scripts/screen_v4.py, output/cloud_shade_20261122):
| run | S55 | S49 | S_t |
|---|---|---|---|
| e105 1.5 K | 0.9972 | 1.0083 | 0.899 |
| e105 3 K | 1.0025 | 1.0214 | 0.838 |
| e105b 3 K, wet pow 2 | 0.9953 | 1.0120 | 0.852 |
| e105b 4 K, wet pow 4 | 0.9960 | 1.0139 | 0.846 |
Equatorial warm bias largely removed (central Amazon +1.6 -> 0.0 C, Kenya-Tanzania coast +1.7 -> +0.4) but every
wet land cools: seasonal-rain lands (Sahel, Burkina, N India, Bengal, N Queensland) in e105, wet mid-latitudes (Alps,
SE US, E Europe, prairies) in e105b, all already slightly too cold.

plan_U1 (30 evaluations, v4 objective with S49 <= 1 guard): infeasible, best S49 1.0002 with the shading refitted
down to 2.0 K and S_t back to 0.953. land_offset, wet_sun, subsidence_warming and dry_coupling do not buy the
mid-latitudes back. Sealed set s unopened. The tropical warm bias is not a missing shading term alone: the same
shade over wet extratropical land is wrong, so the tropical excess must come from somewhere tropical-specific
(the tropical SST / sea-air temperature, or convective heating of the column) — next lead.
