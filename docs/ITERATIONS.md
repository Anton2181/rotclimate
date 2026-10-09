# Improvement log

Each iteration is one cycle of: simulate, compare with the painted map, find
what is structurally wrong, then improve the physics, the scoring or the search.
Scores are the mean zone agreement (0–1) at the reference resolution (21 km
cells, 37 steps per year) unless noted. A frame of every iteration is in
`calibration/iterations/` and animated in `output/improvement.gif`.

Scores are given as *mean* / *bal* (balanced objective, which also penalises
unrealistic rainfall). For reference, round 1's prograde "winner" has a
balanced score of −0.32: it reached its mean by raining 3,500 mm/yr on the
median cell.

| it | what changed | score | notes |
|---|---|---|---|
| it00 | Earth-like guess: prograde spin, 34 °N, 23.4° tilt, default physics | 0.170 / bal 0.05 | Nearly all desert or Mediterranean. The north is far too mild (coldest month +8 °C where the target wants below 0). |
| — | *bug fix:* Köppen dryness threshold was 10× too high | (0.134 → 0.178) | Not physics, just units. |
| — | *physics v1:* saturation from a smoothed column temperature | 0.170 | Coasts were wringing out all moisture in winter. |
| — | *target re-extraction* (after your feedback) | — | Strict paint-colour match, text refilled, enclosed gaps filled. The inferred brown NW area was dropped from cold-and-wet. |
| it01a | round 1 CMA-ES, prograde spin (200 evals) | 0.415 / bal −0.32 | Mediterranean, warm-wet and swamp work. Cold-dry and hot-dry fail. |
| it01b | round 1 CMA-ES, retrograde spin (220 evals) | 0.430 / bal 0.09 | The opposite: cold-wet, cold-dry and hot-dry work, but the west coast is dry. |
| — | *physics v2:* subtropical highs sink harder on one side of ocean basins (the side flips with spin) | — | The missing east–west asymmetry (on Earth, California is dry and the Carolinas are wet). |
| — | round 2: one calibration per scenario (spin × ocean/land west × ocean/land east) | 0.517* | *Prograde reached a high mean by making everything warm and wet (5,000+ mm/yr) while scoring 0 on all three cold or dry zones. That's a flaw in the objective. Stopped early. |
| — | *diagnosis:* the mean wind alone can't wet the coast the wind blows away from | — | Real mid-latitude storms carry moisture both ways (eddy transport, about 10⁶ m²/s). |
| — | *physics v3:* storm-track eddy exchange of heat and moisture | (0.431 → 0.454 with no retuning) | Warm-wet, Mediterranean and swamp all improve at once. |
| — | *physics v3:* mountains no longer squeeze out all upwind moisture | | Peak rainfall drops from about 10,000 to about 4,800 mm/yr. |
| — | *surroundings:* procedural off-map land (after your feedback) replaces stretched edges and rectangles | | The edge continues and fades, then fractal continents with a calibrated land fraction per side. Every candidate is scored on 3 random surroundings. |
| — | *objective:* balanced (half mean, half soft-minimum over zones) plus rainfall realism penalty | | No zone can be sacrificed any more. |
| — | *independent check:* hand-drawn river density vs model runoff (Spearman, never optimised) | | |
| it02a | round 3 (balanced objective, 3-world ensemble), prograde | 0.451 / bal 0.302 | Good mean, but **hot-and-dry stays at 0.00** in every prograde run: with Earth-like spin the south-east is always on the moist side of the basin. |
| it02b | round 3, retrograde | 0.418 / bal 0.333 | Every zone partly met. Rainfall now realistic (median 964 mm, top 5% below 3,500 mm). Rivers ρ = 0.21. North still too mild, summers in the Mediterranean band too wet; the optimizer had switched subsidence off. |
| — | *physics v4:* lakes and small seas follow the land's temperature (and freeze) | | Northern bays and lakes were acting as 10 °C winter heaters. |
| — | *physics v4:* calibrated continental seasonality (land heat capacity) | (cold-dry 0.40 → 0.67 at 1.3× with no retuning) | The Earth-tuned energy balance was a few degrees too mild in continental winters. |
| it03 | round 4, retrograde, physics v4 (800 evals, 2-world ensemble) | 0.453 / bal 0.414 | It moved the map to 33 °N and raised the tilt to 34°, giving colder winters and hotter summers. Full 7 km render gives the same mean (0.454). But the map is too *Mediterranean*: Csa covers the west coast and the hot-dry south. |
| it04 | round 5, retrograde fine-tuning (3-world ensemble) | 0.495 / bal 0.443 | 45% of painted land now falls in its own zone (9% at it00). |
| — | *diagnosis:* the winter storm track is the same at every longitude, so wetting the west coast also waters the southern desert | — | Real storm tracks form off the warm-current coasts (Cape Hatteras, Japan), so one side of a continent is stormy all year and the other only in winter. |
| — | *physics v5:* storm track stronger, and reaching further toward the equator, on the warm-current side (which side flips with spin) | (warm-wet 0.38 → 0.44, swamp 0.39 → 0.42 with no retuning) | |
| it05 | round 6, retrograde, physics v5 (stopped early at 64 evals for the usage window) | 0.500 / bal 0.456 | About level with it04. The new storm-track asymmetry had not been tuned yet. |
| it06 | round 7, retrograde, physics v5 (480 evals, 3-world ensemble) | 0.522 / bal 0.487 | **53% of painted land falls in its own zone.** Hot-dry 0.59, cold-dry 0.50: the two zones that had been weakest throughout. Map centre 32.1 °N, tilt 32.6°. |
| — | *resolution check* of it06 at 21 / 14 / 11 / 7 km cells | 0.509 / 0.506 / 0.489 / 0.468 | Stable down to 14 km, then the threshold zones (cold-dry, hot-dry) drift as finer grids resolve terrain the calibration never saw. The published maps and atlas therefore use 14 km; the map layers are still drawn at 3× resolution with full-detail terrain. |
