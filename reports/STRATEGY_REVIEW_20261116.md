# Strategy review — 16 November 2026

Reviewed canonical checkpoint `5b0d03b19`, including the newer handoff and the
underlying settlement, forest, border and climate reports. The canonical and
`claude/wonderful-mayer-uqbwtb` branches pointed to that same commit; the other
remote continuation branch was older. This is a proposal, not a declaration of
new experiments or an adoption decision. No reserved observations were opened.

## Current state

Release 4 is published and hosted, including the settlement-road display fix
(hosted version 7). The confluence placement factor passed a prospective position
test. Counts are unchanged; placement, supply and affected reach/trade outputs
were rebuilt. The published chain uses the hierarchy size model and the 34%
marketed-share option. The whole-empire supply calibration including Egypt
passes on development evidence after the documented corrections; independent
end-to-end transfer is a separate question.

Earth climate r46 passed its declared development, finer-grid and sealed-set
checks. The fantasy climate atlas intentionally remains r44. The forest layer
uses the verified 0.51 level. Detailed woodland placement was discarded by the
owner. Forest travel is an opt-in, unpublished change; its earlier tests used
the 0.60 forest level. Basin cantons and river-crossing ownership changes were
not adopted.

The roadmap's previous “live” entry still described the 14 November water work,
release 3 and Egypt failure. Those are historical checkpoints, not the present
release status. The release-4 plan also contains completed or superseded work
packages beneath its original proposal. Future continuations should start from
the latest handoff, current chain spec and release receipts.

## Recommendation

Start with **settlement observation definitions and urban concentration**. Run
a small historical-occupancy pilot next, with road-network testing alongside
when suitable independent links are available. Keep global population history,
polity formation and another climate campaign outside the immediate release
dependency until their first discriminating tests are defined.

This differs from the handoff's proposed “population history first” ordering.
History is promising, but present evidence does not identify it as the common
cause of every remaining problem.

## Assessment of the six proposed directions

| Direction | Evidence and limitation | Recommended scope |
|---|---|---|
| Population history | Han's frontier allocation supports distinguishing occupancy from food capacity. The static core prior already helps. Forest clearing still fits zero after applying that prior; this does not establish that a demographic simulation will fix clearing. | A small age-of-occupation comparison against the existing core-distance rule before a global Neolithic-to-present model. |
| Cities and primacy | Two transfer exercises exposed size/density problems. Current town counts are not the archived dense-core count failure. The published size relation responds weakly to hinterland population. | First priority: separate observation semantics, urban allocation and the upper tail of city sizes. |
| Generated roads | Largely independent and has a direct observed-network comparison. The latest dangling-track issue was a display omission, not evidence that route generation failed. | Test connectivity, route lengths and cost-adjusted detours with observed links withheld from generation. |
| Where states form | Scientifically interesting, but political ownership and capacity do not establish state formation. Painted claims remain binding map inputs. | Defer; first identify dated formation/split outcomes and a useful null model. |
| Monsoons and rain shadows | r46 is a qualified improvement; further refits stalled. This suggests testing a different process, not assuming every remaining error shares one parameter cause. | Keep parked until a conservative transport/circulation prototype explains a specific seasonal error. Preserve sealed set l. |
| Herders and the steppe | Important for a world model that otherwise privileges permanent farming settlements. Existing forage and mobility work provides a foundation. | A bounded test of seasonal water/feed feasibility and observed mobility, with joint land/resource accounting. Check prior D-PLACE exposure first. |

## 1. Diagnose urban concentration before adding population history

Three findings should drive the next experiment:

- Southern Mesopotamia failed both location and size tests. Modern channels may
  miss ancient settlement corridors. That is a different failure from city size.
- Mexico's rural people comparison passed its broad gate while no model town
  fell in the surveyed area. The observed settlement areas imply about 18 people
  per hectare, compared with the Old World model's 100–500 reading. Teotihuacan
  is excluded from that rural survey. Those data cannot be treated as a complete
  urban population distribution.
- The 2–7× dense-core town excess belonged to the old production baseline.
  The published history-weighted tiling already substantially corrects it.
  Reopening the rejected count-exponent campaign would target the wrong model.

There is also a useful code-level clue. Released size coefficients are
`[1.91518036, 0.14703888, 0.8]`: ten times as many hinterland people changes
predicted area by only `10**0.14703888 ≈ 1.403` before the capital/selection and
scatter terms. Hinterlands are limited to 60 km, residual draws are clipped at
±2.5 standard deviations and area is bounded. The released area bound is about
1–1,783 ha: **there is no hard 200 ha ceiling**. Failing to generate cities above
200 ha is a result to explain, not a clamp to remove.

First deliverable: reproduce the relevant failures using the actual published
hierarchy/confluence configuration and document the Earth/fantasy differences
in known capitals, marked centres, density readings and survey boundaries.
Existing spent pools are appropriate for this development diagnostic. Report
missing city-count coverage and mismatched area definitions explicitly.

Then compare the existing independent area draws with a small joint allocation
model. Keep regional people totals, candidate positions and counts fixed in the
first comparison. Allocate a finite, evidence-constrained urban population among
centres, leaving the remainder rural. Test whether concentration and access to
food can support observed large centres without creating residents or food.
Role/market weights are hypotheses to test, not established urbanization laws.
The earlier port/river/road size regressions already failed to improve held-out
error. Repeating those flags is not a new direction; the proposed change is the
joint allocation and its finite population budget. A role-specific effect would
need appropriate new role evidence.

