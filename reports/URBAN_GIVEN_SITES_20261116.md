# Size rule with observed locations supplied — 16 November 2026

Supplying the source locations/counts allows the unchanged model to generate
towns above 200 ha, but does not remove the size-distribution mismatch. This is
an explanatory control on spent data, not a site forecast or new blind test.
No model parameter, density reading, climate or published map is changed.

The protocol is `calibration/urban_diagnosis_20261116/conditional_sites.json`,
committed before its outputs. Native-projection correction A1 is disclosed below.
The same 119 Mesopotamian and 27 Mexican source towns are retained on both grids.
No capitals or hierarchy-centre labels are invented. Fractional coordinates
avoid collapsing records into one coarse cell. Each model land cell's people
are allocated once to the nearest supplied centre within 60 km; exact ties share
the cell. Sites receiving no cell population remain in every comparison.

|Source cohort|Grid km|Sites with positive H / supplied|Mean area-distribution KS lower bound, five seeds|
|---|---:|---:|---:|
|Mesopotamian towns|3|119 / 119|0.2672|
|Mesopotamian towns|9|114 / 119|0.2941|
|Mexican small settlements|3|27 / 27|0.2815|
|Mexican small settlements|9|20 / 27|0.4296|

For Mesopotamia the observed classes are intervals, including an open final
class. The statistic is a necessary CDF gap, not an imputed-area KS or p-value.
For Mexico the intervals collapse to the reported areas; arithmetic KS is still
conditional on these selected small-settlement records and their measurement
definitions. No threshold is used to discard small model predictions.

At 3 km, the Mesopotamian model makes an average 1.4 towns above 200 ha over the
five seeds, against three records in that source class. The mean total model
area is 3,891.8 ha; source total area has a lower bound but no finite upper from
these classes. Many ordinary model towns are too large relative to the source's
10.1–20 ha band. Thus a blanket size/population multiplier is a poor next
experiment. Redistributing a fixed population request is a more discriminating
test, while a rank-only control can reveal gains from simply stretching noise.

The coarse grid causes a second limitation: even with every source point
supplied, five Mesopotamian and seven Mexican points receive no population cell
at 9 km. At 3 km all are supported. These zeros are a discretization result,
not evidence that the settlements were uninhabited. Future size comparisons
should preserve the 3 km diagnostic and report the 9 km sensitivity separately.

Mexico's cohort remains rural/small-settlement evidence: no estimate exceeds
1,000 people. The Old World density readings remain scenarios, not a fitted
Mexican population conversion. Nor does this control confirm a complete
regional urban census or Teotihuacan's exact treatment in the survey.

## Checks and correction record

An initial draft treated the native grid as affine latitude/longitude. Its
unreviewed summaries were inspected before grid curvature exposed the error;
no fit or adoption used them. All first artifacts and producer code are retained
under `invalid_affine_first_run/`. Amendment
`conditional_projection_a1.json` was committed before the corrected outputs.
Valid calculations use the existing spherical azimuthal-equidistant projection
and the stored native x/y origins. The Mexico datum assumption remains the one
in the original test; fractional indices do not claim extra source accuracy.

The independent reviewer uses PROJ's spherical projection, scalar point/cell
ownership, raw-source cohorts, direct size/density equations and CDF envelopes.
All 20 case rows and CSV cells pass; 26 component controls pass. Four fresh
exports reproduce byte for byte. Results, geometry/accounting, complete cases
and review are under `output/urban_given_sites_20261116/`.

Reproduce after the earlier diagnosis/input restoration:

```sh
.venv/bin/python scripts/urban_given_sites.py
.venv/bin/python scripts/urban_given_sites.py --out output/urban_given_sites_20261116/fresh
.venv/bin/python scripts/review_urban_given_sites.py
```

The next screen will hold total requested urban residents fixed under each
existing density reading. It will compare stronger dependence on hinterland
people with a control that merely stretches the existing size ranking. This
does not yet certify actual migration, rural labour, grain supply or a new
settlement forecast. Those require the existing origin/food ledger and an
appropriate transfer test before any map integration.
