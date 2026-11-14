"""Score the published release-3 placement rule on Vidarbha (calibration/vidarbha_release3_20261114/plan.json)."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_vidarbha_transfer as V
from polity import settle
from polity.settlement_locations import site_fields, fixed_count_sites, prior_tiling_sites, match_count
from polity.settlement_intensity import intensity_fields, adaptive_count_sites
from polity.survey_transfer import relative_ranks, capture_fraction, sphere_distance
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/vidarbha_release3_20261114/plan.json'; OUT = ROOT / 'output/vidarbha_release3_20261114'
ARCHIVE = ROOT / 'output/settlement_vidarbha_transfer_20261111/results.json'


def evaluate(x, rows, methods, cell):
    args = {k: x[k] for k in ['density', 'land', 'water_km', 'road', 'elev', 'aridity', 'allowed']}; args['cell_km'] = float(x['cell_km'])
    score, eligible = site_fields(**args)
    production, _, smooth = settle.place_towns(**args, marked=[], seed=1); count = len(production)
    tile = dict(allowed=x['allowed'], aridity=x['aridity'])
    control = prior_tiling_sites(x['density'], x['land'], x['water_km'], x['road'], x['elev'], float(x['cell_km']), **tile)
    assert sorted(map(tuple, control)) == sorted(map(tuple, production)), 'tiling control does not reproduce production'
    seat, release3 = match_count(lambda sp: prior_tiling_sites(x['density'], x['land'], x['water_km'], x['road'], x['elev'], float(x['cell_km']),
                                                               prior=x['history800'], seat_people=sp, **tile), count)
    fields = {'environment': np.where(eligible, score, 0.), 'release3_L800': np.where(eligible, score * x['history800'], 0.),
              'fixed_L800': intensity_fields(score, eligible, count, cell, history=x['history800'])[0],
              'lead_L450': intensity_fields(score, eligible, count, cell, history=x['history450'])[0]}
    placements = {'production_seed1': np.asarray(production, int).reshape(-1, 2), 'release3_L800': np.asarray(release3, int).reshape(-1, 2),
                  'fixed_L800_seed1': np.asarray(fixed_count_sites(score, eligible, count, cell, min_spacing_km=18., history=x['history800'], seed=1, stochastic=False).towns, int).reshape(-1, 2)}
    for seed in V.SEEDS:
        placements[f'lead_L450_seed{seed}'] = np.asarray(adaptive_count_sites(score, eligible, count, cell, history=x['history450'], coefficient=.35, seed=seed, stochastic=True).towns, int).reshape(-1, 2)
    width = x['land'].shape[1]; constraints = {}
    for name, towns in placements.items():
        ids = towns[:, 0] * width + towns[:, 1]
        constraints[name] = dict(requested=count, placed=len(towns), count_met=len(towns) == count, all_eligible=bool(eligible.ravel()[ids].all()), unique=len(np.unique(ids)) == len(ids))
    matches = V.match_rows(x, rows, methods)
    frames = {zone: (x['land'] & (sphere_distance(x['lat'], x['lon'], f['latitude'], f['longitude']) <= 13.)) for zone, f in methods['frames'].items()}
    metrics = []
    for cohort in ['EH-S_yes', 'possible_phase', 'whole_record']:
        member = V.cohort_indices(matches, cohort)
        for offset, match in matches['offsets'].items():
            valid = member & np.array(match['in_window']) & np.array(match['land']); ids = np.array(match['cells']); zones = np.array(matches['zones'])
            for zone, mask in frames.items():
                cells = np.unique(ids[valid & (zones == zone)])
                opportunity = {n: V.mean(relative_ranks(f.ravel()[cells], f[mask]).tolist()) for n, f in fields.items()}
                captures = {n: {str(r): capture_fraction(cells, t, width, cell, r) for r in [5, 10, 25]} for n, t in placements.items()}
                metrics.append(dict(cohort=cohort, offset=offset, zone=zone, distinct_cells=len(cells), opportunity=opportunity, captures=captures))
    return dict(natural_production_count=count, release3_seat_people=seat, constraints=constraints, metrics=metrics), placements, fields


def guard(grids):
    primary = [r for r in grids['3']['metrics'] if r['cohort'] == 'EH-S_yes' and r['offset'] == 'central']
    support = sum(r['distinct_cells'] for r in primary) >= 30 and sum(r['distinct_cells'] >= 8 for r in primary) >= 2
    rank = {n: V.mean([r['opportunity'][n] for r in primary]) for n in ('environment', 'release3_L800', 'fixed_L800', 'lead_L450')}
    cap = {n: V.mean([r['captures'][n]['10'] for r in primary]) for n in primary[0]['captures']}
    lead = V.mean([cap[f'lead_L450_seed{s}'] for s in V.SEEDS])
    constraints = all(c[k] for g in grids.values() for c in g['constraints'].values() for k in ('count_met', 'all_eligible', 'unique'))
    rd = rank['release3_L800'] - rank['environment']; cd = cap['release3_L800'] - cap['production_seed1']
    return dict(support_qualified=bool(support), distinct_cell_zone_units=sum(r['distinct_cells'] for r in primary), mean_percentiles=rank, mean10km_capture=cap,
                lead_mean10km_capture=lead, rank_delta_release3_vs_production=rd, capture_delta_release3_vs_production=cd, rank_margin=.05, capture_margin=.10,
                rank_pass=rd >= -.05, capture_pass=cd >= -.10, constraints_pass=bool(constraints), guard_pass=bool(support and rd >= -.05 and cd >= -.10 and constraints),
                drift_control_lead_minus_fixed=lead - cap['fixed_L800_seed1'])


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True)
    records = V.prepare_inputs(out); rows = V.source_rows(); methods = json.loads(V.METHODS.read_text()); grids = {}; arrays = {}
    for cell in (3, 9):
        with np.load(out / f'inputs_{cell}km.npz') as a: x = dict(a)
        grids[str(cell)], placements, fields = evaluate(x, rows, methods, cell)
        for n, t in placements.items(): arrays[f'{cell}km__towns__{n}'] = t
        for n, f in fields.items(): arrays[f'{cell}km__field__{n}'] = f
    np.savez_compressed(out / 'model.npz', **arrays)
    archive = json.loads(ARCHIVE.read_text())
    drift = {}
    for name in ('production_seed1', 'fixed_L800_seed1'):
        old = [r['captures'][name]['10'] for r in archive['grids']['3']['metrics'] if r['cohort'] == 'EH-S_yes' and r['offset'] == 'central']
        new = [r['captures'][name]['10'] for r in grids['3']['metrics'] if r['cohort'] == 'EH-S_yes' and r['offset'] == 'central']
        drift[name] = dict(archived=old, rebuilt=new)
    drift['natural_production_count'] = dict(archived=archive['grids']['3']['natural_production_count'], rebuilt=grids['3']['natural_production_count'])
    result = dict(status='release3_rule_transfer_check_exposed_region', adopt=False, plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)),
        inputs=records, input_sources={p: sha(ROOT / p) for p in V.SOURCES}, survey_files={n: sha(V.CACHE / n) for n in ('Vidarbha_2016Survey_SiteRecords.zip', 'Vidarbha_2016Survey_Readme.txt')},
        grids=grids, guard=guard(grids), input_drift=drift, model_sha256=sha(out / 'model.npz'), raw_rows_or_coordinates_redistributed=False)
    write(out / 'results.json', result); print(json.dumps(result['guard'], indent=1)); print(json.dumps(drift))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
