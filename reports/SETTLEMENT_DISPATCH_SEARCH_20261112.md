# The resident grid missed narrow staffed ranges

The predeclared search check finds numerical misses in the 300-hour joint maps.
The 64-interval grid recovers ten staffed sources in each climate; probing the
existing 150-person staffing threshold finds five more raw-climate and two more
corrected-climate positives. These sites were not established physically
infeasible by the earlier 32-interval map. The original examined-allocation
results remain preserved, with their global-optimality limitation.

The [declaration](../calibration/settlement_dispatch_search_20261112/plan.json)
was committed in `d302ac74` before new outputs. It specified exactly four
open-bin, 120,000-kcal-load cases, 64 versus 32 intervals, unchanged 24 resident
and 40 dispatch refinements, and probes at `150 − 1e-6`, `150`, `150 + 1e-6`.
The 150-person transition is the existing 100 staff plus 50 civilians, not a
threshold fitted after these results.

|Climate|Farm hours|32-interval sources|64-interval sources|Additional positives at exactly 150|
|---|---:|---:|---:|---:|
|Raw|600|861|861|0|
|Raw|300|710|720|5|
|Corrected|600|889|889|0|
|Corrected|300|743|753|2|

All 396 overlapping source/feasibility/destination-shortfall arrays are bit
exact. At 600 hours, finer-grid total changes are below 0.0001 people and no
sources switch. At 300 hours, the finer grid adds 1,524.915899 modeled town
residents in raw climate and 1,529.178524 in corrected climate; the largest
individual changes are 153.836043 and 156.342930 people. Every site and each
probe's eligibility/feasibility remain in the numerical download.

An independent reviewer reconstructs all sixteen complete records (four finer
final allocations and twelve threshold probes): population transfers, remaining
field/reaping work, rural/export/destination monthly inventories, per-origin
integer trips, monthly collector hours and source support. The source-food gate
additionally passes all positive finer allocations. Fresh result and field
files are compared byte for byte. Earlier maps, packets and source hashes are
preserved. This is a numerical-search finding on development inputs, not a new
Earth test, resident census or calibrated control map.

The explicit next [threshold-seeded solver declaration](../calibration/settlement_dispatch_seeded_20261112/plan.json)
adds the known activation point to the 64-interval candidates, then refines its
feasible branch before publishing distinct corrected map versions. It does not
silently overwrite the original sixteen cases or claim that every other
feasible island has been found. Actual geographic patrol work, dated size/role
evidence, prospective transfer, complete diets/household/draft work and mobile
occupancy remain on the [full programme](SETTLEMENT_CONTROL_ROADMAP_20261110.md).
