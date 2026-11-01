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
