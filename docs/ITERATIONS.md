# Improvement log

Each iteration is one cycle of: simulate, compare with the painted map, find
what is structurally wrong, then improve the physics, the scoring or the search.
Scores are the mean zone agreement (0–1) at the reference resolution (21 km
cells, 37 steps per year) unless noted. A frame of every iteration is in
`calibration/iterations/` and animated in `output/improvement.gif`.

| it | what changed | score | notes |
|---|---|---|---|
| it00 | Earth-like guess: prograde spin, 34 °N, 23.4° tilt, default physics | 0.170 | Nearly all desert or Mediterranean. The north is far too mild (coldest month +8 °C where the target wants below 0). |
| — | *bug fix:* Köppen dryness threshold was 10× too high | (0.134 → 0.178) | Not physics, just units. |
| — | *physics v1:* saturation from a smoothed column temperature | 0.170 | Coasts were wringing out all moisture in winter. |
| — | *target re-extraction* (after your feedback) | — | Strict paint-colour match, text refilled, enclosed gaps filled. The inferred brown NW area was dropped from cold-and-wet. |
| it01a | round 1 CMA-ES, prograde spin (200 evals) | 0.415 | Mediterranean, warm-wet and swamp work. Cold-dry and hot-dry fail. |
| it01b | round 1 CMA-ES, retrograde spin (220 evals) | 0.430 | The opposite: cold-wet, cold-dry and hot-dry work, but the west coast is dry. |
| — | *physics v2:* subtropical highs sink harder on one side of ocean basins (the side flips with spin) | — | The missing east–west asymmetry (on Earth, California is dry and the Carolinas are wet). |
| — | round 2: one calibration per scenario (spin × ocean/land west × ocean/land east) | 0.517* | *Prograde reached a high mean by making everything warm and wet (5,000+ mm/yr) while scoring 0 on all three cold or dry zones. That's a flaw in the objective. Stopped early. |
| — | *diagnosis:* the mean wind alone can't wet the coast the wind blows away from | — | Real mid-latitude storms carry moisture both ways (eddy transport, about 10⁶ m²/s). |
| — | *physics v3:* storm-track eddy exchange of heat and moisture | (0.431 → 0.454 with no retuning) | Warm-wet, Mediterranean and swamp all improve at once. |
| — | *physics v3:* mountains no longer squeeze out all upwind moisture | | Peak rainfall drops from about 10,000 to about 4,800 mm/yr. |
| — | *surroundings:* procedural off-map land (after your feedback) replaces stretched edges and rectangles | | The edge continues and fades, then fractal continents with a calibrated land fraction per side. Every candidate is scored on 3 random surroundings. |
| — | *objective:* balanced (half mean, half soft-minimum over zones) plus rainfall realism penalty | | No zone can be sacrificed any more. |
| — | *independent check:* hand-drawn river density vs model runoff (Spearman, never optimised) | | |
