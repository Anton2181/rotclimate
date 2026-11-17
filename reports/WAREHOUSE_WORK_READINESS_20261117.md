# What the existing work budgets can fund — 17 November 2026

The original B600 work archives retain one physical rural workforce and a
listed cereal-task budget. They do **not** retain a complete monthly occupation
schedule or authenticated warehouse-handler affiliation. Unspent listed-work
allowance therefore cannot be promoted directly into logistics staff.

This read-only audit checks ten exact source contracts, four archive schemas
and both original primary work cases. It runs no component-work, food/stock,
graph, Dijkstra, weather, crop or demographic solver. All1103 protected
identities remain exact and no new staffing allocation or Earth scenario runs.

## Original budget quantities

Both cases have56,378 physical source rows and53,265 with positive workforce.
The pinned calendar/source ordering and monthly rural population match exactly.
Workers remain `.4*rural`; listed annual allowance is600 hours per worker.
Harvest-window allowance is `min(annual,workers*30*8)` on the **same** workforce.
It is a subconstraint, not an additional annual pool.

| Original B600 reading | Listed annual allowance | Listed work used | Unspent listed allowance | Sources at annual limit |
|---|---:|---:|---:|---:|
| Central | 12.727 billion hours | 10.914 billion hours | 1.813 billion hours (14.24%) | 45,935 |
| Low | 13.762 billion hours | 11.539 billion hours | 2.224 billion hours (16.16%) | 44,726 |

These are scenario crop-work hours, not complete occupations or newly available
staff. Rural people/worker fractions and600h were not fitted again or changed.
The raw minimum unused amount is−5.82e-11 hours from floating arithmetic, retained
at the existing `1e-8*max(1,allowance)` work tolerance rather than clamped away.

Reaping accounts for15.38% of listed hours; **84.62% of listed work has no
monthly placement** in these archives. The monthly peak arrays time reaping
only. Subtracting reaping again from annual listed use would double-charge it;
treating reaping as the complete monthly schedule would omit the other84.62%.
Both errors would contaminate a handling-labor claim.

## Limit-count caveat retained

The audit's raw absolute-tolerance test records4,761 central/4,759 low sources
near the reaping allowance. The independent review shows all are minute
workforce budgets: their largest allowance is below2e-8 hours. Across those
cells the entire allowance sums to less than9e-7 hours per reading.

Relative utilization is never above38.461539%, and **zero** sources have a
binding reaping constraint by the relative utilization criterion. Thus those
absolute-near counts are tolerance-floor artifacts, not peak labor bottlenecks.
Both original counts and the
[diagnostics](../output/urban_warehouse_work_20261117/limit_diagnostics.json)
are preserved. No budget, tolerance or archived result was changed.

## Inputs still missing for warehouse work

| Input | Available now | Still needed |
|---|---|---|
| Physical rural workforce | One source population and shared crop budget | Evidence for who handles grain and where |
| Crop tasks | Annual listed hours, reaping as a timed subset | Complete baseline monthly occupation schedule |
| Store withdrawals | Funded kcal, role labels and priority | Task definitions and compatible material/throughput units |
| Handling intensity | None adopted | Supplied or sourced hours per defined task/material |
| Affiliation and travel | No authenticated source-to-handler assignment | Nonduplicated physical work assignment and time constraints |
| Capacity/access | Scenario store contracts | Operational capacity, historical rights and compatible work evidence |

The component archive also lacks embedded source IDs: positional arrays align
through the pinned original calendar/producers. This audit checks that recipe
against monthly source IDs, without inventing new site/port affiliations.

## Checks and next implementation

The [independent review](../output/urban_warehouse_work_20261117/review.json)
checks112,756 scalar source rows, allowance identities, annual/peak limits,
reaping as a subset and aggregate sums. See
[budgets](../output/urban_warehouse_work_20261117/budgets.json),
[contracts](../output/urban_warehouse_work_20261117/contracts.csv) and
[qualification](../output/urban_warehouse_work_20261117/qualification.json).

The [next finite declaration](../calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json)
implements a shared task-budget checker using explicit complete manufactured
schedules and supplied task hours. It must reject double-booked role budgets,
annual-only or monthly-only violations, cross-workforce borrowing and missing
full schedules. A passing checker cannot supply the missing Earth schedule,
recruit handlers or calibrate a logistics coefficient.

No source measurements, city tables, reserved Buringh pools or site-survey
workbook were opened. Climate/steppe remain deferred; no population, fit or
atlas/default adoption occurs. Reproduce in an empty isolated OUT with
`scripts/audit_warehouse_work.py`, `scripts/review_warehouse_work.py` and
`scripts/seal_warehouse_work.py`; completed packets refuse overwrite.
