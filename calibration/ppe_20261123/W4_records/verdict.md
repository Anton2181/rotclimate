# plan_W4 verdict (24 Nov 2026)

65 Sobol points + one emulator wave of 16 (81 evaluations, 0 failures) over 9 knobs around e52c (stable layer
behind upwind crests) on r52, scored at pad 1100 against r52.

- Best point is the declared base itself: r52 + e52c (barrier_rate 0.3, barrier_km 1.5, fetch 800 km):
  S 0.9978, 90 % CI [0.9940, 1.0015], T -0.5 %, P +0.1 %, S49 0.9975.
- Wave 1 best other point 1.0001. Emulator LOO RMSE 0.017 (corr 0.90); its best prediction 0.9942.
- Wave 2 (16 emulator picks) best 0.9991; none beat the base. Predicted gain was inside emulator error and
  score noise (sd ~0.005), so W4 closes early per plan.
- Sensitivity: eddy_scale_km, land_offset, eddy_rate dominate; e52c knobs are flat at pad 1100.

Gate: the finalist (base) fails policy v5's first gate (S61 90 % upper bound 1.0015, must be < 1). Not adopted;
no sealed run spent (U18 stays unopened). r52 remains adopted.

What e52c is good for: it removes 4.5-7.7 % of the error a 2,200 km pad exposes (prairies 4.7 -> 2.8 C at
rate 0.6), i.e. it fixes a real winter mechanism that the 1,100 km pad currently hides through compensating
settings. Keep it in the code (off by default). It becomes adoptable only if the scoring domain changes
(e.g. pad 2200 as a gated set) - an owner decision.
