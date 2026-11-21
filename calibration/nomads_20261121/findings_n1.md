# T9 N1 pastoral nomads — ADOPTED (21 Nov 2026)

Plan: plan_n1.json (declared before fitting). 632 Ethnographic Atlas societies with EA004/EA005/EA030 in the two Earth runs;
48 pastoral nomads (EA030 nomadic or seminomadic and herding dominant). 5-fold 10-degree-tile cross-validation.

| model | out-of-fold AUC | log loss |
|---|---|---|
| **P0 herding share** | **0.920** | 0.163 |
| P1 + ln(P/PET) | 0.928 | 0.165 |
| P2 + temperature, growing season | 0.924 | 0.164 |

P0 chosen (simplest within 0.01 of the best). On Earth, almost every herding-dominant society is nomadic or seminomadic
(44 of 49 with a known settlement pattern), so nomadism follows the herding share.

On the map (layer "Pastoral nomads", raw and corrected; scripts/nomads_layer.py, wired into the release after the herding
layer): the mean chance is 1.5-1.6 %; the maximum is about 0.30 (eastern plateau, southern dry country), no land reaches
0.5. The map's driest land still has a ~55-day growing season (herding share 0.50 at most); Earth's nomad belts (Sahel,
Arabia, Mongolian steppe) sit below that. So by the Earth calibration the continent has semi-arid herding margins with
some transhumance, not open steppe or desert nomad country.

Consequence for N2-N4 (nomad density, circuits, steppe confederations): little to model on this map; deferred unless the
owner wants nomad zones (which would need a drier climate or a lore override).
Claude copy v22: 85 layers x 2 climates load.
