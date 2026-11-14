# Matched meteorology produces new paired regional water maps

The new32-case comparison keeps all1,507candidate fields and sixteen exact
archived controls. Matching temperature/rain to the modern ETo period modestly
increases Nile root-water coverage in the fixed members. It does not close
Egypt's calibration gap or establish crop yield. Groundwater remains disabled;
the adopted settlement atlas is unchanged.

Open [the maps and complete comparison](../atlases/earth_evidence/matched_weather/index.html).
Weather declaration `df1e174c` and reviewed input freeze `6e720369` preceded the
field declaration `1189eb46` and all new field outputs. All inputs/earlier results
were declared exposed development; none is an independent regional holdout.

## Paired result

|Region|Reference method|Calendar|ETo-only control root coverage %|Matched T/P/ETo %|
|---|---|---|---:|---:|
|Nile|Hargreaves|5-bin|68.273|70.827|
|Nile|Hargreaves|4-bin fractional|80.820|81.521|
|Nile|Penman–Monteith|5-bin|52.437|53.930|
|Nile|Penman–Monteith|4-bin fractional|66.149|67.850|
|Euphrates only|Hargreaves|5-bin|2.799|2.524|
|Euphrates only|Hargreaves|4-bin fractional|3.612|2.604|
|Euphrates only|Penman–Monteith|5-bin|0.889|0.674|
|Euphrates only|Penman–Monteith|4-bin fractional|1.176|0.728|

These are river-capture cases; all rain-only controls are retained in the32rows,
figure and downloads. Root coverage is actual/potential root transpiration,
not total-crop ET, grain, cultivated area or residents. No reference method,
calendar or parameter is selected from these outcomes. Euphrates capture and
rain-only root coverage agree in these members; the Tigris remains absent.

Nile PM useful delivery is27.984→27.959km³ for the longer crop and28.530→28.504km³
for the shorter crop. Candidate area remains24,497km² Nile /63,986km² Euphrates.
All candidates remain thermally eligible under both supplied temperature choices.
The model has no additional continuous temperature-growth response here, so
this result does not quantify local crop temperature stress.

## Fixed structure and meteorological mapping

Every case retains barley, root depth1.5m, θFC0.25/WP0.10 and TAW225mm,
evaporation depth0.1m/REW9mm, bare background0.15, pond200mm, infiltration20mm/day,
efficiency1, the legacy constant crop coefficient and exposed fraction0.25.
Crop/flood clocks, river excess volumes and periodic criteria remain unchanged.
Thermal eligibility is recomputed from the declared temperature choice without
dropping any candidate water consumer. Original field/soil/router code is unchanged.

Only the T/P source changes within each paired reference method. Thirty fixed
NASA POWER samples have complete2020–2024LST meteorology. All438,480overlapping
weather values, units and provider geometry exactly match the earlier ETo
packets, allowing the previously reviewed ETo arrays to be reused exactly.
Rain totals conserve actual Gregorian month/year amounts and both leap days.
Temperature is a physical Celsius monthly mean, not scaled by month length.
See [the input preflight](MATCHED_REGIONAL_WEATHER_20261114.md).

Area-weighted annual rain rises38.454→110.046mm Nile and139.958→157.692mm
Euphrates-only. More annual rainfall does not guarantee more crop-season root
uptake: timing, location, evaporation, infiltration and carry matter. This is
not a precipitation-product accuracy test. Source, period and sampling change
together; daily extremes and interannual variability remain absent from monthly
climatological inputs.

Modern weather does not match the historical flow epochs: Aswan1871–1901 and
selected Hit1965–1971 means. Nor is this a reconstruction of ancient weather.
Local phenology, basal demand/canopy/root development, soil profiles and drainage
remain supplied approximations. The modern groundwater-source audit did not
qualify regional capacities or capillary permissions; no extra water is added.

## Independent verification and publication

The input reviewer uses raw date/unit/domain/overlap checks,50-digit Decimal
aggregation,360sample bins, scalar containing-tile assignments and36,168mapped
T/P cells. Input maximum aggregation difference is1.43e-14 in retained units.
Four fresh input exports reproduce byte for byte.

The field reviewer imports neither producer nor forcing adapter. It independently
sets up temperature choice/eligibility, calendar and gauge volume and uses the
reviewed scalar soil/pond/node kernel. It replays9,114,336final-cycle field-steps,
all annual field states/fluxes, monthly basin flows, daily basin stocks and every
cell in24,112CSVrows. All sixteen ETo-only cases exactly reproduce every archived
array. Maximum annual-field difference is5.69e-12mm; maximum scalar daily field
residual is1.33e-13mm. Maximum annual joint residual is1.91e-5m³ at basin scale.

All32cases converge. Thirty-one need two repeated cycles; the matched five-bin
Nile rain-only case needs sixteen. The same all-four-stock1e-6mm/50cycle rule
applies throughout. Three fresh field files reproduce byte for byte, and all
952protected scientific files remain unchanged.

Two figures show all32scenario results and eight side-by-side PM capture maps
with a shared0–1root-coverage legend. The normal page exposes every outcome,
fourteen downloads and all raw source packets. Browser checks cover six width/
theme cases, all32numeric rows,54filter combinations, actual CSV download,
fourteen download hashes,31source ZIP members, images/keyboard/width/navigation.
Staged Windows-style checkout and complete release verification are retained.

## Reproduce

```sh
.venv/bin/python scripts/matched_regional_fields.py --workers 4
.venv/bin/python scripts/matched_regional_fields.py --out output/matched_regional_fields_20261114/fresh --workers 4
.venv/bin/python scripts/review_matched_regional_fields.py
.venv/bin/python scripts/publish_matched_regional_fields.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_matched_weather_browser.py
```

Input preflight and field declaration must be committed before scoring. The
browser runner expects port8766. Stage final site assets before
`scripts/check_atlas_checkout.py --out output/matched_regional_fields_20261114/windows_checkout.json`.
Force-add the primary field NPZ; fresh exports and screenshots remain ignored.

## Next dependency

Source-qualify local phenology and stage lengths/thermal time, basal crop demand
and canopy/root development before declaring regional stage-curve comparisons.
Keep consistent soil/retention/depletion/drainage inputs and the basal diffusion
versus evaporation policy explicit. Root coverage cannot directly replace
total-crop ET in the legacy Ky harvest relationship. Groundwater input gaps,
historical river compatibility, shared Earth/fantasy weather/flow, Tigris and
independent regions remain open before frozen harvest and whole-empire checks.

The [local groundwater observations](NILE_GROUNDWATER_SOURCES_20261114.md) often
place the water table inside the currently supplied 1.5 m root profile. Applying
those depths requires a consistent saturated/unsaturated root and oxygen/drainage
definition; simply adding capillary input to this entirely unsaturated bucket
would not represent that boundary.

Release3/marketed share0.3923 remains adopted:850self-fed,174imports,29short,
91%fed;reach staffing1042. Egypt calibration still fails. S3–S5, empirical
occupancy/provider/size, complete resources/diets/work, mobile actors and
political authority remain separate programme obligations.
