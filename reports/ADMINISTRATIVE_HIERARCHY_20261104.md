# Recorded administrative communication — 4 November 2026

**Administration → Administrative links** adds six views to the normal Free,
Earth and Whittaker atlases, with matching raw/corrected Earth packets. They
show recorded commandery seats linked to provincial capitals, and provincial
capitals to the imperial capital. Map lines are schematic relationships, not
travel routes; coloured dots describe seats, not their surrounding territory.
The existing de facto control, population and climate exports are unchanged.

## Evidence and hierarchy

The previous [workbook-backed inventory](IMPERIAL_ACCESS_20261104.md) identifies
72 commanderies, 70 verified seats, 19 provincial-capital flags and one imperial
capital, Aēnaha. Stable IDs join the records. No nearest-city rule invents a
provincial assignment. The source game-era hierarchy is an explicit scenario,
not independently established history or a universal ancient administrative
structure. Kudā's inexact marker position and the Thalamâtâs/Pitané seat dispute
remain unresolved; neither gets a travel time or a budget score. Their known
provincial affiliations remain available in the inventory.

Nineteen of the 70 verified seats are their own provincial capitals. Their
local self-link is zero by definition; this says nothing about travel across
their commandery. There are 51 nontrivial local seat-to-province links. The
imperial capital also has a zero self-link. Aggregate imperial results exclude
that one trivial capital record and treat the other 69 seats equally; these
are not population-weighted statistics or area shares.

## Directed journeys and controlled transport alternatives

For each seat and each of twelve seasonal snapshots, retain four independently
directed shortest travel times:

1. Imperial capital → provincial capital.
2. Provincial capital → commandery seat.
3. Commandery seat → provincial capital.
4. Provincial capital → imperial capital.

Provincial reply time is legs 2+3. Imperial reply via province is all four legs.
This assumes communication passes through the recorded hierarchy; it is not a
claim that a direct courier would always do so. Outward and return paths can
differ because slopes, river flow and winds are directed. A provincial seat
does not require an extra local journey to itself.

Two cases keep exactly the same recorded hierarchy and source locations:

* **Marked interchanges:** existing painted roads/ferries; coastal/river
  interchange eligibility inferred at verified named settlement symbols;
  generated tracks omitted.
* **Proposed transport:** add the existing model's generated tracks and
  proposed-town coastal/river interchanges. Recorded interchanges are retained
  explicitly, so this is an addition rather than a replacement.

Interchange eligibility is not evidence of constructed harbours. Both cases
retain modelled density-dependent path friction, terrain, snow/mud/heat and
runoff effects. Thus the first case is not a fully observed infrastructure
reconstruction. Trips can cross painted political boundaries without extra
permission costs; allegiance, hostile obstruction and institutions are not
inferred from the map.

## Travel calculation and its limits

This audit uses an isolated additive person-travel graph. Existing walking,
river, transfer and sailing coefficients are reused. Parallel edges between
the same directed nodes select the shortest duration rather than adding the
costs of alternatives. The earlier freight audit documented that distinction;
legacy political/trade graphs are not silently replaced here.

Under the currently adopted sailing setting, sea edges use the existing
**beat-or-wait** duration. Unlike the older access map's fair-weather-spell
blending of two shortest-path totals, these edges define an additive route
metric. The calculation does not simulate correlated weather spells along a
voyage. Consequently its absolute times should not be treated as a pure
infrastructure comparison with the older access map; the two new transport
cases can be compared with one another.

All four legs hold the selected climatological model-month conditions fixed,
even if their sum exceeds a month. This is a seasonal travel comparison, not
an actual reply advancing through changing weather. No institutional processing
delay, courier relay, transport capacity, provisioning, social restriction or
political authority is modelled. The inherited sea-season penalty slows travel
rather than guaranteeing a complete sea closure. These are travel-only scenario
times, not observed ancient postal-service performance or guarantees of state
cohesion.

## Six map views and adjustable budgets

