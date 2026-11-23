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

# e106 separate land ITCZ annual mean vs r51 (22 Nov) — FAIL, parked default-off
Diagnosis (r51 monthly, local-season months): West African rains a month early and late (Sahel/Burkina 4-5 C too cold
May-June), southern Amazon/Congo rains two months late and half the amount (3-4 C too warm before the rains).
| run | S55 | S49 | S_t |
|---|---|---|---|
| itcz_mean_land 3 | 1.0090 | 1.0009 | 1.075 |
| itcz_mean_land 0 | 1.0292 | 1.0103 | 1.178 |
Moving the land belt south warms the hot dry north (Najd -2.95 -> -2.08, Sahel -1.93 -> -1.08, Sahara, Iran, N India)
but DRIES and warms the southern Amazon and Congo: the belt's mean latitude does not set southern-tropical land rain.
The northern warming likely comes from the Hadley descending branch (subsidence warming starts at ITCZ + gap) moving
south with it -> next lead: the branch geometry (subsidence_branch_gap, subsidence_warming_taper) on its own.

# e107 land subsidence-warming gap + e107b 10-deg floor (22-23 Nov)
Najd breakdown (scripts/land_budget.py): e71 warming +0.5 K in Jul-Aug (branch start ~24 N over Arabia) vs +2-3 K in
May/Oct. Screens vs r51 (S55 / S49 / S_t): gap 1 0.9996/0.9975/1.021; gap 0 1.0003/0.9977/1.027; floor 15 1.0051/1.0006;
floor 18 1.0054/1.0004; gap 0 floor 10 0.9990/0.9982/0.9985; gap 1 floor 11 0.9999/0.9985/1.004.
plan_U2 (35 evaluations): best S55 0.9953 (T -1.3 %, P +0.3 %), S49 0.9978, S_t 0.969 -> FAIL by 0.0003 (<= 0.995).
Still descending at the cap; continuation declared separately as plan_U3 (sealed s unopened).
