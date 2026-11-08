# Owner preference (8 Nov 2026): post every new map or figure in chat (SendUserFile) as soon as it is generated.
# Owner decision (8 Nov 2026): the free and Whittaker fits are RETIRED; work focuses on the Earth fit only.
* scripts/atlas_set.py (ACTIVE = earth_fit) filters every add-on loop and scripts/refresh_atlas_pages.py; atlases/free_fit and
  atlases/whittaker_fit stay as their last published snapshot (hosted pages untouched, not deleted; URLs in
  atlases/artifact_links_retired.json, removed from artifact_links.json so the Earth-fit pack drops its links to them).
* Release driver for the Earth fit only: scripts/release_earth_fit_d1.sh (D2b re-export on the staged atlas, promote, add-ons).

# Block D: arable land from slope (D1) + irrigation by height above the river (D2) — 8 November 2026

* D1 (calibration/geography_control_20261107/plan_D1.json): arable share a(S) = 0.018 + 0.982 / (1 + (S / 2.75 deg)^1.29)
  of the ~1.85 km slope, fitted on Copernicus GLO-90 with the GAEZ slope rule; blind tiles 12/12 better (RMSE 0.308 ->
  0.184, bias +0.036). Map (harvest/export.py geometry, atlases with a terrain file): tiers 0.85/0.58/0.44/0.30 (were
  constants 0.85/0.75/0.45/0.08); land mean unchanged (0.744 -> 0.739). data/arable_slope_model.json.
* D2: irrigation x exp(-H / 10 m), H = height above nearest river; HID 1900 (Siebert et al. 2015) blind AUC 0.539 -> 0.671.
* Earth harness on both (scripts/land_people_earth.py defaults --arable slope --irrigation hand; ETOPO 60" via
  scripts/arable_slope_earth.py; irr_distance kept for water distance in polity/earth.py). FALLOW 0.68 -> 0.600 (NCP AD 2
  census). No-harm: regional populations RMS 1.701 -> 1.652 (Egypt worse: Nile floodplain wider than the 6 km distance
  rule); control dev BA Rome 0.8488 -> 0.8485, Han 0.6637 -> 0.6628 (whole Earth chain rebuilt in a worktree).
* D4 (roads) already on the eroded terrain by construction (travel graphs use the atlas elevation). D3 (valley towns)
  inherits through density (D1) and the site score's flat-ground and river terms; no separate Earth refit yet.
* Release: scripts/release_d1_arable.sh + release_d1_arable_addons.sh (Earth-fit from the v2.1 checkpoint; free and
  Whittaker food chain refreshed in place, backups in output/atlas_d1/previous_atlases). Report: reports/ARABLE_SLOPE_20261108.md.
* D2b (plan_D1 "D2b", scripts/irrigation_reach_d2b.py): reach 6/12/24/48 km x H0 5/10/20 m scored on AUC + amount vs
  HID 1900 (arid cells); dev chose 6 km x 5 m; blind Americas (now spent) amount 2.51x -> 2.33x, AUC 0.725 -> 0.726: H0
  10 -> 5 m (harvest/export.py IRRIGATION_HAND_H0, land_people_earth.HAND_H0). FALLOW kept 0.600; regions RMS 1.652 ->
  1.653; Egypt +0.64 -> +0.72; control dev BA Rome 0.8485 -> 0.8485, Han 0.6628 -> 0.6628. ADOPTED. Wider reach ranks better but over-irrigates more. Residual = Nile delta fan (12.5k km2 HID
  vs 5.2k model: distributaries) + arid rivers over-irrigated where 1900 is history-shaped (Mesopotamia, Niger).
  Exploration scripts/explore_irrigation_discharge.py (dev only; route over a domain 8 deg wider; burn NE rivers; WorldClim
  lakes passable). Map refresh: scripts/release_d2b.sh (Earth-fit only; it alone has a terrain file).
* Open: D5 control v3 needs a fresh blind pool (all identified pools spent); the evolve() m^4 units refit (B2, hill fit,
  plan_R1); delta-fan irrigation rule (Egypt), needs a reference/blind pool not shaped by 1900 history.

# Drawn rivers kept in the eroded map (plan_R1) + height map as climate lever (plan_T1) — 8 November 2026

* Owner: "all of our drawn rivers also have to be there in the eroded map". Strict check (scripts/terrain_rivers.py check):
  released v2 failed (1.3 % of drawn-river cells drained along the river; 0/107 rivers). Height map v2.1
  (output/terrain_erosion_20261107/map_height_v21.npz): 100 % / 107 of 107, 0 climbs, below every bank. Hybrid
  breach-fill bed at 0.6 x tier ramp + 11 px valley + banks +10 m + Barnes 2014b flats + PF-eps; Earth-fitted on the
  B2 ETOPO windows (joint loss 1.70 -> 0.72 dev, 1.35 -> 0.93 check); hills now tier-1 only, 1,600 m (Earth lowland
  KS 0.045). Tiers 2-4 band shares 0.984/0.516/0.862 (v2 0.962/0.495/0.832). Climate: +0.12 pts corrected vs v2,
  climate-grid river recall 0.65 -> 0.77. Report: reports/RIVERS_TERRAIN_20261108.md.
* Bug found: fastscapelib accumulate() multiplies by cell area; areas passed accumulate(dx^2) were m^4 (river boost
  inactive; "rivers_on_channel 1.0" and B2 M3 = 1.00 meaningless). Reported areas fixed; evolve() numerics kept
  bit-identical because every Earth fit used them. Fixing evolve properly = re-run B2 dev, hill fit, plan_R1 fit.
* plan_T1 (owner: height map helping the climate calibration, tiers intact): band position per upland tier gives
  +0.29 pts corrected (uplands low in their bands, both halves better) < frozen +0.5; ceiling of the lever +0.44.
  Steering tier-1 hills hurts (hills are zero-mean relief). Not adopted. The painted-zone misfit is lowland moisture.
* RELEASED 8 Nov 02:22 (smoke passes free/earth/whittaker; live r44-on-v2 backed up in output/atlas_r44r/previous_atlases).
  Hosted: earth v39 (447 changed files in 4 batches; *_tiers.webp still left out for the 511-file cap), free v35,
  whittaker v24 (13 changed add-on files each).
  Release: scripts/release_r44_rivers.sh + release_r44_rivers_addons.sh (checkpoint output/r44_rivers_world from the
  v2.1 climate check via scripts/make_release_checkpoint.py; params calibration/map_world_r44_terrain21). build_control_v21
  now shades with the atlas's own terrain_file.

# RELEASED: Earth-fit atlas r44 + height map v2 (task 84 + plan D) — 7 November 2026

* Params.terrain_file (rotclimate/config.py; geography.elevation_fullres, climate grid, render.py, atlas.py) -> height
  map v2 everywhere in the Earth-fit atlas (calibration/map_world_r44_terrain/params.json). Climate check (plan_D):
  strict zone agreement +0.73 raw / +0.60 corrected, |dT| 0.39 C. r44 corrections in the corrected climate.
* scripts/release_r44_terrain.sh (staged base) + scripts/release_r44_addons.sh (promote + all add-ons, compute ->
  publish order); live r43 backup local in output/atlas_r44/previous_atlases/earth_fit_r43. Smoke passes all three.
* free_fit / whittaker_fit keep the tier ramps (height map v2 is built on Earth-fit tier tops); their add-ons were
  recomputed consistently. Report: reports/R44_TERRAIN_20261107.md.
* Hosted (republished 7 Nov): earth v35 (4 batches; 492 data files, *_tiers.webp left out for the 511-file cap),
  free v34 and whittaker v23 (22 changed add-on files each; .gz sent as application/wasm).

# Owner: unmarked hills allowed; deserts may be holes — done 7 November 2026

* Height map v2 revised (plan_B2 map_v2_B3_revision_1): no tier compression; Earth-fitted unmarked lowland hills
  (terrain_erosion.hills: 2nd steady-state run, log-normal uplift 80 km / sigma 1.2 / 1,000 m, soft cap 500 m) so
  tier-1 slopes of ~9 km block means match Earth lowlands (median 0.160 vs 0.167 deg; KS 0.069; hill_fit.json).
  Tier-1 elevation p90 164 m, p99 502 m. Rivers 100 % on channels. Climate still on today's elevation.
* plan_A3: enclosed pockets with median P/PET < 0.2 or < 0.5 people/km2 stay holes. Blind 1200 / 1820 / 1500 (spent):
  BA unchanged (0.744 / 0.360 / 0.600) -> adopted. Map: 0.1-0.85 % of land returns to holes.
* Earth-fit control v2.1 shading now from height map v2 (display only; free/whittaker keep their own tier shading).
  Hosted: earth v31, free v33, whittaker v22. Next for the owner to choose: plan D rebuild on height map v2.

# A2 / C1 results: borders follow food, towns and enclosure, not slope, ruggedness or forest — 7 November 2026

* A2 (plan_A2.json): ruggedness travel cost (1 + beta R) lowers dev BA for all beta > 0; beta* = 0; blind pools
  1200/1820/1500 NOT opened (released unused in dataset_usage.json).
* v2.1 cartography + painted claims (light tint + fine line where claimed but unheld). Hosted: earth v30, free v32,
  whittaker v21. Smoke passes.
* C1 (plan_C1.json + amendments 1-2, REVEALS TW6 in data/cache/reveals_20261107, CC BY 4.0): Whittaker biome lookup is
  wrong for temperate Europe (woodland/shrubland -> 0 forest; open land overstated by 0.29). Adopted C1b: forest =
  clip((P/PET - 0.3)/0.2) x clip((GDD5 - 300)/300) x 0.60 (blind open-land RMSE 0.326 vs 0.556). Population clearing
  not adopted (0.346). No rank skill anywhere (|rho| <= 0.11). C1b not yet wired into the map (C2 travel test pending;
  effect is a near-uniform ~10 % friction change).
* Report section 8 lists options for the owner: D rebuild on height map v2; cartographic frontier smoothing; C2.

# B done to owner review: height map v2; discs are the travel model, not the terrain — 7 November 2026

* plan_B2 (amendment 1 before blind): C* (m 0.35, noise 24 km, sigma 0.6, boost 10,000 km2, no smoothing) adopted:
  blind divides better 3/4 (Guizhou worse), slope KS 4/4. Map v2 = ramps + compressed eroded detail (tier 1 x0.50,
  tier 3 x0.82), rivers 100 % on channels, bands pass the Earth reference - 5 pts; climate keeps today's elevation.
  output/terrain_erosion_20261107/map_height_v2.npz (committed); review figures reports/figures/height_map_v2_review_*.png.
* KEY: real-terrain 2-day Tobler zones are discs too (IoU 0.92-0.98 vs ramps, circularity 1.15). Next: Earth-fit a
  terrain-channelled travel cost (pack animal / cart slope response, valleys, passes) + two-state border test
  (CHGIS 1200 Southern Song vs Jin, declare first), then C land cover, then D rebuild. Downstream waits for the owner's
  look at the height map.

# Geography plan: A shipped (control v2.1 default); B generator + Earth test running — 7 November 2026

* Owner: "go with what you think" -> recommended defaults (tiers kept at climate scale with Earth-like relief inside,
  rivers within 1.8 km, ungoverned pockets as an explicit class, order A -> B -> C -> D).
* A (plan_A.json): summed influence C* (tau 2 d, lone reach 2.5 d) dev mean BA 0.763 -> 0.820 but blind late antique 550
  0.752 vs v2 0.766 (fails by 0.004; dense Pleiades sources inflate a sum). Fallback F = v2 + enclosed pockets passed
  (Song 1080 0.697 -> 0.737, 550 0.766 -> 0.774) -> atlas default "v2.1" (scripts/build_control_v21.py; flat fill over
  hillshade, border lines, hatched unadministered upland 2-3 % of land, MMU 3 cells). Hosted: earth v29, free v31,
  whittaker v20. Round-2 idea: saturating union 1 - prod(1 - p_s) instead of a sum (needs a new blind pool).
* B: scripts/terrain_erosion.py = steady-state stream power (chi integral of k_sn A^-m on fastscapelib routing, k_sn
  rescaled to the tier ramps at 14 km; marked rivers burned + boosted). Map preview uncalibrated
  (reports/figures/terrain_erosion_preview.png). Earth test scripts/terrain_earth_b2.py (plan_B2.json, ETOPO 60"
  windows in data/cache/etopo2022_60s via OPeNDAP). First dev look (Apennines): divides 16.7 -> 11.5 km, slope KS
  0.59 -> 0.11, isochrone IoU 0.932 -> 0.951. Real terrain keeps only ~50-60 % of middle tiers inside their bands, so the
  map's faithfulness check uses the Earth M5 reference. M3 (new rivers at 500 km2) is degenerate (sketch covers them).

# Owner: control v2 is dotty; geography should shape borders -> plan written — 7 November 2026

* Diagnosis (output/control_v2_20261107/diagnostic_dots.json, reports/figures/control_v2_dots_diagnosis.png): map slope
  median 0.025 deg vs Earth 0.30 (tier 1 = 70 % of land spans 0-62 m; tier ramps are smooth domes); small held patches
  circularity 0.96 (2-day discs); 161 enclosed holes (141,000 km2) are uplands (765 m vs 39 m, forest 40 vs 20 %).
  Earth: Roman/Han frontiers enriched on desert edges (56 vs 12 %, 25 vs 7 %); relief/rivers mixed.
* Plan: reports/GEOGRAPHY_CONTROL_PLAN_20261107.md. A (summed influence, governable-hole rule, cartography), B (eroded
  height map: stream power + imposed marked rivers + tier projection at climate scale; Earth "posterize and
  reconstruct" test), C (forest: PNV + KK clearance, REVEALS blind), D (rebuild chain, control v3), E (crossings,
  passes, soils, coasts, floods). Owner decisions listed in section 5 (tier strictness, river exactness, holes, scope).

# r44 on the map: raw climate IDENTICAL; corrections retrained — 7 November 2026

* scripts/check_r44_map.py (output/r44_map_check/summary.json): map world (seeds 1-3, downsample 8) under r43 and r44
  (calibration/map_world_r44/params.json = r43 world + four e72 fields): T, P, u, v max |diff| 0 (bit-identical; no map
  plateau). r44 corrections (calibration/earth_correction_r44_20261107; held-out T MAE 1.506 vs r43 1.537 C, rain loss
  0.4318 vs 0.4384) move the corrected map -0.39 C mean (|d| 0.41, p95 0.77, max 1.30 C), rain ratio median 0.998
  (5-95 % 0.925-1.083); corrected strict zone agreement 37.70 -> 37.83 %. r44 checkpoint: output/r44_world/ (local).
* NOT yet released into atlases/earth_fit: the corrected-mode cascade (add_corrected_climate.py, then pasture, farm work,
  administration, coverage, presence, settlement fertility chain + control v2) must rerun on the r44 corrections; the
  atlas stays r43-labelled until then. Raw-mode packets need no change.
* Sealed set h declared (calibration/sealed_20261107h, eight unseen climates) for the next climate milestone (P8).

# Control map v2 PUBLISHED as the de facto default; settlement model blind-tested — 7 November 2026

* Supply-supported reach opens on v2 (joint365 staffing + P2: staffed towns and the painted roads within 2 year-round
  days of them; held where the nearest polity <= 2 days). Built by scripts/build_control_v2.py (output/control_v2_20261107):
  held land free 65.2 %, earth raw 66.0 %, earth corrected 67.2 %, whittaker 63.8 %. The publisher adds the option
  (publish_settlement_integration.py --origin output/settlement_fertility_20261106). Smoke passes all three (local + packed earth_fit).
  Hosted: earth v28, free v30, whittaker v19 (only changed files sent: page, evidence.js, settled-reach.js,
  data/settled_reach.json, v2 webp; earth_fit now 494 files).
* polity/settle.py restored to its reviewed bytes (the settlement chain hashes it); the configurable calibration copy is
  polity/settle_experiments.py (identical towns at default arguments).
* Unmarked settlement model (calibration/settlement_model_20261107/plan.json, reports/SETTLEMENT_MODEL_EARTH_20261107.md):
  fitted weights NOT adopted (G2 fails by 0.003). Current model blind: Sui 610 count +11 %, F1 0.48 at 25 km, block rank
  0.29, AUC 0.63 for 1300 cities beyond the limes. Towns too even (spacing KS 0.76): real clustering is population
  history, so next step is a time-dependent population ledger as the density input (task 83 + F15b). S1/S2 spent.
* Round 2 (plan_round2.json): towns on the Earth-tested cored density (old heartlands, L 800 km). Dev mean F1 0.453 ->
  0.533, block rank 0.274 -> 0.512. Blind Tang 742: F1 0.538 -> 0.551, M1 0.40 -> 0.50, KS 0.80 -> 0.74, but count -20 %
  (G4) and 1300-city AUC inside the limes 0.771 -> 0.754 (G5) fail: NOT adopted. Round 3 idea: E1 count from the bare
  density, sites from the cored; needs a new blind pool (no unspent AD~200 site pool known). Tang 742 + 1300-inside spent.

# Fertility integration PUBLISHED — default bare three-field at AD 200 N 27.5 — 6 November 2026

* User chose: fix low-N artifact, then bare three-field default. Fix: residues scale with stand
  below 0.5 t grain (STAND_T; option, rounds 1-2 reproducible); recheck on spent data: dev loss
  0.1711 -> 0.1705, Broadbalk 1926-67 unchanged.
* Map (bare / joint365): sources free 201/1,207, earth raw 278/1,044, earth corr 273/1,064,
  whittaker 333/1,053; cereal 0.53-0.84x; access 2-3 vs 7 bins. Clover third: 614-1,010 sources.
* Published into atlases (publish_settlement_integration.py --origin
  output/settlement_fertility_20261106); viewer default fert_bare. Hosted artifacts republished
  (earth v25, free v27, whittaker v16) incl. coverage/administration/presence/pasture/farm-work.
  Packager fixed (raw feature packets, manifest .wasm refs, .gz as application/wasm); hosted
  earth_fit drops tier twins (511-file cap). Smoke passes all three.
* Report: reports/FERTILITY_INTEGRATION_20261106.md.

# r44 ADOPTED (r43 + e72d plateau-steered storms) — 7 November 2026

* e72c failed sealed set f (S 1.011, eastern Siberia); e72d (reach 15 deg, split jet) after declaring set g:
  S49 0.9902, 28 km 0.9859, unseen set g 0.9785 (five boxes; yunnan excluded before outcome: overlaps policy-v2 sealed).
* r44_params.json + r44_adoption.json (calibration/local_accuracy_20261023). Sets f and g spent; next unseen set must be
  declared before further climate development. Audit now reads every calibration region file.
* Map worlds unchanged (no plateau > 2.5 km). Next release step: retrain Earth corrections on r44, rebuild + republish
  the Earth-fit atlas (corrected default climate changes).

# P6 East Asia: e72c (plateau-steered storms) QUALIFIES on development data — 7 November 2026

* e72 (band meets plateau) inert: model band 40-53 N over East China all year. e72b (cold-season gate, window terrain):
  East China x0.904, S Brazil x0.880 but East Asia short. e72c (global 0.5-deg plateau ring, earth.plateau_profile):
  k10c East Asia rain x0.947, all-31 x0.987, T x0.990.
