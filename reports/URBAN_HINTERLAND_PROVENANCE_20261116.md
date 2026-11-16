# Urban hinterland provenance — 16 November 2026

The consistently underpredicted province is **Aegyptus**. Its eleven strict
inhabited-area targets are all underpredicted by mixed M1, with mean log-area
residual +1.441. They have no existing capital label. The large opposite error
belongs to a single strict target in Moesia Inferior. These are aggregate source
joins, not new labels or grounds to remove either province.

The input trace exposes an unresolved population-assumption difference: the
current size fit uses the original settlement-base field, while the qualified
Egypt-inclusive supply calculation uses floodplain crop capacity, a heartland
pattern and a different population anchor. This is not proof that a stale field
caused the residuals. A supply success cannot be treated as validation of the
size fit's unchanged H covariate.

The declaration is `hinterland_provenance_audit.json`, committed at f4bdd1dd8
before the new source join. All 51 province codes, 226 basis aggregates and
240 named fixed residual summaries are retained. No city keys/names, raw rows
or coordinates are exported. No regression or new predictive score is computed.

## The three population branches

|Use|Population recipe|What H or supply actually uses|
|---|---|---|
|Current Earth size calibration|Frozen settlement base × central occupation 0.32457727|Original `rome_inputs.npz`, 400×600 cells at 9 km; nearest occupied cell within 60 km|
|Qualified Earth supply calibration|Floodplain crop capacity × legacy heartland history, normalized to 61.4 million on Roman allowed land|Separate P2 population pattern; grain production also applies the floodplain rule|
|Released fantasy town sizes|Published settlement base × published central occupation|Administrative population grid; same 60 km nearest-centre primitive on released town sites|

For the Earth size fit, nearest-centre assignment is to distinct occupied cells.
Catalogue rows sharing one cell receive the same H covariate; adding those row
values is not a conserved population allocation. The archived source size fit
still references pool SHA `dd98cc76…`, exactly matching the original preparation
receipt. Its recorded global harvest input was `bf19bc00…`.

The released supply result instead points exactly to the independently reviewed
Greek-wall supply calibration (`6155cd48…`), whose headline extraction share is
0.3371937. That code samples the floodplain grid (`3b57d0cb…`), multiplies crop
capacity by the old history pattern and normalizes to Frier's 61.4 million.
The supply population basis differs from the size fit in both spatial recipe
and anchoring. Food production, marketed surplus, crop capacity and population
are distinct variables; this audit does not substitute one for another.

The fantasy builder uses the published settlement-base population field. It
does not use the Earth supply calculation's Frier-normalized P2 pattern or the
optional `settlement_cored` harvest field. Core/history weighting in placement
is a separate dependency. Replacing Earth size-fit H with P2 alone would therefore
change its relationship to the population recipe used when applying the fit.
Any later comparison must keep that distinction explicit.

## Source and artifact status

Aegyptus has 20 mixed eligible records, including eleven labelled exactly
`Inhabited area`. Their strict H median is 8,355 people, range 82–70,873; no Greek
wall correction affects them. Moesia Inferior has seven mixed records and one
strict record, so its strict residual remains a small-sample observation. No
date certification follows from either province's source basis label.

The original global grid and the qualified floodplain global/basin arrays are
absent from this checkout at audit time. The frozen Roman input remains present.
A separately restored global baseline is available, with SHA `341d2056…`; it
matches neither the original global grid nor the qualified floodplain grid.
Consequently there is **no numeric old/current H ratio** in this audit. The code
provides a recipe for sampling the qualified grid on the Roman geometry, but
its actual spatial/variable alignment must be verified after exact restoration.

The provenance is a check of code dependencies, recorded receipts and available
arrays. It does not reconstruct an absent historical binary or prove that the
current source code reproduces every historical global field. This distinction
is preserved in the machine-readable receipt.

## Controlled next step

`population_recipe_replay.json` declares the next comparison before outputs:
restore the already qualified floodplain grid exactly in an isolated directory,
then compare the immutable legacy density, the same settlement-base recipe on
the restored floodplain harvest, and the qualified P2/Frier recipe. Preserve
all source sites, centre cells, masks and training records. Report population
totals, assigned/unassigned H mass, per-province H changes and unsupported rows;
do not fit or generate city areas yet.

The restoration replays existing observed-weather harvest/water calculations;
it is not a new climate fit. If its archived SHA cannot be reproduced, retain
the failure and do not call the replacement the qualified input. A field-refresh
comparison can identify changed covariates, but not by itself certify a size
law, transfer or a population map. No Egyptian multiplier or outcome-selected
exclusion is introduced. Climate and reserved Buringh sizes/climate l stay closed.

## Verification

Review reuses the pinned, previously reviewed legacy geometry and independently
rebuilds raw table joins, scalar area corrections, basis/capital/fold encodings,
all 664 anonymous design rows and all province aggregates. Separate AST code
checks and receipt links verify the three dependency branches. All 7,873 CSV
cells match; five fresh files reproduce exactly. Prior artifacts are unchanged.

```sh
.venv/bin/python scripts/urban_hinterland_provenance.py
.venv/bin/python scripts/urban_hinterland_provenance.py --out output/urban_hinterland_provenance_20261116/fresh
.venv/bin/python scripts/review_urban_hinterland_provenance.py
```
