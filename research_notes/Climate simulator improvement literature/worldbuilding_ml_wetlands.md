# Worldbuilding climate methods, ML cross-checks, wetland placement, and Cs/Cfa geography

Scope note: written for rotclimate (fantasy continent, ~27–42°N, reversed spin fits best; swamp precision 0.27 because the "hot + very wet + flat" rule also catches a flat, rainy west-coast lowland painted warm-wet). Sources were fetched directly where possible (Tootchi 2019 full text, Mikolajewicz 2018 full text, Worldbuilding Pasta posts, Azgaar source code, Gharari 2011 PDF, OpenAlex abstracts for Fan 2013 / Fan & Miguez-Macho / Rodwell & Hoskins / WorldClim 2). Items that come only from search-engine summaries are marked "(search summary)".

## Q1. Worldbuilding climate methods and tools: heuristics and what they say about reversed rotation

### Takeaway
The worldbuilding tools fall into two groups. Rule-based generators (Azgaar, Frozen Fractal, and the Artifexian-style hand methods) use latitude bands for rising and sinking air, prevailing-wind sweeps with orographic loss, and Köppen rules applied to January and July values. Model-based workflows (Worldbuilding Pasta's ExoPlaSim workflow) run a coarse GCM with a slab ocean and no ocean currents. On reversed rotation the one explicit worldbuilding statement, from Worldbuilding Pasta, is that retrograde spin is equivalent to flipping the topography east–west. A full Earth-system model (Mikolajewicz et al. 2018) confirms this to first order in Köppen terms, but Earth's real ocean geometry adds large non-mirror changes.

### Cited Findings
**Worldbuilding Pasta (Madeline James) / ExoPlaSim**
- On retrograde rotation, verbatim: "I didn't do any runs in ExoPlaSim for retrograde rotation because it doesn't really change the overall character of the climate in a manner independent of the specific topography of Earth (you'd get the same result if you just flipped the topography map horizontally)." Instead the author ran the published retrograde-Earth model output (Mikolajewicz et al. 2018) through the "koppenpasta" script. — [Worldbuilding Pasta, Climate Explorations: Day Length (2023)](https://worldbuildingpasta.blogspot.com/2023/06/climate-explorations-day-length.html)
- Same post, rotation **rate** (not direction): halving day length shrinks the Hadley cells to about 25° latitude and the Ferrel cells to about 40°, with roughly 5 cells per hemisphere. "The desert belts have shifted towards the equator… Past the desert belts, the semiarid and Mediterranean climates have also shifted equatorward." The ITCZ also shifts less with the seasons, which weakens monsoons. Slower rotation does the reverse: broader and fewer cells. — [Worldbuilding Pasta, Day Length](https://worldbuildingpasta.blogspot.com/2023/06/climate-explorations-day-length.html)
- ExoPlaSim limitations for worldbuilders:
  - The default grid is 32×64 (T21); runs go up to 256×512, but runtimes grow toward months.
  - There are no ocean currents: the ocean is a 50 m mixed-layer slab, so Northern Europe comes out too cool.
  - "ExoPlaSim seems to have a bias towards Mediterranean climate patterns (As, Cs, and Ds zones)." Averaging several years of output reduces the bias.
  - Small islands and peninsulas come out drier than they should.
  - The East Asian monsoon is too weak.
  - T42 is recommended as the minimum for output maps.
  - [Worldbuilding Pasta, Part VI Supplement: Modeling Climate with ExoPlaSim (2021)](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- ExoPlaSim is a modified Planet Simulator (PlaSim) with simplified radiative transfer (2 shortwave bands, 1 longwave band), which is why it runs fast. It ships with a Python API and pip install. — [Paradise et al., ExoPlaSim, arXiv:2107.07685](https://arxiv.org/abs/2107.07685) (search summary)
- Worldbuilding Pasta has since built its own "Pasta Bioclimate" classification as an alternative to Köppen (2025 series). I did not read it in detail. — [Beyond the Köppen-Geiger Climate Classification System, Part II](https://worldbuildingpasta.blogspot.com/2025/03/beyond-koppen-geiger-climate.html)

**Azgaar's Fantasy Map Generator (read from the current source code)**
- Precipitation model, described in the code as "The simplest precipitation model": winds enter the map from each side and drop humidity as they cross cells. Wind direction is set per 30° latitude tier. The default (Earth-based) angles are `[225, 45, 225, 315, 135, 315]` for 6 tiers running north to south. Users can rotate them in the UI, which is how one would reverse the prevailing winds. — [Azgaar FMG, src/generators/precipitation-generator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/generators/precipitation-generator.ts) and [world-configurator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/controllers/world-configurator.ts)
- Latitude precipitation multipliers per 5° band, with the code's own pressure-belt comments:
  - ×4 for 0–5° (rising)
  - ×2 for 5–20° (wet summer, dry winter)
  - ×1 for 20–30° (sinking, dry all year)
  - ×2 for 30–50° ("wet winter… dry summer", which is the Mediterranean belt)
  - ×3 for 50–60° (wet all year)
  - ×2 for 60–70°
  - ×1 for 70–85°
  - ×0.5 for 85–90°
  - [precipitation-generator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/generators/precipitation-generator.ts)
- Orographic rule:
  - Normal loss per cell is `max(humidity/(10·modifier), 1)`.
  - Uphill steps add `diff · (h_next/70)²`.
  - Crossing a water cell adds humidity (+5·modifier) and leaves extra "coastal precipitation" (humidity/rand(10,20)) on the first land cell.
  - Cells above elevation 85 (on a 0–100 scale) block wind.
  - [precipitation-generator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/generators/precipitation-generator.ts)
- Wetland biome rule (directly relevant to swamp placement). Cell moisture is the mean precipitation of the cell and its land neighbours, plus 4, plus `max(riverFlux/10, 2)` if the cell carries a river. A cell becomes "Wetland" if temperature > −2 °C and either moisture > 40 with height < 25 ("near coast"; sea level is 20 on this scale) or moisture > 24 with 24 < height < 60 ("off coast"). Hot deserts (≥25 °C, moisture < 8) are blocked only when there is no river. — [Azgaar FMG, src/generators/biomes-generator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/generators/biomes-generator.ts)
- Biomes otherwise come from a moisture-band × temperature-band lookup matrix. — [biomes-generator.ts](https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/src/generators/biomes-generator.ts)

**Other procedural generators**
- Frozen Fractal's "Around The World" game generator applies Köppen rules to simulated January and July values. Intermediate months are interpolated as a sine curve, which is enough to evaluate rules like "at least four months above 10 °C". The author chose Köppen over Trewartha because it is the most widely used scheme in procedural world generation. — [Frozen Fractal, Around The World Part 9: Climate (2023)](https://frozenfractal.com/blog/2023/12/29/around-the-world-9-climates/)
- Artifexian: I could not retrieve the tutorial itself. One Reddit thread says his video guide, unlike another popular guide, applies the ocean-current rule when assigning zones. This is anecdotal. — [r/mapmaking mirror (search summary)](https://lr.eu.psf.lt/r/MapMaking)

**Reference GCM result on reversed rotation**
- Mikolajewicz et al. (2018) compared a retrograde and a prograde Earth with the MPI Earth System Model. Rotation sense has "relatively little impact on the globally and zonally averaged energy budgets but leads to large shifts in continental climates, patterns of precipitation, and regions of deep water formation." The Sahara greens and large parts of the Americas become desert. The European–Siberian temperature gradient reverses. The ITCZ shifts south. Storm-track activity moves from ocean to land in the Northern Hemisphere. — [Mikolajewicz et al. 2018, ESD 9, 1191–1215](https://esd.copernicus.org/articles/9/1191/2018/)
- Köppen's idealized continent predicts "mirror symmetry about the north–south axis" for retrograde rotation. "Predictions based on Köppen's idealized continent… for the expected mirror symmetry for a retrograde rotating Earth are well supported", and "to a first approximation… these features do appear with mirror symmetry." Some changes "would not have been predicted from just mirroring". The biggest is that deserts shift from Eurasia–Africa to the Americas, and global permanent desert area falls by roughly 40% over Northern Hemisphere land. — [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/)
- The same paper states the classic east–west rule: "In the subtropics, the climate of the west coast is drier and more Mediterranean (winter rains) than on the east coast, where seasonality is more extreme, with more monsoonal (summer rains) patterns of precipitation." — [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/)

### Inferences
- For an isolated continent with idealized oceans, flipping the map east–west and running prograde physics should be equivalent to reversed spin. Pasta says so and Mikolajewicz confirms it to first order in Köppen terms. The residual differences on real Earth come from asymmetric basin geometry and the overturning circulation (AMOC versus a Pacific overturning), which a fast single-continent simulator probably does not resolve.
- Under reversed spin at 27–42°N, the textbook expectation flips. Dry-summer (Cs) climates should sit on the **east** coast, and humid-subtropical, summer-rain (Cfa) climates on the **west** coast. A flat, rainy west-coast lowland painted "warm-wet" therefore fits a mirrored Cfa coast, the analogue of the US Gulf/Atlantic coastal plain. That lowland is climatically "swamp-capable", so separating it from the painted swamp must rely on hydrology (drainage convergence or rivers), not climate alone. See Q3.
- Azgaar's wetland rule includes river flux in moisture and restricts wetlands to low near-coast cells. This is a crude version of the "climate surplus + drainage convergence + low height" logic used in hydrology (Q3), and it is the only generator found that adds river flow explicitly.

### Gaps
- Artifexian's own heuristics: I could not retrieve video transcripts or a written companion page, so there is no first-hand citation.
- "Clima-Sim" and similar named procedural climate generators: none were found in searches.
- The main Worldbuilding Pasta Part VI climate-heuristics post (pressure belts, currents, Köppen placement) was not located in the blog feed. Only the ExoPlaSim supplement and the Day Length exploration were read.
- None of the worldbuilding sources gives explicit swamp-placement rules beyond Azgaar's code.

## Q2. ML models predicting Köppen or monthly climate from geography, and their use as an independent cross-check

### Takeaway
I found no published model trained on Earth to predict Köppen class from pure geography (latitude, elevation, distance to coast, coast orientation, continentality) and then applied to fictional, paleo or exoplanet maps. The closest work is either interpolation between real stations (WorldClim) or classification that already takes climate data as input. Where models are tested out of sample, accuracy drops sharply. A geography-only ML model could serve as a weak, independent cross-check. The east–west mirroring trick for reversed spin is physically justified (Q1), but the model's skill at a fictional coastline would need validation with held-out continents.

### Cited Findings
- WorldClim 2 interpolates station climate with thin-plate splines using covariates including **elevation and distance to the coast**, plus satellite land-surface temperature and cloud cover. Global cross-validation correlations are ≥0.99 for temperature and humidity, 0.86 for precipitation and 0.76 for wind speed. This is interpolation between dense stations, not prediction from geography alone. — [Fick & Hijmans 2017, Int. J. Climatol., WorldClim 2](https://doi.org/10.1002/joc.5086)
- A CNN (LeNet) predicting global biomes from climate reached accuracy of 0.701–0.734 when the training and test climate datasets were identical, but only 0.394–0.559 when they differed. This is evidence of a large out-of-distribution penalty. — [GMD 15, 3121 (2022), Predicting global terrestrial biomes with the LeNet CNN](https://gmd.copernicus.org/articles/15/3121/2022/) (search summary)
- A random forest using latitude, elevation and topography together with bioclimatic variables predicted land cover with 93% accuracy at 0.5°. Its target is land cover, not Köppen, and its inputs include climate. — [Sparey et al. 2024, Atmosphere 15(6):700](https://www.mdpi.com/2073-4433/15/6/700) (search summary)
- On the Korean Peninsula, RF and ANN classifiers trained on Köppen-Geiger labels at 90 stations (inputs: satellite temperature and precipitation plus SRTM elevation) had "relatively high" accuracy. Disagreements concentrated in complex mountainous terrain. — [UNIST scholarworks record (search summary)](https://scholarworks.unist.ac.kr/handle/201301/80290)
- Worldbuilding Pasta's position on a mirror approach for reversed spin is the "flip the topography map horizontally" statement above. — [Worldbuilding Pasta, Day Length](https://worldbuildingpasta.blogspot.com/2023/06/climate-explorations-day-length.html)
- Mikolajewicz et al. (2018) show that a mirror-image Köppen pattern is a good first approximation for a retrograde Earth, with non-mirror departures tied to ocean overturning and storm-track changes. — [ESD 2018](https://esd.copernicus.org/articles/9/1191/2018/)

### Inferences
- A practical cross-check design:
  1. Train a gradient-boosted tree or RF on Earth land pixels.
  2. Use as features latitude, elevation, distance to coast, distance to the west and east coasts separately (an orientation proxy), upwind ocean fetch, and continent width at that latitude (continentality).
  3. Use Köppen class (e.g. Beck et al. 1-km maps) or WorldClim monthly T and P as targets.
  4. Mirror the fictional map east–west before prediction, to represent reversed spin.
  5. Validate by holding out whole continents (e.g. train without North America and test on it), not random pixels. The GMD biome result suggests random-pixel accuracy would badly overstate skill.
- The model is "independent" of rotclimate's physics but not of Earth's specific geography. It will encode Earth idiosyncrasies (e.g. the Tibetan Plateau, the Gulf Stream), so treat disagreement as a flag to investigate, not ground truth.
- Coast orientation is the feature that carries the Cs (west) versus Cfa (east) contrast. Without it, an ML model cannot reproduce the asymmetry rotclimate needs.

### Gaps
- No peer-reviewed accuracy number for geography-only Köppen prediction on held-out continents was found. Do not cite a figure.
- No study was found applying such a model to fictional or exoplanet maps (searched twice, including extended mode).
- The Sparey 2024 and Korean RF details came from search summaries. The full texts were not read.

## Q3. What determines where wetlands/swamps occur, and how a simple model would use TWI/HAND plus climate surplus

### Takeaway
On Earth, large persistent wetlands sit where the water table is at or near the surface. That happens where a climatic water surplus (P − ET) meets topographic convergence (large upstream area over low slope) and impeded drainage near base level (rivers, sea level). Flatness alone is not enough. The standard simple recipe is TCI = ln(a·Pe/tanβ), where a is upstream drainage area per unit contour length and Pe is the sum of monthly max(0, P − PET). Wetland is the top ~6–15% of land by that index. HAND below roughly 5–6 m above the nearest stream is the usual local cut-off for "saturated/wetland" terrain.

### Cited Findings
**Groundwater/water-table framing (Fan; Fan & Miguez-Macho)**
- "Shallow groundwater influences 22 to 32% of global land area, including ~15% as groundwater-fed surface water features and 7 to 17% with the water table or its capillary fringe within plant rooting depths." Water-table patterns "explain patterns in wetlands at the global scale." The model is forced by modern climate, terrain and sea level. — [Fan, Li & Miguez-Macho 2013, Science 339:940](https://doi.org/10.1126/science.1229881)
- Climate models usually treat wetlands as "flat land with wet soil resulting from precipitation events", wetted from above but not from below. The authors' framework uses water-table depth, forced by "precipitation–evapotranspiration–surface runoff, land topography, and sea level". Groundwater "links land drainage to sea level by impeding drainage in lowlands". Large-scale groundwater convergence "nourishes the lowlands even in arid climates." It was validated for North America at 1 km. — [Fan & Miguez-Macho 2011, Climate Dynamics (online 2010)](https://doi.org/10.1007/s00382-010-0829-8)
- Fan et al. used uniform water-table depth (WTD) thresholds: 0 cm for inundated areas and 25 cm for wetlands. — [Tootchi et al. 2019, ESSD 11:189](https://essd.copernicus.org/articles/11/189/2019/)

**Tootchi, Jost & Ducharne 2019 (ESSD), global composite wetland maps**
- Published global wetland extents range from 3% to 21% of land because definitions and methods differ. — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Their wetland definition is mean annual WTD < 20 cm. Using Fan et al.'s WTD gives wetlands over 15% of land. A sensitivity analysis over thresholds from 0 to 40 cm shows little change in total area near 20 cm, so 20 cm separates shallow-WTD land well. — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Topographic index: TI = ln(a / tanβ), with a the drainage area per unit contour length (m) and tanβ the local slope. High values occur on flats with large drainage areas. — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Climate-weighted variant: **TCI = ln(a·Pe / tanβ) = TI + ln(Pe)**.
  - Pe is the mean annual effective precipitation (m).
  - Monthly, Pe_m = max(0, P_m − PET_m), using Penman–Monteith PET from CRU 1980–2016.
  - Pe is the sum of the 12 long-term monthly means.
  - A third variant, TCTrI, adds transmissivity.
  - [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Plain TI puts wetlands "equally distributed over well-known arid areas such as the Sahara and the Kalahari Desert, the Australian Shield and the Arabian Peninsula as in wet regions". Adding Pe (TCI) makes "previously diagnosed wetlands with a TI in dry climates disappear and transfer to regions with wet climates (such as the Amazon basin and South Asia)." — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Thresholds are set as a **land-fraction percentile**, not a fixed value. "TI-based wetlands [are] the pixels with a TI above a certain threshold, defined to match a certain fraction of total land." They used 15% of land (to match WTD ≤ 20 cm) or about 6–6.6% for groundwater-driven wetlands, so that the union with surface-water wetlands equals 15%. The final composite maps cover 15–22% of land. Their surface-water/inundation map (RFW) alone covers 9.7%. — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)
- Uniform TI thresholds do not transfer well across landforms and climates (citing Marthews et al. 2015). TI values depend on pixel size, so they apply Ducharne's (2009) correction to 1 m-equivalent values. In some regions (e.g. one validation region they discuss), "groundwater wetland formation is almost completely explained by topography and climate (of the TCI formulation)". — [Tootchi et al. 2019](https://essd.copernicus.org/articles/11/189/2019/)

**HAND (Height Above Nearest Drainage)**
- The HAND algorithm is formalized in Rennó et al. (2008); the classification and validation are in Nobre et al. (2011). HAND normalizes terrain by height relative to the nearest drainage along flow paths and correlates highly with water-table depth. Classes are waterlogged (saturated to the surface), ecotone (shallow water table), slope, and plateau. It was validated over about 18,000 km² of the lower Rio Negro. — [Rennó et al. 2008, RSE](https://doi.org/10.1016/j.rse.2008.03.018); [Nobre et al. 2011, J. Hydrol. 404:13–29](https://doi.org/10.1016/j.jhydrol.2011.03.051); [HESSD comment C2446 (search summary)](https://hess.copernicus.org/preprints/8/C2446/2011)
- Calibrated thresholds (Wark catchment, Luxembourg, 5 m DEM):
  - Best-fit HAND threshold H = **5.9 m** (95% uncertainty interval 3.2–8.9 m) together with slope S = **0.129** (12.9%).
  - Cells with H < 5.9 m are wetland (flat or "sloped wetlands"). H > 5.9 m with S > 0.129 is hillslope, and H > 5.9 m with S < 0.129 is plateau.
  - With DEM smoothing (60–150 m window), the thresholds become H = 4.7 m (3.5–7.1 m) and S = 0.113.
  - HAND plus slope alone gave the best classification.
  - [Gharari et al. 2011, HESS 15:3275](https://hess.copernicus.org/articles/15/3275/2011/)

**TWI thresholds in practice**
- No universal "TWI > X" cut-off exists. The index depends on DEM resolution and algorithm. Combining several indices with ML raised wet-soil mapping agreement to kappa 0.65 in Sweden. — [Lidberg et al. 2019, Ambio](https://link.springer.com/doi/10.1007/s13280-019-01196-9) (search summary)
- A French national topo-climatic index model reached overall accuracy of 67.8% but kappa of only 0.17. — [EGU2014-12780](https://meetingorganizer.copernicus.org/EGU2014/EGU2014-12780.pdf) (search summary)
- In Brazilian tropical catchments, thresholds calibrated on one catchment and tested on another gave 72.7–73.8% accuracy. — [Authorea preprint](https://authorea.com/doi/full/10.22541/au.160923945.52389246) (search summary)

### Inferences
- Rotclimate's current swamp rule (hot + P ≥ 2× the Köppen aridity threshold + slope < ~1.5‰ over ~15 km) is effectively "climate × flatness", which is the formulation Fan & Miguez-Macho criticize. It misses the drainage-convergence term (a, upstream area) and the base-level term (HAND, or proximity to sea level or river). A flat rainy plain with no large upstream catchment, such as a west-coast lowland drained by short coastal streams, scores as high as a flat delta or lower floodplain fed by a large basin, such as the painted south coast with rivers.
- A minimal fix grounded in these papers:
  1. Compute flow accumulation on the DEM, giving the upstream area a per cell (or per unit width).
  2. Compute Pe = Σ_months max(0, P − PET), the monthly surplus, not the annual surplus. Seasonality matters: a winter-wet, summer-deficit coast scores lower than the same annual P spread evenly.
  3. Compute TCI = ln(a·Pe / max(tanβ, ε)).
  4. Compute HAND, the height above the nearest river or sea cell along the flow path.
  5. Mark swamp where TCI is in the top X% of land (Tootchi used 6–15% globally; a hot, wet south coast might calibrate locally), AND HAND is below a few metres (Gharari 5–6 m at 5 m DEM; at coarse grid scale this must be relaxed and calibrated against the painted map), AND the climate is warm and wet (the existing rule).
- Because TI depends on pixel size (Tootchi apply a resolution correction), thresholds at rotclimate's grid size (~km to tens of km) cannot be taken from 5–30 m DEM studies. A percentile threshold calibrated so the swamp area matches the painted area is the most defensible choice, and it mirrors Tootchi's land-fraction approach.
- Adding "a large upstream area" (river convergence) is the term most likely to separate the south-coast swamp from the west-coast warm-wet lowland. This is an inference: the effect has not been tested on the user's map.

### Gaps
- Nobre et al. (2011) numerical HAND cut-offs for the waterlogged and ecotone classes could not be retrieved; the full text was not accessible. Commonly repeated values (about 5 m for waterlogged, about 15 m for ecotone) were not verified and should not be cited without checking the paper.
- No source gives TCI or HAND thresholds appropriate for km-scale (coarse) grids. Calibration against the painted map is required.
- Tootchi's validation scores (spatial pattern correlation values) were seen only partially (e.g. SPC [CW-TCI15, GDW-WTD] = 0.6). The full validation table was not extracted.

## Q4. Where Mediterranean (Cs) and humid-subtropical (Cfa) climates occur and why; transition zones

### Takeaway
Cs climates occur on the western sides of continents at roughly 30–45° latitude. Summer subsidence under the poleward-shifted subtropical high (reinforced by monsoon-induced descent and cold, upwelling eastern-boundary currents) dries the summer, and winter storm tracks bring the rain. Cfa sits on the southeast/east sides at about 25–40°, where onshore flow around the western flank of the subtropical high and the summer monsoon give hot, humid, summer-rain climates. With reversed spin, both should swap coasts.

### Cited Findings
- "Mediterranean climate zones are typically located along the western coasts of landmasses, between roughly 30 and 45 degrees north or south of the equator." The main cause is the subtropical ridge, which moves poleward in summer and equatorward in winter. They are found poleward of desert and semi-arid climates and equatorward of oceanic climates. — [Wikipedia, Mediterranean climate](https://en.wikipedia.org/wiki/Mediterranean_climate) (secondary source; it cites Kottek et al. 2006 and Peel et al. 2007)
- Köppen "s" definition: the driest summer month has < 30 mm (some authors use 40 mm) and ≤ one-third of the wettest winter month. Csa has a warmest month > 22 °C, Csb a warmest month < 22 °C. Csb also covers areas usually called oceanic (Pacific Northwest, Galicia, southern Chile). — [Wikipedia, Mediterranean climate](https://en.wikipedia.org/wiki/Mediterranean_climate); [Kottek et al. 2006](https://doi.org/10.1127/0941-2948/2006/0130); [Peel et al. 2007](https://www.hydrol-earth-syst-sci.net/11/1633/2007/)
- Cold currents: in coastal California the cold California Current stabilizes the air, further reducing rain and causing marine fog. — [Wikipedia, Mediterranean climate](https://en.wikipedia.org/wiki/Mediterranean_climate)
- Dynamical mechanism:
  - The equatorward part of each summer subtropical anticyclone is a Kelvin-wave response to monsoon heating over the continent to its west.
  - The Rossby-wave response west of monsoon heating, interacting with the westerlies, produces descent. Longitudinal mountain chains enhance it.
  - Beneath the descent, equatorward flow induces cool upwelling.
  - "The Mediterranean-type climates of regions such as California and Chile may be induced remotely by the monsoon to the east."
  - [Rodwell & Hoskins 2001, J. Climate 14:3192, Subtropical Anticyclones and Summer Monsoons](https://doi.org/10.1175/1520-0442(2001)014%3C3192:SAASM%3E2.0.CO;2)
- Humid subtropical (Cfa/Cwa) climates "normally lie on the southeast side of all continents (except Antarctica), generally between latitudes 25° and 40°". Rainfall usually peaks in summer, from convective thunderstorms, tropical lows and tropical cyclones, with a strong monsoon variant (Cwa) in East and South Asia. Annual rainfall is generally over 1,000 mm in East Asia and coastal Australia. — [Wikipedia, Humid subtropical climate](https://en.wikipedia.org/wiki/Humid_subtropical_climate) (citing Britannica)
- West versus east coast asymmetry and its rotation dependence: "In the subtropics, the climate of the west coast is drier and more Mediterranean (winter rains) than on the east coast… with more monsoonal (summer rains) patterns", and Köppen's idealized continent predicts mirror symmetry for retrograde rotation. — [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/)
- Transition examples:
  - In South Asia, Cfa borders Cs in western Pakistan and NW India (Peshawar and Srinagar have a March precipitation peak).
  - In the interior southern US, Cfa shifts to a winter or spring rainfall maximum away from the coast.
  - Caspian Iran, western Georgia and NE Turkey are Cfb/Cfa borderline.
  - [Wikipedia, Humid subtropical climate](https://en.wikipedia.org/wiki/Humid_subtropical_climate)
- Rotation rate also shifts the Cs belt: faster rotation moved Mediterranean and semi-arid climates equatorward in ExoPlaSim experiments. — [Worldbuilding Pasta, Day Length](https://worldbuildingpasta.blogspot.com/2023/06/climate-explorations-day-length.html)
- ExoPlaSim-based workflows over-produce Cs/As/Ds, so worldbuilding maps made that way may show too much Mediterranean climate. — [Worldbuilding Pasta, ExoPlaSim supplement](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)

### Inferences
- For a continent at about 27–42°N with reversed spin, expect Cs/BS along the **east** coast and Cfa along the **west** coast, with a Cfa → Cfb or Cs transition moving poleward along each coast. The painted Mediterranean and warm-wet zones can be used to test whether the simulator has the asymmetry right.
- The Cs–Cfa boundary in Köppen terms is set by summer precipitation (< 30–40 mm and < 1/3 of winter maximum). A small bias in summer rainfall can flip a coastal cell between Cs and Cf, so the boundary is sensitive. Diagnostics should compare summer and winter precipitation ratios against WorldClim analogue cities, not only class labels.
- A west-coast (under reversed spin) Cfa lowland that is flat and very wet is exactly the US Gulf Coast analogue. It has real swamps, but mainly in river floodplains and deltas (high upstream area, low HAND), not uniformly across the flat plain. This supports adding a drainage-convergence term rather than tightening the climate rule.

### Gaps
- No peer-reviewed quantitative width or latitude bounds for Cs–Cfa transition zones were found. The 30–45° and 25–40° ranges come from encyclopedic sources.
- Quantitative cold-current effects (e.g. SST anomaly versus Cs extent) were not sourced.