* Policy v3 gate (plan_gate.json): S49 0.9912 (T -0.86 %, P -0.89 %), S28 0.9859: PASS. retired_b 1.013 (reported).
* NOT adopted yet: the unseen sealed stage needs set f, which stays closed until the owner releases it.
  Candidate: calibration/east_asia_p6_20261107/candidate_e72c_k10c_params.json. Map world unaffected (no plateau > 2.5 km).
* Report: reports/EAST_ASIA_E72_20261107.md.

# Earth control round 2 + BLIND test — no food case passes; transport only stays default — 7 November 2026

* Round 2 (dev, plan d9d2ff99): scaled rural claim L1 (0.6 x produced) + reach P2 (staffed towns + roads within 2 year-round
  days): Rome 0.835 vs legacy 0.820, Han 0.682-0.692 vs 0.700; bare staffs 84 % / 92 % (40 / 76 % before).
* Blind (plan 092f4ab4, Pleiades Hellenistic 200 BC + Neo-Assyrian 700 BC vs Cliopatria any-state; now SPENT): G2 passes
  for all food cases (legume 0.654 vs 0.649, 0.612 vs 0.606), G1 fails in B1 (staffed 49-73 % of Pleiades settlements,
  which include villages). No default change. Lesson: next blind pool needs documented administrative/urban centres.
* e72 storm_plateau (P6) implemented opt-in (bit-for-bit off), dev31 screen running (output/east_asia_p6_20261107).
* Queue: reports/CONTROL_MAP_V2_PLAN_20261107.md (control v2, settlement spread, population; Domesday 1086 blind).

# Earth control test — transport-only map is the DEFAULT again (frozen rule) — 6 November 2026

* Plan d1935f2b (before results); scripts/earth_control_test.py runs the atlas chain on the Rome (Hanson AD 150 +
  Itiner-e) and Han (AD 2 seats) Earth windows. Report reports/EARTH_CONTROL_20261106.md; output/earth_control_20261106.
* BA Rome / Han: legacy_0 0.820 / 0.700; reference 0.697 / 0.641; joint365 0.698 / 0.633; legume 0.689 / 0.630;
  bare 0.606 / 0.603 (staffs 40 % of Roman towns, 76 % of Han seats). No food case passes G2; bare also fails G1.
* Default -> legacy_0 on Supply-supported reach and Settlements (atlas/settled-reach.js); "; default" dropped from the
  fert_bare label; every scored case's note carries its Earth result (publisher reads results.json); badges updated.
* Cause (post hoc): the every-month staffed-source patrol rule (no roads) loses 0.06-0.12 BA before food; bare fallow
  breaks the fixed rural claim (0.6 x old harvest) where F < 0.6 -> 23 % rural need unmet in Rome, no surplus.
  Next: rural claim scaled by F (one ledger); reach rule closer to transport (roads, year-round days); blind pools.
* Date palms: September harvest (perennial, no crop-window calendar), fixed before any Rome result.

# Atlas core view + evidence badges — PUBLISHED (3 atlases + hosted v26 / v17 / v28) — 6 November 2026

* atlas/evidence.js: tier + Earth test for every layer id (fallback by topic) and for the settlement /
  supply options (reach_defacto, reach_towns). Tiers: earth / partial / scenario (core view) and
  experimental / diagnostic (behind the "Experimental & diagnostics" switch). Sources: evidence_spec.json
  + reports (R43, POLITY_V3 / STRENGTH / SEASONS, FORAGING_EARTH, LANGUAGE_AREAS, FERTILITY_INTEGRATION).
  Painted-world atlases (no corrected climate / physics_profile) mark climate "partly tested".
* index.html: CSS-drawn badges (shape, not colour), topic names carry their best tier, legend ends with
  "Evidence: <tier>. <test>", minor sensitivities hidden from the option list (core: fert_bare default,
  fert_legume, joint365, legacy_0 = the only option scored on Earth as a control map, 0.81 / 0.80).
  Deep links to hidden modes turn the switch on; #all=1 and localStorage rotclimate-all keep it.
* Earth-fit core view: 56 of 82 layers, 11 of 15 topics. Smoke test records the core view, then checks
  every layer with the switch on. Update evidence.js when a layer's test status changes.

# Fertility integration (AD 200 N 27.5) — COMPUTED, NOT PUBLISHED, default undecided — 6 November 2026

* harvest/fertility_regimes.py (vectorised emulator, validated within 4 %, bare-fallow 19 % low),
  scripts/fertility_integration.py (earth / earth_figure / maps), scripts/extend_settlement_fertility.py
  (fert_transfer/bare/legume cases on the SAME chain, all 9 earlier cases kept), publisher note.
* Factor F = Y_land(regime) / (0.68 A0) (absolute; first ratio pass exploded, superseded before publish).
* Earth anchor: NCP needs no transfer (water-limited; m* = 0) -> transfer = bare. Census mean |log10|:
  previous 0.538, bare 0.407, legume 0.682 (Gaul 0.10-0.22 -> 0.55-1.24; Sichuan 0.09 -> 0.59).
  [Superseded by the stand-residue rerun 9decd991: bare 0.459, legume 0.685; Gaul 0.31-0.69, Sichuan 0.29.]
* Map: bare cuts wheat/barley grain to 0.42-0.77x and staffed sources ~1,000 -> ~200-330; legume
  1.2-1.5x grain. Zero-grain cells below 26 kg N uptake are a residue-relation artifact.
* Viewer default reverted to joint365; nothing written into atlases. Waiting on user's default choice.
  Report: reports/FERTILITY_INTEGRATION_20261106.md.

# Soil fertility ROUND 2 — credible equilibrium, QUALIFIES blind on Broadbalk 1926-67 — 6 November 2026

* Plan 517f33da (before fit/test read) -> amendment d5b57277 (crop N-demand curve; the
  only one; superseded fit A kept) -> selection 4d282c4c -> single eval 47a05f5c.
* Changes (options in harvest/soil_fertility.py; defaults reproduce round 1 bit-for-bit):
  measured start SOC (Broadbalk 28.8 t C 1843 e-RA; Hoosfield 33.8 RothC), I = F + measured
  wet deposition (Goulding 1998: 4 kg 1855 -> 18 kg 1980), thermal uptake in vegetated months
  capped by demand curve, fitted FYM humification (returned RothC 0.02), clover residues cut.
* Fit (spent data + Broadbalk SOC <=1914 + rwf3 aggregate): F 43.4, uptake 0.15, kappa 2.26,
  M0_woburn 1.55. FYM SOC matched; fallow +0.29 vs +0.14 long run; plot-3 SOC stays ~30 vs 24.
* Broadbalk 1926-67 (strips 3/21/22, 5 sections with fallow 1-in-5): T1 level 0.154 vs existing
  0.219, bias -0.065 (round 1 0.259, FAILS); T2 manure 0.137 vs null 0.322 r .15; T3 fallow
  0.135 vs 0.282 (obs x1.91, model x1.48; weeds not modelled). QUALIFIES. Now SPENT. Note 13
  of that dataset quoted one strip-14 value (not a target).
* Equilibrium (scripts/soil_fertility_regimes_r2.py sweep): at fitted ~52 kg input unmanured
  continuous 0.87 t/ha (Broadbalk plateau). Bare fallow ~no per-crop gain in equilibrium,
  halves per-land output. Clover rotation and FYM dominate.
* AD200 HINGE: non-fertilizer N input. Fitted value lumps real inputs + model loss error.
  Literature ratio pre-industrial / 1850-1925 ~0.4-0.65 -> 20-35 model kg -> per-land yield:
  unmanured 0.2-0.5, bare-fallow systems 0.07-0.25, W/B/clover 0.8-1.0, 5 t FYM 0.8-1.1,
  10 t FYM 1.4-1.7. Needs a decision or a further constraint.
* Next: integration step (declared): AD200 input; regime as land shares (crop / fallow /
  legume / pasture -> manure); per-cell equilibrium grain per land ha from climate + soil
  class (replace Rothamsted soil); feed shared grain -> residents -> reach. Check kappa
  outside England.
* Report: reports/SOIL_FERTILITY_ROUND2_20261106.md.

# Soil-fertility state (RothC + N) — QUALIFIES blind on Exhaustion Land — 6 November 2026

* NEW `harvest/soil_fertility.py`: RothC-26.3 carbon (published constants, from
  RothC_description.pdf) + SUNDIAL-style N (BIO/HUM C:N 8.5), one mineral pool,
  uptake, Burns single-reservoir leaching with dual-ledger drainage. N ledger
  closes. Drivers `scripts/soil_fertility_common.py`.
* Protocol: plan 288d1eaa (before any fit or Phase II read) -> amendment 7aaddff3
  (Hargreaves x monthly factors to RothC's Rothamsted 0.75*pan table, 448 vs 717
  mm/yr; spin-up 25 t C vs RothC 31; drainage 190-250 mm/yr vs 94) -> selection
  66c67e7b (fit on SPENT Broadbalk + Woburn: I 23.8 kg N/ha/yr, uptake 0.20/month,
  kappa 2.26 x A0, prior manure 2.42 t C/yr) -> single eval 55774a8a.
* Exhaustion Land 1902-1935 (rex4, CC BY; plots with 1856-1901 histories, nil
  since 1902, clover 1905/06-11 on 5-10): M1 manure memory 0.163 vs null 0.322
  r .68; M2 legume memory 0.212 vs 0.300 r .65; M3 level 0.161 vs existing 0.223
  (r .61 vs existing -0.59). QUALIFIES. Now SPENT. Misses: manure memory decays
  too fast (known RothC miss on Hoosfield 7-1), clover overpredicted, P/K adds.
* Disclosed: rwf3 (wheat-fallow) page aggregates seen -> development only. Scorer
  crashed twice before any output (serialisation; path); rerun deterministic.
* Woburn caveat: "unmanured" stratum includes plots 10a/11a after their 1877-81
  FYM; never-manured plots 1 and 7 run down MORE (wheat -42/-44 %, barley
  -70/-51 %). Report amended.
* NOT READY FOR PRODUCTION: regime preview (`scripts/soil_fertility_regimes.py`)
  equilibrium continuous unmanured 0.46 t/ha (Broadbalk plot 3 held 0.7-1.0 for a
  century with ~constant SOC); bare fallow no benefit (rwf3 says +0.14); floor
  collapses at lower N input (AD200 pre-industrial deposition is lower).
* Next: constrain equilibrium on development (Broadbalk plot-3 SOC stability +
  yield plateau, rwf3 aggregate), revise clover residues, ground AD200 N input
  (deposition + free-living fixation), then a fresh reserved test (Saxmundham
  rotations?). Regime choice (fallow/manure/legume) belongs to the shared
  settlement chain (manure <- livestock <- pasture), not a new map.
* Report: reports/SOIL_FERTILITY_20261106.md.

# Crop-water ledger + Woburn reserved site — 6 November 2026

* User priority: the Earth-calibrated basis for the control map (grain ->
  residents -> institutions -> reach). Post every figure as it is made.
* NEW `harvest/soil_water_dual.py`: FAO-56 dual coefficient (Allen et al 1998
  ch7 eq69-79 evaporation layer, ch8 eq81-88 root zone). ONE store; T and E are
  each debited once; drainage above field capacity; storage carries across seasons
  (no free sowing refill). 6 tests in `tests/test_soil_water_dual.py` (closure,
  bounds, bare soil <= TEW, no double spending, reduces to `soil_water_year`,
  stage-1 rewetting). Production still uses `harvest/soil_water.py`.
* Broadbalk DEVELOPMENT diagnostic (spent pool; declared in
  `calibration/low_input_yields_20261105/water_ledger_development.json`;
  `scripts/broadbalk_water_ledger.py`; output/broadbalk_water_20261106).
  Closure 1e-12 mm over 48 yr. Wetter = LOWER yield on every measure (winter
  drainage r -0.24 plot3 / -0.40 FYM; season E -0.43/-0.35; T ratio -0.19).
  Water is not limiting; explains old r -0.38. Drainage only ~94 mm/yr (Hargreaves
  high in humid climate, July 146 mm); drain gauges DR20/40/60 need an e-RA
  account -> not used. Leaching fit k=0.109/100 mm, LOO skill ~0.
* Woburn: own met starts 1928 (station WMS), trials end 1926 -> matched weather
  will never exist. Frozen `woburn_plan.json` BEFORE reading yields declared
  Rothamsted (~40 km) as a regional proxy (not silent). Amendment
  `woburn_amendment.json` before scoring (lime coded L0, DD/MM/YYYY sow dates;
  the first run selected 0 rows, nothing seen).
* RESULT (`scripts/woburn_yields.py`, output/woburn_yields_20261106): wheat
  unmanured n21, obs 0.98 t/ha: A0 logMAE .150 r -.23 skill -.12; A (x0.933) .154
  skill -.16; B (A + leaching) .152 r -.11 skill -.18. NOT QUALIFIED; no
  production change. Barley A0 r +.14 skill +.12, A/B worse.
* KEY FINDING: unmanured plots RUN DOWN, manured hold. Barley unfertilised
  1880-84 1.87 -> 1895-99 0.84 t/ha (-55 %), FYM 2.64 -> 2.23 (-16 %); wheat
  1.21 -> 0.77 (-36 %) vs FYM 1.80 -> 1.60. Run-down floor at both sites
  0.7-0.9 t/ha (Broadbalk 1901-25 0.69) ~ model level. Missing component is a
  SOIL-FERTILITY (nitrogen) state driven by land-use history, not water.
* Woburn strata now SPENT (dataset_usage.json `era_woburn_wheat_barley_1877_1926`).
  Broadbalk already spent. Reserved climate f untouched.
* Next: literature-grounded soil-N state (run-down under continuous cropping,
  recovery under fallow/manure/legume rotation), developed on spent Broadbalk +
  Woburn, evaluated on a genuinely separate record (e.g. other Rothamsted
  classicals' early years, Hoosfield aggregates already seen -> not usable as
  blind). Any qualifier feeds the shared grain -> residents -> reach chain.
* Report: reports/CROP_WATER_WOBURN_20261106.md.

# Historical wheat yield benchmark — 5 November 2026

* Latest user priority remains Earth calibration of all components, with utility
  budgets feeding shared settlements/control. No new independent map family.
* New direct historical benchmark, not simulated climate: Broadbalk wheat yields
  + Rothamsted observed monthly temperature/rain. Sources CC BY4.0, pinned under
  `calibration/low_input_yields_20261105`; cache `data/cache/era_low_input_20261105`.
* Preregistration `0ffa8aac`; disclosed input-availability amendment `0e016777`
  BEFORE numerical yield scoring. Original complete-temp rule gave only15 train
  years. Accept provider means missing at most1 daily temperature reading per
  month; retain complete-record test subset. Keep20-year minimum and split.
  Source harvest1883/sow1886 impossible date EXCLUDED, not silently repaired.
* Selection+producer frozen `67b7aa1c`: 20 training primary years1879–1900, 25 test
  years1901–1925. Same physical unfertilized plot3 in both: TEMPORAL at ONE SITE,
  not independent geographic validation. FYM/mineral/other strata kept separate.
* Grain source units t/ha/year already, ~85% dry matter (not measured). Unit in
  workbook fields_metadata, absent JSON field schema. Do not divide by area
  again or compare gross grain to calories after seed/milling losses.
* Mean-temperature column blocks, NOT monthly extremes. DTR is monthly means of
  daily Tmax–Tmin. Rain missing-day counts flagged; trace-only0.05mm/day bound is
  conditional, not proved error bound. RAIN5 historical substitution retained.
* Chronological Sep(previous year)–Aug(harvest year), no cyclic window wrap or
  future autumn leakage. Existing wheat response with sequential100mm reference
  soil state, still NOT a crop-specific transpiration/evaporation ledger.
* RESULT: yield scale0.933. Test logMAE .21287 -> .19930 (6.4%); RMSE .40836 ->
  .36911t/ha; r=-.37786; RMSE skill vs training-mean constant remains -15.3%.
  FAILS qualification despite level improvement. Strict-complete23-year subset
  also fails. NO AD200 or production crop/climate/population/control adoption.
* Actual winter dates: only2/25 seasons meet current temperature/length/heat
  rules;22 length failures,15 temperature failures (overlap),1 season outside
  fixed crop-year. Doesn't prove dormancy/waterlogging/nutrients causal.
* `check_earth_yields.py` independently replays metrics/grid/aggregate units and
  optional source rows. Frozen producer snapshot67b7 supports later code edits.
  180 year/management aggregates are45 shared weather years, not180 independent
  experiments. Public packet/CSV/scores/plot in atlas Earth evidence page.
* Broadbalk scored pool now SPENT. Woburn wheat+barley files pinned/downloaded,
  targets UNOPENED/UNSCORED pending observed local weather (Rothamsted cannot be
  silently treated as Woburn station). Hoosfield aggregate means already seen
  during source discovery. Reserved climate f not opened/run.
* Next mechanics: chronological conservative crop-water ledger, separating crop
  transpiration from bare-soil evaporation/drainage (Allen et al1998 FAO56 ch8/9).
  Verify conservation and no repeated soil-water spending before fitting yield.
  Constrain winter phenology/management; earlier failed chilling-clock remains
  rejected. New mechanisms may use Broadbalk explicitly as DEVELOPMENT, then
  evaluate on genuinely reserved data once matched inputs exist.
* Methods: reports/HISTORICAL_WHEAT_20261105.md. Standard `.bat` atlas hub links
  evidence with result, figure, protocol/amendment/source identities/downloads.
  Existing 4 production atlas folders unchanged; release/evidence hashes updated.

# Earth calibration evidence programme and failed split audit — 5 November 2026

* USER PRIORITY: calibrate every part on Earth as evidence permits. Prioritize
  observed processes and independent household/land/work evidence over more
  scenario maps. Keep all utility budgets feeding shared residents/control.
* First evidence ledger: 11 components / 551 selected numeric configuration
  records. `rotclimate/evidence_audit.py` and
  `calibration/earth_components_20261105/evidence_spec.json` distinguish
  published relationships, actual fits, definitions, scenarios and unreviewed
  evidence. Covers selected JSON and literal top-level constants, NOT every
  function-body coefficient; counts are not degrees of freedom or % calibrated.
* Open VDSA source DOI 10.5281/zenodo.8224522 (CC BY 4.0), files pinned with
  publisher checksums + SHA256. Fetcher never executes downloaded Stata code.
  Raw survey data remain cached, respondent names are not exported. Published
  pseudonymous task records permit independent replay without cached raw files.
* Preregistered plan/source in `e8e09152`, training selection/producer snapshot
  in `5ddb6d20`, before evaluation. Modern 2009–2014 manual wheat/barley task
  benchmark uses actual plot hectares, household size and human hours. Never
  treat wages as hours, output value as grain, or bullock hours as human work.
  Complete subplot/season keys; ambiguous repeats/bundled tasks excluded.
* IMPORTANT FAILURE: initial name-based district split had MAHARASHTRA versus
  MAHARASTRA (Akola) aliases. Independent replay found FIVE households in both
  folds, 7 observations each. Original 1,635-case validation claim is withdrawn;
  original computation retained. Entire affected evaluation district removed
  (29 records), leaving 1,606 wheat observations / FOUR districts, no panel
  overlap. Scale 3.432 not refitted. Restricted error .459 -> .176; within-factor
  two 20.9% -> 80.8% (equal-district weights). This is POST-AUDIT DIAGNOSTIC,
  not new untouched or fully prospective validation; no qualification claimed.
