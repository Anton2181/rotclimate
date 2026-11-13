# Earth calibration of grain supply: real harvests and the seasonal freight network

**Outcome.** The grain supply model now runs on the Roman Empire with the same
production, network and allocation code as the fantasy map. As declared, the
calibration **does not pass**: at the cited 270 km haulage limit the eastern
cities can never be 95% fed, and west and east need very different settings.
The cause is identified: the upstream harvest model gives Egypt less than half
its historical output. With Egyptian cities left out of the score (a post-hoc
check), the cited limit holds, west and east agree, and the fantasy setting
behaves like Rome: one third marketed feeds 88% of Roman city residents and
85% of fantasy ones. No fantasy parameter is changed.

Protocol: [plan](../calibration/settlement_supply_calibration_20261113/plan.json),
committed before any output.

![Fed share of Roman city residents by marketed share and haul limit](figures/settlement_supply_calibration_20261113.png)

## What was rebuilt

The inputs the pilot lacked are back, from public sources: WorldClim climate,
ETOPO relief, Natural Earth rivers and NCEP winds. Three recorded hashes match
(elevation, rivers, arable shares). The Earth harvest grid is a rebuild, not the
lost file: it reproduces the committed Roman people field to 0.35% in total, so
people still come from the committed field and only cereal energy and arable
share come from the rebuild.

## Earth and fantasy production agree

| | Roman Empire | Fantasy world |
|---|---:|---:|
| Rural surplus per rural resident (person-years of grain) | 2.15 | 2.2 |
| Grown as a share of cereal potential (600 field hours) | 57% | 53% |
| Urban share of people | 16.8% | 25.5% |

The field-work rule gives almost the same surplus per head on both, which is
the first direct evidence that the fantasy grain ledger is Earth-like.

## Declared test (all cities)

| Haul limit (road-km) | Fed at one third | Share needed for 95%: all | west | east |
|---:|---:|---:|---:|---:|
| 135 | 62% | not reached | not reached | not reached |
| 200 | 70% | not reached | 0.62 | not reached |
| **270 (cited)** | **78%** | 0.81 | 0.38 | not reached |
| 400 | 91% | 0.44 | 0.22 | 0.57 |
| 540 | 96% | 0.31 | 0.14 | 0.35 |

- **West/east agreement** is best at 540 km, the edge of the declared grid, and
  even there the two halves differ by a factor 2.5.
- **Transfer fails:** the western setting feeds only 53% of eastern residents.
- By the declared rules: the cited 270 km is not confirmed; one third counts as
  Earth-supported only at 540 km; the method is not transferable.

## Why: Egypt

| Region (270 km, one third) | Cities | Residents | Fed |
|---|---:|---:|---:|
| Egypt | 55 | 1.36 M | 22% |
| Greece and Balkans | 141 | 1.59 M | 71% |
| Italy | 406 | 2.44 M | 84% |
| Asia Minor | 121 | 0.90 M | 94% |
| Levant and Syria | 40 | 0.75 M | 99% |
| North-west provinces | 129 | 1.37 M | 100% |

Egypt was the empire's granary. The harvest model gives it a capacity of 2.3 M
people against a historical 4.5–5 M (`output/land_people/earth/regions.json`),
the only region where history exceeds the model twofold. So Egyptian cities
starve in the model and Rome loses its main supplier: Rome is 62% fed.

## Post-hoc: Egyptian cities left out of the score

| Haul limit | Fed at one third | Share needed for 95%: all | west | east | west/east |
|---:|---:|---:|---:|---:|---:|
| 200 | 79% | 0.63 | 0.62 | 0.65 | 0.96 |
| **270 (cited)** | **88%** | **0.42** | 0.38 | 0.47 | 0.82 |
| 400 | 99% | 0.28 | 0.22 | 0.31 | 0.70 |
| 540 | 100% | 0.21 | 0.14 | 0.23 | 0.61 |

Here west and east agree best at 200–270 km, the cited limit is inside the
declared 1.25 tolerance, and 95% feeding needs a marketed share of about 0.42.
This was not declared in advance and Egyptian cities still draw grain in it.

## What this means for the fantasy map

| Fantasy headline (sliding sizes, one third) | Residents fed | Towns short |
|---|---:|---:|
| Haul limit 270 km (current) | 85% | 41 |
| 400 km | 96% | 16 |
| 540 km | 100% | 1 |

- The current setting (one third, 270 km) is in line with Rome outside Egypt.
- Feeding 95% would take a marketed share of about 0.42, or a 400 km limit.
  Neither is adopted; this is an owner decision once Egypt is fixed.

## Limits

- One pool, already used in development, with an internal west/east check.
  Han China has no city sizes and cannot test this.
- The decisive Egypt exclusion is post-hoc.
- The least-work rule picks barley everywhere on Earth (it needs fewer hours),
  as the atlas rule prescribes; Roman farming was wheat-heavy.
- City sizes are areas times a density reading; 600 field hours covers listed
  field tasks only.
- No state grain fleet, no other foods, no shipping capacity.

## Next step

Fix Egypt in the harvest model (Nile flood irrigation gives it half its
historical output), then rerun this calibration unchanged. That is the single
change most likely to turn the declared test from fail to pass.

## Reproduce

```sh
# public inputs: WorldClim 2.1 5m (tavg,tmax,tmin,prec,elev), Natural Earth rivers, NCEP 1981-2010 surface winds
.venv/bin/python -I scripts/arable_slope_earth.py
.venv/bin/python -I scripts/land_people_earth.py --out output/land_people/earth   # then: git checkout output/land_people/earth/regions.json
.venv/bin/python -I scripts/settlement_supply_calibration.py
.venv/bin/python -I scripts/review_settlement_supply_calibration.py
.venv/bin/python -I scripts/settlement_supply_calibration_diagnostics.py --fantasy
```

The review recomputes production, the whole fed-share surface, the interpolated
thresholds and the decision rules; it passes. A fresh run reproduces the results
byte for byte.
