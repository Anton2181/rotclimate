# Rural Britain: role-aware observations and validation blocks

10 November 2026. **An executable evidence layer for S2, without fitting, new
population estimates or changes to the settlement/control maps.** This follows
the [frozen initial preparation](ROMAN_RURAL_PREPARATION_20261110.md); that audit
and both numerical settlement experiments are preserved unchanged.

Source: Allen and colleagues (2018), *The Rural Settlement of Roman Britain: an
online resource*, University of Reading/Cotswold Archaeology/Archaeology Data
Service, [doi:10.5284/1030449](https://doi.org/10.5284/1030449). Source collectors
are not responsible for this model's interpretation. Raw observations and cached
web pages are not redistributed; aggregate diagnostics, explicit interpretations,
source URLs and local content hashes are public. These hashes are not independent
archive checksums.

## What is implemented

`polity/role_evidence.py` separates source records, evidence channels, site-span
compatibility, undated functions and unresolved physical places. The rural adapter
`scripts/prepare_roman_rural_roles.py` joins the five pinned tables and compiles
channels once per source record, preserving simultaneous functions. No channel
allocates people, food, staff, actor affiliation or authority. Unknown labels remain
explicit; missing/negative domestic evidence is not regional absence.

The explicit [crosswalk](../calibration/roman_rural_roles_20261110/crosswalk.json)
is a declared interpretation of source categories, **not a calibrated hierarchy**.
Residential context includes farms/villas/villages; domestic occupation is a
separate observed field. Transport context does not prove freight capacity or
market activity. A villa is not an administrator, a hillfort is not a staffed
garrison, and ritual/funerary evidence does not establish an institution or actor.
Broad rural-settlement categories, morphology and specific functions remain
separate overlapping channels.

|Evidence channel|Records, all dates|Site span compatible with AD 200|
|---|---:|---:|
|Domestic occupation recorded|2637|2023|
|Residential context|2711|2082|
|Nucleated settlement context|550|470|
|Agricultural context|2595|1933|
|Military context|133|102|
|Transport context|169|147|
|Production context|774|572|
|Ritual/funerary context|765|564|

The complete aggregate audit includes three additional broad/morphology channels.
3002 of 3652 records contribute to multiple channels. **Do not sum these columns
as physical settlements, inhabitants, institutions or active AD 200 roles.** Every
role's specific dates remain unknown in this compiler.

## Source-backed taxonomy and chronology

The official [advanced search](https://archaeologydataservice.ac.uk/archives/view/romangl/query.cfm?queryType=structured)
lists `roadside settlement` and `jetty`, resolving the356 observations absent from
the minor CSV lookup. All observed nonempty source labels now have explicit context
mappings; no unknown label is silently dropped. This resolves a lookup discrepancy,
not the meaning, size, date or political affiliation of a physical place.

The same source's date-range help states:

> Start date: Date of commencement of activity within the excavated area. Note
> that sites beginning in the middle Iron Age or earlier will show as ‘-100’.

> End date: Date of cessation of activity. Note that an end date of 400 is given
> when sites are described as ‘continuing until the end of the Roman period’.

> Please note, that these dates apply to the settlement phasing, not individual
> features.

628 records use the −100 start convention and 1295 use the 400 end convention.
The compiler flags these separately; it does not fit exact foundation/abandonment
years to them. Site states are 2641 span-compatible, 892 outside the recorded span,
117 unknown and 2 ambiguous zero endpoints. Outside a recorded span does not prove
regional absence. Extra `PHASE_DATE1`/`PHASE_DATE2` are present in 1041/382 records;
their semantics remain unresolved and they are not used to date functions.
The [semantic receipt](../calibration/roman_rural_roles_20261110/semantic_sources.json)
records source URLs, exact source-help excerpts and cached-content identities.

## Related records must not leak across future folds

The compiler builds transitive blocking components from exact source association
keys `(TYPE, HER_NAME, DESCR)`. It strips surrounding whitespace but does not
case-fold, fuzzy-match or conflate namespaces. Empty descriptions are not keys;
references to missing source records fail explicitly. Shared project/event IDs
can connect multiple actual places, so these are conservative validation blocks,
**not physical-settlement merges**.

There are 3564 components: 3499 singletons and 65 nontrivial components involving 153
records; the largest contains 8. All exact association keys stay within one
component. No validation folds or model scores have been assigned. These links
only remove 88 independent record units, far short of resolving the archive's
published distinction between roughly 3600 records and 2500 settlements. Singleton
records are not thereby independent; missing identifiers, repeated places and
spatially correlated excavation selection remain unresolved.

## Coordinate investigation and remaining calibration gates

The official [map client](https://archaeologydataservice.ac.uk/archives/view/romangl/map.html)
uses EPSG:3857, displays EPSG:4326 and loads an EPSG:27700 definition. It requests
WMS layers rather than directly consuming the exported CSV coordinate fields.
**A client CRS does not identify the native CSV CRS or positional accuracy.** No
CSV MAP-field transform or target map is made. A read-only one-record search
returned HTTP500 and a WFS schema request returned404; these failures do not prove
that the entire archive is unavailable. Coordinates/precision and actual place
grouping remain open rather than being guessed.

Next, resolve place identities, source coordinate precision and function timing;
declare role-specific targets, survey/coverage treatment and grouped spatial
splits before scoring. Retain evidence-only records when these gates cannot be
met. Farm/village observations must not be treated as county seats. Residential
and institutional roles must subsequently enter the **same** resident/food/
staffing ledger and differentiated control consumers, as required by the
[role contract](SETTLEMENT_ROLE_CONTRACT_20261110.md). New source-context channels
alone do not qualify the production model.

This source is selected excavated Britain overlapping the Roman development
geography. It is not a complete census, new sealed validation, or an independent
global-transfer result. All [S1–S5 steps](SETTLEMENT_CONTROL_ROADMAP_20261110.md),
including occupation history, credible transfer and coupled integration, remain.

Reproduce: `.venv/bin/python -I scripts/prepare_roman_rural_roles.py`.
The adapter needs the five pinned observation CSVs in the local source cache;
it verifies their previous snapshot hashes and the current metadata/crosswalk/
code identities. Metadata can be reacquired from the pinned official URLs;
changed content is rejected for review. Public output is aggregate only.

Verification: 64 focused tests pass, including multi-role deduplication, explicit
unknowns, censored/zero/missing dates, transitive blocking, namespace separation,
order invariance and orphan rejection. A fresh-output replay is byte-exact. The
initial preparation audit and all four numerical settlement artifacts remain
byte-exact against7835271d. Served browser checks pass for nested keyboard access,
11 role channels,11 aggregate/document downloads, light/dark mobile layouts,
existing evidence filters and download/failure handling. The standard launcher
verifies the refreshed release; full ZIP/site copies are not rebuilt under quota.

Focused Windows-style checkout preserves 37 critical files byte for byte; all
638 local dependencies of the evidence page resolve. Receipts are retained in
`output/roman_rural_roles_20261110/`.

Coordinate follow-up: the [declared named-site check](ROMAN_RURAL_COORDINATES_20261110.md)
supports operational OSGB-compatible X=easting/Y=northing in metres. All eight
references across six sites lie within188m; this is not whole-source survey
accuracy or official export-CRS certification. Physical places, precision, extra
phases and coverage still constrain role calibration. Earlier audit artifacts
remain unchanged.

The [11 November methodology audit](SETTLEMENT_PHASE_EVIDENCE_20261111.md)
clarifies that major change dates and multiple labels can describe successive
roles. Earlier wording about preserving simultaneous functions should not be
read as evidence of contemporaneity. All source observations remain distinct;
new exact-point/name validation blocks are not physical-place merges.
