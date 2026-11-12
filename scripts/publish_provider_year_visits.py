"""Add distinct optional point maps backed by coherent provider-year calendars."""
import argparse
import copy
import csv
import gzip
import io
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_network_duty_visits import point_image

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
DATA = ROOT / 'atlases/earth_fit/data'


def main(export=DATA, activate=True):
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text()); replay = json.loads((OUT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_provider_year_visits.py') and len(review['cases']) == 8
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_schedule_sha256'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in replay['byte_exact_files'].items(): assert sha(OUT / name) == digest
    f = dict(np.load(OUT / 'fields.npz')); original_fields = dict(np.load(PARENT / 'fields.npz'))
    parent = json.loads((DATA / 'settled_reach.json').read_text()); old = json.loads((DATA / 'network_duty_visits.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text()); packets = {}
    bits = (1 << np.arange(12, dtype='u2'))[:, None, None]
    for mode in ('raw', 'corrected'):
        p, previous_packet = parent['packets'][mode], old['packets'][mode]
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(PARENT / f'{mode}_paths.npz'))
        original = json.loads(gzip.decompress((DATA / previous_packet['payload']).read_bytes())); model = copy.deepcopy(original)
        model['cases'] = [copy.deepcopy(original['cases'][0])]; model['summaries'] = [copy.deepcopy(original['summaries'][0])]
        model['scope'] = 'Qualified point tasks from one checked calendar per provider/year;necessary twelve-bin delivery schedule,not full annual food validation,observed roles or territory.'
        binary_old = gzip.decompress((DATA / previous_packet['binary']).read_bytes()); prefix = binary_old[:p['offsets']['masks']]
        reference = np.frombuffer(binary_old, '<u2', offset=p['offsets']['masks'], count=len(model['actors']) * int(x['land'].sum())).reshape(len(model['actors']), -1)
        positions = np.searchsorted(np.flatnonzero(x['land']), paths['target_nodes']); masks = [reference]
        target = export / 'year_complete' / mode; target.mkdir(parents=True, exist_ok=True); options = []; grids = {}; point_csv = {}
        for row in (r for r in result['rows'] if r['climate'] == mode):
            key = row['key']; ident = f'yearvisits{row["hours_worker_year"]}_crew{row["crew"]}'
            previous_id = f'visits{row["hours_worker_year"]}_crew{row["crew"]}'
            c = copy.deepcopy(next(c for c in original['cases'] if c['id'] == previous_id)); summary = copy.deepcopy(next(s for s in original['summaries'] if s['id'] == previous_id))
            served = f[key + '__served']; policy = f[key + '__policy']; complete = f[key + '__mandatory_complete']; budget = f[key + '__provider_reserved_patrol_hours']
            c.update(id=ident, label=f'Complete-year collection schedule · {row["hours_worker_year"]}h / crew {row["crew"]}', institutional_active=complete.tolist(),
                year_schedule=dict(policy=policy.tolist(), mandatory_complete=complete.tolist(),
                    work_hours=f[key + '__provider_work_hours'].T.tolist(), max_worker_hours=f[key + '__provider_max_worker_hours'].T.tolist(), max_calendar_end=f[key + '__provider_max_calendar_end'].T.tolist()))
            c['point_visits'].update(completed=row['qualified_visits'], calendar_unqualified=row['calendar_unqualified'],
                reserved_hours=budget.T.tolist(), used_hours=f[key + '__provider_visit_hours'].T.tolist(), unused_hours=f[key + '__provider_unused_patrol_hours'].T.tolist(),
                completed_by_provider=f[key + '__provider_completed_visits'].T.tolist())
            c['dispatch_work']['collection_hours'] = f[key + '__provider_collection_hours'].T.tolist()
            c['dispatch_work']['unused_hours'] = f[key + '__provider_unused_staff_hours'].T.tolist()
            summary.update(id=ident, active_sources=row['qualified_providers'], point_task_only=True,
                area_weighted_access_scope='Inherited parent potential-access reference;not visited territory or a calendar-qualified area estimate.')
            for a in row['actors']: summary['actors'][a['actor_index']]['active_sources'] = a['qualified_providers']
            model['cases'].append(c); model['summaries'].append(summary)
            point_masks = np.sum(served.astype('u2') * bits, axis=0).astype('u2'); grid = np.zeros_like(reference); grid[:, positions] = point_masks; masks.append(grid)
            image = target / (ident + '.webp'); point_image(x, paths, served, model['actors'], meta).save(image, lossless=True)
            status = {name: np.sum(f[key + '__' + name].astype('u2') * bits, axis=0).astype('u2') for name in ('served', 'calendar_unqualified', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet', 'original_funded', 'baseline_served')}
            buffer = io.StringIO(newline=''); writer = csv.writer(buffer)
            writer.writerow(['climate', 'scenario', 'actor', 'target_grid_node', 'target_row', 'target_column', 'requested_bins', 'qualified_bins',
                'qualified_bin_mask', 'calendar_unqualified_bin_mask', 'route_unreachable_bin_mask', 'provider_work_unavailable_bin_mask', 'capacity_unmet_bin_mask',
                'original_funded_bin_mask', 'baseline_twelve_bin_mask', 'original_funded_provider_by_bin', 'provider_year_policy_by_bin', 'provider_mandatory_year_flag_by_bin', 'scope'])
            for actor, j in zip(*np.where(f[mode + '__demand'])):
                node = int(paths['target_nodes'][j]); yy, xx = divmod(node, x['land'].shape[1])
                funded = original_fields[key + '__served'][:, actor, j]; provider = np.where(funded, original_fields[key + '__provider_for_target'][:, actor, j], -1)
                policies = [int(policy[s]) if s >= 0 else -1 for s in provider]; flags = [int(complete[s]) if s >= 0 else 0 for s in provider]
                writer.writerow([mode, ident, model['actors'][actor]['name'], node, yy, xx, 12, int(served[:, actor, j].sum()),
                    *[int(status[name][actor, j]) for name in ('served', 'calendar_unqualified', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet', 'original_funded', 'baseline_served')],
                    '|'.join(map(str, provider.tolist())), '|'.join(map(str, policies)), '|'.join(map(str, flags)),
                    'necessary provider-year delivery schedule;not daily food,full annual food validation,observed roles or territory'])
            csv_path = target / (ident + '_points.csv.gz'); csv_path.write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0)); point_csv[ident] = str(csv_path.relative_to(export))
            grids[ident] = 'year_complete/fields.npz'
            options.append(dict(value=ident, label=c['label'], integrated_support=True, year_complete_visit_support=True, file=str(image.relative_to(export)), file_sha256=sha(image),
                note='One checked calendar per provider across all twelve mandatory collection/service bins. Every baseline gated task retained. Supplied availability;necessary delivery schedule only,not full annual food validation,actual roles or authority.',
                caption='Dots:qualified target-point visits from coherent provider-year calendars. Size reflects bins;white centres show actor overlap. Background and intervening land remain unscored.',
                items=[dict(color=a['color'], label=a['name']) for a in model['actors']] + [dict(color='#e3decf', label='Unscored background;no territorial claim')]))
        payload = target / 'settled_reach.json.gz'; binary = target / 'settled_reach.bin.gz'; combined = np.stack(masks)
        payload.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        binary.write_bytes(gzip.compress(prefix + combined.astype('<u2').tobytes(), mtime=0))
        packets[mode] = dict(shape=list(x['land'].shape), cell_px=meta['width'] / x['land'].shape[1], land_cells=int(x['land'].sum()), masks_shape=list(combined.shape),
            offsets=p['offsets'], raw_bytes=len(prefix) + combined.nbytes, payload=str(payload.relative_to(export)), payload_sha256=sha(payload),
            binary=str(binary.relative_to(export)), binary_sha256=sha(binary), parent_payload_sha256=p['payload_sha256'], expected_harvest_fingerprint=p['expected_harvest_fingerprint'],
            expected_harvest_binary_sha256=p['expected_harvest_binary_sha256'], options={'reach_towns': [], 'reach_defacto': options}, fields=grids, point_csv=point_csv)
    shutil.copyfile(OUT / 'fields.npz', export / 'year_complete/fields.npz')
    manifest = export / 'network_visit_year_complete.json'
    write(manifest, dict(version=1, status='optional_necessary_provider_year_delivery_schedules', packets=packets, default_adoption=False, full_annual_food_validation=False))
    for path, digest in {**result['unchanged_map_sha256'], **result['unchanged_schedule_sha256']}.items(): assert sha(ROOT / path) == digest, path
    if not activate:
        print('Fresh provider-year map exports generated without changing the atlas.')
        return
    page = DATA.parent / 'index.html'; html = page.read_text()
    if 'data-network-visit-year-complete-enabled' not in html:
        assert 'data-network-duty-visits-enabled' in html
        html = html.replace('data-network-duty-visits-enabled', 'data-network-duty-visits-enabled data-network-visit-year-complete-enabled', 1)
    page.write_text(html)
    for name in ('settled-reach.js', 'evidence.js'): shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_optional_provider_year_point_visits', manifest_sha256=sha(manifest), scenarios=8,
        producers={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'scripts/publish_network_duty_visits.py')},
        exported_files_sha256={str(p.relative_to(ROOT)): sha(p) for p in (DATA / 'year_complete').rglob('*') if p.is_file()},
        original_maps_unchanged=len(result['unchanged_map_sha256']), original_schedules_unchanged=len(result['unchanged_schedule_sha256']), defaults_unchanged=True,
        necessary_delivery_gate_only=True))
    print('Published eight optional Complete-year collection schedule point maps.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out-data', type=Path)
    args = parser.parse_args(); main(args.out_data or DATA, activate=args.out_data is None)
