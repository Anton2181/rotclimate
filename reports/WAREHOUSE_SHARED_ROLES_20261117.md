# Commercial and town claims share one physical store — 17 November 2026

The new isolated `polity/warehouse_roles.py` adapter connects funded endpoint
arrivals to one inventory and capacity per physical store. Commercial and town
claims are explicit withdrawal roles, not separate copies of the building or
grain. **21 tests pass.** Seven declared manufactured scenarios match all
**15 aggregate inventory fields exactly** against seven direct shared-store
controls, and an independent canonical/physical-ledger review passes every case.
No Earth food scenario or actual warehouse assignment was run.

## Fund once, store once, allocate paid withdrawals

The adapter revalidates no-hold receipts and unique consignment IDs across
batches. Each consignment has one explicit store assignment whose physical node
matches its paid endpoint. Repeat arrivals from the same physical origin/store
are coalesced before inventory; they do not become fictitious extra origins.
Material labels and supplied pooling permission must match. Stores require
unique IDs and distinct supplied nodes; multiple buildings within one model
node are currently unsupported rather than inferred.

All role requests at a store enter **one** existing `shared_warehouse_year` call.
Actual funded withdrawals are then allocated by the supplied fixed role-priority
permutation. Priorities do not resize capacity, deposits or requests. Total role
payments must conserve store departures; each payment is nonnegative and no
larger than that role's request. Freight charges are already paid upstream and
are not reapplied to store deposits. The complete ledger includes freight,
withdrawals, stored spoilage, overflow and stock change.

Priorities and permission are scenario inputs, not reconstructed institutions.
The adapter does not itself certify protected rural meals/work, handler staffing,
historical capacity or rights. A new consignment ID cannot authenticate grain.

## Finite manufactured results

The [declaration](../calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json)
was committed with the no-hold packet before these scenarios ran. Inputs are
manufactured kcal, not archaeological measurements or adopted coefficients.

| Scenario | Physical capacity | Commercial paid | Town paid | Total paid |
|---|---:|---:|---:|---:|
| Shared120 pulse | 20 | 24 | 6 | 30 |
| Priority commercial→town | 5 | 13 | 2 | 15 |
| Priority town→commercial | 5 | 11 | 4 | 15 |
| Calendar wrap, 5% stored loss | 30 | 30 | 15.695581 | 45.695581 |
| Two stores, second unfunded | 20+20 | 30 | 0 | 30 |
| Zero capacity | 0 | 8 | 2 | 10 |
| Zero delivered grain | 20 | 0 | 0 | 0 |

The shared-pulse case has two60 arrivals, requests8+2 each month, one20 capacity,
and90 overflow. It pays30, not two independent reserves. At capacity5, changing
priority redistributes the same15 total; all aggregate stock fields are identical.
The unfunded second store cannot borrow first-store grain or pay from inherited
stock. Zero capacity can pay immediately funded requests but carries nothing.
Calendar-wrap receipts arrive in bins11/0, then use the original inventory's
stored-loss and repeating-stock rules; no extra transport bin is inserted.

## Independent checks and call scope

The reviewer independently groups fixture arrivals and requests, replays one
canonical ledger year from each recorded initial stock, checks all15 fields
exactly, and reconstructs monthly physical grain balances and role-priority
constraints. The maximum periodic residual/original-tolerance ratio is0. The
largest whole-grain residual is1.42e-14 kcal, retained at the existing tolerance.
No original food, storage or routing kernel was changed.

Call counts distinguish scenario evaluation from reference/review work:

| Phase | New role adapter | Direct shared-store reference | Canonical years | Annual-map advances |
|---|---:|---:|---:|---:|
| Seven scenarios | 7 | 0 | 13 | 0 |
| Seven aggregate reductions | 0 | 7 | 13 | 0 |
| Independent reviewer | 0 | 0 | 7 | 0 |

Pytest calls are separate. This is seven manufactured scenarios, not33 scenarios
or any new Earth food case. All1103 protected identities remain exact. See
[qualification](../output/urban_warehouse_roles_20261117/qualification.json),
[scenarios](../output/urban_warehouse_roles_20261117/scenarios.json) and
[independent review](../output/urban_warehouse_roles_20261117/review.json).

## Next dependency: physical work

Shared capacity and paid withdrawals now have an integrated accounting control.
The [next read-only declaration](../calibration/urban_diagnosis_20261117/warehouse_work_readiness.json)
audits existing rural/task budgets before any handling-work integration.
Unspent listed cereal-work allowance is not evidence of available warehouse
staff, a complete monthly occupation schedule or authenticated access to a port.
No handling-rate coefficient, staff recruitment or physical time is imputed.

Climate/steppe, reserved pools and the site-survey workbook remain deferred/
unopened. There is no new fit, actual population or atlas/default change.
Reproduce in an empty isolated OUT with a matching test receipt using
`scripts/audit_warehouse_roles.py`, `scripts/review_warehouse_roles.py` and
`scripts/seal_warehouse_roles.py`. Qualified packets refuse overwrite.
