# r38: warmer winter seas, stable land air and the continental settings, searched together

2026-10-25. Plan frozen before any result: `calibration/stable_land_20261025/plan.json`.
Search: CMA-ES over 15 settings from r37 (`scripts/gate_calibrate.py`, 200 candidates, scored as
the gate scores). Gate: `scripts/gate_stable_land.sh`; outputs in
`output/stable_land_20261025/gate/`. Parameters: `calibration/local_accuracy_20261023/r38_params.json`.

## Why

The model's winter seas were 3–9 °C too cold (January: Black Sea −0.4 °C against 9, western
Mediterranean 6.2 against 14.7, off Portugal 9.6 against 15.0), and the land and rain settings had
been fitted around them. Warm sea air kept its warmth far inland because the land's winter coupling
was the slow radiative one. r38 adds the stable-land coupling (air warmer than the ground cools
toward it within days, e52) and deep winter mixing of the seas, and refits the sea, continental and
rain settings together.

## Search

200 candidates; the best (candidate 171) scored 0.9834 with no group worse. The best by S alone
earlier (0.9898) had failed the gate's group rule (holdout +2 %). Progress figure:
`output/stable_land_20261025/progress.png`.

## Gate (fresh r37 reference under the current source fingerprint)

| check | r37 | r38 | S | result |
|---|---|---|---|---|
| 31 development regions, monthly T MAE | 1.841 °C | 1.796 °C | | |
| 31 development regions, rain loss | 0.4569 | 0.4528 | | |
| gate score (policy v2) | | | **0.9834** | pass; every group better (training 0.988, holdout 0.997, midlatitude 0.971, dev12 0.980) |
| 28 km check (California, western Europe, Japan, New Zealand) | 1.986 °C / 0.4350 | 1.919 °C / 0.4364 | 0.9849 | pass (≤ 1.01) |
| sealed six (Norway, SE Africa, Caucasus, Yunnan, NE US, Tasmania) | 2.037 °C / 0.5054 | 2.003 °C / 0.4888 | 0.9752 | better |

Sealed six by region (T MAE r37 → r38): Norway 3.62 → 3.90 (worse), SE Africa 1.28 → 1.32, Caucasus
2.57 → 2.27, Yunnan 1.48 → 1.48, NE US 1.85 → 1.58, Tasmania 1.43 → 1.47; rain loss better in SE
Africa (0.70 → 0.62) and Yunnan (0.60 → 0.51), worse in Norway (0.52 → 0.56).

City rain (3,667 cities): annual median error 29 % → 27 %, within 25 % of the observed annual total
43.1 % → 46.7 %; closer at 1,907 cities, further at 1,305. North India's foothill towns stay the
worst (model ~150–200 mm against 1,400–2,400).

Sea surface against WOA18 (19 regions; reported, does not decide): monthly MAE 2.79 → 2.87 °C. The
search bought land accuracy with a slightly worse sea; the winter-sea bias it set out to fix was
traded against the continental settings rather than removed.

**Adopted as r38.** The Earth-fit atlas is being refitted on it (world settings only,
`calibration/map_world_r38`).
