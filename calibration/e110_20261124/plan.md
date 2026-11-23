# e110 plan (declared 24 Nov 2026, before the lat-30 screen)

Mechanism: the e70c rain gate (no dry-air descent where it recently rained) locked false dry-season rain into
winter-hemisphere tropical land (Zambia r_14s_32e 50-106 mm/mo Dec-Apr vs obs 2-11; southern Tanzania t_8s_36e
155-180 vs 5-9). Removing the gate entirely (dry_rain 1000) fixes them but floods/dries the summer monsoons it was
made for (southeast_us 1.19, south_brazil 1.17, east_china 1.11): S61 0.9925 [0.975, 1.008], S49 1.0075 - fails.
e110 lifts the gate only in the winter hemisphere (ITCZ across the equator) and, with e110b, equatorward of
subsidence_branch_gate_lat (5 deg ramp).

Screens already run (v5 pool, vs r52): see screen_e110*.log
| variant | S61 [90 %] | T | P | S49 |
| winter, 5 deg ramp | 0.9954 [0.9899, 1.0000] | +0.1 % | -1.0 % | 0.9999 |
| winter, 2 deg ramp | 0.9940 [0.9870, 0.9999] | +0.1 % | -1.3 % | 0.9999 |
| + lat 20 | 0.9858 [0.9721, 0.9973] | +0.1 % | -2.9 % | 0.9984 |
| + lat 25 | 0.9836 [0.9686, 0.9963] | +0.0 % | -3.3 % | 0.9957 |

Declared: one more screen, lat 30 (winter 1.0, 5 deg ramp). Finalist = lowest S61 among lat 20 / 25 / 30 that
meets the v5 dev gates. Then, in order, stopping at the first failure: dev5 (gate_v3.py), fine28 (<= 1.01),
regime scores and the pad-2200 12-region set (reported, not gating), then ONE sealed U18 run
(S <= 1 and 90 % lower bound < 1). Pass -> adopt as r53 (no atlas rebuild). No further tuning of e110 after
the finalist is chosen.
