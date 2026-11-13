"""Publish release-3 settlements (Earth-tested positions + calibrated sizes) as the Settlements default."""
import json, re, shutil, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_settlement_release2 import render

OUT = ROOT / 'output/settlement_release3_20261113'; DATA = ROOT / 'atlases/earth_fit/data'


def main():
    fantasy = json.loads((OUT / 'fantasy.json').read_text())
    for name in ('placement_review.json', 'fantasy_review.json'):
        r = json.loads((OUT / name).read_text())
        if r['status'] != 'passed' or r['fantasy_sha256'] != sha(OUT / 'fantasy.json'):
            raise ValueError('Current review required: ' + name)
    test = json.loads((ROOT / 'output/settlement_placement_iteration_20261113/family_b/results.json').read_text())
    meta = json.loads((DATA / 'atlas.json').read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text())
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in (DATA / 'atlas.json', DATA / 'settled_reach.json', DATA / 'settlement_release2.json')}
    target = DATA / 'settlement_release3'; packets = {}
    for mode in ('raw', 'corrected'):
        (target / mode).mkdir(parents=True, exist_ok=True); old = parent['packets'][mode]; c = fantasy['climates'][mode]
        model = json.loads((OUT / f'placed_{mode}_sites.json').read_text()); f = dict(np.load(OUT / f'placed_{mode}_fields.npz'))
        csv_file = target / mode / 'towns.csv'; shutil.copyfile(OUT / f'placed_{mode}_towns.csv', csv_file); options = []
        for scenario, label, role in (('central', 'sliding 100–500 people/ha', 'published method'), ('low', 'flat 100 people/ha', 'cautious alternative')):
            r = c['residents'][scenario]; file = target / mode / f'towns_{scenario}.webp'
            render(mode, scenario, model['sites'], model['actors'], f, meta).save(file, lossless=True)
            note = (f"Release 3: town POSITIONS and SIZES both tested on Earth. Positions: the earlier town rule plus a pull towards the old "
                f"heartlands (800 km) beat the earlier rule in {test['quadrant_wins']} of 8 regions of Han China and the Roman Empire, with the setting chosen on the other "
                f"pool; {c['placement']['moved']} of {c['placement']['unmarked']} unmarked towns moved, every marked place stays, and the track network is rebuilt. "
                f"Sizes: built-up areas follow the official catalogue of Roman cities (Hanson 2016). Residents = area × {label} ({role}), a density reading, not a census: "
                f"{r['total']/1e6:.2f} M town residents, {100*r['share_of_world_people']:.1f}% of the world's people, largest {r['largest']:,.0f}. Sizes follow the campaign's own ranking: "
                f"capital, major cities, fortified cities, fortified towns, then unmarked towns (a lore choice). Every resident is taken from surrounding rural cells. "
                f"Only {r['local_cereal']['fully_supported_sites']} of {c['sites']} towns (white centre) could be fed from one day's local grain collection; the rest depend on wider supply. "
                f"All Earth data were already used in development: cross-pool and held-out checks, not a blind test. Reach, trade and administration layers still use the earlier towns.")
            options.append(dict(value=f'release3_{scenario}', label=f'Release 3 · Earth-tested positions and sizes · {label} ({role})', note=note,
                integrated_support=False, release3=True, file=str(file.relative_to(DATA)), file_sha256=sha(file), download=str(csv_file.relative_to(DATA)),
                items=[dict(color='#59636b', label='Circle area ∝ town residents (1,000 · 10,000 · 100,000 → radius 2.0 · 3.6 · 8.7 px)'),
                       dict(color='#1d1d1d', label='Dark outline: marked campaign place; white: proposed town'),
                       dict(color='#ffffff', label='White centre: fed by one day’s local grain collection'),
                       dict(color='#8a7458', label='Brown lines: rebuilt minor tracks'),
                       dict(color='#cca985', label='Darker land: larger share of rural people moved to towns')],
                caption='Positions and sizes are calibrated patterns; an individual proposed town is one draw, not a prediction.'))
        packets[mode] = dict(shape=list(f['land'].shape), parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'], options=dict(reach_towns=options),
            towns_csv=str(csv_file.relative_to(DATA)), towns_csv_sha256=sha(csv_file), summary=c)
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest: raise ValueError('Earlier atlas packet modified: ' + path)
    write(DATA / 'settlement_release3.json', dict(version=1, status='earth_tested_positions_and_sizes_default_settlements_map',
        default_adoption=True, default_option='release3_central', placement_test_passed=test['passed'], packets=packets,
        fantasy_sha256=sha(OUT / 'fantasy.json'), publisher_sha256=sha(Path(__file__)), report='../../reports/SETTLEMENT_RELEASE3_20261113.md'))
    page = DATA.parent / 'index.html'; html = page.read_text()
    tag = re.search(r'<script src="settled-reach\.js"[^>]*></script>', html).group(0)
    if 'data-settlement-release3-enabled' not in tag:
        page.write_text(html.replace(tag, tag.replace('></script>', ' data-settlement-release3-enabled></script>')))
    for name in ('settled-reach.js', 'evidence.js'):
        shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_release3_default_settlements_map',
        manifest_sha256=sha(DATA / 'settlement_release3.json'), earlier_packets_sha256=preserved, publisher_sha256=sha(Path(__file__))))
    print('published release 3')


if __name__ == '__main__':
    main()
