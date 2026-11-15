"""Settlement ensemble (calibration/settlement_ensemble_20261115/plan.json): 40 placement/size draws."""
import csv, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_fantasy_inputs as I
from polity import fields as F, settlement_sizes as Z
from polity.settlement_locations import prior_tiling_sites, match_count
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_ensemble_20261115/plan.json'; OUT = ROOT / 'output/settlement_ensemble_20261115'
PUB = ROOT / 'output/settlement_hierarchy_map_20261115'; DATA = ROOT / 'atlases/earth_fit/data'
LORE = {'imperial capital': 0, 'major imperial city': 1, 'fortified city': 2, 'fortified town': 3}; SEEDS = list(range(1, 41))


def seats(mode):
    p = DATA / ('release3/hierarchy/corrected/hierarchy_links.csv' if mode == 'corrected' else 'release3/hierarchy/hierarchy_links.csv')
    with open(p, encoding='utf-8') as h: return {r['province_seat'] for r in csv.DictReader(h)}


def sizes(mode, w, towns, marked_sites, seed, coef, sigma, phi, lo, hi, people, land, cell, seat_names):
    sites = [dict(s) for s in marked_sites] + [dict(row=int(y), column=int(x), marked=False, name='') for y, x in towns]
    sites.sort(key=lambda s: s['row'] * land.shape[1] + s['column'])
    centres = np.array([[s['row'], s['column']] for s in sites]); (_, _, _), H = Z.hinterlands(centres, land, people, cell)
    kinds = {(t['row'], t['col']): t['kind'] for t in F.settlements(land.shape)}
    kind = [kinds.get((s['row'], s['column'])) if s['marked'] else None for s in sites]
    valid = H > 0; cap = np.array([1.0 if s['marked'] and s['name'] in seat_names else 0.0 for s in sites])
    mean = np.full(len(sites), np.nan); mean[valid] = coef[0] + coef[1] * np.log(H[valid]) + coef[2] * cap[valid]
    e = np.array(Z.draws(len(sites), seed), float)
    mk = np.array([s['marked'] for s in sites]); M = np.flatnonzero(mk & valid); U = np.flatnonzero(~mk & valid)
    d = np.sqrt(((centres[U][:, None, :] - centres[M][None, :, :]) ** 2).sum(2)) * cell; own = np.where(d.min(1) <= 75.0, M[d.argmin(1)], -1)
    rng = np.random.default_rng(2026)
    for m in M:
        mem = rng.permutation(U[own == m]); pool = np.r_[m, mem[:int(round(phi * len(mem)))]]; j = pool[np.argmax(e[pool])]; e[m], e[j] = e[j], e[m]
    area = np.where(valid, Z.generate_area(np.nan_to_num(mean), sigma, e, lo, hi), 0.0)
    ranked = sorted((i for i in range(len(sites)) if kind[i] in LORE and valid[i]), key=lambda i: (LORE[kind[i]], -H[i], i))
    area[ranked] = np.sort(area[ranked])[::-1]
    top = [i for i in ranked if kind[i] in ('imperial capital', 'major imperial city')]; k = len(top)
    if k:
        biggest = list(np.argsort(-area, kind='stable')[:k]); values = np.sort(area)[::-1][:k].copy()
        freed = sorted([area[i] for i in top if i not in biggest], reverse=True); holders = sorted(i for i in biggest if i not in top)
        area[top] = values
        for hh, vv in zip(holders, freed): area[hh] = vv
    return sites, area


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    OUT.mkdir(parents=True, exist_ok=True)
    er = json.loads((PUB / 'earth_results.json').read_text())['sizes']['primary']; m = er['models']['M1C']
    coef, sigma, phi = m['full_coefficients'], m['heldout_sigma'], m['hierarchy_phi']; lo, hi = er['area_range_ha']; summary = {}
    for mode in ('raw', 'corrected'):
        w = I.world(mode); pub_sites = json.loads((PUB / f'release3/placed_{mode}_sites.json').read_text())['sites']
        f = np.load(PUB / f'release3/placed_{mode}_fields.npz'); land = f['land']; cell = float(f['cell_km'])
        with np.load(w['folder'] / 'administration_grid.npz') as z: people = np.where(z['land'], z['density'], 0.) * cell ** 2
        marked_sites = [s for s in pub_sites if s['marked']]; seat_names = seats(mode)
        kw = dict(allowed=w['claimed'], aridity=w['aridity'], marked=w['marked'], dry_water_km=w['dry_water_km']); args = (w['density'], w['land'], w['water_km'], w['road'], w['elev'], w['cell'])
        count = len(prior_tiling_sites(*args, **kw)); hits = np.zeros(land.shape); marked_res = {s['name']: [] for s in marked_sites}
        for seed in SEEDS:
            _, towns = match_count(lambda sp: prior_tiling_sites(*args, prior=w['prior'], seat_people=sp, seed=seed, **kw), count)
            sites, area = sizes(mode, w, towns, marked_sites, seed, coef, sigma, phi, lo, hi, people, land, cell, seat_names)
            if seed == 1:
                pub = {(s['row'], s['column']) for s in pub_sites if not s['marked']}
                assert {(int(y), int(x)) for y, x in towns} == pub, 'replica positions differ from the published draw'
                assert np.allclose(area, f['area_ha'], rtol=1e-9, atol=1e-9), 'replica areas differ from the published draw'
            grid = np.zeros(land.shape, bool); grid[tuple(np.array(towns).T)] = True
            hits += ndi.binary_dilation(grid, structure=np.ones((3, 3)))
            res = Z.residents(area, 'central')
            for s, r in zip(sites, res):
                if s['marked']: marked_res[s['name']].append(float(r))
            print(mode, 'seed', seed, flush=True)
        rec = np.where(land, hits / len(SEEDS), 0.0)
        np.savez_compressed(OUT / f'recurrence_{mode}.npz', recurrence=rec.astype(np.float32), land=land)
        with open(OUT / f'marked_residents_{mode}.csv', 'w', newline='', encoding='utf-8') as h:
            wr = csv.writer(h, lineterminator='\r\n'); wr.writerow(['name', 'p10', 'p50', 'p90'])
            for n, v in sorted(marked_res.items()): wr.writerow([n] + [round(float(np.quantile(v, q))) for q in (.1, .5, .9)])
        lab, nh = ndi.label(rec >= 0.5)
        summary[mode] = dict(seeds=len(SEEDS), proposed_per_draw=count, hotspots_ge_half=int(nh), land_share_ge_half=float((rec >= .5)[land].mean()),
                             land_share_any=float((rec > 0)[land].mean()), replica_seed1_exact=True)
    write(OUT / 'results.json', dict(status='settlement_ensemble', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), summary=summary))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
