# What is still needed to attach shared warehouses — 17 November 2026

The shared-store primitive passes its accounting controls, but the saved Earth
network does not yet supply the chosen-path and physical-store provenance
needed for a warehouse attachment. This read-only audit identifies that next
dependency. It runs no Dijkstra, graph rebuild, food solver or new scenario.

## Available inputs and missing paths

The [schema inventory](../output/urban_shared_store_readiness_20261117/schemas.json)
covers six existing archives: both prepared annual readings, both original
monthly cases, the captured transport world and the original Roman input grid.
It reads archive headers rather than loading unrelated grid values. Saved
monthly owner/departure arrays are used only for the recipient-change counts.

Original preparation computes source-to-town distances on the **reversed**
directed graph, including predecessor output, then discards the predecessor
vector (`d, _, src`). Intertown cost batches are projected to city columns;
the capture explicitly rejects predecessor output. The prepared arrays retain
`dist`, `owner` and `between`, while the monthly arrays retain funded grain
and aggregate arrivals. Neither archive supplies a warehouse ID or chosen node/
edge chain. Endpoints and costs cannot reveal which intermediate port was used.

Among 56,378 physical origins in each reading, **4,050** change recipient
owner across the four route snapshots. That includes **3,458 central/3,457
low** origins that actually export in the original monthly baseline. These
are model recipient changes, not moving historical granaries. A fixed physical
warehouse cannot be identified by a quarter-varying recipient index.

The original `costs_from` API can retain predecessors. An existing isolated
freight connector also retains cost, duration and mode on one path, but it
selects the cheapest parallel alternative before CSR construction. The legacy
graph sums duplicate endpoint records when forming CSR. Replacing the old
graph with that connector is therefore not a neutral provenance replay. This
audit does **not** measure how many Roman routes differ or claim a map error.

The transport-world snapshot is also not a complete standalone world: it omits
`road`, `biome` and `cell_km`. The archived road field exists in the original
Roman input grid, and cell size appears elsewhere, but restoration must follow
the exact old recipe and source identities. The already-reviewed 1981–2010
wind requirement remains; the reader's 1991–2020 fallback must not be used.

## Two accounting traps before network integration

The existing delivered fraction is `max(0, 1-cost/L)` for a whole charged leg.
For positive unclipped costs `a`, `b` with `a+b<L`, splitting that leg and
multiplying new fractions gives

`(1-a/L)(1-b/L) = 1-(a+b)/L + ab/L²`.

The product retains more grain than the original whole-leg rule. That algebra
does not establish a better transport model; it means inserting a zero-hold
store must have an explicit reduction contract before anyone interprets a food
gain. Source, transit and store grain charges must remain conserved.

Likewise, existing source and intertown legs each take one accounting bin.
Treating a new warehouse as another ordinary leg silently adds a bin even when
the store holds nothing. Actual path duration is not saved in the cost arrays
and cannot be obtained by converting road-km directly to days. A no-hold
pass-through test must preserve the original arrival timing, or any deliberate
timing change must be separately declared.

## Remaining attachment contracts

The [15-interface manifest](../output/urban_shared_store_readiness_20261117/contracts.csv)
preserves exact source quotes and separates what is already implemented from
what remains a scenario or missing input:

| Interface | Present | Still required |
|---|---|---|
| Deposits | Protected rural overflow and reviewed field work | Upstream certificate for every warehouse deposit |
| Physical store | Unique-ID/shared-capacity primitive | Actual store location, capacity and phase association |
| Allocation | Explicit static origin partition | Route-aware time allocation without copying source grain |
| Paths | Endpoints, distances and owners; predecessor-capable API | Original directed node/edge/port certificates |
| Freight/timing | Whole-leg retention and one-bin assumptions | Explicit zero-hold reduction before splitting a leg |
| Permission | Supplied pooling flag | Historical rights/access or a clearly declared scenario |
| Capacity overlap | Separate commercial and town budgets | One physical store counted once across roles |
| Work/people | Shared rural field workforce and fixed-request ledger | Handling, transport and complete work/resources |

The Ostia source supplies no adopted capacity or ownership coefficient. The
primitive's pooling flag does not close those empirical gaps. The existing
finite people/work accounting must remain at the physical sources; warehouse
pooling cannot duplicate land, grain, workers or recruitment.

## Next declared work

The [route-provenance declaration](../calibration/urban_diagnosis_20261117/warehouse_route_provenance_controls.json)
limits the next step to at most **16 original route records**: one largest
recorded source leg and one largest intertown leg per quarter/density, with
deterministic ties. Selection must be frozen before any route replay. Rebuild
only the original four snapshots and preserve legacy graph semantics. Exact
archived source owners/distances and selected intertown costs must pass before
interpreting paths. No new full all-pairs table, warehouse mapping, capacity,
grain dispatch or meal scenario is authorized by that declaration.

Representative least-cost paths are not evidence that an unrecorded original
path was unique. Auxiliary nodes, direction and parallel-mode ambiguities must
remain visible. Physical days, empirical store rights and source-to-warehouse
attachment remain later dependencies. This is engineering provenance on an
exposed development network, not independent historical validation.

The [qualification](../output/urban_shared_store_readiness_20261117/qualification.json)
checks exact source quotes, schemas, recipient-change counts and all 1103
protected identities. Reproduce with `scripts/audit_shared_store_readiness.py`
then `scripts/seal_shared_store_readiness.py`, redirecting OUT to an empty
directory for fresh replay. All old producers/outputs, population and atlas
defaults remain unchanged. Climate/steppe and reserved pools remain deferred.
