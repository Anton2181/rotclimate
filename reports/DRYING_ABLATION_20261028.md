# Legacy drying and explicit vertical transport — 28 October 2026

Prospectively declared only after the completed, independently verified and
committed wind-interaction study produced no validation shortlist. Its
outcomes remain unchanged. No adopted Earth or world climate is replaced.

The independently solved lower/upper water model transports donor humidity
with continuity-derived vertical dry-air exchange. Separate legacy closures
still remove water from the whole column under subtropical subsidence and
monsoon-driven descent. Whether these represent unresolved transport or
partly overlap the explicit exchange is a physical hypothesis. Large removal
terms alone cannot establish overlap or predict a sink-off climate response.

The literal frozen plan calibration/drying_ablation_20261028/plan.json selects
two separated admissible parent settings using the same objective order and
normalized-distance rule: global01 and global07, both at 4.5 m/s background
westerly amplitude. At each setting run three fixed ablations: zero only
subsidence_drying, zero only monsoon_descent, and zero both. Retained values
are 0.019548865912820436 and 0.015443602894513648 respectively. Parent anchors
with both retained are archived comparisons and add no integrations.

Four exact controls precede six candidates, each on the same seven reused
regions: at most 70 actual new integrations. No local proposals follow. Keep
conservative horizontal and donor vertical transport, independently solved
water, the corrected rainfall/recycling laws, all remaining actual model
parameters and all planetary properties unchanged at each paired anchor.

The parent prediction objective, normalization scales, research shortlist and
hard source/reference/numerical/conservation/branch checks are unchanged.
Improved prediction can support further evaluation but does not by itself
prove that the closure was redundant. Worse predictions also cannot establish
that an empirical water sink correctly represents its claimed physical cause.
This is a small paired structural ablation, not global optimization or
independent validation. Any shortlist needs separately frozen broader Earth,
resolution, ocean and world checks before adoption.

Status: complete; source `745cea2`. All 70 actual integrations pass strict numerics; no validation shortlist or adoption.

## Completed ablations

| Trial | Parent | Closure removed | Objective | Mean rain / r39 | Mean T / r39 | Worst combined / r39 |
|---|---|---|---:|---:|---:|---:|
| global01 | global01 | subsidence_off | 1.15122 | 1.08447 | 1.05376 | 1.30891 |
| global02 | global01 | monsoon_off | 1.13253 | 1.07529 | 1.04347 | 1.28107 |
| global03 | global01 | both_off | 1.16818 | 1.10791 | 1.06445 | 1.31476 |
| global04 | global07 | subsidence_off | 1.16693 | 1.12890 | 1.07765 | 1.42766 |
| global05 | global07 | monsoon_off | 1.13987 | 1.10555 | 1.06310 | 1.36557 |
| global06 | global07 | both_off | 1.19115 | 1.16429 | 1.09019 | 1.43034 |

Every ablation worsens the penalized objective and mean rainfall-error ratio
against its retained parent. Best among the ablations is global02 (monsoon
drying off at wind-study global01), F1.13253 versus parent1.12568 and mean
rain ratio1.07529 versus1.06867. No candidate reaches the research shortlist.

Removing subsidence drying at the first anchor increases North India from
278 to325mm/year (761observed), but increases PNW from1191to1273mm/year
(897observed), and worsens the overall objective. Removing monsoon drying
raises North India to300mm/year while keeping PNW near1193mm/year. Both
removals together perform worse still. These results argue against simple
closure deletion as an accuracy improvement. They do not independently prove
that the old sink correctly represents unresolved atmospheric processes.

All28 archived main controls and4 native companions reproduce exactly. The
independent verifier checks422 frozen sources, every actual case/parameter
identity, raw row/array hashes, step conservation/numerical/branch certificates,
literal paired grid and recomputed objective. Series counters: **1557actual
attempts /1553passes /four preserved historical failures**. This round adds
70passes and no numerical failure. No full/fine/established/world stage ran.

Six figures and full compact metrics are published in the companion: paired
ablation effects, all regional errors, ranking sensitivity, signed water
balances, full-score rainfall seasons and native humidity seasons. The two
preceding studies also receive the native humidity appendix and corrected
southern calendar labels. Model arrays, scoring weights and past outcomes
remain unchanged. Normal climate, foraging, agricultural and population
packets remain untouched.

## Preserved declaration metadata discrepancy

Initial scientific verification stopped with KeyError subsidence_drying while
replaying anchor selection. The original generator selected the two anchors
in the parent's four-axis space, then mutated a nested bounds dictionary
shared with its saved selection-description object. The saved description
therefore incorrectly includes the two subsequently added drying axes.

The original declaration, identity, generator hash, literal six candidate
parameter sets, anchor IDs, parent archives and initial verifier failure are
preserved. Every actual trial was explicitly fixed before integrations.
Verification reconstructs the already executed selection in the committed
four-axis parent space, checks that it yields the original global01/global07
anchors, then checks all six literal trials and their source hashes. It also
recognizes only this exact two-axis metadata extension. No new anchor, trial,
criterion, parameter, score or climate integration is introduced by the fix.

The scientific receipt and published JSON carry declaration_metadata_issues;
the initial failure is recorded separately. The future generator now copies
the nested selection data independently. Two regression checks cover this
aliasing error and rejection of an uncommitted parent; all10 focused checks
pass. This metadata discrepancy is not counted as a numerical climate failure.

## Next work

The wind result remains at its lower declared boundary; the ablations probe
only fixed endpoints at two rain settings. Neither study establishes a local
or global optimum. A separately declared joint space-filling search can test
wind/rain/drying interactions continuously, with native circulation and
humidity errors retained. Planetary properties and all other actual parameters
must stay fixed. Any proposed physical correction still needs direct process
evidence, not an improved aggregate score alone.
