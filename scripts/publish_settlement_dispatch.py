"""Add checked joint food/collection scenarios to the existing map selectors."""
import copy
import gzip
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_dispatch import OUT, PARENT
from settlement_locations_earth import sha, write
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import permanent_food_ceiling

DATA = ROOT / 'atlases/earth_fit/data'


def identity(result):
    suffix = 'open' if result['availability'] == 'all_open' else 'closed'
    return f'dispatch{result["hours_worker_year"]}_{int(result["load_kcal"])}_{suffix}'


def town_image(f, model, x, assignment, meta):
    land = x['land']; h, w = land.shape; size = land.size
    rgb = np.full((size, 3), [.84, .89, .94]); rgb[land.ravel()] = [.84, .83, .78]
    reached = assignment > 0; request = np.array([s['civilian_request_people'] for s in model['sites']])
    ratio = np.clip(np.divide(f['civilian'], request, out=np.zeros_like(request), where=request > 0), 0, 1)[assignment[reached] - 1]
    rgb[reached] = np.array([.89, .85, .76]) * (1 - ratio[:, None]) + np.array([.47, .66, .58]) * ratio[:, None]
    image = Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image); pixel = meta['width'] / w
    for j, site in enumerate(model['sites']):
        xx, yy = (site['column'] + .5) * pixel, (site['row'] + .5) * pixel
        if f['civilian'][j] < 50:
            if site['marked']: draw.rectangle((xx - 2, yy - 2, xx + 2, yy + 2), outline='#222222')
            continue
        radius = max(1.5, min(8, 1.2 + np.sqrt(f['total'][j]) / 22))
        color = model['actors'][site['actor_index']]['color'] if site['actor_index'] >= 0 else '#59636b'
        draw.ellipse((xx - radius, yy - radius, xx + radius, yy + radius), fill=color, outline='white')
        if f['active'][j]: draw.point((xx, yy), fill='#111111')
    return image