Score urban share only where the observation denominator is known, together
with largest-centre share, upper quantiles, rank-size pattern and ordinary-town
error. Retain population and food-ledger checks. Evaluate wall circuits,
inhabited areas and dispersed house-lot settlements with their appropriate
observation models; do not fit an arbitrary density to make each region pass.

**Stopping rule:** if the failure is mainly a survey/area-definition mismatch,
fix the comparison before changing population dynamics. If changing the size
allocation helps with regional totals fixed, global demographic history is not
a prerequisite for that improvement. Freeze numerical gates before future fits.

## 2. Make population history a falsifiable pilot

Compare capacity-only allocation, the existing core-distance prior, and one
source-supported occupation-age/arrival mechanism in a small region with useful
historical constraints. If totals are held fixed, this tests spatial allocation,
not demographic growth. Births, deaths, migration and changing totals require a
separate demographic ledger and evidence.

Farming arrival and state formation are different events. Older settlement need
not imply higher present population after collapse, abandonment or environmental
change. Begin with the simplest mechanism the data can distinguish; do not add
an entire succession of states merely to explain a static residual.

Use census or settlement evidence to test people. HYDE has already been used in
the project and its ancient spatial allocations are model-based: it is a
comparison/prior, not independent ground truth. Radiocarbon date density depends
on research and preservation as well as occupation. Pollen forest change is a
vegetation observation affected by farming, grazing, fuel use and climate; it is
not a direct population count.

**Stopping rule:** scale up only if the mechanism adds predictive skill beyond
the existing static prior on a defensible transfer design. A better fit to one
known forest slice is insufficient.

## 3. Test road generation as a network

Hold the declared settlement inputs and terrain fixed. Compare the generated
network to simple nearest-neighbour/minimum-connection and terrain-cost
baselines. Score connected important places, total road length, route detour,
redundancy and unnecessary branches, rather than just overlapping line pixels.
Ferries, bridges and road chronology need explicit treatment.

Itiner-e has already been used in Earth travel and site predictors. A new test
cannot feed its roads into the cost map or generator and then count their
reproduction as independent validation. Use declared geographic/link withholding
and retain an observed-town versus generated-town comparison to separate town
placement errors from route-generation errors. Check Han road-source coverage
before calling it a second independent benchmark.

**Stopping rule:** require improvement over a useful simple network under a
comparable construction-cost budget. If the generator only traces an input
network, it has not passed this test.

## Other directions worth preserving

**Separate the mechanisms of access and ownership.** The river experiments
suggest that transport reach and political assignment need not use the same
network. A river can support provisioning while failing to determine who owns
its opposite bank. This is a useful hypothesis for later institutional work.
However, high owner agreement given correctly polity-labelled towns is
conditional reconstruction, not prediction of sovereign boundaries. Straight-line
town ownership performs similarly. Any next test should emphasize contested
border corridors, boundary displacement and land deliberately left outside
the scoring domain, alongside area agreement. Do not relax failed past gates.

**Use historical channels to isolate the Mesopotamian location failure.** If
independent period channel/canal geometry can be obtained, compare modern and
historical waterways with everything else fixed. This can diagnose a reference
geometry mismatch before inventing another population prior. Do not derive the
waterways from the settlement coordinates being scored. Since FloodPlains has
been inspected, this is development work unless a distinct transfer pool exists.

**Improve the evaluation design before spending scarce pools.** Different dates
of the same cities, neighbouring forest slices and alternative reconstructions
of one underlying survey share information. New dates do not automatically make
a new independent test. Extend the existing usage register with source families,
feature/outcome exposure and spatial/time overlap. Keep Buringh's reserved size
use and climate set l unopened until an appropriate declared experiment.

## Suggested next sequence

1. Reconcile current release facts with older “live” planning entries. This review
   updates the handoff/roadmap status without choosing a research direction.
2. Freeze a short failure-diagnosis plan for the released settlement pipeline:
   area semantics, missing-city coverage, hierarchy labels and upper-tail limits.
3. If the diagnosis supports it, declare the fixed-total urban-allocation comparison.
4. Prepare a separate road-network benchmark without importing target edges.
5. Scope the historical-occupancy pilot from available independent evidence.

The next useful product is a before/after city-size and concentration comparison
with conserved residents and food, followed by a map change only if qualified.
It is not another unverified detail layer. S3–S5, mobile/nonstate communities,
complete diets/work and institutional evidence remain on the programme; this
ordering does not claim those problems are solved.

## Sources reviewed

- [Latest handoff](../HANDOFF.md), release-4 chain and publication records.
- [Release-4 plan and progress](SETTLEMENT_RELEASE4_PLAN_20261115.md).
- [Town-count diagnostic and correction](TOWN_COUNT_DENSITY_20261116.md).
- [Mesopotamian test](FLOODPLAINS_BLIND_20261115.md) and
  [Mexico test / density qualification](VALLEY_OF_MEXICO_BLIND_20261116.md).
- [Published hierarchy](SETTLEMENT_HIERARCHY_20261115.md),
  [size functions](../polity/settlement_sizes.py) and
  [released size metadata](../output/settlement_release4_20261116/earth_results.json).
- [Forest diagnosis](FOREST_DETAIL_20261116.md),
  [internal borders](INTERNAL_BORDERS_20261116.md),
  [river borders](RIVER_BORDERS_20261116.md), [forest travel](FOREST_TRAVEL_20261116.md).
- [r46 adoption](CLIMATE_R46_20261115.md),
  [Egypt-inclusive development calibration](GREEK_WALLS_20261114.md),
  [existing population-history comparison](ITERATION_LOCAL_20261023.md).
