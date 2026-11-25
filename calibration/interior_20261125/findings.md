# Deep tropical interior rain deficit under r56 (25 Nov 2026) - e133/e133b PARKED

Symptom (r56): interiors 950-1,500 km from the sea get 36-53 % of observed rain (r_7s_59w 1,009/2,136 mm,
u_5s_66w 938/2,617, t_10s_66w 631/1,737, s_0s_28e 556/1,486, u3_11s_55w 876/1,954) and run +0.8 to +2.1 C warm;
coastal tropical boxes get 100-150 %. This deficit (too dry -> too clear -> too warm) is what makes every warming of
clear dry land (dry_heating B5, cloud_radiation e132) also heat the southern tropics, so it blocks the hot-tail fix.

Screens vs r56 (97 dev regions, S97 [90 %]):
| set | S97 | notes |
| edge_inner 0.5 / 1.0 (e81) | 1.022 / 1.090 | northern continents wrecked (Kazakh, Siberia x2-2.7) |
| land_edge_rh 0.7 | 1.074 | Congo 0.48, S Amazon 0.66, Manitoba 0.52; deserts/steppes x2-3.7 |
| edge_inner 1, warm-wet gate 18 C (e115) | 1.005 | |
| e133 edge_itcz_rh 0.5 (max 0.8, width 10) | 1.014 [0.989, 1.045] | Congo 0.66, Amazon 0.87; Tibesti 1.56, Sudan 1.91 |
| e133 1.0 | 1.033 | Congo 0.58, t_10s_66w 0.77; Algeria 2.04, Sudan 2.95 |
| e133 1.0, width 6 | 1.016 | |
| e133 1.0, max 0.9 | 1.046 | |
| e133b poleward width 2 / 4 | 1.016 / 1.019 | tropical gain halves, Sahara/Sahel wetting stays |
| e133b 0.6, poleward 2 | 1.012 | |
| e133b poleward 2, width 15 | 1.017 | |

Reading: the moisture that wets the Sahara/Sahel enters at the maps' southern edges near 10 N (inside the summer
belt, where real air is moist too) and the model carries it too far north; r56's Sahara stays dry only because its
edges are dry. A boundary fix therefore needs a matching fix of the northward reach of monsoon moisture over hot
land (dry air aloft / shallow monsoon layer; cf. e86 onset_suppression, e93 convective_rh_gate) before it can pay.
Code e133/e133b (edge_itcz_rh, edge_itcz_rh_max, edge_itcz_width, edge_itcz_poleward_width) stays, default off.

Combination screen (e133 0.5 + an existing monsoon-reach lever) vs r56:
| set | S97 [90 %] | Tibesti u_21n_21e / Sudan s3_17n_34e |
| + heat_low_drying 0.1 (e80) | 1.0142 | 1.56 / 1.91 |
| + convective_rh_gate_pole 0.5 (e119) | 1.0117 | 1.42 / 1.91 |
| + subsidence_branch_drying 0.5 | 1.0135 | 1.51 / 1.76 |
| + monsoon_descent 0.08 | 1.0096 [0.986, 1.039] | 1.52 / 1.95 |
None of the existing drying levers holds the Sahara/Sahel dry against moist southern edges: their rain comes from
transported column water, not from convective triggering. A new mechanism is needed (e.g. a cap on the northward
moisture flux in the shallow monsoon layer, or edge air whose humidity follows the model's own column RH at that
latitude band in the same map). Line closed for now.