def reach_image(masks, model, x, meta):
    land = x['land']; h, w = land.shape; nodes = np.flatnonzero(land)
    pop = np.array([i.bit_count() for i in range(4096)], np.uint8); count = pop[masks]
    best = count.max(axis=0); winner = count.argmax(axis=0); alpha = best / 12 * .8
    colors = np.array([to_rgb(a['color']) for a in model['actors']])
    rgb = np.full((land.size, 3), [.84, .89, .94])
    rgb[nodes] = np.array([.89, .87, .81]) * (1 - alpha[:, None]) + colors[winner] * alpha[:, None]
    overlap = (count > 0).sum(axis=0) > 1; pattern = ((nodes // w + nodes % w) % 5 == 0) & overlap
    rgb[nodes[pattern]] = rgb[nodes[pattern]] * .65 + .35
    return Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)


def main():
    replay = json.loads((OUT / 'replay.json').read_text())
    if replay['status'] != 'passed' or len(replay['byte_exact_cases']) != 16:
        raise ValueError('Sixteen byte-exact case replays required')
    parent = json.loads((DATA / 'settled_reach.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    protected_paths = [DATA / 'atlas.json', DATA / 'settled_reach.json', DATA / 'settlement_feedback.json']
    for mode in ('raw', 'corrected'):
        folder = DATA / ('corrected' if mode == 'corrected' else '')
        protected_paths.extend(folder / n for n in ('settled_reach.json.gz', 'settled_reach.bin.gz'))
    protected_paths += [p for p in (DATA / 'feedback').rglob('*') if p.is_file()]
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in protected_paths}; packets = {}
    for mode in ('raw', 'corrected'):
        p = parent['packets'][mode]; folder = DATA / ('corrected' if mode == 'corrected' else '')
        original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
        x = dict(np.load(PARENT / f'{mode}_inputs.npz')); land = x['land']; size = land.size
        reach = json.loads((OUT / f'{mode}_reach.json').read_text()); checked = json.loads((OUT / f'{mode}_reach_review.json').read_text())
        if checked['status'] != 'passed' or checked['results_sha256'] != sha(OUT / f'{mode}_reach.json'):
            raise ValueError('Current independent joint reach review required')
        masks = np.load(OUT / f'{mode}_reach.npz')['masks']; reference = np.load(PARENT / f'{mode}_footprints.npz')['reference']
        with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as stream: prefix = stream.read(p['offsets']['masks'])
        assignment = np.frombuffer(prefix, '<u2', count=size, offset=p['offsets']['catchments'])
        model = dict(version=1, atlas='earth_fit', climate=mode, shape=list(land.shape), sites=original['sites'],
            actors=original['actors'], specification=original['specification'], labour_specification=original['labour_specification'],
            cases=[copy.deepcopy(original['cases'][0])], summaries=[copy.deepcopy(original['summaries'][0])],
            scope='Joint people/rural work/cereal/dispatch/collection budget;travel footprints remain potential access,not funded geographic patrols.')
        target = DATA / 'dispatch' / mode; target.mkdir(parents=True, exist_ok=True)
        options = {'reach_towns': [], 'reach_defacto': []}; fields = {}
        for i, key in enumerate(reach['cases']):
            source = OUT / key; r = json.loads((source / 'results.json').read_text()); review = json.loads((source / 'review.json').read_text())
            assert review['status'] == 'passed' and review['results_sha256'] == sha(source / 'results.json')
            assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_settlement_dispatch.py')
            for path, digest in {**r['sources'], **r['producers']}.items():
                if sha(ROOT / path) != digest: raise ValueError('Changed reviewed source: ' + path)
            for name, digest in replay['byte_exact_cases'][key].items(): assert sha(source / name) == digest
            f = dict(np.load(source / 'fields.npz')); total = f['total']; arrivals = f['arrivals']
            need = np.broadcast_to(total * 2500 * 365 / 12, arrivals.shape)
            food = periodic_food_year(arrivals, need, total * 2500 * 90, loss_fraction_year=.05, step_days=365 / 12, record=True)
            np.testing.assert_allclose(food.consumed, f['town_consumed'], rtol=1e-11, atol=1e-4)
            ident = identity(r); availability = 'open' if r['availability'] == 'all_open' else '3 bins closed'
            label = f'Joint food + collection · {r["hours_worker_year"]}h / {r["load_kcal"]/1000:g}k / {availability}'
            model['cases'].append(dict(id=ident, label=label, feedback_coupled=True, food_constrained=True, labour_constrained=True,
                hours_worker_year=r['hours_worker_year'], harvest_days=30, transfer_fraction=.075,
                food_ceiling_people=permanent_food_ceiling(arrivals).tolist(), civilian_people=f['civilian'].tolist(),
                institutional_people=f['staff'].tolist(), institutional_active=f['active'].tolist(), community_viable=(f['civilian'] >= 50).tolist(),
                resident_budget_people=f['budget'].tolist(), source_supported=f['source_supported'].tolist(),
                monthly_arrivals_kcal=arrivals.T.tolist(), monthly_need_kcal=need.T.tolist(), stock_path_kcal=food.stock_path.T.tolist(),
                work_summary=dict(production_retained=r['local_production_retained'], scenario_workers=float(f['rural'].sum() * .4)),
                rural_ledger=dict(unmet_kcal=r['local_rural_unmet_kcal'], deficit_origins=r['local_rural_deficit_origins'], outside_unmet_kcal=r['outside_rural_unmet_kcal']),
                source_gate=r['source_gate'], empirical_resident_size_fit=False, whole_world_food_supported=False,
                dispatch_work=dict(load_kcal=r['load_kcal'], availability=r['availability'], dispatch_scale=f['dispatch_scale'].tolist(),
                    collection_hours=f['work_required_collection_hours'].T.tolist(), gross_hours=f['work_gross_hours'].T.tolist(),
                    unused_hours=f['work_unused_hours'].T.tolist(), actual_geographic_patrol_hours_qualified=False)))
            model['summaries'].append(dict(reach['summaries'][i], id=ident, civilian_people=r['civilian_people'], institutional_people=r['staff_people']))
            grid = target / (ident + '.npz'); shutil.copyfile(source / 'fields.npz', grid); fields[ident] = str(grid.relative_to(DATA))
            towns = target / (ident + '_towns.webp'); town_image(f, model, x, assignment, meta).save(towns, lossless=True)
            travel = target / (ident + '_reach.webp'); reach_image(masks[i], model, x, meta).save(travel, lossless=True)
            note = ('Experimental joint population, farm work, cereal and monthly staff collection. Reduced dispatch passes source meals, '
                'destination stocks and integer collector-trip hours. Loads/work/diets/roles remain scenarios. Uniform catchment dispatch is not globally optimal. '
                'Reach is potential travel access from qualified sources;actual geographic patrol work,authority and mobile occupancy remain unqualified.')
            common = dict(value=ident, label=label, note=note, integrated_support=True, dispatch_support=True)
            options['reach_towns'].append(dict(common, file=str(towns.relative_to(DATA)), file_sha256=sha(towns),
                items=[dict(color='#78a895', label='Same-budget civilians; collection hours checked'), dict(color='#59636b', label='Circles: residents; dark centre: conditional staff'),
                    dict(color='#d6d4c7', label='Unsupported scenario; actual communities unknown')], caption='Same people and grain;monthly collection and source food both checked.'))
            options['reach_defacto'].append(dict(common, file=str(travel.relative_to(DATA)), file_sha256=sha(travel),
                items=[dict(color=a['color'], label=a['name']) for a in model['actors']] + [dict(color='#e3decf', label='No modeled access; local organization unscored')],
                caption='Potential travel access from food/collection-qualified sources;geographic patrol staffing and authority unqualified.'))
        payload = target / 'settled_reach.json.gz'; payload.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        combined = np.concatenate([reference[None], masks]); binary = target / 'settled_reach.bin.gz'
        binary.write_bytes(gzip.compress(prefix + combined.astype('<u2').tobytes(), mtime=0))
        packets[mode] = dict(shape=list(land.shape), cell_px=meta['width'] / land.shape[1], land_cells=int(land.sum()),
            masks_shape=list(combined.shape), offsets=p['offsets'], raw_bytes=len(prefix) + combined.nbytes,
            payload=str(payload.relative_to(DATA)), payload_sha256=sha(payload), binary=str(binary.relative_to(DATA)), binary_sha256=sha(binary),
            parent_payload_sha256=p['payload_sha256'], expected_harvest_fingerprint=p['expected_harvest_fingerprint'],
            expected_harvest_binary_sha256=p['expected_harvest_binary_sha256'], options=options, fields=fields)
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest: raise ValueError('Original map or packet changed: ' + path)
    write(DATA / 'settlement_dispatch.json', dict(version=1, status='optional_joint_dispatch_research', packets=packets,
        producer_sha256=sha(Path(__file__)), original_packets_unchanged=True, default_adoption=False))
    page = DATA.parent / 'index.html'
    page.write_text(re.sub(r'<script src="settled-reach\.js"[^>]*></script>',
        '<script src="settled-reach.js" data-settled-reach-enabled data-settlement-feedback-enabled data-settlement-dispatch-enabled></script>', page.read_text()))
    for name in ('settled-reach.js', 'evidence.js'): shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_optional_joint_dispatch_maps',
        manifest_sha256=sha(DATA / 'settlement_dispatch.json'), original_packets_sha256=preserved,
        publisher_sha256=sha(Path(__file__)), cases_per_climate=8, defaults_unchanged=True,
        actual_geographic_patrol_work_qualified=False))
    print('Published16 joint dispatch scenarios in existing settlement/potential-reach selectors.', flush=True)


if __name__ == '__main__': main()
