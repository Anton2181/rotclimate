# One physical work budget across handling roles — 17 November 2026

The isolated `polity/task_budget.py` checker now tracks one supplied physical
workforce budget across already-charged baseline tasks and additional roles.
**24 tests pass.** All eight predeclared manufactured outcomes pass independent
scalar review: **three accepted, five rejected**. No original work, food/stock,
graph, weather or demographic solver runs, and no Earth staff is assigned.

## Shared annual and monthly constraints

The stateful `TaskBudget` requires unique workforce IDs, annual and twelve-bin
capacities, complete baseline monthly work, consistent baseline annual use and
named already-charged baseline tasks. An explicit complete-schedule declaration
is required. It does not infer missing task timing or replace it with reaping.

Additional tasks each name an ID, physical workforce, month, role and supplied
hours. Repeated calls reserve against the **same remaining** annual/monthly
capacities. Baseline or previous task IDs cannot be charged again; rejected
batches claim no IDs/hours. Different roles do not receive separate copies of
the workforce, and unused time at a different workforce cannot be borrowed.

Both constraints use the original work scale `1e-8*max(1,capacity)`. Annual
capacity is not the sum of twelve independently spendable annual pools. Role
totals must describe the same additional monthly work. Returned certificates
copy inputs and state, so caller mutations cannot enlarge the live budget.

Complete schedules, workforce identity and task hours remain supplied contracts,
not authenticated historical evidence. Known IDs prevent duplicate recorded
debits; a newly named task is not automatically an empirical task observation.

## Declared outcomes

| Manufactured case | Result | Reason |
|---|---|---|
| Baseline6, commercial3+town1, capacity10 | Accept | Joint total10 |
| Baseline6, commercial3+town3, capacity10 | Reject | Both cannot independently spend the same unused4 |
| Annual30, monthly8, baseline6+task3 in one bin | Reject | Monthly9 exceeds8 |
| Annual10, monthly10, baseline6+tasks3 in two bins | Reject | Annual12 exceeds10 |
| Complete zero baseline, task6 in bin0/task4 in bin11 | Accept | Annual10, each month within8 |
| Complete zero baseline/additional zero | Accept | No automatic work or recruitment |
| CrewA has capacity5/baseline4/task2; crewB unused100 | Reject | CrewB cannot fund crewA's6 |
| Missing complete baseline schedule | Reject | Do not manufacture omitted occupation timing |

Tests also cover reservations across calls, already-charged baseline IDs,
duplicate/invalid task and workforce IDs, nonfinite/negative inputs, inconsistent
annual/monthly schedules and atomic rejection. The independent reviewer calls
the new checker **zero** times and reconstructs both constraints and role sums
from scalar fixture values. All1103 protected identities remain exact.

See [qualification](../output/urban_warehouse_tasks_20261117/qualification.json),
[cases](../output/urban_warehouse_tasks_20261117/cases.json) and
[review](../output/urban_warehouse_tasks_20261117/review.json). The
[finite declaration](../calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json)
preceded execution. This continuation's three new modules pass79 tests in total
(34 no-hold,21 shared-role,24 shared-task); those suites are separate from the
qualified manufactured/reference/reviewer evaluations.

## Next bounded bridge and remaining evidence

The [next three-case declaration](../calibration/urban_diagnosis_20261117/warehouse_grain_work_coupling_controls.json)
converts the already-paid manufactured grain receipts into explicit handling
claims. It uses existing priorityAB/BA receipts only, with supplied toy intensities
and one crew budget; no inventory rerun. The same15 grain total can require
different handling hours by role and fail a shared budget. Missing baseline
timing must still reject certification. This will test integration, not calibrate
a task rate or choose a historical priority.

For Earth attachment the original B600 non-reaping monthly schedule, handler
affiliation/travel, task/material units, handling intensity, operational capacity
and access evidence remain missing. Passing this checker does not fill them.
After the finite bridge, evidence inputs take priority over further variants.
Reserved pools and site-survey workbook remain unopened; climate/steppe deferred.
No population, fit or atlas/default change occurs.

Fresh replay requires an empty isolated OUT and pinned test receipt, then
`scripts/audit_warehouse_tasks.py`, `scripts/review_warehouse_tasks.py` and
`scripts/seal_warehouse_tasks.py`. Qualified packets refuse overwrite.
