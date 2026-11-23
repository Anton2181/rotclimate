# East Africa / Somalia rain (24 Nov 2026), r52

Largest single rain error in any benchmark region: s_2n_43e (southern Somalia, S18, spent) simulates ~3,800 mm/yr
against ~460, raining ~500 mm/month May-Oct when observed is 13-30. Southern Tanzania (t_8s_36e) and Zambia
(r_14s_32e) rain 157 and 62 mm/month through their dry seasons against 7 and 2.

Note: southern regions are run mirrored into the northern hemisphere with months rolled by six (earth.py:207);
their cell lat fields are positive by design.

## Cause found (Somalia)
zonal_wind: in July the region sits between the equator and the ITCZ (phi_i ~19 N), where e55 turns
cross-equatorial air westerly (the Somali jet) with weight monsoon_westerly x clip(poleward pressure fall /
monsoon_pressure_hpa). On the 2,500 km region map the poleward fall is ~0 hPa / 1000 km (Arabia and India,
whose heat lows draw the jet, are off the map), so the turning is off and the trades blow onshore at 8 m/s.
This is a limit of regional Earth cases: on the full world map the model sees its own heat lows.

## e109 monsoon_westerly_floor (minimum turning share), screened on the v5 pool
| floor | S61 [90 %] | T | P | S49 |
|---|---|---|---|---|
| 1.0 | 1.0253 [1.007, 1.046] | +1.8 % | +3.3 % | 1.017 |
| 0.5 | 1.0038 [0.999, 1.010] | +0.7 % | +0.1 % | 1.000 |

Somalia rain loss 3.90 -> 2.75 (floor 1) but still ~300 mm/month in JJA: the turned wind nets to ~0 with the
pressure-driven flow, and land evaporation stays ~70 mm/month year-round (recycling sustains the rain).
Losses: Algeria-Sahara (rain loss 0.18 -> 0.52), the Sahel (t_13n_7w), east China, coastal Ecuador / Peru.
The pressure gate is doing real work where the heat low IS on the map. PARKED (default 0).

## Leads
- Land evaporation in semi-arid tropics stays near potential (~70 mm/month at Somalia) even where observed
  rain is ~40: a soil-moisture limit on E may be the stronger lever.
- A larger map for coastal regions whose circulation is driven from beyond 1,250 km would test the domain
  explanation directly (Earth-calibration only; the world map has no such cut).