* New `harvest/panel_validation.py` guard rejects cross-fold households.
  Current benchmark runner refuses the flawed old split/stale identities; do
  NOT bypass it for a new fit. Original archived runner is in `5ddb6d20`.
  Publisher verifies historical producer identities against that Git snapshot.
  `audit_earth_reaping_panels.py` records failure and restricted diagnostic;
  `check_earth_component_results.py` independently replays both computations.
* ZERO cases pass strict recorded low-input screen; no evaluation barley.
  No AD200 default adopted, no model scientific outputs changed. 40% workforce,
  annual/reaping availability, rural demand, stores, imports and institutions
  remain scenario assumptions. Modern fit is not ancient technology calibration.
* Dataset exposure register marks evaluated pools spent and original VDSA
  evaluation flawed; reserved climate f was NOT opened or run. A new study
  needs canonical place IDs/panel integrity and independent evaluation data.
* Normal hub has Earth calibration evidence page (`atlases/earth_evidence/`):
  searchable ledger, graphs, full source/plan/audit downloads and visible caveats.
  Hub text corrected so legacy Han/Roman tests do not validate new food/control
  coupling. Methods: `reports/EARTH_COMPONENT_CALIBRATION_20261105.md`.
* Next: canonicalize geographic identities BEFORE any new fit; acquire matching
  historical/low-input crop/area/work records. Investigate workload per area
  versus harvest mass without selecting a mechanism on this spent pool. Replace
  rural food claim + workforce together from independent compatible households;
  then storage/imports/freight, settlement sizes and actual institutional reach.
  Census capacity fits identify products of yield/area/cropped share/food need,
  not each factor separately. Do not add independent final utility families.

---

# Listed cereal work → food → settlements → reach — 5 November 2026

* Previous integration milestone `cbed21e5` is pushed to BOTH publication refs.
* Added three explicit work sensitivities to the SAME settlement/reach modes:
  `work600_30`, `work600_10`, `work300_30`. Keep food-only default `joint365`;
  no empirical worker calibration selects a new default. All earlier six cases,
  summaries, collection assignments and masks are preserved EXACTLY.
* `harvest/field_support.py` limits complete annual cereal activities by listed
  total and reaping work of the SAME reference workers. Reaping is a subset,
  not double-counted hours. Rural meals remain fixed when grain production
  falls; a deficit cell exports nothing. The resulting single grain ledger
  changes residents, institutional availability and same-source paired reach.
* Reference workers = 40% of the earlier fixed rural cereal-food claim divided
  by 2,500 kcal/day. This is an internally testable food/work allocation, NOT
  observed/census residents. It inherits the baseline claim's dependence on
  potential production. Future population calibration must change the rural
  food claim AND worker anchor together. Never add these scenario people to
  census/occupation/FORGE/pastoral totals.
* Earth corrected: 600 h / 30 d retains 99.79% of grain and 1,062 sources;
  600 h / 10 d retains 1,059; 300 h / 30 d retains 994 versus food-only 1,064.
  Food-only → tighter annual-work access: 7.36 → 6.83 area-weighted bins.
  Other climates lose 31/80/53 sources in the tighter annual-work case.
* `scripts/extend_settlement_labour.py` reuses the frozen first-stage cases;
  sources/inputs hashed, checkpoints reusable. Publisher now takes `--origin`
  and publishes this extension from `output/settlement_labour_20261105`.
  IMPORTANT: invoking publisher with no origin republishes the earlier six-case
  version; use the extension origin for the current release.
* New source/cell work audits, figures and methods in
  `reports/SETTLEMENT_LABOUR_20261105.md`. Normative Columella field counts and
  FAO simultaneous-resource budgeting motivate the mechanism, not worker shares,
  actual deadlines, complete household work or historical productivity.
* Existing viewer selectors expose all three work cases, their budgets/fixed
  rural deficit, CSV fields and downloadable cell audits. Work is partial:
  draft services, other foods, household tasks, processing, water volumes,
  labour exchange/mobile communities and political rights remain unresolved.
  Future utility budgets must constrain this SAME allocation and broad actor
  scope, not create independent final map families or ecology→institutions.

---

# Joint food → settlement → available reach sources — 4 November 2026

* Implemented the user's requested loop into the EXISTING `reach_towns` and
  `reach_defacto` modes, all four climate packets. Default is `joint365`, with
  a transport-matched unconstrained reference, 90/no origin stores, 1% collection,
  smaller 25-person cohort and explicitly labelled legacy comparisons.
* New core `polity/settlement_support.py` solves a seasonal resident ceiling,
  then allocates requested civilians and institutional residents from ONE
  conserved pool. A community can persist without a cohort. Only available
  affiliated cohorts emit same-site two-way reach; no population-power weights.
* All 151 marked icons join bijectively using grid coordinates and kind, with
  coastal snapping kept separate. Raw art pixels differ from atlas pixels.
  Co-located markets merge. Unknown marked affiliation never inherits claims;
  generated-site claim affiliation remains an explicit hypothesis.
* Earth corrected: 1,085 candidates; year-store case has 1,082 communities and
  1,064 staffed sources versus 1,074 reference sources. Civilian requests fall
  from 3.44 M to a 0.79 M alternative allocation; this is NOT a census revision
  or validated town-size prediction. 1% collection leaves 107 sources and
  1.44 area-weighted access bins versus 7.40 reference / 7.36 year-store.
* Candidate generation and path friction remain fixed across cases. Food
  collection has local road/foot eligibility, no sea imports or measured freight
  throughput. Staffed-source reach includes proposed person-transport links.
  Compare food effects ONLY with the matched reference, not the legacy engine.
* `scripts/review_settlement_integration.py` computes/reuses source/input-hashed
  reviews. `publish_settlement_integration.py` publishes optional runtime mode
  replacements without altering `atlas.json` or climate/crop/FORGE packets.
  `atlas/settled-reach.js` lazy-loads ledgers/masks; manifest or Harvest failure
  restores original modes. Missing detailed ledgers retain precomputed plates
  with a visible explanation. Controls remain conditional.
* Methods/scope: `reports/SETTLEMENT_INTEGRATION_20261104.md`; literature access
  in `research_notes/settlement_integration_20261104.json` (Palmyra 2022 paper,
  Erdkamp publisher introduction, FAO storage). Coefficients remain scenarios.
* First integration only: other foods, household work, drinkable water volume,
  livestock nutrition, grain exchange, camps and rights are NOT jointly solved.
  Next work should constrain the same resident/source allocation with these
  budgets, not add independent utility map families or infer institutions from
  ecology. Retain broad polity/nonstate scope and explicit missing evidence.

---

# Required integration into settlements and control — user clarification

* The user explicitly requires ALL utility/resource maps to feed back into
  settlement and control predictions. Standalone diagnostics are intermediate
  evidence, not the development endpoint. Prioritize integration before adding
  further independent map families.
* Food, feed, storage, water, labour and transport must constrain a shared,
  conserved allocation: where communities can persist, their supportable size,
  seasonal relocation/supply dependence, and provisioned institutional presence.
  Apply this across imperial, other-state and nonstate/mobile scenarios.
* Next implementation milestone: supply-constrained settlement scenarios that
  consume the existing seasonal budgets, followed by supply-supported control
  scenarios anchored to those settlements/institutions. Show the causal path
  from resource constraint to changed settlement/presence/reach, alongside the
  baseline and uncertainty. Do not substitute a food/population power multiplier
  or assume that ecological feasibility proves staffing, allegiance or ownership.
* The first local-cereal integration is now implemented (see milestone above).
  Feed, household labour, water volumes, exchange and mobile-community
  allocations still need to constrain this same system; those utility layers
  must not be described as fully integrated. Missing evidence stays unscored.

---

# Readable circuit insets — 4 November 2026

* Continued after pushing `5d953c4c`, per the user's preference to keep working.
  A view-only follow-up makes compact circuits readable within regional tests.
* Inset defaults to route detail (at least eight fine-cell widths of context),
  with a Show whole tested landscape / Focus on route toggle. `pm_frame` is
  preserved in shared URLs and across climate/atlas navigation. No new map
  button or always-visible global selector was added; unscored cases hide it.
* Browser checks all four packets, both framing states, URL reload, identical
  food readouts/CSV before and after toggling, narrow/dark layouts, water cases,
  and optional-packet failure isolation. Science/data are unchanged from
  `5d953c4c`; its 122 tests and independent model review remain applicable.
* Screenshots/receipts: `output/inset_readability_20261104`. Normal `.bat` atlas
  copies and portable bundle are refreshed. Methods describe framing separately
  from the tested landscape extent. No simulation, recalibration or agents.

---

# Origin storage and regional resource circuits — 4 November 2026

* Continued `b919802e`. User said Continue. Same two normal atlas buttons,
  now 11 provisioning scenarios and 3 landscape tests (local; regional with
  sparse outer bases; regional with additional outer bases), all 4 climates.
  No climate, yield, ownership or population recalibration was adopted.
* `harvest/mobility_landscape.py` and `scripts/regional_resource_circuits.py`:
  regional radius 20 fine cells (~73.6 km), retaining the earlier radius-5
  (~18.4 km) bases. Add a stride-4 outer lattice, then offset (2,2). Keep the
  original herd, individual grazing footprint, 7-day pack, slope speed and
  2 travel-days/bin. Transit land supplies paths, never extra food at a base.
* Regional ground is the home-connected fine land component, with no water
  corner cuts. Each move includes its actual fine-node path. Location indices
  refer to candidate patches; segment indices refer to separate ground nodes.
  Grassland/Neck: 157/233 bases on 1,257 cells. Tarani: 70/107 on 608. Mixed
  resource anchor is an island with 13 connected cells; no overland expansion.
* Controls: fixed home; best fixed base over EVERY connected fine cell,
  including unsampled bases, with continuous reserves; optimistic per-bin
  single-patch maximum ignoring travel, with continuous reserves. The last
  is a RESOURCE UPPER BOUND, not a route. Both controls are unchanged between
  sparse/additional outer samples. Local → sparse → additional choices cannot
  reduce optimum feeding; independent review checks both nested comparisons.
* Same grassland example, regional additional bases, mobile versus best fixed:
  Free 88.60% vs82.74%; Earth raw86.73% vs88.42%; Earth corrected89.36% vs90.71%;
  Whittaker81.87% vs71.33%. This is climate-fit sensitivity, not proof of actual
  camps/nomads or ecological determinism. Anchors and return phase remain
  assumptions. Half-day reserve refinement changes support by at most0.137pp.
* Four new food cases vary ONLY origin stores (365→90/0 flow-days), collection
  (10→1% of rural overflow), or rural stores(365→180 demand-days). Destination
  stores/ration/paths/freight stay fixed. RuralFood.exportable centralizes the
  no-export-if-annual-rural-deficit rule; an early-glut/future-deficit test guards
  it. Original7 food cases/balances, local circuits and collection grids exactly
  match baseline values. No new food/power multiplier or population sum.
* Earth corrected fully supplied sites: baseline151;90-day origin store131;
  no origin stores0;1%collection92;rural180store0. The last is a CEREAL-ONLY
  rural ledger with protected meals, not actual famine. Origin tests retain
  the SAME prescribed dispatch policy; they aren't maximum trade capacity.
  Flow-days of annual exportable supply are not days of destination demand.
* Research: Brottem et al.2014 publisher ABSTRACT only on forage connectivity;
  Turner/Schlecht2019 mobility scale distinction; FAO bulk-storage sizing.
  No coefficients copied from inaccessible text or claimed as ancient facts.
  Protocol/limitations in research_notes/presence_mobility_scale_20261104.json.
* UI keeps 2 buttons, adds landscape-test selector and URL/CSV pm_scale state;
  origin assumptions visible in readouts/CSV. Main circuit image now follows
  BOTH water case and landscape test, with matching inset/ledger. Water-excluded
  home remains unscored. Core/frontier and irrelevant controls stay hidden.
* Methods: reports/PRESENCE_MOBILITY_SCALE_20261104.md. Builder records new
  receipts in output/presence_mobility_scale_20261104, preserving prior study
  outputs. Config data/presence_mobility_model.json v2; payload adds mobility_scales
  and complete fine-ground production/adjacency for independent controls.
* Validation:122 analytical/component tests; public review79,728 site-bin food
  ledgers,120 closed circuits,8 reserve refinements; exact baseline preservation;
  nested-choice and upper-bound invariants. Browser4 packets,11 food scenarios,
  2 mobility views×3 tests×2 water cases,3,024 CSV rows, URL/state/narrow/dark/
  downloads and4 failure fixtures. Existing3-atlas smoke passes. Windows and
  portable publication receipts accompany this milestone.
* Figures regional_circuits.png and origin_storage.png were posted. Next:
  standing forage/hay quality and its work/carry budget, home/return-phase
  sensitivity, watering and shared competing users. Preserve perfect-foresight,
  no-nutrition/no-demography/no-actual-camp caveats. Never infer polity types,
  absence of communities or sovereignty from resource feasibility. No agents.

---

# Sustained presence and seasonal resource circuits — 4 November 2026

* Continued `6949ea71`. User approved proposals 1 (food support) and 3 (mobile
  resource circuits). New normal atlas buttons: Political reach → Sustained
  presence (7 scenarios); Livelihoods → Seasonal circuits (2 views, 4 fixed
  landscapes, 2 water cases). All four matching climate packets are published.
  No climate, food-capacity, population or ownership baseline was changed.
* Methods/results: `reports/PRESENCE_MOBILITY_20261104.md`. Assumptions:
  `data/presence_mobility_model.json`. Primary mobility framing is Turner &
  Schlecht 2019; Roth 1999 was consulted only through metadata, not full text.
  Research access and coefficient limitations are recorded explicitly.
* `polity/sustained_presence.py`: all 151 verified marked sites, including 10
  with unresolved affiliation. A single published wheat/barley crop supplies
  protected rural meals, finite rural stores and separate on-farm export stores.
  No export from a cell with unmet annual rural demand. Seed isn't deducted
  twice; the legacy `NEED_KCAL` storage/draft allowance is never used.
* One cell supplies at most one site through a fixed base-bin parent-tree path;
  both directions along that same path must qualify each dispatch bin. Existing
  roads/terrain/weather/ford costs, constant off-path pace; no density feedback,
  generated tracks, ferries or river/sea freight. These are collection areas,
  not control polygons. Permission across painted claims is assumed open.
* Collection is 10% of rural overflow; origin stores hold a year of exportable
  flow, freight 5 tonnes edible cereal-equivalent/bin, delivery delay one bin,
  retention 95%, stored-energy loss 5%/year. Every quantity is a scenario, not
  measured ancient logistics. Group sizes 100/500, destination stores 0/90 days,
  two busy adjacent dispatch bins interrupted, alternative tied crop calendar,
  and a fivefold freight sensitivity. All stocks and in-transit food repeat.
* Earth corrected: 100-person baseline fully supplied at 151/151 sites; a
  two-bin interruption without destination stores at 0/151, with 90-day stores
  at 151/151. For 500 people, unchanged freight caps annual support around 41%
  by construction; fivefold freight fully supplies 135/151 sites. Food support
  does not establish actual staff, labour, shelter, pay, institutions or control.
* `harvest/seasonal_mobility.py`: exact dynamic programming on the declared
  finite location/reserve graph. One unsplit herd, 100 DM reference units,
  6.25 kg/unit/day, 7-day carried reserve in one-day increments. Transit meals
  use prior carried feed; destination food cannot feed the past. Only visited
  current-bin growth is collected, once. Same home AND feed at year end.
* Four previously fixed pasture examples, radius five cells (~18.4 km): Tarani,
  two landscapes outside named claims, and Neck. Not observed camps or societies.
  Reference movement 10 km/day modified by slope, maximum two travel-days/bin.
  Water sensitivity applies to occupied bases within 10 km of mapped water;
  an excluded home is unscored, not proof of no water or impossible occupation.
  Enroute watering, potable volume, wells, carry effort, nutrition and herd
  demography remain unknown. The assumed seven-day pack is 4,375 kg DM.
* Critical control: Earth-corrected fixed home → circuit → best fixed base:
  Tarani 36.6 → 75.1 → 76.0%; grassland 85.6 → 88.4 → 88.5%; mixed resources
  98.2 → 98.3 → 98.4%; Neck 84.8 → 96.2 → 96.2%. NONE beats the best fixed
  base (continuous reserve). Don't portray gains against arbitrary homes as
  evidence that mobility wins. Half-day reserve refinement changes support by
  at most 0.137 percentage points. Perfect foresight of a climatological year;
  finite-graph optimality is not global physics or historical validation.
* `scripts/build_presence_mobility.py` pins sources/inputs/public assets and
  reuses matching complete packets. Public gzip JSON includes stocks, patch
  production, adjacency and actual intermediate paths. Catchments are row-major
  little-endian uint16, 0 unassigned, otherwise site index+1. No joint allocation
  of the four independent herd experiments or addition to population totals.
* `atlas/presence-mobility.js`: matching Harvest/gzip identities, conditional
  controls, URL state, selected-site 84-row CSV and herd 24-row CSV, route inset
  with patch letters and seasonal table. Site selection updates the climate at
  the snapped source cell. Missing/bad packets remove only these two layers;
  a pasture failure retains Livelihoods when circuits are available.
* Validation: 116 analytical/component tests; independent public checks of
  50,736 site-bin ledgers, 40 closed circuits and actual paths; four reserve
  refinements. Combined food-ledger relative residual <4.1e-11. Browser covers
  four packets ×9 views, 1,008 food/480 herd CSV rows, state, water exclusions,
  narrow/light/dark layouts, conditional controls and failure fixtures. Existing
  three-atlas smoke passed. Windows/portable receipts accompany publication.
* Outputs: `output/presence_mobility_20261104`. Figures `food_support.png` and
  `resource_circuits.png` were posted. Next: poorer origin stores/collection,
  producer and clearing labour, independently declared wider seasonal gradients,
  standing-feed quality, watering, real camps and competing users. Preserve the
  negative controls: no biome-to-nomad or food-to-power rule. No agents spawned.

---

# Worldwide source/seasonal coverage audit — 4 November 2026

* Continued1faf860c. User asked how to improve de facto maps, approved a
  worldwide evidence/seasonality audit retaining original ownership baseline.
  Normal Political reach →Coverage audit is ONE extra button/six dynamic views,
  all18 actors, 3source scenarios, 1/2/4day per-leg budgets; all4 climate packets.
* Sources141 linked of151 verified marked sites;10 affiliation-unknown/conflict;
  Kudā additionally position/symbol-unverified, not routed. Explicit aliases
  data/polity_affiliation_aliases.json; workbook owner/commandery and icon
  signals retained. Lakui conflicting signals stays unknown; OCR-unmatched
  nonimperial sites not guessed by fuzzy joins. SourceCSV/JSON also shows claim.
  All data provisional game-world evidence, not independent observations.
* Source scenarios: evidence-linked; add unknown marked-site affiliations
  from painted claims; add existing generated administrative/market sites.
  Known affiliation isn't overwritten by a different claim. Roads NEVER
  emit authority here, legions not fixed sources, no strength/rank/refuge
  multiplier. Generated sites aren't observed villages/camps/institutions.
