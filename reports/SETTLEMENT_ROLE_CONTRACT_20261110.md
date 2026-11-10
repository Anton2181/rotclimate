# Settlement roles: evidence units before hierarchy fitting

S2 preparation,10November2026. This defines the next data/consumer contract; it
does not implement or validate a village-population or political-control model.
S1's history, transfer and coupled-integration gaps remain open on the
[full roadmap](SETTLEMENT_CONTROL_ROADMAP_20261110.md).

The [Roman rural archive](https://doi.org/10.5284/1030449) supplies useful
role/chronology metadata. Its published introduction distinguishes roughly3600
excavation records from roughly2500 settlements. Before the preparation protocol
was frozen, only schema/role lookups were inspected; the later observation-table
audit is linked below and has not computed model scores. Schema/lookup hashes
and exact source URLs are retained with the
[preparation protocol](../calibration/roman_rural_preparation_20261110/plan.json).

## Four units must remain distinct

|Unit|Meaning|How it feeds the model|
|---|---|---|
|Source record|An investigation or catalogue observation|Evidence with its own provenance/coverage, not another resident population or garrison|
|Physical settlement|A place, potentially represented by several records|Allocate residents and service catchments once; grouping needs documented evidence|
|Dated function|A residential, commercial, religious, industrial or military role over an interval|Roles can coexist; missing dates/functions remain unknown|
|Institution/actor link|An attributed, staffed and supported organisation|Eligible input to differentiated control; not inferred merely from an occupied place|

A repeat excavation or additional role row must not create another town, population
allocation or political source. No nearest-point merge substitutes for documented
identity. Shared project identifiers may join fieldwork, rather than physical
settlements; their namespaces must be audited before grouping.

## What the inspected source schema establishes

* Core `ID` identifies a project record. `AREA` is investigated area in hectares;
  it must not become a complete settlement footprint or population estimate.
* `X_REF`/`Y_REF` are text OSGB eastings/northings, not latitude/longitude. Keep
  precision/format information until a documented coordinate transform is needed.
* Site `DATE_START`/`DATE_END` use negative BC values. Interval compatibility with
  AD200 does not prove precise or uninterrupted occupation. Missing is unknown.
* `SETTLEMENT_SIZE` is a separate estimated-size wordlist. Source classifications,
  domestic evidence and building counts have observation/coverage limits.
* Major/minor role tables reference site records and permit multiple categories.
  Metadata names farms, villas, villages, small towns, forts, route features and
  religious/industrial sites; the source does not make them interchangeable.

The metadata schema and lookups were initially read through the archive's exact published
encoded download links. Guessed unencoded URLs returned403, so those failures
should not be mistaken for evidence that the public CSV archive is unavailable.
At that initial checkpoint no raw site table was acquired. The subsequent
[frozen preparation audit](ROMAN_RURAL_PREPARATION_20261110.md) now reports3652
joined records, multiple roles and schema differences, without model scores.
In particular the export's MAP fields are not automatically equated with the
documented OSGB fields, and site occupation dates do not date every function.

## Settlement and control consumers

Residential evidence should constrain the future rural/village/town distribution
and shared resident allocation. Markets/ports should inform service and transport
demand when their roles are supported. Administrative/military/religious roles
may constrain different institutional scenarios; a villa, road or occupied village
does not automatically become an imperial authority source.

Actor affiliation, staffing and supply remain separate from role and physical
presence. An unattributed settlement is not empty or ungoverned; this contract
must work for other polities and nonstate communities as well as the Empire.
Institutional residents, civilians and rural producers must share the same people
and food ledger, with overlapping roles never counted as extra capacities.

For the fantasy-map inputs, icon diameter is not observed built-up area. A legion's
founding number identifies it; it is not a troop count. Marked administrative
relationships remain worldbuilding evidence/scenarios, not Earth calibration truth.

## Next concrete work

The initial preparation-only audit is complete. Resolve physical-place grouping,
exported MAP fields, phase/role timing and taxonomy differences, then declare
role-appropriate calibration units and splits; repeated observations
of one settlement must not leak between fitting and evaluation. Do not evaluate
the county-seat model against every excavated farmstead as though they were the
same target. S1 transfer qualification and the S1e shared-ledger/control rebuild
remain required before changing production maps.

Source: Allen and colleagues2015(updated2018), University of Reading/Cotswold
Archaeology/Archaeology Data Service; Leverhulme Trust and Historic England
support. [Archive introduction](https://archaeologydataservice.ac.uk/archives/view/romangl/),
[download metadata](https://archaeologydataservice.ac.uk/archives/view/romangl/downloads.cfm),
[ADS terms](https://archaeologydataservice.ac.uk/about/policies/use-access-to-data/ads-terms-of-use-and-access/).
This model's interpretations are our own; the original collectors are not
responsible for them. Raw archival tables are not redistributed here.

## Executable observation contract

The [role compiler](ROMAN_RURAL_ROLES_20261110.md) implements deduplicated context
channels, explicit unknown labels, site-span states, censoring flags and exact-
association blocking. Every compiled role remains undated and its physical place
unresolved. It supplies no population, staffing or affiliation. Blocking components
are validation constraints, not physical-place IDs or automatically independent
folds. The downstream allocation/control work above remains required.
