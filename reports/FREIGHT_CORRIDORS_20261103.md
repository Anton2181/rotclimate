# Seasonal freight corridors on the current world — 3 November 2026

The experimental food-provisioning component now uses routes on the actual raw-r43 fantasy geography. Cost and duration follow the **same directed legs of one least-cost path**. A cheap journey can take longer than an expensive alternative. Freight cost, travel time, food energy, cargo capacity and town population remain separate quantities.

## Basis and implementation

The connector reuses the project's existing road/terrain, climate-sensitive sailing and navigable-river edge generators. Historical freight ratios derive from Stanford's [ORBIS network model of the Roman world](https://history.stanford.edu/publications/orbis-stanford-geospatial-network-model-roman-world). The inherited sailing model draws on Casson, *Speed under sail of ancient ships*, Transactions of the American Philological Association 82 (1951), pp.136–148. Neither source independently validates the fantasy geography's speeds, seasons or cargo capacities.

`polity/freight_corridors.py` retains each directed leg's freight cost in road-kilometre equivalents, physical days and transport mode. River legs are generated with the same topology for pricing and physical speed; auxiliary river nodes retain their physical-cell identities. Dijkstra minimizes freight cost; the duration reported is the sum along that selected path, **not an independently computed fastest journey**. Equal-cost parallel alternatives prefer shorter duration and then a deterministic mode order. No time is inferred by treating the freight-cost unit as physical kilometres.

`polity/food_transport.py` supplies the cyclic, time-expanded food ledger. Its network-flow foundation is [Ford and Fulkerson (1958), Constructing maximal dynamic flows from static flows](https://doi.org/10.1287/opre.6.3.419); storage, physical losses and aggregate consumption priorities are explicit adaptations. It is a feasibility/cost component, not a price equilibrium.

## Fixed preview and results

The plan was committed before routing. Distinct marked ports nearest drawing fractions (0.18,0.72) and (0.82,0.62) were selected, with A/B labels. Metadata places nearest these endpoints are Sabate and Pitané; these are context, not verified settlement identities. All 12 model months and both directions are retained. Months 1 and 7 were preselected for the figure.

A→B least-cost journeys range from 26.3 to 78.1 days; B→A from 28.1 to 77.6 days. In month 1, A→B costs 1,149 road-km equivalents and takes 78.1 days; in month 7, 522 and 27.1 days. The direction and seasonal path changes arise from the inherited edge generators. These are conditional model results, not observed journey accuracy.

The same manufactured harvest pulses from the linked field-water demo were assigned to each export endpoint in turn. Annual rural food need is 365 units, town need 146; one unit is 10,000 kcal. Rural need has priority. Farm/town storage capacities are prescribed at 365/30 units; departure capacity is 4 units per five-day step, with no physical food loss. A journey is rounded upward to a whole five-day transport delay. Each step uses the route for its departure month. There is no inferred local crop production, town demand, cargo tonnage or population.

Both directions meet all prescribed farm and town food need. Approximately 4.469 units spill, and annual food ledgers close to 2.85e−14 units. The normalized freight objectives differ (89,103 for A→B and 87,020 for B→A), but are **not currency, measured trade values or calorie losses**. No claim of a food shortfall or population benefit follows from this nonbinding-capacity example.

## Parallel transport alternatives

Each monthly graph contains 155 directed endpoint pairs with two alternative leg records. A sparse CSR constructor normally sums duplicate entries; that is not the cost of choosing a transport alternative. The isolated connector selects the least-cost record before CSR construction, preserving that record's duration and mode. Across these pairs the largest summed/selected ratio in a monthly graph ranges from 4.48 to 20.10; these are local edge ratios, **not total-route or map error estimates**. The existing travel and trade graphs are unchanged. A paired comparison must measure affected paths and outputs before any production replacement.

## Limits and next work

* Conditions are frozen to one month throughout each journey. A 78-day trip is not propagated through changing weather. The connector uses the trade graph's edgewise seasonal sailing expectation, not the separate whole-voyage fair-weather-spell approximation.
* One least-cost route is retained per departure month. The food solver cannot select a faster, more expensive alternative to avoid a seasonal shortage.
* Capacity is a supplied departure throughput, not a fleet inventory. No finite ships, empty returns, convoy scheduling, competing corridors or shared vessel constraints are inferred.
* Fixed retention is separate from freight cost. Journey duration does not automatically imply a spoilage rate; loss coefficients need explicit evidence/scenarios.
* Stocks and in-transit food repeat over the year. This is not a town-founding simulation with an independently observed initial inventory.
* Actual-world crop calendars, cultivar requirements, soil, water supply, storage and labour inputs still need validation before this can estimate food support on the map. A nearby river is not a measured irrigation supply.

The legacy production climate, farming and population layers remain unchanged. This is published as a research component in the launcher-linked economy lab, with the complete path and food-budget receipt.

## Reproduction

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/review_freight_corridors.py
.venv/bin/python scripts/publish_freight_corridors.py
.venv/bin/python scripts/build_economy_lab.py
```

The first command verifies declared atlas inputs and can take several minutes to rebuild geography and route all months. The publisher verifies the stored source/input hashes and path totals, then renders the recorded routes with readable sea lines; it does not reroute or select results. `output/freight_corridors_20261103/review.json` and `presentation.json` retain the identities. Focused tests cover directed paths, same-path metadata, parallel alternatives, auxiliary nodes, food conservation, capacity and transit delays.
