"""Package the active Earth atlas and two retired snapshots with a local HTTP entry page.

Data remain external files: open the extracted bundle through an HTTP server,
not file://. The bundle includes the report, biome methods and source license.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['free_fit', 'earth_fit', 'whittaker_fit']


def page_dependencies(files, root=ROOT):
    """Include the local documents/assets actually linked by packaged pages."""
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.paths = []

        def handle_starttag(self, tag, attrs):
            self.paths.extend(v for k, v in attrs if k in ('href', 'src') and v)

    included = {p.resolve() for p in files}
    pending = [p for p in included if p.suffix == '.html']
    root = root.resolve()
    while pending:
        page = pending.pop()
        links = Links(); links.feed(page.read_text(encoding='utf-8'))
        for link in links.paths:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (root / unquote(url.path).lstrip('/') if url.path.startswith('/')
                      else page.parent / unquote(url.path)).resolve()
            target.relative_to(root)
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                raise ValueError(f'Broken local atlas link: {page.relative_to(root)} -> {link}')
            if target not in included:
                included.add(target)
                if target.suffix == '.html':
                    pending.append(target)
    return sorted(included)


INSTRUCTIONS = '''Rotclimate: Earth atlas and retired snapshots

Extract this whole archive, then double-click start_atlases.command (macOS)
or start_atlases.bat (Windows), with Python 3 installed. Or run:

    python3 scripts/serve_atlases.py

The launcher opens your browser. Keep its terminal window open while browsing.

Earth fit is the active atlas. Free fit and Whittaker fit are retired
snapshots, kept for reference; they stopped receiving updates on 8 November
2026. The Earth atlas identifies its adopted physics and terrain release.
The launcher verifies the release and opens the current hub. The methods
explain the scores, assumptions and numerical checks.
See reports/LAKES_DELTAS_20261108.md for the lake and delta update,
reports/R44_RECONSTRUCTION_20261109.md for recovered correction models, and
reports/CEREAL_DELTA_IRRIGATION_20261109.md for the calendar integration fix.
These are simulated potential climates, not observed vegetation maps.
The hub's Climate accuracy and joint fit page includes measured Earth errors
and rainfall-source maps. The Earth-fit page identifies its adopted physics
release and distinguishes raw from Earth-corrected climate. Earth benchmark
scores are not measured accuracy of the fantasy geography.
The hub's Food, farming and society lab presents c.200 AD proposals and a
manufactured seasonal-storage example, separately labelled from atlas results.
See reports/ITERATION_20261022.md for the coverage refinement and its tradeoffs.
See reports/CLIMATE_PHYSICS_20261023.md for subsequent physics experiments,
paired calibration checks and the criteria used to select published climates.
See reports/RAINFALL_ACCURACY_20261023.md for observed local rainfall errors
and the separate rainfall calibration experiments.

The Farming and Health and ecology topics bring Harvest analysis into each
atlas. Overview includes settlement potential and expected density. Choose
frontier, central or settled-core occupation and environmental malaria or no
malaria penalty. These are c.200 AD scenarios, not a reconstructed census.
Source models, explicit coefficients, province totals and CSVs are inside
each atlas. See reports/HARVEST_MIGRATION_20261022.md for the method.

Food and work adds partial cereal field-work maps, cropped land per food
target, reaping staffing under supplied harvest windows, and retained
calendar alternatives. The work counts stop at the threshing floor; they
do not estimate total subsistence work or population. Select a place for
readouts and CSV, or download the grid arrays. The methods explain the
historical source and scenario assumptions.

Administration adds seasonal access comparisons for recorded commandery seats,
marked places, proposed towns/tracks, roads and military markers. The typed
inventory links geographic spreadsheet evidence by ID and retains disputed
seats. These are two-day travel-access scenarios, not territorial ownership,
allegiance, military strength or validated city populations. Three declared
settlement-placement seeds show sensitivity, not probability. See the methods
report and the in-view CSV/NPZ downloads.

Administrative links adds six schematic hierarchy views under Administration:
seasonal travel-only reply times via the 19 recorded provincial capitals,
marked versus proposed transport, seasonal range and proposed-transport gain.
Select a commandery and comparative reply budget for the seasonal table and
CSV. Connectors are relationships, not routes; colours describe seats, not
surrounding land or political control. Long trips hold the chosen month's
conditions fixed and do not model courier relays or institutional delays.

Livelihoods adds six worldwide pasture-resource views, including outside
state claims: usable annual forage, feed-equivalent units, lean-season new
growth, minimum zero-loss reserves, a 90-day-buffer feed test and mapped water
proximity. These are dry-matter diagnostics, not herd or human carrying
capacities. Protein/energy quality, mobility and drinkable water supply are
not established. Selected-point CSV, full grids and methods are in the viewer.

Political reach / Coverage audit adds six dynamic worldwide views for 18
mapped actors: seasonal same-site outward/return access, longest gap, overlap,
source dependence, directional gaps and unaffiliated-site access. Compare
three source hypotheses and 1/2/4-day per-leg budgets. Missing inventories are
unscored, not uncontrolled or empty territory. Compressed grids load only when
the audit is opened (a modern browser with gzip DecompressionStream is needed).
Original de facto ownership remains available as a labelled comparison.

Political reach / Sustained presence adds eleven cereal provisioning scenarios
at 151 marked sites, including unresolved affiliations: rural priority, origin
and destination stores, finite freight slots, losses and two-bin interruptions.
Livelihoods / Seasonal circuits adds four independent resource landscapes:
one closed herd route with finite carried feed, fixed-home and best-fixed-base
controls, and mapped-water proximity sensitivity. These do not predict actual
garrisons, camps, nutrition, human populations or political control. The viewer
includes seasonal tables, actual land-path insets, CSVs, full ledgers and sources.
Landscape tests compare local and regional extents while retaining local bases,
the daily grazing footprint and travel budget. Regional controls inspect every
connected fine cell. Origin storage and collection sensitivities remain explicit
scenarios under the same dispatch rule, not measured ancient institutional power.

Settlements and supply-supported reach share one conserved local cereal budget.
The existing two modes compare food-capped civilian/cohort allocations against
a transport-matched unconstrained reference and explicit legacy views. Source
availability changes reach; no population-to-power multiplier or validated
sovereignty is inferred. Three field-work scenarios now cap grain by annual
and reaping work of one reference workforce, keeping rural meals fixed. Other
foods, complete household/draft labour and water volumes remain unbalanced.

Earth calibration evidence adds the component ledger and first independent
manual-harvest benchmark, reached from the hub. Its modern fit does not change
AD200 defaults. The full ledger, benchmark plan, source identities and all
held-out results are included; raw survey downloads require the repository
fetcher and are not needed to browse.

Population adds six census-allocation and walking-access maps. Choose a total
population and settlement pattern; local support caps are enforced and excess
people remain explicitly unallocated. Province CSVs reflect the current choices.
See reports/ITERATION_20261023.md. The launcher prints the folder it serves and
the loaded Whittaker coverage. It does not automatically download Git updates.
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    # Historical yield evidence is served from the normal hub and travels offline.
    yield_files = [ROOT/'reports/HISTORICAL_WHEAT_20261105.md', *sorted((ROOT/'calibration/low_input_yields_20261105').glob('*.json'))]
    files = [ROOT/'reports/EARTH_COMPONENT_CALIBRATION_20261105.md', *sorted((ROOT/'calibration/earth_components_20261105').glob('*.json')), ROOT/'reports/SETTLEMENT_LABOUR_20261105.md', ROOT/'research_notes/settlement_labour_20261105.json', ROOT/'data/settlement_labour_model.json', ROOT/'output/settlement_labour_20261105/fieldwork_settlement_reach.png', *sorted((ROOT/'output/settlement_labour_20261105').glob('*/field_support.npz')), ROOT/'output/settlement_integration_20261104/settlement_reach_comparison.png', ROOT/'reports/SETTLEMENT_INTEGRATION_20261104.md', ROOT/'research_notes/settlement_integration_20261104.json', ROOT/'data/settlement_integration_model.json', ROOT/'atlases/index.html', ROOT/'atlases/release.json', ROOT/'reports/PRESENCE_MOBILITY_20261104.md', ROOT/'reports/PRESENCE_MOBILITY_SCALE_20261104.md',
             ROOT/'research_notes/presence_mobility_scale_20261104.json',
             ROOT/'data/presence_mobility_model.json', ROOT/'research_notes/presence_mobility_20261104.json',
             ROOT/'reports/WORLD_COVERAGE_20261104.md', ROOT/'reports/PASTURE_RESOURCES_20261104.md',
             ROOT/'reports/WORLDWIDE_PROVISIONING_SCOPE_20261104.md', ROOT/'reports/ADMINISTRATIVE_HIERARCHY_20261104.md', ROOT/'reports/IMPERIAL_ACCESS_20261104.md',
             ROOT/'reports/CONTROL_SETTLEMENT_PROPOSALS_20261104.md', ROOT/'reports/THREE_FIT_20261022.md',
             ROOT/'reports/WHITTAKER_TARGETS_20261022.md', ROOT/'docs/BIOMES.md',
             ROOT/'reports/HARVEST_MIGRATION_20261022.md', ROOT/'reports/ITERATION_20261022.md',
             ROOT/'reports/CONTINUE_20261022.md', ROOT/'data/biome_target_crosswalk.json',
             ROOT/'data/whittaker_coverage.json',
             ROOT/'reports/ITERATION_20261023.md', ROOT/'data/population_model.json',
             ROOT/'reports/CLIMATE_PHYSICS_20261023.md',
             ROOT/'reports/RAINFALL_ACCURACY_20261023.md',
             ROOT/'reports/JOINT_INPUTS_20261026.md', ROOT/'reports/MOISTURE_SOURCES_20261026.md',
             ROOT/'reports/COLUMN_SHEAR_20261026.md', ROOT/'reports/SURFACE_MOMENTUM_20261026.md',
             ROOT/'reports/MOMENTUM_BALANCE_20261026.md',
             ROOT/'reports/VAPOR_FLUX_20261026.md',
             ROOT/'reports/FLUX_COLUMN_WIND_20261026.md',
             ROOT/'reports/EARTH_CALENDAR_20261026.md',
             ROOT/'reports/CIRCULATION_20261026.md',
             ROOT/'reports/THERMAL_WIND_20261026.md',
             ROOT/'reports/COLUMN_MASS_20261026.md',
             ROOT/'reports/TWO_LAYER_20261026.md',
             ROOT/'reports/MASS_TRACER_20261026.md',
             ROOT/'reports/HUMIDITY_GATE_20261026.md',
             ROOT/'reports/SHARED_WIND_20261026.md',
             ROOT/'reports/STORM_PATH_20261026.md',
             ROOT/'reports/TWO_RESERVOIR_20261026.md',
             ROOT/'reports/RESERVOIR_RAIN_20261026.md',
             ROOT/'reports/RESERVOIR_CLOUDS_20261026.md',
             ROOT/'reports/PRESSURE_COLUMN_20261026.md',
             ROOT/'reports/VERTICAL_REFERENCE_20261026.md',
             ROOT/'reports/RESERVOIR_BACKEND_20261026.md',
             ROOT/'reports/INDEPENDENT_WATER_20261026.md',
             ROOT/'reports/PARCEL_ASCENT_20261026.md',
             ROOT/'reports/COLUMN_RAIN_20261027.md',
             ROOT/'reports/PNW_TRANSPORT_20261027.md',
             ROOT/'reports/WESTERLY_FIT_20261027.md',
             ROOT/'reports/PNW_VERTICAL_20261027.md',
             ROOT/'reports/ENVIRONMENTAL_PARTITION_20261027.md',
             ROOT/'reports/ENVIRONMENTAL_REFERENCE_20261027.md',
             ROOT/'reports/COLUMN_DRYING_20261027.md',
             ROOT/'reports/JOINT_RAIN_20261027.md',
             ROOT/'reports/GLOBAL_RAIN_20261028.md',
             ROOT/'reports/WIND_INTERACTION_20261028.md',
             ROOT/'reports/DRYING_ABLATION_20261028.md',
             ROOT/'reports/GLOBAL_JOINT_20261028.md',
             ROOT/'reports/OCEAN_PROFILE_20261028.md',
             ROOT/'reports/RAINFALL_RECOVERY_PLAN_20261028.md',
             ROOT/'reports/TRANSPORT_DIAGNOSIS_20261028.md',
             ROOT/'reports/THERMAL_LAYER_PROTOTYPE_20261028.md',
             ROOT/'reports/THERMAL_WIND_PILOT_20261028.md',
             ROOT/'reports/SEPARATED_THERMAL_20261028.md',
             ROOT/'reports/DIVERGENT_THERMAL_20261028.md',
             ROOT/'reports/BAROCLINIC_MODE_20261028.md',
             ROOT/'reports/REGIONAL_BAROCLINIC_20261028.md',
             ROOT/'reports/REGIONAL_MODE_TRACER_20261028.md',
             ROOT/'reports/LATENT_HEATING_20261028.md',
             ROOT/'reports/FIRST_MODE_HEATING_20261028.md',
             ROOT/'reports/MOIST_ENTHALPY_20261028.md',
             ROOT/'reports/ENERGY_TRANSPORT_20261028.md',
             ROOT/'reports/MOIST_COMPOSITION_20261028.md',
             ROOT/'reports/VERTICAL_STATE_20261028.md',
             ROOT/'reports/HYDROSTATIC_FEEDBACK_20261028.md',
             ROOT/'reports/MULTILEVEL_TRANSPORT_20261028.md',
             ROOT/'reports/MULTILEVEL_MOIST_20261028.md',
             ROOT/'reports/STABILITY_REFERENCE_20261028.md',
             ROOT/'reports/CELL_THERMAL_20261028.md',
             ROOT/'reports/SUBLAYER_PHASE_20261029.md',
             ROOT/'reports/PRESSURE_MOIST_20261029.md',
             ROOT/'reports/PARCEL_STABILITY_20261029.md',
             ROOT/'reports/CONVECTIVE_ADJUSTMENT_20261029.md',
             ROOT/'reports/PRESSURE_INPUT_PILOT_20261029.md',
             ROOT/'reports/PRESSURE_BOUNDARY_PILOT_20261029.md',
             ROOT/'reports/PRESSURE_MOMENTUM_20261029.md',
             ROOT/'reports/RIGID_LID_20261029.md',
             ROOT/'reports/RIGID_LID_FIRST_ATTEMPT_20261029.md',
             ROOT/'reports/OPEN_MEAN_20261029.md',
             ROOT/'reports/SURFACE_FORCING_20261029.md',
             ROOT/'reports/SURFACE_COUPLING_DECLARATION_20261029.md',
             ROOT/'reports/COLUMN_FORCING_INTERFACE_20261029.md',
             ROOT/'reports/SURFACE_SPINUP_20261029.md',
             ROOT/'reports/REGIONAL_RAINFALL_REFERENCE_20261029.md',
             ROOT/'reports/MONTHLY_WATER_PROGRESS_20261029.md',
             ROOT/'reports/TERRAIN_GEOMETRY_20261029.md',
             ROOT/'reports/TERRAIN_DRY_20261029.md',
             ROOT/'reports/TERRAIN_ADVECTIVE_20261029.md',
             ROOT/'reports/REGIONAL_RAINFALL_RESULTS_20261029.md',
             ROOT/'reports/CONVECTION_CAP_20261029.md',
             ROOT/'reports/REGIONAL_RAINFALL_BENCHMARK_DECLARATION_20261029.md',
             ROOT/'reports/CONVECTION_LIMIT_20261029.md',
             ROOT/'reports/LOWER_CELL_RESOLUTION_20261029.md',
             ROOT/'reports/EXTENDED_SURFACE_SPINUP_20261029.md',
             ROOT/'reports/EXTENDED_SURFACE_SPINUP_DECLARATION_20261029.md',
             ROOT/'reports/PRESSURE_GRID_REMAP_20261029.md',
             ROOT/'reports/PRESSURE_GRID_REMAP_DECLARATION_20261029.md',
             ROOT/'reports/SHARED_TRANSPORT_20261029.md',
             ROOT/'reports/SHARED_TRANSPORT_DECLARATION_20261029.md',
             ROOT/'reports/PHASE_BACKEND_20261029.md',
             ROOT/'reports/PHASE_BACKEND_DECLARATION_20261029.md',
             ROOT/'reports/BOUNDARY_RH_20261028.md', ROOT/'reports/HUMIDITY_PROCESS_NOTES_20261028.md',
             ROOT/'docs/FORAGING_MODELS.md', ROOT/'data/foraging_model.json',
             ROOT/'reports/FORAGING_20261027.md',
             ROOT/'reports/PHYSICS_GAPS_20261030.md',
             ROOT/'reports/EARTH_CORRECTION_20261030.md',
             ROOT/'reports/ATLAS_R40_20261031.md',
             ROOT/'reports/R41_20261101.md', ROOT/'reports/R42_20261101.md',
             ROOT/'reports/RAIN_PROCESSES_20261102.md',
             ROOT/'output/r42_rain_diagnosis_20261102/seasonal_moisture_budget.png',
             ROOT/'output/descent_continuity_20261102/monthly_rain_comparison.png',
             ROOT/'reports/FORAGING_EARTH_20261031.md',
             ROOT/'reports/POLITY_SEASONS_20261031.md',
             ROOT/'reports/LANGUAGE_AREAS_20261101.md',
             ROOT/'output/foraging_20261027/foraging_comparison.png',
             ROOT/'output/foraging_20261027/biomes.csv',
             ROOT/'reports/CONSTRAINED_BLEND_R39_20261025.md', ROOT/'reports/R39_WORLD_TRANSFER_20261026.md',
             ROOT/'reports/SEASONAL_CYCLE_20261026.md',
             ROOT/'output/constrained_blend_20261025/rainfall_changes.png',
             ROOT/'output/r39_world_audit/audit_results.png',
             ROOT/'output/seasonal_cycle_20261026_verified/annual_repeatability.png',
             ROOT/'output/seasonal_cycle_20261026_verified/rainfall_initialization.png',
             ROOT/'scripts/serve_atlases.py', ROOT/'scripts/read_coverage_grid.py', ROOT/'start_atlases.command', ROOT/'start_atlases.bat']
    files += [ROOT/'reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md',
              ROOT/'reports/SETTLEMENT_CONTROL_DATA_QUEUE_20261110.md',
              ROOT/'reports/SETTLEMENT_LOCATIONS_20261110.md',
              ROOT/'reports/figures/settlement_locations_20261110.png',
              ROOT/'calibration/settlement_locations_20261110/plan.json']
    files += sorted(p for p in (ROOT/'calibration/settlement_locations_20261110/data_queue').glob('*') if p.is_file())
    files += [ROOT/'reports/SETTLEMENT_INTENSITY_20261110.md',ROOT/'reports/VIDARBHA_PREPARATION_20261110.md',
              ROOT/'reports/figures/settlement_intensity_maps_20261110.png',ROOT/'reports/figures/settlement_intensity_tradeoffs_20261110.png',
              ROOT/'calibration/settlement_intensity_20261110/plan.json',ROOT/'calibration/vidarbha_preparation_20261110/plan.json']
    files += [ROOT/'reports/ROMAN_RURAL_PREPARATION_20261110.md',ROOT/'reports/SETTLEMENT_ROLE_CONTRACT_20261110.md',
              ROOT/'calibration/roman_rural_preparation_20261110/plan.json',
              ROOT/'calibration/roman_rural_preparation_20261110/metadata_sources.json']
    files += [ROOT/'reports/ROMAN_RURAL_ROLES_20261110.md',
              ROOT/'calibration/roman_rural_roles_20261110/crosswalk.json',
              ROOT/'calibration/roman_rural_roles_20261110/semantic_sources.json']
    files += [ROOT/'reports/ROMAN_RURAL_COORDINATES_20261110.md',
              ROOT/'reports/figures/roman_rural_coordinates_20261110.png',
              ROOT/'calibration/roman_rural_coordinates_20261110/plan.json',
              ROOT/'calibration/roman_rural_coordinates_20261110/plan_v1.json']
    files += [ROOT/'reports/SETTLEMENT_HISTORY_BOUNDARY_20261111.md',
              ROOT/'reports/SETTLEMENT_PHASE_EVIDENCE_20261111.md',
              ROOT/'reports/figures/settlement_history_boundary_20261111.png',
              ROOT/'calibration/settlement_history_boundary_20261111/plan.json',
              ROOT/'calibration/settlement_phase_evidence_20261111/plan.json',
              ROOT/'calibration/settlement_phase_evidence_20261111/semantic_sources.json']
    files += [ROOT/'reports/SETTLEMENT_ROLE_CONTRAST_20261111.md',
              ROOT/'reports/figures/settlement_role_contrast_20261111.png',
              ROOT/'calibration/settlement_role_contrast_20261111/plan.json']
    files += [ROOT/'reports/SETTLEMENT_SERVICE_DEMAND_20261111.md',
              ROOT/'reports/figures/settlement_service_demand_scores_20261111.png',
              ROOT/'reports/figures/settlement_service_demand_maps_20261111.png',
              ROOT/'calibration/settlement_service_demand_20261111/plan.json']
    files += [ROOT/'reports/SETTLEMENT_SERVICE_CONTROLS_20261111.md',
              ROOT/'reports/figures/settlement_service_controls_20261111.png',
              ROOT/'calibration/settlement_service_controls_20261111/plan.json']
    files += [ROOT/'reports/SETTLEMENT_ROLE_COMPOSITION_20261111.md',
              ROOT/'reports/figures/settlement_role_composition_20261111.png',
              ROOT/'calibration/settlement_role_composition_20261111/plan.json',
              ROOT/'calibration/settlement_role_composition_20261111/semantic_sources.json']
    files += [ROOT/'reports/SETTLEMENT_SERVICE_CAPACITY_20261111.md',
              ROOT/'reports/figures/settlement_service_capacity_20261111.png',
              ROOT/'calibration/settlement_service_capacity_20261111/plan.json']
    files += [ROOT/'reports/INSTITUTION_EVIDENCE_20261111.md',
              ROOT/'reports/figures/institution_provider_audit_20261111.png',
              ROOT/'calibration/institution_evidence_20261111/plan.json',
              ROOT/'calibration/institution_evidence_20261111/sources.json']
    files += [ROOT/'reports/INSTITUTION_SCOPE_20261111.md',
              ROOT/'calibration/institution_scope_20261111/plan.json',
              ROOT/'calibration/institution_scope_20261111/sources.json']
    files += [ROOT/'reports/VIDARBHA_SURVEY_20261111.md',
              ROOT/'reports/SETTLEMENT_VIDARBHA_TRANSFER_20261111.md',
              ROOT/'reports/figures/settlement_vidarbha_transfer_20261111.png',
              ROOT/'reports/figures/settlement_vidarbha_geography_20261111.png',
              ROOT/'calibration/vidarbha_survey_20261111/plan.json',
              ROOT/'calibration/vidarbha_survey_20261111/methods.json',
              ROOT/'calibration/settlement_vidarbha_transfer_20261111/plan.json']
    files += [ROOT/'reports/SETTLEMENT_COUNTS_20261111.md',
              ROOT/'reports/figures/settlement_counts_20261111.png',
              ROOT/'reports/figures/settlement_population_coverage_20261111.png',
              ROOT/'calibration/settlement_counts_20261111/plan.json',
              ROOT/'calibration/settlement_counts_20261111/multiplicity_correction.json',
              ROOT/'calibration/settlement_counts_20261111/coverage_domain.json']
    files += [ROOT/'reports/EARTH_POPULATION_EXTENSION_20261111.md',
              ROOT/'reports/figures/population_nodata_correction_20261111.png',
              ROOT/'reports/figures/population_extension_han_20261111.png',
              ROOT/'calibration/earth_population_extension_20261111/plan.json',
              ROOT/'calibration/earth_population_extension_20261111/nodata_correction.json']
    if (ROOT/'output/settlement_joint_locations_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_JOINT_LOCATIONS_20261112.md',
                  ROOT/'reports/figures/settlement_joint_maps_20261112.png',
                  ROOT/'reports/figures/settlement_joint_tradeoffs_20261112.png',
                  ROOT/'calibration/settlement_joint_locations_20261111/plan.json']
    if (ROOT/'output/settlement_residents_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_RESIDENTS_20261112.md']
    if (ROOT/'output/settlement_feedback_20261112/atlas_publication.json').exists():
        files += [ROOT/'reports/SETTLEMENT_FEEDBACK_20261112.md', ROOT/'calibration/settlement_feedback_20261112/plan.json',
                  ROOT/'reports/figures/settlement_feedback_maps_20261112.png', ROOT/'reports/figures/settlement_feedback_scenarios_20261112.png']
    if (ROOT/'output/settlement_size_evidence_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_SIZE_EVIDENCE_20261112.md',
                  ROOT/'reports/figures/settlement_size_evidence_20261112.png']
        files += list((ROOT/'calibration/settlement_size_evidence_20261112').glob('*.json'))
        files += list((ROOT/'data/source/roman_housing_2023').glob('*'))
        files += [ROOT/'output/settlement_size_evidence_20261112/replay.json']
    if (ROOT/'output/settlement_feedback_20261112/scan_check/replay.json').exists():
        files += [ROOT/'output/settlement_feedback_20261112/scan_check/results.json',
                  ROOT/'output/settlement_feedback_20261112/scan_check/replay.json']
    if (ROOT/'output/settlement_housing_diagnostic_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_HOUSING_DIAGNOSTIC_20261112.md',
                  ROOT/'reports/figures/settlement_housing_diagnostic_20261112.png',
                  ROOT/'calibration/settlement_housing_diagnostic_20261112/plan.json']
    if (ROOT/'output/settlement_monthly_work_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_MONTHLY_WORK_20261112.md',
                  ROOT/'reports/figures/settlement_monthly_work_20261112.png',
                  ROOT/'calibration/settlement_monthly_work_20261112/plan.json']
    if (ROOT/'output/settlement_dispatch_20261112/atlas_publication.json').exists():
        files += [ROOT/'reports/SETTLEMENT_DISPATCH_20261112.md',
                  ROOT/'calibration/settlement_dispatch_20261112/plan.json']
        files += list((ROOT/'reports/figures').glob('settlement_dispatch_*_20261112.png'))
    if (ROOT/'output/settlement_dispatch_search_20261112/review.json').exists():
        files += [ROOT/'reports/SETTLEMENT_DISPATCH_SEARCH_20261112.md',
                  ROOT/'calibration/settlement_dispatch_search_20261112/plan.json',
                  ROOT/'calibration/settlement_dispatch_seeded_20261112/plan.json']
    files += sorted(p for p in (ROOT/'atlases/climate_accuracy').rglob('*') if p.is_file())
    files += yield_files
    files += sorted(p for p in (ROOT/'atlases/earth_evidence').rglob('*') if p.is_file())
    evidence = ROOT/'output/three_fit_20261022'
    for name in ['search_comparison.png', 'biome_comparison.png', 'search_review.json', 'search_evaluations.json',
                 'search_review.csv', 'atlas_validation.json', 'publication.json', 'settlement_comparison.png', 'harvest_tests.log',
                 'recovery_probe.json', 'earth_numerics_check.json', 'browser/browser_checks.json',
                 'fresh_checkout.json', 'fresh_browser/browser_checks.json', 'javascript_tests.log']:
        file = evidence/name
        if file.exists():
            files.append(file)
    coverage = ROOT/'output/whittaker_coverage_20261022'
    for name in ['review.json','protocol.json','selected_params.json','publication_params.json','native_choice.json','native_metrics.json','publication.json','coverage_comparison.png',
                 'atlas_validation.json','field_diagnostics.json','fresh_checkout.json',
                 'browser/browser_checks.json','browser/hub_checks.json',
                 'fresh_browser/browser_checks.json','fresh_browser/hub_checks.json']:
        if (coverage/name).is_file():files.append(coverage/name)
    files += sorted((ROOT/'calibration/three_fit_20261022').glob('**/*.json'))
    iteration=ROOT/'output/iteration_20261023'
    for name in ['atlas_validation.json','atlas_browser.json','selector_browser.json','population_maps.png','population_browser/browser_checks.json',
                 'fresh_browser/browser_checks.json','fresh_checkout.json','current_whittaker.json',
                 'core_assets.json','tests.json','hub_checks.json']:
        if (iteration/name).is_file():files.append(iteration/name)
    physics = ROOT/'output/climate_physics_20261023'
    excluded = {'checkpoints', 'fresh_snapshot', 'previous_atlases', 'previous_atlas'}
    if physics.exists():
        files += sorted(p for p in physics.rglob('*') if p.is_file() and p.suffix in {'.json', '.png'}
                        and not excluded.intersection(p.relative_to(physics).parts))
    calibration = ROOT/'calibration/climate_physics_20261023'
    if calibration.exists():
        files += sorted(p for p in calibration.rglob('*') if p.is_file() and p.suffix in {'.json', '.jsonl'})
    summaries = {}
    for name in NAMES:
        directory = ROOT/'atlases'/name
        summary = json.loads((directory/'summary.json').read_text())
        assert summary['observed_numerics']['all_checks_passed'], name
        summaries[name] = summary
        files += sorted(f for f in directory.rglob('*') if f.is_file())
    files += [ROOT/'reports/LAKES_DELTAS_20261108.md', ROOT/'reports/R44_RECONSTRUCTION_20261109.md',
              ROOT/'reports/CEREAL_DELTA_IRRIGATION_20261109.md', ROOT/'reports/figures/lakes_through_v22.png',
              ROOT/'reports/figures/delta_candidates.png']
    files = page_dependencies(files)
    manifest = dict(atlases=summaries, sha256={
        str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in files:
            archive.write(file, str(file.relative_to(ROOT)))
        archive.writestr('README.txt', INSTRUCTIONS)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(args.out) as archive:
        assert archive.testzip() is None
    result = dict(file=str(args.out), bytes=args.out.stat().st_size,
                  sha256=hashlib.sha256(args.out.read_bytes()).hexdigest(),
                  files=len(files)+2, integrity='passed')
    args.out.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
