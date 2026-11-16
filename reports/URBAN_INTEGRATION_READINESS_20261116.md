# Hierarchy integration readiness — 16 November 2026

The released fantasy population, H and hierarchy areas reproduce from existing
packets. The current floodplain port would change no fantasy population cells.
The next necessary predictive step is the **joint hierarchy**, with train-only
uncertainty and centre-pair accounting; the earlier standalone regression gain
does not validate its residual-selection and lore operations.

This audit follows `integration_readiness.json` at 8ede6df38. No new fit, source
score, climate calculation, parameter or published asset is changed.

## Published controls and physical inputs

|Released mode|Sites|Population|Residual-selection centres|Capital-shift centres|Assigned subordinates|
|---|---:|---:|---:|---:|---:|
|Raw|1,034|53,119,879|151|19|576|
|Corrected|1,053|53,428,650|151|19|591|

Both use 463×1,000 analysis cells, 3.6802478592 km square cells and 241,889
majority-land cells. Decoded `settlement_base` times central occupation
0.32457726996 equals the administration density **exactly**. Complete nearest-
centre H replays all published town records. Areas replay the capital shift,
centre residual selection, lore rank ordering and three global-top lore places.
Unrounded total area matches the released summary.

Town CSVs deliberately round H to 0.1 person and area to 0.01 ha. The replay
matches at those precisions; differences below 0.05 person/0.005 ha are export
rounding, not physical-input discrepancies. Administration caches exist. The
released full fields NPZ caches are absent; their metadata/CSV/packet controls
remain available. No missing cache is silently regenerated in the atlas.

The existing independently reviewed fantasy floodplain diagnostic found 26
basins per mode, none passing its seasonal timing condition, **zero qualifying
cells**, and unchanged crop capacity. It was a diagnostic port, not an adopted
harvest replacement. This does not contradict the qualified Egyptian input
change: the fantasy catchments have different seasons. There is no justification
for changing timing thresholds to produce a desired city effect. Fantasy r44
climate remains intentionally retained; Earth r46 does not replace it.

## Actual hierarchy and validation scope

The published Earth fit has β=(1.91518, 0.147039), sigma=1.04797, selection
strength phi=0.5 and capital shift c=0.8. Earth calibration promotes residuals
toward 28 known capital records; fantasy application promotes them toward all
151 marked sites, while shifting means at 19 seats. This application assumption
must stay explicit. Campaign symbols are supplied lore, not fitted city sizes.

The archived hierarchy gate was false and the owner adopted the map with its
narrow exceed-share miss disclosed. That decision and old result are preserved.
Inspection also finds three reasons not to treat it as a fully isolated outer
validation for a new model:

- Its global sigma uses residuals from every outer fold, including each test
  fold's areas.
- Its training-fold objective reuses globally prepared out-of-fold means; the
  mean for a training row can have been trained using the outer test fold.
- A training child's observed size ratio can reference a centre in the outer
  test fold.

The fixed source graph has 664 records, 28 capitals and 95 subordinate edges:
76 within one province-hash fold and 19 across folds. The audit independently
checks spherical nearest-centre assignment, without fitting new areas.

|Outer fold|Test records|Training pairs with both endpoints in training|Pairs with both endpoints in test|Old training pairs referencing a test centre|
|---|---:|---:|---:|---:|
|0|208|47|29|17|
|1|182|66|24|1|
|2|144|70|12|0|
|3|130|83|11|1|

A new comparison must estimate all means, sigma and phi/c choices inside outer
training; observed training ratios may use only pairs with both endpoints there.
Held-out pair metrics likewise use both endpoints in the test fold. All 664
records still contribute area predictions; the 19 cross-fold edges remain
disclosed, rather than being mistaken for independent held-out pairs.

## Rebuild obligations

The ten existing chain stages cover sizes, placement review, size review,
supply, supply review, integration, labour, fertility, staffing and ensemble
checks. A later size-law update can retain current positions/counts if population
inputs stay unchanged, but it must regenerate H/areas, resident requests and
their dependent supply/work/staffing/reach/trade/publication artifacts.

The legacy size builder conserves own/wider moved people and checks annual
local cereal. That alone is not the finite seasonal origin/food/labour audit.
`polity.settlement_residents.allocate_residents` and `audit_origin_food` already
provide the finite partition and coupled origin/destination grain checks. Their
existence does not mean the release chain automatically certifies every joint
ledger. A candidate must use the same source grain, remaining rural population
and work-supported production, not infer feasibility from regional totals.

## Declared continuation

`hierarchy_refresh_trial.json` now fixes one paired legacy/refreshed-H hierarchy
trial. It retains the existing phi/c grid, five seeds and source graph, but
repairs training isolation **in both alternatives**. The comparison therefore
attributes old-versus-new differences to H under a common corrected method; it
will not relabel the old archived gate as an exact numeric control. Primary
metrics cover all 664 extents; the existing 153 strict targets remain a source-
basis sensitivity. No map coefficient is fitted or adopted at this stage.

After that source-development trial, a separately qualified full application
and appropriate transfer/evidence strategy remain necessary. Reused Roman
extents do not become dated or independently validated through more tests.
Buringh sizes and climate l stay reserved; climate stays parked.

## Review

The reviewer separately decodes the harvest binary, uses full-distance nearest-
centre ownership with all ties/radius, and replays hierarchy/lore operations
with scalar equations. It checks both CSV-precision controls and unrounded
total areas, independently reconstructs haversine centre pairs, and verifies
the full chain/receipt inventory. Three fresh exports are byte identical; all
protected inputs and published files remain unchanged.

Artifacts: `output/urban_integration_readiness_20261116/`.

```sh
.venv/bin/python scripts/urban_integration_readiness.py
.venv/bin/python scripts/urban_integration_readiness.py --out output/urban_integration_readiness_20261116/fresh
.venv/bin/python scripts/review_urban_integration_readiness.py
```
