# Urban development evidence: selection and measurement — 16 November 2026

The available sources do not support treating every area as the same observed
urban quantity. The Roman catalogue combines extent definitions, omits many
city areas, and gives no separate area-date column. Archaeological survey town
cohorts select records by measured area. These differences must enter the next
analysis; they cannot be repaired by stretching a city ranking.

This is the source-only audit declared in `development_evidence.json` at
b43e93bfa, after the negative fixed-request concentration screen. No regression,
new predictive score, density law or map change was made. All sources were
already exposed. Protected prior results remain unchanged.

## Recounted source cohorts

|Roman source accounting|Records|
|---|---:|
|Cities / area records, all catalogue dates|1,388 / 885|
|Area keys without a matching city|0|
|All catalogue cities without an area|503|
|City catalogue intervals containing AD 150|1,354|
|Those cities without an area|492 (36.3%)|
|AD 150 catalogue cities with a positive area|862|
|After the existing exact 20/30 ha exclusion|806|
|Excluded exact 20/30 ha records in that source cohort|56|
|Actual current geographically filtered/corrected training cohort|664|

The 862/806 source cohorts precede window, allowed-land, positive-H and finite-
core filters. They also precede the existing Greek wall-area correction. They
are not claimed to reproduce the 664-row training cohort. That cohort's archived
four province folds contain 208/182/144/130 records over 15/14/11/11 provinces.
Source-level excluded values number 56, whereas an older all-date summary gave
57: these have different date selections, not an unexplained missing record.

Among 862 joined AD 150 catalogue records, exact basis labels include 350
`Walls`, 203 `Inhabited area`, 98 `Urban grid`, 62 `Unspecified`, and 47
`Urban grid and walls`. All remaining labels and province counts are retained
in the exports rather than forced into invented equivalent categories. Some
labels explicitly mention Classical, Byzantine or Late Roman walls.

The Areas table has only `Primary Key`, `Area`, and `Estimate Basis`. Catalogue
start/end dates describe the city's existence. They do not by themselves date
its measured extent to AD 150. This is a limitation of the machine-readable
table, not proof that the underlying publications contain no chronology.

The existing exact 20/30 exclusion removes records with several bases, including
21 labelled exactly `Inhabited area`, 20 `Walls`, and others. This audit does not
certify all 56 as defaults or recommend restoring/excluding them on outcome.
Any changed eligibility rule needs a declared sensitivity comparison.

Raw area bins illustrate the selection differences, without making the extent
definitions equivalent:

|Source cohort|<10 ha|10–20 ha|>20–40 ha|>40–200 ha|>200 ha|
|---|---:|---:|---:|---:|---:|
|Roman catalogue AD 150, all joined positive areas|96|196|229|319|22|
|Same, excluding exact 20/30|96|166|203|319|22|

Mesopotamia's reviewed 820 selected all-site records include 119 town-class
records (≥10.1 ha); 87 of those towns are in the 10.1–20 ha band. Mexico's
221 selected small-settlement records include 27 of at least 10 ha. Neither
site-derived survey mask is independent coverage. The supplied-town diagnostic
conditions its locations on the observed size selection. Drawing only above
that threshold would change the estimand and conceal town-membership failures
unless those are evaluated separately.

## Next bounded analysis

The next declaration is `measurement_basis_pilot.json`: compare a homogeneous
exact-`Inhabited area` subset with the existing mixed-basis training set on the
same held-out inhabited-area records. Preserve the legacy geographic eligibility,
20/30 exclusion and Greek correction so this experiment changes training basis
alone. Keep mean-only, hinterland, and existing-capital predictors separate.
Every coefficient and predictive dispersion estimate must come from the outer
training provinces, with inner province folds for dispersion; no full-data
residual estimate may leak into held-out intervals.

This can diagnose whether source mixture explains weak predictive size skill.
It cannot certify AD 150 extent dates, urban population, town counts, actual food
support, or transfer to another source. Missing city areas are not zeros. The
strict label is a reproducible measurement filter, not a certificate of precise
chronology or survey completeness. No source-level population correction follows
from the 36.3% missing-area fraction.

If the strict subset lacks declared fold support, report the support failure
without broadening its definition after seeing scores. Subsequent work may seek
dated extent references or qualify a genuinely independent appropriate transfer
pool. Buringh sizes and climate l stay reserved. The current release remains
unchanged, and climate work remains parked.

## Verification

An independent `csv.reader` implementation recounts all 1,388 city records,
885 areas, unique joins, eligibility, raw bins, basis/province/fold counts,
actual training metadata and survey summaries. All 332 aggregate cells match;
two fresh exports reproduce byte for byte. No raw city keys or coordinates are
redistributed. Source identities and aggregate/review receipts are under
`output/urban_development_evidence_20261116/`.

```sh
.venv/bin/python scripts/audit_urban_development_evidence.py
.venv/bin/python scripts/audit_urban_development_evidence.py --out output/urban_development_evidence_20261116/fresh
.venv/bin/python scripts/review_urban_development_evidence.py
```
