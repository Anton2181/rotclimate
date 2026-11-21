# Rain-fed cereal yield pattern vs GAEZ v4 low input: Earth test, 21 November 2026

**Outcome: the current response is validated; no change is adopted.**

Protocol: [plan](../calibration/crop_yield_gaez_20261121/plan.json), declared before any comparison.

- **Target:** FAO/IIASA GAEZ v4, low-input rain-fed attainable yield, 1971–2000, without CO2 fertilisation (wheat, barley).
- **Model input:** WorldClim at 0.5°, with the production crop response mirrored exactly (checked in the script) and the adopted margin factors.
- **Variants:** 54, chosen on the development half.

| Blind half (11,266 cells) | Current | Best on development (failure band 0.2–0.4) |
|---|---:|---:|
| Spearman, wheat / barley | 0.762 / 0.610 | 0.764 / 0.616 |
| Mean Spearman | 0.686 | 0.690 |
| Grows-or-not F1 | 0.787 | 0.819 |
| Level, model/GAEZ where both grow | 0.38 / 0.41 | 0.36 / 0.41 |

Gates:
- **G1 fails:** +0.003 against +0.03 required.
- **G2 passes.**
- **G3:** not needed.

Figure: [reports/figures/crop_yield_gaez_20261121.png](figures/crop_yield_gaez_20261121.png).

Notes:
- **Level.** The model's 1 t/ha ceiling for c.200 AD gives about 0.4 of GAEZ's modern low-input level. That is a period assumption; it was reported, not fitted.
- **Finding for a future declared test.** The model grows wheat and barley at full yield in the hot, humid tropics (Sahel and West Africa, South China), where GAEZ gives none. The declared grid only *raised* the temperature window. Impact is limited: there the crop mix chooses millet or rice.

The blind run has been done once.
