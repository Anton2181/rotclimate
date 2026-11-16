# Rivers as borders between European states: Earth test, 16 November 2026

**Outcome: not adopted.** Making river crossings costly for ownership changes almost nothing (±0.0005 in owner agreement). An
unplanned side result is more interesting: deciding ownership by walking days alone beats the map's monthly networks, which include
river boats, in all seven pools (+0.002 to +0.015). It just misses the declared gate.

Protocol: [plan](../calibration/river_borders_20261116/plan.json), declared before any result. Development used four seen pools
(Bosker cities 1200/1400/1500/1600, Rome window). The blind run was made once, on Bosker 1000, 1100 and 1800.

## Results (owner agreement where model-held land is inside a real state with towns)

| Pool | Map rule (monthly networks) | Walking only (R0) | Walking + 1 day per river crossing (R1) | R1 − map |
|---|---:|---:|---:|---:|
| 1200 (dev) | 0.907 | 0.921 | 0.921 | +0.014 |
| 1400 (dev) | 0.887 | 0.896 | 0.896 | +0.009 |
| 1500 (dev) | 0.893 | 0.905 | 0.906 | +0.013 |
| 1600 (dev) | 0.916 | 0.930 | 0.931 | +0.015 |
| **1000 (blind)** | 0.906 | 0.921 | 0.921 | +0.015 |
| **1100 (blind)** | 0.882 | 0.884 | 0.884 | +0.002 |
| **1800 (blind)** | 0.914 | 0.924 | 0.924 | +0.0098 |

Gates:
- G1 needs +0.01 in two of three blind pools. Only 1000 clears it; 1800 is at +0.0098, so G1 fails.
- G2 passes.

X = 1 day was chosen on development; 0.5–4 days gave the same results within 0.0003.

## What this means

1. **River crossings are not why European borders follow rivers, at this scale.** Real borders between states lie on rivers
   ×1.1–2.6 (rising from 1000 to 1800). The model's borders move toward rivers with a crossing cost (1800: ×1.44 → ×1.73), but the
   land changes owner very little. Rivers that became borders were mostly *drawn* by treaties along lines that already separated
   town networks, which is what the town labels already capture.
2. **Ownership may be better decided on foot.** The map's ownership uses networks with boats on rivers and seasonal closures. These
   join the two banks of a river, and they reach far along coasts and rivers. Walking days give the right owner slightly more often
   in all seven pools. This is a candidate for its own declared test. Bosker years left unused for control: 800, 900. The effect
   (~+0.01) is small for the map: under 1% of contested land.
3. The map rule's owner agreement stands at 0.88–0.92 in Europe and 0.99 in China (internal-borders report).

Reproduce: `.venv/bin/python -I scripts/river_borders.py prep 1200` (and so on for each year), then `dev`, then `blind` (run once).
