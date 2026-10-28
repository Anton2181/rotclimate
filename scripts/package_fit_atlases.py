"""Package the three active atlas variants with a local HTTP entry page.

Data remain external files: open the extracted bundle through an HTTP server,
not file://. The bundle includes the report, biome methods and source license.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['free_fit', 'earth_fit', 'whittaker_fit']
INSTRUCTIONS = '''Rotclimate: three climate fits

Extract this whole archive, then double-click start_atlases.command (macOS)
or start_atlases.bat (Windows), with Python 3 installed. Or run:

    python3 scripts/serve_atlases.py

The launcher opens your browser. Keep its terminal window open while browsing.

The free and Earth fits optimize the seasonal target zones. The separate
Whittaker fit optimizes the proposed strict target-to-biome crosswalk with
an explicit penalty for land outside the original Whittaker diagram. All
three classify the mean climate over surroundings layouts 1, 2 and 3.
The report explains the scores, crosswalk assumptions and numerical checks.
These are simulated potential climates, not observed vegetation maps.
The hub's Climate accuracy and joint fit page includes measured Earth errors
and rainfall-source maps. It distinguishes latest Earth r39 skill from the
published r38 world; it is not measured accuracy of the fantasy geography.
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
    files = [ROOT/'atlases/index.html', ROOT/'reports/THREE_FIT_20261022.md',
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
             ROOT/'reports/BOUNDARY_RH_20261028.md', ROOT/'reports/HUMIDITY_PROCESS_NOTES_20261028.md',
             ROOT/'docs/FORAGING_MODELS.md', ROOT/'data/foraging_model.json',
             ROOT/'reports/FORAGING_20261027.md',
             ROOT/'output/foraging_20261027/foraging_comparison.png',
             ROOT/'output/foraging_20261027/biomes.csv',
             ROOT/'reports/CONSTRAINED_BLEND_R39_20261025.md', ROOT/'reports/R39_WORLD_TRANSFER_20261026.md',
             ROOT/'reports/SEASONAL_CYCLE_20261026.md',
             ROOT/'output/constrained_blend_20261025/rainfall_changes.png',
             ROOT/'output/r39_world_audit/audit_results.png',
             ROOT/'output/seasonal_cycle_20261026_verified/annual_repeatability.png',
             ROOT/'output/seasonal_cycle_20261026_verified/rainfall_initialization.png',
             ROOT/'scripts/serve_atlases.py', ROOT/'start_atlases.command', ROOT/'start_atlases.bat']
    files += sorted(p for p in (ROOT/'atlases/climate_accuracy').rglob('*') if p.is_file())
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
