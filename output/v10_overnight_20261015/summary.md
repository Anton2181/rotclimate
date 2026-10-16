# Overnight four-layer Earth research

Status: complete. Stage: complete.
Completed cases: 215. Numerical failures: 3. Atlas updated: no.

Regional reanalysis wind, humidity and thermal profiles; shallow terrain return tested separately from deep storm ascent.
Observed temperatures remain forcing; Earth results cannot publish a fantasy atlas. Selection on California monthly rain MAE; other-region/weather/grid checks reported separately.

| Candidate | California 120 km MAE (mm/month) | Eligible | Years | Return | Humidity scale |
|---|---:|---|---:|---|---:|
| 5 | 59.94 | False | 4 | shallow | 1 |
| 120 | 64.00 | False | 4 | shallow | 0.8 |
| 138 | 64.27 | False | 4 | shallow | 0.8 |
| 74 | 64.49 | False | 4 | shallow | 0.8 |
| 86 | 65.15 | False | 4 | shallow | 0.8 |
| 89 | 65.25 | False | 4 | shallow | 0.8 |
| 80 | 65.56 | False | 4 | none | 0.8 |
| 16 | 65.71 | False | 4 | shallow | 0.8 |
| 124 | 68.03 | False | 4 | none | 0.8 |
| 6 | 68.06 | False | 3 | shallow | 1 |
| 22 | 68.13 | False | 4 | shallow | 0.8 |
| 40 | 68.24 | False | 4 | deep | 0.8 |
| 110 | 68.99 | False | 4 | deep | 0.8 |
| 134 | 69.17 | False | 4 | none | 0.8 |
| 21 | 69.34 | False | 4 | shallow | 0.8 |
| 41 | 69.50 | False | 4 | none | 0.8 |

Eligibility requires settling, budget closure, temperature departures <=5/10°C (lower/upper), annual rain ratio 0.5–1.75, >=80% coverage of observed non-arid land, and p99 rain <=4× observed. These are declared development screens, not independent uncertainty estimates. Diagnostic cases are labelled in the data.

## Transfer, weather and finer-grid checks

| Case | MAE (mm/month) | Eligible | Settled |
|---|---:|---|---|
| c000_iberia_g120_s41 | 48.38 | False | True |
| c001_iberia_g120_s41 | 35.76 | False | True |
| c002_iberia_g120_s41 | 46.31 | False | True |
| c003_iberia_g120_s41 | 42.47 | False | True |
| c004_iberia_g120_s41 | 41.78 | False | True |
| c005_iberia_g120_s41 | 33.80 | False | True |
| c006_iberia_g120_s41 | 39.44 | False | True |
| c007_iberia_g120_s41 | 40.76 | False | True |
| c008_iberia_g120_s41 | 38.61 | False | True |
| c009_iberia_g120_s41 | 41.27 | False | True |
| c010_iberia_g120_s41 | 43.39 | False | True |
| c011_iberia_g120_s41 | 38.58 | False | True |
| c012_iberia_g120_s41 | 40.86 | False | True |
| c120_california_g60_s41 | 71.12 | False | True |
| c120_california_g60_s73 | 71.11 | False | True |
| c120_california_g60_s109 | 71.20 | False | True |
| c120_iberia_g60_s41 | 40.90 | False | True |
| c120_iberia_g60_s73 | 40.78 | False | True |
| c120_iberia_g60_s109 | 41.03 | False | True |
| c138_california_g60_s41 | 71.18 | False | True |
| c138_california_g60_s73 | 71.29 | False | True |
| c138_california_g60_s109 | 71.32 | False | True |
| c138_iberia_g60_s41 | 40.89 | False | True |
| c138_iberia_g60_s73 | 40.79 | False | True |
| c138_iberia_g60_s109 | 41.07 | False | True |
| c074_california_g60_s41 | 71.23 | False | True |
| c074_california_g60_s73 | 71.62 | False | True |
| c074_california_g60_s109 | 71.55 | False | True |
| c074_iberia_g60_s41 | 41.34 | False | True |
| c074_iberia_g60_s73 | 41.10 | False | True |
| c074_iberia_g60_s109 | 41.22 | False | True |
| c086_california_g60_s41 | 71.64 | False | True |
| c086_california_g60_s73 | 71.91 | False | True |
| c086_california_g60_s109 | 71.08 | False | True |
| c086_iberia_g60_s41 | 41.28 | False | True |
| c086_iberia_g60_s73 | 40.94 | False | True |
| c086_iberia_g60_s109 | 41.15 | False | True |
| c089_california_g60_s73 | 72.16 | False | True |
| c089_california_g60_s109 | 71.73 | False | True |
| c089_iberia_g60_s41 | 40.99 | False | True |
| c089_iberia_g60_s73 | 40.86 | False | True |
| c089_iberia_g60_s109 | 40.93 | False | True |
| c080_california_g60_s41 | 72.29 | False | True |
| c080_california_g60_s73 | 72.27 | False | True |
| c080_california_g60_s109 | 71.77 | False | True |
| c080_iberia_g60_s41 | 42.14 | False | True |
| c080_iberia_g60_s73 | 41.86 | False | True |
| c080_iberia_g60_s109 | 42.03 | False | True |
| c016_california_g60_s41 | 72.50 | False | True |
| c016_california_g60_s73 | 72.25 | False | True |
| c016_california_g60_s109 | 72.89 | False | True |
| c016_iberia_g60_s41 | 41.58 | False | True |
| c016_iberia_g60_s73 | 40.99 | False | True |
| c016_iberia_g60_s109 | 41.96 | False | True |
| c124_california_g60_s41 | 75.19 | False | True |
| c124_california_g60_s73 | 75.88 | False | True |
| c124_california_g60_s109 | 76.02 | False | True |
| c124_iberia_g60_s41 | 43.76 | False | True |
| c124_iberia_g60_s73 | 43.19 | False | True |
| c124_iberia_g60_s109 | 43.78 | False | True |

## Numerical failures
- c098_california_g120_s41: Bounded column step count exceeded.
- c122_california_g120_s41: Bounded column step count exceeded.
- c089_california_g60_s41: Bounded column step count exceeded.

Full settings, frozen input/code hashes, monthly resume points and case budgets are retained beside this report. A budget stop is a resumable partial experiment, not completion of every planned check.
