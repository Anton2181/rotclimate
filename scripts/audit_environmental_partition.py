"""Cached native environmental-profile comparison; no climate runs or fitting."""
from pathlib import Path
import argparse
import importlib.metadata
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import v10_forcing_audit as reader
from rotclimate.column_thermodynamics import (CP, G, RD, TROPOPAUSE_K,
    integrate_saturation_profile, specific_saturation)
from audit_pnw_vertical import acquire_air, partial_integrals, summarize_arrays
from circulation_reference import acquire, column_targets
from earth_calendar import MONTH_DAYS
from local_benchmark_protocol import file_hash, freeze, identity, write_json

LEVELS = [925, 850, 700, 600, 500, 400, 300]
PROFILES = {'moist': {'profile': 'moist', 'lapse_k_km': 6.0},
    'environmental_6': {'profile': 'lapse', 'lapse_k_km': 6.0},
    'environmental_6.5': {'profile': 'lapse', 'lapse_k_km': 6.5}}
THRESHOLDS = dict(mean_regional_thermal_mae_ratio_max=.95,
    regional_thermal_mae_additive_max_k=.5, mean_regional_qsat_shape_mae_ratio_max=1.,
    regional_qsat_shape_mae_ratio_max=1.10, regional_qsat_shape_mae_additive_max=.005)


def verified_payload(path, url, manifest):
    row = manifest.get(path.name, {})
    if (row.get('url') != url or row.get('sha256') != file_hash(path)
            or row.get('bytes') != path.stat().st_size):
        raise ValueError('Changed reference provenance: '+str(path))
    return path.read_text(), row


def acquire_legacy_air(region):
    """Only the exact pre-existing V10 air subset and verified metadata."""
    cache = ROOT/'data/v10_atmosphere'; manifest_path = cache/'downloads.json'
    manifest = json.loads(manifest_path.read_text()); sources = [manifest_path]; provenance = {}
    base = reader.BASE+'air.mon.1981-2010.ltm.nc'
    def payload(name, url):
        path = cache/name; content, row = verified_payload(path, url, manifest)
        sources.append(path); provenance[str(path.relative_to(ROOT))] = row
        return content
    units = reader.metadata(payload('air.das', base+'.das'), 'air'); pieces = []
    for index, box in enumerate(reader.BOXES[region]):
        y0, y1, x0, x1 = box
        query = f'air[0:1:11][0:1:16][{y0}:1:{y1}][{x0}:1:{x1}]'
        field = reader.parse_ascii(payload(f'air_{region}_{index}.ascii', base+'.ascii?'+query), 'air')
        reader.validate_subset(field, box, reader.VARIABLES['air'])
        pieces.append(reader.normalize(field, 'air', units))
    first = pieces[0]
    for other in pieces[1:]:
        if any(not np.array_equal(getattr(first, axis), getattr(other, axis))
                for axis in ('pressure_hpa', 'latitude', 'time')):
            raise ValueError('Split air axes differ')
    longitude = np.concatenate([field.longitude for field in pieces]); order = np.argsort(longitude)
    return reader.Field(np.concatenate([f.values for f in pieces], axis=-1)[..., order],
        first.pressure_hpa, first.latitude, longitude[order], first.time), sources, provenance


def validate_matched_fields(air, humidity):
    for axis in ('latitude', 'longitude', 'time'):
        if not np.array_equal(getattr(air, axis), getattr(humidity, axis)):
            raise ValueError('Thermal/humidity axes differ: '+axis)
    for field in (air, humidity):
        if (field.values.shape != (12, len(field.pressure_hpa), len(field.latitude), len(field.longitude))
                or not np.isfinite(field.values).all()
                or any(level not in field.pressure_hpa for level in LEVELS)):
            raise ValueError('Invalid reference axes/values or missing hPa nodes')


