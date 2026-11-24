# Maritime mid-latitude land: e28 maritime_mean and e123 latitude gate (24 Nov 2026, policy v6)

Base: W8 finalist w1_023 (S97 0.9858 [0.974, 0.998], passes dev6, fails fine28 1.0115).

| run | change | S97 [90 %] | regimes / notes |
|---|---|---|---|
| mm30 | maritime_mean 0.3 | 0.9898 [0.974, 1.005] | temperate 1.010, med 1.010; tropical_dry 0.990, arid 1.002 |
| mm60 | 0.6 | 0.9997 | Gabon coast 1.45, NW Australia 1.60 (tropical coasts by colder sea) |
| mm40l25 | 0.4, e123 gate from 25 deg | 0.9826 [0.970, 0.995] | all regimes <= 1.010 |
| mm70l25 | 0.7, e123 gate from 25 deg | 0.9809 [0.967, 0.994] | all regimes <= 1.009; T -2.5 %, P -1.3 % |

Finalist mm70l25 declared before gates (finalist_e123.json): dev6 PASSES (upper bound 0.994, worst regime 1.009).
fine28 FAILS: S28 1.0165 (T +2.9 %). California T 1.71 -> 1.82 (bias -0.18 -> -0.49, range error -0.57 -> -1.26),
New Zealand 1.95 -> 2.06 (bias -0.39 -> -0.61, range -1.24 -> -1.64); W Europe and Japan flat. The same two
lose at 55 km (California 1.68 -> 1.77, NZ 1.93 -> 2.05): pulling cold-current coasts toward the sea's annual
mean cools them and over-damps their seasons. V18 UNOPENED.

Next: the maritime centre shift must not cool land beside upwelling / cold currents (California Current,
Southern Ocean around NZ): shift only toward a WARMER sea mean (one-sided), or weight by the sea-minus-zonal
anomaly. That is a new declared candidate (the e123 finalist is spent).
