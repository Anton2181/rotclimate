"""Add optional coupled scenarios to existing atlas modes via a separate packet.

Original model data, manifests and defaults remain byte-identical. The frontend
loads the separate supplement only on the active Earth atlas.
"""
import copy
import gzip
import json
from pathlib import Path
import shutil
import sys
import re

import numpy as np
from PIL import Image, ImageDraw
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, DATA, PLAN
from settlement_locations_earth import sha, write
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import permanent_food_ceiling


def scenario_id(hours, fraction):
    return f'feedback{hours}_{round(fraction * 1000)}'


def main():
    declaration = json.loads(PLAN.read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text())
    if replay['status'] != 'passed' or len(replay['byte_exact_cases']) != 8:
        raise ValueError('Complete fresh eight-case replay required')
    packets = {}; preserved = {str(p.relative_to(ROOT)): sha(p) for p in [DATA / 'atlas.json', DATA / 'settled_reach.json']}
    meta = json.loads((DATA / 'atlas.json').read_text())
    for mode in declaration['climate_modes']:
        old = parent['packets'][mode]; folder = DATA / ('corrected' if mode == 'corrected' else '')
        for name in ('settled_reach.json.gz', 'settled_reach.bin.gz'):
            preserved[str((folder / name).relative_to(ROOT))] = sha(folder / name)
        original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
        x = dict(np.load(OUT / f'{mode}_inputs.npz')); land = x['land']; h, w = land.shape; size = land.size
        reach = json.loads((OUT / f'{mode}_reach.json').read_text())
        review = json.loads((OUT / f'{mode}_reach_review.json').read_text())
        if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / f'{mode}_reach.json'):
            raise ValueError('Current source/reach review required')
        masks = np.load(OUT / f'{mode}_reach.npz')['masks']
        ref = np.load(OUT / f'{mode}_footprints.npz')['reference']
        target = DATA / 'feedback' / mode; target.mkdir(parents=True, exist_ok=True)
        model = dict(version=1, atlas='earth_fit', climate=mode, shape=list(land.shape),
            sites=original['sites'], actors=original['actors'], specification=original['specification'],
            labour_specification=original['labour_specification'], cases=[copy.deepcopy(original['cases'][0])],
            summaries=[copy.deepcopy(original['summaries'][0])],
            scope='Coupled local cell people/work/cereal food; reference populations/work availability/diets remain scenarios. Rural deficits elsewhere preserved.')
        options = {'reach_towns': [], 'reach_defacto': []}; fields = {}
        colors = np.array([to_rgb(a['color']) for a in model['actors']]); pop = np.array([n.bit_count() for n in range(4096)])
        with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:
            prefix = f.read(old['offsets']['masks'])
        assignment = np.frombuffer(prefix, '<u2', count=size, offset=old['offsets']['catchments'])
        for i, c in enumerate(declaration['scenarios']):
            key = f'{mode}_h{c["hours_worker_year"]}_f{c["transfer_fraction"]:g}'; origin = OUT / key
            result = json.loads((origin / 'results.json').read_text()); checked = json.loads((origin / 'review.json').read_text())
            if checked['status'] != 'passed' or checked['results_sha256'] != sha(origin / 'results.json'):
                raise ValueError('Current final cell review required: ' + key)
            for name, digest in replay['byte_exact_cases'][key].items():
                if sha(origin / name) != digest:raise ValueError('Stale fresh feedback replay')
            for name, digest in result['producers'].items():
                if sha(ROOT / name) != digest:raise ValueError('Changed feedback producer: ' + name)
            f = dict(np.load(origin / 'fields.npz')); total = f['total']; arrivals = f['arrivals']
            need = np.broadcast_to(total * 2500 * 365 / 12, arrivals.shape)
            food = periodic_food_year(arrivals, need, total * 2500 * 90, loss_fraction_year=.05, step_days=365/12, record=True)
            np.testing.assert_allclose(food.consumed, f['town_consumed'], rtol=1e-11, atol=1e-4)
            identity = scenario_id(c['hours_worker_year'], c['transfer_fraction'])
            label = f'Coupled residents · {c["hours_worker_year"]}h / {100*c["transfer_fraction"]:g}% · research'
            case = dict(id=identity, label=label, feedback_coupled=True, food_constrained=True, labour_constrained=True,
                hours_worker_year=c['hours_worker_year'], harvest_days=30, transfer_fraction=c['transfer_fraction'],
                food_ceiling_people=permanent_food_ceiling(arrivals).tolist(), civilian_people=f['civilian'].tolist(),
                institutional_people=f['staff'].tolist(), institutional_active=f['active'].tolist(),
                community_viable=(f['civilian'] >= 50).tolist(), resident_budget_people=f['budget'].tolist(),
                source_supported=f['source_supported'].tolist(), monthly_arrivals_kcal=arrivals.T.tolist(),
                monthly_need_kcal=need.T.tolist(), stock_path_kcal=food.stock_path.T.tolist(),
                work_summary=dict(production_retained=result['local_production_retained'], scenario_workers=float(f['rural'].sum() * .4)),
                rural_ledger=dict(unmet_kcal=result['local_rural_unmet_kcal'], deficit_origins=result['local_rural_deficit_origins'],
                    outside_unmet_kcal=result['outside_rural_unmet_kcal']), source_gate=result['source_gate'],
                empirical_resident_size_fit=False, whole_world_food_supported=False)
            model['cases'].append(case)
            summary = dict(reach['summaries'][i], id=identity, civilian_people=result['civilian_people'],
                institutional_people=result['staff_people']); model['summaries'].append(summary)
            audit_file = target / (identity + '.npz'); shutil.copyfile(origin / 'fields.npz', audit_file)
            fields[identity] = str(audit_file.relative_to(DATA))
            rgb = np.empty((size, 3)); rgb[:] = [.84, .89, .94]; rgb[land.ravel()] = [.84, .83, .78]
            served = assignment > 0
            request = np.array([s['civilian_request_people'] for s in model['sites']])
            ratio = np.clip(np.divide(f['civilian'], request, out=np.zeros_like(request), where=request > 0), 0, 1)[assignment[served] - 1]
            rgb[served] = np.array([.89, .85, .76]) * (1 - ratio[:, None]) + np.array([.47, .66, .58]) * ratio[:, None]
            image = Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
            draw = ImageDraw.Draw(image); cell_px = meta['width'] / w
            for j, site in enumerate(model['sites']):
                xx, yy = (site['column'] + .5) * cell_px, (site['row'] + .5) * cell_px
                if not case['community_viable'][j]:
                    if site['marked']:draw.rectangle((xx-2, yy-2, xx+2, yy+2), outline='#222222')
                    continue
                radius = max(1.5, min(8, 1.2 + np.sqrt(total[j]) / 22))
                color = model['actors'][site['actor_index']]['color'] if site['actor_index'] >= 0 else '#59636b'
                draw.ellipse((xx-radius, yy-radius, xx+radius, yy+radius), fill=color, outline='white')
                if f['active'][j]:draw.point((xx, yy), fill='#111111')
            town_file = target / (identity + '_towns.webp'); image.save(town_file, lossless=True)
            note = ('Research scenario: the SAME cell population funds rural, civilian and institutional residents once. '
                'Moving people changes farm workers, production and rural meals before seasonal collection. Positive settlements pass source-food checks; '
                'unmet rural cereal needs remain explicit elsewhere. Reference population, diets, work and cohorts are assumptions, not an Earth size or sovereignty fit. '
                'Transport, sites and tracks are fixed to the exactly reproduced published reference. Other foods, complete household/draft work and mobile occupancy remain unresolved.')
            common = dict(value=identity, label=label, note=note, integrated_support=True, feedback_support=True)
            options['reach_towns'].append(dict(common, file=str(town_file.relative_to(DATA)), file_sha256=sha(town_file),
                items=[dict(color='#78a895', label='Local catchment: supported civilian request'),
                       dict(color='#59636b', label='Circles: same-budget residents; dark centre: conditional cohort'),
                       dict(color='#d6d4c7', label='Unsupported/unassigned; actual communities unknown')],
                caption='Cell people, workers and grain are coupled; this is a conditional local cereal scenario.'))
            counts = pop[masks[i]]; best = counts.max(0); winner = counts.argmax(0)
            rgb[:] = [.84, .89, .94]; alpha = best / 12 * .8
            rgb[land.ravel()] = np.array([.89, .87, .81]) * (1 - alpha[:, None]) + colors[winner] * alpha[:, None]
            overlap = (counts > 0).sum(0) > 1; indices = np.flatnonzero(land); pattern = ((indices // w + indices % w) % 5 == 0) & overlap
            rgb[indices[pattern]] = rgb[indices[pattern]] * .65 + .35
            reach_file = target / (identity + '_reach.webp')
            Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST).save(reach_file, lossless=True)
            options['reach_defacto'].append(dict(common, file=str(reach_file.relative_to(DATA)), file_sha256=sha(reach_file),
                items=[dict(color=a['color'], label=a['name']) for a in model['actors']] + [dict(color='#e3decf', label='No modeled reach; local organization unscored')],
                caption='Same audited resident cohorts select seasonal two-way sources. Access is not proof of allegiance or sovereignty.'))
        payload = target / 'settled_reach.json.gz'
        payload.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        combined = np.concatenate([ref[None], masks]); binary = target / 'settled_reach.bin.gz'
        binary.write_bytes(gzip.compress(prefix + combined.astype('<u2').tobytes(), mtime=0))
        packets[mode] = dict(shape=list(land.shape), cell_px=meta['width']/w, land_cells=int(land.sum()),
            masks_shape=list(combined.shape), offsets=old['offsets'], raw_bytes=len(prefix)+combined.nbytes,
            payload=str(payload.relative_to(DATA)), payload_sha256=sha(payload), binary=str(binary.relative_to(DATA)),
            binary_sha256=sha(binary), parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'],
            expected_harvest_binary_sha256=old['expected_harvest_binary_sha256'], options=options, fields=fields)
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest:raise ValueError('Original atlas packet modified: ' + path)
    write(DATA / 'settlement_feedback.json', dict(version=1, status='optional_coupled_cereal_research', packets=packets,
        producer_sha256=sha(Path(__file__)), original_packets_unchanged=True, default_adoption=False))
    html = DATA.parent / 'index.html'
    page = re.sub(r'<script src="settled-reach\.js"[^>]*></script>',
        '<script src="settled-reach.js" data-settled-reach-enabled data-settlement-feedback-enabled></script>', html.read_text())
    html.write_text(page)
    shutil.copyfile(ROOT / 'atlas/settled-reach.js', DATA.parent / 'settled-reach.js')
    shutil.copyfile(ROOT / 'atlas/evidence.js', DATA.parent / 'evidence.js')
    write(OUT / 'atlas_publication.json', dict(status='published_optional_scenarios', manifest_sha256=sha(DATA/'settlement_feedback.json'),
        original_packets_sha256=preserved, publisher_sha256=sha(Path(__file__)), modes=['reach_towns','reach_defacto'],
        defaults_unchanged=True, cases_per_climate=4))
    print('Published eight coupled scenarios inside the existing settlement/reach selectors; original packets/defaults preserved.')


if __name__ == '__main__':main()
