"""Independently check exported provider-year point masks,pixels,roles and CSVs."""
import csv
import gzip
import io
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageColor

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
DATA = ROOT / 'atlases/earth_fit/data'


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    publication = json.loads((OUT / 'atlas_publication.json').read_text()); manifest = json.loads((DATA / 'network_visit_year_complete.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert publication['manifest_sha256'] == sha(DATA / 'network_visit_year_complete.json')
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256'], **result['unchanged_schedule_sha256'], **publication['producers'], **publication['exported_files_sha256']}.items(): assert sha(ROOT / path) == digest, path
    fields = dict(np.load(OUT / 'fields.npz')); funded = dict(np.load(PARENT / 'fields.npz'))
    old_manifest = json.loads((DATA / 'network_duty_visits.json').read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    reviewed = []; checked_points = checked_pixels = 0
    for mode, packet in manifest['packets'].items():
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(PARENT / f'{mode}_paths.npz')); previous = old_manifest['packets'][mode]
        source_model = json.loads(gzip.decompress((DATA / previous['payload']).read_bytes())); old_binary = gzip.decompress((DATA / previous['binary']).read_bytes())
        assert sha(DATA / packet['payload']) == packet['payload_sha256'] and sha(DATA / packet['binary']) == packet['binary_sha256']
        model = json.loads(gzip.decompress((DATA / packet['payload']).read_bytes())); raw = gzip.decompress((DATA / packet['binary']).read_bytes())
        assert len(raw) == packet['raw_bytes'] and model['climate'] == mode and model['shape'] == list(x['land'].shape)
        assert packet['parent_payload_sha256'] == parent['packets'][mode]['payload_sha256']
        assert packet['expected_harvest_fingerprint'] == parent['packets'][mode]['expected_harvest_fingerprint']
        assert raw[:packet['offsets']['masks']] == old_binary[:previous['offsets']['masks']]
        actors = model['actors']; count = len(actors); land = int(x['land'].sum()); size = count * land
        masks = np.frombuffer(raw, '<u2', offset=packet['offsets']['masks']).reshape(len(model['cases']), count, land)
        old_reference = np.frombuffer(old_binary, '<u2', offset=previous['offsets']['masks'], count=size).reshape(count, land)
        np.testing.assert_array_equal(masks[0], old_reference)
        np.testing.assert_array_equal(model['point_target_nodes'], paths['target_nodes'])
        assert model['point_requested_targets'] == source_model['point_requested_targets'] and not packet['options']['reach_towns']
        names = {a['name']: i for i, a in enumerate(actors)}; assert len(names) == count
        target_lookup = {int(node): j for j, node in enumerate(paths['target_nodes'])}; positions = np.searchsorted(np.flatnonzero(x['land']), paths['target_nodes'])
        for row in (r for r in result['rows'] if r['climate'] == mode):
            key = row['key']; ident = f'yearvisits{row["hours_worker_year"]}_crew{row["crew"]}'
            k = next(i for i, c in enumerate(model['cases']) if c['id'] == ident); c = model['cases'][k]
            prior = next(c for c in source_model['cases'] if c['id'] == f'visits{row["hours_worker_year"]}_crew{row["crew"]}')
            for name in ('civilian_people', 'institutional_people', 'resident_budget_people', 'monthly_arrivals_kcal', 'monthly_need_kcal', 'stock_path_kcal', 'source_supported'):
                assert c[name] == prior[name], (ident, name)
            np.testing.assert_array_equal(c['institutional_active'], fields[key + '__mandatory_complete'])
            np.testing.assert_array_equal(c['year_schedule']['policy'], fields[key + '__policy'])
            np.testing.assert_array_equal(c['year_schedule']['mandatory_complete'], fields[key + '__mandatory_complete'])
            for name in ('work_hours', 'max_worker_hours', 'max_calendar_end'):
                np.testing.assert_array_equal(c['year_schedule'][name], fields[key + '__provider_' + name].T)
            for name, field in [('reserved_hours', 'provider_reserved_patrol_hours'), ('used_hours', 'provider_visit_hours'), ('unused_hours', 'provider_unused_patrol_hours'), ('completed_by_provider', 'provider_completed_visits')]:
                np.testing.assert_array_equal(c['point_visits'][name], fields[key + '__' + field].T)
            assert c['point_visits']['completed'] == row['qualified_visits'] and c['point_visits']['calendar_unqualified'] == row['calendar_unqualified']
            np.testing.assert_array_equal(c['dispatch_work']['collection_hours'], fields[key + '__provider_collection_hours'].T)
            np.testing.assert_array_equal(c['dispatch_work']['unused_hours'], fields[key + '__provider_unused_staff_hours'].T)
            served = fields[key + '__served']; expected = np.zeros((count, land), 'u2')
            point_masks = np.zeros((count, len(paths['target_nodes'])), 'u2')
            for month in range(12): point_masks |= served[month].astype('u2') << month
            expected[:, positions] = point_masks; np.testing.assert_array_equal(masks[k], expected)
            option = next(o for o in packet['options']['reach_defacto'] if o['value'] == ident)
            assert sha(DATA / option['file']) == option['file_sha256'] and option['year_complete_visit_support']
            with Image.open(DATA / option['file']) as image:
                assert image.size == (meta['width'], meta['height']); image = image.convert('RGB')
                visits = served.sum(axis=0)
                for j in np.flatnonzero(visits.any(axis=0)):
                    a = int(np.argmax(visits[:, j])); overlap = int((visits[:, j] > 0).sum())
                    color = (255, 255, 255) if overlap > 1 else ImageColor.getrgb(actors[a]['color'])
                    yy, xx = divmod(int(paths['target_nodes'][j]), x['land'].shape[1])
                    pixel = (int((xx + .5) * packet['cell_px']), int((yy + .5) * packet['cell_px']))
                    assert image.getpixel(pixel) == color, (ident, j, pixel)
                    checked_pixels += 1
            assert (DATA / packet['fields'][ident]).read_bytes() == (OUT / 'fields.npz').read_bytes()
            exported = list(csv.DictReader(io.StringIO(gzip.decompress((DATA / packet['point_csv'][ident]).read_bytes()).decode())))
            assert len(exported) == int(fields[mode + '__demand'].sum()); seen = set(); total = 0
            status = [('qualified_bin_mask', 'served'), ('calendar_unqualified_bin_mask', 'calendar_unqualified'), ('route_unreachable_bin_mask', 'route_unreachable'),
                ('provider_work_unavailable_bin_mask', 'provider_work_unavailable'), ('capacity_unmet_bin_mask', 'capacity_unmet'), ('original_funded_bin_mask', 'original_funded'), ('baseline_twelve_bin_mask', 'baseline_served')]
            for point in exported:
                a = names[point['actor']]; node = int(point['target_grid_node']); j = target_lookup[node]
                assert (a, j) not in seen and fields[mode + '__demand'][a, j]; seen.add((a, j))
                yy, xx = divmod(node, x['land'].shape[1]); assert (int(point['target_row']), int(point['target_column'])) == (yy, xx)
                assert point['scenario'] == ident and point['climate'] == mode and int(point['requested_bins']) == 12
                for column, field in status:
                    value = sum((1 << month) for month in range(12) if fields[key + '__' + field][month, a, j])
                    assert int(point[column]) == value, (ident, node, column)
                assert sum(int(point[name]) for name, _ in status[:5]) == 4095
                assert int(point['baseline_twelve_bin_mask']) & ~int(point['qualified_bin_mask']) == 0
                assert int(point['qualified_bins']) == int(point['qualified_bin_mask']).bit_count(); total += int(point['qualified_bins'])
                source = [int(funded[key + '__provider_for_target'][month, a, j]) if funded[key + '__served'][month, a, j] else -1 for month in range(12)]
                assert list(map(int, point['original_funded_provider_by_bin'].split('|'))) == source
                assert list(map(int, point['provider_year_policy_by_bin'].split('|'))) == [int(fields[key + '__policy'][s]) if s >= 0 else -1 for s in source]
                assert list(map(int, point['provider_mandatory_year_flag_by_bin'].split('|'))) == [int(fields[key + '__mandatory_complete'][s]) if s >= 0 else 0 for s in source]
            assert total == row['qualified_visits']; checked_points += len(exported); reviewed.append(key)
            print('Independent provider-year masks,pixels,conditional cohorts and point CSV passed:', key, flush=True)
    assert len(reviewed) == 8
    write(OUT / 'export_review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), manifest_sha256=sha(DATA / 'network_visit_year_complete.json'),
        reviewer_sha256=sha(Path(__file__)), cases=reviewed, checked_point_rows=checked_points, checked_visited_point_pixels=checked_pixels,
        unchanged_conditional_resident_and_food_ledgers=True, exact_policy_and_worker_fields=True, exact_actor_point_masks=True,
        baseline_mask_inclusion=True, full_five_way_request_partitions=True, original_maps_and_schedules_unchanged=True,
        limits='Pixel symbols and point tasks only;not held blocks,annual food validation,observed roles or authority.'))


if __name__ == '__main__': main()
