"""Add the reviewed market-hierarchy scenarios to the atlas as a separate optional family.

Existing packets, manifests and defaults stay byte-identical. The frontend
loads data/settlement_market.json only on the active Earth atlas.
"""
import copy
import gzip
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_hierarchy_reach import BASE, COHORT, DATA, OUT, TWO_DAY, scenarios
from settlement_locations_earth import sha, write
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import permanent_food_ceiling

DEFAULT_SETTLEMENTS = 'market6_50_capped'
AUDIT = ('total', 'civilian', 'staff', 'active', 'draw', 'own_catchment_residents', 'forwarded_in_residents', 'passed_people',
    'parent', 'depth', 'children', 'leg_days', 'leg_retention', 'chain_retention', 'arrivals', 'local_arrivals', 'leg_loss',
    'budget', 'upper', 'source_supported', 'base_total', 'base_active')


def town_image(meta, land, assignment, sites, actors, total, viable, active, ratio, parent):
    h, w = land.shape; rgb = np.empty((land.size, 3)); rgb[:] = [.84, .89, .94]; rgb[land.ravel()] = [.84, .83, .78]
    served = assignment > 0; share = ratio[assignment[served] - 1]
    rgb[served] = np.array([.89, .85, .76]) * (1 - share[:, None]) + np.array([.47, .66, .58]) * share[:, None]
    image = Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image); cell_px = meta['width'] / w
    centre = [((s['column'] + .5) * cell_px, (s['row'] + .5) * cell_px) for s in sites]
    for j, q in enumerate(parent):                      # forwarding legs first, so circles sit on top
        if q >= 0 and total[j] > 0:draw.line([centre[j], centre[q]], fill='#3b4248', width=1)
    for j in np.argsort(total):                         # largest towns drawn last
        site = sites[j]; xx, yy = centre[j]
        if not viable[j]:
            if site['marked']:draw.rectangle((xx - 2, yy - 2, xx + 2, yy + 2), outline='#222222')
            continue
        radius = max(1.5, min(8, 1.2 + np.sqrt(total[j]) / 22))
        color = actors[site['actor_index']]['color'] if site['actor_index'] >= 0 else '#59636b'
        draw.ellipse((xx - radius, yy - radius, xx + radius, yy + radius), fill=color, outline='white')
        if active[j]:draw.point((xx, yy), fill='#111111')
    return image


