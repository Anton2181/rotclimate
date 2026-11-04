# Origin storage and wider seasonal resource circuits

This extends the [baseline food/circuit milestone](PRESENCE_MOBILITY_20261104.md)
from commit `b919802e`. All seven earlier provisioning cases, four local
resource experiments and their catchment grids retain their earlier values.
Climate, yields, existing population totals and ownership maps are unchanged.

The normal `.bat` atlases have the same two buttons:

- **Political reach → Sustained presence:** eleven provisioning scenarios,
  now including origin storage, collection and protected-rural-store tests.
- **Livelihoods → Seasonal circuits:** local and regional tests, nested
  candidate bases, actual land paths and stronger resource controls.

## Main findings

The earlier conclusion was conditional on small landscapes: none of the four
Earth-corrected local circuits beat its best fixed-base control. Wider extent
can expose seasonal complementarity without enlarging the grazing area at each
stop. It does so in the same grassland example under Free and Whittaker climates;
the anchored circuits still do not beat the stronger control in either Earth
climate. This is climate-model sensitivity, not an ethnographic classification.

### Grassland outside named claims: regional experiment

| Climate | Best fixed base, all connected land | Sparse circuit | Additional-base circuit | Optimistic resource bound |
|---|---:|---:|---:|---:|
| Free | 82.74% | 88.48% | 88.60% | 89.24% |
| Earth raw | 88.42% | 86.73% | 86.73% | 89.63% |
| Earth corrected | 90.71% | 89.22% | 89.36% | 92.61% |
| Whittaker | 71.33% | 81.63% | 81.87% | 84.78% |

Values are fractions of the declared herd's annual dry-matter need met.
The resource bound removes travel constraints and is **not** a feasible route.
Water access is unresolved in this comparison. A positive mobility gain does
not establish an actual pastoral population, adequate nutrition, animal
survival, access rights, historical camps or political organization.

### Origin storage and food collection

Sites fully supplied in every bin of the 100-person food test:

| One changed assumption | Free | Earth raw | Earth corrected | Whittaker |
|---|---:|---:|---:|---:|
| Baseline: 365-day origin export store | 151 | 150 | 151 | 151 |
| Export store reduced to 90 flow-days | 124 | 131 | 131 | 127 |
| No origin export store | 0 | 0 | 0 | 0 |
| Collect 1% instead of 10% of rural overflow | 96 | 91 | 92 | 90 |
| Protected rural store reduced to 180 demand-days | 0 | 0 | 0 | 0 |

The destination group, ration, destination storage, freight slots, calendar and
physical collection paths remain fixed. These are sensitivity results under
the **same prescribed dispatch policy**, not optimized trade capacities or
estimates of historical storage. The protected rural budget is a cereal-only
test: its 180-day case cannot bridge the single-harvest year, so no surplus is
exported from a cell with unmet rural needs. Other staples, animal foods,
exchange and alternative harvest calendars are omitted. This is not evidence
of actual rural famine or inability to support a real institution.

## Scholarly basis and limits of attribution

