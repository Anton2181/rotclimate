# Detailed forest, stage 1: does farming clearing match Roman-period Europe? 16 November 2026

**Outcome: farming-driven clearing not adopted.** On Earth, clearing computed from the model's own population (people × food need ÷ grain yield) makes the AD 200 forest map *worse*: the fit sets the clearing to zero. The climate pattern alone matches well. A side result: the current layer has too much forest overall.

Protocol: [plan](../calibration/forest_detail_20261116/plan.json), declared before any result. One amendment (A1, before the blind run):
- Spearman is computed on rounded block means, because floating-point noise broke ties.
- The clearing grid was extended below its lower edge.

## Target

Zanon et al. 2018, pollen-based forest cover at 1750 BP (c. AD 200), on a 5 arc-minute grid.
- Area: 29–56° N, 11° W–43° E.
- 110,486 cells, scored as 0.5° blocks.
- Split: 5° tiles in a checkerboard.

This target is independent of the REVEALS data used for C1.

## Results (blind tiles, 1,535 blocks)

| Model | RMSE | Spearman | Mean predicted | Mean observed |
|---|---:|---:|---:|---:|
| Current layer (0.60 × climate potential) | 0.184 | 0.687 | 0.50 | 0.44 |
| Level refit (0.51 × potential) | 0.170 | 0.687 | 0.43 | 0.44 |
| Farming clearing (fit: k = 0, so identical to the level refit) | 0.170 | 0.687 | 0.43 | 0.44 |

Gates:
- G1 passes.
- G2 fails: farming clearing adds no rank skill, because its fitted strength is zero.

## Findings

1. **The climate pattern is right at regional scale.** Against Zanon, the potential ranks Europe's AD 200 forest with Spearman 0.69 (development 0.70). Against REVEALS at 1° it had none.
2. **The level is about 7 points too high.** A factor of 0.51 instead of 0.60 cuts blind RMSE from 0.184 to 0.170. This was not a gated model in the plan, so it is offered to the owner rather than adopted.
3. **The model's people are in the wrong places for clearing.** Within climate-saturated land, model density correlates *positively* with AD 200 forest (Spearman +0.37 on the development tiles). The density follows food capacity, which is highest in humid, forest-capable land. Roman-period clearing followed history: the Mediterranean, Gaul and Roman Britain. So a detailed map can draw its clearings from the model's towns and fields, but Earth does not confirm where those clearings fall at regional scale.

## Next

- **Stage 2 is a scenario.** A full-resolution layer can be drawn: fields cleared around the model's towns and farmland, wooded slopes and ridges, wet valley floors and the tree line. It would be labelled as untested for placement. Slope retention could be checked against modern tree cover, which is a separate test.
- **Owner decision:** whether to lower the layer to 0.51 × potential.

Reproduce: `.venv/bin/python -I scripts/forest_detail_earth.py dev` and then `blind`. The blind run has been done once.

## Stage 2: detailed woodland map (scenario)

`scripts/forest_detail_map.py` works at the full map resolution: 926 × 2000 pixels of about 1.8 km, on height map v2.1. It writes
`output/forest_detail_20261116/` (`woodland_mosaic_{raw,corrected}.png`, `forest_detail_*.png`, `detail_summary.json`).

**Regional amount.** It is held at the published layer's values in ~25 km neighbourhoods, which is the Earth-tested scale.

**Placement within each neighbourhood** follows a declared rule. It is not fitted and is untested on Earth:
- **Rural people** clear gentle land.
- **Towns:** each town clears about 1 ha per resident, taking the cheapest land nearby (distance × steepness), so clearings follow flat ground and valleys.
- **Slopes** keep woods.
- **Cold limit:** the warmth ramp is recomputed with a 6.5 K/km lapse onto the fine terrain, giving a tree line.
- **Wet valley floors** are flagged as wet woodland or marsh: flat land with large drainage area in a moist climate.
- **Woodland or open:** the mosaic marks each pixel as one or the other. The choice uses the local preference plus a little smooth, seeded noise, against a threshold that keeps each neighbourhood's share.

Corrected climate:
- Mean forest is 0.49 (same as the regional layer).
- 35% of land carries more than 60% forest, and 14% carries less than 10%.
- 1.9% of land is flagged wet.
- Forest correlates +0.39 with slope.

**Not yet published to the atlas.** This awaits the owner's choice of level (0.60 or 0.51) and whether to show the scenario.
