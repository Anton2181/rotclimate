# Rural Britain: records, roles and chronology prepared

S2 preparation,10November2026. The protocol was committed at066db539 before
site/coordinate tables were downloaded. **No candidate fitting, prediction,
validation score, coordinate map, population estimate or control update.**

Source: Allen and colleagues2015(updated2018),
[The Rural Settlement of Roman Britain](https://doi.org/10.5284/1030449), University
of Reading/Cotswold Archaeology/Archaeology Data Service, with Leverhulme Trust
and Historic England support. Original collectors are not responsible for this
model's interpretation. Raw tables remain locally cached and are not redistributed.
Source URLs and locally recorded SHA256 hashes are retained; the archive did not
supply independent checksums for these files.

## Usable record-level joins and multiple roles

|Table/check|Result|
|---|---:|
|Core records / unique core IDs|3652 /3652|
|Site records / unique site IDs|3652 /3652|
|Core↔site IDs joined|3652|
|Unmatched core/site IDs|0|
|Major-role observations|4365|
|Records with multiple major roles|608|
|Minor-role observations|5970|
|Records with multiple minor roles|1549|
|Association references to missing core IDs|0|

All declared table primary keys are unique. Repeated foreign IDs in role tables
are expected, rather than duplicate settlements: one record can have several
functions. Seven repeated major-role labels and one repeated minor-role label
are separately reported, without creating additional people or authority sources.

Major-role lookups cover all nonempty observed labels. The minor lookup omits356
observations present in the data (principally roadside settlements); preserve
these as unmapped source labels pending explicit taxonomy work, not guessed
categories or discarded records.

Source categories include farms, villas, villages, small towns, forts, religious
sites, industry and route features. These are **record roles**, not a count of
independent physical settlements or dated political institutions. Shared heritage
and project identifiers exist, but grouping into unique places has not been
inferred. The published record/settlement distinction remains important.

## Dates and size do not identify a census

3535 records have two numeric occupation endpoints;117 lack one or both.2641
have an interval apparently compatible with AD200. These are interval-compatible
records, not proof of uninterrupted occupation or each role's activity in AD200.
Two records have a zero-valued endpoint, flagged rather than silently reinterpreted.

`AREA` has2987 positive values and665 missing/non-numeric values. It measures the
investigated/excavated area. The separate settlement-size wordlist is nonempty in
3646 records, including1466 marked uncertain; remaining labels are coarse size
bins. Neither field is converted into population, and source form/enclosure is
not automatically interpreted as fortification or state administration.

## Coordinate/schema work remains

The disseminated core table has `X_REF_MAP`/`Y_REF_MAP`, while the inspected DDL
describes `X_REF`/`Y_REF` OSGB text fields. All3652 exported MAP pairs are numeric,
but their units/precision are not assigned from their names or values. No automatic
alias, projection or target map is performed. The extra phase fields in the site
export also require their own interpretation. Record-level role/chronology work
can proceed; location/phase-specific calibration needs these schema details resolved.

## Parser correction and next steps

Initial automatic CSV detection inferred the wrong double-quote escaping rule.
Standard comma/Excel parsing yields zero nonconforming rows across all five tables;
the earlier apparent extra cells were a reader issue. The shared reader is corrected
and tested. [Vidarbha was rechecked](VIDARBHA_PREPARATION_20261110.md): its primary
join/axis problems persist, with the earlier parser-induced warning removed.

Next S2 work: resolve record↔place grouping, MAP coordinates, phase semantics and
taxonomy mismatches; declare role-appropriate calibration targets/splits before
scoring. Avoid fitting the county-seat generator to every farmstead or leaking
repeated observations of one place across folds. Then wire residential/market/
institutional roles through the shared people/food ledger and differentiated
control, as defined by the [role contract](SETTLEMENT_ROLE_CONTRACT_20261110.md).

Britain overlaps the old Roman development geography and the archive is selected
by excavation/reporting, so this is not automatically independent global transfer
or a complete settlement census. S1c/history, S1d/transfer, S1e/joint integration,
and S3–S5 remain on the [full roadmap](SETTLEMENT_CONTROL_ROADMAP_20261110.md).

Reproduce: `.venv/bin/python -I scripts/audit_roman_rural_preparation.py`.
`output/roman_rural_preparation_20261110/` retains source snapshot and aggregate
audit. Further use must preserve the archive's attribution and access terms.

Verification:52 focused tests pass, including CSV escaping, source keys, multiple
roles and date/coordinate handling. Preparation rerun in a fresh output directory
reproduces both source snapshot and audit byte for byte. Both numerical settlement
studies remain byte-exact against88ea2104. Served-atlas checks pass for the native
collapsed panel, keyboard opening, seven aggregate-only links, preserved adaptive
research and the existing evidence filters in light/dark mobile layouts. Focused
Windows-style checkout preserves26 critical files;634 local page dependencies
resolve, and the standard launcher verifies the refreshed release. Full portable
ZIP/full-site copies remain unbuilt under the disk quota; the packaging recipe
contains the new documents and metadata.

Follow-up: the [role compiler](ROMAN_RURAL_ROLES_20261110.md) resolves the missing
lookup labels through the official search, documents date censoring and builds
conservative association blocks. The initial audit above remains unchanged. CSV
MAP CRS/precision, actual physical places and extra phase semantics remain open.
