# Rain triggers (owner chose this first, 27 Nov 2026): over-wet Somalia / Sahara edge, over-dry Kalahari / inland Australia

## Probe 1 (r58, existing options; five regions; development only)
| probe | Somalia loss | Sahara (u_21n_21e) | north India | Kalahari | NW Australia |
| base (r58) | 3.584 | 1.686 | 0.491 | 1.080 | 1.043 |
| e94 convective_descent 0.5 | 3.572 | 1.822 | 0.472 | 1.077 | 1.040 |
| e94 1.0 | 3.584 | 1.686 | 0.491 | 1.080 | 1.043 |
| e94 1.0, ref 0.25 | 3.586 | 1.670 | 0.492 | 1.080 | 1.044 |
| e84 instability_cap 0.8 (chi0 0.4) | 3.631 | 1.724 | 0.500 | 1.079 | 1.043 |
Reading: the Earth monsoon-descent field (g.descent) is ~0 over the Horn, so e94 cannot act there; the land-crossed
cap does not either. Raw: probe1.txt.

## Diagnosis carried over (calibration/rain_closure_capture_20261127, instability_consolidation_20261127)
Somalia's excess is both base (RH-driven, rh_threshold 0.32) and exponential convection; with observed winds and
SST the base rain is still ~4.9 mm/day vs < 1 observed. Removing the warm-moist boost (instability 0) helps Somalia
33 % but hurts north India 11 %.

## Plan (to be declared step by step, nothing run yet beyond probe 1)
Hypothesis: a weak-temperature-gradient (WTG) trigger. Tropical free-tropospheric temperature is nearly uniform and
set by the warmest convecting seas (Sobel & Bretherton 2000); deep convection needs near-surface moist static energy
above the saturated MSE of that free troposphere, and large-scale rain needs ascent. A cool upwelled sea / strong
trade inversion (Horn, Sahara edge) then suppresses rain while the monsoon trough (India) keeps it.
1. Capture trigger state (near-surface T, RH, MSE, SST, dynamics, instability, base/exponential rain) in Somalia,
   Sahara, north India, Bengal, Sahel, Amazon, Congo, Kalahari, inland Australia under r58.
2. Declare 3-4 candidates (MSE-excess gate on the boost; ascent-gated base rain) with guards (north India, Bengal,
   Sahel, wet tropics no worse than 1 %; target Somalia / Sahara improvement), probe, then dev97 screen, refit, gates.

## Probe 2 (warm-moist boost start temperature instability_t0; same regions + Bengal, Sahel)
rain loss: Somalia 3.584 -> 3.215 / 2.771 / 2.935 / 2.660 (t0 24 / 26 / 26 + instability 5 / 27 + 6);
north India 0.491 -> 0.507-0.533; Bengal 0.554 -> 0.593-0.660; Sahel 0.408 -> 0.432-0.442; Sahara 1.686 -> 1.70-1.75;
Kalahari / NW Australia unchanged. Same trade-off as instability 0: temperature does not separate the Horn from the
monsoon, because the Horn's MODEL air and sea are themselves too warm (sea ~29 C vs WOA 25-26 in Jun-Sep; missing
monsoon upwelling). A trigger built on the model's own state cannot fix the Horn until that sea is right; the
upwelling / Somali-jet circulation is the root (cf. pressure_zonal_exterior, wind_sst_diagnostic).