def verify_archive(region, spec, humidity, references):
    directory = ROOT/spec['directory']; arrays = directory/(spec['stem']+'.npz')
    record_path = directory/(spec['stem']+'.json'); protocol_path = directory/'protocol.json'
    record = json.loads(record_path.read_text()); prior = json.loads(protocol_path.read_text())
    if (record.get('status') != 'passed' or record.get('numerics', {}).get('all_checks_passed') is not True
            or file_hash(arrays) != record.get('arrays_sha256') or identity(prior) != record.get('identity')):
        raise ValueError('Unverified independent native archive: '+region)
    pnw = region == 'pacific_nw'; circulation = record['circulation'] if pnw else record
    if circulation['original_month'] != list(range(12)):
        raise ValueError('Archive is not in geographic January-December order')
    # The independent archive keeps its original code epoch. Compare raw references only.
    for name, row in references.items():
        filename = Path(name).name
        if filename.endswith('.das') or '_'+region+'_' in filename:
            if prior['sources'].get(name) != row['sha256'] or prior.get('references', {}).get(name) != row:
                raise ValueError('Independent archive raw reference differs: '+name)
    with np.load(arrays, allow_pickle=False) as saved:
        prefix = 'circulation_' if pnw else ''
        mask = saved[prefix+'mask_ocean'].copy()
        area = saved['circulation_area' if pnw else 'native_area_km2'].copy()
        days = MONTH_DAYS.copy() if pnw else saved['month_days'].copy()
        targets = {key: saved[prefix+'reference_'+key].copy() for key in ('925', '850', 'q925_300')}
        water = None if pnw else saved['partial_water_kgm2'].copy()
        if not pnw and (not np.array_equal(saved['reference_latitude'], humidity.latitude)
                or not np.array_equal(saved['reference_longitude'], humidity.longitude)
                or not np.array_equal(saved['original_month'], np.arange(12))):
            raise ValueError('Independent native coordinate maps changed')
    count = len(humidity.latitude)*len(humidity.longitude)
    if (mask.dtype != np.dtype(bool) or mask.shape != (count,) or area.shape != (count,)
            or int(mask.sum()) != spec['native_ocean_cells'] or not np.isfinite(area).all()
            or (area[mask] <= 0).any() or not np.array_equal(days, MONTH_DAYS)):
        raise ValueError('Changed fixed native ocean geometry or Gregorian months')
    certificate = (circulation['scores'] if pnw else record['scores']['moisture'])['q925_300']['ocean']
    if certificate['native_cells'] != int(mask.sum()) or certificate['area_km2'] != float(area[mask].sum()):
        raise ValueError('Changed archive native footprint certificate')
    return dict(mask=mask, full_area=area, area=area[mask], days=days, targets=targets, water=water), [arrays, record_path, protocol_path]


def withheld_temperature_mae(predicted, observed, pressure_hpa=LEVELS):
    """Pressure-trapezoid MAE on withheld 850–300 hPa; the anchor has no score."""
    predicted, observed = np.asarray(predicted, float), np.asarray(observed, float)
    p = np.asarray(pressure_hpa, float)
    if (not np.array_equal(p, LEVELS) or predicted.shape != observed.shape or predicted.ndim != 3
            or predicted.shape[:2] != (12, 7) or not np.isfinite(predicted).all()
            or not np.isfinite(observed).all()):
        raise ValueError('Need matched monthly seven-node temperature arrays and hPa levels')
    error = np.abs(predicted[:, 1:]-observed[:, 1:])
    return np.trapezoid(error[:, ::-1], x=p[1:][::-1]*100, axis=1)/55000.


