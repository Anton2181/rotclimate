# Paid grain and shared handling work are now linked — 17 November 2026

The isolated `polity/handling_claims.py` converter turns already-delivered
consignments and **actual paid** role withdrawals into explicit handling tasks.
**14 tests pass.** Exactly three predeclared manufactured coupling controls
pass independent receipt/task/Fraction-hour review, using frozen grain results
without rerunning any store, role, food or stock solver.

The same15 paid grain units require10.8 versus11.4 total hours under two supplied
role priorities and toy handling intensities. With one11-hour crew budget,
the first passes and the second fails. A complete baseline schedule is also
required. This connects grain and work accounting; it does not establish an
ancient handling rate, staff assignment or historical priority.

## Tasks follow paid grain, once

Each positive original consignment generates one unloading task at its existing
endpoint arrival bin. Each positive paid role/bin cell generates one withdrawal
task. Tasks retain original grain references, store ID, month, role, grain,
explicit unit/rate and assigned workforce. Unpaid requests do not generate
completed work. Changing requests without changing actual payment leaves tasks
unchanged. Original incoming/departure amounts and source receipt identities
must agree; duplicate consignments and mismatched endpoints fail.

Rates require explicit `net edible kcal` and `hours/net edible kcal` units.
No mass, density, physical duration or empirical productivity is inferred.
Tasks reserve the same `TaskBudget` once; claiming them again fails by ID.
The converter neither changes dispatch/priority nor hires workers to pass a
failed budget. It preserves all frozen grain outputs and physical capacities.

## The finite comparison

Only existing manufactured `priority_ab` and `priority_ba` receipts are used:
capacity5, two60 arrivals in bin0, total paid15. Supplied toy rates are
0.01 unloading hours per delivered kcal,0.2 commercial hours per paid kcal,
and0.5 town hours per paid kcal. One hypothetical crew has annual11 hours,
monthly10, and6 already-charged baseline hours in bin0. These numbers are
engineering inputs with no empirical qualification.

| Case | Paid commercial/town | Unloading hours | Withdrawal hours | Total with baseline | Outcome |
|---|---:|---:|---:|---:|---|
| Commercial first, complete baseline | 13 / 2 | 1.2 | 3.6 | 10.8 | Accept |
| Town first, same grain total | 11 / 4 | 1.2 | 4.2 | 11.4 | Reject annual budget |
| Commercial first, incomplete baseline | 13 / 2 | 1.2 | 3.6 | 10.8 | Reject missing schedule |

Neither priority is adopted. Different supplied work intensities can make the
same grain total differ in feasibility; this is not a selection or fit of an
institutional policy. No new Earth case or numerical rate/priority sweep runs.

## Independent checks and retained review corrections

The independent review derives each task from the frozen positive arrivals and
paid role/bin cells, then computes exact decimal Fractions for task hours and
both budget constraints. It checks **16 task records** across counts5/6/5.
The second priority splits the final-bin withdrawal between two roles, so it
correctly has an extra task despite the same total grain.

An initial reviewer assertion and follow-up metadata field incorrectly assumed
five tasks in every case. Both failures are retained in the packet. The
reviewer now derives counts from the original receipts and explicitly verifies
5/6/5; all hour/outcome checks pass. The producer, converter, rates, grain
outputs and inventory kernels were not changed or reexecuted for those fixes.

Producer counts: three converters; three no-hold receipt materializations and
three converter funding revalidations; **zero role/store/food/stock solves**.
The reviewer calls all new converters/checkers zero times. Both make zero
original component-work, graph, Dijkstra, climate or demographic calls.
All1103 protected identities remain exact. See
[qualification](../output/urban_warehouse_coupling_20261117/qualification.json),
[cases](../output/urban_warehouse_coupling_20261117/cases.json) and
[independent review](../output/urban_warehouse_coupling_20261117/review.json).

Across this continuation, four new isolated modules pass **93 tests**:
34 no-hold,21 shared-role,24 shared-task and14 grain-to-task conversion tests.
These are separate from manufactured/reduction/reviewer evaluations. Old
scientific producers, existing Earth cases and atlas defaults are frozen.

## Evidence before more numerical variants

The engineering chain now links funded grain, one physical store/capacity,
explicit withdrawals and one shared work budget. Earth attachment still lacks
the complete monthly non-reaping baseline, authenticated handler affiliation/
travel, handling/material evidence, operational capacity and access rights.
The earlier audit's unspent crop-work allowance cannot supply these inputs.

Existing `harvest/labour.py` already schedules operations inside supplied windows;
`polity/monthly_work.py` already audits competing collector/staff duties. Their
published examples include manufactured windows, handling loads/times and
availability profiles. The [next read-only declaration](../calibration/urban_diagnosis_20261117/warehouse_work_evidence_scope.json)
audits their evidence and reusable interfaces before selecting one concrete
primary evidence target. It does not rerun these models, reopen a cohort or
turn their scenario coefficients into observations. Further numerical variants
are deferred until that input contract is clear.

Reserved pools and site-survey workbook remain unopened; climate/steppe deferred.
No fit, actual staff/population or atlas/default adoption occurs. Fresh replay
uses an empty isolated OUT and pinned test receipt, followed by
`scripts/audit_warehouse_coupling.py`, `scripts/review_warehouse_coupling.py` and
`scripts/seal_warehouse_coupling.py`. Qualified packets refuse overwrite.
