# Fixed-infrastructure commercial storage and stock loss — 17 November 2026

Commercial storage dominates the two tested stock-loss settings under the
existing monthly dispatch rule. Reducing commercial capacity from 365 to 90
days of **original baseline** annual marketed energy reduces fixed city meal
coverage by 52.451 central and 47.765 low-density percentage points at 5% loss.
Removing stock loss adds 1.435/1.228 points with 365-day stores, but only
0.329/0.365 points with 90-day stores. These are structural model sensitivities,
not estimates of ancient granaries or a reason to adopt the larger stores.

| Stock loss | Commercial capacity | Central city meals supplied | Low city meals supplied | Full-meal city cells, central/low |
|---|---|---:|---:|---:|
| 5% | 365 days, original baseline | 92.457845% | 93.575793% | 1046 / 967 |
| 5% | 90 days | 40.006758% | 45.810563% | 215 / 129 |
| 0% | 365 days | 93.892804% | 94.803867% | 1053 / 986 |
| 0% | 90 days | 40.336113% | 46.175795% | 217 / 130 |

Percentages describe supplied cereal meals at fixed requests, not supported
occupancy. The requests remain 8,371,324.795 central and 4,057,216.667 low;
production, rural workers and actual populations do not change. Neither all
rural meals nor all city meals are supplied in any scenario.

## What was held fixed

The [frozen factorial](../calibration/urban_diagnosis_20261116/seasonal_transfer_storage_loss_factorial.json)
specifies exactly three new combinations per density, six new cases. Both
original 5%/365 controls reproduce **all 70 food arrays and flags exactly**.
Original first-best calendars and both component harvest pulses, physical
B600h work and grain, rural people, city requests, global factorized recruitment,
270 haul limit, 1981–2010 route snapshots, one-bin legs, original shares
0.3371937035110408/0.14049021985082757, rural 365-day and town 90-day capacity
remain fixed. Rural protection, marketed overflow and town eligibility are
recomputed for each loss level. The dispatch rule remains own-scenario annual
marketed grain divided by 12, masked by route availability.

For each origin, reference energy is the original baseline's annual marketed
grain. A 365-day commercial store is exactly that array; 90 days is reference
×90/365. Absolute capacities stay fixed across loss levels, even as lower
rural loss changes marketed grain. They are experimental grain capacities,
not measured granary volumes or inventories that are necessarily present.

Central/low zero-reference counts are 10,233/10,244. Zero loss newly protects
15/17 previously deficient origins with zero reference capacity. They market
89.337/49.599 grain person-years but depart only 6.908/3.892: a zero-capacity
store can fund immediate dispatch in its harvest bin, while carrying no stock.
All zero-reference commercial stock paths are identically zero. There are
16/19 zero-reference origins with newly positive marketing overall; protection
and positive overflow are separate conditions.

## Effects, interaction and local changes

At 5% loss, shorter stores remove 4,390,850.838 central and 1,937,938.889 low
city meal-equivalent person-years. At zero loss, they remove 4,483,404.627 and
1,972,946.256. The difference of differences is −92,553.789/−35,007.367 meal
person-years, or −1.105605/−0.862842 percentage points. Thus the zero-loss gain
is smaller with the limited commercial infrastructure.

Factor averages across the other tested level are also retained: the mean
capacity effect is −4,437,127.733/−1,955,442.572 meal person-years; the mean
zero-loss effect is +73,848.224/+32,321.942. These averages describe only this
2×2 experiment. No uncertainty interval or fitted response surface is implied.

No city materially gains meals from the capacity reduction in these saved
cases. At 365 days, zero loss improves 38 central/117 low city cells and
materially harms none. At 90 days, it improves 787/911 but **harms 11/8**.
Those losses must remain visible despite aggregate improvements: protected
export eligibility and cheapest-first transfers form a nonlinear allocation.
The next read-only audit will trace the recorded channels before proposing
another policy comparison. No general monotonicity is assumed.

