# Next Earth evidence for settlements and control

Metadata/schema review on10November2026, after the first count-separated
development experiment. This supports S1c/d, S2 and S4 of the
[full roadmap](SETTLEMENT_CONTROL_ROADMAP_20261110.md); it does not qualify or
replace any model. The repository's reports/calibrations/scripts/research notes
were searched for these identifiers, with no previous use found. That search
does not prove their observations are independent of every source already used.

**No target CSVs, coordinates or model scores from these candidates were loaded.**
Only source descriptions and the Vidarbha methods/schema readme were inspected.
These are candidates to audit, not sealed tests or complete archaeological censuses.

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

Next: declare a preparation-only schema/chronology audit without fitting or site
scores. Only after that audit can a candidate and a role-appropriate prospective
comparison be frozen. Do not substitute raw known-site counts for total settlements
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
administrative-seat counts by treating every rural excavation as a seat. Verify
the archive's file licence, schema and version before acquisition.

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
3. Audit Vidarbha schema/coverage before declaring a prospective transfer protocol.
4. S2: acquire role-appropriate rural evidence; keep it separate from county seats.
5. S4: integrate crop/collection evidence into the same food/institution ledger.

S3 differentiated authority and S5 mobile/nonstate communities remain required
stages. These candidate sources do not establish their political mechanisms.