def diagnose(plan, air, humidity, geometry):
    mask, area, days = (geometry[key] for key in ('mask', 'area', 'days'))
    p = np.asarray(LEVELS)[None, :, None]*100
    selected = lambda field: field.values[:, [list(field.pressure_hpa).index(v) for v in LEVELS]].reshape(12, 7, -1)[:, :, mask]
    temperature = selected(air)+273.15; ratio = selected(humidity); q = ratio/(1+ratio)
    qsat = specific_saturation(temperature, p)
    actual, capacity = partial_integrals(q, LEVELS), partial_integrals(qsat, LEVELS)
    theta = lambda t: t*(plan['potential_temperature_reference_pa']/p)**(RD/CP)
    observed = dict(temperature_c=temperature-273.15, potential_temperature_k=theta(temperature),
        specific_humidity_kg_kg=q, specific_saturation_kg_kg=qsat,
        specific_humidity_saturation_fraction=q/qsat,
        **{'actual_'+k: v for k, v in actual.items()}, **{'saturation_'+k: v for k, v in capacity.items()})
    data = dict(observed=summarize_arrays(observed, area, days), profiles={})
    raw = {'observed_'+key: value for key, value in observed.items()}
    ps = np.full((12, len(area)), 92500.)
    edges = np.broadcast_to(np.asarray(LEVELS)[:, None, None]*100, (7,)+ps.shape)
    for name, spec in plan['profiles'].items():
        _, interfaces = integrate_saturation_profile(temperature[:, 0]-273.15, ps, edges,
            **spec, steps=plan['profile_integration_steps_per_interval'])
        predicted = np.moveaxis(interfaces, 0, 1); saturation = specific_saturation(predicted, p)
        integrals = partial_integrals(saturation, LEVELS)
        shape_error = np.abs(integrals['upper_lower_mean_q_ratio']-capacity['upper_lower_mean_q_ratio'])
        arrays = dict(temperature_c=predicted-273.15, potential_temperature_k=theta(predicted),
            specific_saturation_kg_kg=saturation, **{'saturation_'+k: v for k, v in integrals.items()},
            withheld_temperature_mae_k=withheld_temperature_mae(predicted, temperature),
            qsat_shape_absolute_error=shape_error,
            diagnostic_actual_q_shape_absolute_error=np.abs(integrals['upper_lower_mean_q_ratio']-actual['upper_lower_mean_q_ratio']),
            diagnostic_capacity_minus_actual_water_mm=integrals['total_mm']-actual['total_mm'])
        summary = summarize_arrays(arrays, area, days)
        data['profiles'][name] = dict(summary, thermal_mae_k=summary['seasons']['annual']['withheld_temperature_mae_k'],
            qsat_shape_mae=summary['seasons']['annual']['qsat_shape_absolute_error'],
            observed_anchor='Each native monthly observed 925 hPa temperature only; no humidity fit',
            minimum_temperature_k=float(predicted.min()), nodes_at_prescribed_temperature_floor=int(np.sum(predicted <= TROPOPAUSE_K)))
        raw.update({name+'_'+key: value for key, value in arrays.items()})
    return data, raw


def qualify(regions, thresholds):
    """Independent predeclared reviews, with every regional and aggregate failure."""
    reviews = {}
    for name in ('environmental_6', 'environmental_6.5'):
        failures = []; checks = {}; baseline = {}; candidate = {}
        for metric in ('thermal_mae_k', 'qsat_shape_mae'):
            baseline[metric] = float(np.mean([r['profiles']['moist'][metric] for r in regions.values()]))
            candidate[metric] = float(np.mean([r['profiles'][name][metric] for r in regions.values()]))
        for region, row in regions.items():
            old, new = row['profiles']['moist'], row['profiles'][name]
            thermal_limit = old['thermal_mae_k']+thresholds['regional_thermal_mae_additive_max_k']
            shape_limit = old['qsat_shape_mae']*thresholds['regional_qsat_shape_mae_ratio_max']+thresholds['regional_qsat_shape_mae_additive_max']
            checks[region] = dict(thermal_mae_k=new['thermal_mae_k'], thermal_limit_k=thermal_limit,
                qsat_shape_mae=new['qsat_shape_mae'], qsat_shape_limit=shape_limit)
            if new['thermal_mae_k'] > thermal_limit: failures.append(region+': regional thermal MAE protection failed')
            if new['qsat_shape_mae'] > shape_limit: failures.append(region+': regional observed-T qsat-shape protection failed')
        if candidate['thermal_mae_k'] > baseline['thermal_mae_k']*thresholds['mean_regional_thermal_mae_ratio_max']:
            failures.append('Mean-three-region thermal MAE did not improve by at least 5%')
        if candidate['qsat_shape_mae'] > baseline['qsat_shape_mae']*thresholds['mean_regional_qsat_shape_mae_ratio_max']:
            failures.append('Mean-three-region observed-T qsat-shape MAE increased')
        reviews[name] = dict(qualifies=not failures, failures=failures, mean_regional=candidate,
            moist_mean_regional=baseline, regional_checks=checks, thresholds=thresholds)
    return reviews


