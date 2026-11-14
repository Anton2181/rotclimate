# Capillary hydraulics and historical source context verified

The supplied-soil hydraulic component reproduces all 246 FAO61 stationary
profile heights within their published rounding. A separate 50-digit Decimal
implementation agrees with the component and all generated soil-function samples.
This verifies the hydraulic relationship needed before groundwater coupling;
it supplies no water and changes none of the regional field or settlement results.

Open [the curves and source tables](../atlases/earth_evidence/capillary/index.html).
Declaration `3ce2c453` preceded component code and numerical outputs. The published
example and source text were inspected beforehand and are known component
benchmarks, not independent regional validation. This work continued after the
regional forcing/maps checkpoint `074363c0` without pausing at commits/pushes.

## What the source evidence supports

FAO56 Chapter 8 includes capillary rise as an explicit input in its root-zone
water balance. Contribution depends on soil type, water-table depth and root-zone
wetness. Its approximate one-metre-below-root convention is a simplification,
not a universal cutoff for the soil-dependent curves in the later FAO61 Annex 5.

FAO61 supplies Dutch Staring-Series hydraulic parameters and a silty-subsoil O8
example, using six prescribed stationary upward fluxes. These are generic
source properties, not measured ancient Nile parameters. Steady flow itself is
an approximation to transient unsaturated flow, and cannot supply an annual
water budget without recharge, storage and boundary conditions.

The historical source was recovered from the current official University of
Chicago ISAC publication link, which now points to a versioned S3 PDF. The old
PDF-looking URL returned an HTML publication page; its bytes were identified as
HTML, not accepted as a PDF. The verified 7,445,164-byte PDF is digest-pinned in
the protocol and cached, with both printed/PDF page locators retained:

- Butzer 1976, printed p19 / PDF p35, uses contemporary Omo, Senegal and
  Chari–Logone floodplain analogies for earlier Nile ecology. Its discussion of
  capillary/high-water-table support is not a measurement of Roman Nile flux.
- Printed p90 / PDF p106 describes a summer water table at least 3–4 m below
  the surface in most areas. This is a summer statement, not a winter depth.
- Butzer 1984, printed p105 / PDF p4, describes the traditional post-flood high
  water table qualitatively; it does not provide local recharge, storage or a
  quantitative upward flux for adoption.

These contexts support investigating the mechanism. They do not justify a
constant extra groundwater allowance, a larger root-zone TAW, or unrestricted
plant access to water below wilting point.

## Implemented relation

`harvest/capillary_hydraulics.py` accepts supplied residual/saturated water
contents, saturated conductivity, α, connectivity and n, with m=1−1/n. Water
retention and conductivity follow the source Van Genuchten relation. The
component uses a stable log/effective-saturation form; the independent reviewer
uses direct source Equation 4 powers in Decimal arithmetic.

For a supplied ordered suction-magnitude grid starting at zero, midpoint
conductivity determines the stationary head-profile increment. The source's
signed-pressure Equation 6 is equivalent to:

`Δz_cm = Δ|h|_cm × K_mid / (K_mid + q_mm_per_day / 10)`

Height is positive above the water table. Pressure head is negative under
suction; the API accepts its nonnegative magnitude. Conductivity is cm/day and
flux is mm/day, converted once. Zero prescribed flux gives exactly the
hydrostatic profile. Nonuniform increments and multidimensional flux arrays
retain their actual units and shape. Invalid hydraulic parameters, head grids,
nonfinite values and negative prescribed upward flux are rejected.

No stock, recharge, water-table history, root uptake or additional water is
created by this relation. It does not couple itself to the field model.

## Published example and all source profiles

Two independent HTML table parsing paths agree on all 28 Table A5.4 parameter
profiles and every Table A5.5 source cell. The O8 example uses θr=0, θs=0.47,
Ksat=9.08 cm/day, α=0.0136 cm⁻¹, connectivity −0.803 and n=1.342. Pressure-head
magnitudes run 0–400 cm in 10 cm steps. The six prescribed rates are 10, 7.5,
5, 2.5, 1 and 0 mm/day.

