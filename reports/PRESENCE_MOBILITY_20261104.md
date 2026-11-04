# Sustained presence and seasonal resource circuits

This report records baseline milestone `b919802e`. The subsequent
[origin-storage and regional-scale study](PRESENCE_MOBILITY_SCALE_20261104.md)
adds sensitivities while preserving these original results.

These are two new, isolated scenario layers in the normal `.bat` atlases:
**Political reach → Sustained presence**, and **Livelihoods → Seasonal circuits**.
Both use matching Free, Earth raw, Earth corrected and Whittaker climate packets.
They do not change ownership, climate, yields or any population total.

## What the literature supports

Turner & Schlecht (2019), [Livestock mobility in sub-Saharan Africa: A critical
review](https://doi.org/10.1186/s13570-019-0150-z), distinguishes daily grazing
around a base from movements between bases. Its discussion also cautions
against equating mobility, ecology and institutions. This implementation uses
resource patches and travel between them; it does not classify societies from
their biome or equate pastoral, tribal, mobile and nonstate populations.

Roth (1999), [The Logistics of the Roman Army at War, 264 BC–AD
235](https://books.google.com/books?id=LfRiXN5hhCUC), motivates separating food
requirements, supply sources and logistics from travel reach. Only the
bibliographic/publisher description was consulted here; no numerical coefficient
is attributed to unread chapters. This mechanism also applies to civilian or
nonimperial resident groups, without assuming a Roman institutional template.

The [FAO grain-storage manual](https://www.fao.org/4/x5065e/x5065E04.htm)
describes mechanisms of deterioration. The chosen 5% annual loss from stored
energy is an **assumption**, not a universal measured ancient loss rate.
[Ford & Fulkerson (1958)](https://doi.org/10.1287/opre.6.3.419) provides the
general distinction between flow capacity and transit time. This code uses
fixed collection routes and cyclic inventories, not that paper's algorithm.

All numerical budgets are declared in
[`data/presence_mobility_model.json`](../data/presence_mobility_model.json).
Scholarly motivation is separate from calibration or historical validation.

## Sustained presence: food support at marked sites

All **151 verified marked sites** are included, including ten whose affiliation
is unresolved. No generated settlements, road-cell authority sources, ranks,
legion numbers or troop-strength multipliers enter. Actors and communities
without marked sites remain unscored; this is not an absence-of-authority test.

### Geography and collection

Each majority-land travel cell is assigned to its nearest marked source by
directed **cell-to-source** cost in the first climate bin. Only paths costing
at most one reference travel-day in that direction enter the fixed experiment.
Every month, both directions along that same parent-tree path must cost at
most one day each for dispatch to be allowed. Each cell can supply **one** site,
so overlapping sources cannot spend the same grain. Static source selection
and routes do not find every possible seasonal detour or trade connection.

Costs use existing terrain, slope, snow, heat, mud, mapped roads and ford
penalties, with constant off-path pace. There is no feedback from predicted
population, no inferred tracks, ferries, navigable-river freight or sea freight.
This is a **collection eligibility** calculation, not a conversion of walking
speed into cart capacity. Freight slots are separately prescribed. Conditions
are frozen within each reference bin; there is no daily weather simulation.

Collection areas are accounting partitions, not territorial control polygons.
Permission to collect food and cross painted boundaries is assumed open in
these experiments. Political affiliation labels do not establish property,
taxation, cooperation or coercive rights.

### Cereal and rural priority

Use the already published least-listed-work wheat/barley choice, its net
edible kcal/ha, arable fraction, 0.6 farmed share, 0.68 annual sowing/fallow
fraction, and fraction-weighted land area. One cereal harvest is selected from
the existing tied optimal calendar masks: either the first or the last possible
boundary. Alternatives are **not** probabilities or multiple harvests.
Rice, millet, dates, second crops, fish and animal food are omitted.

The experiment's local rural food requirement is 60% of that annual cereal
energy, eaten uniformly across twelve bins. This is an energy-budget scenario,
not an inferred rural census. Each cell has 365 demand-days of protected rural
storage, with explicit 5% annual stored-energy decay. A repeating inventory
prevents free inherited food. If any local annual food requirement is unmet,
**none of its overflow is made available for export**.

The legacy `NEED_KCAL=1.1e6` capacity denominator, which already includes an
implicit storage/draft allowance, is never used. Seed/edible deductions already
in crop energy are not applied twice. New energy ledgers are not added to
existing farming, pastoral or FORGE population capacities.

### Export storage, freight and destination stores

Ten percent of eligible rural overflow enters a **separate on-farm export
inventory at its original cell**. The rest is unavailable for this test. Its
capacity is one year of that cell's annual exportable flow, with explicit
decay. This is an assumed physical storage capacity, not observed granaries.

Each source receives prescribed freight slots of 16.5 million edible kcal per
bin, equivalent to 5 tonnes at 3,300 kcal/kg. Cells share those slots in
proportion to annual exportable supply, without reallocating blocked slots to
other cells. Draws require open same-site collection paths. Actual available
grain limits dispatch; blocked grain can remain in its own finite store.
Shipments arrive one bin later with 95% energy retention. Origin food stocks,
in-transit grain and destination stocks all repeat over the year.

The destination group eats 2,500 kcal/person/day. Seven explicit scenarios:

1. 100 people, 90 demand-days of destination storage.
2. 100 people, no destination storage.
3. 100 people, 90-day storage, two-bin dispatch interruption.
4. The same interruption with no destination storage.
5. 500 people with the same freight slots.
6. 500 people with five times the freight slots.
7. 100 people with the alternative tied crop calendar.

The interruption removes the two busiest adjacent dispatch bins for each site
in its undisturbed case, including cyclic adjacency. It is an imposed stress,
not predicted conflict, weather or necessarily the globally worst disruption.
The minimum zero-loss destination store is a lower bound; insufficient annual
supply stays an annual deficit rather than a fictitious reserve.

Each map colours a fixed collection area by its receiving site's **worst-bin
fraction of specified food need met**. Grey is outside the collection experiment.
Readouts and CSVs identify the receiving site, assumptions and seasonal ledger.
The original de facto map remains available for comparison, with no new power
multiplier. Feeding a group is necessary for many forms of permanent presence;
it does not establish staff, labour, shelter, pay, authority or sovereignty.
Neither clearing/cultivating labour nor crew/draft-feed costs are newly solved;
the ration and delivery-retention scenarios do not claim to cover them.

## Seasonal mobility: one closed herd per independent landscape

Four **previously fixed** pasture-resource examples are reused: Tarani,
grassland outside named claims, mixed resources outside named claims, and the
Tribes of the Neck. These are geographic illustrations, not representative
ethnographic samples or assignments of livelihood to those polities. The
starting point is an arbitrary fixed resource anchor, not an observed camp.
Other land remains unscored, not uninhabited.

Each landscape includes majority-land, seasonally resolved cells within five
analysis cells of its anchor (about 18.4 km radius). Each nonoverlapping cell
is a daily-grazing resource patch. Fresh forage uses the earlier Miami-NPP,
edibility and uncalibrated seasonal allocation assumptions, excluding assigned
crop area. It is an inherited dry-matter proxy, not observed grazing yields.

One unsplit herd demands 100 reference feed units ×6.25 kg DM/day. Those units
do **not** establish actual animal counts or nutritional adequacy. The herd
occupies one destination patch per bin. It may move along connected land
paths, with no diagonal water corner cuts, at an assumed 10 km/day level
speed modified by the inherited Tobler slope shape. Movement is limited to
two travel-days per bin. These are herd travel scenarios, not measured ancient
species speeds, and do not model flood/road/heat effects on livestock.

The herd can carry up to seven demand-days of feed, represented in one-day
increments. Transit meals use **previously carried feed first**; food at the
destination cannot feed an earlier part of the journey. Destination forage
then supplies meals and the next reserve. Current-bin production is drawn at
most once; unused production expires. Unvisited patches never contribute
remote food or a fictitious standing-forage bank. The start/end location **and
carried feed** must match. Shortages are diagnostics, not mortality.

This is a substantial assumed cargo allowance: seven days for this reference
herd is 4,375 kg DM. Pack animals, carts, collection/preservation work, water
carriage and their energetic costs are not solved. No real expedition or
complete pastoral carrying capacity is established by the result. Within-bin
plant growth, feeding and daily grazing orbits are not resolved; the model
accounts in twelve equal monthly resource bins.

Dynamic programming enumerates every allowed starting reserve and all location/
reserve transitions, finding the global minimum unmet DM **on this declared
finite state graph**, followed by travel and starting-reserve tie breaks.
This is not a claim about global optima of the climate calibration or of all
possible pastoral strategies. Coarser reserve states can discard usable food;
refinement checks quantify that approximation.

The optimizer has perfect knowledge of the recurring climatological year.
It does not establish adaptive success under unpredictable weather, drought
sequences, conflict or uncertain permission to use a resource patch.

Controls include:

- A fixed home under the **same discrete reserve states**.
- The best fixed patch anywhere in that same landscape, with continuous
  reserves. This allows relocation and can outperform the anchored circuit;
  gains against the arbitrary home alone do not establish a mobility advantage.
- A water-proximity sensitivity requiring each occupied **base** within 10 km
  of mapped water, compared with no resolved water exclusion. Intermediate
  travel watering, salinity, wells, seasonal permanence and potable volume
  remain unknown. If the fixed home is excluded, the circuit is unscored,
  not assigned a zero carrying capacity or declared impossible in reality.

Actual intermediate land paths are included for each move, avoiding straight
chords across intervening water. Inset letters identify resource patches;
the table gives seasonal order. They are not empirical camps. All four
experiments are **independent alternatives**, not simultaneous
herds sharing a landscape. Neither these nor fixed-home food support is added
to a human population or a polity's strength. Hunting/fishing/other nonstate
livelihoods remain separate existing scenarios; no universal nonstate model
is claimed.

## Reproducibility and interpretation

### First results

Sites fully supplied in all twelve bins under each declared scenario:

| Scenario | Free | Earth raw | Earth corrected | Whittaker |
|---|---:|---:|---:|---:|
| 100 people, 90-day store | 151 | 150 | 151 | 151 |
| 100 people, no destination store | 144 | 150 | 151 | 139 |
| Two-bin interruption, 90-day store | 151 | 150 | 151 | 148 |
| Two-bin interruption, no destination store | 0 | 0 | 0 | 0 |
| 500 people, same freight slots | 0 | 0 | 0 | 0 |
| 500 people, five times the freight slots | 125 | 134 | 135 | 129 |
| 100 people, alternative tied crop calendar | 151 | 150 | 151 | 151 |

These are tests of specified food/logistics budgets, **not empirical success
rates or observed garrison support**. The 500-person/same-freight case has an
explicit freight ceiling below its ration requirement, so no amount of extra
destination storage can make it annually adequate.

Earth-corrected herd annual dry-matter need met:

| Fixed resource landscape | Fixed home | Closed circuit | Best fixed base, continuous reserve |
|---|---:|---:|---:|
| Tarani resource landscape | 36.6% | 75.1% | 76.0% |
| Grassland outside named claims | 85.6% | 88.4% | 88.5% |
| Mixed resources outside named claims | 98.2% | 98.3% | 98.4% |
| Tribes of the Neck resource landscape | 84.8% | 96.2% | 96.2% |

Thus, gains against the arbitrary home **do not demonstrate that mobility
beats choosing the best fixed base** in these four small landscapes. Expanding
to independently chosen wider seasonal gradients is a future test, not a
positive conclusion smuggled into a nomad map. Halving carried-reserve steps
from one day to half a day improves need met by at most **0.137 percentage
points** in these four Earth-corrected circuits. This is a discretization check,
not an uncertainty interval for real livestock or human populations.

The independent review checked **50,736 site-bin ledgers** and **40 closed
circuits**, plus their actual intermediate paths. Maximum combined food-ledger
relative residual is below 4.1×10⁻¹¹. Analytical examples include exhaustive
route enumeration, no free cyclic feed, transit timing, protected rural meals,
calendar alternatives, origin/destination storage and imposed closures.

### Public data

Public `presence_mobility.json` pins matching Harvest identity, compressed
ledger/graph payloads, collection grid and images. `presence_mobility.json.gz`
contains scenario budgets, site stocks and arrivals, rural/freight/site
balances, patch production, adjacency graphs and closed routes. The catchment
grid is row-major little-endian uint16: 0 unassigned, otherwise site index+1.
The climate-specific payload supplies the shape and cell size.

`scripts/build_presence_mobility.py` records source/input hashes and reuses only
matching complete packets. `scripts/review_presence_mobility.py` independently
checks public ledgers and route budgets and refines the reserve states.
`scripts/check_presence_mobility_browser.py` checks visible values and exports
against those public packets. The analytical tests include an exhaustive
enumeration of all closed zero-pack routes on a small two-patch example.

Published results are conditional mechanism tests, not political or demographic
accuracy scores. Especially important: a small resident group can be easy to
feed under generous farming, collection and origin-storage assumptions. That
does not make those assumptions observed or turn food into political power.
Next refinements should test actual cropping/clearing labour, poorer origin
stores, shared competing users, animal nutrition, watering and known camps,
then staffing and institutional access—with evidence kept separate from
scenario assumptions.