def plot_errors(regions, path):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5), constrained_layout=True)
    colors = ['#327f94', '#ad7951', '#9963a0']
    labels = ['Saturated moist', 'Environmental 6.0 K/km', 'Environmental 6.5 K/km']
    for column, (region, row) in enumerate(regions.items()):
        for name, color, label in zip(PROFILES, colors, labels):
            monthly = row['profiles'][name]['monthly']
            axes[0, column].plot(range(12), monthly['withheld_temperature_mae_k'], color=color, label=label, lw=2)
            axes[1, column].plot(range(12), monthly['qsat_shape_absolute_error'], color=color, label=label, lw=2)
        title = {'pacific_nw': 'Pacific Northwest', 'iberia': 'Iberia', 'california': 'California'}[region]
        axes[0, column].set_title(f'{title} · {row["geometry"]["native_ocean_cells"]} native ocean cells')
        for ax in axes[:, column]:
            ax.set(xticks=range(12), xticklabels=list('JFMAMJJASOND'), ylim=(0, None)); ax.grid(alpha=.15)
        axes[0, column].set_ylabel('Withheld 850–300 hPa T MAE (K)')
        axes[1, column].set_ylabel('qsat upper/lower ratio MAE\nversus qsat at observed T')
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle('Thermal partition · same observed 925 hPa anchor for every profile', fontsize=15)
    fig.supxlabel('True native area and Gregorian month weights; no humidity fit, climate run or profile selection. Tiny reused coarse/model-assisted samples.\n'
        'NCEP/NCAR 1981–2010 differs from the rain period; liquid saturation and prescribed 200 K floor. No environmental energy solution or reference forcing.', fontsize=8)
    fig.savefig(path, dpi=145); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/'calibration/environmental_reference_20261027/plan.json')
    parser.add_argument('--out', type=Path, default=ROOT/'output/environmental_reference_20261027')
    args = parser.parse_args(); path = args.plan.resolve(); out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()): raise ValueError('Preserve existing reference output; choose a fresh --out')
    phase = 'plan'; run_identity = None
    try:
        plan = json.loads(path.read_text())
        if (plan['profiles'] != PROFILES or plan['qualification'] != THRESHOLDS or plan['pressure_hpa'] != LEVELS
                or plan['regions'] != ['pacific_nw', 'iberia', 'california'] or plan['climate_integrations'] != 0
                or plan['physics_or_atlas_adoption'] is not False or plan['profile_integration_steps_per_interval'] != 64
                or [plan['archives'][r]['native_ocean_cells'] for r in plan['regions']] != [4, 20, 3]
                or plan['new_reference_boxes'] != {'pacific_nw': [[14, 22, 92, 102]]}):
            raise ValueError('Changed predeclared fixed-profile native reference comparison')
        phase = 'cached-acquisition'
        fields, references = acquire(ROOT, plan, fetch=False)
        sources = [path, Path(__file__), ROOT/plan['physics'], *[ROOT/p for p in plan['reference_plans']],
            ROOT/plan['pnw_air_plan'], ROOT/'data/v10_atmosphere/downloads.json',
            ROOT/'data/cache/circulation_reference_20261026/downloads.json']
        pnw_plan = json.loads((ROOT/plan['pnw_air_plan']).read_text())
        # The reused helper can copy metadata on a cache miss; prohibit any such mutation here.
        if not all((ROOT/pnw_plan['air_cache']/name).is_file()
                for name in ('downloads.json', 'air.das', 'air_pacific_nw_0.ascii')):
            raise ValueError('PNW air cache incomplete; this audit never acquires missing inputs')
        pnw_air, air_sources, air_references = acquire_air(pnw_plan, fetch=False); sources.extend(air_sources)
        air = {'pacific_nw': pnw_air}; geometry = {}
        for region in ('iberia', 'california'):
            air[region], extra, provenance = acquire_legacy_air(region)
            sources.extend(extra); air_references.update(provenance)
        for name, row in {**references, **air_references}.items():
            payload = ROOT/name
            if row.get('bytes') != payload.stat().st_size or row.get('sha256') != file_hash(payload):
                raise ValueError('Changed cached raw payload bytes/hash: '+name)
            sources.append(payload)
        phase = 'archive-verification'
        for region in plan['regions']:
            humidity = fields[region, 'shum']; validate_matched_fields(air[region], humidity)
            geometry[region], extra = verify_archive(region, plan['archives'][region], humidity, references)
            sources.extend(extra)
        # Freeze every actually imported local helper, including transitive reader dependencies.
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                local = Path(filename).resolve()
                if (local.is_relative_to(ROOT) and '.venv' not in local.relative_to(ROOT).parts
                        and local.suffix == '.py'): sources.append(local)
        run_identity = freeze(out/'protocol.json', dict(plan=plan,
            sources={str(p.relative_to(ROOT)): file_hash(p) for p in dict.fromkeys(sources)},
            references=references, air_references=air_references,
            constants=dict(G=G, RD=RD, CP=CP, temperature_floor_k=TROPOPAUSE_K),
            packages={n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'matplotlib')}))
        phase = 'matched-reference-verification'; regions = {}; arrays = {}
        for region in plan['regions']:
            g = geometry[region]; humidity = fields[region, 'shum']
            targets, water, _ = column_targets({v: fields[region, v] for v in ('uwnd', 'vwnd', 'shum', 'hgt')})
            if any(not np.array_equal(value.reshape(12, 2, -1), g['targets'][key]) for key, value in targets.items()):
                raise ValueError('Independent archived native vector targets changed: '+region)
            if g['water'] is not None and not np.array_equal(water, g['water']):
                raise ValueError('Independent archived partial-water targets changed: '+region)
            phase = 'diagnosis'
            row, raw = diagnose(plan, air[region], humidity, g)
            longitude, latitude = np.meshgrid(humidity.longitude, humidity.latitude)
            native = dict(native_flat_indices=np.flatnonzero(g['mask']), native_ocean_mask=g['mask'],
                native_full_area_km2=g['full_area'], native_area_km2=g['area'],
                native_latitude=latitude.ravel()[g['mask']], native_longitude=longitude.ravel()[g['mask']],
                month_days=g['days'], pressure_hpa=np.asarray(LEVELS))
            row['geometry'] = {key: value.tolist() for key, value in native.items()}
            row['geometry'].update(native_ocean_cells=len(g['area']), total_area_km2=float(g['area'].sum()))
            regions[region] = row; arrays.update({region+'_'+key: value for key, value in {**raw, **native}.items()})
        reviews = qualify(regions, plan['qualification']); target = out/'native_profiles.npz'
        with target.with_suffix('.tmp').open('wb') as stream: np.savez_compressed(stream, **arrays)
        target.with_suffix('.tmp').replace(target)
        phase = 'figure'; picture = out/'environmental_profiles.png'; plot_errors(regions, picture)
        for name, expected in json.loads((out/'protocol.json').read_text())['sources'].items():
            if file_hash(ROOT/name) != expected: raise ValueError('Frozen input changed during audit: '+name)
        write_json(out/'review.json', dict(complete=True, status='passed', identity=run_identity,
            climate_integrations=0, physics_or_atlas_adoption=False, regions=regions, reviews=reviews,
            arrays_sha256=file_hash(target), images_sha256={picture.name: file_hash(picture)},
            protocol_sha256=file_hash(out/'protocol.json'), limitations=plan['limitations'],
            selection='No profile ranked or selected; every predeclared outcome retained'))
        print(json.dumps(dict(status='passed', identity=run_identity, reviews=reviews,
            climate_integrations=0, output=str(out)), indent=2), flush=True)
    except Exception as error:
        write_json(out/'failure.json', dict(complete=False, status='failed', phase=phase, error=repr(error),
            identity=run_identity, plan_sha256=file_hash(path), script_sha256=file_hash(Path(__file__)),
            climate_integrations=0, physics_or_atlas_adoption=False))
        raise


if __name__ == '__main__': main()
