# Regional evaporation forcing changes the paired field-water result

All 1,507 existing candidate fields now have a declared regional weather
assignment and paired evaporation-forcing controls. In the fixed Nile capture
illustrations, root-demand coverage is 65.3%/79.0% under archived forcing,
68.3%/80.8% under regional Hargreaves, and 52.4%/66.1% under regional
Penman–Monteith for the five-bin/fractional four-bin crops respectively.
These are conditional water diagnostics, not new crop yields or settlements.

Open [the new comparison maps and complete cases](../atlases/earth_evidence/regional_forcing/index.html).
Declaration `6366d34d` preceded regional weather capture and field outputs.
Commit `7a645ea7` froze the 30 weather snapshots and shared-adapter preflight;
`dadf8859` froze the independently reviewed regional forcing before field runs.
Commits/pushes were used as checkpoints throughout the full experiment.

## What changed, and what stayed fixed

Each existing five-minute field is assigned to the centre of its containing
half-open one-degree tile: floor(latitude/longitude) plus 0.5°. The candidate
mask alone selected all 30 samples, 15 for each region. This is a fixed sampling
lattice, not a claim about NASA's native resolution or local downscaling.
All candidates remain water consumers, even when the prescribed crop is
thermally ineligible. There is no selective deletion or fallback forcing.

NASA POWER agricultural daily point responses supply mean/min/max temperature,
dewpoint, mean relative humidity, 2 m wind, pressure and solar radiation for
2020–2024 local solar time. All 54,810 requested source dates pass the declared
checks. Full raw responses, URLs, units, grid elevations, provider headers,
raw/semantic hashes and source receipt are tracked under
`data/source/regional_reference_forcing_20261114/` and shipped as a source ZIP.
These are MERRA2/SYN1DEG/POWER gridded products, not station observations or
ancient climate. No three-location point ratios are applied to the fields.

At each sample, daily Hargreaves and PM share the same weather and Earth FAO
solar geometry. Each actual Gregorian month is summed for each year; the five
same-month totals are averaged and mapped to the existing twelve equal model
bins. Their annual sum preserves the mean of the five annual daily totals,
including leap days. Actual model-bin/step durations convert these amounts to
rates. This is a declared conservative climatology/phase approximation, not
observed weather on the model's calendar.

The 24 cases are the eight earlier mapped illustrations times three forcing
choices. Every illustration fixes barley, supplied root depth 1.5 m / TAW 225 mm,
bare coefficient 0.15, pond 200 mm, efficiency 1, the same soil/infiltration/
pond/root uptake rules, river source, capture/rain-only policy and one of the
two supplied crop calendars. Original WorldClim temperature/rain and thermal
eligibility are frozen. Only the reference-evaporation array changes.

Thus regional Hargreaves versus regional PM isolates the method under the same
weather/assignment/mapping. Archived versus regional Hargreaves also changes
weather source, period, solar geometry and temporal aggregation. POWER
2020–2024 ETo paired with WorldClim 1970–2000 temperature/rain is explicitly an
evaporation-only sensitivity, not a consistent climate reconstruction.

## Spatial coverage and reference demand

Annual ETo means below use actual candidate-area weights. Distances refer to
field coordinates versus their fixed weather sample, not observational accuracy.

|Region|Fields|Samples|Mean/max distance, km|Archived ETo, mm/year|Regional Hargreaves|Regional PM|
|---|---:|---:|---:|---:|---:|---:|
|Nile|489|15|41.10 / 67.78|1,604.4|1,625.3|2,226.6|
|Mesopotamia, Euphrates only|1,018|15|39.01 / 67.21|1,865.7|1,913.1|2,665.5|

Complete assignments retain field area, sample coordinates, distance and provider
grid elevation. Samples can mix coast, valley, desert and elevated terrain.
Complete coverage does not qualify their spatial or temporal representativeness.

## Paired water outcomes

Root coverage is eligible-field, area-weighted actual/potential root uptake.
It is not the earlier total-crop ET percentage, a yield or cultivated hectares.
All 24 cases reach repeating stocks in two cycles, starting empty.

|Region/calendar/access|Archived forcing|Regional Hargreaves|Regional PM|
|---|---:|---:|---:|
|Nile, five-bin, rain only|0.46%|1.04%|0.13%|
|Nile, five-bin, capture|65.33%|68.27%|52.44%|
|Nile, four-bin fractional, rain only|0.58%|1.26%|0.17%|
|Nile, four-bin fractional, capture|79.00%|80.82%|66.15%|
|Euphrates only, five-bin, either access|3.69%|2.80%|0.89%|
|Euphrates only, four-bin fractional, either access|4.76%|3.61%|1.18%|

With Nile capture, useful delivery also increases: archived 21.913/22.459 km³
versus PM 27.984/28.530 km³ for the two calendars. Greater ETo changes both
losses and demand, while paid river and field ledgers still close. It cannot
be treated as a change to a yield score in isolation. The largest joint annual
mass residual is 7.63e-6 m³ against billion-m³ flows, a numerical closure result.