Central Egypt's capacity effect at 5% loss is −68.841 percentage points,
versus −44.365 west and −58.905 east. Complete regional differences and every
city/month effect, including interaction, are supplied rather than only these
examples. Stock spoilage, grain left unused, freight payments and unmet meals
remain separate ledger quantities. Lower spoilage cannot simply be converted
to additional city meals.

## Numerical control and independent review

A synthetic balanced noninteger zero-loss control exposed a limitation of
generic periodic bisection: 495 of 1000 cases accepted unnecessarily high
inherited reserves despite smaller repeating starts. The
[negative result](../output/urban_storage_loss_20261117/numerical_controls/canonical_zero_loss_failure.json)
is preserved. No original kernel was changed. The
[numerical declaration](../calibration/urban_diagnosis_20261117/storage_loss_numerics.json)
was committed before the Earth cases. At zero loss, the annual clipped map has
lower endpoint T(0) and upper endpoint T(capacity). The isolated adapter uses
the lower endpoint when its replay repeats at the **original**
1e-10×max(1, annual harvest, annual demand) tolerance; otherwise positive drift
requires the upper endpoint. Subtolerance drift uses the same numerical
criterion, not an exact-real root claim. Empty starts are preferred when
admissible. Every selected state is replayed. Five-percent inventories reuse
the frozen analytic adapter, preserving baseline identity.

All 19 adapter tests pass, including balanced integer/noninteger pulses,
zero supply, newly eligible zero-capacity origins, blocked routes and baseline
identity. Independent review reconstructs zero-loss clipped maps and all
recorded monthly stocks/meals/overflow; five-percent stocks are checked against
canonical bisection. It separately rebuilds protected overflow, fixed-capacity
references, source arrivals, sorted intertown shipments and full grain ledgers.
All 338,268 physical source-cases, 24 inventory groups and 23,137 intertown
shipment rows pass. Maximum inventory difference is 0.576484 of the original
tolerance; full grain residual is at most 1.72e−8 person-years. All 1103
protected parent identities remain unchanged.

## Artifacts and continuation

- [Central map](../output/urban_storage_loss_20261117/central_meal_maps.png),
  [low map](../output/urban_storage_loss_20261117/low_meal_maps.png),
  [effect maps](../output/urban_storage_loss_20261117/factor_effect_maps.png),
  [monthly coverage](../output/urban_storage_loss_20261117/monthly_meals.png).
- [Summary](../output/urban_storage_loss_20261117/summary.csv),
  [8680 city rows](../output/urban_storage_loss_20261117/towns.csv),
  [96 month rows](../output/urban_storage_loss_20261117/months.csv),
  [40 region rows](../output/urban_storage_loss_20261117/regions.csv).
- [2170 city factor rows](../output/urban_storage_loss_20261117/city_effects.csv),
  [region factors](../output/urban_storage_loss_20261117/region_effects.csv),
  [month factors](../output/urban_storage_loss_20261117/month_effects.csv),
  [compact town packet](../output/urban_storage_loss_20261117/town_model.npz),
  [qualification](../output/urban_storage_loss_20261117/qualification.json).

Reproduction order in `.venv`: `scripts/urban_storage_loss.py` for each reading,
`scripts/review_urban_storage_loss.py` for each reading/case,
`scripts/render_urban_storage_loss.py`, then `scripts/seal_urban_storage_loss.py`.
Completed stages refuse overwrite. For fresh replay redirect the modules' OUT
to an empty directory in a fresh process; keep all frozen inputs unchanged.
Large per-case fields remain local/ignored; compact public results are tracked.

The [next declaration](../calibration/urban_diagnosis_20261117/storage_throughput_audit.json)
audits throughput and all 19 local-loss cases using saved ledgers only, with
zero new food scenarios. This distinguishes the commercial bottleneck from the
stipulated even-dispatch rule before changing policy. No setting is adopted,
no share refit or historical validation claim is made, and the main atlas and
actual population remain unchanged. Existing exposed-cohort, conditional crop
timing, full diet/work, rights and independent transfer gaps remain. Climate,
the archived steppe sidequest, Buringh sizes and climate `l` stay unopened.
