# Seasons that run late: shelf seas and the band column's snow, 31 October 2026

Climate work after the dry-heating refits (`reports/TRANSPORT_WIND_20261031.md`).
All runs: the 31 development regions at 56 km, scored against the adopted r40
(`output/summer_rain_20261030/r40_dev31`, identical cells to
`output/transport_wind_20261031/r40_dev31`). Screens are development data only;
nothing here touches sealed set b.

## 1. Shelf seas follow the air (e64, e64b; opt-in, not adopted)

East Asia's springs are 3–4 °C too warm and its shallow seas 5–7 °C too warm
in April–May (WOA18). e64 (`shelf_air_coupling`, `shelf_air_lag_days`) lets
the shelf share of each sea cell relax toward the air above it with a 45-day
memory; e64b (`shelf_air_enclosed`) limits it to enclosed shelves (the
Yellow Sea, the Bohai). Results `output/shelf_air_20261031`:

| run | S | T | P | worst regions |
|---|---:|---:|---:|---|
| e64 0.5 | 1.0059 | −0.1 % | +1.3 % | eastern Europe 1.072, Japan 1.054, western Europe 1.039 |
| e64 1.0 | 1.0281 | | | |
| e64 1.0, lag 20 d | 1.0166 | | | |
| e64b 0.5 (enclosed) | 1.0006 | −0.2 % | +0.3 % | eastern Europe 1.057 |
| e64b 1.0 | 1.0075 | −0.1 % | +1.6 % | eastern Europe 1.143 (summer rain 0.70 → 0.39 of observed) |

The coupling cools Korea's spring by 0.3–0.4 °C but leaves Manchuria's
temperature worse (2.09 → 2.17 °C monthly error); its gains are rain, and the
North Sea and the Baltic take the coupling too, drying eastern Europe's
summer. Not adopted; off by default. (The sea-surface diagnostic
`scripts/compare_sea_surface.py` hooks `ClimateModel.sst`, which runs before
e64 is applied, so it cannot show e64's own sea surface.)

## 2. The seasonal phase is late across the mid-latitudes

The first harmonic of each region's mean annual cycle (`phase` in
`output/season_phase_20261031`) peaks late in every maritime mid-latitude
region: British Isles +32 days, New Zealand +31, Patagonia +23, western
Europe +22, Pacific NW and eastern Europe +11, and early in the subtropics
(Levant −7, Japan −7, East China −7). Seen month by month it is a spring
too cold and an autumn too warm (British Isles April −4.3 / October +0.8 °C,
eastern Europe −3.7 / +0.9, Pacific NW −2.6 / −0.2, Alps −1.9 / +0.3).

What it is not:

* **The model's sea.** With WOA18 sea surface (`sst_source="observed"`) the
  British lag is still +23 days. The model's own British seas peak in August
  as WOA18 does, though they swing twice as far (4.0–17.3 °C against
  8.2–15.0).
* **The circulation lag or the ocean's heat capacity** (`circulation_lag_days`
  30: S 1.0055, no phase change; `ocean_heat_capacity` 1.0: S 1.022, later).
* **The land centre** (e28 `maritime_mean` 0.3–1.0: no phase change; S
  1.002–1.029, the subtropical west coasts cool toward their upwelled water).

What it is: **the latitude-mean land column's snow.** Every land cell's
seasons are the band column's anomaly scaled about a centre, and the column's
ice albedo depends on its own temperature: at 53° N its April is 4.3 °C
colder than its October (real interiors at 53° N: Novosibirsk −0.4,
Winnipeg −1.2, Moscow +1.5), so Britain inherits Siberia's snowy spring.
Without the column's land ice the asymmetry at 53° N falls to −0.8 °C.

## 3. e65: keep only a share of the band's seasonal snow (opt-in)

`ebm_land_ice` (default 1, unchanged) keeps that share of the column's
seasonal-snow albedo; land whose annual mean (last year's) is below −10 °C is
ice sheet or perennial snow and keeps all of it (a first version without
this guard stripped Antarctica's albedo and warmed the mirrored southern
regions). The cells' own degree-day snowpack albedo (e16 `snow_albedo`, 0 in
r40) can carry the snow where it lies.

| run (against r40) | S | T | P | train | holdout | midlat | dev12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ebm_land_ice` 0 | 1.0104 | +2.0 % | +0.1 % | 1.0134 | 1.0350 | 1.0333 | 0.9929 |
| 0.5 | 0.9927 | −1.5 % | 0.0 % | 0.9948 | 1.0142 | 0.9979 | 0.9840 |
| 0.5, `continental_mean` 7.0 | **0.9837** | −3.3 % | +0.1 % | 0.9982 | 1.0049 | 0.9691 | 0.9765 |
| 0, `continental_mean` 10.5 | 0.9852 | −3.8 % | +0.8 % | 1.0303 | 1.0141 | 0.9343 | 0.9748 |

At 0.5 the Alps, Pacific NW and eastern Europe improve by 9–12 % and the
British Isles by 5 %, but the warmer column also warms East Asia and the US
Midwest, which were already too warm; the cold-air pool (e31
`continental_mean`, which lowers the centre where poleward land's winter air
can drain) takes them back (Manchuria 2.09 → 1.95 °C). Figure:
`output/season_phase_20261031/season_bias_e65.png`.

## 4. Frozen refit

Plan `calibration/land_ice_refit_20261031/plan.json`, committed before any
search result: start r40 with `ebm_land_ice` 0.5 and `continental_mean` 7.0;
CMA-ES over the column's snow share, the cold-air pool, continentality,
continental depth, the cells' snowpack albedo and the land offset (56
candidates), the retired sealed set as an extra guarded group; validation by
`scripts/validate_monsoon_refit.sh` (fresh paired dev31 under policy v2, the
paired 28 km check, then sealed set b once).