|Prescribed upward flux, mm/day|Published height at h=−400 cm, cm|
|---:|---:|
|10|49.7|
|7.5|59.0|
|5|74.0|
|2.5|105.3|
|1|157.6|
|0|400.0|

All 246 published heights agree within their half-last-digit rounding intervals;
no parameter, recurrence or tolerance was adjusted after the result. Largest
model-versus-printed difference is 0.049981 cm, within the 0.05 cm rounding band.
The output additionally retains 448 water-content/conductivity samples across
all 28 supplied profiles. These are evaluations of the parameterized model,
not additional observations or an exact fit to the separate Table A5.3.

## Independent verification and publication

208 controls pass, including 26 new hydraulic controls and the existing 182.
The independent reviewer imports neither producer nor component: it reparses
source parameters, computes direct source-equation conductivity/water content
and signed-head recurrence with 50-digit Decimal arithmetic, checks all 896
hydraulic sample cells and all 246 profile cells, and verifies historical PDF
page context. Maximum hydraulic numeric error is 5.18e-14 in retained units;
maximum profile numeric error is 1.04e-13 cm.

Three fresh numeric files (`reference.json`, `benchmarks.csv`,
`hydraulic_functions.csv`) reproduce byte for byte. Canonical `controls.json`
retains the test-runtime text and is pinned separately, so fresh exports do not
rewrite that identity. All 932 protected files remain unchanged, including the
nine regional forcing/field numeric files and reviews from the previous step.

The page contains all 28 source profiles, six endpoint summaries, the complete
plot and seven downloads. Six viewport/theme checks verify all 34 displayed
rows, download hashes, an actual CSV download, image/keyboard/width and hub/
evidence/return navigation. The staged Windows-style checkout and release
verification receipt is retained under `output/capillary_hydraulics_20261114/`.

## Reproduce

```sh
.venv/bin/python scripts/capillary_source_benchmarks.py
.venv/bin/python scripts/capillary_source_benchmarks.py --out output/capillary_hydraulics_20261114/fresh
.venv/bin/python scripts/review_capillary_hydraulics.py
.venv/bin/python scripts/publish_capillary_hydraulics.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_capillary_browser.py
```

The producer restores raw sources against protocol digests into
`data/cache/recession_groundwater_20261114/`, reusing earlier FAO56/Butzer1984
caches when available. Source equations were inspected as their linked GIFs;
PDF text uses `pdftotext`. The official Butzer1976 version URL and SHA256 are
retained in the protocol. Source PDFs remain cached rather than redistributed
with this page. The browser runner expects the repository on port 8766. Stage
the final site before `scripts/check_atlas_checkout.py --out
output/capillary_hydraulics_20261114/windows_checkout.json`.

## Next work

Declare finite paid groundwater recharge/storage and transfer into the existing
soil/river ledger. Begin with empty stocks, explicit accessible storage floors
and capacities, actual areas/durations and no double-credit of percolation or
return flow. Recharge must consume the same paid river/rain water; upward
transfer must be limited by both hydraulic permission and stored water. Preserve
matched zero-groundwater/legacy controls and every candidate consumer.

Local soil/pressure-retention parameters, root suction/development, water-table
history, drainage/access, transient-flow and high-water-table crop constraints
still require qualification. Do not graft a Dutch hydraulic profile onto the
old synthetic field soil as if locally measured, use the summer depth as a
winter observation, or select rates/capacities to close Egypt's gap. The forcing
period/grid mismatch and shared Earth/fantasy weather/river inputs remain open.

Tigris, independent regions, frozen harvest translation, Nile gain AND
Mesopotamian non-inflation and whole-empire supply checks remain required. The
release-3 settlement atlas / marketed share 0.3923 stays adopted: 850 self-fed,
174 importers, 29 short, 91% fed; reach staffing 1042. Egypt calibration still
fails. Empirical occupancy/provider/size, S3–S5, complete resources/diets/work,
mobile actors and political authority remain separate open obligations.
