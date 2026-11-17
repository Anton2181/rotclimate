# One physical warehouse, one capacity budget — 17 November 2026

The isolated shared-warehouse primitive is implemented in
[polity/shared_warehouse.py](../polity/shared_warehouse.py). Several explicitly
permitted origins can fund one store without multiplying its capacity. The
primitive accepts supplied deposits and withdrawals; it does not infer warehouse
locations, rights, capacity, routes or urban demand.

Nineteen tests pass. Four required legacy reductions reproduce **all 15
FoodYear fields and actual departures exactly**: central/low × five-percent/
zero stock loss at the existing 90-day commercial capacity. This is 225,512
origin-store control rows, with no new Earth meal scenario or port assignment.

## Physical and permission contracts

Inputs are twelve-bin net-edible kcal deposits, one explicit origin-to-store
assignment, unique physical store IDs, one finite capacity per store and
explicit monthly withdrawal requests. Pool labels must match for every assigned
origin and its store. More than one assigned origin requires a supplied boolean
pooling permission. That flag records a scenario assumption; it cannot prove
historical collective rights or source entitlement.

Duplicate physical IDs, incompatible material pools, nonfinite/negative energy,
unknown or unlimited capacity and unassigned positive deposits are rejected.
An unassigned origin with exactly zero deposits is allowed. Integer partition
types include signed and unsigned arrays. A zero-capacity store can pay an
immediate funded request at receipt, while carrying no stock. Zero deposits
cannot fund an inherited reserve. Zero withdrawal requests cause no departures.

Capacities and quotas remain explicit when deposits change; neither is resized
from the scenario's annual supply. The primitive groups each origin exactly once
and reuses the frozen qualified zero/five-percent inventory adapter. Zero loss
retains the reviewed smallest-endpoint method and original tolerance. Paid
departures equal withdrawal requests minus unmet withdrawals. Stock, spoilage,
overflow and annual stock change close in one compensated physical ledger.

Deposits must already have been released by the upstream rural ledger. This
primitive does not certify that a producer met rural meals or paid field work.
It does not assign paid withdrawals back to owners, route them to a city,
recruit workers or infer a demographic equilibrium. Those are later contracts.

## Controls and independent review

Five [manufactured cases](../output/urban_shared_warehouse_20261117/manufactured.json)
cover one shared harvest pulse, two pulses with decay, zero deposits, zero
capacity and zero withdrawals. In the simple two-origin example, 120 invented
kcal enter one store with 20kcal capacity and 10kcal monthly requests. It pays
30kcal, spills 90kcal and never carries more than 20kcal. These are manufactured
units, not a historical granary estimate or food-policy comparison.

The [four legacy receipts](../output/urban_shared_warehouse_20261117/controls.json)
use one store per original source as an exact reduction. They take the original
marketed arrays, dispatch arrays and saved capacities; they rerun only the
export inventories. Rural work/grain, requests, routes, city allocations and
all old outputs remain frozen. The shared primitive is not replayed again by
the reviewer.

Independent review groups by explicit source additions, checks canonical
bisection for five-percent inventories and separate zero-loss endpoint traces,
then rebuilds every monthly physical ledger. All nine inventory groups pass;
maximum difference is 0.546307 of the original inventory tolerance and maximum
compensated whole-grain residual is zero. The reviewer performs no new shared
mapping on Earth. All 1103 protected parent identities remain unchanged.

Kernel counts are separated rather than described as zero:

| Scope | Shared-adapter calls | Canonical full-year ledger evaluations | Canonical annual-map advances |
|---|---:|---:|---:|
| Five manufactured producer cases | 5 | 7 | 0 |
| Four legacy producer reductions | 4 | 6 | 0 |
| Independent stock review | 0 | 5 | 102 |

The counters instrument the canonical `_year` and `_advance` functions while
preserving their calculations. Pytest is separate from this audited run. A
canonical year/map evaluation is an implementation operation, not another
physical scenario. See the [qualification](../output/urban_shared_warehouse_20261117/qualification.json),
[review](../output/urban_shared_warehouse_20261117/review.json) and
[test receipt](../output/urban_shared_warehouse_20261117/tests.json).

## Next step

The [next declared audit](../calibration/urban_diagnosis_20261117/shared_store_coupling_readiness.json)
checks whether saved routes identify the physical paths and intermediate ports
needed to attach a store. Endpoint owners and aggregate freight costs alone
cannot identify a warehouse or assign its shared capacity. A seasonal recipient
owner also cannot serve as a physical store ID that moves each quarter.

The Ostia source motivates a distinct physical store, while its wheat, pile,
upper-storey and capacity assumptions remain unqualified for this model. Its
unresolved printed arithmetic is not repaired or used as a coefficient. No real
warehouse mapping, new Earth capacity/quota, historical right, population/staff
change or atlas/default adoption follows from these controls. Full diet/work,
rights and independent transfer gates remain open; climate stays deferred.

Reproduce in `.venv`: `scripts/audit_shared_warehouse.py`,
`scripts/review_shared_warehouse.py`, then `scripts/seal_shared_warehouse.py`.
Completed stages refuse overwrite; redirect OUT consistently to an empty
directory with the pinned test receipt for a fresh replay. Large original
source arrays remain local; new public artifacts are compact JSON receipts.
