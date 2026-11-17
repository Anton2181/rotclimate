# Fixed dispatch quotas under zero storage loss — 17 November 2026

Holding monthly departure quotas at their original baseline values removes all
19 local meal declines previously caused by going from five-percent to zero
stock loss with 90-day commercial stores. No other city materially loses meals
against the five-percent control in these two fixed-quota cases. This isolates
the quota feedback in the observed declines; it is not a general monotonicity
proof or a historical dispatch model.

| Scenario, all with 90-day commercial stores | Central meals supplied | Low meals supplied | Full-meal cells, central/low |
|---|---:|---:|---:|
| 5% loss, original own-scenario quota | 40.006758% | 45.810563% | 215 / 129 |
| Zero loss, own-scenario quota | 40.336113% | 46.175795% | 217 / 130 |
| Zero loss, fixed original baseline quota | 40.258773% | 46.087820% | 217 / 131 |

These are fixed requested cereal meals, not population forecasts. Requests,
rural people/work, B600h grain, first-best dates, original shares and 1981–2010
routes remain unchanged. The original 365-day reference still supplies
92.457845% central/93.575793% low meals; this control does not resolve the much
larger dependence on commercial storage.

## The isolated change

The [committed declaration](../calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json)
allows exactly two new cases, one per density: zero loss and commercial
capacity `original baseline annual marketed grain * 90 / 365`. Rural and town
capacities remain 365 and 90 days of fixed needs. The new dispatch rule is
`original baseline annual marketed grain / 12`, masked by unchanged routes,
instead of the zero-loss scenario's larger annual marketed grain divided by
twelve. Dispatch is a requested withdrawal; only physically funded grain
departs. Its realized annual total is allowed to change.

All four required controls (two losses × two densities, original own-scenario
quotas) reproduce all **70 food arrays and flags exactly before either new
case runs**. The isolated adapter reuses the qualified inventory method and
copies the physical accounting order. Original qualified code and outputs
remain untouched. Rural food inventories and monthly marketed grain are
bit-exact to the existing zero-loss/90-day cases; only dispatch and its
downstream consequences change. Zero-reference origins keep both zero
commercial capacity and zero quota, even if newly eligible for marketing.

## What the comparison establishes

All 11 central/8 low previously losing city cells now improve against the
five-percent control, by a combined 563.103/108.681 meal-equivalent person-years.
There are zero newly losing cells against that control. Their previous
combined changes had been −276.520/−107.883. The
[19-cell comparison](../output/urban_fixed_dispatch_20261117/previous_losers.csv)
retains the direct/intertown arrival, overflow, spoilage, initial/final stock
and local exporter-eligibility channels for every case.

Compared with the **zero-loss own-quota** cases, however, the fixed quota
supplies **6474.384 fewer central and 3569.347 fewer low meal person-years**
(−0.077340/−0.087975 percentage points). It benefits 175/193 city cells but
reduces meals in 399/604. These are different comparisons: no city losing
against the five-percent reference does not mean every city benefits from
switching between zero-loss dispatch rules. No rule is selected by its total
meal count or by eliminating a selected set of losses.

Paid source departures fall by 39,158.618 central/17,624.162 low grain
person-years between the two zero-loss cases, with the same increase in
commercial overflow. Lower quotas leave more grain stranded in commercial
stores at the harvest pulse; they do not enlarge capacity or fund extra
shipments. Source-unused grain, town-unused grain, freight payments, cyclic
transit and unmet rural/town meals remain separate in the
[summary](../output/urban_fixed_dispatch_20261117/summary.csv). Aggregate meals
remain only 40.259%/46.088% at this capacity, so small quota changes do not
repair the storage bottleneck identified by the previous audit.

## Verification and artifacts

Ten new adapter tests pass, covering exact own-quota controls, an explicit
equivalent quota, independent capacity/quota references, newly marketable
zero-reference origins, blocked routes and invalid quotas. The same qualified
zero-loss endpoint solver uses the original inventory tolerance. Independent
review checks original inputs, fixed references, all stock paths and minimum
repeating-stock behavior, source arrivals, protected exports, sorted
intertown shipments and the full grain ledger. All 112,756 physical source
cases, eight inventory groups and 3683 shipment rows pass; stock trace
differences and compensated full-grain residuals are zero in these cases.
All 1103 protected parent identities remain unchanged.

- [Meal maps](../output/urban_fixed_dispatch_20261117/meal_maps.png),
  [quota effect maps](../output/urban_fixed_dispatch_20261117/quota_effect_maps.png)
  and [monthly meals](../output/urban_fixed_dispatch_20261117/monthly_meals.png).
- [6510 city records](../output/urban_fixed_dispatch_20261117/towns.csv),
  [2170 complete channel differences](../output/urban_fixed_dispatch_20261117/differences.csv),
  [72 month records](../output/urban_fixed_dispatch_20261117/months.csv) and
  [30 region records](../output/urban_fixed_dispatch_20261117/regions.csv).
- [Compact town packet](../output/urban_fixed_dispatch_20261117/town_model.npz),
  [qualification](../output/urban_fixed_dispatch_20261117/qualification.json)
  and [test receipt](../output/urban_fixed_dispatch_20261117/tests.json).

Reproduce in `.venv`: run `scripts/urban_fixed_dispatch.py controls` first,
then its `central` and `low` phases, `scripts/review_urban_fixed_dispatch.py`
for each density, `scripts/render_urban_fixed_dispatch.py` and
`scripts/seal_urban_fixed_dispatch.py`. Completed phases refuse overwrite.
For a fresh replay redirect OUT consistently in fresh processes to an empty
directory and retain pinned inputs/test identities. Large case fields remain
local/ignored; the compact packet, maps and full city differences are tracked.

## Plan after these controls

The calendar, loss, capacity and quota controls now support a clear priority:
**qualify the storage/dispatch interface before more parameter sweeps or an
occupancy update**. Exact-energy date recipes changed aggregate meals by at
most 0.018604 points at the original stores, while the tested capacity change
cost 47.8–52.5 points. That scale comparison applies to the tested settings;
it does not prove calendars are unimportant locally or under other capacities.

The [next source-scoping declaration](../calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json)
starts with existing exposed documentation, separating reserve algebra and
modern context from historical evidence about rural retention, commercial
staging, town storage and seasonal dispatch. Bibliographic leads can identify
where primary evidence might exist; they must not become fitted capacity
observations without later source qualification and exposure registration.
Footprint, usable volume, edible stocks, institutional ownership and throughput
are distinct. No setting is currently qualified as ancient infrastructure.

After that evidence dependency is addressed, the next integration question is
finite occupancy with food and work charged to the same physical sources.
Full diet/resources, rights and independent transfer still require their own
gates before atlas adoption. Climate remains deferred; Buringh sizes, climate
`l` and the archived steppe sidequest remain unopened. Actual population and
main atlas/defaults do not change in this stage.
