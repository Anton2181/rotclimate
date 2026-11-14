# Matched regional meteorological inputs verified before field comparisons

Temperature, rainfall and reference ETo now share the declared 2020–2024 NASA
POWER sampling period and all thirty fixed sample locations. All1,507 original
candidate assignments remain. This is an input preflight, not a field, crop-yield
or settlement result. Groundwater remains disabled in regional fields.

Declaration `df1e174c` preceded rainfall capture and joint input arrays. The
earlier evaporation-only and groundwater results were exposed development.
New raw packets include all eight previous weather variables plus PRECTOTCORR.
Every one of the438,480 overlapping values and provider geometries/units agrees
exactly with the frozen inputs, so the already independently reviewed daily
Hargreaves and Penman–Monteith evaporation can be reused without substitution.

All54,810 daily sample rows are complete:1,827LST dates per sample, including
29February2020 and2024. Rain is finite nonnegative mm/day. Actual Gregorian
month amounts are summed within each year and the five same-month totals are
averaged, conserving the mean annual total. Those amounts map to twelve equal
model bins. For temperature, daily Celsius means are averaged within each
year/month, then equally across the five years. Physical temperature means are
not scaled to conserve a Celsius integral; constant temperature stays constant.
Monthly means do not reproduce daily thermal extremes or interannual variability.

|Candidate region|Archived area-weighted annual rain mm|Matched annual rain mm|
|---|---:|---:|
|Nile|38.454|110.046|
|Euphrates only|139.958|157.692|

These differences include period, source and spatial sampling effects. They
are not evidence that one precipitation product is locally correct. Five modern
years of gridded weather are not an ancient reconstruction, station validation
or a long climatic normal. Aswan1871–1901 and selected Hit1965–1971 discharge
means remain different epochs. Matching the meteorological inputs does not
resolve historical river-flow compatibility or qualify local crop/soil inputs.

The independent reviewer imports no producer. It checks raw dates/units/domain/
overlap, uses50-digit Decimal month/year arithmetic, verifies all360sample bins,
all1,507scalar containing-tile assignments and36,168mapped T/P cells, all CSV
cells and original array controls. Maximum aggregation difference is recorded
in [review.json](../output/matched_regional_weather_20261114/review.json).
Four fresh files reproduce byte for byte; all947protected files remain unchanged.

Reproduce:

```sh
python scripts/capture_matched_regional_weather.py
.venv/bin/python scripts/matched_regional_weather.py
.venv/bin/python scripts/matched_regional_weather.py --out output/matched_regional_weather_20261114/fresh
.venv/bin/python scripts/review_matched_regional_weather.py
```

Raw packets/receipts are tracked under
`data/source/matched_regional_weather_20261114/`. The input archive and complete
daily/bin exports are under `output/matched_regional_weather_20261114/`.
Next declare paired field comparisons with matched archived controls, recomputed
thermal eligibility and every candidate consumer retained. Keep fixed calendars,
soil/pond/routing/root assumptions visible; no groundwater or harvest adoption.