The view selector offers longest seasonal provincial reply time for either
transport case; longest imperial reply via province for either case; seasonal
range of imperial reply under marked interchanges; and days saved in the
worst-snapshot imperial reply by adding proposed transport. The worst snapshot
can occur in different bins between alternatives. Connectors have a white
casing for readability across water. Outer rings distinguish provincial seats.

Select a commandery in the panel or search for a recorded seat. Unresolved
seats remain selectable but show missing values rather than zero. The table
retains outward, return and imperial reply times for both cases in all twelve
bins. Selected-seat CSV includes all four directed legs; full CSV and NPZ
downloads cover every record. A capital's zero self-link is retained explicitly.

The **imperial reply budget** offers 7, 14, 30 or 60 days. These are declared
comparison scenarios, not literature-calibrated cutoffs for political control.
The readouts count snapshots within the budget and the longest consecutive
over-budget spell, including across the year boundary. Map colours remain
travel-day scales when the budget changes. Twelve equally weighted bins describe
climatology, not weather probabilities or the world's named civil months.
Commandery, budget, map view and climate mode are preserved in shareable URLs.

## Current results

Median of each noncapital seat's longest imperial reply across the twelve
snapshots, in travel days (69 equally weighted seats):

| Climate | Marked interchanges | Proposed transport |
|---|---:|---:|
| Free | 60.5 | 59.6 |
| Earth raw | 62.7 | 61.0 |
| Earth corrected | 62.7 | 61.6 |
| Whittaker | 61.8 | 60.0 |

All 69 noncapital seats have finite journeys in all snapshots under both cases.
This reflects the inherited transport rules and eligibility assumptions; it
does not establish that all routes operated historically. Many journeys remain
over the illustrative reply budgets.

The much smaller changes here, compared with the previous access map's large
gain from proposed towns, help separate two mechanisms: **adding physical
transport links** versus **declaring additional local authority sources**.
The earlier result should not be presented as the benefit of roads alone.
This new comparison does not independently validate the generated settlements
or the state's ability to staff, supply or command them.

## Literature and validation scope

Smith (2005), *Networks, Territories, and the Cartography of Ancient States*,
[doi:10.1111/j.1467-8306.2005.00489.x](https://doi.org/10.1111/j.1467-8306.2005.00489.x),
and Glatz (2009), *Empire as network*,
[doi:10.1016/j.jaa.2008.10.003](https://doi.org/10.1016/j.jaa.2008.10.003),
motivate distinguishing networks from uniformly controlled territories.
Evans & Rivers (2017), *Was Thebes Necessary? Contingency in Spatial Modeling*,
[doi:10.3389/fdigh.2017.00008](https://doi.org/10.3389/fdigh.2017.00008),
motivates exposing sensitivity rather than presenting one layout as inevitable.
The project's existing transport work draws on
[ORBIS](https://history.stanford.edu/publications/orbis-stanford-geospatial-network-model-roman-world)
and its previously documented physical travel assumptions. These sources do
not validate this fictional hierarchy, the reply budgets, or imperial political
outcomes. See the [research proposals](CONTROL_SETTLEMENT_PROPOSALS_20261104.md)
for subsequent provisioning and settlement-budget work.

Analytical tests check asymmetric directed legs, reverse-graph queries,
parallel alternatives, source additions, self-links and unresolved parents.
The audit asserts that adding proposed transport never worsens any directed
leg. Browser checks compare CSV with NPZ, all four climates and six views,
budget counts, self-links, unresolved-seat handling, URL state, conditional
controls, downloads and mobile layout. Bad identity/data removes only the
hierarchy feature, leaving the older access and climate maps usable.

Reproduce with the scientific environment:

```text
python scripts/review_administrative_hierarchy.py
python scripts/publish_administrative_hierarchy.py
python scripts/refresh_atlas_pages.py
python scripts/build_fit_hub.py
```

Source/input hashes and resumable complete-packet receipts are under
`output/administrative_hierarchy_20261104/`. Complete packets are reused only
when source hashes, input hashes and numerical arrays still match. Normal
atlas serving requires no scientific environment or original workbooks.
