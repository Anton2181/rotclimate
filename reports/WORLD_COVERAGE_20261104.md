# Worldwide source and seasonal coverage audit — 4 November 2026

**Political reach → Coverage audit** adds one button with six dynamic views
for all 18 mapped actors. Three source scenarios, an actor selector and
1/2/4-day per-leg budgets expose evidence gaps without assigning sovereignty.
All normal atlases are updated, including matching Earth raw/corrected packets.
The original de facto view remains available, with a link to this audit.
No existing climate, population or political-ownership export is replaced.

## Source evidence and uncertainty

The provisional game-world workbook and the owner's icon key link 141 of
151 verified marked sites to named actors. Ten verified sites have unresolved
or conflicting affiliations; Kudā additionally has an unverified symbol/position
and is not routed. These are map/game records, not independent historical
observations of control.

`data/polity_affiliation_aliases.json` records explicit source-name joins,
including River Cities/Bekoni and the source label Defiant Arǧos. It does not
resolve chronology, revolt status or institutional form. Imperial commandery
IDs, verified commandery-marker joins and explicitly imperial icons supply
provisional affiliation signals. Conflicting signals remain unresolved. A
generic white settlement symbol supplies no allegiance. Missing/OCR-unmatched
records are not silently repaired by a broad fuzzy match.

Each source record retains its signals, sheet row where available, status,
map coordinates and snapped travel-grid node. The published registry also
shows the painted claim for comparison. Linked affiliation is not overwritten
merely because its marker lies in a differently painted claim.

Three nested source hypotheses share the same transport calculation:

1. **Evidence-linked marked sites.** Only sites with a unique provisional
   affiliation in the above inventory.
2. **Add claim-assigned marked sites.** Unknown marked sites receive the
   actor suggested by the painted claim, solely as an explicit hypothesis.
3. **Add generated sites.** Add the existing proposed administrative/market
   sites, with their claim-based affiliations. These are not observed villages,
   camps or political institutions.

Road cells never emit authority in this audit. Legion positions are not added
as fixed political sources; founding numbers supply no manpower. All actors
use the same person-travel assumptions. Pastoral/mounted capability and mobile
camps are not inferred from a biome, name or feed-equivalent map.

The Avādāyā Tribes and Tribes of the Neck have no linked-site inventory here.
Their evidence-only access is **unscored**, not zero actual control, uninhabited
land or a reason to give their territory to a neighbour. In corrected Earth,
the expanded hypotheses create 28 and 62 source nodes respectively. The Neck
has four claim-assigned marked sites, while Avādāyā has none. Sparse inventories
also remain visible for every other polity. More documentary detail for the
Empire must not be mistaken for a measured advantage in actual state capacity.

Unknown marked sites are retained as a separate spatial evidence signal,
including when a claim-only hypothesis assigns them to an actor. That signal
is not an additional competing polity and does not draw local-autonomy borders.
Communities and institutions may also exist where no marker was recorded.

## Same-site directional and seasonal test

Within each snapshot and per-leg budget B, a cell qualifies only if there is
at least one source A satisfying both:

```text
shortest directed trip A → cell ≤ B
shortest directed trip cell → A ≤ B
```

Both legs must use the **same source**. Taking the nearest outward source and
an independently nearest return source can fabricate a reversible journey.
A synthetic directed-graph test demonstrates and rejects that error. Journeys
ending at another coordinated centre could be legitimate under additional
institutional assumptions, but are not counted by this particular test.

Source sites are assumed available as journey origins in every snapshot;
occupation, staffing and provisioning are not established. Locations are fixed.
A different source can qualify in a different
season; in the aggregate view even the qualifying actor can change between
bins. Twelve bins of aggregate access therefore do not establish a single
persistent authority or a permanently operating base.

Three per-leg budgets (1, 2 and 4 days) are comparison scenarios. No new
administrative cutoff is calibrated or adopted. Dijkstra searches truncated
at four days preserve all three threshold tests exactly. Outward-only access
is also retained. Source additions cannot reduce coverage, and same-site
two-way coverage cannot exceed outward coverage; both are asserted per month.

Twelve equally weighted climatological snapshots hold conditions fixed during
both trips. They are not civil-calendar dates, weather probabilities or voyages
advancing through changing seasons. Each source hypothesis shares the current
central-density friction and transport, including proposed tracks/landings.
The first case is therefore not observed-only infrastructure.