* Avādāyā/Neck have0 linked inventories: selected evidence coverage unscored,
  not zero actual control/empty land. Corrected expanded case supplies28/62
  source nodes; Neck claim-only has4. Unknown marked-site access is a separate
  evidence signal, NOT a new polity or an inferred local-autonomy footprint.
* Coherent same-site condition: A→cell AND cell→A within B. Merge AFTER each
  individual-site test; nearest out-A +nearest back-B does not qualify. Sites
  fixed/assumed available; qualifying site/actor may vary across months. No
  capacity/staffing/food/permissions/mobile-camp/sovereignty inference. Common
  central-density transport incl proposed tracks/landings in all source cases.
  Additive beat-or-wait/minparallel engine from hierarchy audit; differs from
  legacy fair-spell/refuge metric, so not an engine-controlled old/new contrast.
* Six views: paired seasonal bins, cyclic longest gap, simultaneous actor
  overlap, source-addition sensitivity, outward-without-same-site-return bins,
  unaffiliated marked-site access. Missing actor baseline makes gain unscored.
  Aggregate12bins can involve different actors: not persistent single control.
* Corrected2days/leg: all12bins ANYactor8.64%land linked →9.18%claim-added →
  47.19%generated. Outward/no-return anybin2.94%linked. Overlap anybin0.11%
  linked/7.16%generated. Land-fraction weights on majority-land travel grid.
  These are source sensitivity, NOT accuracy or observed political shares.
* polity/coverage_audit.py +scripts/review_world_coverage.py stream bounded
  forward/reverse Dijkstra per unique source, checkpoint every3months; complete
  packets reused only with source/input/binary identities. Old science modules,
  climate/food/population and de facto ownership exports remain unchanged.
* Gzip packets~1MB each, lazy browser load; uint32lookup +[3cases,18actors,
  2directions,Nland]words +[2directions,Nland]unknown words. Eachword12×2bit
  classes0>4days/1≤4/2≤2/3≤1. Do NOT bitwiseOR classes (1|2 givesfalse3);
  merge monthclass MAX or thresholded seasonal masks. Read helper
  scripts/read_coverage_grid.py usesNumPy; normal server remains stdlib.
* UI actor/source/budget+view URL state, LRU mask cache, conditional controls;
  original de facto/polity views now link to source audit. No new topic sprawl.
  Bad identity/gzip/unsupported DecompressionStream removes only audit layer.
  Source inventories/table show unscored missing actors;54row pointCSV allcases.
* 103 linked analytical tests pass. Browser4×6views,648actor/scenario/budget
  CSV checks,4096packing cases, missing baseline, lazy/reused fetch, URLs,
  controls/mobile/downloads, original-baseline links and3 failure cases pass.
  Oldall3 smoke passes. Independent grid-reader example checked. Windows/ZIP
  verified in publication receipt; launcher6views/18actors, release pinsmanifest.
  Gzip assets byte-exact in Windows checkout. Scientific figure and viewer posted.
* Methods reports/WORLD_COVERAGE_20261104.md; outputs output/world_coverage_20261104.
  Next: independently curate missing nonimperial affiliations/OCR aliases,
  documented seasonal camps/mobile support, provisioned/staffed presence and
  institutional ties. Do not infer these from biome or multiply power by food/
  taxable people; previous negative controls still apply. No climate recalibration.

---

# Worldwide pasture/feed resource maps — 4 November 2026

* Continued from e205c539 scope correction. New Livelihoods topic in all normal
  atlases (Earth raw/corrected matched): 3 buttons/6 views for annual usable DM,
  annual feed equivalents, lean-bin new growth, minimum zero-loss feed reserve,
  90-demand-day buffer shortfalls and mapped water distance. ALL245031 land
  cells included; polity claims only label illustrative geographic examples.
  This is a feed-resource diagnostic, NOT a complete pastoral population model.
