# Evidence bridge and baseline stock use

The read-only audit identifies commercial grain storage and spoilage as the
next assumptions to test. Every exporting origin's recorded peak exceeds a
hypothetical capacity equal to 90/365 of its original annual marketed grain.
That flags a potentially binding capacity; it does **not** say all exports or
meals would be lost with a smaller store. No food scenario was rerun.

The preceding [timing comparison](URBAN_CALENDAR_SENSITIVITY_20261116.md)
changed aggregate meals little under two recipes, while individual city
fractions moved by up to 12.78 points. Those recipes do not bound outcomes or
isolate the effect of storage. The original first-best dates remain the
reference; no better-looking date assignment is adopted.

## What the existing evidence can establish

| Already exposed source | Supported use | Missing integration contract |
|---|---|---|
| [Modern Sacks calendar diagnostic](OBSERVED_CROP_CALENDARS_20261103.md) | Duration-envelope and coarse cold-exposure checks with qualifiers retained | Ancient pointwise planting/harvest dates, exact date errors and yield validation |
| [Conditional cereal clock](CEREAL_DEVELOPMENT_20261103.md) | Physiological maturity duration given supplied sowing | Endogenous sowing, harvest operations, cultivars, water/yield coupling and an unseen evaluation pool |
| [FAO56 stage component](CROP_STAGE_20261114.md) | Context-labelled supplied duration and coefficient curves | A universal ancient Nile barley calendar or unadjusted local root-water demand |
| [Reserve algebra](CALENDAR_STORAGE_20261103.md) | Zero-loss minimum storage under specified repeating harvest/meals | Universal historical granary capacity, spoilage rate or food-risk probability |
| [Current monthly pilot](URBAN_EARTH_MONTHLY_20261116.md) | Conditional physical food/route accounting | Empirical calibration of the date/store/loss rules, actual occupancy or demographic equilibrium |

The old cereal evaluation is not fresh evidence: its country groups have
already been scored. The reported fixed heat-only adaptation improved that
conditional-duration comparison (28.56 days versus the threshold ablation's
51.99), while the trained chilling candidate performed worse (68.06 days,
with two non-maturity cases). Its failed adoption status is retained. These
historical report findings are not a new evaluation of the present clock.

Likewise, a modern duration envelope passing does not validate a predicted
harvest date, and a climate-window endpoint is not necessarily physiological
maturity or a harvest operation. No raw Sacks records, new geographic
intersection, cultivar fit or phenology re-scoring was performed. The audit
checked source text/locators, current interface identities and their stated
limits; it did not substitute a new date engine.

## What the saved stock paths show

All individual peaks were reconstructed exactly from recorded stocks,
supply, meals and capacities before spoilage. The two aggregate peak measures
are distinct: a simultaneous peak is the largest stock at one accounting
instant across a class, while the sum of individual peaks can combine
different months. They must not be added or interpreted interchangeably.

Units below are **million person-years of grain calories**, not people fed,
observed stored grain, tonnes or archaeological granary volume. The table
describes the original baseline's scenario infrastructure.

| Density / store class | Capacity | Simultaneous peak | Sum of individual peaks |
|---|---:|---:|---:|
| Central rural | 53.029 | 35.592 | 52.757 |
| Central commercial export | 30.444 | 18.484 | 27.944 |
| Central town | 2.064 | 0.800 | 0.801 |
| Low rural | 57.343 | 38.462 | 57.022 |
| Low commercial export | 13.203 | 8.048 | 12.119 |
| Low town | 1.000 | 0.508 | 0.509 |

Commercial stores have a median individual peak of 11/12 of their declared
annual-marketed-grain capacity. All 46,145 central and 46,134 low commercial
stores with positive capacity exceed the hypothetical quarter-year threshold.
Restricting to origins that actually depart grain still flags **all 45,453
central and 45,442 low origins**, associated with 100% of recorded departures.
That is a saved-path comparison, not a counterfactual export or meal forecast.
Stocks, overflow, eligibility and routing would have to be recalculated under
a changed capacity.

Stock spoilage in the baseline is approximately 1.415M rural, 0.703M export
and 0.041M town grain person-years centrally; low is 1.529M, 0.305M and 0.026M.
Those losses cannot simply be subtracted from city shortfalls: their locations,
protection rules, freight losses and unused grain matter.

The [source-contract table](../output/urban_evidence_buffers_20261116/evidence_contracts.csv),
[exact buffer diagnostics](../output/urban_evidence_buffers_20261116/buffer_usage.csv)
and [receipt](../output/urban_evidence_buffers_20261116/qualification.json)
retain source identities and definitions. No inventory solver or food kernel
was called, and no stored stocks or previous outputs changed.

## Next declared experiment

The [storage/loss factorial](../calibration/urban_diagnosis_20261116/seasonal_transfer_storage_loss_factorial.json)
predeclares a 2×2 comparison: 5% versus zero stock loss, and commercial
capacity equal to 365 versus 90 days of **baseline** annual marketed grain.
The existing 5%/365 case is the exact control; six new cases cover the other
three combinations at central/low requests. Original first-best dates,
B600h production, rural/town capacities, routes, delays and calibrated shares
stay fixed.

Absolute commercial capacity is held fixed across loss levels. It is not
resized when lower spoilage changes marketed grain. A source with zero
baseline commercial capacity retains zero capacity even if it becomes
eligible to export in a zero-loss scenario; that is part of the explicit
fixed-infrastructure comparison, not observed storage behavior.

The new parameterized adapter must reproduce the original 70 food arrays
exactly before any interpretation and handle zero-loss repeating stocks
without an invalid analytic division or free inherited food. Every physical
ledger and monthly route remains subject to independent review. No scenario
will be selected as a new default simply because it feeds more cities.

This audit supplies a next experiment, not historical storage evidence or a
new empirical transfer result. Main atlas, population, policy shares and
climate remain unchanged; full diet/work, rights and independent validation
are still open.

## Reproduction

With parent qualifications and original monthly arrays available, run
`scripts/audit_urban_evidence_buffers.py` in the project virtual environment,
then `scripts/seal_urban_evidence_buffers.py`. Completed audit output refuses
overwrite; redirect runtime OUT to an empty directory for a fresh read-only
replay. No raw observation or new food run is required.
