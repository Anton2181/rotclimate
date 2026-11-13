"""Publish the wider grain supply scenario: supply maps, CSVs and the updated default-map legend."""
import json, re, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_settlement_release2 import render, radius, SCALE

OUT = ROOT / 'output/settlement_wide_supply_20261113'; R3 = ROOT / 'output/settlement_release3_20261113'
DATA = ROOT / 'atlases/earth_fit/data'; COLORS = {'self': '#3f8f5f', 'imports': '#3f78b4', 'short': '#c8503a'}
OLD_SENTENCE = re.compile(r"(Only \d+ of [\d,]+ towns \(white centre\) could be fed from one day's local grain collection; the rest depend on wider supply\. |\d+ of \d+ towns \(white centre\) can be fed when grain may travel[^.]*\. )")


def supply_map(sites, f, z, key, residents, meta):
    land = f['land']; h, w = land.shape; W, H = meta['width'] * SCALE, meta['height'] * SCALE
    rgb = np.empty((h, w, 3)); rgb[:] = [.84, .89, .94]; rgb[land] = [.90, .88, .82]
    reach = (z['share'].max(0) > 0).reshape(h, w); rgb[land & ~reach] = [.80, .78, .74]
    image = Image.fromarray(np.rint(rgb * 255).astype('u1')).resize((W, H), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image); px = W / w
    xy = lambda i: ((sites[i]['column'] + .5) * px, (sites[i]['row'] + .5) * px)
    ships = z[key + '_shipments']; top = ships[np.argsort(-ships[:, 3])][:400]
    for i, j, _, got in top[::-1]:
        draw.line([xy(int(i)), xy(int(j))], fill='#5a6f8a', width=max(1, int(round(SCALE * (0.4 + np.sqrt(got / 912500.0) / 120)))))
    fed = z[key + '_fed_share']; own = z[key + '_delivered'] >= residents * 912500.0 * (1 - 1e-9)
    for j in np.argsort(-residents):
        x, y = xy(int(j)); r = radius(residents[j]) * SCALE
        color = COLORS['self'] if own[j] else (COLORS['imports'] if fed[j] >= 1 - 1e-6 else COLORS['short'])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline='#1d1d1d' if sites[j]['marked'] else '#ffffff', width=max(1, SCALE // 2))
    return image.resize((meta['width'], meta['height']), Image.Resampling.LANCZOS)


def main():
    results = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('Current reviewed supply plan required')
    meta = json.loads((DATA / 'atlas.json').read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text())
    towns = json.loads((DATA / 'settlement_release3.json').read_text()); target = DATA / 'release3/supply'; packets = {}
    for mode in ('raw', 'corrected'):
        (target / mode).mkdir(parents=True, exist_ok=True); old = parent['packets'][mode]; c = results['climates'][mode]['scenarios']
        model = json.loads((R3 / f'placed_{mode}_sites.json').read_text()); f = dict(np.load(R3 / f'placed_{mode}_fields.npz')); z = np.load(OUT / f'supply_{mode}.npz')
        csv_file = target / mode / 'towns.csv'; shutil.copyfile(OUT / f'supply_{mode}_towns.csv', csv_file); options = []
        for key, label in (('central_x10', '10% of surplus grain marketed'), ('central_x33', 'one third of surplus grain marketed')):
            s = c[key]; L = s['ledger_person_years']; file = target / mode / f'supply_{key}.webp'
            supply_map(model['sites'], f, z, key, f['residents_central'], meta).save(file, lossless=True)
            note = (f"Scenario, not an Earth test: can the release-3 towns (sliding density) be fed if grain may travel? Each cell markets {label.split(' of ')[0]} of "
                f"its cereal surplus to the town it reaches most cheaply; towns with excess ship to towns in need, cheapest link first. Transport is paid in grain: "
                f"road haulage eats a load's whole value at about 270 km (Duncan-Jones), and sea and river carriage cost 1/28 and 1/5 as much per km (Diocletian's Price Edict). "
                f"Result: {s['self_sufficient_towns']} towns are fed by their own hinterland, {s['fed_with_imports_towns']} with imports and {s['short_towns']} stay short; "
                f"{100*s['fed_share_of_residents']:.0f}% of town residents are fed. Of {L['available']/1e6:.1f} M person-years of marketed grain, "
                f"{(L['hinterland_transport']+L['between_town_transport'])/1e6:.1f} M are consumed by transport. Wheat and barley only; no other foods, prices, "
                f"shipping capacity, storage or state grain fleets. Town sizes are not changed by this map.")
            options.append(dict(value='release3_supply' + ('' if key.endswith('10') else '_x33'), label=f'Release 3 · grain supply · {label}', note=note,
                integrated_support=False, release3=True, file=str(file.relative_to(DATA)), file_sha256=sha(file), download=str(csv_file.relative_to(DATA)),
                items=[dict(color=COLORS['self'], label='Fed by its own freight hinterland'), dict(color=COLORS['imports'], label='Fed with grain shipped from other towns'),
                       dict(color=COLORS['short'], label='Still short of grain'), dict(color='#5a6f8a', label='Lines: the 400 largest grain shipments'),
                       dict(color='#ccc7bd', label='Darker land: beyond grain-carrying reach of any town')],
                caption='A declared scenario on existing freight costs; nothing is fitted to Earth.'))
        packets[mode] = dict(shape=list(f['land'].shape), parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'], options=dict(reach_towns=options),
            towns_csv=str(csv_file.relative_to(DATA)), towns_csv_sha256=sha(csv_file), summary=c)
        # default settlement maps: white centre now means fed including imports (declared legend change)
        for option in towns['packets'][mode]['options']['reach_towns']:
            density = option['value'].split('_')[1]; key = f'{density}_x10'; s = c[key]
            g = dict(f); g['local_support_share_' + density] = z[key + '_fed_share']
            file = DATA / option['file']; render(mode, density, model['sites'], model['actors'], g, meta).save(file, lossless=True)
            option['file_sha256'] = sha(file)
            sentence = (f"{s['self_sufficient_towns'] + s['fed_with_imports_towns']} of {s['towns']} towns (white centre) can be fed when grain may travel "
                        f"(10% of surplus marketed; see the grain supply map); " + (f"{s['short_towns']} of the largest stay short. " if s['short_towns'] else "none stay short. "))
            option['note'], n = OLD_SENTENCE.subn(sentence, option['note']) if OLD_SENTENCE.search(option['note']) else (option['note'], 1)
            for item in option['items']:
                if item['label'].startswith('White centre'): item['label'] = 'White centre: fed, including grain shipped in'
    towns['supply_legend'] = 'white centre = fed including imports (wide supply, 10% marketed)'
    write(DATA / 'settlement_release3.json', towns)
    write(DATA / 'release3_supply.json', dict(version=1, status='wide_grain_supply_scenario_not_fitted', packets=packets,
        results_sha256=sha(OUT / 'results.json'), publisher_sha256=sha(Path(__file__)), report='../../reports/SETTLEMENT_WIDE_SUPPLY_20261113.md'))
    page = DATA.parent / 'index.html'; html = page.read_text()
    tag = re.search(r'<script src="settled-reach\.js"[^>]*></script>', html).group(0)
    if 'data-release3-supply-enabled' not in tag:
        page.write_text(html.replace(tag, tag.replace('></script>', ' data-release3-supply-enabled></script>')))
    for name in ('settled-reach.js', 'evidence.js'):
        shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published', manifest_sha256=sha(DATA / 'release3_supply.json'),
        settlements_manifest_sha256=sha(DATA / 'settlement_release3.json'), publisher_sha256=sha(Path(__file__))))
    print('published', {m: [o['value'] for o in p['options']['reach_towns']] for m, p in packets.items()})


if __name__ == '__main__':
    main()