* Primary sources researched: FAO2012 feed assessments; FAO Kenya Annex5§7.4
  reference250kg TLU/6.25kgDMday; Mottet/Assouma2024 FBS DOI10.3389/fanim.2024.
  1354728 (DM alone doesn't establish energy/protein adequacy); Illius/O'Connor
  2000 heterogeneity abstract (publisher403, no equations/coefficients copied).
  research_notes/pasture_20261104.json; config data/pasture_model.json.
* harvest/pasture.py excludes assigned crop area from forage (arable×.6),
  reuses published Miami NPP and existing Harvest forage shares .5aboveground,
  .25usable, biome-dependent edible fraction. Annual coefficients remain
  assumptions, not newly validated sustainable grazing. No crop-residue credit.
* Uncalibrated seasonal weights clip(T/15,0,1)×P/(P+50), normalized to annualDM.
  Positive annual supply with no active weight stays unknown, not uniform.
  Current4packets happen to resolve all cells. Synthetic unknown case tested.
* Constant test demand=.5annual usableDM. Cyclic minimum zero-loss capacity;
  90-demand-day buffer uses minimal repeating inventory, explicit overflow
  and consumption once, via existing food_stocks.py. Maxledgerresid<5e-11kg/km².
  Standing forage/hay undifferentiated; no preservationlabour/quality, protein,
  energy, herd dynamics, migration, water volume, animal products or new people.
  365day reference accounting year/12equalbins, not the world's civil calendar.
* Median minimum reserve days Free33.5/Earthraw37.2/Earthcorrected35.6/Whittaker47.
  Land share >90days12.8/14.6/15.3/19.3%. Corrected Earth~25%annualDM outside
  named claims. These are conditional resource figures, not herd counts/famine.
  Waterdistance is mean land proximity to mapped rivers/lakes: no permanence,
  salinity, wells, measured drinking capacity or species-specific gate assumed.
* Four fixed-anchor examples from published Earthraw eligibility: Tarani
  agricultural resources, nonimperial grassland outside named claims, mixed
  resources outside named claims, Tribes of the Neck. Map labels do not assign
  livelihoods or institutions. No selection on new reserve outcomes/validation.
* scripts/build_pasture_maps.py pins inputs/sources, renders maps+publicNPZ and
  compact binary; sources frozen climate/Harvest unchanged. atlas/pasture.js
  checks loaded Harvest and binary identities, exposes CSV and NPZ downloads.
  AnnualDM float32 to preserve tiny positives; ratios1/60000,reserve.01days,
  water.1km and integer shortfall bins, explicit nodata. Coastal resource
  readout retains original click before station-card snapping; other cards
  retain their old selection behaviour. Conditional occupation controls hidden.
* 97 analytical/component tests pass. Pasture browser4×6 views/16pilotCSV-NPZ
  checks, outside-claim/tribal/nonimperial coverage, state/download/mobile,
  corruptedidentity/binary isolation pass. Existing hierarchy browser4×6 and
  all3 atlas smoke pass. Windows checkout/portable hashes in publication receipt.
  Launcher prints Livelihoods6views; release pins manifests. Normal .bat viewer
  updated. Figures world_resources.png and seasonal_profiles.png posted.
* Methods reports/PASTURE_RESOURCES_20261104.md; output/pasture_maps_20261104.
  Next: energy/protein/standing-forage quality and water dynamics; then conserved
  herd/mobility and shared household food/land/labour scenarios. Do not add these
  feed equivalents to old farming/pastoral/FORGE population totals. No cropfood/
  human-consumption integration or physics recalibration adopted this milestone.
  Integration caution: legacy scripts/land_people.py NEED_KCAL=1.1e6 already
  includes a storage/draft-animal allowance. Replace that proxy explicitly
  before charging those same requirements again in a joint household/feed LP.

---

# Scope correction: all societies, not only the Empire — 4 November 2026

* User explicitly wants other polities (sparse spreadsheets) and communities
  outside polities, including mobile pastoral/other tribal societies. Do not
  focus subsequent provisioning/population work solely on imperial administration.
* Separate livelihood, mobility, settlement form and political organization;
  no automatic nomad=nonstate or tribe=pastoral equivalence. Sparse evidence
  stays unknown/scenario-based, not an invented imperial hierarchy.
* General food/feed/water/storage/exchange model must work outside claims.
  Existing claimed-only proposed administrative-town generator is not a global
  inhabitability or village/camp model. Do not simply remove its claim mask
  and extrapolate administrative-seat counts. Unclaimed does not mean empty.
* Farming/pastoral/FORGE capacities currently compare scenarios; do not sum
  them into extra populations without shared land/resource accounting. Annual
  grazing proxy is not a seasonal herd/mobility model. Institution collection
  and garrison support become optional overlays on wider local livelihoods.
* Next pilot should include nonimperial agricultural, mobile pastoral/mixed,
  and settled nonstate cases. See reports/WORLDWIDE_PROVISIONING_SCOPE_20261104.md.
  This is a recorded scope update, not newly implemented model/maps.

---

# Recorded administrative hierarchy maps — 4 November 2026

* Continued from 71b52b47. New Administration → Administrative links: one
  button/six views on all normal fits, including matching Earth raw/corrected.
  Recorded 72 seats →19 provincial capitals →Aēnaha. 70 verified seats,
  51 nontrivial local links; Kudā and Thalamâtâs/Pitané remain unresolved.
  No nearest-parent inference or game balance coefficients adopted.
* Two controlled person-transport cases: marked-settlement coastal/river
  interchange eligibility with no generated tracks; add proposed tracks and
  proposed-town interchanges, explicitly retaining marked interchanges.
  Both retain current central-density path friction. Interchanges inferred,
  not proven harbours. Recorded authority sources/hierarchy held fixed.
* Isolated polity/administrative_hierarchy.py selects MINIMUM directed
  duration among parallel alternatives (legacy CSR sums them). Additive
  beat-or-wait sea edges, NO legacy whole-voyage fair-spell blend. This is
  a separate travel calculation; do not compare its absolute times as if
  it differed from old access only by infrastructure. No legacy source
  modules or frozen climate/food/political exports changed.
* Four legs retained per seat/bin/case: capital→province, province→seat,
  seat→province, province→capital. Provincial reply=sum middle2; imperial
  reply=sum4 under SAME frozen monthly conditions. No courier relays,
  institutional delay, changing weather during voyage, capacity/provisioning
  or political-border permissions. Twelve model snapshots, not civil months.
* Median worst-snapshot imperial reply over69 noncapital seats, marked→
  proposed days: Free60.5→59.6;Earth raw62.7→61.0;Earth corrected62.7→61.6;
  Whittaker61.8→60.0. All69 finite allbins both cases, not validated service.
  Physical-transport benefit is modest versus old access's large gain from
  adding proposed authority sources. Do not conflate those two mechanisms.
* Six views: longest provincial reply ×2cases; longest imperial reply ×2;
  marked seasonal range; worst imperial reply days saved by proposed transport.
  Schematic connectors NOT paths or control polygons. Coloured dots only
  describe seats; outer rings provincial capitals. Map views have fixed-day
  scales. Select recorded seat +7/14/30/60day comparative reply budget for
  within-budget bins and longest cyclic over-budget gap. No budget validated
  as a political cutoff. Capital self-links explicitly zero, unknown seats
  unscored, full directional seasonal CSV/NPZ and selected24rowCSV downloads.
* Optional atlas/administrative-hierarchy.js verifies inventory, food binary
  and travel JSON identities. Failure removes only new layer. Fixed old
  Administration failure handling to retain topic if hierarchy remains valid.
  Commandery/budget/view/climate URL state, normal climate-selection sync,
  irrelevant core/frontier/malaria/month/tiers controls hidden on new maps.
* Runner scripts/review_administrative_hierarchy.py hashes all inputs/source,
  resumes only identical complete packets; 4-thread directional shortest paths.
  Small links.npz perpacket retained in output/administrative_hierarchy_20261104.
  Publisher, comparison-plot and browser scripts named administrative_hierarchy.
  Methods reports/ADMINISTRATIVE_HIERARCHY_20261104.md cites Smith/Glatz/Evans-
  Rivers/ORBIS as motivation, not validation of lore hierarchy or thresholds.
* 91 linked analytical tests pass. New browser checks4packets×6views, directed
  CSV versus NPZ, budget counts, capital self-links, unresolved searches,
  state/downloads/mobile/control hiding and bad identity/data failure isolation.
  Previous access browser4×12 and oldall3 atlas smoke pass. Windows checkout,
  portable bundle and byte identities verified in publication receipt. Launcher
  prints19 capitals/6 new views; release pins hierarchy manifests. Comparison
  figure posted. Physics unchanged; no new climate-calibration claim.
* Next: conserved provisioning/staffing before control inference; settlements
  share population and food budgets. For communication itself, evidence-backed
  courier relay/institutional delays and time-varying long voyages are missing.

---

# Workbook-backed administration and seasonal access — 4 November 2026

* User supplied Imperial Commanderies.xlsx and Ravages Master sheet (1).xlsx,
  explicitly game-era evidence rather than authoritative physical parameters.
  Originals remain local under /workspace/attachments; do not commit them.
  scripts/import_imperial_datasheets.py extracts only geography/admin columns
  to data/imperial_datasheet_evidence.json, with workbook hashes and sheet rows.
  Excludes game supply/population caps, loyalty, wealth, factions, notes/players.
* Owner list/key data/imperial_administration.json: all 72 names agree with
  reference workbook. Stable IDs resolve split districts and differently named
  temple seats. Preserve Tašar/Garaz town-sheet name conflict (IC4C5), Uγra/Uyra
  spelling evidence. 70 verified marker seats. Kudā has no matching symbol,
  Thalamâtâs conflicts with Pitané seat flag: both excluded as seat sources,
  candidate evidence retained. Named inventory 152 vs 151 drawn symbols; Kudā
  is an unmarked Elder Village, not a merged capital icon. 14 legion positions;
  founding numbers untranscribed, never strength. 25 imperial fort markers.
* New optional Administration topic in normal Free/Earth/Whittaker pages,
  Earth raw+corrected matched: 4 packets, 3 buttons/12 views each. Six cases:
  verified seats; add marked places; add proposed towns; add generated tracks;
  add road cells as sources; separate forts+legion scenario. Same ports/river
  landings incl proposed-town ports throughout, so NOT observed-only transport.
  Threshold 2 person-days, 12 equal climatological frozen-condition bins. Count,
  cyclic longest isolation, annual log-mean versus continuous access, paired
  gains, plus placement seeds 1/2/3 recurrence within10km (not probability).
* Earth corrected all-12-bin claim-area shares: seats14.8%, marked15.7%,
  towns63.0%, tracks65.9%, roads70.7%, military7.0%. Main gain is adding proposed
  sources, not tracks. Sparse seat inventory doesn't prove weak actual control.
  Old de facto, climate/food/population binaries and legacy polity code unchanged.
* Sources/scripts: polity/administration.py, administrative_world.py,
  seasonal_access.py; scripts/audit_administrative_inventory.py,
  review_imperial_access.py, publish_imperial_access.py, plot_imperial_access.py.
  Full review/source hashes in output/administrative_inventory_20261104 and
  output/imperial_access_20261104. Shared atlas/administration.js verifies food
  binary/inventory/grid identities; mismatch removes topic, keeps climate usable.
  Centre CSV, typed inventory, NPZ and selected-place CSV available in viewer.
* 87 linked component tests pass. New browser verifies 4 packets x12 views,
  CSV/NPZ consistency, all4096 masks, controls/state/downloads/mobile and bad
  identity; prior cereal browser and all3 old smoke checks pass. Windows-style
  checkout and portable bundle verified for publication (see receipt).
  Launcher prints Administration/70-of72; release pins sidecar hashes. Methods:
  reports/IMPERIAL_ACCESS_20261104.md; comparison PNG posted during work.
* Next: use workbook province/commandery hierarchy for explicit capital-to-seat
  continuity; threshold/source uncertainty; conserved food/staffing provisioning
  before control claims. Recorded hex memberships are game evidence, not adopted
  physical terrain or independently validated boundaries. No physics recalibration
  this milestone. Keep literature proposals/negative controls in view.

---

# Food and work maps in normal atlases — 3 November 2026

* User asked to work toward new maps. Delivered Food and work topic in normal
  Free/Earth/Whittaker viewers, including Earth raw +corrected:4matchedpackets.
  Cereal field work button has5views(hours, croppedland, reapingstaff10/20/30days);
  Calendar alternatives button showsdistincttiedoptimalharvestboundarybins.
* harvest/work_maps.py uses exactdecodedpublished kcal_wheat/barley, target1M
  netkcal, Columella336/208listedhours/ha and48/32reapingh/ha under explicit8hday,
  approx.25ha/iugerum. Least-work singlecereal, not totalwork/population or a
  full seasonal household plan. All4packets choosebarley withcurrentinputs;
  don't pretend cropchoicemap hasdiversity. Landmap is forwork-efficientcrop,
  NOT independentlyminland; reapingstaff usesprescribedwindow, notrealdeadline.
* Regenerated allcerealwindows onall245031landcells perpacket. Maxdifference
  fromexportedcropenergy~20.9kcal/ha (packingprecision +float32rounding). Retains
  allbestboundaryties(currentmonthlymodel), notnewdailyclock/observedcalendar.
  Ambiguouscells free187932/Earthraw187398/Earthcorrected194256/Whittaker164414.
  Manyties aremodelambiguity, notestimatedagriculturalflexibility/probabilities.
* Builtsidecars data/farm_work.json, sixwebps perpacket, uint16calendarbin and
  NPZvalues. Existingfrozen atlas.json/climate/harvest inputs unchanged andchecked.
  Sourcehashprovenance frozen inmanifest. atlas/farm-work.js verifiesmatching
  Harvestfingerprint/metadata/calendar/loadedbinaryhashes beforeexposingreadouts.
  Mismatchremovesnewtopic/layers, keepsnormalclimateworking, visiblesourcemessage.
  SharedHarvestUI exposesread-onlyfieldgetter/buffer forverifiedreuse,nodoublefetch.
* UI:2buttons, oneviewselectoronlywhereused; nooccupation/malariacontrols inwork
  maps. PlaceCSV/nullmissing values, fullNPZ+methoddownloads, shareablehashstate,
  corrected/rawmatching, dark/light/mobile.73focusedcomponenttests pass; existing
  atlasbrowser smoke passesall3. Newbrowserchecks4packets×6views and numerical
  CSVagainstNPZ, controlhiding/restoration, badidentity fail-closed.
* Source/report CEREAL_WORK_MAPS_20261103; outputs output/cereal_work_maps_20261103.
  Figure work_maps.png posted. refresh_atlas_pages copiesnewoptionalJS andonly
  enablesifmanifestexists; legacyearth_physics disabled. Launcherprintsnewtopic
  andcounts67/72/69layers. Hubreleasealsoverifiesnewmanifesthashes.
* Next: fulltask evidence, climate/workabilitydeadlines, crop-specificcultivars,
  finitewater andjointseasonalfood/stores/work. Existingyield/rainwaterirrigation
  proxy andcold/drymargins remainlimitations. Newmaps havenoindependenthistorical
  validation, state/inequality inference, weatherprobabilities orclimateadoption.

---

# Minimum listed field work for required output — 3 November 2026

* Continued after labour milestone d70c3e00 (pushedbothbranches). Added
  minimum_farm_work to the same shared LP; target>=need, minimizechosenwork
  resource, keepallotherresource/season/landlimits. InfeasibleFarmPlan is an
  explicit error, never hidden foodshortfall or zero requiredwork. Maximum-
  output and minimum-work marginals separated.30focused analyticaltests pass.
* demo_required_farm_work.py uses EXPLICIT hypothetical netfood/ha100wheat,
  80barley, annualneed300arbitraryunits. Historical Columella listedfieldtasks
  only. Fourha:barley3.75ha/780h;3.5ha:wheat1+barley2.5/856h;3ha:wheat3/1008h.
  These are analytical controls, NOT historicalyield or subsistence estimates.
  Insufficientland2.9ha ceiling290;10dayreap ceiling200 => bothinfeasible,
  workloadnull NOTzero. No calorie/population conversion, seasonalconsumption
  and foodstocks notyetjointlyoptimized, omittedhousehold/animalcare unchanged.
* Allpriorseven field-area controls remain unchanged aftersharedsolverextension.
  Sourcehashreceipts refreshed by rerunning, not manually patched. Published
  workshop verifies bothstudies, fullschedules and missingvaluehandling.
* Next: missingtask evidence and jointseasonalfood/stores/work formulation,
  actualcrop/cultivar/workability validation. These LPs solve their supplied
  linear scenarios, not the nonconvexclimatecalibration or globaloptimum question.

---

# Seasonal field-operation scheduling — 3 November 2026

* Continued after world-route8560dc0e and paired-audit5f6e55ff (both pushed).
  New harvest/labour.py plans complete annual activity hectares and every
  required operation within supplied windows. Shared seasonal human/team
  resources, land budget, divisible LP activities, no implicit winter-to-harvest
  labour transfer. Separate simultaneous resources supported; no task precedence
  beyond supplied windows, weather workability, endogenous hiring or integers.
* Historical task counts independently transcribed Columella2.12.1–2: wheat
  4+1+2+1+1+1.5=10.5days/iugerum;barley3+1+1.5+1=6.5. These stop at threshing
  floor, not full food/subsistence work. Approx .25ha/iugerum and8h/day are
  explicit scenario conversions. FAO whole-farm LP is method foundation;
  Bogaard2025 motivates constraints, not coefficients/inequality prediction.
* Manufactured73×5day schedules: same2920annual farm-allocationhours,
  wheat narrow10dayreap =>1.6667ha vs4ha if ignoreseasons or widenreaping30days.
  Sameannualbudget withadditionalharveststaffing also4ha; within3workers×8h/day
  upperenvelope, NOT banked wintertime. Moreland/fasterprep remain1.6667ha.
  Barleynarrow2.5ha comparesworkablearea NOTfood/nutrition. Everytask/budget
  checked;18focusedtests and61linkedcomponenttests pass. No ancientfarm-size,
  foodadequacy, leisure/surpluslabour or population predicted.
* research_notes/farm_labour_20261103.json stores sourcecounts/cachehashes and
  allassumptions. outputs output/farm_labour_20261103; report FARM_LABOUR_20261103.
  New economy_labour_section.py verifies source/input/figure/ledger identities.
  Existing atlas farming/population/climate remain unchanged; published workshop
  only. No climatebenchmark F used or new climatefit adopted.
* Next integration: missing threshing/processing/storage tasks, complete household
  and animalfeed/care budgets, crop-calendar/workability windows, parameter ranges
  from evidence; then minimum work for a supplied food need, not a biome-driven
  civilization score. Current numerical marginals are not historical regime labels.

---

# Same-path seasonal freight connector — 3 November 2026

* Continued after publication3b65b92b. New connector57ef94cb retains physical
  time, freight cost and mode along identical directed legs. Actual raw-r43
  geography recomputed from current atlas (not old Oct25 economic NPZ).
* Fixed endpoints/drawing fractions committed before routing; 12months ×2
  directions retained. A→B26.3–78.1days, B→A28.1–77.6days. These are monthly
  snapshots holding conditions fixed throughout transit, edgewise sailing
  expectation (not whole-voyage weather-spell model). One least-cost path,
  not a fastest journey or cost/time Pareto set.
* Food integration assigns SAME manufactured harvest/budget to either endpoint
  in turn. Both directions meet365farm+146town need under assumed storage365/30
  and departurecap4units/5days. Food ledgersclose2.85e-14; NOT inferred ancient
  population/production/cargo. Finite ships/empty returns are not modeled.
* Audit finds155directed endpointpairs with parallel alternatives permonth;
  legacy CSR sumsduplicates. Isolated connector choosesleastcost thenfastesttie
  and keeps that leg's time/mode. Maximum local summed/selected ratios4.48–20.10
  across months are NOT path-level or map errors. Legacy graphs unchanged.
* publish_freight_corridors.py verifies source/inputhashes and same-path totals,
  renders stored paths with readable white-cased sea lines and correct transfer
  legend. economy_freight_section.py publishes all24paths and assumptions.
  Report FREIGHT_CORRIDORS_20261103.26 focused freight/food/directed tests pass.
* Paired audit then completed with prospective plan8560dc0e: ten fixedsources,
  fourtrade months, identicaltopology/reachability, only155parallelpairweights
  differ eachmonth. No costincrease; all360sampled directedtownpairs unchanged.
  BroadMAmax+.0107%, localMAmax+.0735%; maxindividualroutecostdrop7.807roadkm,
  up to2.654%reachableclaimedpeople have >1roadkm saving for a source/month.
  Small sampled aggregateeffect, not a large trade-map discrepancy explanation.
  Data output/parallel_freight_20261103/review.json. Legacy maps unchanged.
* Next: historical seasonal labour and fixed operation windows; retain
  faster/costlier paths before shortage inference; finite fleet/return-voyage
  scenarios and actual-world crop/storage/labour validation remain separate.

---

# Linked cereal, soil-water, food-stock and provisioning prototypes — 3 November 2026

* Owner approved the four-step implementation (published cereal development,
  continuous crop-sequence soil water, storage, directed town provisioning)
  and asked to continue during work. Components now implemented and linked in
  a manufactured end-to-end scenario, with explicit assumptions. Normal r43
  climate and production farming/population layers remain adopted unchanged.
  No claim of independently validated ancient town sizes or crop yields.
* Daily development harvest/phenology.py independently implements LPJmL4
  Schaphoff2018 eq73–79 and S10/S11 parameters; reference photoperiod disabled
  as paper, explicit cultivar thresholds required to enable it. Source v4
  checked for PVD<=10 and PHU lower-bound conventions, no upstream C imported.
  Country-separated protocol calibration/cereal_phenology_20261103/plan.json
  committed before fitting, selected global parameters frozen f805ea3c before
  evaluation. 237training records/62countries;29evaluation/16countries;19QC
  exclusions. The underlying Sacks dataset was previously inspected, NOT unseen.
* Cereal eval complete/pushed79194116. Equal-country penalized duration error:
  existing heat-only ablation train58.96/eval51.99days; published heat adaptation
  with NO chilling36.96/28.56 (no nonmature eval); fixed45day winter chilling
  97.28/74.05; training-selected global scale.8/PVD15 gives90.86/68.06 with2
  nonmature eval cases (365day penalty retained). Generic chilling fails this
  test; don't adopt that failed candidate or call old ablation atlas date skill.
  Prescribed observed sowing, WorldClim centroid climate, no frost/biomass/yield
  model. Eval pool now scored; don't retune and call it untouched.
* harvest/soil_water.py: FAO56 eq81–88 daily fixed-root-zone conservation,
  no refills between crops, explicit finite field irrigation, periodic state.
  Reproduces published Example37 within.05mm rounding. Field budget != routed
  river supply. No snow/frozen soil, dynamic roots, ponded rice or groundwater.
* harvest/upland_food.py links supplied feasible upland seasons to the shared
  water ledger and individual seasonal Ky responses; no half-weight second
  crop or repeated seed deduction. Explicit analysis guard refuses severe
  deficit extrapolation; no positive food from zero ET demand. The integrated
  demo derives maturity using the new heat-only clock under manufactured
  temperature and prescribed sowing; actual world calendars remain unvalidated.
* polity/food_transport.py is a time-expanded cyclic capacitated food LP:
  directed routes, delay, net retention, seasonal capacity, stocks/spoilage,
  aggregate consumption priorities, then freight/holding-cost minimization.
  Food quantities != gravity weights, costs don't consume calories; no food
  from hidden initial/transit stocks. Ford/Fulkerson1958 is the flow foundation;
  storage/priorities/losses are declared adaptations, not a price equilibrium.
* Complete scenario backend pushed fefecd4b, then zero-ET guard added. Six
  manufactured development->water->harvest->stores->town cases: town need met5.5/54.2/
  69.2/69.2/100/84.9%. Last pair isolates seasonal closure with ample farm
  storage. Initial cases expose a stronger storage bottleneck. No estimates of
  actual granary capacities, famine frequencies or towns. Separate food/water
  ledgers close to floating-point tolerance.97 focused tests pass.
* Evidence reports CEREAL_DEVELOPMENT_20261103 /SEASONAL_FOOD_SYSTEM_20261103;
  outputs output/cereal_phenology_20261103 and output/seasonal_food_system_20261103.
  Economy lab now leads with both studies, methods, full-data downloads, and
  folds previous experiments. Current producer helper
  scripts/economy_component_sections.py verifies all source/result/image hashes.
  Desktop/mobile/dark/light,11downloads, nested-details keyboard checks pass.
  A workspace restart occurred after these checks; restart a local no-store
  server on port8766 for final browser QA. No science jobs remain running.
* Next world integration requires cost AND time for the SAME selected route,
  cargo capacities, rural budgets and town-demand scenarios. Existing graph
  costs are road-km equivalents: NEVER turn them into travel days or treat
  gravity weights as grain. Historical storage/labour, actual cultivar chilling
  and crop-specific soil-water/yield validation remain before production maps.
  River irrigation needs basin/allocation accounting; current finite field
  supply prototype does not create it. All Earth-climate F remains unused.

---

# Observed calendar diagnostic identifies winter-phenology gap — 3 November 2026

* All source-backed joint-calendar and reserve prototypes were published and
  pushed41b76ca9 after345793f2. Continued after pushing with an actual modern
  observed-calendar diagnostic, as owner specifically requested academic basis.
* Committed prospective diagnostic e6224742 BEFORE group-score inspection:
  calibration/crop_calendar_observations_20261103/plan.json. Authors' Sacks2010
  CSV cached locally (1.2MB), raw SHA fixed. Parser keeps all qualifiers; source
  Exclude groups explicitly flagged and separate (notes explain crop weighting
  or ambiguous sequential/spatial cropping). 1510raw ->481 mapped/basic-valid,
  9source-flagged,472unflagged;1025unmapped +4invalid dates. Generic millet not
  treated as foxtail. Source cold summaries missing != zero. No tuning/adoption.
* Unflagged winter wheat138 records:55 outside current duration envelope,
  22 still outside with full-bin30.4day tolerance;54/137 climate summaries have
  below-zero exposure. Winter barley49:13/2 outside,13/48 exposure. Unqualified
  rice145:36/2 outside,0/143 exposure. Every group and record retained publicly.
  This is a necessary-duration/descriptive exposure check, NOT exact predicted
  dates, full agronomic validation, ancient cultivars, independent CI, or an
  exact monthly-model rejection rate. No Earth climate F data touched.
  This Sacks dataset has now been inspected diagnostically; do not later call
  aggregate reuse an unseen test. Freeze geography-separated training/evaluation
  before phenology fitting, disclose prior inspection, and check dependencies
  before treating MIRCA (shared calendar inputs) as independent evidence.
* Next meaningful process: published spring/winter phenology, including dormancy,
  vernalization and photoperiod (Schaphoff2018 LPJmL4 DOI10.5194/gmd-11-1343-2018).
  Not implemented yet; don't claim the new selector solves these processes or
  just widen bounds until all observations fit. Couple sequence soil-water and
  assess period cultivars/labour/yields before adopting population or food maps.
* New files scripts/check_observed_crop_durations.py (optional --download with
  exact source hash), reports/OBSERVED_CROP_CALENDARS_20261103.md,
  output/observed_crop_durations_20261103.62 focused tests pass. Economy lab
  now leads with observed evidence and full-data/declared-plan downloads;
  desktop/mobile/light/dark and all9downloads pass. Figure/source checksums
  guarded in builder. Research manifest updated; sequence/storage numerical
  comparisons rerun unchanged to keep their provenance current.

---

# Joint crop calendars and reserve uncertainty — 3 November 2026

* USER STEERING: keep new mechanics grounded in real academic literature.
  Explicit source/assumption register research_notes/crop_sequences_20261103.json:
  Waha2013/2020 (sequences and sowing), FAO33 response/FAO56 (water), Sacks2010
  observed calendars as a future independent check, not yet scored. The code
  is a simplified prototype, not LPJmL/GAEZ reproduction or ancient validation.
* Joint window selector committed/pushed345793f2; retains all216 annual crop
  windows and optimizes up to2 compatible crops; both-turnaround and year-wrap
  constraints. Existing secondary weight.5, water gate and different-crop rule
  held fixed ONLY to isolate selection. All per-crop maxima exactly reproduce
  production. Same fixed4,096 raw-r43 fantasy samples:113 improved,263 example
  pairs,3150 with tied optima. One-bin turnaround110/261/3094. All12 jointly
  rolled climate/soil origins exactly match energy/count/boundary union on256
  fixed cells. Production yields/population/physics remain unchanged.
* New calendar_stock_bounds computes min/max no-loss reserve requirements
  across ALL tied annual optima, retaining unknown perennial timing. Conditional
  harvest pulses, uniform need equal to annual harvest, zero loss; no ancient
  storage/loss/population coefficient fitted.162 samples show calendar-dependent
  reserves, max range30.815days; five-day vs daily bounds differ≤4days. Five
  perennial-only cases have blank CSV bounds (not zeros). Formula checked against
  independent cyclic-deficit and repeating inventories in120 cases/3 clocks.
  58 focused tests pass. Sources harvest/{crop_sequences,calendar_stocks,
  calendar_sample}.py; reports CROP_SEQUENCES_20261103 /CALENDAR_STORAGE_20261103.
  Outputs under output/crop_sequences_20261103 and output/calendar_storage_20261103.
* Normal .bat hub's economy lab now presents both comparisons, academic source
  register, CSV and explicit limits. Older manufactured/tie checks folded into
  keyboard-operable details. Desktop/mobile/light/dark/downloads pass, no
  overflow. Public models still require observed-calendar evaluation, coupled
  crop-specific sequential soil water, historical labour/cultivar evidence and
  revalidation of capacity/fallow before adoption. No new physics trials active;
  r43 remains adopted and F remains unused.

---

# Calendar evidence and final drying qualification — 3 November 2026

* Stronger dry-branch qualification is COMPLETE/REJECTED, a55cb748, pushed to
  both branches. S61=1.0023168712, temperature +.05438%, rain loss +.40899%;
  historical49 S=1.0054999951, rain +.94186%. No fine or reserved F case ran;
  F remains unopened. All six declared physics/publication jobs now finished.
  Normal r43 physics remains adopted. Public latest section and full paired
  evidence: atlases/climate_accuracy/data/dry_branch_validation.json.
* Actual crop-calendar ambiguity now quantified by a passive production-model
  audit on4,096 systematic raw-r43 fantasy land samples. Original kcal mix
  reproduced, individual crop yield drift0. Calendar origin changes mix in226
  samples; alternative individually-optimal masks permit a better pair in58.
  Largest local gain47.12%, unweighted sample energy sum+.151%; NOT whole-map
  area/population forecasts. No production crop/yield/population layer changed.
  harvest/calendar_audit.py, scripts/audit_crop_calendars.py,
  reports/CROP_CALENDARS_20261103.md, output/crop_calendar_audit_20261103.
  Five analytic/control tests plus Harvest/food stocks:31 tests pass.
* Economy lab now includes this observed model diagnostic beside its explicitly
  manufactured inventory experiment. Desktop/mobile dark/light browser passes.
  Final publication QA: Windows1,061 byte-exact assets; portable1,625 files,
  644links; climate companion73 studies/169 images with working keyboard and
  deep links. Final receipts in output/crop_calendar_audit_20261103 and
  output/dry_branch_validation_review_20261103. ZIP stays local under the
  food_stock_prototype output folder; all bundle sources indexed and hashed.
  Next: retain all feasible crop windows, jointly select compatible sequences
  (turnaround, same-crop policy, perennial timing explicit), validate calendar
  behavior, then connect to stocks. No precise harvest dates from tie-breaking.
  Town grain balance, household labour, finite irrigation, seasonal herds and
  state provisioning remain researched proposals, not quietly adopted models.

---

# Economy lab publication and one frozen climate qualification — 3 November 2026

* Complete r43 is live. Normal .bat hub now links Food, farming and society
  (atlases/economy_lab/): six researched proposals plus the isolated food-stock
  example. Actual production climate/economic layers remain unchanged by this
  lab. Desktop/mobile, both themes, downloads and no-overflow pass; portable
  1,621 files /639 links and Windows 1,058 byte-exact assets pass. Source
  outputs/receipts: output/food_stock_prototype_20261103 (ZIP stays local).
* Existing dry-branch rate .4/day is prospectively frozen in
  calibration/dry_branch_validation_20261103/plan.json (2cf3763a). Only one
  parameter differs. Fresh baseline numerical reproduction PASSED; candidate
  full61 running at 14:19 UTC. Session66825 / PID4148, supervisor20952;
  output/dry_branch_validation_20261103.log. Scientific source c20f99bd private
  model; do not edit its frozen orchestrator/shared source dependencies.
  Pipeline: full61 gate -> paired fine28 -> reserved F ONCE if qualified.
  No auto-adoption. F remains unopened as of this note. Supervisor --status
  checks real process identity; environment shutdown stops work.
* Public fixed-face section now includes the completed NEGATIVE fitted-flux
  screen, browser checked. No fitted transport physics was adopted.

---

# Human-model prototype and final physics-screen outcomes — 3 November 2026

* Economic proposals have been PRESENTED to the owner after complete r43
  publication. First bounded implementation now harvest/food_stocks.py:
  net-edible energy inventory, explicit capacity/spoilage/overflow/unmet food,
  finite-year and smallest-periodic-reserve modes, exact zero-loss minimum
  capacity. No atlas economic model, crop yield, population or FORGE changed.
  38 focused Harvest/FORGE/inventory checks pass; stale settlement_cored test
  fixture repaired. Manufactured demo: identical annual365 harvest/demand,
  capacity200 gives164 shortage days for one harvest vs0 for two; no actual
  world prediction. Report reports/FOOD_STOCKS_20261103.md; full demo receipt
  output/food_stock_prototype_20261103. Calendar ties/perennials/double crops
  need validation before integration; don't manufacture exact harvest dates.
* All five earlier pipeline jobs COMPLETE and pushed. Fitted-vs-upwind screen
  b1691d33: fitted S8=2.18614 vs production, upwind-flux2.11131; fitted rain
  loss4.76% worse than upwind flux, no adoption/F. Default numerical control
  passes. Do not call reduced numerical smearing a climate improvement.
* Bound probes0c142313: lower marine thresholds do not help. Stronger existing
  dry-branch rate0.4/day gives S8=.97461255, T−.7879%, P−4.2896%; combination
  S8=.97546346. Reused8-region evidence ONLY; not selected/adopted by that
  screen. Any broader qualification must prospectively freeze one candidate,
  reproduce full61 control, report historical49 separately, then fine/F gates.
  F remains unopened. Keep the owner's human-model priority; no new physical
  family such as geometric conductance has been implemented/launched.

---

# Verified release complete — 3 November 2026, 14:30 Warsaw

* R43 atlas publication COMPLETE and pushed to BOTH branches in1ac032ab.
  The normal .bat-served Earth atlas is now actuallyr43 (70 raw /55 corrected
  layers, all5 languages). Corrected strict target agreement37.4727%, raw34.4712%.
  Matching corrections and ALL climate/food/people/foraging/political/trade/language
  exports complete. Raw9-layout and3-extra-year diagnostics pass; cycles repeat.
  Browser checks all3 atlases, Windows1,053 byte-exact assets, portable1,613
  files/627links pass. Launcher and page display actual r43 metadata. Source
  snapshot remains8cfdf7b4 with validated scientific model03c4351f.
* Full61 storm study COMPLETE/REJECTED, results9d3d6ab1, public evidencefe7ffc46.
  S61 1.026560 /1.016619. F remains unopened. Do not advertise the initial8-region
  gain as broad improvement or select a failed family.
* User's requested next phase: return to c.200AD state/farming/trade/anthropology
  and present proposals. Concrete researched note now reports/ECONOMY_PROPOSALS_20261103.md,
  with existing-feature/source audit research_notes/economy_proposals_20261103.json.
  Recommend agricultural seasonal stocks + real grain provisioning, then labour;
  finite irrigation needs audited catchments (current flow index is not m3/s).
  Optional forager storage already exists and was rejected, so don't sell it as
  new validated progress. Forager cycles need numerical checks before risk maps.
* Fitted transport screen is now ACTIVE (source-pinnedc20 model), profile reference,
  session40089. Bounds session47219 waits for that complete screen. Both reuse8
  development regions, no F/adoption. Supervisor4645 monitors live processes;
  status command .venv/bin/python -I scripts/continue_climate_work.py --status.
  No new physics families have been launched; geometric conductance is backlog
  only. Continue the user's human-model direction while the declared screens run.

---

# Owner's next priority and latest result — 3 November 2026

* USER STEERING: after the next full physics update, return to the c.200 AD
  state/farming/trade/anthropology model and PRESENT proposals for mechanics
  or maps. Finish the current verified r43 atlas release and full61 report,
  then present concrete researched choices. Draft prepared in
  output/econ_proposals_20261103/proposals.md: seasonal food/storage, actual
  grain provisioning, finite irrigation water, household labour, pastoral
  transhumance and delivered fiscal surplus. Existing forager storage was
  tested/rejected; avoid proposing it as a new proven gain. Modern papers
  support mechanisms, not universal200AD coefficients or climate determinism.
* Storm61 COMPLETE, auto-committed/pushed9d3d6ab1. Both profiles rejected:
  storm-r42 S61=1.02655993 (rain+5.2287%), storm-r43=1.01661899 (rain+2.8546%).
  No finalist, fine test or F run. F remains unopened. Source-pinned study
  fully finished; no score from partial cases. Broad research producer
  scripts/publish_storm_expansion.py verifies full raw packets and handles
  failed profiles as unscored. Its public page/browser QA is ready.
* R43 raw exports, nine-layout sensitivity and3-extra-year settling checks
  COMPLETE; annual cycles repeat. Matching corrected layers COMPLETE.
  Corrected full export is now freight season3/4 (13:24UTC). Then languages,
  identity, promotion/browser/Windows/portable/push. Keep checking supervisor
  status; final publisher waits for committed research at the package boundary.
* Fitted transport and calibration-bound probes remain prospectively queued
  after atlas publication, then sequentially. They can continue in background
  while economic proposals are discussed; don't open further physics families
  before honouring the user's priority. A geometric storm-conductance idea is
  documented ONLY as backlog in reports/NEXT_PHYSICS_20261103.md, unimplemented.

---

# Resumed after environment restart — 3 November 2026, 13:49 Warsaw

* One-command recovery/status now available:
  `.venv/bin/python -I scripts/continue_climate_work.py --status` reads actual
  processes, never stale marker text. Run without --status to attach/resume
  all five committed jobs and monitor them in the foreground. Supervisor
  session4645 currently attaches to all five live drivers, without duplicates.
  It cannot keep a shutdown workspace alive; rerun after environment restart.
  Two process-identity/argument-matching tests pass. Do not claim overnight
  computation merely because a saved marker says running.
* Host restarted between overnight and today's Continue: no overnight progress
  after01:10UTC. Fetched origin; both remote refs are ancestors, no external
  changes. Do not mistake stale running markers for live processes.
* ACTIVE snapshot builder session35814; publisher47579. Raw world export is
  COMPLETE and stages_completed=[world]. Diagnostics resumed (two workers);
  corrected layers/full corrected export and language/QA/push follow. Matching
  r43 correction training remains complete. Snapshot scientific model03 pinned.
* ACTIVE storm61 session91042, one worker nice5. Full61 damped control PASSED:
  max monthly drift .0035593 C/.0493469mm, same forcing/observations. First fixed
  physical profile resumes after40 passed cases; second must also finish before
  selection/fine/unopenedF. Private source03, active plan_v2 unchanged.
* ACTIVE fitted-flux screen session40089 waits for full r43 publication, using
  private sourcec20f99bd. The new default-upwind numerical implementation passed
  111 focused tests. No climate result for fitted flux yet; do not imply one.
* Retrospective search design audit:36 unique proposals, rank9, condition6.53;
  whole-start linear prediction MAE .57/1.34/.65%, comparable to .86% gain.
  No unseen data, new candidate selection or global-minimum certificate.
  Public plot/evidence ready, browser71studies168images, no errors.
* New prospective fixed bound-probe screen follows the completed fitted screen
  (then reuses its exact fresh pinned-source r43 control). Four profiles:
  positive marine threshold .15/.05, branch drying .4/day, .15/.4 combination.
  Zero threshold is intentionally AVOIDED because it disables the marine gate.
  Eight reused regions only, no selection/fine/F/adoption/atlas change.
  Driver scripts/screen_parameter_bounds.py; plan calibration/parameter_bounds_20261103.
* Space3.1GB after removing three superseded generated ZIPs; latest verified
  r42 final bundle and all maps/source/results preserved. Cleanup receipt tracked.
* Main atlas template now shows actual metadata physics_profile in loaded-data
  status. Final r43 publisher will refresh normal pages from this template.
  Both remote branches must be atomically pushed at milestones. Continue after
  pushes, post generated maps, never claim a background job survived a restart.

---

# Latest running jobs — 3 November 2026, Warsaw

* Main physical option c20f99bd: conservative fitted vapor face transport,
  `moisture_flux_scheme="exponential"`, default upwind unchanged. 111 focused
  tests plus 33 declaration/operator tests pass. Screen frozen in6bd040ae,
  private modelc20f99bd, session12649 waits for r43 publication; no F/adoption.
  Plan calibration/fitted_flux_20261103/plan.json. Main driver/helper hashes
  are frozen; do not edit them during active studies.
* Atlas source-data preflight restored pinned /land/ after /ravages/. Snapshot
  scientific sources unchanged; all harvest provenance inputs verified present.
  Current build session28453 and publisher37574 (older sessions failed). Raw
  farming/population/foraging exports now complete; political/trade export runs.
  Source-root repair remains8cfdf7b4, original validated model03c4351f.
* Storm61 session62644 is integrating its full numerical control, no physical
  candidate yet; see output/storm_expansion_20261103b/status.json. Main helper
  scripts/run_atlas_snapshot.py cannot be edited while this frozen driver runs.
  Future initial sparse-checkout setup must include /land/ as well as /ravages/;
  current snapshot has them manually restored from its exact pinned commit.
* Completed factorial now published to research companion, all four scores and
  matched monthly curves; browser QA70 studies166images, no errors. Producer
  scripts/publish_storm_factorial.py. Default model/atlas labels remain separate.
* New zero-integration observer scripts/diagnose_face_convergence.py observes
  fixed-state point-to-flux advection difference on verified raw r43 world.
  It is not a rainfall prediction and does not include removing the old import
  closure. Two analytic tests pass; outputs output/face_convergence_20261103.

---

# Active continuation — 3 November 2026, 01:40 Warsaw

* r43 is adopted (58e19b16), after all 39 search records, paired reproduction,
  fine28 and sealed-e validation. S49=.991378006, fine28=1.008070474,
  sealed-e=.999790900 (effectively tied). T49=1.878921 C, rain loss=.49314846.
  All planet/orbit settings fixed. E is now spent; reserved F remains unopened.
* Normal atlas STILL r42 pending the complete pinned r43 rebuild. Build session
  98719, publisher 68393. Snapshot: output/atlas_r43/snapshot, source 8cfdf7b4,
  scientific model exactly validated 03c4351f. Correction training COMPLETE.
  Linked input receipt paths and omitted Ravages data repaired in f75e631c;
  exact snapshot helper repair is merged into main (c0d87cfc). Raw world climate
  checkpoint verified, target agreement 34.2273 -> 34.4712%; no relabelling of
  older served maps. Rebuild is resuming export from its saved checkpoint.
* Original conservative replay COMPLETE (03c140e2), no winner. Isolated storm
  factorial COMPLETE (a4e131d2): storm-only S8=.9729019, rain loss -4.36%,
  temperature -1.06%. Flux alone S8=2.1720; added accounted rainout S8=1.1108.
  This is reused eight-region development evidence, not adoption/generalization.
* Broader fixed storm-r42/storm-r43 comparison prospectively declares 61 regions
  (49 historical + spent D/E), reports S49 separately, no regional/group veto.
  Driver scripts/expand_storm_exchange.py active plan is plan_v2.json under
  calibration/storm_expansion_20261103. Session 62644 (one worker, nice5),
  output/storm_expansion_20261103b/status.json, own pinned model worktree03.
  Plan A stopped at setup waiting for failed training receipt: ZERO integrations.
  Revision B changes orchestration hashes/output only; all parameters/policy
  unchanged. Full damped control first; then BOTH61 cases before selection,
  one frozen finalist -> paired fine28 -> reserved F once. No auto-adoption.
* Public research companion adds completed r43 calibration and raw world preview;
  generated by scripts/publish_r43_calibration.py. Keep it committed before the
  final atlas publisher packages. Historical r39 cards explicitly historical.
* Exact resumable market-access/trade checkpoints committed03c4351f. Source
  snapshot isolates atlas from main development; don't alter shared raw input
  archive bytes or legacy shared derived cache files while studies are active.
* ALWAYS atomic push BOTH refs: claude/ecstatic-wozniak-rtrwd2 and DEFAULT
  claude/friendly-turing-43ygeu. Launcher fix badaefe7 fresh port/URL/no-store and
  verified release.json is published to both. User wants continuous iteration,
  commits/pushes at milestones, generated maps posted, no pause after pushes.
* CPU quota2, disk ~2.4GB free. Main .venv scientific libs; system python has
  Playwright, Chromium /usr/bin/chromium. Long jobs foreground persistent exec
  sessions. No new subagents. Dates Europe/Warsaw. Research server8766 running.

---

# Active continuation — 3 November 2026 (Warsaw)

* The workspace restarted; old processes/sessions were gone. Resumed frozen
  three-start search in persistent session **34654** (nice 5, two workers) and
  conservative replay in **97823** (nice 10, one worker). No source or parameter
  changes were made to either. Third search start has 9/13 records; starts 1/2
  each have 13. Best still chain 1, n=7, S49 0.9913780. No sealed-e results.
* **Automatic paired validation is now queued**, session **70465**, using
  `calibration/r42_multistart_validation_20261102/plan.json`. It waits for all
  39 records; freezes and commits one finalist plus all records; reproduces
  both full dev49 vectors and actual reference footprints; runs paired fine28;
  commits qualification before opening sealed e only if both gates pass.
  Every outcome/raw packet is retained. It commits/pushes its own artifacts,
  but does NOT adopt physics or rebuild an atlas. Four targeted tests passed.
* **Launcher stale-page fix is published** in badaefe7 to BOTH branches:
  `claude/ecstatic-wozniak-rtrwd2` and default `claude/friendly-turing-43ygeu`.
  The default was an ancestor and was fast-forwarded, without history rewrite.
  User's screenshots proved their metadata were current (70 Earth modes,
  Whittaker 1.44%) but browser showed the old 22 October hub. Normal launches
  now use a fresh available port plus unique URL; explicit ports remain
  supported. Launcher prints folder, checkout branch/commit, and r42 release
  only if all metadata and normalized hub hashes match atlases/release.json.
  build_fit_hub regenerates that manifest; packaging includes it. Windows
  line-ending normalization is tested. Real stale-cache/browser test, 1,000
  Windows-checkout assets, portable launch and three unit tests passed.
  Receipts/screenshot: output/launcher_refresh_20261102. User was told to pull,
  close the old tab, rerun the .bat, and use its new URL. Never say the launcher
  automatically downloads updates; it still serves local files only.
