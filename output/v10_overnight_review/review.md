# Completed V10 overnight review

Finished in 6.15 hours: 215 completed cases, 3 failed cases, 944 completed years verified.
No original case qualifies. No 30/15 km refinement or atlas publication occurred.

## Rainfall and the unchanged acceptance rules

| Region, best-screen setting 120 at 60 km, seed 41 | Rain / reference | Rain MAE | Zero-rain MAE | Coverage |
|---|---:|---:|---:|---:|
| california | 2.00 | 71.12 | 33.48 | 54.6% |
| iberia | 0.78 | 40.90 | 35.35 | 65.3% |

Zero rain is an information-free error baseline, not an acceptable climate model. The shortlisted 60 km cases all have worse monthly rain MAE than this baseline. Thus correcting the temperature comparison alone does not rescue rainfall.

## The thermal screen also needs diagnosis

Old targets add each local surface-temperature anomaly to an offshore profile in every layer. The following comparison samples cached NCEP air at each local layer pressure instead. The unchanged old guards remain recorded; this is a separate exploratory reference audit.

| Reference-informed shallow control, 120 km | Old target error, lower / upper p95 °C | Local pressure-reference error, lower / upper p95 °C |
|---|---:|---:|
| california | 7.69 / 17.63 | 6.40 / 8.56 |
| iberia | 8.51 / 13.61 | 7.44 / 5.45 |

Do not infer that all 215 runs have a 10–18°C free-air error from their departure from the imposed targets. The spatial target construction exaggerates upper departures; lower-layer/reference errors and rainfall failures still remain.

## Three failures were clock remainders

- c098_california_g120_s41: rejected a 0.001474-second boundary remainder despite a 2160.00-second CFL allowance; scalar-only corrected clock completes the year in 14296 steps.
- c122_california_g120_s41: rejected a 0.005989-second boundary remainder despite a 3600.00-second CFL allowance; scalar-only corrected clock completes the year in 13594 steps.
- c089_california_g60_s41: rejected a 0.005069-second boundary remainder despite a 1350.00-second CFL allowance; scalar-only corrected clock completes the year in 26561 steps.

No atmospheric states were advanced in these probes. Failed physical cases remain failed in the original evidence. A new clock helper permits positive boundary fragments without discarding time; the old sources are unchanged.

## Next controlled experiment

Test replacing only the upper two temperature targets with spatial pressure-level reference temperatures. Keep setting 120, seed 41, 60 km inputs, geometry, winds, humidity and storms fixed; reuse the completed baseline in each region. Record signed horizontal/vertical thermal transport, relaxation, condensation heating and layer rain. Two new regional cases, no search or atlas publication. This tests the surface-temperature imprint and exposes the remaining rain mechanism without another broad sweep.

## Limits

- Local pressure-level reference is coarse 2.5-degree reanalysis, not independent station observations.
- Native terrain can differ; pressure-level products may contain below-ground extrapolation, especially for the lowest layer.
- Reference periods differ; temperature is observation-informed forcing, not an independent prediction.
- Local reference audit does not change historical eligibility, selection or acceptance rules.
