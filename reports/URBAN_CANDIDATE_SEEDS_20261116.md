# Candidate town changes across five paired seeds — 16 November 2026

The candidate's largest single-seed changes are not stable town predictions.
**No town doubles, or falls below half, in all five paired seeds** on either map.
Even the sign of the aggregate central-reading town population change varies.
The [map comparison](../output/urban_hierarchy_candidate_20261116/index.html)
remains a useful seed-1 scenario, with its development status unchanged.

This implements the seed component of the committed
[supply/robustness declaration](../calibration/urban_diagnosis_20261116/candidate_supply_robustness.json)
from `9f7a65633`, after the map was committed and pushed. No model was refit,
location moved, source pool opened, climate rerun or seed chosen for appearance.
Both models use seeds **1, 7, 19, 43, 97** on the same sites and standard-normal
draws. The residual-member permutation retains its separate fixed 2026 seed.
The canonical hierarchy builder performs the residual selection, clipping,
lore ordering and finite own/wider population movements for every case.
The candidate retains the previously disclosed runtime-only guard adapter,
`adopt=False` and `gate.passed=False`.

## Persistence of large changes

| Map | Seed-1 towns >2× | >2× in at least 3/5 seeds | >2× in all seeds | Seed-1 towns <½ | <½ in at least 3/5 seeds | <½ in all seeds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw, 1,034 sites | 39 | 7 | 0 | 22 | 2 | 0 |
| Corrected, 1,053 sites | 34 | 11 | 0 | 13 | 1 | 0 |

These are counts across each entire site list, not survival fractions restricted
to the seed-1 outliers. The median across sites of each site's paired median
area ratio is 1.0163 raw / 1.0154 corrected. Changing hierarchy selection
reassigns residuals and can also change the later lore swaps; a large change at
one named node in one draw therefore needs considerably more interpretation
than the modest shift in the central tendency.

## Aggregate changes also depend on seed

Candidate relative to published, percentages:

| Seed | Raw area / low-density residents | Raw central residents | Corrected area / low-density residents | Corrected central residents |
| --- | ---: | ---: | ---: | ---: |
| 1 | +0.306% | −0.770% | +0.057% | −1.117% |
| 7 | +1.236% | +1.565% | +1.763% | +2.397% |
| 19 | +1.101% | +0.941% | −0.532% | −2.612% |
| 43 | +1.947% | +2.908% | +1.034% | +0.680% |
| 97 | +1.503% | +2.086% | +0.897% | +0.415% |

Low density is fixed at 100 residents/ha, so its resident and area percentage
changes coincide when all requests are met. The central density depends on
area and amplifies differences in the upper tail. Neither the seed-1 decline
nor the largest positive draw should be presented as the expected change.

The stage comprises **20 fixed-site area draws, 40 actual annual population
cases and 20,870 per-site seed rows**. Each case conserves world population;
requested town residents are met to floating precision. All source withdrawal
and remaining rural arrays are recalculated, not copied from seed 1. Annual
local cereal support is also recalculated and its import dependence remains
visible. This is not a wider grain-supply or seasonal food/work qualification.

## Artifacts and independent review

Under `output/urban_candidate_seeds_20261116/`:

- `seed_towns.csv`: every site's area, selected residual, actual residents,
  own/wider contributions, draw radius and annual local cereal support in each
  model/seed and both density readings.
- `town_intervals.csv`: each site's model area/resident p10/p50/p90, paired
  ratio p10/p50/p90 and doubling/halving frequencies.
- `cases.csv` / `results.json`: complete annual totals, population residuals,
  unmet requests, rural-array identities and primacy/top-ten/Gini summaries.
- `model.npz`: compact unrounded per-town arrays, tracked. Large case fields
  and fresh duplicates are ignored and reproducible.
- `review.json`: passed independent replay; reviewer application adapter is
  retained in `reviewer_application_snapshot.txt`.

The p10/p90 values are linear sample quantiles of **five scenario draws**. They
are not calibrated confidence/credible intervals, a placement ensemble, new
held-out validation or proof of transfer to the fantasy world.

Seed 1 reproduces all eight published/candidate CSV and complete field-file
identities from the preceding map stage. The separate reviewer reuses the
preceding independently implemented scalar application/annual equations,
exposing only their formerly fixed seed. Full-distance ownership is recomputed;
scalar concentration and explicit order-statistic interpolation check the new
summaries. It checks all 20,870 site rows, 40 ledgers, compact and remaining-rural
arrays, protected source/main assets and exact fresh compact exports. Maximum
independent area difference is 1.14e−13 ha, rural difference 6.83e−13 people.

Reproduce from the repository root:

```sh
.venv/bin/python scripts/urban_candidate_seed_sensitivity.py
.venv/bin/python scripts/urban_candidate_seed_sensitivity.py --out output/urban_candidate_seeds_20261116/fresh
.venv/bin/python scripts/review_urban_candidate_seeds.py
```

Next is the annual work-limited wider-supply component of the same declaration:
restore exact release-4 supply controls on these nodes, then rebuild candidate
seed-1 grain production, rural need/work and transport accounting at the existing
calibrated extraction shares. Preserve deficits. Seasonal joint source food/work,
staff/reach/trade and appropriate transfer evidence still precede adoption or
main-atlas publication. Climate remains parked.