* Conservative screen: numerical control and first THREE physical profiles
  complete (4/5 total). Combined ratios vs r42 control: flux+storms 2.1144,
  mass-balanced counterflow 1.4562, independent reservoirs 1.6166. The final
  resolved-drying profile is running. None adopted; no partial-profile score.
  Source review/figure: `scripts/review_r42_transport.py` and
  `output/r42_transport_review_20261102`. Research companion now opens on
  these results, explicitly marking pending outcomes, with 32 verified raw
  packets. `scripts/publish_r42_transport.py` updates it; browser navigation,
  dark/light, mobile, images and downloads passed before the fourth data row.
* New prospective factorial, committed in e23ba585, queued in session **71498**
  behind the original screen. Plan: calibration/r42_storm_factorial_20261102.
  Four profiles: vapor flux alone; symmetric storms alone; accounted crest
  condensation; flux+accounted condensation. Baseline r42 eddy_rainout is ZERO;
  the latter two explicitly ADD eddy_rainout=1 (local saturation), not an
  inherited active cap. All four construct with the same Earth planet, no
  imposed wind/SST. Maximum 32 reused-region integrations, no retuning, unseen
  evaluation, adoption or normal atlas changes. Driver will publish all results
  to both branches. Report: reports/TRANSPORT_FACTORS_20261102.md.
* `scripts/review_r42_multistart.py` is ready for selection.json after all starts.
  It plots every start and estimates descriptive region-mix sensitivity. This
  resampling is explicitly not selection-corrected generalization uncertainty.
  Analytic scaled-error test passed. Do not run it before selection exists.
* Canonical model/benchmark sources remain frozen for all active/queued studies.
  Independent producers/plots may change. Keep the normal atlas on adopted r42
  until a fully qualified candidate is reviewed and adopted. Future atlas
  publication must keep BOTH remote branches current, not just development.

---

# Post-publication physics continuation — 2 November 2026, 15:48 UTC

* All atlases are published and verified; see release notes immediately below.
  Latest pushed bookkeeping/preview commit **e95a9677**, release **c55e705c**.
* Conservative replay session **61643** passed all eight damped numerical
  controls (forcing/observations equal, strict checks passed, all monthly
  field drifts within prospective limits). It is now integrating
  `flux_conservative`, followed by counterflow and reservoir variants.
  Live status: `output/r42_conservative_replay_20261102/status.json`.
  This experiment cannot adopt physics or update the atlas. Its driver will
  retain every profile outcome, commit its completed result packet, and push.
* Three-start calibration session **75930** reached **chain 3** at 15:46.
  Chains 1 and 2 completed 13 evaluations apiece. The best remains the chain-1
  candidate S49 0.9913780 (T −0.27%, rain −1.46%). Wait for all 39 and the
  selection.json finalist before validation. No sealed-e evaluation yet.
  The portfolio driver itself does not commit, validate or adopt candidates.
* Canonical model/benchmark sources remain frozen for BOTH active experiments.
  Do not change their source hashes mid-run. Next after portfolio completion:
  freeze/commit the one finalist, reproduce paired dev49 on current geometry,
  paired fine28 (California, western Europe, Japan, NZ), then only if both
  qualify run the declared unseen set e once, with r42 as its paired control.
  `scripts/validate_v3.sh` defaults to r41 and spent set d: override these or
  run its steps explicitly. Aggregate improvements count; regional/group
  regressions are reported, not individual vetoes. Reproduction checks must
  account for the recovered Tripolitania footprint, not its obsolete cache.

---

# r42 atlas PUBLISHED — 2 November 2026, 15:43 UTC

* **Release commit c55e705c is pushed** to
  `origin/claude/ecstatic-wozniak-rtrwd2`; remote HEAD was read back and matched.
  The normal `atlases/earth_fit` folder and `.bat` launcher now serve r42.
  Free-fit and Whittaker map data are byte-unchanged; Whittaker remains 1.44%
  outside the diagram. Three final browser tests passed, Windows checkout
  retained 1,000 byte-exact assets, and the portable bundle passed 560 links,
  1,554 entries and the fresh extracted launcher. Receipts:
  `output/atlas_r42/final_qa/{publication,completion,portable}.json`.
* Earth atlas: 70 raw modes, 55 corrected modes, all five language layers
  restored. Raw target-zone strict agreement 34.23%, corrected 36.56%; these
  fantasy-world target agreements are separate from Earth validation skill.
  R42-trained dev31 correction scores: temperature 1.7144 -> 1.5616 C,
  rainfall loss 0.4347 -> 0.4233 with geographic clusters held out.
* Release session 83151 and finalizer 95390 both finished successfully.
  Do not rerun promotion. Old r41 atlas is retained in
  `output/atlas_r42/previous_atlases/earth_fit_r41`; complete portable ZIP is
  `output/atlas_r42/final_qa/rotclimate_r42_atlases.zip` (not in Git).
  The prospective publication source freeze has completed.
* Calibration session **75930** is running again. Its two workers were
  temporarily SIGSTOPed at 15:37 to prioritize atlas export; watchdog session
  33364 automatically resumed both at 15:43. This changed no model inputs,
  tolerances or candidate order. Search still uses frozen source identities.
  Do not edit canonical model code until the search completes.
* Conservative replay session **61643** started its damped numerical control
  at 15:43 after observing the verified publication marker. California has
  completed. Watch `output/r42_conservative_replay_20261102/status.json` and
  `reference_damped.log`. It must pass forcing/observation equality, strict
  checks and declared monthly-field drift before any physical profiles.
  Its canonical model sources remain frozen too. No candidate adoption or
  sealed-e evaluation has occurred.
* Posted rainfall/Whittaker preview is retained in
  `output/r42_atlas_preview_20261102`; rendering now reads both exact published
  Git revisions, so later atlas overwrites cannot invalidate the comparison.
  User was told the atlas is ready and to pull then run start_atlases.bat.

---

# Current jobs — 2 November 2026, 15:35 UTC

* The r42 release is still running in session **83151**. Raw export and
  correction training finished; corrected climate, farming, population and
  foraging exports finished. Corrected political reach is routing freight
  (season 2/4 complete). Watch `output/atlas_r42/corrected.log` and
  `output/atlas_r42/resumed_20261102.log`. The served Earth atlas remains r41
  until staging is complete. Latest user ETA: 15–25 more minutes at 15:32 UTC,
  including final checks and push; explain any overrun honestly.
* Finalizer session **95390** waits on RELEASE DONE using committed
  `calibration/r42_atlas_publication_20261102/plan_v2.json`. Do not edit its
  guarded model/producer/template/research sources. It will promote/verify
  the release, smoke-test all three atlases, test checkout/portable launch,
  commit only its declared artifacts and push. Preserve the r41 backup.
