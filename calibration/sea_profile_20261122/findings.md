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

## e98 stage 0: sst_offset -1.23, sst_damping 0.83 (full at 55 deg); WOA RMSE 1.58 (N 1.97, S 1.18)
## e98 stage A: S49 1.097 (T +8.7 %, P +10.7 %) -> stage B (under the 1.10 stop)
Better: BC coast T 3.48->2.80, Sahel 2.12->1.47, Mexico 1.46->1.16, Anatolia/Levant rain, N Queensland rain.
Worse: mid-latitude coasts too warm and too wet with the warmer sea (W Europe rain bias +98->+438 mm,
California +95->+371, Cape, Victoria, E Australia, Iberia; SW Australia T 0.70->1.78). The hot tail barely
moves (cell-months obs >=30 C: -3.0 -> -2.8): the sea is not the main cause of the hot land's cold bias.

## e98 stage B (joint_refit, 39 evaluations): best S49 1.082 (T +7.2 %, P +9.2 %): FAIL dev gate (<= 0.995). Not adopted; r50 stays.
The observed sea breaks the land and rain settings fitted around the cold sea (offset -4.4); the declared
temperature-only refit recovers just 0.015. A sea fix needs a joint rain + land refit at a scale (100s of
evaluations) or a new campaign; parked. Sealed set q unopened.
