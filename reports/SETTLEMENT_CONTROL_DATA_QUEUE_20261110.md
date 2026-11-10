# Next Earth evidence for settlements and control

Metadata/schema review on10November2026, after the first count-separated
development experiment. This supports S1c/d, S2 and S4 of the
[full roadmap](SETTLEMENT_CONTROL_ROADMAP_20261110.md); it does not qualify or
replace any model. The repository's reports/calibrations/scripts/research notes
were searched for these identifiers, with no previous use found. That search
does not prove their observations are independent of every source already used.

At the initial metadata review no target tables were loaded. A subsequent frozen
[preparation-only audit](VIDARBHA_PREPARATION_20261110.md) loaded the Vidarbha master
and settlement CSVs, without predictions, maps or model scores. It found zero ID
joins and conflicting coordinate documentation, so this version is not ready for
located transfer. The Roman rural source has since completed a separate preparation-only audit, also without scores; crop/collection evidence remains metadata-only. None has sealed status.

## 1. Vidarbha: a non-Roman geographical transfer candidate

[Hawkes, Abbas, Casile, Lefrancq & Toraskar2020](https://doi.org/10.5281/zenodo.3667657),
*The Archaeology of Vidarbha, Maharashtra: A Census of Known Sites and Remains
(Megalithic to Medieval)*, CC BY4.0. Settlement, religious, coin, megalith and
other-site records are distinguished; the methods describe chronology, dating
basis, location accuracy and discovery/survey methods. The inspected readme and
its checksum/source receipt are retained in
`calibration/settlement_locations_20261110/data_queue/`.

This could assess settlement locations outside the existing Roman/Han development
geographies and support later settlement-role work. It is an inventory assembled
from archaeological literature, not a population or administrative census.
Before any score, audit joins/record counts, occupation-date ambiguity around
AD200, coordinate accuracy, discovery effort and coverage. Do not count coins,
burials or religious monuments as residential or administrative centres.

**Specific loader hazard:** the readme defines `YCoord` as longitude and `XCoord`
as latitude, opposite a common naming convention. A future loader must use the
documented definitions and verify the regional bounds, not infer axes from names.
The manifest's very small master-list file also warrants checking actual records
and join structure; metadata alone does not establish a usable site table.

Preparation audit now completed: the coordinate master and settlement table have
zero joins, and documented axes conflict with source values. Resolve the source
or choose another before freezing a role-appropriate located transfer comparison. Do not substitute raw known-site counts for total settlements
unless survey coverage supports that interpretation.

## 2. Roman Britain: rural settlements and settlement roles

[The Rural Settlement of Roman Britain](https://doi.org/10.5284/1030449),
Archaeology Data Service, with published Britannia monographs. The
[ADS project account](https://archaeologydataservice.ac.uk/blog/rural-settlement-of-roman-britain-salute/)
confirms downloadable CSVs and related finds/environmental evidence. It explicitly
describes a synthesis of excavated evidence, not a complete atlas of Roman sites.

Use principally for S2: distinguish farmsteads/villages and larger centres, with
chronology and available economic evidence. Archaeological recording effort must
be modelled or controlled when evaluating spatial density. Britain overlaps the
existing Roman training geography, and sites may overlap other catalogues; this
is not automatically an independent global transfer pool. It cannot validate
administrative-seat counts by treating every rural excavation as a seat. The [initial record-level preparation](ROMAN_RURAL_PREPARATION_20261110.md) is now complete under a frozen protocol; grouping, MAP/phase semantics and taxonomy still need resolution before calibration.

## 3. Roman crop collection: material evidence for the shared ledger

[Rob Wiseman, *Gathering the Harvest* research data](https://doi.org/10.17863/CAM.115666),
University of Cambridge; related article [doi:10.1111/ojoa.70007](https://doi.org/10.1111/ojoa.70007).
The source describes Latin references to crops/transport and phased
archaeobotanical data from87 excavations in Cambridgeshire/Peterborough, with
processing metadata; CC BY4.0 except where otherwise specified.

Use for S4 hypotheses about crop mix, processing/storage and collection patterns,
feeding the actual rural-surplus/settlement ledger. These data are **not** direct
observations of freight tonnage/day, crop yields, tax rates or garrison staffing.
The excavations may overlap the rural-settlement archive; audit their identities
and phases before combining evidence or declaring separate tests.

## Resumption order

1. Preserve the frozen12-variant result and both its location/spacing alternatives.
2. S1c: examine occupancy assumptions and unique-location versus spacing losses;
   address rasterized site roles/resolution without changing past selection rules.
3. Resolve or replace Vidarbha's audited source before a prospective located test.
4. S2: rural preparation complete; resolve place/MAP/phase/taxonomy semantics
   before role-specific calibration, keeping rural evidence separate from county seats.
5. S4: integrate crop/collection evidence into the same food/institution ledger.

S3 differentiated authority and S5 mobile/nonstate communities remain required
stages. These candidate sources do not establish their political mechanisms.

Rural-Britain follow-up: [executable role evidence](ROMAN_RURAL_ROLES_20261110.md)
resolves missing lookup labels from source search, documents −100/400 date
conventions and builds exact-association blocking components. No folds or scores.
Actual places, exported CSV CRS/precision, extra phases and coverage remain gates
before calibration; shared event/project IDs are not site identity.

Coordinate follow-up: the [declared named-site check](ROMAN_RURAL_COORDINATES_20261110.md)
supports operational OSGB-compatible X=easting/Y=northing in metres. All eight
references across six sites lie within188m; this is not whole-source survey
accuracy or official export-CRS certification. Physical places, precision, extra
phases and coverage still constrain role calibration. Earlier audit artifacts
remain unchanged.
