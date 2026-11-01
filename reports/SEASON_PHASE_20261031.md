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

## 5. Warm currents mostly in winter (e66, opt-in, not adopted)

The model's British seas swing 4.0–17.3 °C against WOA18's 8.2–15.0. e66
(`warm_current_seasonality` k) scales the warm current anomalies by
(1 − k s), s = +1 at the lagged mid-summer, −1 at mid-winter: the North
Atlantic Drift's heat reaches the surface through the deep winter mixed
layer. Screens `output/warm_current_20261031` (default bit-identical):

| run | S | T | P | British Isles | western Europe |
|---|---:|---:|---:|---:|---:|
| k 0.5 | 1.0100 | +0.2 % | +1.8 % | 1.103 | 1.101 |
| k 1.0 | 1.0262 | +1.0 % | +4.2 % | 1.274 | 1.294 |
| k 0.5 + e65 0.5 + continental_mean 7 | 0.9943 | −2.9 % | +1.8 % | 1.052 | 1.066 |

At k 1.0 the British seas invert (13.6 °C in December, 6.8 in May: the
subpolar drift adds ~9 °C, so the right k would be ~0.3), but the land gets
worse at every k: its seasonal swing falls from 0.99 to 0.85 (k 0.5) of the
observed and its phase moves later (+32 → +35 days). The British land air
had the right swing only because a sea swinging twice too far drove it; the
land itself follows the sea too closely (the "maritime lag" of HANDOFF.md).
Mending the sea alone exposes that. Kept off; it belongs with a land surface
that answers more to its own sunshine.

## 6. The frozen refit (not adopted)

`calibration/land_ice_refit_20261031` (plan frozen before any result): 45
candidates (the search stopped there), best cost 0.9901, candidate 29:
`ebm_land_ice` 0.33, `continental_mean` 7.31, `continentality` 0.56,
`continental_depth` 0.31, `snow_albedo` 1.34, `land_offset` −0.68.

Validation (`scripts/validate_monsoon_refit.sh`, fresh paired runs against
r40; `output/land_ice_20261031/refit/validation.json`):

| check | result |
|---|---|
| dev31 S | 0.9843 (T −3.0 %, P +0.1 %) |
| training / holdout / mid-latitude / dev12 | **1.0029** / 0.9987 / 0.9645 / 0.9793 |
| retired sealed six (development data) | 0.9441 |
| 28 km paired S | 0.9926 |
| sealed set b | not run (the dev gate failed first; the set stays unseen) |

It fails policy v2 on the training group alone: East China's temperature
worsens 5 % (its spring was already too warm and a lighter band snow warms
it), Iberia 1 %, Central Asia 0.7 %. The US Midwest's temperature worsens
9 % inside a mid-latitude group that improves 3.5 % (Pacific NW 0.93,
eastern Europe 0.93, Manchuria 0.93, western Europe 0.98). Nothing is
adopted; the atlases keep r40. e65 stays in the code (off). What blocks it is
the subtropical east-coast spring (East China, and Japan in the holdout),
already too warm, which any warmer land column worsens. The next physics step
there is the East Asian spring itself, not the band's snow.

## 7. East Asia's spring: what the warmth is not

East Asia's springs are 3–4 °C too warm (r40, April: Korea +3.4, Japan
+3.5, East China +4.1 °C; autumns +2), the blocker of the e65 refit and of
earlier ones. Previous sessions blamed the shelf seas. Swapping in
observations (`scratchpad ea_obswind.py`; the existing diagnostic switches
`sst_source` and `wind_source`):

| run | Korea Apr / May | Japan Apr / May | East China Apr / May | British Isles MAE |
|---|---|---|---|---:|
| r40 | +3.4 / +4.0 | +3.5 / +3.6 | +4.1 / +2.8 | 2.46 |
| WOA18 sea surface | +2.9 / +4.0 | +3.3 / +4.0 | +4.2 / +3.1 | — |
| NCEP surface winds | +3.2 / +4.0 | +3.3 / +3.7 | +4.3 / +3.3 | 2.04 |
| both | +2.9 / +4.0 | +3.6 / +4.3 | +4.3 / +3.3 | **1.26** |

* **Not the sea and not the circulation.** With the observed sea and winds
  together the spring warmth stays (the British Isles' error halves).
* **Not the seas' own error, though that is real.** e67
  (`continental_sea_air`: the sea follows the lagged air over it in
  proportion to that air's continental share; opt-in, off) puts Korea's seas
  right (March 9.7 °C against WOA18 10.3; r40 13.5) but leaves the land's
  spring where it was, and cools the Baltic and North Sea enough to hurt
  eastern Europe (S 1.0009–1.0113; `output/continental_sea_20261031`).
* **Not the lapse rate.** Korea's April bias is +3.2 to +3.8 °C at every
  elevation band from the coast to 1,000 m.
* **Cloud shading helps only East China.** e4 `cloud_radiation` 2–6 against
  the globe's land cloud (`cloud_reference` "earth"): East China improves to
  0.93 of its error (April +3.4 at 4), Korea and Japan do not move (April
  +3.3), East China's summer cools 1.5 °C too far (its modelled summer is too
  wet and cloudy), and Mexico, Texas and the US south-east worsen (S 1.004 at
  2, 1.029 at 6).

What is left is the land's own spring energy balance: the springs of East
China, Korea and Japan are among the cloudiest and wettest of the
mid-latitudes (the spring persistent rains south of the Yangtze, the frontal
rains ahead of the Meiyu and Baiu), and the model's spring rain there is
0.5–0.7 of the observed (Japan 0.62–0.65, East China 0.54–0.70). The
missing piece is spring frontal rain and cloud along the East Asian coast,
which in the real atmosphere the westerly jet's passage around and over the
Tibetan Plateau organises. That is rain-making physics, not sea or winds.
The sea-surface diagnostic now records the sea surface each step actually
uses (`ClimateModel.sst_record`), so terms applied after `ClimateModel.sst`
(upwelling, e64, e67) are included.

### Where the model puts the spring storms

The storm field (the lift and the eddy exchange of heat and water) is a
Gaussian band around the planet's mean storm-track latitude: about 41 °N in
January and February, 44.6 °N in April, 47.7 °N in May, 52 °N in July and
August (width 14.7°). East coasts get only a secondary band, scaled by
`storm_asym` (0.30), shifted equatorward by `storm_reach` (4.7°), on top of
the main band. In April East China (29 °N) sits at 0.3 of the storm field's
peak, where in the real atmosphere the East Asian jet and its frontal rain
stay at 30–35 °N until late May or June (the land-sea contrast and the
Tibetan Plateau hold them there; the "seasonal jump" north comes with the
Meiyu's end). Screens of the existing switches do nothing: `storm_reach` 8
and 12 give S 1.0001 and 1.0009, East Asia unchanged; with `storm_asym` 0.5,
S 1.0107. A storm track that follows the model's own baroclinic zone (the
latitude of the strongest north-south temperature gradient, smoothed over
~2,000 km along the latitude) would put it there in spring and let it jump
north in summer; that is the next physics change to design, freeze and test.
