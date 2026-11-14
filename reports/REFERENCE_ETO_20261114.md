# Reference evaporation differs materially between methods on matched weather

Daily Hargreaves reference evaporation is 19–30% below FAO56 Penman–Monteith on
the declared 2020–2024 NASA POWER gridded weather at Cairo, Aswan and Hit. The
comparison exposes uncertainty in the forcing used by the earlier water
experiments. It does not validate either method against measured crop ET,
select a correction factor, or change the settlement atlas.

Open [the normal evidence page](../atlases/earth_evidence/reference_eto/index.html)
for charts, every climatological month, complete daily results and raw weather.
Protocol `4d93e88b` preceded weather capture and model outputs. Commit `15010e41`
froze the weather snapshots and independent preflight before site ETo results.
The known FAO examples are published component checks, not blind validation.

## Fixed inputs and methods

All sites and dates were declared before inspecting POWER weather: Cairo
30.04°N/31.24°E, Aswan 24.09°N/32.90°E, Hit 33.64°N/42.83°E; 1 January 2020
through 31 December 2024, local solar time. Each site has 1,827 days, including
the two leap days. All 5,481 requested rows pass the declared checks; no filling,
date exclusion, alternate period or replacement location is used.

The eight provider variables are mean/minimum/maximum temperature, dewpoint,
mean relative humidity, 2 m wind, surface solar radiation and surface pressure.
NASA POWER identifies its MERRA2/SYN1DEG/POWER sources. These are gridded
model/satellite products, not station observations or ancient climate.
Returned grid elevations are 135.44 m, 253.64 m and 79.59 m respectively; they
are not surveyed city/station elevations. The source returns solar radiation in
MJ/m²/day under the agricultural community, so the applied conversion factor
is 1, not 3.6. Every raw response, request URL, provider unit, source header,
raw SHA256 and semantic parameter-data digest is retained under
`data/source/reference_eto_20261114/` and in the published downloads.

`harvest/reference_eto.py` implements daily FAO56 grass-reference equations:

- Extraterrestrial radiation includes the Earth–Sun distance factor, latitude,
  declination and Gregorian day of year. The trigonometric denominator is 365
  as specified in FAO56, including when the supplied date is leap-year day 366.
- Net shortwave radiation uses albedo 0.23. Longwave radiation uses supplied
  daily min/max temperatures, actual vapour pressure from mean dewpoint and
  clear-sky radiation based on the provider grid elevation. The cloud ratio
  Rs/Rso is explicitly bounded to 0.3–1, as declared before source capture.
- Daily Penman–Monteith uses supplied 2 m wind, pressure and mean temperature,
  mean saturation pressure at Tmin/Tmax, and soil heat flux G=0. Raw signed ETo
  and its radiation/aerodynamic terms are retained; reported ETo is bounded at
  zero. No negative raw ETo occurs in these snapshots.
- Daily Hargreaves uses exactly the same temperatures and FAO extraterrestrial
  radiation, coefficient 0.0023 and the 0.408 conversion from MJ/m²/day to
  evaporation-equivalent mm/day. Its coefficient is not fitted by location.

There are 213 cloud-ratio bound events: Cairo 14, Aswan 156, Hit 43. Every raw
and bounded value is exported; the bound is a declared empirical approximation,
not an inferred site calibration. The component does not supply polar-night
longwave estimation or any crop coefficient/root uptake.

## Results

Five-year average annual totals, mm/year; leap days are included in each year's
sum. “Atlas-style” applies the unchanged monthly atlas functions to the same
modern monthly weather. It is not the archived WorldClim field forcing.

|Location|FAO Penman–Monteith|Daily Hargreaves|Atlas-style monthly|Daily Hargreaves / PM|Nov–Mar Hargreaves / PM|
|---|---:|---:|---:|---:|---:|
|Cairo|2,160.3|1,744.8|1,766.7|80.8%|83.9%|
|Aswan|3,043.8|2,126.5|2,148.2|69.9%|71.2%|
|Hit|2,381.0|1,709.6|1,735.3|71.8%|77.1%|

November–March pools those Gregorian calendar months across the fixed period.
It is not the earlier field model's equal-bin five-month or fractional crop
window. Daily Hargreaves mean differences against PM are −1.137, −2.510 and
−1.838 mm/day, with RMSE 1.441, 2.969 and 2.603 mm/day respectively. These are
**method differences against a reference equation**, not measured prediction
errors or local yield validation.

The output retains 180 site/year/month rows, 15 annual rows and 36 monthly
climatology rows. It separates three effects rather than mixing them:

1. Daily Hargreaves minus PM on identical daily weather and FAO geometry.
2. Hargreaves on monthly mean weather minus the average of daily Hargreaves.
3. The unchanged atlas solar geometry applied to those same monthly inputs,
   minus Hargreaves with the average daily FAO extraterrestrial radiation.

