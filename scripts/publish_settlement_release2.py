"""Publish release-2 calibrated settlement sizes as Settlements map options."""
import gzip, json, re, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_release2_20261113'; DATA = ROOT / 'atlases/earth_fit/data'
SCALE = 3      # supersample for clean circles


def radius(people):
    return 1.2 + np.sqrt(people) / 42.0          # px at 2000 px width: 1k 2.0, 10k 3.6, 100k 8.7, 250k 13.1


def render(mode, scenario, sites, actors, f, meta):
    land = f['land']; h, w = land.shape; W, H = meta['width'] * SCALE, meta['height'] * SCALE
    rural = np.divide(f['rural_' + scenario], f['people'], out=np.ones_like(f['people']), where=f['people'] > 0)
    rgb = np.empty((h, w, 3)); rgb[:] = [.84, .89, .94]
    drawn = np.clip(1 - rural, 0, .8)[land][:, None] / .8
    rgb[land] = np.array([.90, .88, .82]) * (1 - drawn) + np.array([.80, .66, .52]) * drawn
    image = Image.fromarray(np.rint(rgb * 255).astype('u1')).resize((W, H), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image); px = W / w
    people = f['residents_' + scenario]; support = f['local_support_share_' + scenario]
    for j in np.argsort(-people):
        s = sites[j]; x, y = (s['column'] + .5) * px, (s['row'] + .5) * px; r = radius(people[j]) * SCALE
        color = actors[s['actor_index']]['color'] if s['actor_index'] >= 0 else '#59636b'
        edge = '#1d1d1d' if s['marked'] else '#ffffff'
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=edge, width=SCALE if s['marked'] else max(1, SCALE // 2))
        if support[j] >= 1:
            draw.ellipse((x - SCALE, y - SCALE, x + SCALE, y + SCALE), fill='#ffffff')
    return image.resize((meta['width'], meta['height']), Image.Resampling.LANCZOS)


def main():
    fantasy = json.loads((OUT / 'fantasy.json').read_text()); review = json.loads((OUT / 'fantasy_review.json').read_text())
    if review['status'] != 'passed' or review['fantasy_sha256'] != sha(OUT / 'fantasy.json'):
        raise ValueError('Current reviewed fantasy build required')
    earth = json.loads((OUT / 'results.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    parent = json.loads((DATA / 'settled_reach.json').read_text())
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in (DATA / 'atlas.json', DATA / 'settled_reach.json')}
    target = DATA / 'settlement_release2'; packets = {}
    g = earth['sizes']['primary']
    for mode in ('raw', 'corrected'):
        (target / mode).mkdir(parents=True, exist_ok=True)
        folder = DATA / ('corrected' if mode == 'corrected' else ''); old = parent['packets'][mode]
        model = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
        f = dict(np.load(OUT / f'fantasy_{mode}_fields.npz')); c = fantasy['climates'][mode]
        csv_file = target / mode / 'towns.csv'; shutil.copyfile(OUT / f'fantasy_{mode}_towns.csv', csv_file)
        options = []
        for scenario, label, role in (('central', 'sliding 100–500 people/ha', 'published method'), ('low', 'flat 100 people/ha', 'cautious alternative')):
            r = c['residents'][scenario]; file = target / mode / f'towns_{scenario}.webp'
            render(mode, scenario, model['sites'], model['actors'], f, meta).save(file, lossless=True)
            note = (f"Release 2: town SIZES calibrated on Earth, on the existing town positions. Built-up areas follow the official "
                f"catalogue of Roman cities (Hanson 2016): held-out distribution distance {g['gate']['mean_ks']:.3f} against a 0.10 limit. "
                f"Residents = area × {label} ({role}; Hanson 2016 and Hanson & Ortman 2017 find density rising with city size and a 20–30% urban share), a density scenario, not a census: {r['total']/1e6:.2f} M town residents, "
                f"{100*r['share_of_world_people']:.1f}% of the world's people, largest {r['largest']:,.0f}. Which place is large is "
                f"almost unexplained on Earth, so sizes follow the campaign's own ranking: capital, major cities, fortified cities, fortified towns, then unmarked towns (a lore choice). "
                f"Every resident is taken from surrounding rural cells; nobody is created. Only {r['local_cereal']['fully_supported_sites']} of "
                f"{c['sites']} towns (white centre) could be fed from one day's local grain collection; the rest depend on wider supply. "
                f"Town positions were NOT changed: the tested new placement rule won 5 of 8 regions, short of its declared 6. "
                f"Reach, trade and administration layers still use the earlier settlement sizes.")
            options.append(dict(value=f'release2_{scenario}', label=f'Release 2 · Earth-calibrated sizes · {label} ({role})', note=note,
                integrated_support=False, release2=True, file=str(file.relative_to(DATA)), file_sha256=sha(file),
                download=str(csv_file.relative_to(DATA)),
                items=[dict(color='#59636b', label='Circle area ∝ town residents (1,000 · 10,000 · 100,000 → radius 2.0 · 3.6 · 8.7 px)'),
                       dict(color='#1d1d1d', label='Dark outline: marked campaign place; white: proposed town'),
                       dict(color='#ffffff', label='White centre: fed by one day’s local grain collection'),
                       dict(color='#cca985', label='Darker land: larger share of rural people moved to towns')],
                caption='Sizes are a calibrated distribution; an individual town is one seeded draw, not a prediction.'))
        packets[mode] = dict(shape=list(f['land'].shape), parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'], options=dict(reach_towns=options),
            towns_csv=str(csv_file.relative_to(DATA)), towns_csv_sha256=sha(csv_file), summary=c)
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest: raise ValueError('Original atlas packet modified: ' + path)
    write(DATA / 'settlement_release2.json', dict(version=1, status='earth_calibrated_sizes_legacy_placement_optional',
        default_adoption=True, default_option='release2_central', default_basis='owner instruction, plan amendment A5', placement_test_passed=earth['placement']['passed'], size_gate_passed=g['gate']['passed'],
        packets=packets, fantasy_sha256=sha(OUT / 'fantasy.json'), earth_results_sha256=sha(OUT / 'results.json'),
        publisher_sha256=sha(Path(__file__)), report='../../reports/SETTLEMENT_RELEASE2_20261113.md'))
    page = DATA.parent / 'index.html'; html = page.read_text()
    tag = re.search(r'<script src="settled-reach\.js"[^>]*></script>', html).group(0)
    if 'data-settlement-release2-enabled' not in tag:
        page.write_text(html.replace(tag, tag.replace('></script>', ' data-settlement-release2-enabled></script>')))
    for name in ('settled-reach.js', 'evidence.js'):
        shutil.copyfile(ROOT / 'atlas' / name, DATA.parent / name)
    write(OUT / 'atlas_publication.json', dict(status='published_release2_sizes_default_settlements_map', defaults_unchanged=False,
        manifest_sha256=sha(DATA / 'settlement_release2.json'), original_packets_sha256=preserved, publisher_sha256=sha(Path(__file__))))
    print('published', {m: [o['value'] for o in p['options']['reach_towns']] for m, p in packets.items()})


if __name__ == '__main__':
    main()