def main():
    parent_manifest = json.loads((DATA / 'settled_reach.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    review = json.loads((OUT / 'reach_review.json').read_text())
    if review['status'] != 'passed' or any(sha(OUT / f'{m}_reach.json') != d for m, d in review['results_sha256'].items()):
        raise ValueError('Current hierarchy reach review required')
    for family in (TWO_DAY, OUT, COHORT):
        checked = json.loads((family / 'review.json').read_text()); replay = json.loads((family / 'replay.json').read_text())
        if checked['status'] != 'passed' or replay['status'] != 'passed':raise ValueError('Scenario review and replay required')
        for path, digest in checked['results_sha256'].items():
            if sha(ROOT / path) != digest:raise ValueError('Stale scenario review: ' + path)
        for path, digest in replay['byte_exact_files'].items():
            if sha(family / path) != digest:raise ValueError('Stale scenario replay: ' + path)
    guard = sorted(p for p in DATA.rglob('*') if p.is_file() and 'market' not in p.relative_to(DATA).parts
                   and p.name != 'settlement_market.json')
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in guard}
    packets = {}; pop = np.array([n.bit_count() for n in range(4096)])
    for mode in ('raw', 'corrected'):
        old = parent_manifest['packets'][mode]; folder = DATA / ('corrected' if mode == 'corrected' else '')
        original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
        x = dict(np.load(BASE / f'{mode}_inputs.npz')); land = x['land']; h, w = land.shape; size = land.size
        reach = json.loads((OUT / f'{mode}_reach.json').read_text()); masks = np.load(OUT / f'{mode}_reach.npz')['masks']
        ref = np.load(BASE / f'{mode}_footprints.npz')['reference']
        target = DATA / 'market' / mode; target.mkdir(parents=True, exist_ok=True)
        model = dict(version=1, atlas='earth_fit', climate=mode, shape=list(land.shape), sites=original['sites'],
            actors=original['actors'], specification=original['specification'], labour_specification=original['labour_specification'],
            cases=[copy.deepcopy(original['cases'][0])], summaries=[copy.deepcopy(original['summaries'][0])],
            scope='Market-hierarchy research scenarios on the original coupled cell people/work/cereal ledger. Share and range are scenarios; sizes are relative.')
        options = {'reach_towns': [], 'reach_defacto': []}; fields = {}
        colors = np.array([to_rgb(a['color']) for a in model['actors']])
        with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:prefix = f.read(old['offsets']['masks'])
        assignment = np.frombuffer(prefix, '<u2', count=size, offset=old['offsets']['catchments'])
        request = np.array([s['civilian_request_people'] for s in model['sites']])
        for i, c in enumerate(scenarios(mode)):
            result = json.loads((c['folder'] / 'results.json').read_text()); f = dict(np.load(c['folder'] / 'fields.npz'))
            if sha(c['folder'] / 'fields.npz') != result['fields_sha256']:raise ValueError('Scenario fields changed')
            total = f['total']; arrivals = f['arrivals']; need = np.broadcast_to(total * 2500 * 365 / 12, arrivals.shape)
            food = periodic_food_year(arrivals, need, total * 2500 * 90, loss_fraction_year=.05, step_days=365 / 12, record=True)
            np.testing.assert_allclose(food.consumed, f['town_consumed'], rtol=1e-11, atol=1e-4)
            share = round(100 * c['share'])
            rule = c.get('rule')
            label = f"Market hierarchy · {c['range_days']}-day legs / {share}% passed up" + (
                ' above the cohort' if rule == 'excess' else ', cohort kept' if rule == 'capped' else '') + ' · research'
            viable = f['civilian'] >= 50
            case = dict(id=c['id'], label=label, feedback_coupled=True, food_constrained=True, labour_constrained=True,
                hours_worker_year=600, harvest_days=30, transfer_fraction=.075,
                food_ceiling_people=permanent_food_ceiling(arrivals).tolist(), civilian_people=f['civilian'].tolist(),
                institutional_people=f['staff'].tolist(), institutional_active=f['active'].tolist(),
                community_viable=viable.tolist(), resident_budget_people=f['budget'].tolist(),
                source_supported=f['source_supported'].tolist(), monthly_arrivals_kcal=arrivals.T.tolist(),
                monthly_need_kcal=need.T.tolist(), stock_path_kcal=food.stock_path.T.tolist(),
                work_summary=dict(production_retained=result['local_production_retained'], scenario_workers=float(f['rural'].sum() * .4)),
                rural_ledger=dict(unmet_kcal=result['local_rural_unmet_kcal'], deficit_origins=result['local_rural_deficit_origins'],
                    outside_unmet_kcal=result['outside_rural_unmet_kcal']), source_gate=result['source_gate'],
                market_hierarchy=dict(range_days=c['range_days'], forward_share=c['share'], distance_scaled=result['legs']['distance_scaled'],
                    towns_with_parent=result['forest']['towns_with_parent'], parent_site=f['parent'].tolist(),
                    own_catchment_people=f['own_catchment_residents'].tolist(), forwarded_in_people=f['forwarded_in_residents'].tolist(),
                    passed_up_people=f['passed_people'].tolist(), leg_days=f['leg_days'].tolist(), cohort_rule=rule,
                    gini=result['shape_metrics']['all_places']['gini'], shape_within_reference_band=result['shape_supported']),
                empirical_resident_size_fit=False, whole_world_food_supported=False)
            model['cases'].append(case)
            summary = dict(reach['summaries'][i], civilian_people=result['civilian_people'], institutional_people=result['staff_people'])
            assert summary['id'] == c['id']; model['summaries'].append(summary)
            audit = target / (c['id'] + '.npz'); np.savez_compressed(audit, **{k: f[k] for k in AUDIT}); fields[c['id']] = str(audit.relative_to(DATA))
            ratio = np.clip(np.divide(f['draw'], request, out=np.zeros_like(request), where=request > 0), 0, 1)
            town_file = target / (c['id'] + '_towns.webp')
            town_image(meta, land, assignment, model['sites'], model['actors'], total, viable, f['active'], ratio, f['parent']).save(town_file, lossless=True)
            largest = result['largest_towns'][0]
            protect = (' A town that can hold a cohort passes only from what it holds above 150 residents.' if rule == 'excess' else
                       ' A town that can hold a cohort never passes so much that it falls below 150 residents.' if rule == 'capped' else '')
            note = (f"Research scenario: every town passes {share}% of the residents and collected grain it holds to the largest same-actor town it can reach "
                f"within {c['range_days']} days each way all year.{protect} {result['forest']['towns_with_parent']:,} of {result['forest']['towns']:,} towns have such a market; "
                f"the largest town holds {largest['residents']:,.0f} residents. People are counted once and every forwarding leg loses grain. "
                'Built on the original coupled cell scenario (600 h, 7.5%), not the later dispatch versions. Share and range are scenarios, not calibrated values; '
                'sizes are relative and imply no historical city size, date or sovereignty. Other foods, household and draft work and mobile occupancy remain unresolved.')
            common = dict(value=c['id'], label=label, note=note, integrated_support=True, market_support=True)
            towns = dict(common)
            if c['id'] == DEFAULT_SETTLEMENTS:                 # owner decision of 12 November 2026
                towns.update(label=f"Default · market hierarchy with cohorts kept ({c['range_days']}-day legs, {share}%) · development-fitted",
                    note='Default Settlements map since 12 November 2026 by owner decision: development-fitted, not prospectively validated. ' + note)
            options['reach_towns'].append(dict(towns, file=str(town_file.relative_to(DATA)), file_sha256=sha(town_file),
                items=[dict(color='#78a895', label='Local catchment: share of its civilian request drawn'),
                       dict(color='#59636b', label='Circles: residents after forwarding; dark centre: conditional cohort'),
                       dict(color='#3b4248', label='Lines: a town passing its share to a larger market'),
                       dict(color='#d6d4c7', label='Unsupported/unassigned; actual communities unknown')],
                caption='Same people and grain as the coupled scenario, redistributed up declared market links; a conditional cereal scenario.'))
            counts = pop[masks[i]]; best = counts.max(0); winner = counts.argmax(0)
            rgb = np.empty((size, 3)); rgb[:] = [.84, .89, .94]; alpha = best / 12 * .8
            rgb[land.ravel()] = np.array([.89, .87, .81]) * (1 - alpha[:, None]) + colors[winner] * alpha[:, None]
            overlap = (counts > 0).sum(0) > 1; indices = np.flatnonzero(land); pattern = ((indices // w + indices % w) % 5 == 0) & overlap
            rgb[indices[pattern]] = rgb[indices[pattern]] * .65 + .35
            reach_file = target / (c['id'] + '_reach.webp')
            Image.fromarray(np.rint(rgb.reshape(h, w, 3) * 255).astype('u1')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST).save(reach_file, lossless=True)
            options['reach_defacto'].append(dict(common, file=str(reach_file.relative_to(DATA)), file_sha256=sha(reach_file),
                items=[dict(color=a['color'], label=a['name']) for a in model['actors']] + [dict(color='#e3decf', label='No modeled reach; local organization unscored')],
                caption='Cohorts left after forwarding select seasonal two-way sources. Small towns that fall below the cohort threshold stop being sources. Access is not proof of allegiance or sovereignty.'))
        payload = target / 'settled_reach.json.gz'
        payload.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        combined = np.concatenate([ref[None], masks]); binary = target / 'settled_reach.bin.gz'
        binary.write_bytes(gzip.compress(prefix + combined.astype('<u2').tobytes(), mtime=0))
        packets[mode] = dict(shape=list(land.shape), cell_px=meta['width'] / w, land_cells=int(land.sum()),
            masks_shape=list(combined.shape), offsets=old['offsets'], raw_bytes=len(prefix) + combined.nbytes,
            payload=str(payload.relative_to(DATA)), payload_sha256=sha(payload), binary=str(binary.relative_to(DATA)),
            binary_sha256=sha(binary), parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'],
            expected_harvest_binary_sha256=old['expected_harvest_binary_sha256'], options=options, fields=fields)
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest:raise ValueError('Existing atlas packet modified: ' + path)
    write(DATA / 'settlement_market.json', dict(version=1, status='optional_market_hierarchy_research', packets=packets,
        producer_sha256=sha(Path(__file__)), existing_packets_unchanged=True, default_adoption=True,
        default_settlements=DEFAULT_SETTLEMENTS, default_basis='owner decision; development-fitted, not prospectively validated',
        default_decision='calibration/settlement_default_adoption_20261112/decision.json'))
    page = DATA.parent / 'index.html'; html = page.read_text()
    if 'data-settlement-market-enabled' not in html:
        assert html.count('data-network-duty-visits-enabled') == 1
        html = html.replace('data-network-duty-visits-enabled', 'data-network-duty-visits-enabled data-settlement-market-enabled')
    page.write_text(html)
    for name in ('settled-reach.js', 'evidence.js'):shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_optional_market_hierarchy_scenarios', manifest_sha256=sha(DATA / 'settlement_market.json'),
        publisher_sha256=sha(Path(__file__)), existing_data_files_unchanged=len(preserved), modes=['reach_towns', 'reach_defacto'],
        defaults_unchanged=False, default_settlements=DEFAULT_SETTLEMENTS, reach_default_unchanged=True,
        cases_per_climate=len(scenarios('raw'))))
    print('Published', 2 * len(scenarios('raw')), 'market-hierarchy scenarios as a separate optional family; existing packets preserved; Settlements default is', DEFAULT_SETTLEMENTS)


if __name__ == '__main__':main()
