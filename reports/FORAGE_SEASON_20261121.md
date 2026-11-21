# Forage-growth season vs observed plant productivity: Earth test, 21 November 2026

**Outcome: adopted.** The seasonal forage weights used by the pasture maps and the herding circuits change to:
- temperature floor 0 °C and span 20 °C (was 15 °C);
- rain half-saturation 100 mm (was 50 mm);
- rain averaged over the current and previous month.

Protocol: [plan](../calibration/forage_season_20261121/plan.json), declared before any score.

- **Target:** FLUXCOM-X monthly GPP at 0.5°, averaged over 2001–2021 (ICOS, CC BY 4.0).
- **Model input:** WorldClim.
- **Split:** blocks of 2.5°, divided by a 10° checkerboard offset by 5°.
- **Variants:** 72, chosen on the development half.

| Blind half (425 blocks) | Current | Adopted |
|---|---:|---:|
| 12-month cycle correlation, median | 0.837 | **0.890** |
| lower quartile | 0.508 | 0.547 |
| Peak month within ±1 | 61 % | 67 % |

Gates:
- **V passes:** the current proxy was already supported.
- **G1 passes:** +0.054 against the +0.03 required.
- **G2 passes.**

Figure: [reports/figures/forage_season_20261121.png](figures/forage_season_20261121.png).

What changed and what remains:
- The adopted weights stretch the growth season and follow the lagged rains. The Sahel no longer greens a month early, and Anatolia loses its false autumn flush.
- The remaining misfits are irrigated winter-crop land (Nile, Mesopotamia, Indus–Ganges rabi wheat) and true desert. FLUXCOM includes crops, which this rain-fed proxy cannot and should not follow.
- The annual budget (Miami NPP) was not tested.

Wiring: `harvest/pasture.py seasonal_forage` gains `rain_memory`, and `data/pasture_model.json` phenology is updated. Both are applied at the bundled rebuild, together with the runoff rule. The blind run has been done once.