* The three-start search is still session **75930** (nice 10). First start
  completed 13 evaluations; second has 11/13 logged. Best provisional S49
  0.9913780 relative to r42 (temperature −0.27%, rain loss −1.46%). No adoption
  or sealed-e run before all starts and finalist validation.
* New conservative-moisture replay is committed and queued in persistent
  session **61643**, nice 10, one worker. It waits for finalizer status
  `finished_pushed`; see `output/r42_conservative_replay_20261102/status.json`
  and its sibling `.log`. Prospective plan/README:
  `calibration/r42_conservative_replay_20261102`. Eight existing development
  regions, a damped numerical control first, then four existing conservative
  transport/counterflow/reservoir profiles, maximum 40 new integrations.
  Strict checks unchanged. All outcomes retained, no partial-profile averages,
  no automatic adoption or map changes. It commits/pushes only its own results.
  Three targeted tests passed. Canonical physics is unchanged.
* Created and posted a comparison of r41/r42 corrected annual rainfall and
  Whittaker maps: `output/r42_atlas_preview_20261102/`. Existing exported maps,
  no model rerun; script and byte hashes retained. The final atlas still needs
  trade export and final QA. Free/Whittaker map data are unchanged.
* Latest pushed commit before this note: **031985b2** (queued physics screen).

---

# Release completion queued — 2 November 2026

* Active publication declaration is
  `calibration/r42_atlas_publication_20261102/plan_v2.json` (committed).
  `scripts/finalize_r42_atlas.py --run .../plan_v2.json` is running in persistent
  session **95390**, at nice=5. Watch
  `output/atlas_r42/final_qa/automation_status.json` and
  `output/atlas_r42/finalization.log`. The older plan.json was NOT executed
  and is superseded; its self-source guard no longer matches.
* This job waits for the existing release's RELEASE DONE marker, checks source
  identities (including the declared hub-label change), raw r42 checkpoint,
  matching physics/correction models, language layers and unchanged other-fit
  map data. It browser-tests the final atlases, tests Windows checkout and the
  complete portable bundle, then commits only whitelisted release artifacts
  using git commit --only and pushes the resulting commit. User's unrelated
  staged work and already-staged deletions are covered by an actual Git test.
  Eighteen new targeted tests pass in this iteration.
* The publication plan guards producers, templates and the research companion.
  Do not edit those files while waiting. Do not run another finalizer or
  start the promotion script again. If the job fails, inspect its exact
  receipt and retained logs; preserve the declaration and unfinished work.
* Raw r42 atlas browser check passed; shared physical settings match the r42
  profile exactly, strict world target agreement is 34.23% (r41 32.56%).
  All nine surroundings checks and the three-extra-year repeatability check
  passed. Production is waiting for the separately started correction job.
* Temperature correction training is complete: dev31 raw monthly T MAE 1.7144
  -> cluster-held-out 1.5616 C. Full-grid 14 km field reconstructions have
  completed; rain pattern training/evaluation follows. Release and correction
  jobs serialize their common output via flock and a verified receipt.
* New research companion passed keyboard/deep-link, mobile/dark/light checks;
  Windows checkout preserves 997 asset bytes exactly. Updated portable bundle
  passed 560 links / 1551 archive entries / freshly extracted launcher. These
  checks precede the final r42 corrected atlas; that gets its own final QA.
* Best provisional search result is now S49 0.9913780 relative to r42 (T −0.27%,
  rainfall loss −1.46%), still only partway through the first of three starts.
  The old 0.56% candidate remains historical intermediate progress. No early
  adoption, no sealed-e evaluation. Current campaign source hashes unchanged.

---

# Iteration update — rainfall processes and atlas release, 2 November 2026

This section supersedes the earlier job-stage notes.

* Production physics is unchanged r42. The three-start 49-region campaign is
  still active (`output/r42_multistart_20261102b`). First generation has one
  provisional candidate S49 0.9944235 (T −0.96%, rain −0.15%); historical
  holdout group +7.75%, retired desert group −8.37%. Do not adopt/select early:
  all 39 evaluations, paired fine-grid and frozen finalist/sealed validation
  remain required. Set e is untouched. Background search has nice=10.
* Completed four **full-footprint r42 moisture diagnostics**, exactly
  reproducing ordinary T/P benchmark errors. Plan and receipts:
  `calibration/r42_rain_diagnosis_20261102`, `output/r42_rain_diagnosis_20261102`.
  Tripolitania's main error is false summer rain (JJA 1.146 vs 0.007 mm/day),
  whereas North India's monsoon is weak (2.623 vs 5.643). Signed column terms
  are concentration-equation tendencies, not global mass conservation or
  independent water-origin tracers. Monsoon drying is a subset of total drying.
* Completed isolated **continuity-limited branch drying** probe. Frozen copy
  lives under `experiments/descent_continuity_20261102`; it does NOT replace
  or monkeypatch production. Ordinary / disabled / enabled runs in four regions
  all pass; disabled reproduces all eight full-domain output arrays exactly.
  Aggregate four-region error **worsens 1.50%** (rain +2.70%, T +0.30%); India
  rain improves 2.56%, desert worsens 8.18%. Not adopted or advanced.
  Source diff, raw fields and every result retained in
  `output/descent_continuity_20261102`; report `reports/RAIN_PROCESSES_20261102.md`.
* The served **Climate accuracy** companion now opens on these completed
  results, with two figures and eight verified raw-packet downloads. Its old
  r39 headline cards are explicitly historical; the current r42 overview
  links the release/reference-recovery evidence. Publication script:
  `scripts/publish_r42_rain_processes.py`. No normal map fields changed.
* r42 raw atlas export has finished (14:19 UTC); diagnostics are running.
  Release is still `output/atlas_r42/release.sh`, persistent session 83151,
  `output/atlas_r42/resumed_20261102.log`. Raw trade export was expensive:
  463,000 physical graph nodes, not the 116×250 climate grid. `py-spy` read-only
  stack sampling confirmed progress in market access, then ordered shipments.
