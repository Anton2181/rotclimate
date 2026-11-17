# Grain and timing through zero-hold events — 17 November 2026

The new isolated `polity/no_hold.py` ledger preserves one funded whole leg while
annotating intermediate charge events. **34 tests pass.** Eight predeclared
manufactured cases pass independent exact-fraction grain/timing checks. Exactly
two original monthly baseline accounting reductions reproduce all **eight
direct/intertown arrival/export arrays exactly**, without any food/stock solve.

## One consignment, one charge and one arrival

Each batch supplies unique consignment IDs, physical endpoint IDs, original sent
and delivered kcal, departure/arrival bins and zero hold. Duplicate IDs within
or across calls fail atomically. Delivered grain may not exceed funded sent
grain. Intermediate labels and nonnegative charges annotate that same movement;
they do not authorize another shipment, capacity, right or time bin. Explicit
allocations must sum to the original whole-leg charge and may not overdraw it.
Returned arrays are copied and read-only; the exact upstream delivered value
remains authoritative, including its original rounding.

The counterexample is now executable: sent100, costs25+20 at L100 delivers55
under the existing whole-leg rule. Multiplying .75×.80 would deliver60. The new
ledger keeps55, with the original arrival bin. Changing the allocation of the
existing45 charge cannot create the extra5 or add a delay. December departures
still arrive in January. The accounting scale remains `1e-10*max(1,sent,delivered)`;
endpoint reduction equality is exact and no food/path tolerance changed.

The ledger validates supplied funding identities; it cannot authenticate an
external source's grain merely from a new ID. Upstream protected-rural/work
funding remains a separate obligation. Event labels are not warehouse evidence.
Positive hold, capacity and rights have no supported input here.

## Exact original reductions

The [finite declaration](../calibration/urban_diagnosis_20261117/warehouse_no_hold_controls.json)
was committed as `25723f6c6` before implementation execution. Source rows keep
their original physical order and per-month `bincount` operation. Recorded
intertown shipment order and sent/got values remain intact. The only new
annotation divides an already-paid charge into quarter/quarter/remainder;
no retention is recomputed for intermediate stops.

| Original reading | Source records, including zero amounts | Intertown records | Exact arrays |
|---|---:|---:|---:|
| Central | 617,142 | 8,173 | 4 |
| Low | 617,142 | 7,723 | 4 |

These are **1,250,180 consignment records**, not that many positive shipments or
new routes. Both replays make13 ledger calls. Exact arrays are `direct`,
`inter_received`, `inter_exported` and combined `arrivals`. The independent
review uses scalar source accumulation and archived shipment rows, with **zero
new-ledger calls**; it also independently checks all manufactured events using
Fractions. No graph, Dijkstra, weather, crop, food, stock or demographic solver
runs in either producer or reviewer. This is zero new Earth food scenarios.

Per-consignment charge-allocation residuals are zero in both reductions.
Separately rounded aggregate totals have residuals −0.00390625 kcal central and
+0.001953125 kcal low against about3.29e13/1.37e13 kcal sent, within the existing
grain accounting tolerance. They are retained rather than adjusted to zero.
All1103 protected identities remain exact; old producers/outputs are frozen.

See [qualification](../output/urban_warehouse_no_hold_20261117/qualification.json),
[independent review](../output/urban_warehouse_no_hold_20261117/review.json) and
[control receipts](../output/urban_warehouse_no_hold_20261117/controls.json).
Compact exact arrival arrays are tracked; no original large cache is duplicated.

## Next integration

The [shared-role declaration](../calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json)
connects funded endpoint arrivals to one physical inventory across explicit
commercial/town claims. Seven manufactured scenarios must prove one capacity,
one grain balance, explicit withdrawal priority and no cross-store borrowing;
all15 aggregate inventory fields must reduce to the qualified shared ledger.
This closes a structural accounting gap without selecting a real warehouse or
imputing its capacity, access or handling workforce. No Earth case is declared.

Climate/steppe, reserved Buringh size/climate pools and the site-survey workbook
remain deferred/unopened. No fit, population or atlas/default adoption occurs.
For fresh replay use an empty isolated OUT and pinned test receipt, then run
`scripts/audit_warehouse_no_hold.py`, `scripts/review_warehouse_no_hold.py` and
`scripts/seal_warehouse_no_hold.py`. Completed packets refuse overwrite.