Mesopotamia still receives Euphrates water only, without the Tigris. In these
fixed members, capture does not change root coverage under any forcing choice.
This does not establish complete regional supply or harvest non-inflation.
No forcing, calendar or field parameter is selected for adoption.

## Shared Earth/fantasy adapter

`harvest/reference_forcing.py` accepts explicit supplied extraterrestrial
radiation and meteorological variables, applies the reviewed FAO daily algebra,
and conserves supplied bin amounts. Earth supplies Earth solar geometry. A
fantasy caller must supply its own world radiation plus compatible mean/min/max
temperatures, vapour pressure, 2 m wind, pressure, surface solar radiation and
elevation; daily reference units and the terrestrial empirical assumptions also
need qualification. Missing inputs are rejected, not inferred from Earth.

The existing fantasy harvest cache path consumes `Tm`/`Pm`, geometry and a learned
diurnal range. It does not supply all the required near-surface weather through
that adapter. The shared algebra is implemented and tested; a qualified fantasy
weather connection and the shared Earth/fantasy river-flow adapter remain open.
The old daily reference kernel and legacy atlas functions are unchanged.

## Independent review and publication

- 182 controls pass. Before regional outputs, 1,000 supplied-world radiation
  cases / 17,000 scalar-Decimal cells and 3,600 independent bin-amount cells
  verify the adapter, alongside tile boundaries, arbitrary period labels,
  leap years, source units/ranges and fractional model steps.
- Independent regional-weather review reconstructs all 931,770 computed cells
  across 54,810 dates, every monthly amount and all 1,507 assignments. Maximum
  daily numeric difference is 2.49e-14 in retained units; maximum monthly amount
  difference is 2.28e-13 mm. Four fresh weather exports are byte-identical.
- Independent field review reuses the earlier qualified scalar soil/pond/node
  kernel with only its PET input changed. It reconstructs clock/eligibility/
  gauge inputs, replays all cases through spin-up, checks 6,835,752 final-cycle
  field-steps, annual per-field stocks/fluxes, monthly basin ledgers, daily basin
  stocks and all 18,084 CSV rows. Full daily per-field trajectories are not
  exported/directly compared. Maximum annual field difference is 3.64e-12 mm;
  maximum scalar daily mass residual is 1.35e-13 mm.
- All eight legacy cases reproduce their archived field/flux/state/basin arrays
  exactly. Three fresh field exports are byte-identical. All 923 protected files
  remain unchanged, including the previous three-location weather audit and
  earlier Earth-fit/water/crop-stage numeric outputs.
- The normal page retains all 24 outcomes, both regional coverage rows, two
  figures and fourteen downloads. Browser checks cover six viewport/theme
  cases, every displayed cell, 162 filter combinations, all download hashes,
  every raw source ZIP member, a real field-CSV download, images, keyboard,
  width and hub/evidence/return links. Staged Windows checkout and complete
  release verification are retained alongside the other receipts.

## Reproduce

```sh
# Source/core stage; frozen source and core proofs must precede weather outputs.
python scripts/capture_regional_reference_weather.py
.venv/bin/python scripts/audit_reference_forcing.py
.venv/bin/python scripts/regional_reference_weather.py
.venv/bin/python scripts/regional_reference_weather.py --out output/regional_reference_forcing_20261114/fresh
.venv/bin/python scripts/review_regional_reference_weather.py
# Freeze the reviewed weather inputs before the field producer gate.
.venv/bin/python scripts/regional_reference_fields.py
.venv/bin/python scripts/regional_reference_fields.py --out output/regional_reference_forcing_20261114/fresh
.venv/bin/python scripts/review_regional_reference_fields.py
.venv/bin/python scripts/publish_regional_reference_forcing.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_regional_reference_browser.py
```

The source capture reuses frozen tracked responses. For core-only verification,
use `audit_reference_forcing.py --out
output/regional_reference_forcing_20261114/core/fresh`; overwriting canonical
core/review.json changes its runtime text and requires regenerating downstream
provenance. The field producer always reads canonical reviewed forcing, even
when exporting a fresh result directory. Serve the repository on port 8766 for
the browser runner. Stage the final site before `scripts/check_atlas_checkout.py
--out output/regional_reference_forcing_20261114/windows_checkout.json`.

## Next work

Regional forcing and paired fields are complete as development evidence. Period,
grid and reference assumptions still need qualification before forcing adoption.
The next source check concerns post-flood crop support: soil/root development,
canopy/basal diffusion and the documented high water table, with explicit paid
recharge and finite storage if groundwater is modelled. Do not add unlimited
capillary water, select a rooting depth/season to close Egypt's gap or apply
point multipliers. Crop phenology and pond/access/drainage evidence remain open.

Tigris, shared Earth/fantasy weather/river adapters, independent regional evidence
and frozen harvest translation remain required before Nile gain AND Mesopotamian
non-inflation and whole-empire supply checks. The release-3 settlement atlas and
marketed share 0.3923 remain adopted: 850 self-fed, 174 importers, 29 short,
91% fed; reach staffing 1042. Egypt calibration still fails. Empirical occupancy/
provider/size, S3–S5, complete resources/diets/work, mobile actors and political
authority remain separate programme obligations; these maps do not close them.
