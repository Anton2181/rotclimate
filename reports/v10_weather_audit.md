# Heat-transport result and the next weather diagnosis

**Access update, 15 October:** the user still receives HTTP 429 after waiting.
One fresh tiny annual-air metadata request reproduces the response, with no
Retry-After header. A public help-page HEAD returns 200; NOAA's documented
static-file HEAD also returns 200 and advertises byte ranges, but a bounded
64 KB range request times out before a response. No field data were downloaded.
This establishes an access failure at the requested subset endpoint, not its
precise cause or duration; overload versus client/network restriction cannot
be distinguished from the generic response. Waiting a few minutes is not a
verified remedy, and a working alternate reader has not been established.

Pause this reference audit for now. The separately prepared
[2.5-hour water-source batch](v10_water_sources.md) uses cached inputs and makes
no NOAA requests. Do not repeatedly restart the subset fetch or substitute
daily/monthly data for its six-hourly analyses. The official alternative
download path is documented in [NOAA's access help](https://psl.noaa.gov/data/ftp.html),
but full annual global files (the checked air file is 320,180,440 bytes) are
not a drop-in replacement for the bounded regional plan. Original scripts,
protocols and paused result remain unchanged. Small status-check evidence is
in `output/v10_pressure_review/noaa_access_check.json`; the range timeout is
recorded separately in `noaa_range_check.json`.

15 October 2026. The four user-run pressure-based heat-transport cases are
complete. Their immutable protocols, input arrays, configurations, annual
fields, settling checks and recomputed summaries agree. All settle after four
cycles; sixteen saved cycles took 16.67 minutes. The assistant analysed saved
fields only and did not start another climate integration.

## The correction did not fix the rainfall

| Region / winds | Monthly rain MAE, old → corrected | Corrected annual rain / reference | Skill against zero-rain MAE |
|---|---:|---:|---:|
| California / uniform | 41.66 → 40.07 mm | 473.3 / 401.8 mm | −19.7% |
| Iberia / uniform | 32.07 → 32.20 mm | 176.8 / 424.2 mm | +8.9% |
| California / spatial | 29.88 → 30.33 mm | 39.9 / 401.8 mm | +9.4% |
| Iberia / spatial | 34.91 → 35.02 mm | 22.2 / 424.2 mm | +0.9% |

Zero-rain skill is 1 − model MAE / zero-rain MAE on the same scored monthly
cells. Positive skill alone is insufficient: the spatial cases still receive
only 9.9% and 5.2% of reference rainfall. California's uniform case passes the
existing broad screen, but is worse than zero rain and wets the wrong places.
Its coast receives 387.1 mm versus 627.0 mm observed; its interior gets 338.0 mm
versus 252.8 mm. Iberia's uniform coast/interior receive 244.2/10.3 mm versus
661.1/86.6 mm observed.

The dry-law manufactured tests establish a local physical improvement. They
did not establish that this defect caused the regional drought, and the paired
annual results now show little benefit for rain. Keep the corrected transport
as a separate experimental implementation; do not promote these climates or
retune storm frequency in response to a marginal MAE change.

The water and declared energy ledgers close, including explicit prescribed-flow
work. Mean diagnosed work is 23.9/14.3 W/m² in the uniform California/Iberia
cases and 16.3/5.7 W/m² with spatial winds. This is exchange with an unsolved
prescribed circulation, not independent momentum/kinetic-energy closure.
Lower/upper-layer p95 temperature departures remain about 2.1–3.8°C / 6.0–9.9°C.

Detailed saved-field review:
[`output/v10_pressure_review/review.md`](../output/v10_pressure_review/review.md).

## Updated Köppen comparison

![Completed pressure-based Earth pilots and target Köppen zones](../output/v10_koppen_pressure/koppen_comparison.png)

| Region / winds | Exact class agreement | Desert BW share | Reference Mediterranean cells becoming arid B |
|---|---:|---:|---:|
| California / uniform | 38.7% | 55.0% | 46.4% |
| California / spatial | 28.6% | 88.8% | 84.1% |
| Iberia / uniform | 42.0% | 76.7% | 82.3% |
| Iberia / spatial | 36.2% | 96.9% | 98.5% |

These maps hold observed surface temperature fixed to isolate rainfall errors.
The target is classified from the same WorldClim 1970–2000 monthly fields, grid,
mask and project classifier; it is not a different published Köppen raster.
The regions include neighboring western US / Mediterranean / North African land.
The final settled model year repeats one synthetic weather catalogue, rather
than sampling a multi-decade climate. Warm-up cycles and neighboring cells are
not independent observations.

The [companion comparison and temperature sensitivity](../output/v10_koppen_pressure/comparison.md)
include full counts, confusion tables, source identities, arrays and vector
figures. The sensitivity adds the lowest-layer temperature anomaly to observed
surface temperature; it is explicitly a proxy, not predicted 2 m temperature.
Original pre-correction maps remain preserved. The fantasy atlas is unchanged.

## Next: measure real weather coupling before another model run

The current boundary humidity profiles and monthly wind backgrounds do not
carry the observed time-varying relationship between wind, moisture and
temperature. Synthetic vortices alone need not reproduce it. This is an
unresolved hypothesis, not an established explanation of all missing rain;
internally transported model moisture can already covary with storms.

The [research strategy](research_strategy_20261015.md) calls for measuring
mean(q·v) − mean(q)·mean(v). The next audit implements that measurement before
introducing a new forcing mechanism or calibration parameter. It uses annual
[NCEP/NCAR Reanalysis 1 pressure-level analyses from NOAA PSL](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis/pressure/catalog.html),
not the monthly climatology used by the current prototype.

User-run command:

```sh
.venv/bin/python -u scripts/audit_v10_weather.py --fetch --run
```

This downloads and analyses reference data; it performs **zero climate
integrations or calibrations**. Expect several minutes if NOAA responds
normally, with network-dependent timing and a 30-minute invocation budget.
There are 56 sequential requests spaced at least three seconds apart: eight
small metadata files and 48 regional subsets. Each response is capped at 4 MB,
the declared reference cache at 96 MB. The same command resumes the verified
cache. On HTTP 429/503 it stops without immediate retry, reports any Retry-After
header and preserves completed downloads; rerun later rather than repeatedly
restarting while the server is busy.

The fixed protocol samples January and July of 1990 and 2000, each with 124
six-hourly observations, in the two existing marine upwind boxes. It uses
925/850/700/600/500/400/300 hPa temperature, **specific humidity**, and eastward/
northward wind. Native offshore selection checked on the unchanged cached
coordinate grids yields 14 California and 19 Iberia centers. Cosine-latitude
weights apply after computing temporal contrasts separately at every center;
the audit does not mix spatial covariance into the temporal term.

Outputs include:

- Pressure-integrated mean paired moisture transport, the product of separate
  temporal means and their covariance difference, for both wind components.
- The share of positive eastward transport carried by the top decile of
  eastward-transport samples, plus their 925 hPa humidity/temperature anomalies.
- Liquid-reference relative-humidity percentiles by pressure level and exact
  native sampling coordinates.
- Immutable source/protocol identities, source URLs, checksums, a result table
  and a transport comparison figure in `output/v10_weather_audit/`.

Only 925–300 hPa is integrated: this omits near-surface and upper transport.
Marine selection and omission of 1000 hPa reduce below-ground contamination,
but without instantaneous surface pressure cannot prove every remaining native
pressure sample is above the surface. These coarse reanalysis fields are
model-informed. Two years and two seasons are mechanism evidence, not climate
normals or independent validation. The marine-box flux is not a closed
boundary-import budget; top-transport composites do not identify cyclones; flux
does not by itself predict rainfall.

If covariance is substantial and its sign/seasonal structure is consistent
across these windows, the next justified prototype would replay **paired**
temperature/humidity/wind weather, preserving their timing. Compare against
the same records with variable timing deliberately separated, keeping their
individual distributions and means. First resolve mass/pressure consistency
and boundary treatment; do not insert annual reference winds into the current
fixed-column engine unexamined. This would test whether coupling changes rain
placement, rather than merely whether any new weather wets the map.

If the measured contribution is small or inconsistent, it will not justify a
large covariance-tuning sweep. Move to source-water accounting, vertical
quadrature, cloud conversion/fallout and event-scale transport instead. This
decision uses transport evidence, not an arbitrary percentage chosen to fit
the precipitation target. No new overnight parameter search is prepared now.

## Verification and current limit

Fifteen offline tests pass: time-window/leap-year slices, packed-unit decoding,
specific-humidity convention, date/product rejection, analytical positive and
negative covariance with identical means, zero covariance, exact cache resume,
corruption rejection, rate-limit handling, read-only defaults, and Köppen
calendar/mask/surface-proxy policy. All frozen production and earlier experiment
source identities match; completed heat-case evidence is verified.

Preflight is saved in
[`output/v10_pressure_review/weather_preflight.json`](../output/v10_pressure_review/weather_preflight.json).
A tiny live metadata request returned HTTP 429. **Live six-hourly array retrieval
has not yet been validated**; the reader stops on unexpected units, packing,
dates, coordinates or missing selected data. No audit cache or weather result
was generated by the assistant. The user-run command is the next live check.

NCEP/NCAR Reanalysis 1 data are provided by NOAA PSL, Boulder, Colorado, USA.
Fantasy Mediterranean/cold-dry/hot-dry safeguards and the validated atlas remain
in force; reference-driven Earth prototypes still need a fantasy forcing bridge.
