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
| — | *hydrology:* runoff routed downhill (priority-flood drainage) into river discharge | — | **Independent validation:** the simulated big rivers (> 20 m³/s) land on your drawn rivers: 87% of drawn river cells lie within one cell of a simulated river, and 53% of simulated big-river cells lie near a drawn one. The model never sees your rivers. |
| — | *tested and rejected:* letting river floodplains count as "swampy" | (would lift swamp 0.28 → 0.49) | In the model the painted swamp coast is no more river-fed than other lowland (floodplain share 0.21 vs 0.21), so it would only have loosened the rule. Not adopted. |
| it07p | **fairness check:** Earth-like spin with the same physics v5, objective, 3-world ensemble and 400-eval budget as round 7 | 0.448 / bal 0.343 | Best balanced 0.336 in calibration vs 0.493 for retrograde. Hot-and-dry stays at 0.09 again, as in every prograde round, though Earth-like spin does reproduce the swamp (0.74). The spin finding holds on equal footing. (`it07p` is a comparison frame, not the published map.) |
| — | *diagnosis:* why the swamp falls short | — | It is hot enough, and summer rain matches the warm-wet coast. The deficit is winter rain (2.7 against about 4 mm/day), which leaves it just under the "very wet" line (1,270 mm/yr against about 1,290 needed). The swamp lies at 27–31°N in the (reversed) mid-latitude easterlies, downwind of the dry interior, facing a gulf hemmed in by the land the calibration had put beyond the south edge. |
| — | *physics v6:* moist instability (rain forms faster over hot, moist ground, as in tropical convection) | (no change to the swamp with no retuning) | Kept as a calibrated gene; round 9 set it near zero (0.07). |
| — | *surroundings v6:* the north and south edges can differ between their west and east halves | (with the whole south edge opened: swamp +0.07, hot-dry −0.21) | Lets the calibration open the sea toward the swamp while keeping land behind the south-eastern desert. |
| it08 | round 9, retrograde, physics v6 (400 evals, 3-world ensemble) | 0.557 / bal 0.526 | **14 km render: mean 0.532, bal 0.483** (round 7 re-scored the same way: 0.504 / 0.461); 54% of painted land in its own zone. Mediterranean 0.49 → 0.65 and cold-wet, cold-dry and tree all improve; swamp 0.39 → 0.43; hot-dry falls 0.54 → 0.42. The south edge splits as expected (south-west 91% land, south-east ~100%), but the swamp's gain from the open south-west is small: closing it again moves only 0.03 from swamp to hot-dry. Map centre 31.6°N, tilt 33.1°, lower and flatter lowlands (lowland ≤ 104 m). *Superseded: these scores were flattered by the time-step artifact below.* |
| — | *found:* why every published map scored below its calibration (swamp 0.43 → 0.31) | — | Not the grid: at 14 km with calibration's 25 steps a year the swamp scores 0.42, and at 28 km with 73 steps it scores 0.28. Not numerical mixing either (adding back the coarse grid's upwind diffusion changed nothing), and not soil-moisture memory. It was temperature: each step took its storm-eddy mixing and thermal winds from the *previous* step's temperature. With 15-day steps that lag acted like a slow filter that added about 2.6 °C of winter warmth along the gulf, and the calibration had learned to rely on it. |
| — | *fix:* temperature and winds are iterated within each step until nothing moves by 0.05 °C (about 9 passes, 1.4× the cost); soil-moisture memory and spin-up are set in days | (round 9 re-scored: 0.508 at 28 km / 25 steps, 0.511 at 14 km / 73 steps) | Calibration and the published maps now see the same climate. The swamp's honest score with round 9's settings is 0.24: winters there are colder (5.5 °C) and drier than the artifact suggested. |
| it09 | round 10, retrograde, converged-temperature physics (480 evals, 3-world ensemble, 28 km) | 0.523 / bal 0.496 | **Swamp 0.51** (it is reproduced for the first time with honest physics). The moist-instability gene now matters (0.43), with more convective rain and weaker subtropical sinking. Hot-dry falls to 0.38. At 14 km the swamp holds (0.52) but hot-dry falls to 0.28 (bal 0.445, a tie with round 9 re-scored). |
| — | *diagnosis:* why the dry zones get wetter on finer grids | — | Not elevation (the desert's terrain mix is the same at every grid) and not convergence or upslope rain (widening their smoothing changes nothing). Water is: finer grids resolve small lakes and narrow seas that coarse cells round to land, and their evaporation waters the land downwind. Filling the lakes recovers most of cold-dry's loss (0.43 → 0.52) but not hot-dry's, which sits beside a sea connected to the ocean. These are real resolution effects, so the next round calibrates at the published 14 km directly; since the time-step fix, 25 steps a year give the same climate as 73, which keeps that affordable. |
| it10 | round 11, retrograde, refined at the published 14 km (192 evals, 3-world ensemble) | 0.503 / bal 0.477 | **Published map: mean 0.506, bal 0.485** (round 7 as published: 0.504 / 0.461). Every zone between 0.40 and 0.79: swamp 0.48 (was 0.28), hot-dry 0.42, cold-wet 0.40 (was 0.61). 46% of painted land falls in its own zone (54% before): with every zone partly met, the single best zone flips more often. Map centre 34.1°N, tilt 26.2°. |
| — | *found:* the zone score never penalised a rule holding where you painted something else | — | Round 11 met the swamp rule in half the painted swamp, but also across the lowland warm-wet, Mediterranean and tree areas, so the hard "best zone" never named the swamp (0%). Each zone is now also scored on *precision* (how much of its rule's area lies inside its own painted zone, or a narrower zone it contains; ridges above 1,500 m don't count as spill) and on *F1*, the balance of coverage and precision. Round 11: F1 objective 0.371; round 7: 0.360. Lowest precision: cold-wet 0.18 (winters too cold on the warm-wet north-east coast), swamp 0.20, tree 0.26; hot-dry spills into the painted cold-dry north. |
| — | *scale:* the map is drawn on hexes with 15-mile sides (30 mi corner to corner, ~585 sq mi) | — | The fitted hex grid gives 1.147 mi/px: 2,294 × 1,062 mi, 15.4° of latitude. Rounds 1–11 used 2,200.5 × 1,018.5 mi (hexes 25 mi across the flats, 4% too small). |
| it11 | round 12, retrograde, F1 objective, hex scale, 14 km (208 evals, 3-world ensemble) | F1-objective 0.401 | Re-scored on equal terms (new scale, 14 km, 3 worlds): F1-objective 0.401 vs 0.393 (round 11) and 0.375 (round 7); hard accuracy 50.2% (round 11: 46.3%, round 7: 51.4%). It keeps round 11's swamp (F1 0.29 vs 0.20 for round 7) while recovering most of round 7's discrimination; best cold-dry (0.61) and tree (0.46). Moist instability now strong (0.89). Map centre 35.2°N, tilt 26.9°. |
| — | *diagnosis:* what sets the painted swamp apart | — | Not rain: it gets the same as the warm-wet coast (~1,510 mm). Terrain does: it is ~5× flatter (median slope 0.7 vs 3.4 ‰ for warm-wet and tree), mostly lowland, with the densest drawn rivers. The swamp rule now needs flat ground (slope under ~1.5 ‰ over ~15 km) and 2.0× the dry threshold instead of 2.3× (flat ground waterlogs with less rain), and a place meeting it counts as swamp. On round 12 that lifts the swamp from 0% to 32% correct. The model's hottest, wettest climate is still in the painted *tree* zone, so flatness evens the two rather than tipping them. |
| — | *trade-off:* the north-east "warm and wet" coast | — | It reads cold-and-wet because the calibration puts land beyond the north-east edge (~100%): its winter monsoon chills the coast, as Siberia does Korea. Opening that land warms the coast (warm-wet F1 0.42 → 0.45) but costs the cold north more (cold-dry 0.61 → 0.55); left to the calibration. |
| it12 | round 13, retrograde, F1 objective with the waterlogged-swamp rule, hex scale, 14 km (208 evals, 3-world ensemble) | F1-objective 0.409 | Round 12 re-scored on the new rule: 0.395. Hard accuracy 51.5% (round 12: 49.0%; the best so far), swamp correct 35%, tree 59% (was 28%), Mediterranean 58%; warm-wet F1 0.42 → 0.50. Map centre 35.2°N, tilt 25.5°. |
| — | *tested and rejected:* orographic rain drifting downwind of crests ("spillover", 15–50 km) | (F1 0.409 → 0.408) | The hot-dry patches in the Mediterranean band sit next to very wet cells (347 vs 1,548 mm within 40 km), which suggested a too-sharp rain shadow. But carrying the uplift share of the rain downwind changed nothing at 15–30 km and destabilised the solver at 50 km, so that dryness is not the crest cutting off orographic rain. Not adopted. The swamp's remaining spill onto the flat south of the west coast is genuinely the same climate (hot, flat and even wetter, 2,360 mm), so no rule should split them. |
| — | *originals:* your lossless layers replace the chat-compressed ones (`data/source/original/`, derived by `scripts/prepare_sources.py`) | — | Terrain land/tiers agree on 99.9% / 99.5% of pixels, the painted zones on 98.8% of land (per-zone overlap 0.975–0.993), rivers 0.84: the compression had not distorted anything material. The hex lines give the exact scale: a perfectly regular grid (4,284 centres, residual 0.25 px), 1.143 mi/px, map 2,286.8 × 1,058.2 mi (0.3% smaller than the earlier estimate). Place names now sit on their settlement markers (151 of 152), the canonical town positions. |
| — | *speed:* same results, ~3× faster calibration | — | (1) The wide Gaussian smoothings (300–500 km, every step) run by FFT with the same kernel and edge handling (identical to 1e-14). (2) Winds and storm fields that do not depend on temperature are computed once per step instead of on every temperature pass. (3) Each step's temperature passes start from the previous step carried along its seasonal trend (6.5 instead of 9 passes; the same 0.05 °C convergence test, F1 objective 0.4057 vs 0.4049). Together 2.1× per model run. (4) Racing: a candidate whose first surrounding world already scores 0.06 below the best skips the other two (3× the 95th-percentile world-to-world spread); it would have saved 23–45% of recent rounds. Over-relaxing the temperature passes was tried and rejected (it diverges). |
| — | *spin re-test:* Earth-like spin on today's terms (320 evals from its round-8 best) | F1-objective 0.409 | Level with retrograde's round 13 (0.409), and still improving at the end: the old verdict (0.336 vs 0.493) came from the earlier physics and scoring. Both spins get the same further 320 evals. |
| it13 | round 14, retrograde, from round 13 (320 evals; the last 272 on the faster code with racing) | F1-objective 0.427 | Equal terms (lossless layers, exact hex scale, 3 worlds): 0.427 vs 0.405 for round 13; **53.5% correct**, the best so far (Mediterranean 68%, hot-dry 65%, swamp 38%). Map centre 34.4°N, tilt 25.8°. |
| — | *spin verdict on today's terms:* Earth-like spin, another 320 evals (round 15p, faster code with racing) | F1-objective 0.421 | Against retrograde round 14 at 0.427: retrograde narrowly ahead on the objective and clearly on correctness (53.5% vs 48.1%). The Earth-like world moves to 32–48°N with tilt 15.6° and still fails the warm-wet west coast (4% correct vs 32%) and the hot-dry south-east (35% vs 65%), while doing better on the Mediterranean band (83% vs 68%) and the swamp (43% vs 38%). Both were still improving when their budgets ran out. |
| — | *literature review* (`reports/Climate simulator improvement literature.md`, notes in `research_notes/`) | — | Mostly confirms the design: the reversed-spin pattern is what a full Earth-system model gives for a retrograde Earth (Mikolajewicz et al. 2018), and the rain shadow is as steep as real ones (halving every ~18 km; Olympics 19–23 km). Drainage-based wetland measures (height above the nearest river, wetness index, upstream area) do not separate the painted swamp from look-alike wet lowland on this map (the four flat tiers leave no relief to read), but heat does (mean annual temperature, AUC 0.96). |
| — | *spin gap on fresh worlds:* rounds 14 and 15p re-scored on 12 surrounding worlds neither search saw | (0.423 vs 0.420) | The objective gap shrinks from 0.006 to 0.004 with a 95% interval of −0.007 to +0.014, so the score alone cannot separate the spins; reversed spin's lead in painted land correct holds on 12 of 12 worlds (52.8% vs 48.2%). |
| — | *scoring:* the swamp rule also needs a hot year (mean annual above ~21 °C, from the legend's "Hot and wet" vs "Warm and wet") | (static: 0.427 → 0.444 retrograde, 0.421 → 0.429 Earth-like) | Swamp precision 0.26 → 0.45, correct 53.5% → 57.4%. A hottest-month form was rejected: it scores worse and asks for summers almost no wet place on Earth has. |
| — | *physics v7:* subtropical highs can sink harder in summer; one search box for both spins | (no change at the start point) | Ten of 49 genes sat at a bound in each spin's best fit. Modelling choices are widened the same way for both (monsoon strength 3 → 5 and scale 900 → 1,500 km, storm-track rain 5 → 8, lowland top down to 50 m, upland thickness to 2,500 m, faster land and sea adjustment, wider off-map coastlines, continental seasonality to 2.0); true limits stay (land fraction, current strength ≥ 0, sea-air humidity ≤ 0.9, surface westerlies ≥ 2 m/s). |
| — | *found:* humid summers far hotter than Earth's | — | On Earth (WorldClim lowland 20–50°, area-weighted) only 2.8% of the land whose warmest month brings 80 mm or more of rain passes 30 °C (0.4% at 120 mm). Round 14's reversed-spin world did so on about half of it (swamp 32.6 °C, warm-wet 30.3 °C, against 28–29 °C on the Gulf Coast); round 15p's Earth-like world has few wet summers and passes on 6%. The land's summer warmth ignored how wet the ground is. |
| — | *physics v8 and objective f1r:* wet ground cools summers; humid summers hotter than twice Earth's share are penalised | (static, retrograde: f1 0.444 → 0.406 at wet_cooling 0.6, hot share 0.52 → 0.12) | Without recalibrating, the realism penalty costs reversed spin far more than Earth-like spin (f1r 0.36 vs 0.42), so round 16 recalibrates both on it. |
| it14r / it14p | **round 16**, both spins on v8 physics and the f1r objective (320 evals each from their previous bests, worlds 1–3, same box) | f1r 0.397 (retrograde) vs 0.433 (Earth-like) | With humid summers held to Earth's limit, the reversed-spin world loses its lead: it had been making the swamp, forest and warm-wet coast hot partly with summers no wet place on Earth has. Retrograde: 34.9°N, tilt 24.7°, wet cooling 0.59, 41.9% correct, swamp now New-Orleans-like (coldest month 10 °C, hottest 28 °C, mean 21 °C). Earth-like: 39.4°N, tilt 17.6°, wet cooling 0.45, 48.4% correct, sea surface at the +4 °C limit of its offset. Reversed spin was still improving at the end; Earth-like had plateaued for 130 evals. |
| — | *rematch on 60 fresh worlds* (`scripts/spin_rematch.py`, `calibration/r16_rematch.json`): each spin's top 3, seeds 101–160, tie band ±0.01 declared in advance | gap −0.028 (95%: −0.034 to −0.012) | **Earth-like ahead**, outside the tie band, and on painted land correct on 57 of 60 worlds (47.4% vs 40.9%). Reversed spin still fits the warm-wet west coast (F1 0.59 vs 0.47) and the Mediterranean band (0.50 vs 0.44) better; Earth-like fits the swamp (0.41 vs 0.28), forest (0.47 vs 0.32) and cold-dry north (0.52 vs 0.42) better. |
| — | *round 16b:* 160 more evals per spin toward convergence | f1r 0.405 (retrograde) vs 0.439 (Earth-like) | Both gain a little (+0.008, +0.006); the gap holds. Correct 45.7% vs 48.5%. The Earth-like world now has land at the +5 °C limit of its offset and sea at +3.7 °C; the reversed one land +3.0 °C and sea −3.2 °C. |
| it14 | **round 17**, both spins with the sea and land temperature offsets limited to ±2 °C (200 evals each from their 16b bests), then the 60-world rematch | f1r 0.403 (retrograde) vs 0.437 (Earth-like) | Neither spin needed its large offsets: each scores about what it did without the limit. On fresh worlds the objective still favours **Earth-like spin** (gap −0.027, 95% −0.040 to −0.013, outside the ±0.01 tie band), but painted land correct now favours reversed spin (51.1% vs 47.7%, ahead on 46 of 60 worlds): reversed spin gets more land right but sacrifices the swamp and hot-dry zones, which the objective's soft minimum punishes. By the rule declared in advance (objective on fresh worlds), Earth-like spin wins; the published map is now round 17's Earth-like world: 29.4–44.7°N (centre 37.1°N), tilt 17.0°, height tiers 51 / 251 / 564 m with peaks to 2,697 m, sea and land offsets at +2 °C. |
| — | *sensitivity screening* around both round 17 bests (each gene ±10% of its range, worlds 1–3; `calibration/sensitivity_r17_*.json`) | — | Latitude, tilt, the subtropical-high edge and the land temperature settings dominate. Ten genes move nothing for either spin (ITCZ position and swing, trade-wind speed, storm reach, summer-strengthened highs, subsidence asymmetry, the two upper tiers, orographic rain, terrain drag): the realistic rain shadows need no orographic tuning. The Earth-like fit sits at a local optimum (no single nudge gains more than 0.005), the reversed-spin fit does not (Hadley edge +10%: +0.019), so round 18 polishes both with the same pattern search. |
| — | *independent check with ExoPlaSim* (T21 general-circulation model, slab ocean, ozone, Earth CO2; each world under each spin, reversed spin as the mirrored map; `output/exoplasim_check.*`) | — | Without ozone the planet settled 5 °C colder than Earth with 20% sea ice; with it, 17–21 °C. At T21 the continent's southern half is desert under either spin, so the wet/dry layout gets no skill (rank agreement ≈ 0). But in both worlds reversed spin puts the dry-summer belt on the painted Mediterranean band (agreement +0.38 / +0.54 against +0.08 / +0.23 with Earth spin): one independent point for reversed spin. |
| it15 | **round 18**: both round 17 bests polished with the same batch pattern search (`scripts/polish.py`; the ten inert genes frozen, offsets within ±2 °C, ~400 evals each), then the 60-world rematch | f1r 0.442 (retrograde, from 0.403) vs 0.468 (Earth-like, from 0.437) | Both gain about as much: the screening's untapped one-gene moves were real for both spins once searched for. On fresh worlds **Earth-like spin wins on both measures**: objective gap −0.030 (95% −0.049 to −0.010, outside the ±0.01 tie band) and painted land correct 52.2% vs 50.6% (Earth-like ahead on 40 of 60 worlds). The Earth-like world now matches the warm-wet west coast almost as well (F1 0.57 vs 0.59) and the swamp, forest and hot-dry zones better. Published world: 29.4–44.7°N, tilt 17.0°. |
| — | *zone rules follow Köppen* | (static on round 18: Earth-like 0.468 → 0.456, reversed 0.442 → 0.438) | Cold-and-dry took cold places up to 1.3× the dryness threshold, so dry-summer continental Dsa (not a Köppen dry climate) counted as cold and dry: 54% of the simulated cold-dry land was Dsa. Cold-and-dry is now BSk/BWk and hot-and-dry BSh/BWh (split at Köppen's 18 °C line, was 17 °C), Mediterranean is all of Cs (Csb too), and a place's label can only be a zone its Köppen class allows. On the published map the share of land correct drops 48% → 42%: the painted cold-dry north is simulated as Dsa, a little too wet for a steppe. |
| — | *map orientation* (physics v9: true north may point anywhere; with the spin this also covers mirror images and the southern hemisphere) and a screen of every 30° × both spins (80 evals on one world each, `calibration/run_orient_screen.sh`) | best 0.358 (Earth-like) / 0.333 (reversed) at 0° | North at the top of the map fits far better than any other orientation for both spins: 30° off already costs 0.05–0.12, 90° off 0.2, the upside-down map (equivalent to the southern hemisphere) 0.2–0.25. Turning north anticlockwise costs a little less than clockwise (330°: 0.27–0.28), so round 19 leaves the orientation free around 0°. |

## Handoff continuation: reliable calibration restarts

The handoff includes round-19 scripts but no orientation-screen run directory or
round-19 results. The launch script previously waited forever for the absent
`screen.done`. It now starts from each spin's retained round-18 fit if no completed
screen candidates are available, and exits on failed commands instead of marking
failed stages complete. The orientation screen also exits on failure.

Before further calibration:

* v9 encoding wraps bearings into −180° to 180° before applying search bounds;
  a screened 330° fit therefore starts at −30°, rather than being clipped to 180°.
* CMA-ES evaluates and saves the starting candidate on every requested world,
  after applying fixed genes and bounds. A restart cannot discard this candidate
  just because its random offspring are worse.
* The evaluation budget includes that initial evaluation; only complete CMA-ES
  populations that fit the remaining budget run. Round 19 now requests 321
  evaluations (one initial candidate plus 20 populations of 16).
* Round 19 disables first-world racing. Racing is a speed heuristic that can
  reject a fit which would recover on other worlds, not a proven score bound.
  Only fully evaluated, successful candidates can replace the saved best.

Regression tests are in `tests/test_calibration.py`. This work repairs the search
workflow; it does not establish a new preferred spin or replace the published
round-18 parameters and atlas.

To run the full pending experiment with the local environment:

```sh
PATH="$PWD/.venv/bin:$PATH" sh calibration/run_round19.sh
```

The pattern-search and 60-world rematch stages remain part of that full run.

Known validation caveat: the original core suite passes but emits NumPy matrix
multiplication warnings (divide-by-zero, overflow, invalid) in `ebm.py` and
`koppen.py` on this machine. Finite-output checks pass; the cause of those warnings
has not yet been established.

The initial live trial stalled in the forked worker pool after the baseline had
initialized the numerical libraries. Calibration now uses fresh (`spawn`)
workers, avoiding inherited native runtime locks on macOS. The interrupted
trial's baseline is retained in `calibration/r19_smoke_earthlike`; the rerun is
in `calibration/r19_smoke_spawn`.

Validation: 31 tests passed (23 existing core checks and eight new calibration
regressions); the eight search regressions also passed after switching worker
startup to spawn. Both edited shell scripts pass syntax checking.

## Round 19 review — 13 October 2026

The user completed round 19. The 60-world rematch favors Earth-like spin on F1r
(0.4749 vs 0.4276), but reversed spin on painted-zone accuracy (49.04% vs 43.34%).
The Earth-like atlas render shows only 32.41% accuracy. Its parameters match the
polished winner except that downsample changes 8→4, steps/year 25→73, and moisture
iterations 2→3. Those effects have not yet been isolated on the same world.

See `reports/round19_diagnosis.md` for evidence, research sources and priorities.
`scripts/diagnose_numerics.py` prepares controlled comparisons and per-zone
physical diagnostics. Only its plan and two lightweight setup tests were run;
no simulations or calibrations were run during this review.

User workflow preference: leave calibrations and other long-running tasks to the
user; provide exact commands rather than launching them or waiting for them.

### Round-19 numerical isolation results

User-run same-seed diagnostics identify grid refinement as the main effect:
44.22% accuracy at calibration settings → 32.96% with only downsample 8→4.
Changing moisture iterations 2→3 yields 43.87%; changing steps 25→73 yields
43.28%. The full render is 32.41%. The earlier moisture-iteration hypothesis is
not the main explanation on this case.

Fine-grid temperature/wind iteration reaches its cap on 29/33 steps, compared
with 0/33 coarse-grid steps. Added observation of final updates and actual
convergence decisions without changing the numerical solution. Prepared
`grid4_t48` and `grid4_t96` cases for the user to test iteration stability before
investigating spatial discretization and geography. Three quick setup tests pass;
no climate runs were launched by the assistant.

### Round-19 transport investigation

User-run fine-grid temperature caps of 48 and 96 both converge within at most
28 iterations and give identical objective 0.29318846 / accuracy 32.5503%.
Increasing the cap does not recover the fit. Added an experimental exponential
transport stencil (default remains upwind) to test grid-dependent numerical
diffusion. Prepared `coarse_fitted,fine_fitted` diagnostic cases for the user.

Reproduced the matrix warnings on small, finite, benign inputs independently
of the climate model, consistent with NumPy/Apple Accelerate issue #28687.
EBM and monthly statistics now use explicit contractions to avoid that backend
path; real nonfinite model outputs stop the diagnostic before scoring.
Thirteen focused tests pass. No assistant-run seasonal simulations or calibrations.

### Round-19 fitted transport results

User-run fitted transport gives 43.59% coarse-grid accuracy and 33.40% fine-grid
accuracy, with temperature convergence in both. This recovers only 0.85 points
on the fine grid versus converged original transport (32.55%). It does not
resolve the coarse/fine gap. Keep upwind as the default.

Made the existing linear solver update tolerance explicit (`solver_rtol`, default
0.001). Prepared `coarse_tight,fine_tight` with rtol=1e-6 to check whether loose
boundary-scaled per-sweep stopping explains part of the grid dependence. Saved
cap counts must be inspected before claiming convergence. Thirteen focused
checks pass; no assistant-run seasonal simulations.

### Round-19 cause identified: linear solve stopping accuracy

User-run tighter solves close the same-world grid gap: coarse/fine accuracy is
43.65%/43.78%, objectives 0.4668/0.4660, and cold-dry median annual rainfall
277/275 mm. With original stopping, converged coarse/fine accuracy was about
44.22%/32.55%. Loose inner linear solves explain the main discrepancy in this
case; this is not yet a multi-world or 73-step validation.

Fine tightening reached the old 400-sweep cap in 32 solves. Added actual
convergence status, configurable `solver_max_iter` (historical default 400), and
`solver_require_convergence` (historical default false; unfinished legacy solves
warn once). Prepared `fine_verified` at rtol=1e-6 with a 2,000-sweep cap and
strict rejection of unfinished solves. Sixteen focused tests pass. The user
runs the final verification; no assistant-run seasonal simulations.

### Round-19 fine-grid verification complete

User-run `fine_verified` completes all 243 linear solves (maximum 602 sweeps) and
all temperature/wind steps. Accuracy 43.7783%, objective 0.4659994; rainfall is
stable relative to the 400-cap tight run. Saved exact tested settings as
`calibration/round19_earthlike_strict.json` (same physical fit, no new calibration).

Added `--saved-numerics` to both render entry points so tested grid/steps/Picard
settings can be preserved explicitly. Exports include numerical provenance and
an audit of the two existing label policies on the model grid. The atlas display
policy is shared with the audit; historical strict accuracy and label rules are
unchanged. Nineteen focused tests pass. User runs atlas regeneration; no
assistant-run seasonal simulations or calibration.

### Corrected atlas checked; round-20 pilot prepared

The regenerated atlas and output summary match the verified numerics: 43.7783%
strict accuracy, 46.0979% display-policy accuracy. Forest discount raises warm-wet
recall 5.44→21.82% but lowers forest recall 30.35→11.25%; label weights alone trade
classes instead of improving the climate.

Added optional `zonefit` objective: equal weight to balanced fuzzy F1 and balanced
per-zone strict recall, with unchanged realism penalties. Historical objectives
and label policies remain intact. Ensembles and held-out comparisons log recall
and display accuracy; rematches can compare unchanged starts on identical worlds.

Prepared `scripts/round20_pilot.py`: 65 evaluations per spin on worlds 1–3,
strict numerics, then winners and unchanged starting fits on fresh worlds
201–212. It refuses existing output directories and leaves the atlas untouched.
Thirty-two focused tests pass; only the plan was previewed. User launches the
hours-long pilot.

### Atlas reference-climate controls

Added a temperature/precipitation priority slider to “Feels like”; its midpoint
preserves the original distance formula and score, and endpoints rank by just
one component. City rows are keyboard-accessible toggle buttons that update the
graph's temperature comparison and outlined precipitation bars. A selected city
stays pinned when rankings or the selected map location change; an automatic
comparison button restores the closest match. Reverse city-to-map search keeps
its existing balanced metric.

Reference rainfall is integrated from equal solstice-aligned bins into the local
35-day months and 15 Holy Days, preserving annual totals. The precipitation axis
includes both series. Verified ranking changes, city selection, pinning and both
chart series in the browser; four fast calculation tests pass. This is a static
atlas edit and needs only a page refresh, with no simulation or calibration.

### Similarity slider also controls real-city search

The temperature/precipitation weights now apply consistently to “Feels like”,
real-city search scores, ranked map towns, and map highlight regions. Changing
the slider refreshes an active search automatically without reframing the map.
The search panel states the active weighting. Grid comparison components are
cached and recombined with the same distance helper used for city comparisons.

Browser check with Athens: balanced ranks Paraman at 26%; temperature-only ranks
Selinunte at 49%; precipitation-only ranks Tuz at 44%. Highlight changes were
verified while the viewport transform stayed unchanged. Selecting Tuz reproduces
the same 44% Athens score in its station card. Five fast calculation tests pass;
no simulation or calibration rerun is needed.

### Round-20 apparent stall: active computation with batch-buffered reporting

A read-only process inspection during the user-run pilot found Earth-like complete
(65 candidates, no errors, starting score 0.3852 → best 0.4137 at evaluation 5).
Reversed spin had saved its initial candidate (score 0.4542) and was evaluating its
first 16-candidate population. Four worker processes each used approximately
one core continuously; a one-second stack sample showed compiled numerical work.
The starting reversed fit took about 17 minutes on three worlds, substantially
longer than the Earth-like configuration.

The old parent used blocking pool.map and wrote no candidate results until the
entire population returned, explaining unchanged files and no console messages.
Changed future runs to consume indexed results with imap_unordered, flush each
candidate immediately, and pass the complete population back to CMA-ES in the
original ask order. Added explicit pilot stage start/completion messages. The
active run is left running; loaded code will keep its old reporting behavior.

### Round-20 pilot stopped after first reversed-spin population

User stopped the run after 65 Earth-like and 17 reversed-spin evaluations. Both
best files match the successful logged candidates; no calibration worker remains.
Training strict accuracy is 44.72% Earth-like and 52.88% reversed. These are not
held-out results, and the unequal search budgets preclude a final spin claim.

Added `round20_pilot.py --compare-only` to evaluate saved fits without restarting
searches. The rematch deduplicates exactly identical parameter sets (ignoring the
seed explicitly overridden by each job); the reversed-spin winner is identical
to its baseline, reducing the comparison from 48 to 36 simulations. It now prints
and checkpoints each completed world, and uses spawned workers with an explicit
objective initializer. Six focused tests pass; plan confirms three unique fits
on twelve worlds. No comparison simulations were launched by the assistant.

### Round-20 held-out comparison completed

User-run comparison on worlds 201–212: reversed strict accuracy 49.33% versus
Earth-like 43.36% (ahead on all twelve worlds); display-policy accuracy 51.60%
versus 50.77%. zonefit gap +0.0150, bootstrap 95% −0.0111 to +0.0426: undecided.
Search budgets were unequal (65 vs 17), and reversed retains its starting fit.

Earth-like improves strict accuracy only 0.915 points over its start; mean
per-zone recall decreases 0.269 points and fuzzy F1 objective decreases 0.00614.
Its zonefit gain 0.02973 is more than explained by removal of a 0.03432 hot-wet
summer penalty. Warm-wet recall stays low (7.76%); reversed has 46.72% but swamp
recall only 19.72% against Earth-like's 37.54%. Further broad search is not
justified by the pilot alone. Preserve both fits and diagnose rule competition
and physical mismatches before changing objectives again. Analysis used saved
metrics only; no assistant-run simulations.

### Retrograde atlas selection and factor diagnosis

User selected the pilot's saved retrograde fit. Saved exact parameters as
`calibration/round20_retrograde_selected.json`; user runs render with
`--saved-numerics --out output --atlas` at the tested 14.7 km / 25-step settings.

Confirmed a structural overlap: a compatible humid Cfa example scores 0.9254
warm-wet but 0.9530 forest and therefore receives the broad forest label. F1
spill handling already recognizes this hierarchy; flat label argmax largely
does not. Swamp's five multiplied factors create a compound threshold whose
limiting factor must be checked on actual fields.

Named factor extraction retains existing memberships and classification rules.
Each render now saves `rule_diagnostics.json` with eligibility, weak-rule and
competing-label explanations, and `rule_fields.npz` with exact cropped fields
for offline rule/label analysis. Seventeen focused tests pass. The assistant
prepared the update and diagnosis; no seasonal simulation was launched.

### Completed retrograde atlas: saved-field probes

User completed the retrograde rebuild. Atlas metadata verified: strict model-grid
agreement 54.19%, display agreement 56.51%. Köppen gate failures cover 28.90%
of painted cells, versus 9.03% losing to other labels and 7.89% weak own rules.
The forest display multiplier trades warm-wet recall 47.24→69.98% against
forest 58.07→12.74%. A fixed selective warm-wet priority probe at membership
0.9 gives 57.32% accuracy and 58.10% balanced recall on this one world, but is
not yet validated across worlds. No production policy changed.

Added `scripts/audit_saved_rules.py` for offline NPZ policy probes, including
exclusive-label precision. Removing swamp annual heat increases swamp recall
23.15→42.56%, but precision falls 79.29→41.71% and overall accuracy declines.
Report: `reports/round19_diagnosis.md`; results: `output/rule_policy_probes.json`.
Seventeen focused tests pass. No assistant-run climate simulations/calibrations.

### Mediterranean dry patch is the next user priority

Saved fields show 12.99% of the Mediterranean target is steppe (BSh/BSk), not
BW desert. Of those dry cells, 99.74% already meet dry-summer rainfall criteria;
median annual rain 472.7 mm falls 45.2 mm below the current non-arid threshold.
This points to testing cool-season moisture delivery, retaining dry summers.

Prepared `scripts/mediterranean_pilot.py`: read-only plan by default, explicit
`--run` for two seasonal simulations on the saved seed. One probe increases
seasonal belt migration 2°, the other storm exchange 25%. Neither uses target
paint in the physics. Existing baseline is reused, exact parameters checked,
completed cases resumable, strict numerics retained. Prints progress and checks
Mediterranean dry/Cs area alongside intended dry-zone recall. No atlas overwrite.
`diagnose_numerics.diagnose` now optionally saves exact fields and accepts a
progress callback. No assistant-run climate simulation or calibration.

### Mediterranean pilot completed; fix coupled temperature iteration next

User-run storm exchange probe reduces Mediterranean dry area 12.99→2.81%, but
cold-dry recall falls 56.32→30.64%, hot-dry 69.22→41.37%, and overall accuracy
54.19→48.90%. Seasonal belt probe gives little Mediterranean benefit. Neither
promoted. Fixed original Mediterranean dry cells gain winter rain 284.6→378.1 mm
under stronger storm mixing, confirming moisture delivery as the useful mechanism.

Critical new diagnostic: despite converged linear solves, coupled temperature/
wind iteration fails on 21/20 seasonal steps in belt/mixing probes. Maximum final
updates inside map 16.75/15.30°C. Scores remain provisional. Added opt-in
`t_relaxation` with legacy default 1; damping does not shrink the convergence-error
test. Prepared one `coarse_damped` user-run numerical test (quarter updates,
192 iterations), exact fields optional via `--save-fields`. Numerical metadata
records relaxation. Legacy NPZ parameter checks normalise new defaults.
Thirty focused tests pass. No assistant-run long task, no atlas update.

### Damped baseline verified by user

User completed quarter-update temperature test in 129.3 seconds. All 33 coupled
steps and 947 linear solves converge; coupled iterations 16–51, median 24, no
cap hits. The unchanged physical fit now has 48.70% strict agreement and 24.15%
dry area inside the Mediterranean target, versus 54.19% and 12.99% previously.
This exposes numerical sensitivity in the fitted baseline; do not retain an
unsettled solve for its higher score.

Saved `calibration/round20_retrograde_stable.json` from the verified archive.
Next user command in the diagnosis report reruns only storm mixing on the stable
baseline. Pilot now optionally checks baseline convergence history and records/
rejects failed candidate convergence before continuing. Atlas remains unchanged.
Thirty-one focused tests pass; assistant ran no climate simulation.

### Stable storm mixing succeeds for Mediterranean; cold-dry remains a tradeoff

User-run stable storm exchange completes in 117.9 seconds with zero linear or
coupled temperature convergence failures. Mediterranean dry area 24.15→6.15%,
Mediterranean recall 41.85→64.16%, overall agreement 48.70→51.61%. Hot-dry
recall stays 68.33→67.25%, while cold-dry falls 64.51→39.64%.
Preserved exact fit as `calibration/round20_retrograde_stable_mixing.json`.
Prepared one combined belt/exchange probe to investigate recovery of cold-dry
contrast. Pilot now retains matching completed cases in incremental comparisons.
Thirty-two focused tests pass. No assistant-run simulation; atlas unchanged.

### Combined stable fit recovers cold-dry contrast

User completed combined belt/exchange probe in 119.3 seconds; all linear and
coupled temperature solves converge. Mediterranean dry area 6.18%, Mediterranean
recall 65.73%, cold-dry recall 61.07%, overall agreement 54.58%. Versus stable
baseline, hot-dry declines 68.33→59.02% and forest 59.13→51.38%; this is a
Mediterranean-focused compromise, not universal improvement or multiworld proof.
Saved exact fit as `calibration/round20_retrograde_mediterranean.json` after
checking parameters and convergence. Prepared user-run atlas render command in
the diagnosis report. No more parameter probes now; review the atlas next.
Assistant ran no simulation/render; existing atlas unchanged pending user rebuild.

### Combined Mediterranean atlas rebuilt by user

Verified exact combined parameters and stable numerical metadata in the updated
atlas. Strict agreement reproduces 54.5821%; model-grid display agreement 56.3057%.
Mediterranean target has 68.27% Cs and 6.18% steppe (185 cells), no BW desert.
Dayan/Ayah model-grid locations are now Csa; Yezi/Šepaš remain BSh. No new long
run requested; review this map first. Verification used saved outputs only.

### Continuing Mediterranean: focus storm exchange geographically

Remaining dry cells are lowland (median elevation 46.8 m) around 35.49°N, inland
of wetter Mediterranean cells. Dry target medians lie north (cold, 39.19°N) and
south (hot, 27.81°N). Prepared one `focused_storms` probe relative to the current
atlas: storm width ×0.8 and eddy exchange ×1.25. Simplified zonal winter exchange
ratios are 1.21 / 0.91 / 0.84 at Mediterranean / cold-dry / hot-dry medians.
Summer dry-zone ratios increase; actual precipitation must be tested, not assumed.

Pilot now tracks fixed original Mediterranean dry cells, newly dry cells and
same-location seasonal rainfall changes, rather than relying only on total area.
Prepared one user-run command in the diagnosis report. Thirty-three focused tests
pass; no assistant-run simulation or change to atlas data/production physics.

### Focused storms rejected; user retains current atlas

User-run focused fit cures 174/185 dry Mediterranean cells, creates no new dry
cells and reduces dry area 6.18→0.37%. Both solvers converge. Cold-dry agreement
nevertheless falls 61.07→32.56%, overall 54.58→51.49%. Cold-dry temperatures
hardly change; rainfall increases in winter and summer. User explicitly prefers
keeping current atlas and diagnosing this collateral damage.

Preserved rejected fit as `round20_retrograde_focused.json`. Added opt-in local
discrete moisture-equation terms, monthly wind/water archives, and absolute
residual aggregation. Diagnostics observe final fields without changing physics;
they are not conservative global water budgets. Prepared user command
`scripts/diagnose_moisture.py --run` for exact current/rejected reruns, no search
or atlas writes. Check two-Picard moisture closure before more parameter tuning.
Thirty-six focused tests pass; assistant ran no climate simulation.

### Moisture closure is the next numerical defect

User transport reruns reproduce both earlier fits. Despite converged linear/
temperature solves, current mean absolute moisture-equation residual / mean rain
is 82.4% cold-dry, 37.4% Mediterranean, 21.0% hot-dry, 18.6% swamp. Two partial
moisture updates leave large opposing seasonal errors. Focused cold-dry storm
exchange increases mainly in summer, but unsettled closure makes attribution
provisional. Atlas kept unchanged per user's explicit choice.

Added opt-in equation-based convergence in `rotclimate/moisture.py`, damped
iteration and strict failure handling. Legacy fixed-count behavior remains default
and matches old water arithmetic in tests. Adaptive runs enforce Dirichlet values
after damping and safely handle zero water. Numerical metadata includes the new
settings. Prepared one user-run current-fit check: `scripts/diagnose_moisture.py
--converged --cases current --run`, with 1% scaled equation tolerance, quarter
updates, cap256 and linear rtol1e-7. Fails early rather than completing invalid
runs. Forty-two focused tests pass. No assistant seasonal simulation/calibration.

### Moisture equation verification passes; seasonal fit needs retesting

User strict moisture run completes in 475.8 seconds. All seasonal temperature,
linear and moisture checks pass; moisture iterations 28–46, median36. Cold-dry
mean absolute equation residual / rain drops 82.4→0.0437%, Mediterranean
37.4→0.0193%. Corrected Mediterranean Cs area is only 20.67%, dry B area23.75%,
Cfa46.93%. Median winter rain 419.6→320.3 mm, summer245.8→300.0 mm. Overall
strict agreement43.31%; cold-dry66.18%, hot-dry65.10%. Earlier fit partly depended
on unfinished seasonal moisture updates; do not use them to retain a score.

Saved exact profile as `round20_retrograde_moisture_verified.json`. Prepared one
focused-case rerun using the same strict numerics; current baseline reused and
retained in comparisonJSON. Added comparable zone recalls and Mediterranean
climate shares. Forty-three focused tests pass. Current atlas remains unchanged
per user's preference; no assistant seasonal simulation.

### Settled focused storms still fail the dry-zone tradeoff; test seasonality

User converged focused case takes 479.2 seconds and passes all local numerical
checks. Mediterranean dry area23.75→9.12%, Cs20.67→37.37%, but Cfa remains45.22%
and cold-dry recall66.18→43.07%. Mediterranean summer rain barely changes
(376.3→372.0 mm mean), while cold-dry summer rain259.0→313.2 mm.

Added opt-in `eddy_seasonality`, default0 preserving old exchange arithmetic.
One fixed probe at0.4 scales the existing exchange1.4× in winter and0.6× summer
at seasonal extrema, applied consistently to heat and moisture. It uses the
verified current baseline, with no focused width/rate changes and no paint forcing.
Prepared user command `scripts/diagnose_moisture.py --converged --cases seasonal
--run`. Annual exchange/rain is not assumed conserved. Forty-nine focused tests
pass; no assistant simulation or atlas update. Research rationale in diagnosis report.

### Seasonal exchange improves verified fit; next test summer circulation

User seasonal case converges in 477.6 seconds. Overall agreement43.31→46.91%,
Mediterranean Cs20.67→30.26%, dry B23.75→15.10%, cold-dry recall66.18→67.04%.
Hot-dry recall falls65.10→60.78%. Exact profile preserved as
`round20_retrograde_seasonal_verified.json`; atlas unchanged.

Mediterranean summer exchange drops45.8 mm but wind export drops25.8 mm,
offsetting much of the reduction. Prepared one existing-parameter `poleward`
probe on the seasonal fit: Hadley edge+4°, moving summer high centre27.82→31.82°N
and summer storm centre40.82→44.82°N. Winter storm movement may wet cold-dry
land, so all zones remain in the comparison. Fifty focused tests pass. No
assistant-run climate simulation or atlas update.

### Poleward shift fails; protect verified numerics and test stronger seasonality

User poleward run converges in444.1 seconds but overall agreement falls46.91→32.94%
and Mediterranean dry area15.10→56.01%. Reject; no atlas update. Winter and summer
Mediterranean rain both decrease, while hot-dry summer rain surges. Seasonal fit
remains best verified candidate. Prepared one `strong_seasonal` test at contrast0.7
versus0.4, retaining its geometry and strict solver settings.

Found calibration/sensitivity still forcing Picard2. Added shared numerical
configuration helper: verified positive-tolerance profiles preserve saved settings
automatically; legacy defaults unchanged, explicit overrides take priority. Render
shares the helper. Calibration/sensitivity gain saved-numerics, picard override and
read-only plan options; sensitivity uses spawn. Sixty-three focused tests pass.
No assistant climate simulation, calibration, sensitivity run or atlas update.

### Stronger seasonality improves the verified fit; interaction test prepared

User contrast0.7 run converges in482.9 seconds. Overall48.90%, Mediterranean
Cs37.24%, dry B12.02%, strict Mediterranean34.27%, cold-dry68.30%, hot-dry57.16%.
Saved `round20_retrograde_strong_seasonal_verified.json`; atlas unchanged.
Prepared one `focused_seasonal` interaction case using the already-tested focused
width/rate plus contrast0.7. Focused storms added54.3 mm cold-dry summer rain;
strong seasonality removed54.6 mm relative to the same verified current baseline,
motivating a mitigation test without assuming additive responses. No poleward
shift or new parameter. Sixty-four focused tests pass. No assistant-run simulation.

### Interaction completed; switch to paired fresh-world screening

User combined case converges in491.6 seconds. Overall48.79%, Mediterranean
dry1.57%, Cs50.37%, cold-dry48.38%, hot-dry63.73%. Cold-dry still drops20 points
versus strong seasonal; no automatic atlas selection. Preserved exact combined
profile. Two equal overall scores hide the regional tradeoff.

Prepared `scripts/validate_mediterranean.py` for both finalists on seeds301/302:
four sequential user-run simulations, resumable by exact parameters/model-source
fingerprint, strict checks, paired comparisons and saved rule fields. Plan only
by default. Roadmap in `reports/near_term_plan.md`: screen finalists, then one
small bounded calibration with dry-zone limits, independent checks and atlas
review. Sixty-six focused tests pass. No assistant-run simulation or atlas update.

### Fresh-world validation finds a difficult temperature fixed point

First user job, strong seasonal world301, takes672.6 seconds and passes all linear/
moisture checks. Temperature steps19–21 cap at192 with in-map final updates
0.101/0.095/0.054°C >0.05°C. Result rejected; other jobs not run. Preserved original
failed JSON/fields with `_pre_temperature_retry` suffix.

Added opt-in bounded temperature retries and strict failure: first-stage arithmetic
unchanged, up to two continuation stages halve damping and double caps while
retaining full-update0.05°C tolerance. Validation uses the same policy for both
finalists and fails immediately on persistent temperature failure. Detailed stage
histories and live retry progress added. Prepared one-job retry command in report;
default validation can resume afterward. Sixty-nine focused tests pass; no
assistant-run seasonal simulation or atlas update.
