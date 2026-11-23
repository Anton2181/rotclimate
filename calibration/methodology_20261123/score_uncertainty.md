# How noisy are our scores? (23 Nov 2026, scripts/score_ci.py)

Paired bootstrap over regions (20,000 resamples; a region's candidate and reference move together). It asks: if the
benchmark had drawn a different sample of regions like these, how much would S move?

| decision | S | 90 % interval | sd | P(S >= 1) | outcome then |
|---|---|---|---|---|---|
| r51 vs r50, dev55 | 0.9713 | 0.9485 - 0.9923 | 0.013 | 0.002 | pass (v4) |
| r51 vs r50, dev49 | 0.9960 | 0.9910 - 1.0010 | 0.003 | 0.095 | guard pass |
| r51 vs r50, sealed r (6) | 0.9905 | 0.9401 - 1.0490 | 0.034 | 0.356 | pass -> adopted |
| plan_C vs r50, dev49 | 0.9916 | 0.9828 - 0.9998 | 0.005 | 0.045 | pass (v3) |
| plan_C vs r50, sealed q (6) | 1.0648 | 1.0097 - 1.1324 | 0.037 | 0.985 | fail |
| plan_U2 best vs r51, dev55 | 0.9953 | 0.9884 - 1.0014 | 0.004 | 0.112 | fail (v4, by 0.0003) |
| e107 floor 10 screen, dev55 | 0.9990 | 0.9912 - 1.0070 | 0.005 | 0.422 | screen |
| e105b screen, dev55 | 0.9953 | 0.9782 - 1.0104 | 0.010 | 0.335 | screen |

Findings
1. The v3/v4 dev threshold (S <= 0.995, a 0.5 % gain) is about one standard deviation of the region-sampling noise for a
   typical candidate (sd 0.003-0.005). Passing or failing it near the line says little: U2 "failed" at 0.9953 with an
   11 % chance of no real gain; a candidate at 0.9949 would have "passed" with about the same evidence.
2. The 6-region sealed sets are too small to confirm a modest gain: sd 0.034-0.037, so a 1 % improvement is
   indistinguishable from none (r51's sealed pass had a 36 % chance of no gain). They DO catch real overfitting:
   plan_C's sealed failure is clear (90 % interval wholly above 1).
3. The noise depends on the candidate: a change concentrated in a few regions (e105b, r51's tropical gain) has a
   wide interval, a broad change a narrow one. A fixed threshold ignores that; an interval does not.
4. Caveat: the dev regions were used for tuning, so their intervals are optimistic (in-sample). The sealed check is what
   measures out-of-sample gain, which is why it should be larger, not dropped.
