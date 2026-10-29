# Monthly rainfall progress and moisture-supply diagnosis

This snapshot is partial. No incomplete-month candidate error or pooled score is produced. The committed31-day scoring objective, masks and model parameters remain unchanged.

| Region | Branch | Days | Rain | Evaporation | Net import | Vapor change |
|---|---|---|---:|---:|---:|---:|
| north_india | wet | 15–30 | 1.0433 | 1.6623 | -0.9109 | -0.2920 |
| north_india | dry | 15–30 | 0.0000 | 0.0000 | -0.0790 | -0.0790 |

Rates are mm/day on fixed projection-area-weighted scoring footprints. For this liquid-only model, E=P−Δsoil and net horizontal column import=Δ(vapor+soil), with stores divided by interval length. Consequently P=E+import−Δvapor. This is a conserved-store diagnosis, not an independent source tracer or a rainfall-conversion efficiency measurement.

The wet India scoring area exports water while depleting its surface store. The dry branch has almost no rain there. Moisture delivery/circulation and land-surface supply warrant investigation before trying to fix rainfall by changing conversion coefficients. No unique causal attribution: starting water also changes thermal capacity, skin temperature and circulation. Missing terrain and nonlinear momentum remain plausible structural limitations, not demonstrated causes from this snapshot.

An environment restart interrupted the original India processes at wet day29 and dry day30. Every saved daily prefix was retained and checked against its hash and independent energy/water ledger. Three isolated one-day replay segments were retained, including a repeated wet replay after removing a CLI-global dependency. Both branches reproduce all10 subsequent checkpoint fields byte exactly. These segments add zero new Earth initializations; the two process interruptions are separately recorded. Original per-step histories before interruption were not flushed. They are unavailable rather than fabricated. All future daily checkpoints and continuation step histories are retained.

Recovery milestone41f77a71 was committed and pushed before the monthly workers resumed. The frozen model sources, forcing, calendar, time step, masks and objective remain unchanged. Reused regional summer tests are not independent global/annual validation. No recalibration, physical adoption, normal-atlas climate changes or claim of optimizer convergence.