[Brottem, Turner, Butt & Singh (2014)](https://doi.org/10.1007/s10745-014-9640-1)
examines seasonal forage connectivity and key resource sites in four Mali
transhumance zones. Only its publisher abstract was accessible here. It
motivates testing connectivity between resource patches and keeping access
rights separate; no equations or institutional coefficients were copied.

[Turner & Schlecht (2019)](https://doi.org/10.1186/s13570-019-0150-z) distinguishes
daily grazing around a base from travel between bases. That distinction matters
for a scale test: enlarging the movement domain must not silently give each
base the forage of a much larger daily grazing orbit. The new radii and lattice
spacing are **declared numerical experiments**, not fitted ancient distances.

The [FAO storage manual](https://www.fao.org/4/t1838e/t1838e19.htm) separates
short receipt periods, longer dispatch schedules and storage requirements. It
also discusses the dependence of deterioration on grain and store conditions.
The 90/180/365-day capacities and 5% annual stored-energy decay remain scenario
assumptions; no universal ancient storage rate is claimed.

Source access and the study protocol are recorded in
[`research_notes/presence_mobility_scale_20261104.json`](../research_notes/presence_mobility_scale_20261104.json).
The [model configuration](../data/presence_mobility_model.json) contains every
changed budget. This study does not rank biomes by social development or infer
tribal/nonstate institutions from climate.

## Regional experiment

Use the same four previously declared anchors: Tarani, grassland outside named
claims, mixed resources outside named claims, and the Tribes of the Neck.
No anchor was moved or selected using new mobility results.

### Hold these inputs fixed

- One unsplit herd: 100 dry-matter reference units ×6.25 kg/unit/day.
- One fine analysis cell as the grazing patch; land fractions remain explicit.
- The same seasonal forage proxy, crop-area exclusion and annual productivity.
- Seven demand-days of carried feed, represented in one-day increments.
- Two travel-days per bin, reference level speed 10 km/day and the same slope
  response. The reference year has twelve equal bins totalling 365 days.
- Feed for transit comes from the reserve carried before departure. A path
  cannot consume a future destination harvest or draw food from skipped cells.
- Both location and feed reserve repeat. The fixed home is visited at the
  declared year boundary; home phase is not optimized or observed.

The old local disk has radius five analysis cells, about 18.4 km. The regional
disk has radius twenty cells, about 73.6 km. These are two physical extents and
three selectable **landscape tests**, not three different physical radii.

### Ground paths and candidate bases

First construct the fine land graph over the larger disk, excluding water and
diagonal cuts across water corners. Retain the component connected to the
fixed home. Travel may use any node in that graph. No boats, ferries, roads,
new livestock heat/mud response or water-supply network is added here.

Retain every reachable candidate from the original local disk. Then add outer
bases on a lattice relative to the unchanged home. The sparse outer lattice
uses every fourth fine cell along each coordinate. The additional-base lattice
retains all of those bases and adds the diagonal offset (2,2). Each candidate
still supplies only its own fine-cell production. Transit land is not pooled
into a candidate's food budget.

The grassland and Neck examples use 157/233 candidate bases on the same
1,257-node ground graph at the regional extent; the Tarani example has 70/107
bases on 608 connected cells. The mixed-resource anchor lies on a small connected
island: only 13 fine cells remain. Increasing the geographical search disk
cannot create an overland route off an island.

Every reachable local base belongs to both regional tests, and the sparse
outer set is a subset of the additional outer set. With identical budgets,
enlarging either extent or the base sample cannot worsen the optimizer's best
feeding result. The independent review enforces both comparisons. Sampling
uncertainty remains: these are not every possible real camp location.

### Stronger controls

1. **Fixed home:** the same location and discrete reserve states as the mobile
   circuit. Movement never removes this option.
2. **Best fixed base:** examine **every home-connected fine cell**, including
   cells that were not sampled as candidate mobile bases. Continuous reserves
   make this a deliberately strong control. It permits free initial relocation;
   it does not require travel back to the arbitrary home anchor.
3. **Optimistic resource bound:** select the largest single fine-patch fresh
   forage supply in each bin anywhere on connected land, ignoring travel and
   with a continuous seven-day reserve. This is an upper bound on the tested
   circuits, not a route, simultaneous use of all patches or an actual herd.

Thus the broader experiment cannot manufacture a positive result merely by
omitting a superior fixed base from the movement lattice. All circuits must
remain below the resource bound; both stronger controls are identical between
the nested base samples.

The mapped-water sensitivity still gates occupied bases by mean distance to
mapped water. If the unchanged home is excluded, the circuit is **unscored**.
Wells, water permanence, salinity, potable volume, enroute watering, tenure and
permission remain unresolved. In the viewer, the main circuit map now changes
with the selected water case as well as the landscape test. The inset and CSV
use the same selected case. Pale transit land is not a map of unoccupied people.

## Provisioning sensitivities

The original equations and seven scenarios remain as documented in the
[baseline report](PRESENCE_MOBILITY_20261104.md). Four new cases change one
assumption at a time:

1. Origin export stores hold 90 rather than 365 days of annual export flow.
2. Origin export stores have zero capacity.
3. One rather than ten percent of protected rural overflow is offered for
   collection. This is not a measured tax rate or evidence of coercion.
4. Rural stores hold 180 rather than 365 demand-days; exports are blocked in
   every cell whose full repeating rural year has any unmet food requirement.

All scenarios retain finite freight slots allocated between the same fixed
cells by annual exportable flow. Blocked slots are not reassigned, and the
allocator does not maximize town food support. In particular, removing origin
stores does not test every possible harvest-season dispatch policy. It tests
storage dependence of the current policy. Destination reserves cannot replace
grain that never arrives under that policy.

`RuralFood.exportable` now centralizes the annual rural protection rule. Its
analytical test includes a harvest glut with future rural deficits, which must
not become city exports. Rural, origin, transport and destination ledgers close
separately and jointly; no food or carrying capacity is added to population or
political strength.

## Validation and data

`scripts/build_presence_mobility.py` publishes the four matching climate
packets and records source/input hashes in `output/presence_mobility_scale_20261104`.
`harvest/mobility_landscape.py` constructs the connected ground and nested
bases; `scripts/regional_resource_circuits.py` runs the wider experiments.

The existing gzip payload gains `mobility_scales`. Each regional example
contains all fine ground nodes and their monthly production, directed ground
edges, candidate-to-ground indices, controls, and actual fine-node path
segments. A route's `locations` index candidate patches, while its `segments`
index fine ground nodes. The original local schema stays intact.

The independent review checks 79,728 site-bin food records, 120 closed
herd/control circuits, actual intermediate paths, rural protection, the
resource bounds and the nested base sets. It also verifies that all earlier
seven food scenarios, their balances, the original local circuits and the
collection grid match the baseline commit. Refining reserve states from one
day to half a day checks both local and additional-base Earth-corrected cases.

The browser exposes the landscape test in shareable URL state and CSVs, keeps
irrelevant settlement controls hidden, and uses readable path/patch markers at
both extents. Its inset defaults to route detail, with a **Show whole tested
landscape** toggle; framing is saved as `pm_frame` in the shareable URL. This
changes only the view, never the ground domain, bases, optimization or ledgers.
The inset keeps at least eight fine-cell widths of context around compact routes.
All choices, water exclusions and optional-packet failure paths
are checked against the public ledgers. Windows checkout and portable bundle
checks remain part of publication.

These are perfect-foresight tests of a repeating mean year. They do not include
unpredictable droughts, standing-forage quality, human labour or diet, actual
livestock carrying costs, grazing competitors, institutional rights or camp
evidence. Wider movement is therefore a physical resource hypothesis to test,
not an automatic nomad or territorial-control classification.
