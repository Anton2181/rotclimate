# C1 sea profile — findings (22 Nov 2026)

## Stage 0 (EBM ocean fitted to WOA18 zonal SST)
| fit | RMSE N / S (C) | mean bias N / S | swing error N / S | values |
|---|---|---|---|---|
| r50 | 3.98 / 4.28 | -2.89 / -3.41 | +3.36 / +3.55 | capacity 1.4, seasonality 0.2, transport 0, offset -4.43 |
| existing knobs | 1.87 / 1.17 | +0.19 / -0.24 | -1.21 / -0.17 | capacity 4.37, seasonality 0.58, transport 0, offset +2.0 (bound) |
| + e97 | 1.77 / 1.07 | +0.29 / -0.17 | +0.67 / +1.04 | capacity 0.5, seasonality 0.8, polar 20 (3 at bounds), transport 0.22, offset +0.33 |
e97 improves the fit only 7 % (< 15 %): not carried.

## Stage A (r50 + the stage-0 sea, dev49 paired with r50): STOP (S49 1.281 > 1.10)
T +44.8 %, P +11.5 %. Land 2.05 C too cold on average (r50 -0.25), every month: the deeper EBM ocean
changes the energy balance's own land column, which sets the regional land background, so the warmer
regional sea did not warm the land. Lesson: correct the regional sea without touching the energy balance (e98).
