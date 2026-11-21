# T8 occupation field — findings (21 Nov 2026)

Plan declared before scoring: plan.json. Units: 98 Han AD 2 commanderies (Zheng & Wu 2026 outlines) + 7 western
reference regions (Egypt, Italy, Gaul, Iberia, Asia Minor, Syria, Mesopotamian alluvium). y = ln(people / settlement base).

| model | CV score (pool-balanced mean abs ln error) | Han | West |
|---|---|---|---|
| M0 one level (today) | 1.050 | 1.219 | 0.881 |
| **M1 level x exp(-D/L)** | **0.813** | 0.838 | 0.787 |
| M2 + herding share | 0.828 | 0.842 | 0.814 |
| M3 + malaria, aridity | 0.957 | 0.925 | 0.988 |

M1 passes the adoption rule (-23 % vs M0; simplest within 2 % of best). Fitted ratio = 1.42 exp(-D / 811 km): the decay
length matches the 800 km heartland weight already used to place people, so the SHAPE of today's map is confirmed.
With L fixed at 800 km, A = 1.44. Held-out residual quantiles (ln): q10 -1.45, q50 0.11, q90 1.20.
Worst unit: the Mesopotamian alluvium (predicted ~9x too many; Parthian-Sasanian decline and salinisation).

What changes is the LEVEL. Today the total is the median ratio 0.32 x capacity, whatever the cores. Under M1 it follows
how close the land lies to old cores. Earth units sit on average at exp(-D/800) = 0.27 (Han 0.267, West 0.268); the
fantasy land, with seven lore cores, sits at 0.565 (raw climate, settlement-base weighted). Applied as fitted, the
central fraction becomes 1.44 x 0.565 = 0.81 instead of 0.32: about 125 M people (38 per km2) instead of 50 M (15 per km2).

That rests on reading the seven lore cores as equivalent to Earth's cradles (Uruk, Memphis, Harappa, Zhengzhou: about
3,000 years of states by AD 200) and Rome. Several lore cores are much younger (Arǧos since ~25, present year 486).
Earth has too few cores to fit an age effect. Owner decision needed before adoption (see HANDOFF).

## Owner decision (21 Nov 2026): keep 50 M
Today's level (median ratio 0.32 x capacity) stays. The Earth fit is recorded as confirming the 800 km heartland pattern
(fitted L 811 km); the fitted level is not applied. No rebuild.
