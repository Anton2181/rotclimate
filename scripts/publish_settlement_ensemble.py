"""Publish the 40-draw recurrence map as an extra Settlements option (run after publish_settlement_release3 / wide supply)."""
import json, re, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_settlement_release2 import radius, SCALE

ENS = ROOT / 'output/settlement_ensemble_20261115'; PUB = ROOT / 'output/settlement_hierarchy_map_20261115'; DATA = ROOT / 'atlases/earth_fit/data'
STOPS = [(0.0, (0.90, 0.88, 0.82)), (0.2, (0.93, 0.78, 0.55)), (0.5, (0.85, 0.47, 0.25)), (1.0, (0.45, 0.12, 0.10))]


def color(v):
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if v <= b: t = (v - a) / (b - a); return [ca[i] + t * (cb[i] - ca[i]) for i in range(3)]
    return list(STOPS[-1][1])


def main():
    res = json.loads((ENS / 'results.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    towns = json.loads((DATA / 'settlement_release3.json').read_text())
    for mode in ('raw', 'corrected'):
        z = np.load(ENS / f'recurrence_{mode}.npz'); rec, land = z['recurrence'], z['land']; h, w = land.shape
        rgb = np.empty((h, w, 3)); rgb[:] = [.84, .89, .94]
        lut = np.array([color(v) for v in np.linspace(0, 1, 101)]); rgb[land] = lut[np.rint(rec[land] * 100).astype(int)]
        W, H = meta['width'] * SCALE, meta['height'] * SCALE; img = Image.fromarray(np.rint(rgb * 255).astype('u1')).resize((W, H), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(img); px = W / w; sites = json.loads((PUB / f'release3/placed_{mode}_sites.json').read_text())['sites']
        f = np.load(PUB / f'release3/placed_{mode}_fields.npz'); people = f['residents_central']
        for j, s in enumerate(sites):
            if not s['marked']: continue
            x, y = (s['column'] + .5) * px, (s['row'] + .5) * px; r = radius(people[j]) * SCALE
            draw.ellipse((x - r, y - r, x + r, y + r), fill='#ffffff', outline='#1d1d1d', width=SCALE)
        folder = DATA / 'settlement_release3' / mode; file = folder / 'towns_recurrence.webp'
        img.resize((meta['width'], meta['height']), Image.Resampling.LANCZOS).save(file, lossless=True)
        csv_file = folder / 'marked_residents_range.csv'; shutil.copyfile(ENS / f'marked_residents_{mode}.csv', csv_file)
        s = res['summary'][mode]
        note = (f"Where proposed towns recur: the release-3 placement and the settlement-hierarchy sizes redrawn {s['seeds']} times with different random seeds "
                f"(the default map is draw 1). Darker land had a proposed town within about 9 km in more of the draws; {s['hotspots_ge_half']} places hold a town in at least half of them, "
                f"while proposed towns elsewhere move between draws. Marked campaign places (white) are fixed. The download gives each marked place's residents "
                f"in the 10th, 50th and 90th percentile draw (sliding density). A proposed town on the default map is one draw; this map shows which positions are robust.")
        opts = [o for o in towns['packets'][mode]['options']['reach_towns'] if o['value'] != 'release3_recurrence']
        opts.append(dict(value='release3_recurrence', label='Release 3 · where proposed towns recur (40 draws)', note=note, integrated_support=False, release3=True,
            file=str(file.relative_to(DATA)), file_sha256=sha(file), download=str(csv_file.relative_to(DATA)),
            items=[dict(color='#7a1e1a', label='Dark: a proposed town here in most draws'), dict(color='#d98a4a', label='Mid: in about half of the draws'),
                   dict(color='#e6e0d1', label='Pale: rarely or never'), dict(color='#ffffff', label='White circles: marked campaign places (fixed)')],
            caption='Recurrence over 40 placement and size draws; not a probability of a historical town.'))
        towns['packets'][mode]['options']['reach_towns'] = opts
    write(DATA / 'settlement_release3.json', towns)
    write(ENS / 'publication.json', dict(status='published', manifest_sha256=sha(DATA / 'settlement_release3.json'), publisher_sha256=sha(Path(__file__))))
    print('published recurrence option')


if __name__ == '__main__':
    main()
