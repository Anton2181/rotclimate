# Borders between states: Earth test, 16 November 2026

**Outcome: canton rule not adopted. The map's owner rule passes its first Earth test.**

Protocol: [plan](../calibration/internal_borders_20261116/plan.json), declared before any result. Three development pools were used
(seen), then one blind run on three pools never used in a control test.

## Method

Each pool's towns are labelled with the Cliopatria polity they lie in, which is how the map's towns carry their painted claim.
Held land is control v2.1. Each held cell goes to the polity whose staffed towns reach it soonest (the map's rule, O0). Scores are
taken where model-held land lies inside a real polity with towns:

- **Owner agreement (OA):** the share of that land where the model's owner is the real one.
- **Border recall and precision:** real borders between two states found within two cells (~18 km) of a model border, and the reverse.
- **Divide and river enrichment:** how often borders lie on watershed divides and rivers, relative to the land around them.

## Results

| Pool | OA, map rule | OA, straight-line nearest town | OA, cantons (L8) | Border recall, map / cantons | Precision, map / cantons |
|---|---:|---:|---:|---:|---:|
| Europe 1200 (dev) | 0.907 | 0.917 | 0.907 | 0.39 / 0.42 | 0.48 / 0.49 |
| Europe 1500 (dev) | 0.893 | 0.897 | 0.891 | 0.47 / 0.54 | 0.65 / 0.62 |
| China 1200 (dev) | 0.990 | 0.990 | 0.990 | 0.67 / 0.76 | 0.86 / 0.72 |
| **Europe 1400 (blind)** | 0.887 | 0.889 | 0.886 | 0.46 / 0.53 | 0.54 / 0.56 |
| **Europe 1600 (blind)** | 0.916 | 0.922 | 0.914 | 0.53 / 0.61 | 0.68 / 0.66 |
| **China 1140 (blind)** | 0.989 | 0.989 | 0.988 | 0.68 / 0.75 | 0.86 / 0.74 |

Gates: G1 (cantons beat the map rule by 0.01 in OA in two of three blind pools) **fails**. G2 (never more than 0.01 worse)
passes. Not adopted.

### Where real borders between states run

| Pool | Real: divide | Real: river | Map rule: divide / river | Cantons: divide / river |
|---|---:|---:|---:|---:|
| Europe 1200 | ×1.06 | ×1.00 | ×1.01 / ×0.56 | ×1.23 / ×0.70 |
| Europe 1400 | ×1.10 | ×1.21 | ×1.05 / ×0.93 | ×1.23 / ×1.08 |
| Europe 1500 | ×1.12 | ×1.89 | ×1.06 / ×1.17 | ×1.24 / ×1.21 |
| Europe 1600 | ×1.09 | ×2.06 | ×1.08 / ×1.47 | ×1.22 / ×1.64 |
| China 1140 | ×1.10 | ×0.48 | ×1.04 / ×0.44 | ×1.21 / ×0.42 |
| China 1200 | ×1.12 | ×0.52 | ×1.07 / ×0.49 | ×1.22 / ×0.34 |

## What this means

1. **The owner rule works.** Where states meet, the map's rule gives 89–99% of the land to the right state. Straight-line
   distance to the nearest labelled town does as well. Ownership is set mostly by which towns belong to whom; travel time adds
   little.
2. **Natural borders between states are real but mild.** Between states, borders lean slightly onto watershed divides (×1.06–1.12),
   unlike the outer edge of the state space, which avoided them. In Europe after 1400, they lean clearly onto rivers (×1.2–2.1).
   In China they avoid rivers (×0.5): the Song–Jin line follows the Huai–Qinling divide zone, not the Yellow River.
3. **Cantons place borders better but not ownership.** Basin cantons raise border recall in all six pools (+0.03 to +0.09).
   Precision rises in Europe 1400 and falls in China. They overshoot the divide preference (×1.22 against Earth's ×1.10). A cell
   is either on a divide or not, so moving a border by one basin hardly changes who owns the land.
4. **A possible next test is rivers as borders between European states.** Rivers carry about twice the border share in Europe
   1500–1600. A rule that makes a large river a tie-breaker between two states could be tested on unused Bosker years (1000,
   1100, 1800).

Reproduce: `.venv/bin/python -I scripts/internal_borders.py prep D1` (and so on for each pool), then `dev`, then `blind` (run once).