* **Correction training is now running independently in parallel**, at nice=5:
  session 75656, log `output/atlas_r42/corrections_early.log`, per-case logs
  under `output/earth_correction_r42_20261101`. The release will call the same
  script later. `scripts/retrain_earth_corrections.sh` now locks its output;
  a complete artifact/source/input-cache checksum receipt permits reuse,
  otherwise ordinary per-case source/reproduction checks apply. Never start
  another unlocked writer to these folders. Canonical rotclimate/*.py remains
  unchanged so the running atlas checkpoint/search source identities hold.
* Eleven new unit tests passed for diagnostics, continuity bounds and training
  receipts. The new research page passed browser checks before its historical
  headline relabel; rerun after that text update. Finish Windows checkout,
  portable package and current/final atlas browser QA before final publication.
* On release completion: inspect corrected models/evaluations, raw/corrected
  atlas browser flows, preserved language layers, page notes and hub. Commit
  all r42 release assets and correction models (force-add required ignored NPZ
  model files), retain previous r41 atlas outside publication. Push to
  `claude/ecstatic-wozniak-rtrwd2`. Do not rerun the whole promotion script once
  its r41 backup exists. Do not treat intermediate fit progress as adoption.

---

# Latest state — reference recovery, 2 November 2026

This supersedes the running-search details in the next section.

* The original pilot stopped at its first logged r42 control: 48/49 error
  pairs reproduced exactly, but Tripolitania did not. Auditing the actual
  case hashes with the original float-valued `cell_km` confirms **48/49
  input cases match exactly**, too. Tripolitania has 182 scored land cells
  versus the archived 195 despite identical scientific-source and WorldClim
  archive hashes. The exact old aggregation cache is unavailable; a legacy
  name-only cache key is a possible cause, not a proved diagnosis.
* Fresh **paired r41/r42 runs on all six retired-c regions** completed strict
  checks and retained raw NPZ cell packets in
  `output/r42_reference_recovery_20261102`. Reconstructing S49 with these
  matched inputs gives **0.9628116258** vs r41, still a 3.72% improvement.
  Every one of the 49 recovered r42 reference error pairs matches the saved
  current control to 1e-10. Original scores and failed runs are retained.
* Active search is now the prospectively frozen revision
  `calibration/r42_multistart_20261102b/campaign.json`, same bounds, seeds,
  39-evaluation budget and selection rules, with retired-c references from
  the fresh run. Output `output/r42_multistart_20261102b`, execution session
  75930, two workers. Original `output/r42_multistart_20261102` is a STOPPED
  diagnostic run, not an active search. Sealed set e remains unseen.
* The revised search's first full control completed: S49 = S31 = 1.0, all
  49 reference error pairs reproduced to 1e-10. Candidate evaluations have
  now started; no candidate is adopted. The first control and frozen search
  identity are retained in `output/r42_multistart_20261102b/chain_1`.
* The r42 atlas simulation completed and saved its verified checkpoint;
  export is running. Its persistent release session is still 83151. The
  served atlas stays r41 until staged corrections and exports finish.
* Do not edit `rotclimate/*.py` while the release/checkpoint and calibration
  sources are frozen. A future cache fix should include complete geometry
  and source identity in aggregate cache keys or manifests and explicitly
  handle legacy unmanifested NPZs. Do not silently relabel an old score.

---

# Active continuation — 2 November 2026

Read this section before the older handoff below.

* Fetched `origin/claude/ecstatic-wozniak-rtrwd2` at `46db7674`, the newer
  development branch. The old checkout's two terrain numerical-probe commits
  remain on local branch `work`; its untracked outputs were preserved. Active
  branch: `work-latest-20261102`, tracking the newer remote branch. Both remote
  branch fetch refspecs are now configured locally.
* Adopted physics **r42**, not r39. Archived paired 49-region raw results:
  monthly T MAE **1.9770 -> 1.8849 C**, rain loss **0.51530 -> 0.50077**,
  S49 **0.9626111** vs r41. 29 regions improve / 20 worsen under the combined
  metric. Set d S **0.9406**. These are regional benchmarks, not global skill.
* **The served Earth atlas is still r41 until the release completes.** The
  inherited r42 release stopped during the simulation in the previous
  environment. Its path was hardcoded to `/home/user/rotclimate`. The resumed
  `output/atlas_r42/release.sh` is repository-relative and builds corrections,
  corrected animations and language layers in staging before promotion;
  the r41 atlas is retained. Do not label the atlas r42 before promotion.
* Calibration mismatch fixed: `scripts/gate_calibrate.py` now accepts
  `scoring_policy: v3`, equal-region S49 including retired a/b/c, reports
  group regressions without penalties, keeps the individual T/P safeguards.
  Legacy v2 plans retain their objective. v3 resumes freeze the plan,
  references and source identities. r42's archived score matches the independent
  release gate exactly. 69 targeted tests passed (calibration, guarded search,
  physics switches and Earth corrections).
* Frozen pilot `calibration/r42_multistart_20261102/campaign.json`: three
  independent CMA starts (r42 and two scrambled Sobol centres), 13 evaluations
  each, existing r42 parameter bounds, no orbital/world changes. Each start
  first reproduces r42 over all 49 regions to 1e-10. No sealed evaluation
  occurs in the runner. This tests starting-point sensitivity within one
  parameter box; it cannot prove global optimality.
* Fresh sealed set e: `calibration/sealed_20261102e`. Six scored rectangles
  checked against all 61 earlier definitions, none overlapping; forcing halos
  are not independent. Never use this set in search or mechanism design.
  Freeze one finalist after the S49 / 28 km gates before its single evaluation.
* Running jobs use persistent foreground execution sessions. In this executor,
  shell-detached `nohup ... &` children were terminated after their launching
  shell ended; those interrupted logs/output directories were preserved.
  A subsequent clean restart has no completed candidate yet at this handoff's
  initial writing. Check processes and receipts; do not trust stale PIDs.
  - r42 release: `output/atlas_r42/resumed_20261102.log`, per-stage logs in the
    same directory. Execution session 83151.
  - search: `output/r42_multistart_20261102/status.json`, `chain_1.log`,
    `chain_1/evals.jsonl`; execution session 90518. Two workers alongside the atlas build. Resume with `.venv/bin/python -u -I
    scripts/run_calibration_portfolio.py --campaign
    calibration/r42_multistart_20261102/campaign.json --out
    output/r42_multistart_20261102 --workers 2` in a persistent session.
* The first full control reached a logging integration error (`n` counted both
  evaluations and regions), before metrics were persisted. Fixed by keeping
  `n_regions` separate; a real CMA/log/checkpoint/resume integration test now
  covers the path. The failed run and exact source are retained in
  `output/r42_multistart_20261102_recording_failure`; the clean replacement
  must reproduce its baseline before any candidate claim.
* On finishing the atlas: browser-smoke raw/corrected views, package and verify
  the portable bundle, then commit/push all release assets and update the
  r42 report. Packager now includes r40-r42 and current foraging/language/reach
  method reports, and avoids claiming the Earth atlas is still r38/r39.
  Do not rerun the whole release over a promoted atlas/retained r41 backup.
* Portable bundle verification passed: 543 links, 1537 archive entries, fresh
  extracted launcher. Current browser smoke checks passed all three atlases.
  Windows-style checkout passed 986 byte-exact atlas assets after fixing
  `.gitattributes` to include nested corrected-climate JSON/CSV/binary files.
* Dependencies restored: scikit-learn added to requirements; installed the
  existing Playwright package's Chromium headless shell for browser checks.
* Accuracy figure and paired aggregate details:
  `output/r42_resume_20261102/{r42_accuracy.png,accuracy.json}`.

---

# Handoff — Earth corrections, physics gaps and r40 (30 October 2026)

Branch `claude/ecstatic-wozniak-rtrwd2`. Previous handoff (regional rainfall
benchmark, terrain research cores, detached jobs of an earlier container that
no longer exist): `reports/handoffs/BEFORE_EARTH_CORRECTION_20261030.md`.

## State

* Adopted Earth physics is now **r40** (`calibration/local_accuracy_20261023/r40_params.json`), also in the Earth-fit atlas:
  r39 plus e55/e55b monsoon westerlies, e56 shelf rule, e58 sea column under
  cold air, and refitted itcz_shift / precip_tau_days / monsoon_descent.
  Gate S 0.9932, 28 km 0.9953, sealed six 0.9671 (used once for r40).
  Evidence: `output/physics_gaps_20261030/refit3/`, report §12.
  The Earth-fit atlas publishes r40 on the r38 world geometry (see Next 1).
  New switches in `rotclimate/model.py` (e54-e61) all default off;
  r39 and r40 cells reproduce bit for bit.
* The Earth corrections below were trained on **r39**; r40 versions are in
  `calibration/earth_correction_r40_20261031/{temperature,rain_pattern}`
  (`scripts/retrain_earth_corrections.sh`; held out T 1.807 -> 1.548 C,
  rain 0.4329 -> 0.4201; 14 km T 1.283, rain 0.4424). Use the pair that
  matches the physics (they check its hash).
* Fresh-container setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt scikit-learn`;
  WorldClim 2.1 5′ `tavg prec elev vapr` zips into `data/cache/worldclim/`
  (geodata.ucdavis.edu); `python -I scripts/prepare_woa18.py --download`.
  The r39 dev31 run then reproduces every archived cell hash.
* New: `rotclimate/correction.py` (numpy-only application),
  `scripts/train_earth_correction.py`, `scripts/evaluate_earth_correction.py`,
  `scripts/plot_earth_correction.py`, `tests/test_earth_correction.py`.
  Rain pattern: `scripts/collect_earth_fields.py` (full-grid monthly winds),
  `scripts/train_rain_pattern.py`, `scripts/evaluate_rain_pattern.py`.
  Model files: `calibration/earth_correction_20261030/` and
  `calibration/earth_rain_pattern_20261030/` (final model, 12 held-out fold
  models, evaluation, protocol hashes each). Evidence and figures:
  `output/earth_correction_20261030/`. Report: `reports/EARTH_CORRECTION_20261030.md`.

## Measured (held out by geographic cluster)

Monthly land T MAE 1.793 → 1.540 °C over 31 regions, every policy group
better; 28 km pairs 1.896 → 1.274; 14 km pairs (atlas scale) 1.908 → 1.288; sealed Norway/SE Africa 2.621 → 2.143.
Worse: six regions (South Brazil +0.22 °C worst), seasonal range MAE +6 %,
coldest month +1 %. Köppen agreement ~unchanged (rain dominates classes).
Rain *amount* corrections were **rejected** (cluster holdout made unseen
continents worse). A **local rain pattern** (wind over terrain, 300 km local
mean removed) passes: loss 0.4424 → 0.4281, every group better, 4 regions
slightly worse (western Europe +0.027); 28 km −1.8 %, 14 km −1.5 %, sealed
−2.4 %. Köppen exact 47.1 → 48.6 % with both stages; main group dips on fine
grids (California, New Zealand). A domain-mean version made broad shifts on
the larger map and was replaced. Air-coupled SST seasonality (e53) and coupling retunes
were tested and **rejected** (S 0.999–1.023), code reverted.

Full test suite: 1605 pass; 7 fail identically on the pre-session commit
7e0b146 (harvest `settlement_cored`, Mediterranean spin-up `column_projector`,
zonefit missing `calibration/r19p_earthlike/best_params.json`).

## Physics gaps (reports/PHYSICS_GAPS_20261030.md)

* New reference: `scripts/prepare_ncep_reference.py --download` (NCEP/NCAR R1
  1991-2020 monthly surface winds, SLP, RH, precipitable water via PSL
  OPeNDAP; the plain download URL is refused, OPeNDAP text works but rate-limits).
* New diagnostic switch `wind_source="observed"` (grid.obs_wind) and
  `scripts/attribute_observed_forcing.py`: observed winds give North India
  933 mm (r39 256, obs 761); observed winds+SST fix the maritime lag; Mexico,
  Texas, Iran flood (rain settings fitted to wrong winds).
* Circulation is the largest gap (single zonal ITCZ, no monsoon westerlies,
  land winds 1.8x too strong, winter trades 2-6x); SST 1-3 C too cold
  (global offset -4.4 C), mid-latitude SST range too large; Tibet too wet.
* New opt-in `dry_heating` / `dry_heating_chi0` (e54): best 3.0 / 0.6 gives
  S 0.9933 but former-holdout 1.038 and mid-latitude 1.027 groups worsen
  (Chile, East Asia downwind of the Gobi); not adopted. All new switches
  default off; r39 cells reproduce bit for bit.
* New opt-in `monsoon_westerly` (e55; plus `itcz_shift_ocean`, which failed):
  cross-equatorial trades turn westerly toward the ITCZ with inflow at the
  boundary-layer angle. w 0.7: North India 256 -> 482 mm, Arabian Sea July
  wind 6.4/3.4 (NCEP 6.9/5.1), but East Australia, East China, Iran wetter;
  training group S 1.045.
* e55b `monsoon_pressure_hpa`: turn only where the model's own pressure falls
  poleward (Arabian Sea yes, Coral Sea/Caribbean no). Frozen refit
  calibration/monsoon_refit_20261030 (48 evals) best: w 0.934, G 2.95,
  dry_heating 0.09, precip_tau 10.93, monsoon_descent 0.0211 -> gate S 0.9938,
  rain -1.5 %, 28 km S 0.9984, but training 1.0055 and mid-latitude 1.0005
  fail; not adopted, sealed six unused. Validation:
  output/physics_gaps_20261030/refit/ (scripts/validate_monsoon_refit.sh).
* e56 `shelf_warm_currents`: the warm subtropical current is scaled by
  1 - s*(1 - deep-sea share), so the Kuroshio stays off the East China Sea
  shelf (East China coastal SST bias +2.6 -> +0.6 C at s 1). Second frozen
  refit calibration/monsoon_refit2_20261030 (shelf + itcz_shift): best w 0.935,
  G 3.29, s 0.62, itcz 14.43, precip_tau 10.08, descent 0.0190 -> gate S
  0.9949, rain -1.7 %, 28 km S 0.9962, training 1.0005 fails (California,
  Iberia); not adopted, sealed six unused. output/physics_gaps_20261030/refit2/.
* e57 `zonal_land_friction` (belts slowed over land, 300 km): US Midwest,
  western Europe, Great Basin better, Central Asia/Anatolia/Levant lose
  westerly water; net harmful. The one model wind is both surface wind and
  ~850 hPa transport wind.
* scripts/compare_column_water.py: winter column water 1.3-1.85x NCEP pw in
  14 regions, winter rain error follows it (r 0.67 log); summer rain 0.5-0.8x
  with columns ~right (r 0.08): summer needs rain-making physics.
* e58 `ocean_column_air`: sea column saturates at the column temperature
  where that is colder than the SST. Korea winter 292 -> 155 mm (94 obs),
  training group 0.988, but Japan/S Brazil/British Isles lose annual rain.
* Third frozen refit calibration/monsoon_refit3_20261030 (+ e58, wider
  precip_tau): 56 evals, one candidate clears every group and is the lowest
  cost -> validated (gate 0.9932, 28 km 0.9953, sealed six 0.9671) -> r40.

## Rules to keep

* The correction is valid only for r39 physics (hash in its metadata);
  refit after any physics change. Keep raw output alongside corrected.
* Score honestly with whole clusters held out: neighbouring regions overlap.
* Do not tune on the sealed regions (norway, southeast_africa); they have now
  been used once for this milestone.

## Next

0. Physics: summer rain-making. reports/SUMMER_RAIN_20261030.md: humid
   summers lack 10-22 % column water (from the sea), x3 through the RH gate;
   e59 (warm air over cooler sea, gated by subsidence), a frozen refit with
   ocean_rh/e58/tau (best S 1.0008) and slower sea uptake all fail against
   r40. Next: season-aware rain-making (mid-latitude summer convection is
   ~absent: instability from 22 C, closure ~0.1 mm/day) and winter overflow
   of supersaturated columns. eddy_rh_cap (e38b) + land_recycling refit
   (calibration/eddy_cap_refit_20261030) passed gate 0.9946 and 28 km 0.9981
   but sealed six 1.0135 (NE US rain +27 %): NOT adopted (judgment; policy
   lists sealed as a record). e60 eddy_cap_contrast_k (cap only for cold-air
   outbreaks) refit: gate 0.9942, 28 km 0.9972, sealed six 1.0406 (NE US
   winter 44 -> 12 mm vs 77): not adopted; the cap deletes real warm-frontal
   precipitation. The sealed six have been run for 3 candidates: declare a
   fresh sealed set before the next adoption. Next physics: direction-aware
   eddy moisture transport (eddies weakened against strong offshore mean
   flow: winter monsoon coasts). e61 eddy_upwind_days built and screened:
   fixes East Asian winters but floods west-coast winters (r40's over-land
   westerlies 2-5x too strong); needs a separate transport wind (~850 hPa)
   beside the surface wind. cold_high_storms 0.25-0.40: small clean gain
   (S 0.998), refit candidate. Then North India's pre-monsoon cold. Gate any change against r40 (REF_NAME=r40 REF_FIT=...
   in scripts/validate_monsoon_refit.sh).
   31 Oct (reports/TRANSPORT_WIND_20261031.md): the transport/surface wind split
   (e62 heat_land_friction / water_land_friction) does not help alone; the
   interiors lack a warm winter sea (scripts/compare_sea_surface.py: r40's
   Mediterranean ~6 C too cold in January, west-coast seas' ranges ~2x WOA18).
   North India's plain sits on the latitude's mean land column (2-3 C too
   cold). Dry heating gated to warm ground (e54c dry_heating_warm_c) + small
   frictions: refit calibration/dry_heat_refit_20261031 passed dev31 (S 0.9879,
   North India T 3.40 -> 2.99) and 28 km (0.9893) but the FRESH sealed six got
   worse (1.0405: Kazakh steppe, Hokkaido ranges grow): not adopted. The fresh
   sealed set has now been seen once (declaration.json seen_by); a dry-heating
   design that spares cold steppes should come with another fresh set.
   e63 inland_sea_lag_days (lagged enclosed seas) alone just shifts East Asia's
   sea error from spring to autumn.
1. World refit for the invented map on r40 (calibration/map_world_r40,
   scripts/world_campaign_r40.py): NOT published. Coarse best 0.1922 vs
   0.1895 but every better candidate breaks a zone/Mediterranean guard; the
   start fails every native protection (zonefit 0.1796 vs 0.1828, strict
   33.1 vs 35.0 %, Med dry 9.0 vs 6.4 %). Audit layouts 590xxx unused.
   reports/R40_WORLD_20261031.md.
   RULE (user, 31 Oct): a release better on the Earth test updates the atlas.
   So atlases/earth_fit is now r40 physics + r38 geometry (reports/ATLAS_R40_20261031.md;
   r38 backup in output/atlas_r40/previous_atlases/). Hosted artifacts (hub,
   free, earth, whittaker; URLs in atlases/artifact_links.json) republished
   with all local features (FORGE etc.): scripts/package_atlas_artifact.py ->
   Artifact publish per atlas; check with scripts/check_atlas_smoke.js.
   Earth-fit atlas has a Corrected topic (scripts/add_corrected_layers.py,
   r40 corrections on the atlas checkpoint; zone agreement 33.1 -> 35.6 %;
   rerun it after any rebuild of atlases/earth_fit, refuses other physics).
2. Fresh sealed set declared 2026-10-31: calibration/sealed_20261031/
   (hokkaido, canadian_prairies, kazakh_steppe, namibia_kalahari,
   southern_italy, north_queensland; no model run on them yet). Use
   SEALED_SPEC=calibration/sealed_20261031/regions.json with
   scripts/validate_monsoon_refit.sh; the old sealed six are development data.
2. Physics for the maritime lag: the land air is ~95 % sea-controlled because
   the land equilibrium is the latitude's continental column (2.3 °C mean over
   Britain). Needs a land surface layer / two-tile coast and recalibration.
   31 Oct (reports/SEASON_PHASE_20261031.md): much of the late spring is the
   band column's temperature-driven snow albedo (53 N: April 4.3 C colder
   than October, real interiors ~0). e65 ebm_land_ice keeps a share of it
   (ice sheets keep all); 0.5 + continental_mean 7 screens S 0.9837 (holdout
   1.0049). Frozen refit calibration/land_ice_refit_20261031 (validate with
   sealed set b). e64/e64b shelf seas following the air: harmful, off.
3. Small: two-scale relief lapse (+~0.8 % T alone).

## Food, foraging and political reach side project (31 Oct)

* Earth-fit atlas opens on the Earth-corrected climate (user, 31 Oct: no
  separate "Corrected" topic): scripts/add_corrected_climate.py renders a full
  corrected copy (climate layers, station packet, farming, population,
  FORGE, political reach) with the normal exporters into data/corrected/;
  one Climate switch (#climate=raw) shows the raw simulation; the change maps
  sit under Fit checks. Supersedes add_corrected_layers.py (topic) and
  add_corrected_food.py. Rerun it after any rebuild of atlases/earth_fit,
  any change to an exporter, or export_reach.py (it needs winds12.npz).
* FORGE's first Earth test (reports/FORAGING_EARTH_20261031.md; frozen plan
  and aquatic addendum in calibration/forager_binford_20261031/): Binford's
  hunter-gatherers with observed climate, North America fits, the rest of
  the world tests. Adopted: terrestrial food x0.5 + coastal/freshwater fish
  (test error x3.0 -> x1.8, fish-share rank 0.78); all atlases rebuilt with a
  Fish share map. Not adopted: long-window median/mean summaries (missed the
  0.02 allowance), food storage (worsens the fit). Weak spot: California /
  Northwest Coast ~3x too sparse; marine scale at its grid edge.
  Data: data/cache/binford_dl (CRAN binford 0.1.0), data/cache/naturalearth.
* Political reach (reports/POLITY_SEASONS_20261031.md): autumn mud ADOPTED
  by a second frozen addendum (addendum_mud_pet_20261031: topsoil layer gives
  both rasputitsa seasons at 6 unseen stations, no mud at 10 dry controls;
  polity.seasons.TOPSOIL_MM = 25; all three atlases' reach rebuilt).
  Droogers-Allen PET changes nothing. Monsoon-coast closure not adopted.
  State strength (reports/POLITY_STRENGTH_20261031.md): second design with
  independent city networks (Parthian capitals; excavated Xiongnu centres)
  is informative and chooses gamma 0: no strength term. Western Med sailing
  diagnosed (scripts/polity_sea_west.py): the west is slow (light NCEP winds,
  'uncertain' storminess in July), long upwind passages ~3x fast (no waiting
  for fair winds). A waiting rule needs ORBIS (test T7) to be tested blind;
  ORBIS is not in the container (o_sites.csv, new_routes.topojson under
  data/cache/orbis). Earth polity data rebuilt by scripts/prepare_polity_data.py
  (data/cache, not committed).

## 1 November 2026 round (reports/SEASON_PHASE_20261031.md sections 5-7)

* East Asia's spring warmth (3-4 C, the refits' blocker) is NOT the sea, the
  surface winds (observed WOA18 + NCEP swapped in: unchanged), the lapse rate
  or cloud shading alone. The storm band is planet-wide (45 N in April) while
  East Asia's jet and fronts stay at 30-35 N; and wet_cooling acts only above
  the annual mean, flattening summers so springs/autumns end too warm.
* New opt-in levers (all off, bit-identical): e66 warm_current_seasonality
  (fixes British seas, worsens land: compensating error), e67
  continental_sea_air (fixes Korea's seas, not the land), e68 storm_baroclinic
  (+ _cold_c, _max_deg; storm band on the model's baroclinic zone), e69
  wet_sun (+ _ref; sunshine-driven wet cooling; with wet_cooling 0 East China
  2.00 -> 1.30 C), world lever ebm_land_scale (planet land by latitude).
* Frozen refit calibration/spring_refit_20261101 (e65 + e68 + e69 + continental
  terms) running; validate with sealed set b (still unseen) -> r41 if it passes.
* Political reach: dry-land towns need water within 40 km on Earth (22.9 km on
  drawn maps, scaled to Natural Earth river density); ORBIS cached
  (data/cache/orbis); sailing constants not adopted (ORBIS blind test).
* FORGE aquatic addendum 2 not adopted (marine scale grid-edge is the NW Coast).
* Off-map land: scripts/offmap_earth_test.py measures the skill an invented
  surrounding costs on Earth (British Isles 0.77 C RMS, mostly systematic, not
  layout noise); full run pending.
* Data fetched for these tests (user-approved, data/cache, not committed):
  HydroRIVERS v1.0 NA/AS/AR tiles (hydrorivers), CLIWOC 2.1 logbooks
  (cliwoc), ORBIS v2 sites + routes (orbis).
* FORGE salmon (reports/FORAGING_EARTH_20261031.md): eight frozen attempts
  with HydroRIVERS; best = attempt 7 (sea-ice factor on the marine supply +
  a_salmon 300, upstream thinning L 800 km, outlets 2-15 C): leave-one-area-out
  CV 0.442 -> 0.372, NW Coast 0.577 -> 0.302, Arctic 0.65 -> 0.52, world
  unchanged; the Subarctic fold always worsens (post-epidemic densities?), so
  not adopted by the rule. A user decision could carry attempt 7 to the maps.
* Sailing: CLIWOC confirms the polar (close-hauled 0.82 vs model 0.85; Casson's
  0.45 rejected). Waiting rule halves ORBIS's error (0.522 -> 0.306) but adds
  Casson scatter (Etesian short passages; western Earth-only storminess); next
  design recorded in reports/POLITY_SEASONS_20261031.md.

## 1 November 2026, after r41 (in flight)

* r41 adopted (reports/R41_20261101.md); release pipeline
  output/atlas_r41/release.sh rebuilds the Earth-fit atlas, retrains the
  corrections and re-exports the corrected climate. Sailing waiting rule
  adopted (SAILING_RULE "wait"), reach of free/whittaker fits rebuilt with it.
* Sealed set b is spent; sealed set c declared
  (calibration/sealed_20261101c: Nova Scotia, middle Volga, Tripolitania,
  northern BC coast, Tibet, Ethiopian highlands; never run).
* W2 frozen (calibration/map_world_r41_planet/plan.json,
  scripts/world_campaign_r41.py): world refit with tilt, eccentricity,
  perihelion, starlight, greenhouse and land-by-latitude free, 300 km
  continuation fixed, guarded search inside the coarse screen. Needs the
  'world_screen' guard form in rotclimate/calibrate.guard_penalty (patch kept
  in the session scratchpad; apply after the r41 release finishes, since the
  release hashes rotclimate sources).
* P3 frozen (calibration/maritime_refit_20261101/plan.json): sea swing (e66,
  e67, e64) + land coupling + wet_sun_ref (r41 warms dry ground); needs a
  plain r41 run of retired sealed set a as its extra reference first.
* FORGE attempt 10 frozen (addendum_forest10): game x (1 - c x closed-forest
  share) for the eastern Subarctic's over-prediction, CV with salmon + ice.
* Results since (1 Nov, later): r41 atlas released and republished (corrected
  climate default, change maps under Fit checks, r41-trained corrections:
  T −11 %, rain −3 % held out). W2 world refit with planet levers: no world
  qualifies (reports/WORLD_PLANET_R41_20261101.md); the best finalist gains
  strict agreement 32.6 → 37.3 % and the Mediterranean but loses the painted
  desert (hot-dry recall 0.246 → 0.176); the nine audit layouts are still
  unseen. FORGE attempt 10 (closed-forest game) not adopted: only the
  Subarctic wants it. P3 maritime refit search running; its validation (sealed
  set c) is queued in output/maritime_refit_20261101/after_search.sh.
* P4 desert refit (reports/DESERT_HEAT_20261101.md): new opt-in e70, e54e,
  e71 (+b/c/d). Candidate 39 passed dev31 (S 0.9826, every group) and 28 km
  (0.9964) but failed sealed set c (S 1.0159: Tibet warmed, Volga/BC coast
  cooled by the land-offset compensation). Not adopted; r41 stays. Sealed
  set c is spent; set d declared (calibration/sealed_20261101d: Egypt,
  Thailand, Finland, central Siberia, Yucatan, Kenya; never run). Next: e71
  without summer-ascent areas (plateaus, monsoon) and without a global offset.
* F11: Mooney (1928) early-contact estimates do not support the epoch
  explanation for the eastern Subarctic (ratio ~1.0 east, 1.3-1.8 west);
  the Shield over-prediction is a model error (soil/wetland, next).
* Desert refits #2 and #3 (P4b/P5): #2 not adopted (sealed d not run);
  #3 (calibration/desert_refit3_20261101, core drying e70b/c + gated e71 with
  rain/top/chi0 gates) search in flight, output/desert_heat_20261101/
  search3.log; validate the best on sealed set d by hand if it beats r41.
* FORGE F14 lifeways (hunters / gatherers / fishers + camp moves) adopted and
  live in the atlases (data/forager_lifeways.json). F15 contact-basin culture
  areas not adopted (ARI vs Murdock areas).
* Language areas from below (reports/LANGUAGE_AREAS_20261101.md; plans in
  calibration/language_areas_20261101/): the owner wants languages grown from
  the land and compared with the polities only at the end.
  - Layer 1 (Gavin group splitting on FORGE density), 1b and 1c: counts within
    x1.5-1.8, richness R2 0.17-0.28; not adopted. Owner to decide on
    illustrative use.
  - Layer 2 (Pinhasi 2005 Neolithic dates): plain distance beats terrain/sea
    and crop-slowed waves held out (950 vs 987/1121 y); 1.0 km/yr, r 0.83.
    Farming spreads by distance; crop rules decide only where it roots.
  - Layer 2b (Diamond's nine homelands): neither FORGE nor productivity
    places hearths (AUC 0.75-0.78 < 0.80). Hearths are the owner's choice.
  - Layer 2c (Nichols / Michalopoulos): ADOPTED. Terrain + land-quality
    variation predict language density on held-out macroareas (R2 0.34 vs
    0.28 climate only, 5/6 macroareas). Fantasy-map preview
    (scripts/language_map_preview.py): ~130 languages, Xšāça ~48; polity
    borders barely follow likely language edges (0.23 vs 0.19).
  - Layer 2d (hearths from the map alone): Earth base rate x productivity
    gives 0.42 expected independent hearths on the map (66 % chance farming
    came from beyond); land beyond (SW 72 %, SE 45 %) and homeland
    latitudes point south; on-map best guess the west coast.
    Model's surroundings picture (layout 1) shows big seas; land link only to
    the NW (cold) -> P(on-map hearth | farming present)
    = 0.34/(0.34+0.66 q), ~70-90 % unless a narrow crossing/land link exists.
  - The preview is in all three atlases (and hosted) as the 'Languages'
    topic: scripts/add_language_layers.py (density, one draw of territories,
    likely boundaries vs de jure borders), labelled illustrative.
* FORGE F13 (food store scored on Binford's storage): not adopted (held-out
  rho 0.00); Binford's ET 15.25 threshold gives rho 0.72 (his own rule).
* Polity A1 (steppe reach from herding land, no polygons): Xiongnu 0.950
  (centres alone 0.728), Tang-Turgesh 0.900 vs bar 0.904; not adopted. Next:
  Tang protectorate garrisons as sources.
* P7 (reports/AUTUMN_PHASE_20261101.md): subtropical land peaks 4-9 days
  early; the marine air does not follow the sea (eddy mixing 1.43/day vs
  air-sea 0.37/day). Fast coupling (e51+e3 0.5 d) helps the Mediterranean
  and British coasts, hurts East Asia (+0.4-1.2 C MAE); blocked by P6.
* P6 evidence (r41): East Asia spring rain 0.5-0.7 of observed, winter rain
  2-3x (Japan, Korea, North China Plain); warm bias peaks Mar-May.

## 1 November 2026, evening: policy v3 and r42

* The owner set aside "no group may get worse": adoption now follows overall
  accuracy (calibration/local_accuracy_20261023/policy_v3.json): S over the 49
  development regions (dev31 + retired sealed a, b, c) improves >= 0.5 %, T and
  P within +1 %, paired 28 km within 1 %, the next unseen sealed set not worse.
  Groups are reported only. scripts/gate_v3.py + scripts/validate_v3.sh.
* r42 = desert refit #3 candidate 1 (e71 compression warming + e70b/c branch
  drying): S49 0.9626, 28 km 0.990, sealed set d 0.941 (rain -11 %). Holdout
  1.039 and mid-latitude 1.022 as groups (Manchuria, NZ, southern coasts).
  reports/R42_20261101.md; release output/atlas_r42/release.sh.
* Sealed set d is spent; declare sealed set e before the next search.
* Future searches: score on S49 (no group penalty) to match policy v3.
