"""Release-2 fantasy settlements: Earth-calibrated sizes on the retained placement.

Follows calibration/settlement_release2_20261113/plan.json. The placement
confirmation test failed its declared rule, so the published legacy sites are
kept. Sizes use the gate-passing model from the Earth calibration. People are
moved from hinterland and regional cells, never created (plan amendment A1).
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settlement_sizes as Z
from polity import fields as F
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_release2_20261113/plan.json'
OUT = ROOT / 'output/settlement_release2_20261113'
DATA = ROOT / 'atlases/earth_fit/data'
LEDGER = ROOT / 'output/settlement_feedback_20261112'
LORE_RANK = {'imperial capital': 0, 'major imperial city': 1, 'fortified city': 2, 'fortified town': 3}
KCAL_YEAR = 2500.0 * 365.0
COLLECTION, RETENTION, MAX_SHARE, SEED = 0.10, 0.95, 0.5, 1
WIDE_RADII_KM = (120.0, 240.0, 480.0, 960.0, 1920.0)
SCENARIOS = ('central', 'low')        # headline first (amendment A4)


def build(mode, earth, out):
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    packet = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    sites = packet['sites']; shape = tuple(packet['shape']); h, w = shape
    meta = json.loads((DATA / 'atlas.json').read_text())
    cell = meta['width'] / w * meta['mi_per_px'] * 1.609344
    with np.load(folder / 'administration_grid.npz') as z:
        land, density = z['land'], z['density']
    people = np.where(land, density, 0.0) * cell ** 2
    centres = np.array([[s['row'], s['column']] for s in sites])
    kinds = {(t['row'], t['col']): t['kind'] for t in F.settlements(shape)}
    kind = [kinds.get((s['row'], s['column'])) if s['marked'] else None for s in sites]
    if any(s['marked'] and k is None for s, k in zip(sites, kind)):
        raise ValueError('A marked site lost its campaign symbol')
    (cells, owner, weight), H = Z.hinterlands(centres, land, people, cell)

    size = earth['sizes']['primary']; name = size['selected']; names = Z.MODELS[name]
    if not size['gate']['passed'] or names != ('lnH',):
        raise ValueError('This builder implements the adopted M1 size model only')
    coef = size['models'][name]['full_coefficients']; sigma = size['models'][name]['heldout_sigma']
    low_ha, high_ha = size['area_range_ha']
    valid = H > 0
    mean = np.full(len(sites), np.nan); mean[valid] = coef[0] + coef[1] * np.log(H[valid])
    e = Z.draws(len(sites), SEED)
    # Lore ordering (amendment A2): the largest drawn residuals go to the ranked
    # walled places; everything else keeps the remaining draws in sequence.
    ranked = sorted((i for i in range(len(sites)) if kind[i] in LORE_RANK and valid[i]),
                    key=lambda i: (LORE_RANK[kind[i]], -H[i], i))
    top = np.argsort(-e, kind='stable')[:len(ranked)]
    rest = np.delete(e, top)
    pooled = [i for i in range(len(sites)) if i not in set(ranked)]
    e_new = np.empty(len(sites)); e_new[ranked] = e[top]; e_new[pooled] = rest
    if not np.array_equal(np.sort(e_new), np.sort(e)):
        raise ValueError('Lore reassignment changed the residual set')
    e = e_new; order = ranked
    area = np.where(valid, Z.generate_area(np.nan_to_num(mean), sigma, e, low_ha, high_ha), 0.0)

    # Strict lore order (amendment A3): the ranked places' own areas, reassigned so
    # area follows campaign rank. Same set of areas, same distribution.
    area[ranked] = np.sort(area[ranked])[::-1]

    x = dict(np.load(LEDGER / f'{mode}_inputs.npz'))
    if not np.array_equal(x['nodes'], [s['node'] for s in sites]) or not np.array_equal(x['land'], land):
        raise ValueError('Reviewed collection catchments do not match these sites')
    if not np.allclose(x['people'], people.ravel(), rtol=1e-12, atol=1e-9):
        raise ValueError('Reviewed ledger people differ from the population grid')
    local = x['local_index']; catchment = x['owner']
    yy, xx = np.indices(shape); L = {}; summary = {}
    q = lambda v: {str(p): float(np.quantile(v, p)) for p in (.05, .25, .5, .75, .95)}
    for scenario in SCENARIOS:
        # People ledger (amendment A1): own hinterland first, then the wider region.
        wanted = np.where(valid, Z.residents(area, scenario), 0.0)
        own = np.minimum(wanted, MAX_SHARE * H); excess = wanted - own
        frac = np.divide(own, H, out=np.zeros_like(own), where=H > 0)
        moved_own = np.bincount(cells, weights=weight * people.ravel()[cells] * frac[owner], minlength=h * w)
        rural = (people.ravel() - moved_own).reshape(shape)
        wide = np.zeros(len(sites)); radius_used = np.zeros(len(sites)); shortfall = np.zeros(len(sites))
        for i in np.argsort(-excess, kind='stable'):
            if excess[i] <= 0:
                break
            d2 = ((yy - centres[i, 0]) ** 2 + (xx - centres[i, 1]) ** 2) * cell ** 2
            for radius in WIDE_RADII_KM:
                mask = land & (d2 <= radius ** 2); pool = float(rural[mask].sum())
                if pool >= 4.0 * excess[i]:
                    break
            draw = min(excess[i], 0.25 * pool)
            rural[mask] *= 1.0 - draw / pool
            wide[i] = draw; radius_used[i] = radius; shortfall[i] = excess[i] - draw
        res = own + wide; rural = rural.ravel(); moved = people.ravel() - rural
        if rural.min() < -1e-6 or abs(moved.sum() - res.sum()) > 1e-6 * max(1.0, res.sum()):
            raise ValueError('People ledger does not close')
        need = rural[local] * KCAL_YEAR
        surplus = np.maximum(x['potential_kcal'][local] - need, 0.0)
        collectable = np.bincount(catchment, weights=surplus, minlength=len(sites)) * COLLECTION * RETENTION
        support = np.divide(collectable, res * KCAL_YEAR, out=np.zeros_like(res), where=res > 0)
        positive = res > 0
        L[scenario] = dict(res=res, own=own, wide=wide, radius=radius_used, rural=rural, moved=moved, support=support)
        summary[scenario] = dict(total=float(res.sum()), share_of_world_people=float(res.sum() / people.sum()),
            quantiles=q(res[positive]), largest=float(res.max()),
            people_ledger=dict(moved=float(moved.sum()), rural=float(rural.sum()),
                residual=float(people.sum() - rural.sum() - res.sum()),
                from_own_hinterland=float(own.sum()), from_wider_region=float(wide.sum()),
                sites_drawing_wider=int((wide > 0).sum()), unmet_shortfall=float(shortfall.sum()),
                wider_radius_counts={str(int(r)): int((radius_used == r).sum()) for r in WIDE_RADII_KM},
                minimum_cell_rural_share=float(np.min(np.divide(rural, people.ravel(), out=np.ones_like(rural), where=people.ravel() > 0)))),
            local_cereal=dict(collection_fraction=COLLECTION, retention=RETENTION,
                fully_supported_sites=int(np.sum(positive & (support >= 1.0))),
                import_dependent_sites=int(np.sum(positive & (support < 1.0))),
                supported_resident_equivalents=float(np.minimum(collectable / KCAL_YEAR, res).sum()),
                median_support_share=float(np.median(support[positive])),
                collection_origin_cells=int(len(local)),
                origin_cells_below_rural_need=int(np.sum(x['potential_kcal'][local] < need - 1e-6))))

    legacy = np.array([s['civilian_request_people'] for s in sites])
    rows = []
    for i, s in enumerate(sites):
        row = dict(id=s['id'], name=s['name'], row=s['row'], column=s['column'], marked=bool(s['marked']),
            campaign_symbol=kind[i] or '', actor=s['actor'] or '', hinterland_people=round(float(H[i]), 1),
            calibrated_area_ha=round(float(area[i]), 2))
        for k in SCENARIOS:
            v = L[k]
            row.update({f'residents_{k}': round(float(v['res'][i]), 1), f'from_wider_region_{k}': round(float(v['wide'][i]), 1),
                f'local_cereal_support_share_{k}': round(float(min(v['support'][i], 99.0)), 4),
                f'import_dependent_{k}': bool(v['res'][i] > 0 and v['support'][i] < 1.0)})
        row['legacy_request_people'] = round(float(legacy[i]), 1); rows.append(row)
    target = out / f'fantasy_{mode}_towns.csv'
    with target.open('w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\r\n'); wr.writeheader(); wr.writerows(rows)
    arrays = {}
    for k, v in L.items():
        arrays.update({f'residents_{k}': v['res'], f'from_own_hinterland_{k}': v['own'], f'from_wider_region_{k}': v['wide'],
            f'wider_radius_km_{k}': v['radius'], f'rural_{k}': v['rural'].reshape(shape), f'moved_{k}': v['moved'].reshape(shape),
            f'local_support_share_{k}': v['support']})
    np.savez_compressed(out / f'fantasy_{mode}_fields.npz', land=land, people=people, hinterland_people=H, area_ha=area,
        residual=e, cell_km=cell, lore_class=np.array([LORE_RANK.get(k, 9) for k in kind]), **arrays)
    return dict(climate=mode, sites=len(sites), marked=int(sum(s['marked'] for s in sites)), cell_km=cell,
        world_people=float(people.sum()), sites_without_hinterland_people=int((~valid).sum()), headline_scenario=SCENARIOS[0],
        size_model=dict(name=name, coefficients=coef, sigma=sigma, area_range_ha=[low_ha, high_ha], seed=SEED),
        area_quantiles_ha=q(area[valid]), earth_observed_quantiles_ha=size['observed_quantiles_ha'],
        total_area_ha=float(area.sum()), residents=summary,
        legacy=dict(request_total=float(legacy.sum()), share_of_world_people=float(legacy.sum() / people.sum()),
                    quantiles=q(legacy), largest=float(legacy.max())),
        lore_ordering=dict(marked_reassigned=len(order), rule='largest residuals to ranked walled places (A2); their areas then strictly follow campaign rank (A3)'),
        outputs={p.name: sha(p) for p in (target, out / f'fantasy_{mode}_fields.npz')},
        inputs={str(p.relative_to(ROOT)): sha(p) for p in (folder / 'settled_reach.json.gz', folder / 'administration_grid.npz',
                LEDGER / f'{mode}_inputs.npz', DATA / 'atlas.json')})


def run(out):
    earth = json.loads((OUT / 'results.json').read_text())
    review = json.loads((OUT / 'review.json').read_text())
    if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('Current reviewed Earth calibration required')
    out.mkdir(parents=True, exist_ok=True)
    result = dict(status='release2_fantasy_settlements_calibrated_sizes_legacy_placement',
        plan_sha256=sha(PLAN), earth_results_sha256=sha(OUT / 'results.json'), producer_sha256=sha(__file__),
        model_sha256=sha(ROOT / 'polity/settlement_sizes.py'),
        placement='legacy published sites retained: fixed18_L800 won 5 of 8 quadrants, below the declared 6',
        tracks_rebuilt=False, downstream_layers_rebuilt=False,
        climates={mode: build(mode, earth, out) for mode in ('raw', 'corrected')},
        limits='Sizes are a calibrated distribution with a weak hinterland tilt; an individual town size is one seeded draw, not a prediction. '
               'Residents use a density scenario. Local cereal support is an annual check within the reviewed one-day collection catchments.')
    write(out / 'fantasy.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT)
    r = run(p.parse_args().out)
    for mode, c in r['climates'].items():
        print(mode, {k: (round(v['total']), round(v['share_of_world_people'], 4), round(v['largest']), v['local_cereal']['fully_supported_sites'], v['people_ledger']['sites_drawing_wider']) for k, v in c['residents'].items()})
