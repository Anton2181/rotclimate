"""Run the predeclared, frozen location comparison on the primary field survey.

Raw survey rows and matches remain in private cache; public fields contain only
model-derived data. This is a conditional known-site test, not a census fit.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha, write
from polity import earth as E, settle
from polity.settlement_locations import site_fields, fixed_count_sites
from polity.settlement_intensity import intensity_fields, adaptive_count_sites
from polity.survey_transfer import relative_ranks, capture_fraction, sphere_distance
from prepare_vidarbha_survey import load_tables, CACHE
from rotclimate.earth import forward, inverse

CONFIG = ROOT/'calibration/settlement_vidarbha_transfer_20261111'
METHODS = ROOT/'calibration/vidarbha_survey_20261111/methods.json'
DEFAULT_OUT = ROOT/'output/settlement_vidarbha_transfer_20261111'
SEEDS = [1, 7, 19, 43, 97]
OFFSETS = [('central', 0., 0.)] + [(f'{axis}{shift:+g}km', shift if axis=='x' else 0., shift if axis=='y' else 0.)
    for axis in ['x', 'y'] for shift in [-3., -1., 1., 3.]]
PARENTS = ['output/settlement_intensity_20261110/results.json',
           'output/vidarbha_preparation_20261110/audit.json',
           'output/vidarbha_survey_20261111/preparation.json',
           'output/vidarbha_survey_20261111/review.json']
SOURCES = ['output/land_people/earth/earth.npz', 'data/cache/worldclim/wc2.1_5m_elev.zip',
           'data/cache/naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson',
           'polity/earth.py', 'polity/settle.py', 'polity/settlement_locations.py',
           'polity/settlement_intensity.py', 'scripts/population_cores.py',
           'scripts/settlement_model_earth.py', 'harvest/models.py', 'rotclimate/biomes.py',
           'rotclimate/earth.py', 'polity/survey_transfer.py']


def numeric_digest(path):
    h = hashlib.sha256()
    with np.load(path) as z:
        for key in sorted(z.files):
            a = np.ascontiguousarray(z[key]); h.update(key.encode()); h.update(str(a.dtype).encode())
            h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def xyz(lat, lon):
    a, b = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(a)*np.cos(b), np.cos(a)*np.sin(b), np.sin(a)])


def prepare_inputs(out):
    from rotclimate.earth import _wc
    from population_cores import travel_distance, CORE_SETS
    from settlement_model_earth import sample_earth
    print('Building common global history and reading elevation', flush=True)
    with np.load(ROOT/'output/land_people/earth/earth.npz') as archive:
        global_fields = dict(archive)
    distance = travel_distance(global_fields, CORE_SETS['cradles + Rome'], forest_cost=2., sea_cost=1., relief_cost=1.)
    elevation = _wc('elev'); finite = np.isfinite(elevation); filled = np.nan_to_num(elevation)
    records = {}
    for cell in [3, 9]:
        print('Preparing', cell, 'km common grid', flush=True)
        g = E.grid(20.8, 78.5, 1350., 900., cell)
        lat, lon = g['lat'], g['lon']
        land = E.sample_global(finite.astype(np.uint8), lat, lon).astype(bool)
        elev = E.sample_global(filled, lat, lon, order=1)
        density, herders, covered = E.earth_people(lat, lon)
        if not covered[land].all():
            raise ValueError('Regional land outside global density coverage')
        river = E.rivers(g) & land
        water = ndi.distance_transform_edt(~river) * cell
        aridity = sample_earth(global_fields['aridity'], lat, lon)
        if not np.isfinite(aridity[land]).all():
            raise ValueError('Nonfinite regional aridity')
        d = sample_earth(distance, lat, lon)
        x = dict(g, land=land, elev=np.where(land, elev, 0.), density=density*land,
                 herders=herders*land, covered=covered, river=river, water_km=water,
                 road=np.zeros(land.shape, bool), aridity=aridity, allowed=land.copy(),
                 history800=np.exp(-d/800.), history450=np.exp(-d/450.))
        path = out/f'inputs_{cell}km.npz'; np.savez_compressed(path, **x)
        records[str(cell)] = dict(shape=list(land.shape), land_cells=int(land.sum()),
            covered_land_cells=int((covered&land).sum()), river_cells=int(river.sum()),
            numeric_sha256=numeric_digest(path))
    return records


def source_rows():
    tables, _, _ = load_tables()
    byid = {r['sitecode']: r for r in tables['AllSites']}
    rows = [byid[r['sitecode']] for r in tables['Settlements']]
    if len(rows)!=134 or any(r['sitetype'].casefold()!='settlement' for r in rows):
        raise ValueError('Changed prepared settlement cohort')
    return rows


def match_rows(x, rows, methods):
    lat = np.array([float(r['north']) for r in rows]); lon = np.array([float(r['east']) for r in rows])
    zones = np.array([r['surveyzone'] for r in rows]); flags = np.array([r['ehs'].casefold() for r in rows])
    source_inside = np.zeros(len(rows), bool)
    for zone, frame in methods['frames'].items():
        source_inside |= (zones==zone) & (sphere_distance(lat, lon, frame['latitude'], frame['longitude']) <= 13.)
    xx, yy = forward(lat, lon, 20.8, 78.5)
    tree = cKDTree(xyz(x['lat'].ravel(), x['lon'].ravel()))
    ny, nx = x['land'].shape; cell = float(x['cell_km'])
    matches = {}
    for name, dx, dy in OFFSETS:
        la, lo = inverse(xx+dx, yy+dy, 20.8, 78.5)
        ids = tree.query(xyz(la, lo))[1]
        in_window = (np.abs(xx+dx)<=nx*cell/2) & (np.abs(yy+dy)<=ny*cell/2)
        land = x['land'].ravel()[ids]
        matches[name] = dict(cells=ids.tolist(), in_window=in_window.tolist(), land=land.tolist())
    return dict(site_ids=[r['sitecode'] for r in rows], zones=zones.tolist(), phase=flags.tolist(),
                source_inside=source_inside.tolist(), offsets=matches)


def cohort_indices(matches, cohort):
    flags = np.array(matches['phase']); valid = np.array(matches['source_inside'])
    if cohort=='EH-S_yes': valid &= flags=='yes'
    elif cohort=='possible_phase': valid &= np.isin(flags, ['yes', '?', ''])
    elif cohort!='whole_record': raise ValueError(cohort)
    return valid


def mean(values):
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else None


def evaluate_grid(x, rows, methods, out, cell):
    args = {k:x[k] for k in ['density', 'land', 'water_km', 'road', 'elev', 'aridity', 'allowed']}
    args['cell_km'] = float(x['cell_km'])
    score, eligible = site_fields(**args)
    production, _, smooth = settle.place_towns(**args, marked=[], seed=1)
    count = len(production)
    print(cell, 'km natural production budget', count, 'eligible', int(eligible.sum()), flush=True)
    fields = {'environment': np.where(eligible, score, 0.),
        'fixed_L800': intensity_fields(score, eligible, count, cell, history=x['history800'])[0],
        'lead_L450': intensity_fields(score, eligible, count, cell, history=x['history450'])[0]}
    lead_radius = intensity_fields(score, eligible, count, cell, history=x['history450'])[1]
    nohistory_radius = intensity_fields(score, eligible, count, cell)[1]
    placements = {'production_seed1': (np.asarray(production, int).reshape(-1, 2), None),
        'fixed_L800_seed1': (np.asarray(fixed_count_sites(score, eligible, count, cell,
            min_spacing_km=18., history=x['history800'], seed=1, stochastic=False).towns, int).reshape(-1,2), None)}
    for name, history, radius in [('lead_L450', x['history450'], lead_radius), ('ablation_nohistory', None, nohistory_radius)]:
        for seed in SEEDS:
            p = adaptive_count_sites(score, eligible, count, cell, history=history,
                coefficient=.35, seed=seed, stochastic=True)
            placements[f'{name}_seed{seed}'] = (np.asarray(p.towns, int).reshape(-1,2), radius)
    numerical = dict(score=score, eligible=eligible, **fields)
    constraints = {}
    width = x['land'].shape[1]
    for name, (towns, radius) in placements.items():
        ids = towns[:,0]*width+towns[:,1]
        dy = towns[:,None,0]-towns[None,:,0]; dx = towns[:,None,1]-towns[None,:,1]
        distances = np.hypot(dy,dx)*cell
        pairs = np.triu(np.ones(distances.shape, bool),1)
        if radius is not None:
            local = radius.ravel()[ids]; threshold = .5*(local[:,None]+local[None,:])
        elif name.startswith('fixed'): threshold = np.full(distances.shape, 18.)
        else:
            local = settle.SPACING*np.minimum(np.sqrt(settle.SEAT_PEOPLE/settle.SEAT_REF_DENSITY
                *(settle.SEAT_REF_DENSITY/np.maximum(smooth.ravel()[ids],1e-9))**settle.SEAT_BETA/np.pi), settle.MAX_RADIUS_KM)
            # Legacy sequential exclusion is asymmetric: each earlier site blocks later ones.
            threshold = np.broadcast_to(local[:,None], distances.shape)
        check = dict(requested=count, placed=len(towns), count_met=len(towns)==count,
            all_eligible=bool(eligible.ravel()[ids].all()), unique=len(np.unique(ids))==len(ids),
            spacing_pass=bool(np.all(distances[pairs] > np.broadcast_to(threshold, distances.shape)[pairs])),
            minimum_separation_km=float(distances[pairs].min()) if pairs.any() else None)
        constraints[name] = check; numerical['towns_'+name] = towns
        print(cell, name, check['placed'], 'constraints', all(check[k] for k in ['count_met','all_eligible','unique','spacing_pass']), flush=True)
    np.savez_compressed(out/f'model_{cell}km.npz', **numerical)
    matches = match_rows(x, rows, methods)
    private = CACHE/f'transfer_matches_{cell}km.json'; write(private, matches)
    frame_masks = {zone: (x['land'] & (sphere_distance(x['lat'], x['lon'], f['latitude'], f['longitude'])<=13.))
                   for zone, f in methods['frames'].items()}
    output = []
    for cohort in ['EH-S_yes','possible_phase','whole_record']:
        membership = cohort_indices(matches, cohort)
        for offset, match in matches['offsets'].items():
            valid = membership & np.array(match['in_window']) & np.array(match['land'])
            ids = np.array(match['cells']); zones = np.array(matches['zones'])
            for zone, mask in frame_masks.items():
                selected = valid & (zones==zone); cells = np.unique(ids[selected])
                opportunity = {}
                for name, field in fields.items():
                    values, background = field.ravel()[cells], field[mask]
                    ranks = relative_ranks(values, background)
                    opportunity[name] = dict(mean_percentile=mean(ranks.tolist()),
                        median_percentile=float(np.median(ranks)) if len(ranks) else None,
                        relative_mean_score_lift=float(values.mean()/background.mean()) if len(values) and background.mean()>0 else None)
                captures = {name:{str(r):capture_fraction(cells,towns,width,cell,r) for r in [5,10,25]}
                            for name,(towns,_) in placements.items()}
                output.append(dict(cohort=cohort, offset=offset, zone=zone,
                    included_records=int(selected.sum()), distinct_cells=len(cells),
                    background_land_cells=int(mask.sum()), eligible_fraction=mean(eligible.ravel()[cells].astype(float).tolist()),
                    matched_cell_centres_outside_frame=int((~mask.ravel()[cells]).sum()),
                    opportunity=opportunity, captures=captures))
    exclusion = dict(settlement_records=len(rows), original_points_inside_assigned_frame=int(sum(matches['source_inside'])),
        original_points_outside_assigned_frame=int(len(rows)-sum(matches['source_inside'])),
        unknown_zone_records=sum(z not in methods['frames'] for z in matches['zones']),
        phase_records=dict(collections.Counter(matches['phase'])),
        by_offset={name:dict(outside_window=int((~np.array(m['in_window'])).sum()),
            nonland=int((~np.array(m['land'])).sum())) for name,m in matches['offsets'].items()})
    return dict(natural_production_count=count, constraints=constraints, exclusions=exclusion,
        metrics=output, private_matches_sha256=sha(private), model_numeric_sha256=numeric_digest(out/f'model_{cell}km.npz'))


def guard(grids):
    primary = [r for r in grids['3']['metrics'] if r['cohort']=='EH-S_yes' and r['offset']=='central']
    support = sum(r['distinct_cells'] for r in primary)>=30 and sum(r['distinct_cells']>=8 for r in primary)>=2
    ranks = {name:mean([r['opportunity'][name]['mean_percentile'] for r in primary]) for name in ['fixed_L800','lead_L450']}
    capture = {name:mean([r['captures'][name]['10'] for r in primary])
               for name in ['fixed_L800_seed1']+[f'lead_L450_seed{s}' for s in SEEDS]}
    lead_capture = mean([capture[f'lead_L450_seed{s}'] for s in SEEDS])
    all_constraints = all(v[k] for g in grids.values() for v in g['constraints'].values()
        for k in ['count_met','all_eligible','unique','spacing_pass'])
    rank_delta = ranks['lead_L450']-ranks['fixed_L800']
    capture_delta = lead_capture-capture['fixed_L800_seed1']
    return dict(support_qualified=bool(support), distinct_cell_zone_units=sum(r['distinct_cells'] for r in primary),
        zones_with_at_least8_units=sum(r['distinct_cells']>=8 for r in primary), mean_percentiles=ranks,
        rank_delta=rank_delta, rank_margin=.05, rank_pass=rank_delta>=-.05,
        mean10km_capture=capture, lead_mean10km_capture=lead_capture, capture_delta=capture_delta,
        capture_margin=.10, capture_pass=capture_delta>=-.10, all24_constraints_pass=all_constraints,
        diagnostic_guard_pass=bool(support and rank_delta>=-.05 and capture_delta>=-.10 and all_constraints),
        adopt=False, reason='Engineering diagnostic only;partial targeted rural survey does not validate counts,population sizes or institutional roles.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=DEFAULT_OUT);args=p.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    plan=json.loads((CONFIG/'plan.json').read_text())
    assert plan['status']=='declared_before_regional_environmental_inputs_or_prediction_scores'
    parent_hashes={path:sha(ROOT/path) for path in PARENTS}
    input_hashes={path:sha(ROOT/path) for path in SOURCES}
    records=prepare_inputs(out);rows=source_rows();methods=json.loads(METHODS.read_text());grids={}
    for cell in [3,9]:
        with np.load(out/f'inputs_{cell}km.npz') as archive:x=dict(archive)
        grids[str(cell)]=evaluate_grid(x,rows,methods,out,cell)
    result=dict(status='completed_prospective_frozen_regional_diagnostic_source_now_spent',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),methods_sha256=sha(METHODS),producer_sha256=sha(Path(__file__)),
        parent_artifacts=parent_hashes,input_sources=input_hashes,inputs=records,grids=grids,guard=guard(grids),
        limits='Partial targeted archaeological survey;conditional known-site comparison,not true absence,censusprecision,exactAD200occupation or globalindependentcalibration. UpstreamEarthpredictors/historyexposed;only placementparametercomparison prospective.3kmrefinementdoesnotcreatefinerobservedclimate;site smoothing1cell changesphysicalscale;roadzeros;globalannualaridity common-inputlimitation. Allplacementscompatibilitycountnotnewcountfit. Relativeopportunityisnotexactinclusionprobabilityorpeople.',
        raw_rows_or_coordinates_redistributed=False)
    assert parent_hashes=={path:sha(ROOT/path) for path in PARENTS}
    write(out/'results.json',result);print(json.dumps(result['guard'],indent=2),flush=True)


if __name__=='__main__':main()
