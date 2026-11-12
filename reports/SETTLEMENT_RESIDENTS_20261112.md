# A finite resident budget feeds the existing seasonal settlement allocator

The new resident consumer prevents civilian and institutional requests from
creating additional people. It partitions an explicit origin population into
people remaining rural and people allocated to settlements, then feeds the same
seasonal-food `SettlementPlan` used by the existing food/control machinery.
Production atlas values are unchanged. This is an accounting implementation and
conditional sensitivity study, not calibrated town populations.

## One population, including staff

`polity/settlement_residents.py` accepts explicit origin people, one catchment
owner per origin (`-1` unassigned), and a supplied transferable fraction. It
sums allowances once per destination. The maximum civilian-plus-staff group is
bounded by that population allowance and the existing seasonal food ceiling.
Staff receive the existing conditional reservation only if the minimum civilian
community can coexist within both budgets. Otherwise a civilian community may
persist without an institution. Unknown affiliation creates no new staff.

Actual transfers are proportional to origin allowances within each catchment.
Unused allowances, food-limited requests and unassigned origins remain rural.
The accounting identity is `rural origin people + settlement civilians +
settlement staff = original supplied people`. Minimum town requests cannot
create residents. No new occupation estimate, recruitment rate or institutional
role is inferred. The legacy allocator is wrapped without changing its source
or defaults, preserving all previous benchmark producer identities.

## Source food is a separate hard gate

Demographic partition and delivered destination food are insufficient to prove
the full chain feasible. `audit_origin_food` requires twelve-bin origin harvests,
departures, storage capacities, delivery delay and retention. Declared shipments
must reproduce destination arrivals. Remaining rural people must still receive
the same supplied ration while those shipments leave. The audit reconstructs
destination food, rejects changed population/food records, and closes one grain
ledger across rural meals, storage loss, shipments, transport loss, town meals,
unused grain and inventory changes.

It refuses rural-meal shortfalls instead of exporting their food. Numerical
support uses the existing inventory tolerances; actual consumption and tiny unmet
amounts remain explicit in the output. Manufactured balanced and transport-loss
examples retain 100 people across rural/town groups and close grain to below
1e-6 kcal. A third example with insufficient rural meals is rejected. These are
manufactured accounting checks, not Earth observations or calibrated mechanisms.
Production grain must already be compatible with the workers remaining rural;
the audit does not supply free replacement labour, routes or freight capacity.

## Existing atlas cases: conditional population sensitivity

The runner consumes the exact current raw/corrected Earth-atlas
`settled_reach.json.gz` packets. Existing site catchments provide an explicitly
assumed reference population envelope. All market IDs are disjoint between
destinations. These modeled people are not observed inhabitants; rural, pastoral
and forager scenarios must never be added as overlapping populations.

Twenty existing food allocations are replayed with zero difference in their
civilian/staff arrays. Three supplied transfer fractions, 5%, 7.5% and 10%, give
60 cases across raw and corrected climate. The resident consumer uses the same
food arrivals and civilian requests; only the shared population cap is new.
Independent scalar formulas verify 62,610 site/scenario caps and population
partitions and replay destination inventories. A fresh run reproduces
`results.json` and `fields.npz` byte for byte. Ninety-four focused checks cover
the resident/source-food mechanism, previous settlement/service budgets, spatial
placement and food inventories; this is not a full-repository test claim.

For the corrected-climate year-store case:

|Transfer allowance|Earlier town people|New town people|Rural remainder|Conditional sources|
|---|---:|---:|---:|---:|
|5%|812,546|801,473|40,273,912|1,010|
|7.5%|812,546|812,204|40,263,181|1,010|
|10%|812,546|812,376|40,263,009|1,010|

The prior case has 1,011 conditional sources. This shows how population can
restrict food-supported requests; it does not demonstrate that any chosen
urban share or resident count is historically correct. The large modeled rural
remainder is not a revised census. All source maps, locations and food packets
retain their original hashes. No routes or control masks are regenerated.

## Remaining coupling and release boundary

The actual atlas sensitivity still uses food arrivals produced under the older
rural-food claim. It therefore has **not** passed the new source-food gate:
rural meals, available agricultural labour, production, collection and shipments
must be recomputed from the returned rural residents first. The manufactured
gate checks do not grant the actual atlas cases that missing qualification.
No numeric production map is adopted, and release milestones 2–4 remain open.

The next consumer step is to connect origin population/work and net crop
harvests on the same physical cells, rebuild rural needs and collection under
each relocation, and require both population and source-food audits before
passing a resulting `SettlementPlan` to staffing/reach. Feedback must converge
or refuse the case; it cannot retain exports computed for a different rural
population. Empirical resident-size evidence remains distinct: Han district
population is not seat inhabitants, and Roman areas/imputations are not observed
resident counts. All actors, unaffiliated and mobile/nonstate cases remain on
the full roadmap; this primitive does not assign them to permanent towns.

```sh
.venv/bin/python -I scripts/build_settlement_residents.py
.venv/bin/python -I scripts/review_settlement_residents.py
.venv/bin/python -I scripts/build_settlement_residents.py --out output/settlement_residents_20261112/fresh
# Verify both numerical outputs before recording replay.json.
.venv/bin/python -I scripts/publish_settlement_residents.py
.venv/bin/python -I scripts/build_fit_hub.py
```