The legacy solar function uses equal-bin midpoints, a cosine declination with
Earth tilt 23.44° and solstice day 355, and a circular-orbit approximation
without FAO's Earth–Sun distance factor. Its combined geometry effect also
contains the phase/bin convention. It is left unchanged. The chart shows that
aggregation/geometry effects are small compared with the method gap in these
snapshots; the audit does not attribute that whole gap to any single weather
variable or establish the correct ancient forcing.

## Verification

Before site ETo outputs, 159 controls passed (22 new and the existing 137).
The component reproduces FAO56 Example 18's rounded 3.9 mm/day at Uccle and its
reported intermediates within stated rounding/propagation tolerances, and
Example 8's 32.2 MJ/m²/day at 20°S/day 246. A separate scalar reference uses
standard-library solar angles and 40-digit Decimal pressure/radiation/ET
algebra. On 1,000 synthetic weather days / 18,000 cells, the largest difference
is 1.43e-14 in the retained quantity's units. It exercises vector/scalar shapes,
source units, clipping, signed raw ETo, invalid weather and unsupported domains.

The weather reviewer imports neither producer nor harvest component. It
reconstructs source dates, units, all raw values and QA flags; checks all
98,658 computed daily cells; independently computes every monthly/annual/
climatological statistic and the atlas-style geometry; and verifies source,
code and protected-file digests. Maximum PM difference is 1.43e-14 mm/day;
maximum aggregate numeric difference is 1.82e-12. Both fresh numeric files
(`results.json`, `daily.csv`) are byte-identical. All 920 protected files remain
unchanged, including earlier Earth-fit, daily water, rain-timing and crop-stage
numeric results.

The normal page retains all 39 displayed summary/month rows. Browser checks
cover six viewport/theme cases, 312 filter combinations, ten byte-checked
downloads including raw sources, an actual complete daily CSV download,
image loading, keyboard focus, page width and hub/evidence/return navigation.
The staged Windows-style checkout and release verification receipt is retained
alongside the numerical and publication receipts.

The frozen protocol's Chapter 4 locator includes Equation 52; that equation and
its Hargreaves regional-verification discussion are actually in Chapter 3.
Both chapters were pinned before capture. Results metadata corrects this
bibliographic locator; no source, equation or numeric method changed.

## Reproduce

```sh
# Full source/preflight reproduction before the weather producer:
python scripts/capture_reference_eto_sources.py
.venv/bin/python scripts/audit_reference_eto.py
# Freeze/stage source receipt and core proof before the producer gate.
.venv/bin/python scripts/reference_eto_weather.py
.venv/bin/python scripts/reference_eto_weather.py --out output/reference_eto_20261114/fresh
.venv/bin/python scripts/review_reference_eto_weather.py
.venv/bin/python scripts/publish_reference_eto.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_reference_eto_browser.py
```

The captured raw weather is tracked; the capture script reuses it without
replacing it with a new provider response. For a verification-only preflight
rerun, use `audit_reference_eto.py --out
output/reference_eto_20261114/core/fresh`: the canonical core receipt includes
test-runtime text and is pinned by weather results. Overwriting it intentionally
requires regenerating downstream provenance. FAO source caches restore against
protocol digests. The browser runner expects the repository served on port 8766.
After staging the final site, run `scripts/check_atlas_checkout.py --out
output/reference_eto_20261114/windows_checkout.json`.

## Implication for the programme

Do not use the three point ratios as multipliers on the regional field maps.
They are exposed development diagnostics on modern gridded weather. A next
regional forcing comparison needs a declared spatial/reference policy,
qualification of humidity/wind/radiation and period/grid representativeness,
and matched legacy-forcing controls before inspecting field effects. Greater
ETo changes crop demand and losses together; this audit does not infer a new
harvest or population result from the method differences alone.

Daily mean RH is not the daily minimum RH needed by FAO Equation 70, so no
field crop-coefficient climate adjustment is inferred from RH2M. Local
phenology, basal diffusion versus root uptake, canopy exposure/root development,
pond access/infiltration/drainage, Tigris, shared Earth/fantasy river flow and
independent regional evidence remain unresolved. Freeze any harvest translation
before Nile gain AND Mesopotamian non-inflation and whole-empire supply checks.

Current release-3 settlements and marketed share 0.3923 remain adopted:
850 self-fed, 174 importers, 29 short, 91% fed; reach staffing 1042. Egypt
calibration still fails. Actual occupancy/provider/size evidence, S3–S5,
complete resources/diets/work, mobile actors and political authority remain
separate open obligations. Reference-method agreement would not complete them.
