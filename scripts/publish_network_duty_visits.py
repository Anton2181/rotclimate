"""Add optional funded POINT visits to the existing supply-reach selector."""
import copy
import csv
import gzip
import io
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from build_network_duty_visits import OUT, PARENT

DATA = ROOT / 'atlases/earth_fit/data'


def point_image(x, paths, served, actors, meta):
    h, w = x['land'].shape; rgb = np.full((h, w, 3), [214, 227, 240], 'u1'); rgb[x['land']] = [227, 222, 207]
    image = Image.fromarray(rgb).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image); scale = meta['width'] / w
    bins = served.sum(axis=0); best = bins.max(axis=0); who = bins.argmax(axis=0)
    for j in np.flatnonzero(best):
        row, col = divmod(int(paths['target_nodes'][j]), w); px, py = (col + .5) * scale, (row + .5) * scale
        color = actors[int(who[j])]['color']; radius = .55 + .75 * best[j] / 12
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)
        if (bins[:, j] > 0).sum() > 1: draw.point((px, py), fill='white')
    return image


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text()); fields = dict(np.load(OUT / 'fields.npz'))
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_network_duty_visits.py')
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in replay['byte_exact_files'].items(): assert sha(OUT / name) == digest
    parent = json.loads((DATA / 'settled_reach.json').read_text()); seeded = json.loads((DATA / 'settlement_dispatch_seeded.json').read_text())
    meta = json.loads((DATA / 'atlas.json').read_text()); packets = {}
    for mode in ('raw', 'corrected'):
        p = parent['packets'][mode]; x = dict(np.load(PARENT / f'{mode}_inputs.npz')); paths = dict(np.load(OUT / f'{mode}_paths.npz'))
        original = json.loads(gzip.decompress((DATA / seeded['packets'][mode]['payload']).read_bytes()))
        model = copy.deepcopy(original); model['cases'] = [copy.deepcopy(original['cases'][0])]; model['summaries'] = [copy.deepcopy(original['summaries'][0])]
        model['point_target_nodes'] = paths['target_nodes'].tolist()
        model['point_requested_targets'] = [paths['target_nodes'][v > 0].tolist() for v in paths['target_reference_masks']]
        model['scope'] = 'Conditional walking point visits using the SAME reserved patrol hours;not whole-block territory,observed demand or authority.'
        with gzip.open(DATA / seeded['packets'][mode]['binary'], 'rb') as stream: prefix = stream.read(p['offsets']['masks'])
        landnodes = np.flatnonzero(x['land']); positions = np.searchsorted(landnodes, paths['target_nodes'])
        mask_parts = [np.load(PARENT / f'{mode}_footprints.npz')['reference']]; options = []; grids = {}; point_csv = {}
        target = DATA / 'network_visits' / mode; target.mkdir(parents=True, exist_ok=True)
        for row in (r for r in result['rows'] if r['climate'] == mode):
            key = row['key']; ident = f'visits{row["hours_worker_year"]}_crew{row["crew"]}'
            c = copy.deepcopy(next(c for c in original['cases'] if c['id'] == f'dispatchv2{row["hours_worker_year"]}_120000_open'))
            summary = copy.deepcopy(next(s for s in original['summaries'] if s['id'] == c['id']))
            served = fields[key + '__served']; used = fields[key + '__used_hours']; budget = fields[key + '__reserved_hours']
            provider = fields[key + '__provider_for_target']; completed = np.zeros_like(used, dtype='i8')
            for month in range(12): completed[month] = np.bincount(provider[month][served[month]], minlength=len(x['nodes']))
            c.update(id=ident, label=f'Funded walking point visits · {row["hours_worker_year"]}h / crew {row["crew"]}',
                point_visits=dict(crew=row['crew'], requested=row['requested_visits'], completed=row['completed_visits'],
                    route_unreachable=row['route_unreachable'], provider_work_unavailable=row['provider_work_unavailable'], capacity_unmet=row['capacity_unmet'],
                    reserved_hours=budget.T.tolist(), used_hours=used.T.tolist(), unused_hours=fields[key + '__unused_hours'].T.tolist(),
                    completed_by_provider=completed.T.tolist(), actual_block_edge_km=result['target_metadata'][mode]['actual_block_edge_km']))
            # Actual unused staff now includes unspent patrol reservations.
            c['dispatch_work']['unused_hours'] = fields[key + '__whole_provider_unused_hours'].T.tolist()
            summary['id'] = ident; model['cases'].append(c); model['summaries'].append(summary)
            masks = np.zeros_like(mask_parts[0]); bitmasks = np.sum(served.astype('u2') * (1 << np.arange(12, dtype='u2'))[:, None, None], axis=0).astype('u2')
            masks[:, positions] = bitmasks; mask_parts.append(masks)
            image = target / (ident + '.webp'); point_image(x, paths, served, model['actors'], meta).save(image, lossless=True)
            buffer = io.StringIO(newline=''); writer = csv.writer(buffer)
            writer.writerow(['climate', 'scenario', 'actor', 'target_grid_node', 'target_row', 'target_column', 'requested_bins', 'completed_bins',
                'served_bin_mask', 'route_unreachable_bin_mask', 'provider_work_unavailable_bin_mask', 'capacity_unmet_bin_mask',
                'chosen_provider_indexes_by_bin', 'scope'])
            for actor, j in zip(*np.where(fields[mode + '__demand'])):
                masks_by_status = [int(np.sum(fields[key + '__' + status][:, actor, j].astype('u2') * (1 << np.arange(12, dtype='u2'))))
                    for status in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet')]
                node = int(paths['target_nodes'][j]); yy, xx = divmod(node, x['land'].shape[1])
                writer.writerow([mode, ident, model['actors'][actor]['name'], node, yy, xx, 12, int(served[:, actor, j].sum()), *masks_by_status,
                    '|'.join(map(str, provider[:, actor, j].tolist())), 'supplied point tasks;not observed visits or whole-block territory'])
            csv_path = target / (ident + '_points.csv.gz'); csv_path.write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))
            point_csv[ident] = str(csv_path.relative_to(DATA))
            # One complete eight-scenario physical packet, shared without duplication.
            grids[ident] = 'network_visits/fields.npz'
            options.append(dict(value=ident, label=c['label'], file=str(image.relative_to(DATA)), file_sha256=sha(image),
                integrated_support=True, network_visit_support=True,
                note='Whole walking visits spend only the already reserved patrol slice after collection and services. Supplied points,crew and monthly frequency;not observed patrols or territory.',
                caption='Dots: visited target points;size reflects completed bins. White centres: multiple actors. Blocks and intervening land are unscored.',
                items=[dict(color=a['color'], label=a['name']) for a in model['actors']] + [dict(color='#e3decf', label='Background is unscored;no territorial claim')]))
        payload = target / 'settled_reach.json.gz'; binary = target / 'settled_reach.bin.gz'; combined = np.stack(mask_parts)
        payload.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        binary.write_bytes(gzip.compress(prefix + combined.astype('<u2').tobytes(), mtime=0))
        packets[mode] = dict(shape=list(x['land'].shape), cell_px=meta['width'] / x['land'].shape[1], land_cells=int(x['land'].sum()),
            masks_shape=list(combined.shape), offsets=p['offsets'], raw_bytes=len(prefix) + combined.nbytes,
            payload=str(payload.relative_to(DATA)), payload_sha256=sha(payload), binary=str(binary.relative_to(DATA)), binary_sha256=sha(binary),
            parent_payload_sha256=p['payload_sha256'], expected_harvest_fingerprint=p['expected_harvest_fingerprint'],
            expected_harvest_binary_sha256=p['expected_harvest_binary_sha256'], options={'reach_towns': [], 'reach_defacto': options}, fields=grids, point_csv=point_csv)
    shutil.copyfile(OUT / 'fields.npz', DATA / 'network_visits/fields.npz')
    write(DATA / 'network_duty_visits.json', dict(version=1, status='optional_conditional_walking_point_tasks', packets=packets,
        default_adoption=False, producer_sha256=sha(Path(__file__))))
    for path, digest in result['unchanged_map_sha256'].items(): assert sha(ROOT / path) == digest
    page = DATA.parent / 'index.html'; html = page.read_text()
    if 'data-network-duty-visits-enabled' not in html: html = html.replace('data-settlement-dispatch-seeded-enabled', 'data-settlement-dispatch-seeded-enabled data-network-duty-visits-enabled')
    page.write_text(html)
    for name in ('settled-reach.js', 'evidence.js'): shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_conditional_point_visits', manifest_sha256=sha(DATA / 'network_duty_visits.json'),
        publisher_sha256=sha(Path(__file__)), scenarios=8, unchanged_map_files=len(result['unchanged_map_sha256']), defaults_unchanged=True,
        point_maps_not_territory=True, fields_sha256=sha(DATA / 'network_visits/fields.npz')))
    print('Published8 optional point-visit maps in the existing Supply-supported reach selector.')


if __name__ == '__main__': main()