The isolated additive graph reuses the hierarchy audit's person-travel costs,
beat-or-wait sailing and minimum parallel alternatives. It does not use the
old access map's whole-voyage fair-spell blend or its extra refuge/rank terms.
Absolute differences from the older de facto map cannot be attributed to source
changes alone. Comparisons *between the three new cases* hold the engine fixed.
No staffing, supply, political permission, conflict, tribute or state strength
is inferred. Historical negative results for strength multipliers still apply.

## Views and interpretation

* **Seasonal access:** bins with same-site two-way access.
* **Longest access gap:** longest cyclic absence of that access, including
  across the year boundary.
* **Overlapping reach:** bins where at least two represented actors qualify;
  with one actor selected, bins where that actor and another qualify.
* **Dependence on extra sources:** bins covered only by the expanded hypothesis.
  A selected actor with no evidence baseline stays unscored in this comparison.
* **Outward access without same-site return:** bins where a one-way trip would
  exaggerate the reversible-access footprint.
* **Unaffiliated marked sites:** two-way access from the unresolved marked-site
  pool, independently of the actor/source selectors. Irrelevant selectors hide.

These are access and evidence diagnostics. Overlap is not observed fighting;
no access is not absent communities or proof of autonomy; missing affiliation
does not identify a new polity. The older ownership map is a labelled scenario
for comparison, not independent validation.

## Current numerical comparison

Percent of the model's majority-land travel grid with all twelve bins of
two-way access from *some represented actor*, at two days per leg:

| Climate | Linked evidence | With claim-assigned sites | With generated sites |
|---|---:|---:|---:|
| Free | 9.0% | 9.5% | 52.3% |
| Earth raw | 8.6% | 9.2% | 46.6% |
| Earth corrected | 8.6% | 9.2% | 47.2% |
| Whittaker | 9.4% | 9.9% | 48.9% |

Corrected Earth's linked-site case has outward-without-return access in at
least one bin on about 2.9% of land. Overlap in at least one bin is about 0.11%
under linked evidence and 7.16% under expanded sources. All area summaries use
land-fraction weights inside the travel grid. They measure sensitivity, not
control accuracy or political probabilities. No polygon agreement score is
used to select a preferred hypothesis.

## Delivery and numerical format

The six views share one button. Actor/source/budget choices are URL state.
Point CSV includes all 18 actors under all three source cases (54 rows);
missing inventories have null scores, not zero. Source CSV/JSON keeps the
affiliation evidence available for review. Named coastal sites use their
recorded travel-grid node; arbitrary clicks retain the clicked analysis cell.

Full grids load lazily, only when the audit opens. A roughly 1 MB gzip packet
expands into a little-endian uint32 land lookup, packed coverage words and
unaffiliated-site words. A modern browser with DecompressionStream is needed
for this optional layer; other atlas features stay usable after failure.
The manifest gives dimensions, byte offsets, checksums and actor order.

Each uint32 word holds twelve two-bit threshold classes: 0 outside four days,
1 within four, 2 within two, 3 within one. Words are ordered
`[source case, actor, direction, land index]`; directions are outward then
same-site two-way. Lookup values are one-based land indices, zero for water.
The separate unknown-site array is `[direction, land index]`. Thresholded
monthly masks can be combined across actors; packed two-bit classes must not
be bitwise-ORed (1 OR 2 would spuriously become class3).

For an independent point reader, with NumPy installed:

```text
python scripts/read_coverage_grid.py atlases/earth_fit/data/coverage.json --climate corrected --row 200 --column 500 --budget 2
```

The ordinary launcher remains standard-library only. Source/input identity
checks, three-month checkpoints and complete-packet reuse are implemented in
`scripts/review_world_coverage.py`. Publication verifies the scientific inputs
before copying results; the browser verifies the actual loaded food/climate
and compressed data identities. Numerical and browser checks cover source
nesting, directionality, missing evidence, threshold packing, point exports,
state, controls and mismatch handling. Frozen climate/population/old ownership
exports are unchanged.

The motivation remains differentiated imperial/other political networks and
explicit settlement uncertainty, as reviewed in
[the literature proposals](CONTROL_SETTLEMENT_PROPOSALS_20261104.md). This
implements an access audit, not those authors' complete institutional models.
The [worldwide scope](WORLDWIDE_PROVISIONING_SCOPE_20261104.md) applies to
future source work, provisioning, mobile camps and nonstate institutions.
