# Gated dry heating re-test on r50 (22 Nov 2026) — FAIL, parked

Stage A screen (dev49 paired with r50): D1 1.0009, D2 (annual-dryness gate) 0.9998, D3 (no warm-month gate) 1.0002.
The heating is weak where it is needed: Najd Jul-Sep +0.3 C (bias -5 to -6), Sahara +0.4, North India Apr-May +0.3,
Deccan and Sahel 0.

Stage B (plan_B.json, 39 evaluations, joint_refit vs r50): best S49 0.9989 (T -0.5 %, P +0.3 %): FAIL (<= 0.995).
Raising dry_heating to 4.3 does not help (1.000); every knob moves S49 by < 0.001 except land_offset (worse both ways).
The hot dry interiors are a small share of S49, and the coast gate (chi0 0.86-0.95) and the annual-dryness
gate leave little land heated. Not adopted; r50 stays. Sealed set q unopened.
