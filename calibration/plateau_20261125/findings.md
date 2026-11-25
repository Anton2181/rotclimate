# e134 plateau heating (Tibet seasonal range) under r56 - CANDIDATE COMPONENT (25 Nov 2026)

Symptom: Tibet (4.7 km) winter +2 to +4 C, summer -3 to -4 C, seasonal range 5.1 C too small; no general range error
with elevation across the 97 dev regions. lapse_seasonal 0.15 (e25: steeper summer lapse) shrinks the range at height.

Screens vs r56 (S97 [90 %], highland regime, Tibet / Tarim side r_40n_94e / Altiplano s2_23s_67w):
| set | S97 | highland | Tibet / Tarim / Altiplano |
| lapse_seasonal 0 | 1.0007 [0.992, 1.010] | 1.040 | 0.79 / 1.31 / 1.42 |
| lapse_seasonal 0.30 | 1.0228 | 1.197 | 1.36 / 0.87 / 1.45 |
| e134 plateau_heating 2 (300 km smoothed > 1.5 km, lat ramp 15-30) | 0.9981 [0.993, 1.002] | 0.971 | 0.84 / 1.17 / 1.02 |
| e134 4 | 0.9991 | 0.995 | 0.82 / 1.36 / 1.05 |
| e134 4, from 1.0 km | 1.0025 | 1.059 | 0.82 / 1.65 / 1.14 |
| e134 6 | 1.0034 | 1.082 | 0.97 / 1.55 / 1.10 |
| e134b 2 (cell height too, lat ramp 20-35) | 0.9976 [0.993, 1.000] | 0.958 | 0.86 / 1.05 / 1.00 |
| e134b 4 | 0.9971 [0.991, 1.001] | 0.952 | 0.81 / 1.10 / 1.01 |
| e134b 6 | 0.9991 | 0.994 | 0.91 / 1.16 / 1.02 |
| e134 2, lat ramp 20-35 | 0.9984 | 0.975 | 0.86 / 1.17 / 1.00 |

Reading: a real but one-region gain (~0.3 %, upper bound at 1.001). Not refit alone (predicted < 0.005); carry
e134b (plateau_heating 4, plateau_heating_cell true) as a component to stack with the next structural win in one
refit. Code default off.
